"""Shared Organisation Portal operations used by the organisation and Super Admin APIs
(docs/ORGANISATION_PORTAL.md). Plaintext activation codes leave this module only as a return value."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models.organization import OrgActivationCode, Organization
from backend.app.models.user import User
from backend.app.services.org_credentials import (
    activation_code_hint,
    generate_activation_code,
    hash_activation_code,
    slugify,
)


def utcnow() -> datetime:
    """Naive UTC, the convention of every TIMESTAMP column in this schema."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso(value: Optional[datetime]) -> Optional[str]:
    """ISO-8601 with an explicit UTC offset."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def find_organisation_by_name(db: Session, name: str, exclude_id: Optional[str] = None) -> Optional[Organization]:
    query = db.query(Organization).filter(func.lower(Organization.name) == name.strip().lower())
    if exclude_id:
        query = query.filter(Organization.id != exclude_id)
    return query.first()


def unique_slug(db: Session, name: str) -> str:
    base = slugify(name)
    slug = base
    while db.query(Organization.id).filter(Organization.slug == slug).first() is not None:
        slug = f"{base[:131]}-{secrets.token_hex(4)}"
    return slug


def email_in_use(db: Session, email: str) -> bool:
    return db.query(User.id).filter(User.email == email.strip().lower()).first() is not None


def member_count(db: Session, organization_id: str) -> int:
    return db.query(func.count(User.id)).filter(User.organization_id == organization_id).scalar() or 0


def member_counts(db: Session, organization_ids: Iterable[str]) -> dict:
    ids = list(organization_ids)
    if not ids:
        return {}
    rows = (db.query(User.organization_id, func.count(User.id))
            .filter(User.organization_id.in_(ids)).group_by(User.organization_id).all())
    return dict(rows)


def active_code(db: Session, organization_id: str) -> Optional[OrgActivationCode]:
    """The newest code that is unused, unrevoked and unexpired."""
    return (db.query(OrgActivationCode)
            .filter(OrgActivationCode.organization_id == organization_id,
                    OrgActivationCode.used_at.is_(None),
                    OrgActivationCode.revoked_at.is_(None),
                    OrgActivationCode.expires_at > utcnow())
            .order_by(OrgActivationCode.created_at.desc())
            .first())


def latest_code(db: Session, organization_id: str) -> Optional[OrgActivationCode]:
    return (db.query(OrgActivationCode)
            .filter(OrgActivationCode.organization_id == organization_id)
            .order_by(OrgActivationCode.created_at.desc())
            .first())


def revoke_unused_codes(db: Session, organization_id: str) -> int:
    now = utcnow()
    return (db.query(OrgActivationCode)
            .filter(OrgActivationCode.organization_id == organization_id,
                    OrgActivationCode.used_at.is_(None),
                    OrgActivationCode.revoked_at.is_(None))
            .update({OrgActivationCode.revoked_at: now}, synchronize_session=False))


def issue_activation_code(
    db: Session, organization: Organization, admin_name: str, admin_email: str, issued_by: Optional[str]
) -> Tuple[str, OrgActivationCode]:
    """Revoke the organisation's unused codes and add a new one (not committed). Returns the plaintext,
    which the caller shows once and never stores or logs."""
    revoke_unused_codes(db, organization.id)
    plaintext = generate_activation_code()
    code = OrgActivationCode(
        organization_id=organization.id,
        code_hash=hash_activation_code(plaintext),
        code_hint=activation_code_hint(plaintext),
        admin_name=admin_name.strip(),
        admin_email=admin_email.strip().lower(),
        expires_at=utcnow() + timedelta(hours=settings.ORG_ACTIVATION_CODE_TTL_HOURS),
        created_by=issued_by,
        created_at=utcnow(),
    )
    db.add(code)
    return plaintext, code


def revoke_member_sessions(db: Session, organization_id: str) -> int:
    """Invalidate every token held by the organisation's members (token_version + 1)."""
    return (db.query(User)
            .filter(User.organization_id == organization_id)
            .update({User.token_version: User.token_version + 1}, synchronize_session=False))
