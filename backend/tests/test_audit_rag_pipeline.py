"""Audit regressions for the RAG orchestrator (AUDIT_REPORT.md F-02, F-03, F-04, F-27). Offline only."""

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.app.api import messages as messages_api
from backend.app.services.rag_service import rag_service
from backend.tests.offline_rag import DEFAULT_ANSWER, RAG_QUESTION, offline_rag

# Draft with a fabricated procedure; the repair returns the supported answer instead.
UNVERIFIED_DRAFT = (
    "Run transaction ZQQ_FAKE_UNBLOCK and update table ZFAKE_POSTING directly to change the posting area [E1]. "
    "Convergent Invoicing transfers invoicing documents to FI-CA [E1]."
)


def _stream_events(**offline_kwargs):
    with offline_rag(**offline_kwargs):
        return list(rag_service.stream_query(db=MagicMock(), query=RAG_QUESTION))


def test_f02_process_query_completes_retrieval_backed_answer():
    """process_query used undefined names in its diagnostics and raised NameError after generation."""
    with offline_rag() as calls:
        result = rag_service.process_query(db=MagicMock(), query=RAG_QUESTION)

    assert calls["retrieve"] >= 1, "question must go through retrieval"
    assert "posting area" in result["answer"].lower()
    assert result["citations"], "knowledge-base citations are built"
    diagnostics = result["diagnostics"]
    assert diagnostics["retrieved_chunks_count"] == 2
    assert diagnostics["final_context_chunks_count"] >= 1
    assert isinstance(diagnostics["post_processing_modified"], bool)


def test_f03_stream_never_emits_text_before_verification():
    events = _stream_events(answer=UNVERIFIED_DRAFT, repair=DEFAULT_ANSWER)
    types = [e["type"] for e in events]
    stages = [e.get("stage") for e in events]
    verifying_at = stages.index("verifying_claims")
    first_token_at = types.index("token")
    assert first_token_at > verifying_at, "draft tokens were streamed before claim verification"

    done = events[-1]
    streamed = "".join(e["content"] for e in events if e["type"] == "token")
    assert done["type"] == "done"
    assert streamed == done["answer"], "client must receive exactly the verified answer"
    assert "ZQQ_FAKE_UNBLOCK" not in streamed and "ZFAKE_POSTING" not in streamed


def test_f03_stream_text_matches_verified_answer_without_repair():
    events = _stream_events()
    streamed = "".join(e["content"] for e in events if e["type"] == "token")
    assert streamed == events[-1]["answer"]


def _run_stream(response):
    async def collect():
        return [chunk async for chunk in response.body_iterator]
    return asyncio.run(collect())


def test_f03_interrupted_stream_does_not_persist_unverified_text():
    def broken_stream(*args, **kwargs):
        yield {"type": "token", "content": "Unverified partial text that never reached done"}
        raise RuntimeError("provider disconnected")

    save_db = MagicMock()
    user = SimpleNamespace(id="u1", is_admin=False)
    with patch.object(messages_api, "SessionLocal", return_value=save_db), \
            patch.object(messages_api.rag_service, "stream_query", side_effect=broken_stream):
        response = messages_api.handle_streaming_response(
            "chat-1", "question", chat_history=[], current_user=user, attachments=None, user_message_id="m1"
        )
        body = "".join(c if isinstance(c, str) else c.decode() for c in _run_stream(response))

    assert '"type": "error"' in body
    save_db.add.assert_not_called()
    save_db.commit.assert_not_called()
    save_db.close.assert_called_once()
