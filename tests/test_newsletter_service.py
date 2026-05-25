from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from src.models.article import Article as ArticleModel
from src.services.newsletter_service import get_articles_for_week, send_newsletter


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
    return row


def _cfg(recipients=None):
    return MagicMock(
        email_sender="sender@example.com",
        email_password="pwd",
        email_recipients=recipients or ["mikael@example.com"],
        lookback_days=7,
    )


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


class TestSendNewsletter:
    def test_no_articles_returns_not_sent(self):
        with (
            patch("src.services.newsletter_service.SessionLocal", return_value=MagicMock()),
            patch("src.services.newsletter_service.Config") as mock_cfg,
            patch("src.services.newsletter_service.get_articles_for_week", return_value=[]),
        ):
            mock_cfg.load.return_value = _cfg()
            result = send_newsletter("2026-W21")
        assert result == {"week": "2026-W21", "articles_sent": 0, "sent": False, "recipients": []}

    def test_email_not_configured_returns_not_sent(self):
        from tests.conftest import make_article

        with (
            patch("src.services.newsletter_service.SessionLocal", return_value=MagicMock()),
            patch("src.services.newsletter_service.Config") as mock_cfg,
            patch("src.services.newsletter_service.get_articles_for_week", return_value=[make_article()]),
        ):
            mock_cfg.load.return_value = MagicMock(
                email_sender="", email_password="", email_recipients=[], lookback_days=7,
            )
            result = send_newsletter("2026-W21")
        assert result["sent"] is False
        assert result["articles_sent"] == 1

    def test_sends_to_base_recipients(self):
        from tests.conftest import make_article

        with (
            patch("src.services.newsletter_service.SessionLocal", return_value=MagicMock()),
            patch("src.services.newsletter_service.Config") as mock_cfg,
            patch("src.services.newsletter_service.get_articles_for_week", return_value=[make_article()]),
            patch("src.services.newsletter_service.Mailer") as mock_mailer_cls,
        ):
            mock_cfg.load.return_value = _cfg(["mikael@example.com"])
            mock_mailer_cls.return_value = MagicMock()
            result = send_newsletter("2026-W21")

        assert result["sent"] is True
        assert result["recipients"] == ["mikael@example.com"]
        mock_mailer_cls.assert_called_once_with(
            "sender@example.com", "pwd", ["mikael@example.com"]
        )

    def test_extra_recipients_appended(self):
        from tests.conftest import make_article

        with (
            patch("src.services.newsletter_service.SessionLocal", return_value=MagicMock()),
            patch("src.services.newsletter_service.Config") as mock_cfg,
            patch("src.services.newsletter_service.get_articles_for_week", return_value=[make_article()]),
            patch("src.services.newsletter_service.Mailer") as mock_mailer_cls,
        ):
            mock_cfg.load.return_value = _cfg(["mikael@example.com"])
            mock_mailer_cls.return_value = MagicMock()
            result = send_newsletter("2026-W21", extra_recipients=["emma@example.com", "gabriel@example.com"])

        assert result["recipients"] == ["mikael@example.com", "emma@example.com", "gabriel@example.com"]
        mock_mailer_cls.assert_called_once_with(
            "sender@example.com", "pwd",
            ["mikael@example.com", "emma@example.com", "gabriel@example.com"],
        )

    def test_extra_recipients_deduplicated(self):
        from tests.conftest import make_article

        with (
            patch("src.services.newsletter_service.SessionLocal", return_value=MagicMock()),
            patch("src.services.newsletter_service.Config") as mock_cfg,
            patch("src.services.newsletter_service.get_articles_for_week", return_value=[make_article()]),
            patch("src.services.newsletter_service.Mailer") as mock_mailer_cls,
        ):
            mock_cfg.load.return_value = _cfg(["mikael@example.com"])
            mock_mailer_cls.return_value = MagicMock()
            # mikael est déjà dans les destinataires de base
            result = send_newsletter("2026-W21", extra_recipients=["mikael@example.com", "emma@example.com"])

        assert result["recipients"] == ["mikael@example.com", "emma@example.com"]
