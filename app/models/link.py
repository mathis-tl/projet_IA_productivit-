from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.core.database import Base

class Link(Base):
    __tablename__ = "links"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    source_page_id = Column(Integer, ForeignKey("pages.id"), nullable=False, index=True)
    target_page_id = Column(Integer, ForeignKey("pages.id"), nullable=False, index=True)
    type = Column(String, default="related")  # "related", "blocks", "implements", "references"
    created_at = Column(DateTime, default=datetime.utcnow)