"""Modèles de données internes au pipeline (dataclasses).

Article est le DTO (Data Transfer Object) utilisé tout au long du pipeline :
fetch → filter → nlp → export. Distinct des modèles SQLAlchemy de src/models/
qui représentent la persistance en base.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Article:
    title: str
    url: str
    source: str
    category: str
    summary: str = ""
    published: Optional[datetime] = None
    matched_keywords: list[str] = field(default_factory=list)
    score: int = 0
    nlp_keywords: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None

    def __str__(self) -> str:
        return f"[{self.source}] {self.title}"
