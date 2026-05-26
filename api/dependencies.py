"""Dépendances FastAPI injectées dans les routers.

get_db() fournit une session SQLAlchemy par requête via le système d'injection
de dépendances de FastAPI (Depends). La session est fermée automatiquement
après chaque requête, qu'elle réussisse ou échoue.
"""

from collections.abc import Generator

from sqlalchemy.orm import Session

from src.db.session import SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
