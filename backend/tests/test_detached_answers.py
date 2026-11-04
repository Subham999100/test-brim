"""An answer keeps generating and is saved when the browser disconnects (new chat, another chat, a reload, a
closed tab); only Stop cancels it (owner request 2026-11-04)."""

import asyncio
import threading
import time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.app.api import messages as messages_api
from backend.app.database import SessionLocal
from backend.app.main import app
from backend.app.models.chat import Chat
from backend.app.models.message import Message
from backend.app.security.stream_tokens import issue_stream_token
from backend.app.services.conversation_memory_service import conversation_memory_service
from backend.app.services.detached_stream import detached, stream_cancellations
from backend.tests.org_helpers import OrgFixtures, headers_for
from backend.tests.test_chat_modes import FakeSession
from backend.tests.test_token_savings import _fake_sprint_stream

client = TestClient(app)


def _wait_for(condition, seconds=5.0):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.02)
    return condition()


@pytest.fixture(autouse=True)
def _fresh_cancellations():
    stream_cancellations.clear()
    yield
    stream_cancellations.clear()


# ---------------------------------------------------------------- the runner

def _producer(log, release=None, count=3):
    try:
        for index in range(count):
            if release is not None and index == 1:
                release.wait(2)
            yield f"event-{index}"
        log.append("saved")  # where the real streams persist the answer
    finally:
        log.append("closed")


def test_the_producer_finishes_after_the_reader_goes_away():
    log, release = [], threading.Event()
    stream = detached(_producer(log, release))
    assert next(stream) == "event-0"
    stream.close()  # the browser disconnected
    release.set()
    assert _wait_for(lambda: "closed" in log)
    assert log == ["saved", "closed"]


def test_a_reader_still_gets_every_event_in_order():
    log = []
    assert list(detached(_producer(log))) == ["event-0", "event-1", "event-2"]
    assert log == ["saved", "closed"]


def test_stop_cancels_the_producer_before_it_saves():
    log, release = [], threading.Event()
    stream = detached(_producer(log, release), stream_id="stream-token-1")
    assert next(stream) == "event-0"
    stream_cancellations.cancel("stream-token-1")
    release.set()
    assert _wait_for(lambda: "closed" in log)
    assert log == ["closed"], "a stopped answer is not saved as a finished one"
    assert stream_cancellations.is_cancelled("stream-token-1")
    assert not stream_cancellations.is_cancelled("another-stream")


# ---------------------------------------------------------------- the real answer streams

def test_a_sprint_answer_is_saved_when_the_browser_disconnects_after_the_first_event(monkeypatch):
    session = FakeSession()
    monkeypatch.setattr(messages_api, "SessionLocal", lambda: session)
    monkeypatch.setattr(messages_api, "issue_stream_token", lambda *_args: "signed-stream")
    monkeypatch.setattr(messages_api.llm_service, "stream_sprint_reply", _fake_sprint_stream)
    monkeypatch.setattr(conversation_memory_service, "update_rolling_summary", lambda *_a, **_k: None)
    response = messages_api.handle_sprint_streaming_response(
        "chat-id", "Explain SAP BRIM", chat_history=[], current_user=SimpleNamespace(id="u", is_admin=False),
        attachments=[], user_message_id="user-message-id", conversation_chars=0,
    )

    async def read_one_event_then_disconnect():
        iterator = response.body_iterator
        first = await iterator.__anext__()
        await iterator.aclose()
        return first

    first = asyncio.run(read_one_event_then_disconnect())
    assert "signed-stream" in (first.decode() if isinstance(first, bytes) else first)
    saved = lambda: [row for row in session.added if isinstance(row, Message) and row.role == "assistant"]
    assert _wait_for(lambda: bool(saved())), "the answer kept generating and was saved"
    assert "SAP answer" in saved()[0].content
    assert _wait_for(lambda: session.closed)


def test_save_partial_cancels_the_running_stream():
    fx = OrgFixtures()
    try:
        user = fx.user()
        with SessionLocal() as db:
            chat = Chat(user_id=user.id, title="Stopped answer")
            db.add(chat)
            db.commit()
            chat_id = chat.id
        token = issue_stream_token(user.id, chat_id)
        saved = client.post(f"/api/chats/{chat_id}/messages/save-partial", headers=headers_for(user.id),
                            json={"content": "Partial text the user saw", "stream_id": token})
        assert saved.status_code == 200, saved.text
        assert stream_cancellations.is_cancelled(token)
    finally:
        fx.cleanup()
