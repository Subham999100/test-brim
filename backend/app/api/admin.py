from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.schemas.auth import UserResponse
from backend.app.security.access import normalize_groups
from backend.app.security.auth import get_current_admin_user, verify_admin_key_or_user
from backend.app.ingestion.ingest import run_ingestion

router = APIRouter(prefix="/admin", tags=["Admin / Developer Ingestion"])


class GroupsUpdate(BaseModel):
    groups: List[str] = Field(..., min_length=1, max_length=50)


@router.post("/documents/ingest")
def trigger_ingestion(
    authorized: bool = Depends(verify_admin_key_or_user),
    db: Session = Depends(get_db)
):
    """
    Developer-only ingestion endpoint.
    Scans backend/knowledge_base/documents/ for PDFs, extracts, chunks, embeds, and stores them.
    """
    results = run_ingestion(db)
    return {
        "status": "success",
        "message": "Ingestion process completed successfully.",
        "details": results
    }


@router.get("/users", response_model=List[UserResponse])
def list_users(
    search: Optional[str] = Query(None, max_length=255),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Accounts with their access groups (AUDIT_REPORT F-01)."""
    query = db.query(User)
    if search:
        query = query.filter(User.email.ilike(f"%{search.strip()}%"))
    users = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    return [UserResponse.model_validate(u) for u in users]


@router.patch("/users/{user_id}/groups", response_model=UserResponse)
def set_user_groups(
    user_id: str,
    update: GroupsUpdate,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Replace a user's access groups; retrieval then only uses documents sharing one of them."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    groups = normalize_groups(update.groups)
    if not groups:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="At least one group is required")
    user.groups = groups
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)
