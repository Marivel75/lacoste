import logging
import os
from datetime import datetime, timezone
from notion_client import Client
from notion_client.errors import APIResponseError

from .fetcher import Article

logger = logging.getLogger(__name__)

# Propriétés attendues dans la base Notion
NOTION_DB_PROPERTIES = {
    "Titre": {"title": {}},
    "Source": {"select": {}},
    "Catégorie": {
        "select": {
            "options": [
                {"name": "Actualité", "color": "blue"},
                {"name": "Étude/Rapport", "color": "green"},
                {"name": "Réglementation", "color": "orange"},
                {"name": "Aide", "color": "yellow"},
                {"name": "Institution", "color": "purple"},
                {"name": "Presse", "color": "gray"},
            ]
        }
    },
    "Date de publication": {"date": {}},
    "URL": {"url": {}},
    "Résumé": {"rich_text": {}},
    "Mots-clés": {"multi_select": {}},
    "Score": {"number": {}},
    "Statut": {
        "select": {
            "options": [
                {"name": "À lire", "color": "red"},
                {"name": "Lu", "color": "green"},
                {"name": "Archivé", "color": "gray"},
            ]
        }
    },
    "Semaine de collecte": {"date": {}},
}


def _get_client() -> Client:
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        raise ValueError("NOTION_TOKEN manquant dans les variables d'environnement")
    return Client(auth=token)


def setup_database(page_id: str) -> str:
    notion = _get_client()
    db = notion.databases.create(
        parent={"type": "page_id", "page_id": page_id},
        title=[{"type": "text", "text": {"content": "Veille Rénovation Énergétique"}}],
        properties=NOTION_DB_PROPERTIES,
    )
    db_id = db["id"]
    logger.info("Base Notion créée : %s", db_id)
    return db_id


def init_database(database_id: str) -> None:
    """Configure les propriétés sur une base de données Notion déjà existante."""
    notion = _get_client()
    # La propriété "title" existe déjà sous le nom par défaut — on exclut "Titre"
    props_to_add = {k: v for k, v in NOTION_DB_PROPERTIES.items() if k != "Titre"}
    notion.databases.update(database_id=database_id, properties=props_to_add)
    logger.info("Propriétés configurées sur la base %s", database_id)


def _get_existing_urls(notion: Client, database_id: str) -> set[str]:
    existing = set()
    cursor = None
    while True:
        kwargs = {
            "database_id": database_id,
            "filter": {"property": "URL", "url": {"is_not_empty": True}},
            "page_size": 100,
        }
        if cursor:
            kwargs["start_cursor"] = cursor
        resp = notion.databases.query(**kwargs)
        for page in resp.get("results", []):
            url_prop = page.get("properties", {}).get("URL", {})
            url = url_prop.get("url")
            if url:
                existing.add(url)
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")
    return existing


def _format_date(dt: datetime | None) -> dict | None:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return {"start": dt.isoformat()}


def _article_to_page(article: Article, database_id: str, collect_date: str) -> dict:
    title = article.title[:2000]
    summary = article.summary[:2000] if article.summary else ""
    keywords = [{"name": kw[:100]} for kw in article.matched_keywords[:10]]

    properties: dict = {
        "Titre": {"title": [{"text": {"content": title}}]},
        "Source": {"select": {"name": article.source[:100]}},
        "Catégorie": {"select": {"name": article.category}},
        "URL": {"url": article.url},
        "Score": {"number": article.score},
        "Statut": {"select": {"name": "À lire"}},
        "Semaine de collecte": {"date": {"start": collect_date}},
    }
    if summary:
        properties["Résumé"] = {"rich_text": [{"text": {"content": summary}}]}
    if keywords:
        properties["Mots-clés"] = {"multi_select": keywords}
    date_val = _format_date(article.published)
    if date_val:
        properties["Date de publication"] = {"date": date_val}
    return {"parent": {"database_id": database_id}, "properties": properties}


def push_articles(articles: list[Article], database_id: str) -> int:
    if not articles:
        return 0
    notion = _get_client()
    collect_date = datetime.now(tz=timezone.utc).date().isoformat()

    logger.info("Récupération des URLs déjà présentes dans Notion…")
    existing_urls = _get_existing_urls(notion, database_id)
    logger.info("  %d URLs existantes", len(existing_urls))

    new_articles = [a for a in articles if a.url not in existing_urls]
    logger.info("%d nouveaux articles à publier", len(new_articles))

    pushed = 0
    for art in new_articles:
        try:
            page = _article_to_page(art, database_id, collect_date)
            notion.pages.create(**page)
            pushed += 1
        except APIResponseError as exc:
            logger.error("Erreur Notion pour '%s' : %s", art.title[:60], exc)
    return pushed
