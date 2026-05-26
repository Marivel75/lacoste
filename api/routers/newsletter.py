from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.schemas.newsletter import NewsletterLogOut, NewsletterSendRequest, NewsletterSendResult
from src.models.newsletter_log import NewsletterLog
from src.services.newsletter_service import send_newsletter

router = APIRouter(prefix="/newsletter", tags=["newsletter"])


@router.post("/send", response_model=NewsletterSendResult)
def send(req: NewsletterSendRequest = NewsletterSendRequest()):
    try:
        result = send_newsletter(req.week, extra_recipients=req.extra_recipients or None, limit=req.limit)
        return NewsletterSendResult(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/logs", response_model=list[NewsletterLogOut])
def list_logs(limit: int = 20, db: Session = Depends(get_db)):
    return (
        db.query(NewsletterLog)
        .order_by(NewsletterLog.sent_at.desc())
        .limit(limit)
        .all()
    )
