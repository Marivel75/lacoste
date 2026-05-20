"""Service de persistance des articles collectés.

Gère l'écriture en base avec déduplication par URL : un article dont l'URL
est déjà connue n'est jamais réinséré. Retourne (total, nouveaux) pour
alimenter le log CollectionRun.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.models.article import Article as ArticleModel
from src.pipeline.models import Article as PipelineArticle


def current_week() -> str:
    """Retourne la semaine ISO courante, ex : '2026-W21'."""
    return datetime.now(tz=timezone.utc).strftime("%G-W%V")


def upsert_articles(
    db: Session,
    articles: list[PipelineArticle],
    week: str,
) -> tuple[int, int]:
    """Insère les articles inconnus en base, ignore les doublons par URL.

    Returns:
        (articles_fetched, articles_new)
    """
    if not articles:
        return 0, 0

    urls = [a.url for a in articles]
    existing_urls = {
        row[0]
        for row in db.query(ArticleModel.url).filter(ArticleModel.url.in_(urls)).all()
    }

    new_rows = [
        ArticleModel(
            url=art.url,
            title=art.title,
            source_name=art.source,
            source_category=art.category,
            published_at=art.published,
            summary=art.summary,
            score=art.score,
            keywords=art.matched_keywords,
            nlp_keywords=art.nlp_keywords,
            topics=art.topics,
            sentiment_score=art.sentiment_score,
            sentiment_label=art.sentiment_label,
            collection_week=week,
        )
        for art in articles
        if art.url not in existing_urls
    ]

    if new_rows:
        db.add_all(new_rows)
        db.commit()

    return len(articles), len(new_rows)
