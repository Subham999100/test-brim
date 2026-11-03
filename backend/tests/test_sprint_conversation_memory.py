"""Sprint conversation memory: exact lookups, summary, keyword recall, all without embeddings (offline)."""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from backend.app.api import messages as messages_api
from backend.app.services import conversation_memory_service as memory_module
from backend.app.services.conversation_memory_service import MemoryIntent, conversation_memory_service
from backend.app.services.llm_service import LLMService

from backend.tests.test_chat_modes import FakeSession, _sse_events

SENT = datetime(2026, 10, 31, 9, 30, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _no_embeddings(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Sprint memory must not use the embedding model")

    monkeypatch.setattr(memory_module.embedding_service, "embed_text", forbidden)
    monkeypatch.setattr(conversation_memory_service, "embed_message_content", forbidden)


def test_first_question_is_answered_from_the_database(monkeypatch):
    seen = {}

    def first(db, chat_id, exclude_message_id=None):
        seen["exclude"] = exclude_message_id
        return {"id": "m1", "content": "How does FI-CA clearing work?", "created_at": SENT}

    monkeypatch.setattr(conversation_memory_service, "get_first_user_message", first)

    memory = messages_api._sprint_memory(None, "chat-1", "user-1", "What was my first question?", [], "current")

    assert memory["intent"] == MemoryIntent.FIRST_MESSAGE_LOOKUP
    assert "How does FI-CA clearing work?" in memory["answer"]
    assert seen["exclude"] == "current"  # the question being asked is not its own answer


def test_history_recall_uses_keyword_search_and_summary(monkeypatch):
    calls = {}

    def search(db, query, **kwargs):
        calls.update(kwargs)
        return [{"message_id": "m9", "chat_id": "chat-1", "chat_title": "Chat", "role": "user",
                 "content": "We use port 5434 for PostgreSQL", "created_at": SENT}]

    monkeypatch.setattr(conversation_memory_service, "search_history", search)
    monkeypatch.setattr(conversation_memory_service, "get_chat_summary", lambda db, chat_id: "User: set up billing")
    history = [{"id": "h1", "role": "user", "content": "hello"}]

    memory = messages_api._sprint_memory(None, "chat-1", "user-1", "What port did I mention earlier?", history, "current")

    assert memory["intent"] == MemoryIntent.HISTORY_RECALL
    assert calls["use_embeddings"] is False
    assert calls["cross_conversation"] is False
    assert set(calls["exclude_message_ids"]) == {"h1", "current"}
    assert memory["summary"] == "User: set up billing" and memory["answer"] is None


def test_cross_conversation_recall_without_matches_returns_fixed_answer(monkeypatch):
    monkeypatch.setattr(conversation_memory_service, "search_history", lambda db, query, **kw: [])
    monkeypatch.setattr(conversation_memory_service, "get_chat_summary", lambda db, chat_id: None)

    memory = messages_api._sprint_memory(None, "chat-1", "user-1", "What did we cover in my other chat?", [], None)

    assert memory["intent"] == MemoryIntent.CROSS_CONVERSATION_RECALL
    assert "could not find" in memory["answer"]


def test_recall_question_is_not_refused_and_gets_memory_context(monkeypatch):
    captured = {}

    def reply(query, **kwargs):
        captured.update(kwargs)
        return "You mentioned port 5434."

    monkeypatch.setattr(messages_api.llm_service, "generate_sprint_reply", reply)
    recalled = [{"content": "port 5434"}]
    memory = {"intent": MemoryIntent.HISTORY_RECALL, "answer": None, "summary": "older turns", "recalled": recalled}

    result = messages_api._sprint_result("What port did I mention earlier?", [], [], memory=memory)

    assert result["source_type"] == "sprint"
    assert captured["summary"] == "older turns" and captured["recalled_messages"] == recalled


def test_sync_refusal_carries_grounding_score_for_persistence():
    result = messages_api._sprint_result("What is the weather today?", [], [])

    assert result["source_type"] == "refusal" and result["grounding_score"] is None


def test_sprint_prompt_includes_summary_and_recalled_messages():
    prompt = LLMService._build_sprint_prompt(
        "What port did I use?", [{"role": "user", "content": "hi"}], [],
        summary="User: configured PostgreSQL",
        recalled_messages=[{"role": "user", "content": "port 5434", "created_at": SENT, "message_id": "m9"}],
    )

    assert "configured PostgreSQL" in prompt and "port 5434" in prompt
    assert prompt.index("Summary of older messages") < prompt.index("Current SAP question")


def test_search_history_lexical_mode_skips_embedding_model():
    rows = [
        (SimpleNamespace(id="m1", chat_id="c1", role="user", content="PostgreSQL runs on port 5434",
                         created_at=SENT, embedding=None, embedding_model=None, embedding_version=None), "Chat"),
        (SimpleNamespace(id="m2", chat_id="c1", role="user", content="Billing run failed",
                         created_at=SENT, embedding=None, embedding_model=None, embedding_version=None), "Chat"),
    ]

    class Query:
        def join(self, *_a, **_k):
            return self

        filter = join
        order_by = join

        def all(self):
            return rows

    db = SimpleNamespace(query=lambda *_a: Query())

    found = conversation_memory_service.search_history(
        db, "which port 5434", user_id="u1", current_chat_id="c1", use_embeddings=False
    )

    assert [r["message_id"] for r in found] == ["m1"]


def test_stream_returns_memory_answer_without_llm_and_updates_summary(monkeypatch):
    session = FakeSession()
    summaries = []
    monkeypatch.setattr(messages_api, "SessionLocal", lambda: session)
    monkeypatch.setattr(messages_api, "issue_stream_token", lambda *_args: "signed-stream")
    monkeypatch.setattr(
        messages_api.llm_service, "stream_sprint_reply",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("memory lookups must not call the LLM")),
    )
    monkeypatch.setattr(
        conversation_memory_service, "update_rolling_summary",
        lambda db, chat_id, user_msg, answer: summaries.append((chat_id, answer)),
    )
    answer = 'Your first question in this chat was:\n\n> "How does FI-CA clearing work?"'

    response = messages_api.handle_sprint_streaming_response(
        "chat-id", "What was my first question?", chat_history=[],
        current_user=SimpleNamespace(id="user-id", is_admin=True), attachments=[],
        user_message_id="user-message-id",
        memory={"intent": MemoryIntent.FIRST_MESSAGE_LOOKUP, "answer": answer},
    )
    events = _sse_events(response)

    done = next(event for event in events if event["type"] == "done")
    assert done["source_type"] == "conversation_memory"
    assert done["answer"] == answer
    assert session.added[0].embedding is None
    assert summaries == [("chat-id", answer)]


def _long_history(messages):
    return [
        {"id": f"m{i}", "role": "user" if i % 2 == 0 else "assistant",
         "content": f"MSG{i:02d}-START " + "detail " * 400 + f"MSG{i:02d}-END"}
        for i in range(messages)
    ]


def test_sprint_prompt_sends_last_six_messages_verbatim_and_older_ones_as_excerpts():
    history = _long_history(10)
    prompt = LLMService._build_sprint_prompt("And the next step?", history, [], summary="User: configured PostgreSQL")

    for item in history[-6:]:
        assert item["content"] in prompt, "recent messages are sent word for word"
    for item in history[:4]:
        assert item["content"] not in prompt, "older messages are not sent in full"
        number = item["content"][:5]
        assert f"{number}-START" in prompt and f"{number}-END" in prompt, "their start and end stay as an excerpt"
    assert "configured PostgreSQL" in prompt
    assert "{'role'" not in prompt, "history is plain text, not a Python list"
    assert prompt.index("Summary of older messages") < prompt.index("MSG04-START") < prompt.index("Current SAP question")


def test_short_sprint_chat_is_sent_in_full():
    history = _long_history(4)
    prompt = LLMService._build_sprint_prompt("And the next step?", history, [])

    assert all(item["content"] in prompt for item in history)
    assert "Summary of older messages" not in prompt


def test_rolling_summary_and_sprint_excerpts_use_the_same_rule():
    entry = conversation_memory_service.summary_entry("assistant", "  word " * 300)
    assert entry.startswith("Assistant: word") and " … " in entry
    assert len(entry) <= len("Assistant: ") + memory_module.SUMMARY_MESSAGE_MAX_CHARS + 3
    assert conversation_memory_service.summary_entry("user", "   ") == ""
