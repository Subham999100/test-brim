"""Builders for Organisation Portal tests. Rows go into the *_test database (see conftest.py) and are
removed by OrgFixtures.cleanup()."""

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from backend.app.database import SessionLocal
from backend.app.models.chat import Chat
from backend.app.models.message import Message
from backend.app.models.organization import Organization
from backend.app.models.user import User
from backend.app.security.auth import create_access_token, hash_password

PASSWORD = "Correct-Horse-Battery-9"
_PASSWORD_HASH = None


def _password_hash():
    global _PASSWORD_HASH
    if _PASSWORD_HASH is None:
        _PASSWORD_HASH = hash_password(PASSWORD)
    return _PASSWORD_HASH


def unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def headers_for(user_id: str) -> dict:
    with SessionLocal() as db:
        user = db.get(User, user_id)
        return {"Authorization": f"Bearer {create_access_token({'sub': user.id, 'ver': user.token_version})}"}


class OrgFixtures:
    def __init__(self):
        self.user_ids = []
        self.org_ids = []

    def user(self, *, org=None, role=None, is_admin=False, is_active=True, must_change_password=False,
             name=None, email=None) -> User:
        with SessionLocal() as db:
            user = User(
                email=email or f"{unique('org-test')}@example.com",
                name=name or unique("Person"),
                password_hash=_password_hash(),
                is_admin=is_admin,
                role="admin" if is_admin else "consultant",
                account_type="organisation" if org is not None else "individual",
                organization_id=org.id if org is not None else None,
                org_role=role if org is not None else None,
                is_active=is_active,
                must_change_password=must_change_password,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            db.expunge(user)
        self.user_ids.append(user.id)
        return user

    def track_user(self, user_id: str):
        self.user_ids.append(user_id)

    def organisation(self, status="active", name=None) -> Organization:
        now = datetime.now(timezone.utc)
        with SessionLocal() as db:
            org_name = name or unique("Org")
            org = Organization(name=org_name, slug=org_name.lower(), contact_email="contact@example.com",
                               contact_name="Contact", status=status,
                               activated_at=now if status in ("active", "suspended", "deactivated") else None)
            db.add(org)
            db.commit()
            db.refresh(org)
            db.expunge(org)
        self.org_ids.append(org.id)
        return org

    def track_org(self, org_id: str):
        self.org_ids.append(org_id)

    def liked_answer(self, user: User, question="How do I configure rating in Convergent Charging?",
                     answer="Use the charge plan in SAP Convergent Charging [E1].", feedback="up") -> str:
        """A chat with one question and one assistant answer; returns the answer's message id."""
        now = datetime.now(timezone.utc)
        with SessionLocal() as db:
            chat = Chat(user_id=user.id, title="Org test chat")
            db.add(chat)
            db.flush()
            db.add(Message(chat_id=chat.id, role="user", content=question, created_at=now - timedelta(seconds=5)))
            answer_message = Message(chat_id=chat.id, role="assistant", content=answer, feedback=feedback,
                                     created_at=now)
            db.add(answer_message)
            db.commit()
            return answer_message.id

    def cleanup(self):
        with SessionLocal() as db:
            if self.user_ids:
                db.query(User).filter(User.id.in_(self.user_ids)).delete(synchronize_session=False)
            if self.org_ids:
                db.query(User).filter(User.organization_id.in_(self.org_ids)).delete(synchronize_session=False)
                db.query(Organization).filter(Organization.id.in_(self.org_ids)).delete(synchronize_session=False)
            db.commit()


def random_password() -> str:
    return "Pw-" + secrets.token_urlsafe(18)
