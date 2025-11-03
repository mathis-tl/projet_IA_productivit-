from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List

class AITraceCreate(BaseModel):
    """Données pour logger une trace IA"""
    page_id: Optional[int] = None
    task_id: Optional[int] = None
    analysis_type: str  # "summarize", "checklist", "link_suggestion", etc.
    source_blocks: Optional[List[int]] = None  # IDs des blocks analysés
    generated_content: str  # résultat de l'analyse
    model_used: str = "mistral:7b"  # quel modèle Ollama
    tokens_used: Optional[int] = None  # tokens consommés
    execution_time_ms: Optional[int] = None  # temps d'exécution
    success: bool = True
    error_message: Optional[str] = None

class AITraceResponse(BaseModel):
    """Trace IA retournée par l'API"""
    id: int
    user_id: int
    page_id: Optional[int]
    task_id: Optional[int]
    analysis_type: str
    source_blocks: Optional[List[int]]
    generated_content: str
    model_used: str
    tokens_used: Optional[int]
    execution_time_ms: Optional[int]
    success: bool
    error_message: Optional[str]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
