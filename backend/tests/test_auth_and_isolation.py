import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_user_registration_and_login():
    email = "user_test_1@sap.enterprise.com"
    password = "SecretPassword123!"

    # 1. Register
    reg_resp = client.post("/api/auth/register", json={
        "email": email,
        "name": "SAP Consultant One",
        "password": password
    })
    # Either 201 or 400 (if already registered)
    assert reg_resp.status_code in (201, 400)

    # 2. Login
    login_resp = client.post("/api/auth/login", json={
        "email": email,
        "password": password
    })
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == email


def test_sign_up_creates_the_account_but_only_login_starts_a_session():
    import uuid
    email = f"signup_{uuid.uuid4().hex[:10]}@example.com"
    password = "abcd1234"

    try:
        reg_resp = client.post("/api/auth/register", json={"email": email, "name": "New Person", "password": password})
        assert reg_resp.status_code == 201
        assert "access_token" not in reg_resp.json()
        assert reg_resp.json()["email"] == email

        login_resp = client.post("/api/auth/login", json={"email": email, "password": password})
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200 and me.json()["email"] == email
    finally:
        from backend.app.database import SessionLocal
        from backend.app.models.user import User
        db = SessionLocal()
        try:
            db.query(User).filter(User.email == email).delete()
            db.commit()
        finally:
            db.close()


def test_multi_user_chat_isolation():
    """
    CRITICAL SECURITY TEST:
    User A creates a chat.
    User B must NEVER be able to see or access User A's chat (must return 404/403).
    """
    # Create User A
    user_a_email = "user_a_secure@sap.com"
    client.post("/api/auth/register", json={"email": user_a_email, "name": "User Alpha", "password": "Password123!"})
    login_a = client.post("/api/auth/login", json={"email": user_a_email, "password": "Password123!"}).json()
    token_a = login_a["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Create User B
    user_b_email = "user_b_secure@sap.com"
    client.post("/api/auth/register", json={"email": user_b_email, "name": "User Beta", "password": "Password123!"})
    login_b = client.post("/api/auth/login", json={"email": user_b_email, "password": "Password123!"}).json()
    token_b = login_b["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A creates a chat
    create_chat_resp = client.post(
        "/api/chats",
        json={"title": "User A Private Confidential MM Question"},
        headers=headers_a
    )
    assert create_chat_resp.status_code == 201
    chat_a_id = create_chat_resp.json()["id"]

    # User A can access their chat
    get_chat_a = client.get(f"/api/chats/{chat_a_id}", headers=headers_a)
    assert get_chat_a.status_code == 200
    assert get_chat_a.json()["id"] == chat_a_id

    # User B lists chats -> Must NOT include User A's chat
    list_b = client.get("/api/chats", headers=headers_b)
    assert list_b.status_code == 200
    chat_ids_b = [c["id"] for c in list_b.json()]
    assert chat_a_id not in chat_ids_b

    # User B attempts to access User A's chat directly by ID -> Must receive 404 Not Found (no leak)
    unauth_access = client.get(f"/api/chats/{chat_a_id}", headers=headers_b)
    assert unauth_access.status_code == 404

    # User B attempts to delete User A's chat -> Must receive 404 Not Found
    unauth_delete = client.delete(f"/api/chats/{chat_a_id}", headers=headers_b)
    assert unauth_delete.status_code == 404
