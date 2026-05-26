"""Tests du service newsletter — mode quotidien (limit) et hebdomadaire (week)."""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from src.models.article import Article as ArticleModel
from src.models.newsletter_log import NewsletterLog
from src.services.newsletter_service import (
    get_articles_for_week,
    get_unsent_articles,
    send_newsletter,
)


def _db_article(db, week="2026-W21", score=3, url="https://example.com/a1"):
    row = ArticleModel(
        url=url,
        title="DPE : nouvelles obligations",
        source_name="ADEME",
        source_category="Réglementation",
        summary="Résumé test.",
        score=score,
        keywords=["DPE"],
        nlp_keywords=["dpe", "rénovation"],
        topics=["réglementation"],
        sentiment_score=0.1,
        sentiment_label="positif",
        collection_week=week,
        collected_at=datetime.now(tz=timezone.utc),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _db_log(db, article_ids=None, week="2026-W21", status="sent"):
    """Insère un log d'envoi pour simuler des articles déjà envoyés."""
    log = NewsletterLog(
        week=week,
        recipients=["mikael@example.com"],
        articles_count=len(article_ids or []),
        article_ids=article_ids or [],
        status=status,
    )
    db.add(log)
    db.commit()
    return log


def _cfg(recipients=None):
    return MagicMock(
        email_sender="sender@example.com",
        email_password="pwd",
        email_recipients=recipients or ["mikael@example.com"],
        lookback_days=7,
    )


def _mock_row(id=1):
    """Mock d'un row ArticleModel minimal pour les tests d'envoi."""
    row = MagicMock()
    row.id = id
    row.published_at = None
    return row


def _weekly_mock_db(rows):
    """Mock session dont .query().filter().order_by().all() retourne rows."""
    mock = MagicMock()
    mock.query.return_value.filter.return_value.order_by.return_value.all.return_value = rows
    return mock


# ── TestGetArticlesForWeek ─────────────────────────────────────────────────────

class TestGetArticlesForWeek:
    def test_returns_empty_for_unknown_week(self, db):
        assert get_articles_for_week(db, "2026-W99") == []

    def test_returns_articles_for_week(self, db):
        _db_article(db, week="2026-W21", url="https://ex.com/1")
        _db_article(db, week="2026-W21", url="https://ex.com/2")
        result = get_articles_for_week(db, "2026-W21")
        assert len(result) == 2

    def test_ignores_other_weeks(self, db):
        _db_article(db, week="2026-W20", url="https://ex.com/old")
        _db_article(db, week="2026-W21", url="https://ex.com/new")
        result = get_articles_for_week(db, "2026-W21")
        assert len(result) == 1
        assert result[0].url == "https://ex.com/new"

    def test_sorted_by_score_desc(self, db):
        _db_article(db, week="2026-W21", score=1, url="https://ex.com/low")
        _db_article(db, week="2026-W21", score=5, url="https://ex.com/high")
        result = get_articles_for_week(db, "2026-W21")
        assert result[0].score == 5
        assert result[1].score == 1

    def test_dto_fields_mapped_correctly(self, db):
        _db_article(db, week="2026-W21", url="https://ex.com/a")
        article = get_articles_for_week(db, "2026-W21")[0]
        assert article.title == "DPE : nouvelles obligations"
        assert article.source == "ADEME"
        assert article.category == "Réglementation"
        assert article.matched_keywords == ["DPE"]
        assert article.nlp_keywords == ["dpe", "rénovation"]
        assert article.topics == ["réglementation"]
        assert article.sentiment_label == "positif"


# ── TestGetUnsentArticles ─────────────────────────────────────────────────────

class TestGetUnsentArticles:
    def test_returns_articles_sorted_by_score(self, db):
        _db_article(db, score=5, url="https://ex.com/1")
        _db_article(db, score=1, url="https://ex.com/2")
        _db_article(db, score=3, url="https://ex.com/3")
        result = get_unsent_articles(db, limit=10)
        assert [a.score for a in result] == [5, 3, 1]

    def test_respects_limit(self, db):
        for i in range(5):
            _db_article(db, url=f"https://ex.com/{i}")
        result = get_unsent_articles(db, limit=2)
        assert len(result) == 2

    def test_excludes_previously_sent_ids(self, db):
        a1 = _db_article(db, score=5, url="https://ex.com/1")
        _db_article(db, score=3, url="https://ex.com/2")
        _db_log(db, article_ids=[a1.id])
        result = get_unsent_articles(db, limit=10)
        assert len(result) == 1
        assert result[0].url == "https://ex.com/2"

    def test_excludes_ids_from_multiple_logs(self, db):
        a1 = _db_article(db, score=5, url="https://ex.com/1")
        a2 = _db_article(db, score=4, url="https://ex.com/2")
        _db_article(db, score=3, url="https://ex.com/3")
        _db_log(db, article_ids=[a1.id])
        _db_log(db, article_ids=[a2.id])
        result = get_unsent_articles(db, limit=10)
        assert len(result) == 1
        assert result[0].url == "https://ex.com/3"

    def test_error_logs_do_not_block_articles(self, db):
        a1 = _db_article(db, url="https://ex.com/1")
        _db_log(db, article_ids=[a1.id], status="error")
        result = get_unsent_articles(db, limit=10)
        assert len(result) == 1

    def test_returns_empty_when_all_sent(self, db):
        a1 = _db_article(db, url="https://ex.com/1")
        _db_log(db, article_ids=[a1.id])
        result = get_unsent_articles(db, limit=10)
        assert result == []


# ── TestSendNewsletter ────────────────────────────────────────────────────────

class TestSendNewsletter:
    def test_no_articles_returns_not_sent(self):
        with (
            patch("src.services.newsletter_service.SessionLocal", return_value=MagicMock()),
            patch("src.services.newsletter_service.Config") as mock_cfg,
        ):
            mock_cfg.load.return_value = _cfg()
            result = send_newsletter("2026-W21")
        assert result == {"week": "2026-W21", "articles_sent": 0, "sent": False, "recipients": []}

    def test_email_not_configured_returns_not_sent(self):
        with (
            patch("src.services.newsletter_service.SessionLocal", return_value=_weekly_mock_db([_mock_row()])),
            patch("src.services.newsletter_service.Config") as mock_cfg,
        ):
            mock_cfg.load.return_value = MagicMock(
                email_sender="", email_password="", email_recipients=[], lookback_days=7,
            )
            result = send_newsletter("2026-W21")
        assert result["sent"] is False
        assert result["articles_sent"] == 1

    def test_sends_to_base_recipients(self):
        with (
            patch("src.services.newsletter_service.SessionLocal", return_value=_weekly_mock_db([_mock_row()])),
            patch("src.services.newsletter_service.Config") as mock_cfg,
            patch("src.services.newsletter_service.Mailer") as mock_mailer_cls,
        ):
            mock_cfg.load.return_value = _cfg(["mikael@example.com"])
            mock_mailer_cls.return_value = MagicMock()
            result = send_newsletter("2026-W21")
        assert result["sent"] is True
        assert result["recipients"] == ["mikael@example.com"]
        mock_mailer_cls.assert_called_once_with("sender@example.com", "pwd", ["mikael@example.com"])

    def test_extra_recipients_appended(self):
        with (
            patch("src.services.newsletter_service.SessionLocal", return_value=_weekly_mock_db([_mock_row()])),
            patch("src.services.newsletter_service.Config") as mock_cfg,
            patch("src.services.newsletter_service.Mailer") as mock_mailer_cls,
        ):
            mock_cfg.load.return_value = _cfg(["mikael@example.com"])
            mock_mailer_cls.return_value = MagicMock()
            result = send_newsletter("2026-W21", extra_recipients=["emma@example.com", "gabriel@example.com"])
        assert result["recipients"] == ["mikael@example.com", "emma@example.com", "gabriel@example.com"]

    def test_extra_recipients_deduplicated(self):
        with (
            patch("src.services.newsletter_service.SessionLocal", return_value=_weekly_mock_db([_mock_row()])),
            patch("src.services.newsletter_service.Config") as mock_cfg,
            patch("src.services.newsletter_service.Mailer") as mock_mailer_cls,
        ):
            mock_cfg.load.return_value = _cfg(["mikael@example.com"])
            mock_mailer_cls.return_value = MagicMock()
            result = send_newsletter("2026-W21", extra_recipients=["mikael@example.com", "emma@example.com"])
        assert result["recipients"] == ["mikael@example.com", "emma@example.com"]

    # ── Mode quotidien (limit) ────────────────────────────────────────────────

    def test_daily_mode_sends_limit_articles(self):
        with (
            patch("src.services.newsletter_service.SessionLocal", return_value=MagicMock()),
            patch("src.services.newsletter_service.Config") as mock_cfg,
            patch("src.services.newsletter_service._load_unsent_rows") as mock_load,
            patch("src.services.newsletter_service.Mailer") as mock_mailer_cls,
        ):
            mock_cfg.load.return_value = _cfg(["mikael@example.com"])
            mock_load.return_value = [_mock_row(1), _mock_row(2), _mock_row(3)]
            mock_mailer_cls.return_value = MagicMock()
            result = send_newsletter(limit=3)
        assert result["sent"] is True
        assert result["articles_sent"] == 3

    def test_daily_mode_no_articles_returns_not_sent(self):
        with (
            patch("src.services.newsletter_service.SessionLocal", return_value=MagicMock()),
            patch("src.services.newsletter_service.Config") as mock_cfg,
            patch("src.services.newsletter_service._load_unsent_rows", return_value=[]),
        ):
            mock_cfg.load.return_value = _cfg()
            result = send_newsletter(limit=10)
        assert result["sent"] is False
        assert result["articles_sent"] == 0

    def test_daily_mode_stores_article_ids_in_log(self):
        with (
            patch("src.services.newsletter_service.SessionLocal", return_value=MagicMock()),
            patch("src.services.newsletter_service.Config") as mock_cfg,
            patch("src.services.newsletter_service._load_unsent_rows") as mock_load,
            patch("src.services.newsletter_service.Mailer") as mock_mailer_cls,
            patch("src.services.newsletter_service._log_send") as mock_log,
        ):
            mock_cfg.load.return_value = _cfg(["mikael@example.com"])
            mock_load.return_value = [_mock_row(10), _mock_row(20)]
            mock_mailer_cls.return_value = MagicMock()
            send_newsletter(limit=2)
        assert mock_log.call_args.kwargs["article_ids"] == [10, 20]
