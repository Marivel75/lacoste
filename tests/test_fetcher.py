from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.fetcher import SourceFetcher


@pytest.fixture
def fetcher():
    return SourceFetcher()


class TestParseDate:
    def test_iso_string(self, fetcher):
        result = fetcher._parse_date("2026-01-15T10:00:00+00:00")
        assert isinstance(result, datetime)

    def test_rfc2822_string(self, fetcher):
        result = fetcher._parse_date("Mon, 15 Jan 2026 10:00:00 +0000")
        assert isinstance(result, datetime)

    def test_struct_time(self, fetcher):
        import time
        t = time.strptime("2026-01-15", "%Y-%m-%d")
        result = fetcher._parse_date(t)
        assert isinstance(result, datetime)
        assert result.year == 2026
        assert result.month == 1

    def test_none_returns_none(self, fetcher):
        assert fetcher._parse_date(None) is None

    def test_empty_string_returns_none(self, fetcher):
        assert fetcher._parse_date("") is None

    def test_invalid_string_returns_none(self, fetcher):
        assert fetcher._parse_date("not-a-date") is None


class TestParseEntry:
    def test_valid_entry(self, fetcher):
        entry = {
            "title": "DPE : nouvelles règles en 2026",
            "link": "https://example.com/article",
            "summary": "Le diagnostic de performance énergétique évolue.",
            "published": "Mon, 15 Jan 2026 10:00:00 +0000",
        }
        article = fetcher._parse_entry(entry, "TestSource", "Presse")
        assert article is not None
        assert article.title == "DPE : nouvelles règles en 2026"
        assert article.url == "https://example.com/article"
        assert article.source == "TestSource"
        assert article.category == "Presse"

    def test_missing_title_returns_none(self, fetcher):
        entry = {"title": "", "link": "https://example.com/article"}
        assert fetcher._parse_entry(entry, "Source", "Cat") is None

    def test_missing_link_returns_none(self, fetcher):
        entry = {"title": "Article", "link": ""}
        assert fetcher._parse_entry(entry, "Source", "Cat") is None

    def test_html_summary_stripped(self, fetcher):
        entry = {
            "title": "Article",
            "link": "https://example.com",
            "summary": "<p>Texte <b>important</b></p>",
        }
        article = fetcher._parse_entry(entry, "Source", "Cat")
        assert "<p>" not in article.summary
        assert "important" in article.summary

    def test_summary_truncated_at_500(self, fetcher):
        entry = {
            "title": "Article",
            "link": "https://example.com",
            "summary": "x" * 600,
        }
        article = fetcher._parse_entry(entry, "Source", "Cat")
        assert len(article.summary) <= 500


class TestFetchAll:
    def test_deduplicates_urls(self, fetcher):
        entry = {
            "title": "Article dupliqué",
            "link": "https://example.com/article",
            "summary": "Texte.",
        }
        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = [entry, entry]

        with patch("feedparser.parse", return_value=mock_feed):
            sources = [
                {"name": "Source A", "type": "rss", "url": "https://a.com/feed", "category": "Presse"},
                {"name": "Source B", "type": "rss", "url": "https://b.com/feed", "category": "Presse"},
            ]
            articles = fetcher.fetch_all(sources)

        urls = [a.url for a in articles]
        assert len(urls) == len(set(urls))

    def test_unsupported_source_type_skipped(self, fetcher):
        sources = [{"name": "Bad", "type": "unknown", "url": "https://x.com"}]
        articles = fetcher.fetch_all(sources)
        assert articles == []
