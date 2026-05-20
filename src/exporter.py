"""Export CSV des articles filtrés (héritage du pipeline v1).

Conservé pour compatibilité et backup local. Dans la nouvelle architecture,
la persistance principale se fait en base via article_service. L'export CSV
reste disponible comme sortie optionnelle du pipeline.
"""

import csv
import logging
from datetime import datetime, timezone
from pathlib import Path

from .models import Article

logger = logging.getLogger(__name__)

COLUMNS = [
    "source", "categorie", "titre", "url", "date_publication",
    "thematiques", "mots_cles_nlp", "topics", "score",
    "sentiment_label", "sentiment_score",
]


class CSVExporter:

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    def export(self, articles: list[Article]) -> Path:
        self.data_dir.mkdir(exist_ok=True)
        path = self.data_dir / self._filename()
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writeheader()
            for article in articles:
                writer.writerow(self._to_row(article))
        logger.info("CSV exporté : %s (%d articles)", path, len(articles))
        return path

    @staticmethod
    def _to_row(article: Article) -> dict:
        published = ""
        if article.published:
            published = article.published.strftime("%Y-%m-%d")
        return {
            "source": article.source,
            "categorie": article.category,
            "titre": article.title,
            "url": article.url,
            "date_publication": published,
            "thematiques": ", ".join(article.matched_keywords),
            "mots_cles_nlp": ", ".join(article.nlp_keywords),
            "topics": ", ".join(article.topics),
            "score": article.score,
            "sentiment_label": article.sentiment_label or "",
            "sentiment_score": article.sentiment_score if article.sentiment_score is not None else "",
        }

    @staticmethod
    def _filename() -> str:
        week = datetime.now(tz=timezone.utc).strftime("%Y-W%W")
        return f"veille_{week}.csv"
