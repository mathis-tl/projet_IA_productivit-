"""
Router pour les analyses IA avec Ollama.

Endpoints:
- POST /ai-analyze/summarize - Résumer du contenu
- POST /ai-analyze/extract-actions - Extraire des actions
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.ai_trace import AITrace
from app.core.security import decode_token
from app.services.ai_service import generate_summary, extract_actions, is_ollama_running
from fastapi import Header
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/ai-analyze", tags=["ai-analyze"])

#SCHEMAS
#Request pour résumer du contenu
class SummarizeRequest(BaseModel):
    content: str
    page_id: Optional[int] = None
    task_id: Optional[int] = None
#Reponse
class SummarizeResponse(BaseModel):
    summary: str
    tokens_used: int
    execution_time_ms: int
    trace_id: int
#request pour extraire les actions
class ExtractActionsRequest(BaseModel):
    content: str
    page_id: Optional[int] = None
    task_id: Optional[int] = None

#reponse avec les actions
class ExtractActionsResponse(BaseModel):
    actions: List[str]
    tokens_used: int
    execution_time_ms: int
    trace_id: int

#AUTH

def get_current_user(db: Session = Depends(get_db), authorization: Optional[str] = Header(None)) -> User:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    
    token = authorization.replace("Bearer ", "")
    from app.core.security import decode_token
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return user

#ENDPOINTS

@router.post("/summarize", response_model=SummarizeResponse, status_code=status.HTTP_201_CREATED)
def summarize(
    request: SummarizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Résumer  avec Ollama.
    
    1 Vérifier qu'Ollama est dispo
    2 Appeler Ollama.generate_summary()
    3 Logger la trace dans AITrace
    4 Retourner le résumé + les stats
    
    exemple:
    POST /ai-analyze/summarize
    {
      "content": "Texto long à résumer...",
      "page_id": 1
    }
    →
    {
      "summary": "Résumé du texte...",
      "tokens_used": 342,
      "execution_time_ms": 1200,
      "trace_id": 5
    }
    """
    
    # Vérifier qu'Ollama est disponible
    if not is_ollama_running():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ollama is not running. Start it with: ollama run mistral:7b"
        )
    
    try:
        # Appeler Ollama
        summary, tokens_used, execution_time_ms = generate_summary(request.content)
        
        # Logger la trace
        trace = AITrace(
            user_id=current_user.id,
            page_id=request.page_id,
            task_id=request.task_id,
            analysis_type="summarize",
            generated_content=summary,
            model_used="mistral:7b",
            tokens_used=tokens_used,
            execution_time_ms=execution_time_ms,
            success=True,
            error_message=None
        )
        db.add(trace)
        db.commit()
        db.refresh(trace)
        
        return SummarizeResponse(
            summary=summary,
            tokens_used=tokens_used,
            execution_time_ms=execution_time_ms,
            trace_id=trace.id
        )
        
    except Exception as e:
        # Logger l'erreur dans AITrace
        error_trace = AITrace(
            user_id=current_user.id,
            page_id=request.page_id,
            task_id=request.task_id,
            analysis_type="summarize",
            generated_content="",
            model_used="mistral:7b",
            tokens_used=0,
            execution_time_ms=0,
            success=False,
            error_message=str(e)
        )
        db.add(error_trace)
        db.commit()
        db.refresh(error_trace)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ollama error: {str(e)}"
        )

@router.post("/extract-actions", response_model=ExtractActionsResponse, status_code=status.HTTP_201_CREATED)
def extract_actions_endpoint(
    request: ExtractActionsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Extraire les actions/tâches du contenu avec Ollama.
   
    mm logique
    
    EXEMPLE:
    POST /ai-analyze/extract-actions
    {
      "content": "Appelle Jean demain, puis finalise le rapport"
    }
    →
    {
      "actions": ["Appeler Jean", "Finaliser le rapport"],
      "tokens_used": 215,
      "execution_time_ms": 980,
      "trace_id": 6
    }
    """
    
    if not is_ollama_running():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ollama is not running"
        )
    
    try:
        # Appeler Ollama
        actions, tokens_used, execution_time_ms = extract_actions(request.content)
        
        # Logger la trace
        trace = AITrace(
            user_id=current_user.id,
            page_id=request.page_id,
            task_id=request.task_id,
            analysis_type="extract_actions",
            generated_content="\n".join(actions),
            model_used="mistral:7b",
            tokens_used=tokens_used,
            execution_time_ms=execution_time_ms,
            success=True,
            error_message=None
        )
        db.add(trace)
        db.commit()
        db.refresh(trace)
        
        return ExtractActionsResponse(
            actions=actions,
            tokens_used=tokens_used,
            execution_time_ms=execution_time_ms,
            trace_id=trace.id
        )
        
    except Exception as e:
        # Logger l'erreur
        error_trace = AITrace(
            user_id=current_user.id,
            page_id=request.page_id,
            task_id=request.task_id,
            analysis_type="extract_actions",
            generated_content="",
            model_used="mistral:7b",
            tokens_used=0,
            execution_time_ms=0,
            success=False,
            error_message=str(e)
        )
        db.add(error_trace)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ollama error: {str(e)}"
        )

@router.get("/health")
def health_check():
    """Vérifier si Ollama est disponible"""
    if is_ollama_running():
        return {"status": "ok", "ollama": "running"}
    else:
        return {"status": "warning", "ollama": "not running"}
