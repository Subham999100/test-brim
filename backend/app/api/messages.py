import json
import inspect
import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, load_only

logger = logging.getLogger(__name__)

from backend.app.database import get_db, SessionLocal
from backend.app.models.user import User
from backend.app.models.chat import Chat
from backend.app.models.message import Message
from backend.app.models.citation import Citation
from backend.app.models.web_source import WebSource
from backend.app.models.web_image import WebImage
from backend.app.models.uploaded_attachment import UploadedAttachment
from backend.app.models.shared_prompt import SharedPrompt
from backend.app.schemas.message import MessageCreate, MessageFeedback, MessageResponse, SavePartialRequest
from backend.app.security.auth import get_current_user
from backend.app.security.ratelimit import rate_limiter
from backend.app.security.stream_tokens import STREAM_TOKEN_TTL_SECONDS, issue_stream_token, verify_stream_token
from backend.app.services.rag_service import rag_service
from backend.app.services.llm_service import SPRINT_CASUAL_SYSTEM_PROMPT, UNAVAILABLE_RESPONSE, llm_service
from backend.app.services.query_router import QueryRoute, query_router
from backend.app.services.retrieval_service import retrieval_service
from backend.app.services.reranking_service import reranking_service
from backend.app.services.grounding_service import grounding_service
from backend.app.services.web_search_service import web_search_service
from backend.app.services.sap_classifier import NON_SAP_REFUSAL_RESPONSE, sap_classifier
from backend.app.services.evidence_markers import strip_markers, StreamingMarkerStripper
from backend.app.services.conversation_memory_service import MemoryIntent, conversation_memory_service
from backend.app.services.public_payload import public_done_event
from backend.app.services import audit_log, token_meter
from backend.app.config import settings

# "[Attached: a.pdf (2 pages)]\n\n" header that prefixes prompts sent with files.
ATTACHED_PREFIX = re.compile(r"^\[Attached:.*?\]\n\n", re.DOTALL)



def visible_content(content: str, is_admin: bool) -> str:
    """Inline evidence markers point at sources; users who cannot see sources get clean text."""
    return content if is_admin else strip_markers(content or "")

def _fit(model, field: str, value):
    """Clip display metadata to its VARCHAR length; PostgreSQL rejects over-long values."""
    if value is None:
        return None
    value = str(value)
    limit = getattr(model.__table__.c[field].type, "length", None)
    return value if not limit or len(value) <= limit else value[: limit - 1] + "…"


def _url_fits(model, field: str, url) -> bool:
    """A clipped URL is a broken link, so over-long URLs are skipped instead."""
    limit = getattr(model.__table__.c[field].type, "length", None)
    return bool(url) and (not limit or len(str(url)) <= limit)


def source_rows(message_id: str, citations, web_sources, images) -> list:
    """Citation, web-source and web-image rows for an assistant message, sized to their columns."""
    rows = []
    for c in citations or []:
        document = str(c.get("document", ""))
        rows.append(Citation(
            message_id=message_id,
            source_type="knowledge_base",
            document_id=_fit(Citation, "document_id", "doc-" + document),
            document_name=_fit(Citation, "document_name", document),
            chunk_id="chunk-ref",
            page_number=c.get("page"),
            section=_fit(Citation, "section", c.get("section")),
            similarity_score=c.get("score"),
            citation_text=c.get("snippet"),
        ))
    for w in web_sources or []:
        if not _url_fits(WebSource, "url", w.get("url")):
            logger.warning("Skipping web source with over-long URL (%d chars)", len(str(w.get("url") or "")))
            continue
        rows.append(WebSource(
            message_id=message_id,
            url=w.get("url"),
            title=_fit(WebSource, "title", w.get("title")),
            domain=_fit(WebSource, "domain", w.get("domain")),
            snippet=w.get("snippet"),
        ))
    for image in images or []:
        if not _url_fits(WebImage, "url", image.get("url")):
            logger.warning("Skipping web image with over-long URL (%d chars)", len(str(image.get("url") or "")))
            continue
        source_url = image.get("source_url")
        rows.append(WebImage(
            message_id=message_id,
            url=image.get("url"),
            description=image.get("description"),
            alt_text=_fit(WebImage, "alt_text", image.get("alt_text")),
            source_url=source_url if _url_fits(WebImage, "source_url", source_url) else None,
            source_title=_fit(WebImage, "source_title", image.get("source_title")),
        ))
    return rows


router = APIRouter(prefix="/chats/{chat_id}/messages", tags=["Messages"])

def verify_chat_ownership(chat_id: str, user_id: str, db: Session) -> Chat:
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user_id).first()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    return chat


def persist_uploaded_attachments(message: Message, attachments: List[dict]) -> None:
    """Keep extracted text scoped to the user message that uploaded it."""
    message.uploaded_attachments = [
        UploadedAttachment(
            name=attachment["name"],
            file_type=attachment.get("file_type") or "txt",
            page_count=attachment.get("page_count"),
            extracted_text=attachment["text"],
        )
        for attachment in attachments
        if attachment.get("text", "").strip()
    ]


def latest_chat_attachments(
    db: Session, chat_id: str, current_message_id: str, current_attachments: List[dict]
) -> List[dict]:
    """Reuse the most recently attached files for follow-up questions in this chat."""
    if current_attachments:
        return current_attachments
    prior_message = (
        db.query(Message)
        .join(UploadedAttachment, UploadedAttachment.message_id == Message.id)
        .filter(
            Message.chat_id == chat_id,
            Message.role == "user",
            Message.id != current_message_id,
        )
        .order_by(Message.created_at.desc())
        .first()
    )
    if not prior_message:
        return []
    return [
        {
            "name": item.name,
            "file_type": item.file_type,
            "page_count": item.page_count,
            "text": item.extracted_text,
        }
        for item in prior_message.uploaded_attachments
    ]

@router.get("", response_model=List[MessageResponse])
def get_messages(
    chat_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    verify_chat_ownership(chat_id, current_user.id, db)
    messages = (
        db.query(Message)
        .options(load_only(
            Message.id, Message.chat_id, Message.role, Message.content, Message.source_type,
            Message.grounding_score, Message.created_at, Message.feedback,
        ))
        .filter(Message.chat_id == chat_id)
        .order_by(Message.created_at.asc())
        .all()
    )

    is_admin = bool(current_user.is_admin)
    result = []
    for msg in messages:
        c_list = [
            {
                "id": c.id,
                "document": c.document_name,
                "page": c.page_number,
                "section": c.section,
                "score": c.similarity_score,
                "snippet": c.citation_text
            }
            for c in msg.citations
        ] if is_admin else []

        w_list = [
            {
                "id": w.id,
                "title": w.title,
                "url": w.url,
                "domain": w.domain,
                "snippet": w.snippet
            }
            for w in msg.web_sources
        ] if is_admin else []

        image_list = [
            {
                "url": image.url,
                "description": image.description,
                "alt_text": image.alt_text,
                "source_url": image.source_url if is_admin else None,
                "source_title": image.source_title if is_admin else None,
                "relevance_score": None,
            }
            for image in msg.images
        ]
        result.append(
            MessageResponse(
                id=msg.id,
                chat_id=msg.chat_id,
                role=msg.role,
                content=visible_content(msg.content, is_admin),
                source_type=msg.source_type if is_admin else None,
                grounding_score=msg.grounding_score if is_admin else None,
                verification_status=("unavailable" if msg.source_type == "unavailable" else None),
                created_at=msg.created_at,
                feedback=msg.feedback,
                citations=c_list,
                web_sources=w_list,
                images=image_list,
                attachments=[
                    {
                        "name": attachment.name,
                        "file_type": attachment.file_type,
                        "page_count": attachment.page_count,
                    }
                    for attachment in msg.uploaded_attachments
                ] or None,
            )
        )
    return result

def _invoke_rag_process(db: Session, query: str, chat_history, user, attachments, chat_id: Optional[str] = None):
    kwargs = {"chat_history": chat_history, "user": user, "attachments": attachments}
    target = getattr(rag_service.process_query, "side_effect", None) or rag_service.process_query
    try:
        sig = inspect.signature(target)
        if "chat_id" in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
            kwargs["chat_id"] = chat_id
    except Exception:
        kwargs["chat_id"] = chat_id
    try:
        return rag_service.process_query(db, query, **kwargs)
    except TypeError as te:
        if "chat_id" in str(te) and "chat_id" in kwargs:
            kwargs.pop("chat_id", None)
            return rag_service.process_query(db, query, **kwargs)
        raise


def _invoke_rag_stream(db: Session, query: str, chat_history, user, attachments, chat_id: Optional[str] = None):
    kwargs = {"chat_history": chat_history, "user": user, "attachments": attachments}
    target = getattr(rag_service.stream_query, "side_effect", None) or rag_service.stream_query
    try:
        sig = inspect.signature(target)
        if "chat_id" in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
            kwargs["chat_id"] = chat_id
    except Exception:
        kwargs["chat_id"] = chat_id
    try:
        return rag_service.stream_query(db, query, **kwargs)
    except TypeError as te:
        if "chat_id" in str(te) and "chat_id" in kwargs:
            kwargs.pop("chat_id", None)
            return rag_service.stream_query(db, query, **kwargs)
        raise


def _plain_chat_history(db: Session, chat_id: str, exclude_message_id: Optional[str] = None):
    """Read conversational text only; Sprint must not touch message embeddings or retrieval services."""
    query = db.query(Message.id, Message.role, Message.content).filter(Message.chat_id == chat_id)
    if exclude_message_id:
        query = query.filter(Message.id != exclude_message_id)
    rows = query.order_by(Message.created_at.desc(), Message.id.desc()).limit(20).all()
    return [{"id": msg_id, "role": role, "content": content} for msg_id, role, content in reversed(rows)]


def _conversation_chars(db: Session, chat_id: str, exclude_message_id: Optional[str] = None) -> int:
    """Length of the whole conversation, which a generic chatbot resends with every question."""
    query = db.query(func.coalesce(func.sum(func.length(Message.content)), 0)).filter(Message.chat_id == chat_id)
    if exclude_message_id:
        query = query.filter(Message.id != exclude_message_id)
    return int(query.scalar() or 0)


def _history_chars(history) -> int:
    return sum(len(item.get("content") or "") for item in history or [])


def _usage_event(tokens: int) -> str:
    return f"data: {json.dumps({'type': 'usage', 'tokens': tokens})}\n\n"


# Questions about the conversation itself; they bypass the SAP-only scope check.
_SPRINT_RECALL_INTENTS = (MemoryIntent.HISTORY_RECALL, MemoryIntent.CROSS_CONVERSATION_RECALL, MemoryIntent.MIXED)


def _sprint_memory(
    db: Session, chat_id: str, user_id: str, query: str, chat_history, user_message_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Conversation memory for Sprint, without embeddings: exact first/last-question lookups, the rolling
    summary of turns older than the 20-message window, and keyword recall from this chat or the user's
    other chats. A set "answer" is final and is returned without calling the LLM.
    """
    intent = conversation_memory_service.classify_intent(query, chat_history=chat_history)
    memory: Dict[str, Any] = {"intent": intent, "answer": None, "summary": None, "recalled": []}
    if intent in (MemoryIntent.FIRST_MESSAGE_LOOKUP, MemoryIntent.LAST_MESSAGE_LOOKUP):
        memory["answer"] = conversation_memory_service.exact_lookup_answer(
            db, chat_id, intent, exclude_message_id=user_message_id
        )
        return memory

    memory["summary"] = conversation_memory_service.get_chat_summary(db, chat_id)
    if intent in _SPRINT_RECALL_INTENTS:
        cross = intent == MemoryIntent.CROSS_CONVERSATION_RECALL
        memory["recalled"] = conversation_memory_service.search_history(
            db, query, user_id=user_id, current_chat_id=chat_id,
            exclude_message_ids=[m.get("id") for m in (chat_history or [])] + [user_message_id],
            cross_conversation=cross, top_k=5, use_embeddings=False,
        )
        if not memory["recalled"] and cross:
            memory["answer"] = (
                "I searched your other conversations, but could not find any earlier discussion matching your query."
            )
        elif not memory["recalled"] and intent == MemoryIntent.HISTORY_RECALL and not chat_history and not memory["summary"]:
            memory["answer"] = (
                "I reviewed our conversation history, but could not find any previous mention of that in our messages."
            )
    return memory


def _sprint_allowed(query: str, chat_history, attachments) -> bool:
    attachment_text = "\n".join(str(item.get("text") or "") for item in (attachments or []))
    allowed, _ = sap_classifier.classify(f"{query}\n{attachment_text}")
    if not allowed and chat_history:
        prior_user_questions = [
            item.get("content", "") for item in chat_history if item.get("role") == "user"
        ][-3:]
        allowed, _ = sap_classifier.classify("\n".join([*prior_user_questions, query]))
    return allowed


def _sprint_route(query: str, chat_history, attachments, memory: Dict[str, Any]) -> str:
    """
    The Sprint path for this turn; the value is also the stored source_type. Memory answers and SAP
    questions (including SAP follow-ups such as "ok, what about dunning?") win, so only a turn that
    would otherwise be refused is checked for small talk, with the same router as Scholar's casual path.
    """
    if memory.get("answer"):
        return "conversation_memory"
    if memory.get("intent") in _SPRINT_RECALL_INTENTS or _sprint_allowed(query, chat_history, attachments):
        return "sprint"
    if not attachments and query_router.route(query, chat_history=chat_history).route == QueryRoute.EMOTIONAL_CASUAL:
        return "conversational"
    return "refusal"


def _sprint_result(query: str, chat_history, attachments, memory: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    memory = memory or {}
    route = _sprint_route(query, chat_history, attachments, memory)
    if route == "conversation_memory":
        return {
            "answer": memory["answer"], "source_type": "conversation_memory",
            "verification_status": "unverified", "grounding_score": None,
        }
    if route == "refusal":
        return {
            "answer": NON_SAP_REFUSAL_RESPONSE, "source_type": "refusal",
            "verification_status": "unverified", "grounding_score": None,
        }
    if route == "conversational":
        answer = llm_service.generate_emotional_casual_reply(
            query, chat_history=chat_history, system_prompt=SPRINT_CASUAL_SYSTEM_PROMPT
        )
        return {
            "answer": answer, "source_type": "conversational",
            "verification_status": "unverified", "grounding_score": None,
        }

    answer = llm_service.generate_sprint_reply(
        query, chat_history=chat_history, attachments=attachments,
        summary=memory.get("summary"), recalled_messages=memory.get("recalled"),
    )
    return {
        "answer": answer,
        "source_type": "unavailable" if answer == UNAVAILABLE_RESPONSE else "sprint",
        "verification_status": "unavailable" if answer == UNAVAILABLE_RESPONSE else "unverified",
        "grounding_score": None,
    }


@router.post("")
def send_message(
    chat_id: str,
    msg_in: MessageCreate,
    stream: bool = Query(False, description="Enable Server-Sent Events (SSE) streaming"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    chat = verify_chat_ownership(chat_id, current_user.id, db)

    attachments_data = [att.model_dump() for att in (msg_in.attachments or [])]
    user_content = msg_in.content.strip()
    if attachments_data and not user_content.startswith("[Attached"):
        doc_summary = ", ".join([f"{a.get('name', 'Document')} ({a.get('page_count', 1)} pages)" for a in attachments_data])
        user_content = f"[Attached: {doc_summary}]\n\n{user_content}"

    # 1. Save user message
    user_msg = Message(
        chat_id=chat_id,
        role="user",
        content=user_content,
        embedding=None if msg_in.mode == "sprint" else conversation_memory_service.embed_message_content(user_content)
    )
    persist_uploaded_attachments(user_msg, attachments_data)
    db.add(user_msg)
    
    # Auto-generate chat title from first question if default
    if chat.title == "New SAP Chat" or not chat.title:
        words = msg_in.content.strip().split()
        chat.title = " ".join(words[:6]) + ("..." if len(words) > 6 else "")

    chat.updated_at = datetime.now(timezone.utc)
    db.commit()
    if msg_in.mode == "sprint":
        db.refresh(user_msg, attribute_names=["id", "created_at"])
    else:
        db.refresh(user_msg)

    # Fetch recent conversation history (max 20 messages, excluding the new user_msg)
    sprint_memory = None
    if msg_in.mode == "sprint":
        chat_history = _plain_chat_history(db, chat_id, exclude_message_id=user_msg.id)
        request_attachments = attachments_data
        sprint_memory = _sprint_memory(
            db, chat_id, current_user.id, msg_in.content.strip(), chat_history, user_message_id=user_msg.id
        )
    else:
        chat_history = conversation_memory_service.get_recent_messages(
            db, chat_id, limit=20, exclude_message_id=user_msg.id
        )
        request_attachments = latest_chat_attachments(db, chat_id, user_msg.id, attachments_data)

    # 2. Check SSE streaming flow
    if stream:
        if msg_in.mode == "sprint":
            return handle_sprint_streaming_response(
                chat_id, msg_in.content.strip(), chat_history=chat_history,
                current_user=current_user, attachments=request_attachments, user_message_id=user_msg.id,
                memory=sprint_memory, conversation_chars=_conversation_chars(db, chat_id, user_msg.id),
            )
        return handle_streaming_response(
            chat_id, msg_in.content.strip(), chat_history=chat_history, current_user=current_user,
            attachments=request_attachments, user_message_id=user_msg.id,
            conversation_chars=_conversation_chars(db, chat_id, user_msg.id),
        )

    # 3. Sprint makes a direct configured-LLM call; Scholar retains the existing RAG pipeline.
    if msg_in.mode == "sprint":
        rag_result = _sprint_result(msg_in.content.strip(), chat_history, request_attachments, memory=sprint_memory)
        rag_result.update({"citations": [], "web_sources": [], "images": [], "follow_up_questions": []})
    else:
        rag_result = _invoke_rag_process(
            db, msg_in.content.strip(),
            chat_history=chat_history,
            user=current_user,
            attachments=request_attachments,
            chat_id=chat_id
        )

    # 4. Save assistant message
    assistant_msg = Message(
        chat_id=chat_id,
        role="assistant",
        content=rag_result["answer"],
        source_type=rag_result["source_type"],
        grounding_score=rag_result["grounding_score"],
        embedding=None if msg_in.mode == "sprint" else conversation_memory_service.embed_message_content(rag_result["answer"])
    )
    db.add(assistant_msg)
    db.commit()
    if msg_in.mode == "sprint":
        db.refresh(assistant_msg, attribute_names=["id", "created_at"])
    else:
        db.refresh(assistant_msg)

    # 5. Persist citations, web sources and web images
    rows = source_rows(
        assistant_msg.id, rag_result.get("citations", []), rag_result.get("web_sources", []), rag_result.get("images")
    )
    if rows:
        db.add_all(rows)
        db.commit()

    # 6. Incrementally maintain conversation summary (both modes; it reads text only, no embeddings)
    try:
        conversation_memory_service.update_rolling_summary(
            db, chat_id, user_content, rag_result["answer"]
        )
    except Exception as sum_err:
        logger.warning(f"Failed to update rolling summary for chat {chat_id}: {sum_err}")

    if msg_in.mode == "sprint":
        db.refresh(assistant_msg, attribute_names=["id", "created_at"])
    else:
        db.refresh(assistant_msg)

    is_admin = bool(current_user.is_admin)

    return MessageResponse(
        id=assistant_msg.id,
        chat_id=assistant_msg.chat_id,
        role=assistant_msg.role,
        content=visible_content(assistant_msg.content, is_admin),
        source_type=assistant_msg.source_type if is_admin else None,
        grounding_score=assistant_msg.grounding_score if is_admin else None,
        is_in_rag_pipeline=rag_result.get("is_in_rag_pipeline") if is_admin else None,
        kb_score=rag_result.get("kb_score") if is_admin else None,
        web_score=rag_result.get("web_score") if is_admin else None,
        winning_score=rag_result.get("winning_score") if is_admin else None,
        verification_status=(rag_result.get("verification_status") if is_admin or rag_result.get("verification_status") == "unavailable" else None),
        internal_evidence_confidence=rag_result.get("internal_evidence_confidence") if is_admin else None,
        selected_evidence_quality=rag_result.get("selected_evidence_quality") if is_admin else None,
        external_search_used=rag_result.get("external_search_used", False) if is_admin else False,
        created_at=assistant_msg.created_at,
        citations=[
            {
                "id": c.id,
                "document": c.document_name,
                "page": c.page_number,
                "section": c.section,
                "score": c.similarity_score,
                "snippet": c.citation_text
            }
            for c in assistant_msg.citations
        ] if is_admin else [],
        web_sources=[
            {
                "id": w.id,
                "title": w.title,
                "url": w.url,
                "domain": w.domain,
                "snippet": w.snippet
            }
            for w in assistant_msg.web_sources
        ] if is_admin else [],
        images=[
            {
                "url": image.url,
                "description": image.description,
                "alt_text": image.alt_text,
                "source_url": image.source_url if is_admin else None,
                "source_title": image.source_title if is_admin else None,
                "relevance_score": None,
            }
            for image in assistant_msg.images
        ],
        follow_up_questions=rag_result.get("follow_up_questions", [])
    )


@router.post("/stream")
def send_message_stream(
    chat_id: str,
    msg_in: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Direct POST /chats/{chat_id}/messages/stream endpoint for SSE streaming."""
    chat = verify_chat_ownership(chat_id, current_user.id, db)

    attachments_data = [att.model_dump() for att in (msg_in.attachments or [])]
    user_content = msg_in.content.strip()
    if attachments_data and not user_content.startswith("[Attached"):
        doc_summary = ", ".join([f"{a.get('name', 'Document')} ({a.get('page_count', 1)} pages)" for a in attachments_data])
        user_content = f"[Attached: {doc_summary}]\n\n{user_content}"

    # 1. Save user message
    user_msg = Message(
        chat_id=chat_id,
        role="user",
        content=user_content,
        embedding=None if msg_in.mode == "sprint" else conversation_memory_service.embed_message_content(user_content)
    )
    persist_uploaded_attachments(user_msg, attachments_data)
    db.add(user_msg)

    if chat.title == "New SAP Chat" or not chat.title:
        words = msg_in.content.strip().split()
        chat.title = " ".join(words[:6]) + ("..." if len(words) > 6 else "")

    chat.updated_at = datetime.now(timezone.utc)
    db.commit()
    if msg_in.mode == "sprint":
        db.refresh(user_msg, attribute_names=["id", "created_at"])
    else:
        db.refresh(user_msg)

    if msg_in.mode == "sprint":
        chat_history = _plain_chat_history(db, chat_id, exclude_message_id=user_msg.id)
        request_attachments = attachments_data
        return handle_sprint_streaming_response(
            chat_id, msg_in.content.strip(), chat_history=chat_history,
            current_user=current_user, attachments=request_attachments, user_message_id=user_msg.id,
            memory=_sprint_memory(
                db, chat_id, current_user.id, msg_in.content.strip(), chat_history, user_message_id=user_msg.id
            ),
            conversation_chars=_conversation_chars(db, chat_id, user_msg.id),
        )

    chat_history = conversation_memory_service.get_recent_messages(
        db, chat_id, limit=20, exclude_message_id=user_msg.id
    )
    rag_attachments = latest_chat_attachments(db, chat_id, user_msg.id, attachments_data)
    return handle_streaming_response(
        chat_id, msg_in.content.strip(), chat_history=chat_history, current_user=current_user,
        attachments=rag_attachments, user_message_id=user_msg.id,
        conversation_chars=_conversation_chars(db, chat_id, user_msg.id),
    )


@router.post("/{message_id}/edit")
def edit_message_stream(
    chat_id: str,
    message_id: str,
    msg_in: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Replace a user prompt, drop every later message, and stream a fresh answer (SSE)."""
    chat = verify_chat_ownership(chat_id, current_user.id, db)
    user_msg = (
        db.query(Message)
        .options(*(
            [load_only(Message.id, Message.chat_id, Message.role, Message.content, Message.created_at)]
            if msg_in.mode == "sprint" else []
        ))
        .filter(Message.id == message_id, Message.chat_id == chat_id, Message.role == "user")
        .first()
    )
    if not user_msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    new_text = msg_in.content.strip()
    if not new_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Prompt cannot be empty")

    # The old answer and any follow-up turns were built on the old prompt, so they go.
    for later in (
        db.query(Message)
        .options(*([load_only(Message.id)] if msg_in.mode == "sprint" else []))
        .filter(Message.chat_id == chat_id, Message.created_at > user_msg.created_at)
        .all()
    ):
        db.delete(later)

    # Files attached to the original prompt stay attached to the edited one.
    own_attachments = [
        {
            "name": item.name,
            "file_type": item.file_type,
            "page_count": item.page_count,
            "text": item.extracted_text,
        }
        for item in user_msg.uploaded_attachments
    ]
    if own_attachments:
        doc_summary = ", ".join(f"{a['name']} ({a['page_count'] or 1} pages)" for a in own_attachments)
        user_msg.content = f"[Attached: {doc_summary}]\n\n{new_text}"
    else:
        user_msg.content = new_text

    user_msg.embedding = None if msg_in.mode == "sprint" else conversation_memory_service.embed_message_content(user_msg.content)
    chat.updated_at = datetime.now(timezone.utc)
    db.commit()

    if msg_in.mode == "sprint":
        chat_history = _plain_chat_history(db, chat_id, exclude_message_id=user_msg.id)
        return handle_sprint_streaming_response(
            chat_id, new_text, chat_history=chat_history,
            current_user=current_user, attachments=own_attachments, user_message_id=user_msg.id,
            memory=_sprint_memory(db, chat_id, current_user.id, new_text, chat_history, user_message_id=user_msg.id),
            conversation_chars=_conversation_chars(db, chat_id, user_msg.id),
        )

    chat_history = conversation_memory_service.get_recent_messages(
        db, chat_id, limit=20, exclude_message_id=user_msg.id
    )
    rag_attachments = latest_chat_attachments(db, chat_id, user_msg.id, own_attachments)
    return handle_streaming_response(
        chat_id, new_text, chat_history=chat_history, current_user=current_user,
        attachments=rag_attachments, user_message_id=user_msg.id,
        conversation_chars=_conversation_chars(db, chat_id, user_msg.id),
    )


@router.post("/{message_id}/share")
def share_prompt(
    chat_id: str,
    message_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create (or refresh) the public read-only link for one of the user's prompts or answers."""
    verify_chat_ownership(chat_id, current_user.id, db)
    msg = (
        db.query(Message)
        .filter(Message.id == message_id, Message.chat_id == chat_id, Message.role.in_(("user", "assistant")))
        .first()
    )
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    answer = None
    question_msg = msg
    if msg.role == "assistant" and (msg.source_type or "").startswith("interrupted"):
        # Stopped answers are partial and their text came from the client; never publish them (F-37).
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Interrupted answers cannot be shared")
    if msg.role == "assistant":
        # An answer is shared together with the question it answers.
        question_msg = (
            db.query(Message)
            .filter(Message.chat_id == chat_id, Message.role == "user", Message.created_at < msg.created_at)
            .order_by(Message.created_at.desc())
            .first()
        )
        if not question_msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
        # The public page has no sources, so evidence markers are always stripped.
        answer = strip_markers(msg.content or "").strip()

    # Attachment names and extracted file text stay private.
    content = ATTACHED_PREFIX.sub("", question_msg.content, count=1).strip()
    # One atomic upsert: two concurrent shares of the same message get the same link
    # instead of the second failing on the unique message_id.
    token = db.execute(
        pg_insert(SharedPrompt)
        .values(message_id=msg.id, content=content, answer=answer)
        .on_conflict_do_update(
            index_elements=[SharedPrompt.message_id],
            set_={"content": content, "answer": answer, "revoked": False},
        )
        .returning(SharedPrompt.token)
    ).scalar_one()
    db.commit()
    audit_log.record("share_create", request=request, principal=current_user, target=msg.id,
                     details={"includes_answer": answer is not None})
    return {"token": token}


@router.delete("/{message_id}/share", status_code=status.HTTP_204_NO_CONTENT)
def revoke_shared_prompt(
    chat_id: str,
    message_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_chat_ownership(chat_id, current_user.id, db)
    shared = db.query(SharedPrompt).join(Message, SharedPrompt.message_id == Message.id).filter(
        SharedPrompt.message_id == message_id, Message.chat_id == chat_id
    ).first()
    if not shared:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shared prompt not found")
    shared.revoked = True
    db.commit()
    audit_log.record("share_revoke", request=request, principal=current_user, target=message_id)


@router.put("/{message_id}/feedback")
def set_message_feedback(
    chat_id: str,
    message_id: str,
    feedback_in: MessageFeedback,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Record a thumbs up/down on one of the user's answers; a null value clears it."""
    verify_chat_ownership(chat_id, current_user.id, db)
    answer = (
        db.query(Message)
        .filter(Message.id == message_id, Message.chat_id == chat_id, Message.role == "assistant")
        .first()
    )
    if not answer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    answer.feedback = feedback_in.value
    db.commit()
    return {"message_id": answer.id, "feedback": answer.feedback}


@router.post("/save-partial")
def save_partial_message(
    chat_id: str,
    msg_in: SavePartialRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Saves what the user saw of an answer they stopped. Requires the stream id the server issued to this
    user for this chat, and accepts it once, so arbitrary "assistant" text cannot be stored (F-37)."""
    chat = verify_chat_ownership(chat_id, current_user.id, db)
    nonce = verify_stream_token(msg_in.stream_id, current_user.id, chat_id)
    if nonce is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unknown or expired stream")
    if not rate_limiter.backend.hit(f"partial-saved:{nonce}", 1, STREAM_TOKEN_TTL_SECONDS):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This stream was already saved")
    partial_msg = Message(
        chat_id=chat_id,
        role="assistant",
        content=msg_in.content.strip(),
        source_type="interrupted",
        grounding_score=0.0
    )
    db.add(partial_msg)
    chat.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(partial_msg)
    return {"status": "saved", "message_id": partial_msg.id}


def handle_streaming_response(
    chat_id: str,
    query: str,
    db: Session = None,
    chat_history: List[Dict[str, Any]] = None,
    current_user: User = None,
    attachments: Optional[List[Dict[str, Any]]] = None,
    user_message_id: Optional[str] = None,
    conversation_chars: Optional[int] = None,
):
    """
    Generates Server-Sent Events (SSE) stream using the complete verified RAG pipeline.
    Progressively yields structured status stages, LLM token stream, and done event with citations/grounding.
    Persists the completed assistant message in the database once generation concludes.
    `usage` events carry the running token estimate; the done event carries `token_usage`.
    """
    def event_stream():
        save_db = SessionLocal()
        accumulated_text = ""
        done_payload = None
        marker_stripper = None if current_user.is_admin else StreamingMarkerStripper()
        meter = token_meter.TokenMeter()
        reported_tokens = 0

        # Stream id: the only credential save-partial accepts for text shown in this stream (F-37).
        yield f"data: {json.dumps({'type': 'stream', 'stream_id': issue_stream_token(current_user.id, chat_id)})}\n\n"

        # Lets the client swap its optimistic prompt for the stored one (needed to edit it later).
        if user_message_id:
            yield f"data: {json.dumps({'type': 'user_message', 'message_id': user_message_id})}\n\n"

        hist = chat_history
        if hist is None:
            hist = conversation_memory_service.get_recent_messages(
                save_db, chat_id, limit=20, exclude_message_id=user_message_id
            )

        try:
            rag_events = _invoke_rag_stream(save_db, query, chat_history=hist, user=current_user, attachments=attachments, chat_id=chat_id)
            for event in token_meter.metered(rag_events, meter):
                if meter.used_tokens != reported_tokens:
                    reported_tokens = meter.used_tokens
                    yield _usage_event(reported_tokens)
                event_type = event.get("type")

                if event_type == "status":
                    if not current_user.is_admin:
                        event["message"] = "Thinking..." if event.get("stage") != "generating" else "Generating response..."

                elif event_type == "token":
                    accumulated_text += event.get("content", "")
                    if marker_stripper is not None:
                        event["content"] = marker_stripper.feed(event.get("content", ""))
                        if not event["content"]:
                            continue

                elif event_type == "done":
                    if marker_stripper is not None:
                        leftover = marker_stripper.flush()
                        if leftover:
                            yield f"data: {json.dumps({'type': 'token', 'content': leftover})}\n\n"
                    done_payload = event
                    full_answer = event.get("answer", accumulated_text)
                    source_type = event.get("source_type", "knowledge_base")
                    grounding = event.get("grounding_score", 0.0)
                    citations = event.get("citations", [])
                    web_sources = event.get("web_sources", [])
                    images = event.get("images", [])

                    # Anti-duplicate persistence check:
                    # Check if an interrupted or duplicate message was already saved for this turn
                    last_msg = (
                        save_db.query(Message)
                        .filter(Message.chat_id == chat_id)
                        .order_by(Message.created_at.desc())
                        .first()
                    )
                    if last_msg and last_msg.role == "assistant" and last_msg.source_type == "interrupted":
                        # Upgrade the interrupted message to the final verified answer
                        assistant_msg = last_msg
                        assistant_msg.content = full_answer
                        assistant_msg.source_type = source_type
                        assistant_msg.grounding_score = grounding
                        assistant_msg.embedding = conversation_memory_service.embed_message_content(full_answer)
                        save_db.commit()
                    else:
                        assistant_msg = Message(
                            chat_id=chat_id,
                            role="assistant",
                            content=full_answer,
                            source_type=source_type,
                            grounding_score=grounding,
                            embedding=conversation_memory_service.embed_message_content(full_answer)
                        )
                        save_db.add(assistant_msg)
                        save_db.commit()
                        save_db.refresh(assistant_msg)

                    rows = source_rows(assistant_msg.id, citations, web_sources, images)
                    if rows:
                        save_db.add_all(rows)
                        save_db.commit()

                    # Incrementally update conversation summary
                    try:
                        conversation_memory_service.update_rolling_summary(
                            save_db, chat_id, query, full_answer
                        )
                    except Exception as sum_err:
                        logger.warning(f"Failed to update rolling summary for chat {chat_id}: {sum_err}")

                    event["message_id"] = assistant_msg.id
                    event["token_usage"] = meter.summary(
                        question=query, answer=full_answer,
                        conversation_chars=_history_chars(hist) if conversation_chars is None else conversation_chars,
                    )

                    if not current_user.is_admin:
                        # Allowlist: diagnostics, model names, scores and audits stay admin-only.
                        event = public_done_event(event)

                # SSE Event Formats:
                # 1. Main JSON payload: data: {"type": ...}\n\n
                yield f"data: {json.dumps(event)}\n\n"


        except Exception as e:
            logger.error(f"Streaming generation error: {e}", exc_info=True)
            err_event = {
                "type": "error",
                "message": "Generation interrupted. Please try again."
            }
            yield f"data: {json.dumps(err_event)}\n\n"

        finally:
            # A stream that ends before 'done' never finished claim verification, so its text is
            # not stored as an answer (AUDIT_REPORT F-03). The user can simply ask again.
            if not done_payload and accumulated_text.strip():
                logger.info("Stream for chat %s ended before verification; partial text not persisted", chat_id)
            save_db.close()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


def handle_sprint_streaming_response(
    chat_id: str,
    query: str,
    chat_history: Optional[List[Dict[str, Any]]] = None,
    current_user: User = None,
    attachments: Optional[List[Dict[str, Any]]] = None,
    user_message_id: Optional[str] = None,
    memory: Optional[Dict[str, Any]] = None,
    conversation_chars: Optional[int] = None,
):
    """Direct LLM stream and persistence path. It intentionally never calls RAG or embedding services.
    `memory` comes from _sprint_memory: a final memory answer, or summary/recalled context for the LLM."""
    memory = memory or {}

    def event_stream():
        save_db = SessionLocal()
        accumulated_text = ""
        marker_stripper = None if current_user.is_admin else StreamingMarkerStripper()
        done_payload = False
        meter = token_meter.TokenMeter()

        yield f"data: {json.dumps({'type': 'stream', 'stream_id': issue_stream_token(current_user.id, chat_id)})}\n\n"
        if user_message_id:
            yield f"data: {json.dumps({'type': 'user_message', 'message_id': user_message_id})}\n\n"

        hist = chat_history if chat_history is not None else _plain_chat_history(
            save_db, chat_id, exclude_message_id=user_message_id
        )
        try:
            yield f"data: {json.dumps({'type': 'status', 'stage': 'generating', 'message': 'Generating response...'})}\n\n"
            route = _sprint_route(query, hist, attachments, memory)
            if route in ("sprint", "conversational"):
                chunks = llm_service.stream_sprint_reply(
                    query, chat_history=hist, attachments=attachments,
                    summary=memory.get("summary"), recalled_messages=memory.get("recalled"),
                ) if route == "sprint" else llm_service.stream_emotional_casual_reply(
                    query, chat_history=hist, system_prompt=SPRINT_CASUAL_SYSTEM_PROMPT
                )
                reported_tokens = 0
                for chunk in token_meter.metered(chunks, meter):
                    if meter.used_tokens != reported_tokens:
                        reported_tokens = meter.used_tokens
                        yield _usage_event(reported_tokens)
                    accumulated_text += chunk
                    visible = marker_stripper.feed(chunk) if marker_stripper is not None else chunk
                    if visible:
                        yield f"data: {json.dumps({'type': 'token', 'content': visible})}\n\n"
                answer = strip_markers(accumulated_text).strip()
                source_type = "unavailable" if answer == UNAVAILABLE_RESPONSE else route
                verification_status = "unavailable" if source_type == "unavailable" else "unverified"
            else:
                # A memory lookup answered from the database, or the SAP-scope refusal.
                answer = memory["answer"] if route == "conversation_memory" else NON_SAP_REFUSAL_RESPONSE
                source_type = route
                verification_status = "unverified"
                accumulated_text = answer
                visible = marker_stripper.feed(answer) if marker_stripper is not None else answer
                if visible:
                    yield f"data: {json.dumps({'type': 'token', 'content': visible})}\n\n"

            if marker_stripper is not None:
                leftover = marker_stripper.flush()
                if leftover:
                    yield f"data: {json.dumps({'type': 'token', 'content': leftover})}\n\n"

            assistant_msg = Message(
                chat_id=chat_id,
                role="assistant",
                content=answer,
                source_type=source_type,
                grounding_score=None,
                embedding=None,
            )
            save_db.add(assistant_msg)
            save_db.commit()
            save_db.refresh(assistant_msg, attribute_names=["id", "created_at"])

            try:
                conversation_memory_service.update_rolling_summary(save_db, chat_id, query, answer)
            except Exception as sum_err:
                logger.warning("Failed to update rolling summary for chat %s (%s)", chat_id, type(sum_err).__name__)

            done_payload = True
            event = {
                "type": "done",
                "answer": answer,
                "message_id": assistant_msg.id,
                "source_type": source_type,
                "grounding_score": None,
                "citations": [],
                "web_sources": [],
                "images": [],
                "verification_status": verification_status,
                "is_in_rag_pipeline": False,
                "external_search_used": False,
                "follow_up_questions": [],
                "token_usage": meter.summary(
                    question=query, answer=answer,
                    conversation_chars=_history_chars(hist) if conversation_chars is None else conversation_chars,
                ),
            }
            if not current_user.is_admin:
                event = public_done_event(event)
            yield f"data: {json.dumps(event)}\n\n"
        except Exception as exc:
            logger.error("Sprint streaming generation failed (%s)", type(exc).__name__, exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': 'Generation interrupted. Please try again.'})}\n\n"
        finally:
            if not done_payload and accumulated_text.strip():
                logger.info("Sprint stream for chat %s ended before completion; partial text was not persisted", chat_id)
            save_db.close()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
