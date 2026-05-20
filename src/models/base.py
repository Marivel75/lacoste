"""Base déclarative SQLAlchemy partagée par tous les modèles ORM."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
