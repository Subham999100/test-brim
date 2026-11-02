"""Organisation Portal tables (docs/ORGANISATION_PORTAL.md, Alembic revision 0006_organisations).

Every row that belongs to an organisation carries organization_id, and every query in the
organisation APIs filters on the caller's organisation, never on an ID taken from the request.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, UniqueConstraint

from backend.app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


ORG_STATUS_REQUESTED = "requested"
ORG_STATUS_PENDING = "pending_activation"
ORG_STATUS_ACTIVE = "active"
ORG_STATUS_SUSPENDED = "suspended"
ORG_STATUS_DEACTIVATED = "deactivated"
ORG_STATUS_REJECTED = "rejected"
ORG_STATUSES = (ORG_STATUS_REQUESTED, ORG_STATUS_PENDING, ORG_STATUS_ACTIVE, ORG_STATUS_SUSPENDED,
                ORG_STATUS_DEACTIVATED, ORG_STATUS_REJECTED)

ORG_ROLE_OWNER = "owner"
ORG_ROLE_ADMIN = "admin"
ORG_ROLE_MEMBER = "member"
ORG_MANAGER_ROLES = (ORG_ROLE_OWNER, ORG_ROLE_ADMIN)

ACCOUNT_INDIVIDUAL = "individual"
ACCOUNT_ORGANISATION = "organisation"


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=_uuid)
    # Unique; names are also compared case-insensitively in code and by ux_organizations_name_lower.
    name = Column(String(120), unique=True, nullable=False)
    slug = Column(String(140), unique=True, nullable=False)
    contact_name = Column(String(120), nullable=True)
    contact_email = Column(String(255), nullable=False)
    request_message = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default=ORG_STATUS_REQUESTED)
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    activated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_now, nullable=False)
    updated_at = Column(DateTime, default=_now, onupdate=_now, nullable=False)


class OrgActivationCode(Base):
    """A Super-Admin-issued activation code. Only the SHA-256 of the normalised code is stored."""

    __tablename__ = "org_activation_codes"

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    code_hash = Column(String(64), unique=True, nullable=False)
    code_hint = Column(String(8), nullable=False)  # last 4 characters, for the dashboard
    admin_name = Column(String(120), nullable=False)
    admin_email = Column(String(255), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    used_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=_now, nullable=False)


class OrgSharedAnswer(Base):
    """An assistant answer a member shared to the organisation's knowledge hub (snapshot of the text)."""

    __tablename__ = "org_shared_answers"
    __table_args__ = (UniqueConstraint("organization_id", "message_id", name="uq_org_shared_answers_org_message"),)

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id = Column(String(36), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)  # evidence markers stripped
    category = Column(String(64), nullable=False)
    shared_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    shared_by_name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=_now, nullable=False)
    updated_at = Column(DateTime, default=_now, onupdate=_now, nullable=False)


class OrgAnswerLike(Base):
    __tablename__ = "org_answer_likes"
    __table_args__ = (UniqueConstraint("shared_answer_id", "user_id", name="uq_org_answer_likes_answer_user"),)

    id = Column(String(36), primary_key=True, default=_uuid)
    shared_answer_id = Column(String(36), ForeignKey("org_shared_answers.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=_now, nullable=False)


class OrgAnswerComment(Base):
    __tablename__ = "org_answer_comments"

    id = Column(String(36), primary_key=True, default=_uuid)
    shared_answer_id = Column(String(36), ForeignKey("org_shared_answers.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    author_name = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=_now, nullable=False)
