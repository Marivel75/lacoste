"""Modèle SQLAlchemy pour la table newsletter_picks.

Stocke les surcharges manuelles de la sélection automatique :
- action 'pin'     → forcer l'inclusion d'un article dans la newsletter
- action 'exclude' → forcer l'exclusion d'un article
Les picks sont appliqués en priorité sur le top-6 automatique par thématique.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class NewsletterPick(Base):
    __tablename__ = "newsletter_picks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    week: Mapped[str] = mapped_column(String, nullable=False, index=True)
    article_id: Mapped[int] = mapped_column(Integer, ForeignKey("articles.id"), nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)  # pin | exclude
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
    )

    article = relationship("Article", lazy="joined")

    def __repr__(self) -> str:
        return f"<NewsletterPick week={self.week} action={self.action} article_id={self.article_id}>"
