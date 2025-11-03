from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List

# Schemas pour les pages

class PageCreate(BaseModel):
    title: str
    description: Optional[str] = None
    icon: Optional[str] = "📄"

class PageUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None

class PageResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: Optional[str]
    icon: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PageWithBlocks(PageResponse):
    blocks: List['BlockResponse'] = []