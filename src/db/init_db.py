"""Initialisation du schéma de base de données.

Appelle Base.metadata.create_all() pour créer toutes les tables si elles n'existent
pas encore. Idempotent : sans effet si les tables sont déjà présentes.
Utilisé au démarrage de l'API (lifespan) et via `python main.py initdb`.
"""

import logging

import src.models.article  # noqa: F401
import src.models.collection_run  # noqa: F401
import src.models.newsletter_log  # noqa: F401
import src.models.newsletter_pick  # noqa: F401
from src.db.session import engine
from src.models import (
    Base,  # noqa: F401 — importe tous les modèles pour que SQLAlchemy les enregistre
)

logger = logging.getLogger(__name__)


def init_db() -> None:
    logger.info("Initialisation de la base de données...")
    Base.metadata.create_all(bind=engine)
    logger.info("Tables créées (ou déjà existantes).")
