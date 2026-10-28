"""AUDIT_REPORT Phase 2 regressions: authentication and access control. Offline (fake DB session)."""

import uuid
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.main import app
from backend.app.security.auth import hash_password
from backend.app.security.ratelimit import MemoryBackend, rate_limiter

PASSWORD = "correct-horse-battery-1"
PASSWORD_HASH = hash_password(PASSWORD)


class FakeQuery:
    def __init__(self, user):
        self._user = user

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._user


class FakeSession:
    """Just enough of a SQLAlchemy session for the auth endpoints."""

    def __init__(self, users):
        self.users = {u.email: u for u in users}
        self.last_email = None

    def query(self, *args):
        return self

    def filter(self, condition):
        # User.email == "<value>": SQLAlchemy keeps the bound value on the right side.
        self.last_email = getattr(getattr(condition, "right", None), "value", None)
        return self

    def first(self):
        return self.users.get(self.last_email)

    def commit(self):
        pass


def make_user(email, is_admin=False):
    return SimpleNamespace(id=str(uuid.uuid4()), email=email, name="Test User", password_hash=PASSWORD_HASH,
                           is_admin=is_admin, role="admin" if is_admin else "consultant", token_version=0,
                           created_at=__import__("datetime").datetime(2026, 1, 1))


@pytest.fixture
def client():
    session = FakeSession([make_user("alice@example.com"), make_user("bob@example.com"),
                           make_user("admin@example.com", is_admin=True)])
    app.dependency_overrides[get_db] = lambda: session
    with TestClient(app) as test_client:
        yield test_client


def login(client, email, password, **headers):
    return client.post("/api/auth/login", json={"email": email, "password": password}, headers=headers)


# --- F-06: rate limiting and lockout -------------------------------------------------------------

def test_f06_random_authorization_header_does_not_reset_login_limit(client):
    limit = settings.LOGIN_RATE_LIMIT_PER_MINUTE
    statuses = [
        login(client, f"user{i}@example.com", "wrong-password-123", Authorization=f"Bearer random-{uuid.uuid4()}").status_code
        for i in range(limit + 2)
    ]
    assert statuses[:limit] == [401] * limit
    assert statuses[limit:] == [429, 429], statuses


def test_f06_spoofed_forwarded_for_is_ignored_from_untrusted_peer(client):
    limit = settings.LOGIN_RATE_LIMIT_PER_MINUTE
    statuses = [
        login(client, f"user{i}@example.com", "wrong-password-123", **{"X-Forwarded-For": f"203.0.113.{i}"}).status_code
        for i in range(limit + 1)
    ]
    assert statuses[-1] == 429


def test_f06_account_locks_after_repeated_failures_even_with_correct_password(client):
    for _ in range(settings.LOGIN_MAX_FAILURES):
        assert login(client, "alice@example.com", "wrong-password-123").status_code == 401
    assert login(client, "alice@example.com", PASSWORD).status_code == 429
    assert login(client, "bob@example.com", PASSWORD).status_code == 200, "other accounts are unaffected"


def test_f06_admin_login_failures_count_toward_lockout(client):
    for _ in range(settings.LOGIN_MAX_FAILURES):
        resp = client.post("/api/auth/admin-login", json={"email": "admin@example.com", "password": "wrong-password-1"})
        assert resp.status_code == 401
    resp = client.post("/api/auth/admin-login", json={"email": "admin@example.com", "password": PASSWORD})
    assert resp.status_code == 429


def test_f06_successful_login_clears_failure_count(client):
    for _ in range(settings.LOGIN_MAX_FAILURES - 1):
        login(client, "alice@example.com", "wrong-password-123")
    assert login(client, "alice@example.com", PASSWORD).status_code == 200
    for _ in range(settings.LOGIN_MAX_FAILURES - 1):
        login(client, "alice@example.com", "wrong-password-123")
    assert login(client, "alice@example.com", PASSWORD).status_code == 200


def test_f06_unknown_accounts_lock_too_so_lockout_does_not_reveal_existence(client):
    for _ in range(settings.LOGIN_MAX_FAILURES):
        assert login(client, "nobody@example.com", "wrong-password-123").status_code == 401
    assert login(client, "nobody@example.com", "wrong-password-123").status_code == 429


def test_f06_memory_backend_caps_keys_and_expires_buckets():
    backend = MemoryBackend(max_keys=3)
    for i in range(10):
        assert backend.hit(f"k{i}", 1, 60)
    assert len(backend) == 3
    assert backend.hit("k9", 1, 60) is False
    with patch("backend.app.security.ratelimit.time.monotonic", return_value=10_000.0):
        assert backend.hit("k9", 1, 60) is True, "the window expired"


def test_f06_rate_limit_can_be_disabled_explicitly():
    with patch.object(settings, "RATE_LIMIT_ENABLED", False):
        assert all(rate_limiter.allow("t", "x", 1) for _ in range(5))
