from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class LinkCreate(BaseModel):
    """Créer un lien entre deux pages"""
    source_page_id: int
    target_page_id: int
    type: str = "related"  # "related", "blocks", "implements", "references"

class LinkResponse(BaseModel):
    """Lien retourné"""
    id: int
    user_id: int
    source_page_id: int
    target_page_id: int
    type: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)