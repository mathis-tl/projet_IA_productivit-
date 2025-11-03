from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Boolean
from datetime import datetime
from app.core.database import Base

class AITrace(Base):
    __tablename__ = "ai_traces"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    page_id = Column(Integer, ForeignKey("pages.id"), nullable=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True, index=True)
    analysis_type = Column(String, nullable=False)  # "summarize", "extract_actions", "parse_calendar", etc
    source_blocks = Column(JSON, nullable=True)  #IDs des blocks analysés
    generated_content = Column(String, nullable=False)  # résultat de l'analyse
    model_used = Column(String, default="mistral:7b")  # Ollama
    tokens_used = Column(Integer, nullable=True)  #tracking coûts/perf
    execution_time_ms = Column(Integer, nullable=True)  # temps d'exécution
    success = Column(Boolean, default=True)
    error_message = Column(String, nullable=True)  # si failure
    created_at = Column(DateTime, default=datetime.utcnow)