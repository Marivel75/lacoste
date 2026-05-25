"""Envoi de la newsletter hebdomadaire depuis la base de données.

Charge les articles d'une semaine ISO (ex: '2026-W21'), les convertit en DTOs
pipeline, recalcule le nuage de mots, puis délègue l'envoi au Mailer SMTP.
"""

import logging

from sqlalchemy.orm import Session

from src.config import Config
from src.db.session import SessionLocal
from src.mailer import Mailer
from src.models.article import Article as ArticleModel
from src.models.newsletter_log import NewsletterLog
from src.pipeline.models import Article as PipelineArticle
from src.pipeline.nlp import count_term_frequencies
from src.services.article_service import current_week

logger = logging.getLogger(__name__)


def get_articles_for_week(db: Session, week: str) -> list[PipelineArticle]:
    """Retourne les articles d'une semaine depuis la DB, triés par score desc."""
    rows = (
        db.query(ArticleModel)
        .filter(ArticleModel.collection_week == week)
        .order_by(ArticleModel.score.desc())
        .all()
    )
    return [_to_dto(row) for row in rows]


def send_newsletter(
    week: str | None = None,
    extra_recipients: list[str] | None = None,
) -> dict:
    """Envoie la newsletter pour la semaine donnée (courante par défaut).

    Args:
        week: semaine ISO cible, ex. '2026-W21' (courante si None)
        extra_recipients: destinataires supplémentaires ajoutés aux EMAIL_RECIPIENTS du .env

    Returns:
        {"week": str, "articles_sent": int, "sent": bool, "recipients": list[str]}
    """
    config = Config.load()
    db = SessionLocal()
    try:
        target_week = week or current_week()
        articles = get_articles_for_week(db, target_week)

        if not articles:
            logger.warning("Newsletter %s — aucun article en base.", target_week)
            return {"week": target_week, "articles_sent": 0, "sent": False, "recipients": []}

        # Fusionne les destinataires de base + extra, sans doublons, ordre conservé
        all_recipients = list(dict.fromkeys(
            config.email_recipients + (extra_recipients or [])
        ))

        if not config.email_sender or not config.email_password or not all_recipients:
            logger.warning(
                "Newsletter %s — %d articles trouvés mais email non configuré.",
                target_week, len(articles),
            )
            return {"week": target_week, "articles_sent": len(articles), "sent": False, "recipients": []}

        all_texts = [f"{a.title} {a.summary}" for a in articles]
        word_freq = count_term_frequencies(all_texts, top_n=30)

        mailer = Mailer(config.email_sender, config.email_password, all_recipients)
        try:
            mailer.send(articles, lookback_days=config.lookback_days, word_freq=word_freq)
        except Exception as exc:
            _log_send(db, target_week, all_recipients, len(articles), "error", str(exc))
            raise

        _log_send(db, target_week, all_recipients, len(articles), "sent")
        logger.info(
            "Newsletter %s envoyée à %d destinataire(s) — %d articles.",
            target_week, len(all_recipients), len(articles),
        )
        return {"week": target_week, "articles_sent": len(articles), "sent": True, "recipients": all_recipients}
    finally:
        db.close()


def _log_send(
    db,
    week: str,
    recipients: list[str],
    articles_count: int,
    status: str,
    error_message: str | None = None,
) -> None:
    entry = NewsletterLog(
        week=week,
        recipients=recipients,
        articles_count=articles_count,
        status=status,
        error_message=error_message,
    )
    db.add(entry)
    db.commit()


def _to_dto(row: ArticleModel) -> PipelineArticle:
    return PipelineArticle(
        title=row.title,
        url=row.url,
        source=row.source_name,
        category=row.source_category,
        summary=row.summary or "",
        published=row.published_at,
        matched_keywords=row.keywords or [],
        score=row.score,
        nlp_keywords=row.nlp_keywords or [],
        topics=row.topics or [],
        sentiment_score=row.sentiment_score,
        sentiment_label=row.sentiment_label,
    )
