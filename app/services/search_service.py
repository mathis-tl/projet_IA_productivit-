from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.page import Page
from app.models.block import Block
from typing import List


class SearchResult:
    def __init__(self, result_type: str, id: int, title: str, snippet: str):
        self.result_type = result_type
        self.id = id
        self.title = title
        self.snippet = snippet


def full_text_search(db: Session, user_id: int, query: str) -> List[SearchResult]:
    # Cherche dans pages et blocks
    search_pattern = f"%{query.lower()}%"
    results = []
    
    # Pages par titre
    pages = db.query(Page).filter(
        Page.user_id == user_id,
        Page.is_archived == False,
        Page.title.ilike(search_pattern)
    ).all()
    
    for page in pages:
        results.append(SearchResult(
            result_type="page",
            id=page.id,
            title=page.title,
            snippet=page.description or ""
        ))
    
    # Blocks par contenu
    blocks = db.query(Block).filter(
        Block.user_id == user_id,
        Block.is_archived == False,
        Block.content.ilike(search_pattern)
    ).all()
    
    for block in blocks:
        preview = block.content
        if len(preview) > 100:
            preview = preview[:100] + "..."
        
        results.append(SearchResult(
            result_type="block",
            id=block.id,
            title=f"Block ({block.type})",
            snippet=preview
        ))
    
    return results
