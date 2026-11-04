import logging
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response
from sqlalchemy import func
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.models.chat import Chat
from backend.app.models.message import Message
from backend.app.models.shared_prompt import SharedPrompt
from backend.app.schemas.auth import ChangePasswordRequest, UserRegister, UserLogin, Token, UserResponse
from backend.app.schemas.message import TokenSavingsSummary
from backend.app.security.auth import (
    account_is_usable,
    authenticate_user,
    create_access_token,
    get_current_user,
    get_current_user_allow_password_change,
    hash_password,
    verify_password,
)
from backend.app.security.ratelimit import client_ip, rate_limiter
from backend.app.services import audit_log

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)

TOO_MANY_ATTEMPTS = "Too many login attempts. Try again later."
# Shown only after a correct password (docs/ORGANISATION_PORTAL.md, "Authentication and account state").
ORGANISATION_ACCOUNT_AT_INDIVIDUAL_LOGIN = "This is an organisation account. Sign in through the Organisation Portal."
INDIVIDUAL_ACCOUNT_AT_ORGANISATION_LOGIN = "Sign in with your individual account at /login."
ACCOUNT_NOT_ACTIVE = "This account is not active. Contact your administrator."
CURRENT_PASSWORD_INCORRECT = "The current password is incorrect."
PASSWORD_UNCHANGED = "The new password must be different from the current password."


def _guard_login(request: Request, email: str) -> None:
    """Per-IP login rate and per-account lockout, checked before the password (AUDIT_REPORT F-06)."""
    if not rate_limiter.allow("login-ip", client_ip(request), settings.LOGIN_RATE_LIMIT_PER_MINUTE, 60):
        logger.warning("[AUTH] Login throttled: IP rate limit exceeded for client %s", client_ip(request))
        audit_log.record("login", "denied", request=request, target=email, details={"reason": "ip_rate_limit"})
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=TOO_MANY_ATTEMPTS)
    if rate_limiter.account_locked(email):
        logger.warning("[AUTH] Login throttled: account locked for email %s", email)
        audit_log.record("login", "denied", request=request, target=email, details={"reason": "account_lockout"})
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=TOO_MANY_ATTEMPTS)


def deny_sign_in(request: Request, action: str, user: User, reason: str, detail: str) -> None:
    """The password was correct but this account may not sign in here. Not a failed guess, so the
    lockout counter is cleared rather than increased."""
    rate_limiter.clear_login_failures(user.email)
    logger.warning("security_event login_denied reason=%s", reason)
    audit_log.record(action, "denied", request=request, principal=user, details={"reason": reason})
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def require_usable_account(request: Request, action: str, user: User) -> None:
    if not account_is_usable(user):
        deny_sign_in(request, action, user, "account_not_active", ACCOUNT_NOT_ACTIVE)


def issue_login_token(request: Request, action: str, user: User, db: Session) -> Token:
    """Successful sign-in: clear the lockout counter, record last_login_at, audit and issue a token."""
    rate_limiter.clear_login_failures(user.email)
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()  # expired attributes reload on access below
    audit_log.record(action, request=request, principal=user)
    logger.info("[AUTH] User authenticated successfully: %s (role=%s)", user.email, "admin" if user.is_admin else "user")
    access_token = create_access_token(data={"sub": user.id, "ver": user.token_version})
    return Token(access_token=access_token, token_type="bearer", user=UserResponse.model_validate(user))

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserRegister, request: Request, db: Session = Depends(get_db)):
    # Individuals sign up directly, with no code; organisations use activation codes (AUDIT_REPORT F-01).
    # The only gate is the operator's emergency switch.
    if not settings.REGISTRATION_ENABLED:
        audit_log.record("register", "denied", request=request, details={"reason": "registration_disabled"})
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Sign-up is temporarily unavailable. Please try again later.")

    existing_user = db.query(User).filter(User.email == user_in.email.lower()).first()
    # Hash in both branches so a duplicate email is not revealed by a faster response (F-39).
    password_hash = hash_password(user_in.password)
    if existing_user:
        logger.warning("security_event registration_rejected reason=duplicate")
        audit_log.record("register", "failure", request=request, details={"reason": "duplicate"})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration could not be completed."
        )

    new_user = User(
        email=user_in.email.lower(),
        name=user_in.name.strip(),
        password_hash=password_hash,
        is_admin=False,
        role="consultant",
        groups=[settings.DEFAULT_ACCESS_GROUP],
        account_type="individual",
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    audit_log.record("register", request=request, principal=new_user, target=new_user.id)

    # Sign-up only creates the account; the user signs in afterwards (owner decision 2026-11-04),
    # so the session starts at /login with its rate limit, lockout and audit trail.
    return UserResponse.model_validate(new_user)

@router.post("/login", response_model=Token)
def login(login_data: UserLogin, request: Request, db: Session = Depends(get_db)):
    _guard_login(request, login_data.email)
    user = authenticate_user(db, login_data.email, login_data.password)
    if not user:
        rate_limiter.record_login_failure(login_data.email)
        logger.warning("[AUTH] Login failed: invalid credentials for email=%s", login_data.email)
        audit_log.record("login", "failure", request=request, target=login_data.email.lower())
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if getattr(user, "account_type", None) == "organisation":
        deny_sign_in(request, "login", user, "organisation_account", ORGANISATION_ACCOUNT_AT_INDIVIDUAL_LOGIN)
    require_usable_account(request, "login", user)
    return issue_login_token(request, "login", user, db)

@router.post("/admin-login", response_model=Token)
def admin_login(login_data: UserLogin, request: Request, db: Session = Depends(get_db)):
    _guard_login(request, login_data.email)
    user = authenticate_user(db, login_data.email, login_data.password)
    if not user:
        rate_limiter.record_login_failure(login_data.email)
        logger.warning("[AUTH] Admin login failed: invalid credentials or unauthorized user email=%s", login_data.email)
        audit_log.record("admin_login", "failure", request=request, target=login_data.email.lower())
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_admin:
        rate_limiter.record_login_failure(login_data.email)
        logger.warning("[AUTH] Admin login failed: invalid credentials or unauthorized user email=%s", login_data.email)
        audit_log.record("admin_login", "denied", request=request, principal=user, details={"reason": "not_admin"})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    require_usable_account(request, "admin_login", user)
    return issue_login_token(request, "admin_login", user, db)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user_allow_password_change)):
    return UserResponse.model_validate(current_user)


@router.get("/me/token-savings", response_model=TokenSavingsSummary,
            summary="Estimated tokens saved across the authenticated user's answers")
def my_token_savings(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Sums the figures stored with each answer in the user's own chats. Answers without stored figures
    (older or non-streamed ones) are left out rather than estimated; an answer that saved nothing counts 0."""
    answers, used, baseline, saved = (
        db.query(
            func.count(Message.id),
            func.coalesce(func.sum(Message.tokens_used), 0),
            func.coalesce(func.sum(Message.tokens_baseline), 0),
            func.coalesce(func.sum(func.greatest(Message.tokens_baseline - Message.tokens_used, 0)), 0),
        )
        .join(Chat, Chat.id == Message.chat_id)
        .filter(
            Chat.user_id == current_user.id,
            Message.role == "assistant",
            Message.tokens_used.isnot(None),
            Message.tokens_baseline.isnot(None),
        )
        .one()
    )
    return TokenSavingsSummary(answers=answers, used=used, baseline=baseline, saved=saved)


@router.post("/change-password", response_model=Token)
def change_password(
    change: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user_allow_password_change),
    db: Session = Depends(get_db),
):
    """Set a new password, clear a pending forced change and revoke every existing token."""
    if not rate_limiter.allow("change-password", current_user.id, settings.LOGIN_RATE_LIMIT_PER_MINUTE, 60):
        logger.warning("security_event password_change_throttled")
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=TOO_MANY_ATTEMPTS)
    if not verify_password(change.current_password, current_user.password_hash):
        audit_log.record("password_change", "failure", request=request, principal=current_user,
                         details={"reason": "current_password"})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=CURRENT_PASSWORD_INCORRECT)
    if verify_password(change.new_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=PASSWORD_UNCHANGED)
    current_user.password_hash = hash_password(change.new_password)
    current_user.must_change_password = False
    current_user.token_version += 1
    db.commit()
    db.refresh(current_user)
    audit_log.record("password_change", request=request, principal=current_user, target=current_user.id)
    access_token = create_access_token(data={"sub": current_user.id, "ver": current_user.token_version})
    return Token(access_token=access_token, token_type="bearer", user=UserResponse.model_validate(current_user))


@router.get("/me/export", summary="Export the authenticated user's account and conversation data")
def export_my_account(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    chats = db.query(Chat).filter(Chat.user_id == current_user.id).order_by(Chat.created_at).all()
    message_ids = [message.id for chat in chats for message in chat.messages]
    shared_by_message = {}
    if message_ids:
        for shared in db.query(SharedPrompt).filter(SharedPrompt.message_id.in_(message_ids)).all():
            shared_by_message[shared.message_id] = {
                "created_at": shared.created_at,
                "revoked": shared.revoked,
                "content": shared.content,
                "answer": shared.answer,
            }

    chat_exports = []
    for chat in chats:
        message_exports = []
        for message in chat.messages:
            message_exports.append({
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at,
                "feedback": message.feedback,
                "citations": [
                    {
                        "source_type": citation.source_type,
                        "document_name": citation.document_name,
                        "page_number": citation.page_number,
                        "section": citation.section,
                        "citation_text": citation.citation_text,
                    }
                    for citation in message.citations
                ],
                "web_sources": [
                    {"url": source.url, "title": source.title, "domain": source.domain, "snippet": source.snippet}
                    for source in message.web_sources
                ],
                "images": [
                    {
                        "url": image.url,
                        "description": image.description,
                        "alt_text": image.alt_text,
                        "source_url": image.source_url,
                        "source_title": image.source_title,
                    }
                    for image in message.images
                ],
                "attachments": [
                    {
                        "name": attachment.name,
                        "file_type": attachment.file_type,
                        "page_count": attachment.page_count,
                        "extracted_text": attachment.extracted_text,
                    }
                    for attachment in message.uploaded_attachments
                ],
                "shared_link": shared_by_message.get(message.id),
            })
        chat_exports.append({
            "id": chat.id,
            "title": chat.title,
            "created_at": chat.created_at,
            "updated_at": chat.updated_at,
            "summary": chat.summary,
            "messages": message_exports,
        })

    payload = {
        "export_version": 1,
        "exported_at": datetime.now(timezone.utc),
        "account": {
            "id": current_user.id,
            "email": current_user.email,
            "name": current_user.name,
            "created_at": current_user.created_at,
        },
        "chats": chat_exports,
    }
    audit_log.record("account_export", request=request, principal=current_user, target=current_user.id)
    return JSONResponse(
        content=jsonable_encoder(payload),
        headers={"Content-Disposition": f'attachment; filename="account-export-{uuid.uuid4().hex[:12]}.json"'},
    )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT, summary="Delete the authenticated user's account and data")
def delete_my_account(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.is_admin:
        remaining_admins = db.query(User).filter(
            User.is_admin.is_(True), User.id != current_user.id
        ).count()
        if remaining_admins == 0:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="The final administrator account cannot be deleted.")
    # Deleting the owner would leave the organisation without anyone able to manage it.
    if getattr(current_user, "org_role", None) == "owner":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="The organisation owner account cannot be deleted. Ask Clyptus to "
                                   "deactivate the organisation instead.")

    account_id = current_user.id
    email = current_user.email
    actor_type = "admin" if current_user.is_admin else "user"
    db.delete(current_user)
    db.commit()
    rate_limiter.clear_login_failures(email)
    audit_log.record(
        "account_delete", request=request, actor_id=account_id, actor_type=actor_type, target=account_id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, current_user: User = Depends(get_current_user_allow_password_change),
           db: Session = Depends(get_db)):
    current_user.token_version += 1
    db.commit()
    audit_log.record("logout", request=request, principal=current_user)
