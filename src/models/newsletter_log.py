"""Modèle SQLAlchemy pour la table newsletter_logs.

Historique de chaque envoi de newsletter : semaine, destinataires, nombre
d'articles inclus, statut (sent/error). Évite les doublons d'envoi et permet
le suivi depuis la page Newsletter du Streamlit.
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class NewsletterLog(Base):
    __tablename__ = "newsletter_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    week: Mapped[str] = mapped_column(String, nullable=False, index=True)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
    )
    recipients: Mapped[list] = mapped_column(JSON, default=list)
    articles_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, nullable=False)  # sent | error
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<NewsletterLog week={self.week} status={self.status} count={self.articles_count}>"
