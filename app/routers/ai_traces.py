from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.ai_trace import AITrace
from app.schemas.ai_trace import AITraceCreate, AITraceResponse
from app.core.security import decode_token
from fastapi import Header
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/ai-traces", tags=["ai-traces"])

def get_current_user(db: Session = Depends(get_db), authorization: Optional[str] = Header(None)) -> User:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return user

@router.post("", response_model=AITraceResponse, status_code=status.HTTP_201_CREATED)
def create_ai_trace(trace_data: AITraceCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    
    new_trace = AITrace(
        user_id=current_user.id,
        page_id=trace_data.page_id,
        task_id=trace_data.task_id,
        analysis_type=trace_data.analysis_type,
        source_blocks=trace_data.source_blocks,
        generated_content=trace_data.generated_content,
        model_used=trace_data.model_used,
        tokens_used=trace_data.tokens_used,
        execution_time_ms=trace_data.execution_time_ms,
        success=trace_data.success,
        error_message=trace_data.error_message
    )
    db.add(new_trace)
    db.commit()
    db.refresh(new_trace)
    
    return new_trace

@router.get("", response_model=List[AITraceResponse])
def list_ai_traces(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    traces = db.query(AITrace).filter(
        AITrace.user_id == current_user.id
    ).order_by(AITrace.created_at.desc()).all()
    
    return traces

@router.get("/{trace_id}", response_model=AITraceResponse)
def get_ai_trace(trace_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):    
    trace = db.query(AITrace).filter(
        AITrace.id == trace_id,
        AITrace.user_id == current_user.id
    ).first()
    if not trace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trace not found"
        )
    
    return trace

@router.get("/page/{page_id}", response_model=List[AITraceResponse])
def get_traces_for_page(page_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    
    traces = db.query(AITrace).filter(
        AITrace.page_id == page_id,
        AITrace.user_id == current_user.id
    ).order_by(AITrace.created_at.desc()).all()
    return traces

@router.get("/task/{task_id}", response_model=List[AITraceResponse])
def get_traces_for_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):    
    traces = db.query(AITrace).filter(
        AITrace.task_id == task_id,
        AITrace.user_id == current_user.id
    ).order_by(AITrace.created_at.desc()).all()
    
    return traces
