"""A user's projects (folders for related chats). Every query filters on the signed-in user, so another
account's project ids return 404."""

from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.chat import Chat
from backend.app.models.project import Project
from backend.app.models.user import User
from backend.app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from backend.app.security.auth import get_current_user

router = APIRouter(prefix="/projects", tags=["Projects"])

PROJECT_NOT_FOUND = "Project not found."


def own_project(db: Session, user: User, project_id: str) -> Project:
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PROJECT_NOT_FOUND)
    return project


def _chat_counts(db: Session, user: User) -> Dict[str, int]:
    rows = (
        db.query(Chat.project_id, func.count(Chat.id))
        .filter(Chat.user_id == user.id, Chat.project_id.isnot(None))
        .group_by(Chat.project_id)
        .all()
    )
    return {project_id: count for project_id, count in rows}


def _out(project: Project, chat_count: int) -> ProjectResponse:
    response = ProjectResponse.model_validate(project)
    response.chat_count = chat_count
    return response


@router.get("", response_model=List[ProjectResponse])
def list_projects(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    counts = _chat_counts(db, current_user)
    projects = (
        db.query(Project).filter(Project.user_id == current_user.id).order_by(Project.created_at.desc()).all()
    )
    return [_out(project, counts.get(project.id, 0)) for project in projects]


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(body: ProjectCreate, current_user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    project = Project(user_id=current_user.id, name=body.name, description=body.description,
                      is_pinned=body.is_pinned)
    db.add(project)
    db.commit()
    db.refresh(project)
    return _out(project, 0)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: str, body: ProjectUpdate, current_user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    project = own_project(db, current_user, project_id)
    sent = body.model_fields_set
    if "name" in sent and body.name is not None:
        project.name = body.name
    if "description" in sent:
        project.description = body.description
    if "is_pinned" in sent and body.is_pinned is not None:
        project.is_pinned = body.is_pinned
    db.commit()
    db.refresh(project)
    return _out(project, _chat_counts(db, current_user).get(project.id, 0))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Deletes the project only: its chats stay in the user's chat list."""
    project = own_project(db, current_user, project_id)
    db.query(Chat).filter(Chat.project_id == project.id, Chat.user_id == current_user.id).update(
        {Chat.project_id: None}, synchronize_session=False
    )
    db.delete(project)
    db.commit()
