from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ArticleOut(BaseModel):
    id: int
    url: str
    title: str
    source_name: str
    source_category: str
    published_at: datetime | None
    summary: str
    score: int
    keywords: list[str]
    nlp_keywords: list[str]
    topics: list[str]
    sentiment_score: float | None
    sentiment_label: str | None
    collection_week: str
    collected_at: datetime

    model_config = ConfigDict(from_attributes=True)
