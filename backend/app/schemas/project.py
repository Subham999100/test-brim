from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Same limits as the project dialog (frontend/src/components/projects/ProjectModal.tsx).
NAME_MAX = 100
DESCRIPTION_MAX = 500


class _ProjectFields(BaseModel):
    @field_validator("name", check_fields=False)
    @classmethod
    def clean_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Enter a project name")
        return value

    @field_validator("description", check_fields=False)
    @classmethod
    def clean_description(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return value.strip() or None


class ProjectCreate(_ProjectFields):
    name: str = Field(..., min_length=1, max_length=NAME_MAX)
    description: Optional[str] = Field(default=None, max_length=DESCRIPTION_MAX)
    is_pinned: bool = False


class ProjectUpdate(_ProjectFields):
    """Only the fields sent are changed; an empty description clears it."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=NAME_MAX)
    description: Optional[str] = Field(default=None, max_length=DESCRIPTION_MAX)
    is_pinned: Optional[bool] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    is_pinned: bool
    created_at: datetime
    updated_at: datetime
    chat_count: int = 0

    model_config = ConfigDict(from_attributes=True)
