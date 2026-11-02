import asyncio
import json
from datetime import datetime, timezone
from types import SimpleNamespace

from backend.app.api import messages as messages_api
from backend.app.schemas.message import MessageCreate


class FakeSession:
    def __init__(self):
        self.added = []
        self.closed = False

    def add(self, row):
        self.added.append(row)

    def commit(self):
        pass

    def refresh(self, row, attribute_names=None):
        row.id = "sprint-answer-id"
        row.created_at = datetime.now(timezone.utc)

    def close(self):
        self.closed = True


def _sse_events(response):
    async def collect():
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk.decode() if isinstance(chunk, bytes) else chunk)
        return chunks

    text = asyncio.run(collect())
    return [json.loads(line[6:]) for line in "".join(text).splitlines() if line.startswith("data: ")]


def test_message_mode_defaults_to_scholar_for_legacy_api_callers():
    assert MessageCreate(content="What is SAP BRIM?").mode == "scholar"
    assert MessageCreate(content="What is SAP BRIM?", mode="sprint").mode == "sprint"


def test_sprint_stream_uses_direct_llm_without_rag_or_embeddings(monkeypatch):
    session = FakeSession()
    monkeypatch.setattr(messages_api, "SessionLocal", lambda: session)
    monkeypatch.setattr(messages_api, "issue_stream_token", lambda *_args: "signed-stream")
    monkeypatch.setattr(
        messages_api.llm_service,
        "stream_sprint_reply",
        lambda *_args, **_kwargs: iter(["## SAP answer\n\n", "- Direct response\n"]),
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Sprint must bypass retrieval and embedding services")

    monkeypatch.setattr(messages_api.rag_service, "stream_query", forbidden)
    monkeypatch.setattr(messages_api.retrieval_service, "retrieve", forbidden)
    monkeypatch.setattr(messages_api.conversation_memory_service, "embed_message_content", forbidden)

    response = messages_api.handle_sprint_streaming_response(
        "chat-id",
        "Explain SAP BRIM",
        chat_history=[],
        current_user=SimpleNamespace(id="user-id", is_admin=True),
        attachments=[],
        user_message_id="user-message-id",
    )
    events = _sse_events(response)

    assert "".join(event.get("content", "") for event in events if event["type"] == "token") == (
        "## SAP answer\n\n- Direct response\n"
    )
    done = next(event for event in events if event["type"] == "done")
    assert done["source_type"] == "sprint"
    assert done["is_in_rag_pipeline"] is False
    assert done["citations"] == []
    assert session.added[0].embedding is None
    assert session.added[0].content == "## SAP answer\n\n- Direct response"
    assert session.closed


def test_sprint_refuses_non_sap_questions_without_calling_llm(monkeypatch):
    monkeypatch.setattr(
        messages_api.llm_service,
        "generate_sprint_reply",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("LLM must not answer non-SAP topics")),
    )

    result = messages_api._sprint_result("What is the weather today?", [], [])

    assert result["source_type"] == "refusal"
    assert "only assist with SAP" in result["answer"]
