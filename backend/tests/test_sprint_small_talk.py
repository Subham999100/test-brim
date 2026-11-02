"""Sprint small talk: greetings, thanks, feelings and "who are you?" get a short conversational reply
instead of the SAP-only refusal, without retrieval or embeddings. SAP questions keep the Sprint answer
path and non-SAP requests stay refused (offline)."""

from types import SimpleNamespace

import pytest

from backend.app.api import messages as messages_api
from backend.app.services.llm_service import EMOTIONAL_CASUAL_FALLBACKS, EMOTIONAL_CASUAL_SYSTEM_PROMPT, llm_service
from backend.app.services.conversation_memory_service import conversation_memory_service
from backend.app.services.sap_classifier import NON_SAP_REFUSAL_RESPONSE

from backend.tests.test_chat_modes import FakeSession, _sse_events

PRESETS = EMOTIONAL_CASUAL_FALLBACKS
SAP_HISTORY = [
    {"id": "h1", "role": "user", "content": "How does dunning work in SAP FI-CA?"},
    {"id": "h2", "role": "assistant", "content": "Dunning in FI-CA runs per contract account."},
]


def _forbid(*_args, **_kwargs):
    raise AssertionError("must not be called on this path")


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(messages_api.rag_service, "process_query", _forbid)
    monkeypatch.setattr(messages_api.rag_service, "stream_query", _forbid)
    monkeypatch.setattr(messages_api.retrieval_service, "retrieve", _forbid)
    monkeypatch.setattr(conversation_memory_service, "embed_message_content", _forbid)
    monkeypatch.setattr(conversation_memory_service, "update_rolling_summary", lambda *_a, **_k: None)


def _stream(monkeypatch, query):
    session = FakeSession()
    monkeypatch.setattr(messages_api, "SessionLocal", lambda: session)
    monkeypatch.setattr(messages_api, "issue_stream_token", lambda *_args: "signed-stream")
    response = messages_api.handle_sprint_streaming_response(
        "chat-id", query, chat_history=[], current_user=SimpleNamespace(id="user-id", is_admin=True),
        attachments=[], user_message_id="user-message-id",
    )
    events = _sse_events(response)
    return events, next(event for event in events if event["type"] == "done"), session


def test_greeting_gets_a_reply_instead_of_the_sap_refusal(monkeypatch):
    monkeypatch.setattr(messages_api.llm_service, "generate_sprint_reply", _forbid)
    monkeypatch.setattr(messages_api.llm_service, "generate_completion", _forbid)  # preset, no provider call

    result = messages_api._sprint_result("Hi", [], [])

    assert result["source_type"] == "conversational"
    assert result["answer"] == PRESETS["hi"]
    assert result["grounding_score"] is None and result["verification_status"] == "unverified"


def test_feelings_get_an_empathetic_reply(monkeypatch):
    monkeypatch.setattr(messages_api.llm_service, "generate_completion", _forbid)

    result = messages_api._sprint_result("I had a bad day", [], [])

    assert result["source_type"] == "conversational"
    assert result["answer"] == PRESETS["i had a bad day"]


def test_identity_question_is_answered_as_clyptus_sprint(monkeypatch):
    captured = {}

    def completion(prompt, system_prompt):
        captured.update(prompt=prompt, system=system_prompt)
        return "I'm Clyptus.AI Sprint, here to help with SAP questions."

    monkeypatch.setattr(messages_api.llm_service, "generate_completion", completion)
    monkeypatch.setattr(messages_api.llm_service, "generate_sprint_reply", _forbid)

    result = messages_api._sprint_result("What is your name?", [], [])

    assert result["source_type"] == "conversational"
    assert result["answer"] == "I'm Clyptus.AI Sprint, here to help with SAP questions."
    assert "Clyptus.AI Sprint" in captured["system"]
    assert "What is your name?" in captured["prompt"]


def test_small_talk_is_not_mistaken_for_a_memory_question(monkeypatch):
    monkeypatch.setattr(conversation_memory_service, "get_chat_summary", lambda db, chat_id: None)
    monkeypatch.setattr(conversation_memory_service, "search_history", _forbid)
    monkeypatch.setattr(messages_api.llm_service, "generate_completion", _forbid)

    for query in ("hello", "who are you?", "thanks!"):
        memory = messages_api._sprint_memory(None, "chat-1", "user-1", query, [], "current")
        result = messages_api._sprint_result(query, [], [], memory=memory)
        assert (result["source_type"], result["answer"]) == ("conversational", PRESETS[query])


def test_stream_answers_who_are_you_without_the_sap_answer_path(monkeypatch):
    monkeypatch.setattr(messages_api.llm_service, "stream_sprint_reply", _forbid)
    monkeypatch.setattr(messages_api.llm_service, "_stream_configured", _forbid)

    events, done, session = _stream(monkeypatch, "Who are you?")

    expected = PRESETS["who are you?"]
    assert "".join(event.get("content", "") for event in events if event["type"] == "token").strip() == expected
    assert (done["source_type"], done["answer"]) == ("conversational", expected)
    assert done["verification_status"] == "unverified" and done["is_in_rag_pipeline"] is False
    saved = session.added[0]
    assert (saved.content, saved.source_type, saved.embedding) == (expected, "conversational", None)


def test_stream_identity_question_uses_the_sprint_persona(monkeypatch):
    seen = {}

    def stream(prompt, system_prompt):
        seen["system"] = system_prompt
        yield "I'm Clyptus.AI Sprint."

    monkeypatch.setattr(messages_api.llm_service, "_stream_configured", stream)
    monkeypatch.setattr(messages_api.llm_service, "stream_sprint_reply", _forbid)

    _events, done, _session = _stream(monkeypatch, "Introduce yourself")

    assert (done["source_type"], done["answer"]) == ("conversational", "I'm Clyptus.AI Sprint.")
    assert "Clyptus.AI Sprint" in seen["system"]


# Regression guards: the small-talk path must not take over anything Sprint already answers or refuses.

def test_greeting_that_asks_an_sap_question_still_gets_the_sprint_answer(monkeypatch):
    monkeypatch.setattr(messages_api.llm_service, "generate_sprint_reply", lambda query, **_kw: "SAP answer")

    result = messages_api._sprint_result("Hi, how do I set up dunning in SAP FI-CA?", [], [])

    assert (result["source_type"], result["answer"]) == ("sprint", "SAP answer")


def test_acknowledged_sap_follow_up_is_answered_not_treated_as_small_talk(monkeypatch):
    monkeypatch.setattr(messages_api.llm_service, "generate_sprint_reply", lambda query, **_kw: "Dunning levels...")

    result = messages_api._sprint_result("ok, what about dunning levels?", SAP_HISTORY, [])

    assert (result["source_type"], result["answer"]) == ("sprint", "Dunning levels...")


def test_small_talk_with_a_non_sap_attachment_is_still_refused(monkeypatch):
    monkeypatch.setattr(messages_api.llm_service, "generate_completion", _forbid)

    result = messages_api._sprint_result("hi", [], [{"name": "menu.txt", "text": "Pizza and pasta recipes"}])

    assert (result["source_type"], result["answer"]) == ("refusal", NON_SAP_REFUSAL_RESPONSE)


def test_non_sap_requests_are_still_refused(monkeypatch):
    monkeypatch.setattr(messages_api.llm_service, "generate_completion", _forbid)

    for query in ("What is the weather today?", "Write a Python script to sort a list"):
        assert messages_api._sprint_result(query, [], [])["source_type"] == "refusal"


def test_scholar_small_talk_keeps_its_own_prompt(monkeypatch):
    captured = {}

    def completion(prompt, system_prompt):
        captured["system"] = system_prompt
        return "Good evening to you too!"

    monkeypatch.setattr(llm_service, "generate_completion", completion)

    llm_service.generate_emotional_casual_reply("Good evening, friend")

    assert captured["system"] == EMOTIONAL_CASUAL_SYSTEM_PROMPT
