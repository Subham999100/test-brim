from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from backend.app.schemas.message import MessageResponse

class ChatCreate(BaseModel):
    title: Optional[str] = Field(default="New SAP Chat", max_length=255)
    # Start the chat inside one of the user's projects.
    project_id: Optional[str] = Field(default=None, max_length=36)

class ChatUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)

class ChatResponse(BaseModel):
    id: str
    user_id: str
    title: str
    project_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []

    model_config = ConfigDict(from_attributes=True)

class ChatListItem(BaseModel):
    id: str
    user_id: str
    title: str
    project_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = ConfigDict(from_attributes=True)
