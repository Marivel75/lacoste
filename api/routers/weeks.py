from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.schemas.week import WeekSummary
from src.models.article import Article
from src.models.collection_run import CollectionRun

router = APIRouter(prefix="/weeks", tags=["weeks"])


def _week_summary(db: Session, week: str, article_count: int) -> WeekSummary:
    run = (
        db.query(CollectionRun)
        .filter(CollectionRun.week == week)
        .order_by(CollectionRun.run_at.desc())
        .first()
    )
    return WeekSummary(
        week=week,
        article_count=article_count,
        articles_new=run.articles_new if run else 0,
        run_at=run.run_at if run else None,
        status=run.status if run else None,
    )


@router.get("/", response_model=list[WeekSummary])
def list_weeks(db: Session = Depends(get_db)):
    rows = (
        db.query(Article.collection_week, func.count(Article.id))
        .group_by(Article.collection_week)
        .order_by(Article.collection_week.desc())
        .all()
    )
    return [_week_summary(db, week, count) for week, count in rows]


@router.get("/{week}", response_model=WeekSummary)
def get_week(week: str, db: Session = Depends(get_db)):
    count = (
        db.query(func.count(Article.id))
        .filter(Article.collection_week == week)
        .scalar()
    )
    if not count:
        raise HTTPException(status_code=404, detail=f"Semaine {week} introuvable")
    return _week_summary(db, week, count)
