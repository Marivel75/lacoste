"""Client HTTP du frontend Streamlit vers l'API FastAPI.

Toutes les pages Streamlit passent exclusivement par ce module pour accéder
aux données — aucun accès direct à la base de données depuis le frontend.
"""

import httpx

from frontend.config import API_BASE_URL


class APIError(Exception):
    pass


def _get(path: str, params: dict | None = None):
    try:
        with httpx.Client(base_url=API_BASE_URL, timeout=30) as client:
            r = client.get(path, params={k: v for k, v in (params or {}).items() if v is not None})
            r.raise_for_status()
            return r.json()
    except httpx.ConnectError:
        raise APIError("API non accessible — lancez `make api` dans un autre terminal.")
    except httpx.HTTPStatusError as exc:
        raise APIError(f"Erreur API {exc.response.status_code} : {exc.response.text}")


def _post(path: str, body: dict | None = None):
    try:
        with httpx.Client(base_url=API_BASE_URL, timeout=120) as client:
            r = client.post(path, json=body or {})
            r.raise_for_status()
            return r.json()
    except httpx.ConnectError:
        raise APIError("API non accessible — lancez `make api` dans un autre terminal.")
    except httpx.HTTPStatusError as exc:
        raise APIError(f"Erreur API {exc.response.status_code} : {exc.response.text}")


def health() -> dict:
    return _get("/health")


def get_weeks() -> list[dict]:
    return _get("/weeks/")


def get_articles(
    week: str | None = None,
    source: str | None = None,
    category: str | None = None,
    min_score: int = 0,
    limit: int = 200,
) -> list[dict]:
    return _get("/articles/", params={
        "week": week,
        "source": source,
        "category": category,
        "min_score": min_score if min_score > 0 else None,
        "limit": limit,
    })


def trigger_collect(days: int = 7, min_score: int = 1) -> dict:
    return _post("/pipeline/collect", {"days": days, "min_score": min_score})


def send_newsletter(week: str | None = None, extra_recipients: list[str] | None = None) -> dict:
    return _post("/newsletter/send", {
        "week": week,
        "extra_recipients": extra_recipients or [],
    })


def get_newsletter_logs() -> list[dict]:
    return _get("/newsletter/logs")
