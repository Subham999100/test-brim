"""Projects: a user's folders for related chats (Alembic revision 0009_projects).

A chat belongs to at most one project (`chats.project_id`). That foreign key exists in the migration only,
because revision 0001 builds `chats` from the current model before `projects` exists. Deleting a project
keeps its chats (ON DELETE SET NULL); deleting the user removes their projects (ON DELETE CASCADE).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text

from backend.app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_pinned = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=_now, nullable=False)
    updated_at = Column(DateTime, default=_now, onupdate=_now, nullable=False)
