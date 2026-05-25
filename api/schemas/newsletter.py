from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NewsletterSendRequest(BaseModel):
    week: str | None = None
    extra_recipients: list[str] = []


class NewsletterSendResult(BaseModel):
    week: str
    articles_sent: int
    sent: bool
    recipients: list[str]


class NewsletterLogOut(BaseModel):
    id: int
    week: str
    sent_at: datetime
    recipients: list[str]
    articles_count: int
    status: str
    error_message: str | None

    model_config = ConfigDict(from_attributes=True)
