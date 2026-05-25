from datetime import datetime

from pydantic import BaseModel


class WeekSummary(BaseModel):
    week: str
    article_count: int
    articles_new: int
    run_at: datetime | None
    status: str | None
