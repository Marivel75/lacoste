from src.pipeline.models import Article as PipelineArticle
from src.services.article_service import upsert_articles

WEEK = "2026-W21"


def _art(url="https://example.com/1", title="Article test") -> PipelineArticle:
    return PipelineArticle(title=title, url=url, source="Source", category="presse")


def test_inserts_new_articles(db):
    fetched, new = upsert_articles(db, [_art()], WEEK)
    assert fetched == 1
    assert new == 1


def test_deduplicates_by_url(db):
    upsert_articles(db, [_art()], WEEK)
    fetched, new = upsert_articles(db, [_art()], WEEK)
    assert fetched == 1
    assert new == 0


def test_empty_list(db):
    fetched, new = upsert_articles(db, [], WEEK)
    assert fetched == 0
    assert new == 0


def test_partial_dedup(db):
    upsert_articles(db, [_art("https://example.com/1")], WEEK)
    fetched, new = upsert_articles(
        db,
        [_art("https://example.com/1"), _art("https://example.com/2")],
        WEEK,
    )
    assert fetched == 2
    assert new == 1


def test_maps_fields_correctly(db):
    from src.models.article import Article as ArticleModel

    art = PipelineArticle(
        title="Test titre",
        url="https://example.com/champ",
        source="Le Monde",
        category="presse",
        summary="Un résumé",
        score=3,
        matched_keywords=["dpe", "rénovation"],
        nlp_keywords=["isolation"],
        topics=["dpe_audit"],
        sentiment_score=0.5,
        sentiment_label="positive",
    )
    upsert_articles(db, [art], WEEK)
    row = db.query(ArticleModel).filter_by(url=art.url).one()
    assert row.title == "Test titre"
    assert row.source_name == "Le Monde"
    assert row.score == 3
    assert row.keywords == ["dpe", "rénovation"]
    assert row.topics == ["dpe_audit"]
    assert row.sentiment_label == "positive"
    assert row.collection_week == WEEK
