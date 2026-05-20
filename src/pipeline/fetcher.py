"""Récupération des flux RSS.

Parse chaque source configurée via feedparser, nettoie le HTML des résumés
et retourne une liste d'Article (dataclass pipeline). Déduplique les URLs
au sein d'un même appel à fetch_all.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import feedparser
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from src.pipeline.models import Article

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; veille-renovation/1.0; "
        "+https://github.com/optimmo-energies/veille-renovation)"
    )
}


class SourceFetcher:

    def fetch_all(self, sources: list[dict]) -> list[Article]:
        articles: list[Article] = []
        seen_urls: set[str] = set()
        for source in sources:
            for article in self._fetch_source(source):
                if article.url not in seen_urls:
                    seen_urls.add(article.url)
                    articles.append(article)
        logger.info("Total brut : %d articles uniques", len(articles))
        return articles

    def _fetch_source(self, source: dict) -> list[Article]:
        source_type = source.get("type", "rss")
        if source_type == "rss":
            return self._fetch_rss(
                name=source["name"],
                url=source["url"],
                category=source.get("category", "Actualité"),
            )
        logger.warning("Type de source non supporté : %s (%s)", source_type, source["name"])
        return []

    def _fetch_rss(self, name: str, url: str, category: str) -> list[Article]:
        articles = []
        try:
            feed = feedparser.parse(url, request_headers=HEADERS)
            if feed.bozo and not feed.entries:
                status = getattr(feed, "status", "?")
                reason = str(feed.bozo_exception) if hasattr(feed, "bozo_exception") else "inconnu"
                logger.warning("RSS inaccessible [%s] : %s — %s", status, url, reason)
                return articles
            for entry in feed.entries:
                article = self._parse_entry(entry, name, category)
                if article:
                    articles.append(article)
        except Exception as exc:
            logger.error("Erreur fetch %s : %s", name, exc)
        logger.info("  %-40s → %d articles", name, len(articles))
        return articles

    def _parse_entry(self, entry: dict, source: str, category: str) -> Optional[Article]:
        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()
        if not title or not link:
            return None
        summary = BeautifulSoup(
            entry.get("summary", entry.get("description", "")), "html.parser"
        ).get_text(" ", strip=True)[:500]
        published = self._parse_date(
            entry.get("published") or entry.get("updated")
            or entry.get("published_parsed") or entry.get("updated_parsed")
        )
        return Article(
            title=title,
            url=link,
            source=source,
            category=category,
            summary=summary,
            published=published,
        )

    @staticmethod
    def _parse_date(value) -> Optional[datetime]:
        if not value:
            return None
        if isinstance(value, str):
            try:
                return dateparser.parse(value, ignoretz=False)
            except Exception:
                return None
        try:
            return datetime(*value[:6], tzinfo=timezone.utc)
        except Exception:
            return None
