from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.schemas.article import ArticleOut
from src.models.article import Article

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("/", response_model=list[ArticleOut])
def list_articles(
    week: str | None = Query(None, description="Semaine ISO, ex: 2026-W22"),
    source: str | None = Query(None),
    category: str | None = Query(None),
    min_score: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(Article)
    if week:
        q = q.filter(Article.collection_week == week)
    if source:
        q = q.filter(Article.source_name == source)
    if category:
        q = q.filter(Article.source_category == category)
    if min_score:
        q = q.filter(Article.score >= min_score)
    return q.order_by(Article.score.desc()).offset(offset).limit(limit).all()


@router.get("/{article_id}", response_model=ArticleOut)
def get_article(article_id: int, db: Session = Depends(get_db)):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article introuvable")
    return article
