from datetime import datetime, timedelta, timezone

import pytest

from src.filter import KeywordFilter
from tests.conftest import make_article

KEYWORDS = ["dpe", "rénovation énergétique", "maprimerénov", "passoire thermique"]


@pytest.fixture
def kf():
    return KeywordFilter(KEYWORDS)


class TestScore:
    def test_keyword_in_title_scores_double(self, kf):
        art = make_article(title="Le DPE évolue en 2026", summary="")
        score, matched = kf._score(art)
        assert score == 2
        assert "dpe" in matched

    def test_keyword_in_summary_only_scores_one(self, kf):
        art = make_article(title="Immobilier : nouvelles règles", summary="Le DPE change.")
        score, matched = kf._score(art)
        assert score == 1
        assert "dpe" in matched

    def test_keyword_in_title_and_summary_scores_two(self, kf):
        art = make_article(title="DPE : ce qui change", summary="Le DPE est réformé.")
        score, matched = kf._score(art)
        assert score == 2
        assert matched.count("dpe") == 1  # dédupliqué

    def test_multi_keyword_scores_accumulate(self, kf):
        art = make_article(
            title="DPE et rénovation énergétique",
            summary="Aide maprimerénov disponible.",
        )
        score, matched = kf._score(art)
        assert score >= 5  # dpe×2 + rénovation énergétique×2 + maprimerénov×1
        assert len(matched) == 3

    def test_no_keyword_scores_zero(self, kf):
        art = make_article(title="Tour Eiffel rénovée", summary="Travaux terminés.")
        score, matched = kf._score(art)
        assert score == 0
        assert matched == []


class TestFilter:
    def test_excludes_below_min_score(self, kf):
        articles = [
            make_article(title="Article sans mot-clé"),
            make_article(title="DPE article"),
        ]
        results = kf.filter(articles, min_score=1)
        assert len(results) == 1
        assert results[0].title == "DPE article"

    def test_excludes_old_articles(self, kf):
        old = make_article(
            title="DPE ancien article",
            published=datetime.now(tz=timezone.utc) - timedelta(days=30),
        )
        recent = make_article(title="DPE récent")
        results = kf.filter([old, recent], min_score=1, lookback_days=7)
        assert len(results) == 1
        assert results[0].title == "DPE récent"

    def test_article_without_date_passes(self, kf):
        art = make_article(title="DPE sans date", published=None)
        art.published = None
        results = kf.filter([art], min_score=1)
        assert len(results) == 1

    def test_results_sorted_by_score_desc(self, kf):
        low = make_article(title="DPE info", summary="")
        high = make_article(title="DPE rénovation énergétique passoire thermique", summary="")
        results = kf.filter([low, high], min_score=1)
        assert results[0].score >= results[1].score

    def test_score_stored_on_article(self, kf):
        art = make_article(title="DPE article")
        results = kf.filter([art], min_score=1)
        assert results[0].score == 2

    def test_empty_list_returns_empty(self, kf):
        assert kf.filter([], min_score=1) == []


class TestIsRecent:
    def test_recent_article_passes(self, kf):
        art = make_article(published=datetime.now(tz=timezone.utc) - timedelta(days=3))
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=7)
        assert kf._is_recent(art, cutoff) is True

    def test_old_article_excluded(self, kf):
        art = make_article(published=datetime.now(tz=timezone.utc) - timedelta(days=10))
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=7)
        assert kf._is_recent(art, cutoff) is False

    def test_naive_datetime_handled(self, kf):
        art = make_article(published=datetime.now(tz=timezone.utc).replace(tzinfo=None) - timedelta(days=3))
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=7)
        assert kf._is_recent(art, cutoff) is True
