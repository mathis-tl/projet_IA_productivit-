from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import verify_token, decode_token
from app.models.user import User
from app.models.ai_trace import AITrace
from app.services.nlp_service import extract_entities, extract_dates, suggest_task
from app.schemas.task import TaskCreate

router = APIRouter(prefix="/ai-nlp", tags=["ai-nlp"])


# Récupérer l'utilisateur actuel à partir du token JWT
def get_current_user(db: Session = Depends(get_db), authorization: Optional[str] = Header(None)) -> User:
    if not authorization:
        raise HTTPException(status_code=401, detail="Token manquant")
    
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Token invalide")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    return user


# Schémas Pydantic
class ExtractEntitiesRequest(BaseModel):
    text: str


class ExtractEntitiesResponse(BaseModel):
    personnes: List[str]
    lieux: List[str]
    dates: List[str]
    organisations: List[str]
    trace_id: Optional[str] = None


class ExtractDatesRequest(BaseModel):
    text: str


class ExtractedDate(BaseModel):
    text: str
    datetime: Optional[str]
    timestamp: Optional[float]


class ExtractDatesResponse(BaseModel):
    dates: List[ExtractedDate]
    trace_id: Optional[str] = None


class SuggestTaskRequest(BaseModel):
    text: str


class SuggestTaskResponse(BaseModel):
    titre: str
    description: str
    date_echéance: Optional[str]
    priorité: int
    trace_id: Optional[str] = None


# Endpoint 1: Extraire les entités nommées
@router.post("/extract-entities", response_model=ExtractEntitiesResponse)
def extract_entities_endpoint(
    request: ExtractEntitiesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Extraire les entités
    entities = extract_entities(request.text)
    
    # Créer une trace d'audit
    trace = AITrace(
        user_id=current_user.id,
        action="extract_entities",
        input_text=request.text[:500],  # Limiter à 500 caractères
        output_text=str(entities)[:500],
        tokens_used=0,
        execution_time_ms=0
    )
    db.add(trace)
    db.commit()
    db.refresh(trace)
    
    return ExtractEntitiesResponse(
        **entities,
        trace_id=str(trace.id)
    )


# Endpoint 2: Extraire et parser les dates
@router.post("/extract-dates", response_model=ExtractDatesResponse)
def extract_dates_endpoint(
    request: ExtractDatesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Extraire les dates
    dates = extract_dates(request.text)
    
    # Créer une trace d'audit
    trace = AITrace(
        user_id=current_user.id,
        action="extract_dates",
        input_text=request.text[:500],
        output_text=str(dates)[:500],
        tokens_used=0,
        execution_time_ms=0
    )
    db.add(trace)
    db.commit()
    db.refresh(trace)
    
    return ExtractDatesResponse(
        dates=[ExtractedDate(**d) for d in dates],
        trace_id=str(trace.id)
    )


# Endpoint 3: Suggérer une tâche
@router.post("/suggest-task", response_model=SuggestTaskResponse)
def suggest_task_endpoint(
    request: SuggestTaskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Suggérer une tâche
    task_suggestion = suggest_task(request.text)
    
    # Créer une trace d'audit
    trace = AITrace(
        user_id=current_user.id,
        action="suggest_task",
        input_text=request.text[:500],
        output_text=str(task_suggestion)[:500],
        tokens_used=0,
        execution_time_ms=0
    )
    db.add(trace)
    db.commit()
    db.refresh(trace)
    
    return SuggestTaskResponse(
        **task_suggestion,
        trace_id=str(trace.id)
    )
