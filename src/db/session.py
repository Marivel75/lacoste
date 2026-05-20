"""Connexion à la base de données.

Crée l'engine SQLAlchemy et la factory de sessions (SessionLocal) à partir
de la variable d'environnement DATABASE_URL.
Défaut : SQLite local (data/lacoste.db). Passe à PostgreSQL en prod via DATABASE_URL.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/lacoste.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
