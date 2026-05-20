"""Filtrage et scoring des articles par mots-clés.

Attribue un score à chaque article selon les mots-clés détectés :
- mot-clé présent dans le titre  → 2 points
- mot-clé présent dans le résumé uniquement → 1 point
Filtre les articles trop anciens (lookback_days) et ceux sous le score minimum.
"""

import logging
import re
from datetime import datetime, timedelta, timezone

from src.pipeline.models import Article

logger = logging.getLogger(__name__)


class KeywordFilter:

    def __init__(self, keywords: list[str]):
        self.keywords = keywords

    def filter(
        self,
        articles: list[Article],
        min_score: int = 1,
        lookback_days: int = 7,
    ) -> list[Article]:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=lookback_days)
        results = []
        for article in articles:
            if not self._is_recent(article, cutoff):
                continue
            score, matched = self._score(article)
            if score < min_score:
                continue
            article.score = score
            article.matched_keywords = matched
            results.append(article)
        results.sort(key=self._sort_key, reverse=True)
        logger.info("Filtre : %d articles retenus sur %d", len(results), len(articles))
        return results

    def _score(self, article: Article) -> tuple[int, list[str]]:
        haystack = f"{article.title} {article.summary}".lower()
        title_lower = article.title.lower()
        matched = []
        for kw in self.keywords:
            pattern = re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
            if pattern.search(haystack):
                matched.append(kw)
        # Mots-clés présents dans le titre comptent double
        score = sum(2 if kw in title_lower else 1 for kw in matched)
        return score, list(dict.fromkeys(matched))

    @staticmethod
    def _is_recent(article: Article, cutoff: datetime) -> bool:
        if not article.published:
            return True
        pub = article.published
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        return pub >= cutoff

    @staticmethod
    def _sort_key(article: Article):
        pub = article.published or datetime.min.replace(tzinfo=timezone.utc)
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        return (article.score, pub)
