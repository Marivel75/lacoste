"""Tests des routers FastAPI — articles, weeks, newsletter/logs."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Importe tous les modèles AVANT create_all pour qu'ils soient enregistrés dans Base.metadata
import src.models  # noqa: F401 — enregistre Article, CollectionRun, NewsletterLog, NewsletterPick
from api.dependencies import get_db
from api.main import app
from src.models.article import Article
from src.models.base import Base
from src.models.collection_run import CollectionRun
from src.models.newsletter_log import NewsletterLog

# ── DB de test en mémoire ──────────────────────────────────────────────────────
# StaticPool : connexion unique partagée — l'état en mémoire persiste entre sessions.

_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_Session = sessionmaker(bind=_engine)
Base.metadata.create_all(_engine)


def _override_get_db():
    db = _Session()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db
client = TestClient(app)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clean_db():
    """Vide les tables entre chaque test via DELETE sur toutes les tables."""
    yield
    db = _Session()
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()
    db.close()


def _insert_article(week="2026-W22", score=3, url="https://ex.com/1", category="Presse"):
    db = _Session()
    row = Article(
        url=url,
        title="Titre test",
        source_name="ADEME",
        source_category=category,
        summary="Résumé.",
        score=score,
        keywords=["DPE"],
        nlp_keywords=["dpe"],
        topics=["réglementation"],
        sentiment_score=0.1,
        sentiment_label="positif",
        collection_week=week,
        collected_at=datetime.now(tz=timezone.utc),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    article_id = row.id
    db.close()
    return article_id


def _insert_run(week="2026-W22", status="success", articles_new=10):
    db = _Session()
    run = CollectionRun(
        week=week,
        articles_fetched=45,
        articles_new=articles_new,
        status=status,
    )
    db.add(run)
    db.commit()
    db.close()


# ── /health ───────────────────────────────────────────────────────────────────

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ── /articles ─────────────────────────────────────────────────────────────────

class TestArticles:
    def test_list_empty(self):
        r = client.get("/articles/")
        assert r.status_code == 200
        assert r.json() == []

    def test_list_returns_articles(self):
        _insert_article(url="https://ex.com/1")
        _insert_article(url="https://ex.com/2")
        r = client.get("/articles/")
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_filter_by_week(self):
        _insert_article(week="2026-W22", url="https://ex.com/1")
        _insert_article(week="2026-W21", url="https://ex.com/2")
        r = client.get("/articles/?week=2026-W22")
        assert len(r.json()) == 1

    def test_filter_by_min_score(self):
        _insert_article(score=1, url="https://ex.com/low")
        _insert_article(score=5, url="https://ex.com/high")
        r = client.get("/articles/?min_score=3")
        assert len(r.json()) == 1
        assert r.json()[0]["score"] == 5

    def test_filter_by_category(self):
        _insert_article(category="Presse", url="https://ex.com/1")
        _insert_article(category="Réglementation", url="https://ex.com/2")
        r = client.get("/articles/?category=Presse")
        assert len(r.json()) == 1

    def test_get_by_id(self):
        article_id = _insert_article()
        r = client.get(f"/articles/{article_id}")
        assert r.status_code == 200
        assert r.json()["id"] == article_id

    def test_get_by_id_not_found(self):
        r = client.get("/articles/9999")
        assert r.status_code == 404

    def test_sorted_by_score_desc(self):
        _insert_article(score=1, url="https://ex.com/low")
        _insert_article(score=5, url="https://ex.com/high")
        data = client.get("/articles/").json()
        assert data[0]["score"] >= data[1]["score"]


# ── /weeks ────────────────────────────────────────────────────────────────────

class TestWeeks:
    def test_list_empty(self):
        r = client.get("/weeks/")
        assert r.status_code == 200
        assert r.json() == []

    def test_list_weeks(self):
        _insert_article(week="2026-W22", url="https://ex.com/1")
        _insert_article(week="2026-W21", url="https://ex.com/2")
        r = client.get("/weeks/")
        weeks = [w["week"] for w in r.json()]
        assert "2026-W22" in weeks
        assert "2026-W21" in weeks

    def test_week_includes_run_stats(self):
        _insert_article(week="2026-W22")
        _insert_run(week="2026-W22", articles_new=12)
        r = client.get("/weeks/2026-W22")
        assert r.status_code == 200
        data = r.json()
        assert data["article_count"] == 1
        assert data["articles_new"] == 12
        assert data["status"] == "success"

    def test_week_not_found(self):
        r = client.get("/weeks/2099-W99")
        assert r.status_code == 404

    def test_weeks_sorted_desc(self):
        _insert_article(week="2026-W20", url="https://ex.com/1")
        _insert_article(week="2026-W22", url="https://ex.com/2")
        data = client.get("/weeks/").json()
        assert data[0]["week"] > data[1]["week"]


# ── /newsletter ───────────────────────────────────────────────────────────────

class TestNewsletter:
    def test_logs_empty(self):
        r = client.get("/newsletter/logs")
        assert r.status_code == 200
        assert r.json() == []

    def test_logs_returns_entries(self):
        db = _Session()
        db.add(NewsletterLog(
            week="2026-W22",
            recipients=["mikael@example.com"],
            articles_count=10,
            status="sent",
        ))
        db.commit()
        db.close()
        r = client.get("/newsletter/logs")
        assert len(r.json()) == 1
        assert r.json()[0]["status"] == "sent"

    def test_send_no_articles(self):
        with patch("api.routers.newsletter.send_newsletter") as mock_send:
            mock_send.return_value = {
                "week": "2026-W22", "articles_sent": 0, "sent": False, "recipients": []
            }
            r = client.post("/newsletter/send", json={"week": "2026-W22"})
        assert r.status_code == 200
        assert r.json()["sent"] is False

    def test_send_with_extra_recipients(self):
        with patch("api.routers.newsletter.send_newsletter") as mock_send:
            mock_send.return_value = {
                "week": "2026-W22", "articles_sent": 5, "sent": True,
                "recipients": ["mikael@example.com", "emma@example.com"],
            }
            r = client.post("/newsletter/send", json={
                "week": "2026-W22",
                "extra_recipients": ["emma@example.com"],
            })
        assert r.status_code == 200
        assert "emma@example.com" in r.json()["recipients"]
        mock_send.assert_called_once_with(
            "2026-W22", extra_recipients=["emma@example.com"]
        )
