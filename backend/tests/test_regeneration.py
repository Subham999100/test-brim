"""Regenerate: a repeated question is answered by another provider/model, the count is stored with the answer,
and the provider/model recorded are the ones that actually answered. Regressions from merging the multi-LLM
regeneration feature (2026-11-03 review)."""

import contextvars
import importlib
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import inspect

from backend.app.api import messages as messages_api
from backend.app.config import settings
from backend.app.database import SessionLocal, engine, run_migrations
from backend.app.main import app
from backend.app.models.message import Message
from backend.app.services.llm_service import LLMService
from backend.app.services.public_payload import public_done_event
from backend.tests.test_chat_modes import FakeSession, _sse_events

# The services package re-exports the llm_service instance under the module's name.
llm_module = importlib.import_module("backend.app.services.llm_service")
client = TestClient(app)


def _service(monkeypatch, allowed="groq,gemini", preferred="groq") -> LLMService:
    monkeypatch.setattr(settings, "LLM_ALLOWED_PROVIDERS", allowed)
    monkeypatch.setattr(settings, "LLM_PROVIDER", preferred)
    monkeypatch.setattr(settings, "LLM_ALLOW_FREE_TIER", False)
    return LLMService()


# ---------------------------------------------------------------- provider and model rotation

def test_provider_call_rotates_models_on_regeneration(monkeypatch):
    service = _service(monkeypatch)
    service.groq_api_key = "test-key"
    service.GROQ_MODELS = ["groq-a", "groq-b"]
    tried = []

    class FakeGroq:
        def __init__(self, **_kwargs):
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

        @staticmethod
        def create(**kwargs):
            tried.append(kwargs["model"])
            choice = SimpleNamespace(message=SimpleNamespace(content="answer"), finish_reason="stop")
            return SimpleNamespace(choices=[choice], usage=None)

    monkeypatch.setattr("groq.Groq", FakeGroq)
    monkeypatch.setattr(service, "_prepare_external_prompts", lambda _p, _m, prompt, system: (prompt, system))

    # Used to raise NameError: the provider calls referenced an undefined `regeneration_index`.
    assert service._call_groq("prompt", "system") == "answer"
    assert service._call_groq("prompt", "system", regeneration_index=1) == "answer"
    assert tried == ["groq-a", "groq-b"]


def test_regeneration_tries_another_provider_first(monkeypatch):
    service = _service(monkeypatch)
    service.groq_api_key = service.gemini_api_key = "test-key"
    calls = []

    def provider(name):
        def call(prompt, system_prompt, result=None, regeneration_index=None):
            calls.append((name, regeneration_index))
            return f"{name} answer"
        return call

    monkeypatch.setattr(service, "_call_groq", provider("groq"))
    monkeypatch.setattr(service, "_call_gemini", provider("gemini"))

    assert service.generate_completion("question", "system") == "groq answer"
    assert service.generate_completion("question", "system", regeneration_index=1) == "gemini answer"
    assert calls == [("groq", None), ("gemini", 1)]


def test_regeneration_order_never_adds_a_disallowed_or_local_provider(monkeypatch):
    service = _service(monkeypatch, allowed="groq,gemini", preferred="local")
    for index in (1, 2, 3):
        assert sorted(service._provider_order(regeneration_index=index)) == ["gemini", "groq"]

    service = _service(monkeypatch, allowed="groq,gemini", preferred="openrouter")
    assert "openrouter" not in service._provider_order(regeneration_index=1)

    service = _service(monkeypatch, allowed="groq,gemini", preferred="groq")
    assert service._provider_order(regeneration_index=1) == ["gemini", "groq"]


def test_stream_keeps_regeneration_and_answering_model_across_worker_contexts():
    """Starlette runs each step of a streaming response in a fresh copy of the request context."""
    seen = []

    def steps():
        seen.append(llm_module.get_regeneration_index())
        yield "token"
        seen.append(llm_module.get_regeneration_index())
        llm_module.set_current_llm_info("gemini", "gemini-test")
        yield "done"

    request_context = contextvars.Context()
    info = {}
    stream = llm_module.with_generation_context(steps(), 2, info)
    while True:
        try:
            request_context.copy().run(next, stream)
        except StopIteration:
            break

    assert seen == [2, 2]
    assert info == {"provider": "gemini", "model": "gemini-test"}
    assert request_context.run(llm_module.get_current_llm_info) == {}, "nothing leaks into the request context"
    # Outside a bound record nothing is stored, so a later request cannot read a stale provider.
    llm_module.set_current_llm_info("groq", "stale")
    assert llm_module.get_current_llm_info() == {}


# ---------------------------------------------------------------- chat API

def _login(email: str) -> dict:
    client.post("/api/auth/register", json={"email": email, "name": "Regenerator", "password": "Password123!"})
    token = client.post("/api/auth/login", json={"email": email, "password": "Password123!"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _events(response) -> list:
    return [json.loads(line[len("data: "):]) for line in response.text.splitlines() if line.startswith("data: ")]


def _stored(chat_id: str):
    db = SessionLocal()
    try:
        return [
            (m.role, m.regeneration_count, m.llm_provider, m.llm_model)
            for m in db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.created_at).all()
        ]
    finally:
        db.close()


def _answering_stream(seen: list):
    """A RAG stream whose provider call reports which model answered, before the verified tokens are sent."""
    def fake_stream(db, query, chat_history=None, user=None, attachments=None, regeneration_index=None):
        seen.append(regeneration_index)
        llm_module.set_current_llm_info("gemini", "gemini-test")
        yield {"type": "token", "content": "Answer"}
        yield {"type": "done", "answer": "Answer", "source_type": "knowledge_base", "grounding_score": 0.9,
               "citations": [], "web_sources": [], "images": [], "repair_count": 1}
    return fake_stream


def test_regenerate_counts_up_and_records_the_model_that_answered():
    headers = _login("regenerate_edit@sap.com")
    chat_id = client.post("/api/chats", json={"title": "Regenerate"}, headers=headers).json()["id"]
    base = datetime.now(timezone.utc)
    db = SessionLocal()
    question = Message(chat_id=chat_id, role="user", content="What is FKKINV?", created_at=base)
    db.add_all([question, Message(chat_id=chat_id, role="assistant", content="First answer",
                                  source_type="knowledge_base", created_at=base + timedelta(seconds=1))])
    db.commit()
    question_id = question.id
    db.close()

    seen = []
    with patch.object(messages_api.rag_service, "stream_query", side_effect=_answering_stream(seen)):
        for _ in range(2):  # the Regenerate button re-sends the same prompt through the edit endpoint
            response = client.post(f"/api/chats/{chat_id}/messages/{question_id}/edit",
                                   json={"content": "What is FKKINV?"}, headers=headers)
            assert response.status_code == 200, response.text

    done = _events(response)[-1]
    assert seen == [1, 2]
    # Recorded from the provider call, not guessed, although Starlette ran each stream step in its own context.
    assert _stored(chat_id) == [("user", 0, None, None), ("assistant", 2, "gemini", "gemini-test")]
    # Regular users see the badge count only: no model names and not the pipeline's repair count.
    assert done["type"] == "done" and done["regeneration_count"] == 2
    assert not {"llm_provider", "llm_model", "repair_count"} & set(done)
    history = client.get(f"/api/chats/{chat_id}/messages", headers=headers).json()
    assert history[-1]["regeneration_count"] == 2
    assert history[-1]["llm_provider"] is None and history[-1]["llm_model"] is None


def test_resending_the_latest_question_counts_regenerations_up():
    headers = _login("regenerate_resend@sap.com")
    chat_id = client.post("/api/chats", json={"title": "Resend"}, headers=headers).json()["id"]

    seen = []
    with patch.object(messages_api.rag_service, "stream_query", side_effect=_answering_stream(seen)):
        for _ in range(3):
            response = client.post(f"/api/chats/{chat_id}/messages/stream",
                                   json={"content": "Explain FPVA", "mode": "scholar"}, headers=headers)
            assert response.status_code == 200, response.text

    assert seen == [0, 1, 2]
    assert [row[1] for row in _stored(chat_id) if row[0] == "assistant"] == [0, 1, 2]


def test_sprint_answers_without_an_llm_record_no_provider(monkeypatch):
    session = FakeSession()
    monkeypatch.setattr(messages_api, "SessionLocal", lambda: session)
    monkeypatch.setattr(messages_api, "issue_stream_token", lambda *_args: "signed-stream")
    monkeypatch.setattr(messages_api.conversation_memory_service, "update_rolling_summary", lambda *_a, **_k: None)

    response = messages_api.handle_sprint_streaming_response(
        "chat-id", "What is the weather today?", chat_history=[],
        current_user=SimpleNamespace(id="user-id", is_admin=True), attachments=[], user_message_id="q",
        memory={}, is_regeneration=True, regeneration_index=1,
    )
    done = _sse_events(response)[-1]

    answer = session.added[-1]
    assert done["source_type"] == "refusal"
    assert (answer.llm_provider, answer.llm_model, answer.regeneration_count) == (None, None, 1)


def test_public_payload_keeps_the_regeneration_badge_only():
    event = public_done_event({"type": "done", "answer": "ok", "regeneration_count": 3, "repair_count": 1,
                               "llm_provider": "groq", "llm_model": "secret-model"})
    assert event["regeneration_count"] == 3
    assert not {"llm_provider", "llm_model", "repair_count"} & set(event)
    assert public_done_event({"type": "done", "answer": "ok"})["regeneration_count"] == 0


def test_migration_0007_adds_the_message_columns_idempotently():
    run_migrations()
    run_migrations()
    columns = {column["name"] for column in inspect(engine).get_columns("messages")}
    assert {"llm_provider", "llm_model", "regeneration_count"} <= columns
