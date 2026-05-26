"""Envoi de la newsletter depuis la base de données.

Deux modes :
- Quotidien (limit=N) : top N articles jamais envoyés, triés par score desc.
  Les IDs envoyés sont tracés dans newsletter_logs.article_ids pour éviter
  tout doublon lors des envois suivants.
- Hebdomadaire (week=X) : tous les articles d'une semaine ISO donnée.
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
    """Retourne les articles d'une semaine ISO depuis la DB, triés par score desc."""
    rows = (
        db.query(ArticleModel)
        .filter(ArticleModel.collection_week == week)
        .order_by(ArticleModel.score.desc())
        .all()
    )
    return [_to_dto(row) for row in rows]


def get_unsent_articles(db: Session, limit: int = 10) -> list[PipelineArticle]:
    """Retourne les N articles les plus pertinents jamais envoyés dans une newsletter."""
    sent_logs = (
        db.query(NewsletterLog.article_ids)
        .filter(NewsletterLog.status == "sent")
        .all()
    )
    sent_ids: set[int] = {aid for (ids,) in sent_logs for aid in (ids or [])}

    query = db.query(ArticleModel).order_by(ArticleModel.score.desc())
    if sent_ids:
        query = query.filter(ArticleModel.id.notin_(sent_ids))

    return [_to_dto(row) for row in query.limit(limit).all()]


def send_newsletter(
    week: str | None = None,
    extra_recipients: list[str] | None = None,
    limit: int | None = None,
    prod: bool = False,
) -> dict:
    """Envoie la newsletter.

    Args:
        week:  semaine ISO cible (mode hebdo). Ignoré si limit est fourni.
        extra_recipients: destinataires supplémentaires (s'ajoutent au .env).
        limit: mode quotidien — envoie les N articles les plus pertinents
               jamais encore envoyés.

    Returns:
        {"week": str, "articles_sent": int, "sent": bool, "recipients": list[str]}
    """
    config = Config.load()
    db = SessionLocal()
    try:
        if limit is not None:
            articles_rows = _load_unsent_rows(db, limit)
            article_ids = [r.id for r in articles_rows]
            articles = [_to_dto(r) for r in articles_rows]
            label = current_week()
        else:
            target_week = week or current_week()
            rows = (
                db.query(ArticleModel)
                .filter(ArticleModel.collection_week == target_week)
                .order_by(ArticleModel.score.desc())
                .all()
            )
            article_ids = [r.id for r in rows]
            articles = [_to_dto(r) for r in rows]
            label = target_week

        if not articles:
            logger.warning("Newsletter %s — aucun article à envoyer.", label)
            return {"week": label, "articles_sent": 0, "sent": False, "recipients": []}

        base = config.newsletter_recipients if prod else config.email_recipients
        all_recipients = list(dict.fromkeys(base + (extra_recipients or [])))

        if not config.email_sender or not config.email_password or not all_recipients:
            logger.warning(
                "Newsletter %s — %d articles trouvés mais email non configuré.",
                label, len(articles),
            )
            return {"week": label, "articles_sent": len(articles), "sent": False, "recipients": []}

        all_texts = [f"{a.title} {a.summary}" for a in articles]
        word_freq = count_term_frequencies(all_texts, top_n=30)

        mailer = Mailer(config.email_sender, config.email_password, all_recipients)
        try:
            mailer.send(articles, lookback_days=config.lookback_days, word_freq=word_freq)
        except Exception as exc:
            _log_send(db, label, all_recipients, len(articles), "error", str(exc), article_ids)
            raise

        _log_send(db, label, all_recipients, len(articles), "sent", article_ids=article_ids)
        logger.info(
            "Newsletter %s envoyée à %d destinataire(s) — %d articles.",
            label, len(all_recipients), len(articles),
        )
        return {"week": label, "articles_sent": len(articles), "sent": True, "recipients": all_recipients}
    finally:
        db.close()


def _load_unsent_rows(db: Session, limit: int) -> list[ArticleModel]:
    sent_logs = (
        db.query(NewsletterLog.article_ids)
        .filter(NewsletterLog.status == "sent")
        .all()
    )
    sent_ids: set[int] = {aid for (ids,) in sent_logs for aid in (ids or [])}
    query = db.query(ArticleModel).order_by(ArticleModel.score.desc())
    if sent_ids:
        query = query.filter(ArticleModel.id.notin_(sent_ids))
    return query.limit(limit).all()


def _log_send(
    db: Session,
    week: str,
    recipients: list[str],
    articles_count: int,
    status: str,
    error_message: str | None = None,
    article_ids: list[int] | None = None,
) -> None:
    entry = NewsletterLog(
        week=week,
        recipients=recipients,
        articles_count=articles_count,
        article_ids=article_ids or [],
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
