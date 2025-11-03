# IMPORTS
from sqlalchemy.orm import Session
from app.models.page import Page
from app.models.block import Block
from app.models.link import Link
from typing import List, Tuple, Optional

# func 1: get_page_with_blocks()
def get_page_with_blocks(db: Session, user_id: int, page_id: int) -> Tuple[Optional[Page], List[Block]]:
   
    page = db.query(Page).filter(Page.id == page_id, Page.user_id == user_id).first()
    
    if not page:
        return None, []
    
    blocks = db.query(Block).filter(Block.page_id == page_id).order_by(Block.order).all()
 
    return page, blocks

# func 2: get_page_backlinks()
def get_page_backlinks(db: Session, user_id: int, page_id: int) -> List[Link]:
  
    backlinks = db.query(Link).filter(
        Link.target_page_id == page_id,
        Link.user_id == user_id
    ).all()
    
    return backlinks

# func 3: get_related_pages()
def get_related_pages(db: Session, user_id: int, page_id: int) -> List[Page]:
    # outlinks
    outlink_pages = db.query(Page).join(
        Link, Link.target_page_id == Page.id
    ).filter(
        Link.source_page_id == page_id,
        Link.user_id == user_id
    ).all()

    # backlinks
    backlink_pages = db.query(Page).join(
        Link, Link.source_page_id == Page.id
    ).filter(
        Link.target_page_id == page_id,
        Link.user_id == user_id
    ).all()
# on combine les deux listes et on retire les doublons
    all_related = outlink_pages + backlink_pages
    

    seen_ids = set()
    unique_pages = []
    for page in all_related:
        if page.id not in seen_ids:
            seen_ids.add(page.id)
            unique_pages.append(page)
    
    return unique_pages