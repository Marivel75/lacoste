"""Service de journalisation des runs de collecte.

Crée un enregistrement CollectionRun après chaque exécution du pipeline.
Permet de détecter une semaine manquante ou un run en anomalie depuis
l'interface d'administration.
"""

from sqlalchemy.orm import Session

from src.models.collection_run import CollectionRun


def log_run(
    db: Session,
    week: str,
    articles_fetched: int,
    articles_new: int,
    status: str,
    error_message: str | None = None,
) -> CollectionRun:
    """Persiste le résultat d'un run et retourne l'objet créé."""
    run = CollectionRun(
        week=week,
        articles_fetched=articles_fetched,
        articles_new=articles_new,
        status=status,
        error_message=error_message,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run
