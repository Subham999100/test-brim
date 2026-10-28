import hmac
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.schemas.auth import UserRegister, UserLogin, Token, UserResponse
from backend.app.security.auth import authenticate_user, hash_password, create_access_token, get_current_user
from backend.app.security.ratelimit import client_ip, rate_limiter
from backend.app.services import audit_log

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)

TOO_MANY_ATTEMPTS = "Too many login attempts. Try again later."


def _guard_login(request: Request, email: str) -> None:
    """Per-IP login rate and per-account lockout, checked before the password (AUDIT_REPORT F-06)."""
    if not rate_limiter.allow("login-ip", client_ip(request), settings.LOGIN_RATE_LIMIT_PER_MINUTE, 60):
        logger.warning("security_event login_throttled reason=ip_rate")
        audit_log.record("login", "denied", request=request, target=email, details={"reason": "ip_rate_limit"})
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=TOO_MANY_ATTEMPTS)
    if rate_limiter.account_locked(email):
        logger.warning("security_event login_throttled reason=account_lockout")
        audit_log.record("login", "denied", request=request, target=email, details={"reason": "account_lockout"})
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=TOO_MANY_ATTEMPTS)

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user_in: UserRegister, request: Request, db: Session = Depends(get_db)):
    # Public self-registration is opt-in, optionally behind an invite code (AUDIT_REPORT F-01).
    if not settings.REGISTRATION_ENABLED:
        audit_log.record("register", "denied", request=request, details={"reason": "registration_disabled"})
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Self-registration is disabled. Ask an administrator for an account.")
    if settings.INVITE_CODE and not hmac.compare_digest(
        (user_in.invite_code or "").encode("utf-8"), settings.INVITE_CODE.encode("utf-8")
    ):
        logger.warning("security_event registration_rejected reason=invite_code")
        audit_log.record("register", "denied", request=request, details={"reason": "invite_code"})
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="A valid invite code is required.")

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
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    audit_log.record("register", request=request, principal=new_user, target=new_user.id)

    access_token = create_access_token(data={"sub": new_user.id, "ver": new_user.token_version})
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(new_user)
    )

@router.post("/login", response_model=Token)
def login(login_data: UserLogin, request: Request, db: Session = Depends(get_db)):
    _guard_login(request, login_data.email)
    user = authenticate_user(db, login_data.email, login_data.password)
    if not user:
        rate_limiter.record_login_failure(login_data.email)
        logger.warning("security_event login_failed flow=standard")
        audit_log.record("login", "failure", request=request, target=login_data.email.lower())
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    rate_limiter.clear_login_failures(login_data.email)
    audit_log.record("login", request=request, principal=user)
    access_token = create_access_token(data={"sub": user.id, "ver": user.token_version})
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

@router.post("/admin-login", response_model=Token)
def admin_login(login_data: UserLogin, request: Request, db: Session = Depends(get_db)):
    _guard_login(request, login_data.email)
    user = authenticate_user(db, login_data.email, login_data.password)
    if not user:
        rate_limiter.record_login_failure(login_data.email)
        logger.warning("security_event login_failed flow=admin")
        audit_log.record("admin_login", "failure", request=request, target=login_data.email.lower())
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_admin:
        rate_limiter.record_login_failure(login_data.email)
        logger.warning("security_event login_failed flow=admin")
        audit_log.record("admin_login", "denied", request=request, principal=user, details={"reason": "not_admin"})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    rate_limiter.clear_login_failures(login_data.email)
    audit_log.record("admin_login", request=request, principal=user)
    access_token = create_access_token(data={"sub": user.id, "ver": user.token_version})
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.token_version += 1
    db.commit()
    audit_log.record("logout", request=request, principal=current_user)
