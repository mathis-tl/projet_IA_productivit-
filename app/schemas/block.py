from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Any

class BlockCreate(BaseModel):
    """Créer un block"""
    type: str = "text"  # "text", "heading", "list", "code", "image", "quote"
    content: str
    order: int = 0
    block_metadata: Optional[dict[str, Any]] = None

class BlockUpdate(BaseModel):
    """Modifier un block"""
    type: Optional[str] = None
    content: Optional[str] = None
    order: Optional[int] = None
    block_metadata: Optional[dict[str, Any]] = None

class BlockResponse(BaseModel):
    """Block retourné"""
    id: int
    page_id: int
    user_id: int
    type: str
    content: str
    order: int
    block_metadata: Optional[dict[str, Any]]
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)