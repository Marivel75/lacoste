"""Client HTTP du frontend Streamlit vers l'API FastAPI.

Toutes les pages Streamlit passent exclusivement par ce module pour accéder
aux données — aucun accès direct à la base de données depuis le frontend.
Utilise httpx avec l'URL de base définie dans frontend/config.py.
"""

import httpx

from frontend.config import API_BASE_URL


def _get(path: str, params: dict | None = None) -> dict:
    with httpx.Client(base_url=API_BASE_URL, timeout=30) as client:
        response = client.get(path, params=params)
        response.raise_for_status()
        return response.json()


def health() -> dict:
    return _get("/health")


def get_weeks() -> list[str]:
    return _get("/weeks")


def get_articles(week: str | None = None, **filters) -> dict:
    params = {"week": week, **filters} if week else filters
    return _get("/articles", params=params)


def get_nlp_topics(week: str) -> dict:
    return _get("/nlp/topics", params={"week": week})


def get_nlp_sentiment(week: str) -> dict:
    return _get("/nlp/sentiment", params={"week": week})


def get_nlp_wordfreq(week: str, topic: str | None = None) -> dict:
    path = f"/nlp/wordfreq/{topic}" if topic else "/nlp/wordfreq"
    return _get(path, params={"week": week})


def get_nlp_timeline(weeks: int = 8) -> dict:
    return _get("/nlp/timeline", params={"weeks": weeks})


def get_newsletter_preview(week: str) -> str:
    return _get("/newsletter/preview", params={"week": week})


def send_newsletter(week: str, recipients: list[str] | None = None) -> dict:
    with httpx.Client(base_url=API_BASE_URL, timeout=30) as client:
        body = {"week": week}
        if recipients:
            body["recipients"] = recipients
        response = client.post("/newsletter/send", json=body)
        response.raise_for_status()
        return response.json()
