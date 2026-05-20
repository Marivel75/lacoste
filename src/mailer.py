"""Génération et envoi de la newsletter par email (SMTP Gmail).

Construit le HTML de la newsletter (articles groupés par catégorie, nuage de mots)
et l'envoie via SMTP SSL. Sera migré vers src/services/newsletter_service.py
lors de l'implémentation de la carte [Lacoste] Service newsletter.
"""

import logging
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.pipeline.models import Article

from .nlp import sentiment_badge_html, topic_badges_html

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


class Mailer:

    def __init__(self, sender: str, password: str, recipients: list[str]):
        self.sender = sender
        self.password = password
        self.recipients = recipients

    def send(
        self,
        articles: list[Article],
        lookback_days: int = 7,
        word_freq: dict[str, int] | None = None,
    ) -> None:
        if not articles:
            logger.info("Aucun article à envoyer par email.")
            return
        subject = self._subject()
        html = self._build_html(articles, lookback_days, word_freq or {})
        msg = self._build_message(subject, html)
        self._send(msg)
        logger.info("Email envoyé à : %s", ", ".join(self.recipients))

    def _send(self, msg: MIMEMultipart) -> None:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
            server.login(self.sender, self.password)
            server.sendmail(self.sender, self.recipients, msg.as_string())

    def _build_message(self, subject: str, html: str) -> MIMEMultipart:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"Veille Rénovation <{self.sender}>"
        msg["To"] = ", ".join(self.recipients)
        msg.attach(MIMEText(html, "html", "utf-8"))
        return msg

    @staticmethod
    def _subject() -> str:
        week = datetime.now(tz=timezone.utc).strftime("W%W")
        date = datetime.now(tz=timezone.utc).strftime("%d/%m/%Y")
        return f"Veille Rénovation Énergétique — {week} ({date})"

    @staticmethod
    def _build_word_cloud_html(word_freq: dict[str, int]) -> str:
        if not word_freq:
            return ""
        max_count = max(word_freq.values()) or 1
        min_size, max_size = 11, 22
        words_html = ""
        for term, count in list(word_freq.items())[:28]:
            ratio = count / max_count
            size = round(min_size + ratio * (max_size - min_size))
            opacity = round(0.45 + ratio * 0.55, 2)
            words_html += (
                f'<span style="font-size:{size}px;color:#1a73e8;opacity:{opacity};'
                f'margin:3px 5px;display:inline-block;font-weight:{"600" if ratio > 0.6 else "400"}">'
                f'{term}</span>'
            )
        return f"""
        <div style="margin:20px 0 0">
          <h2 style="font-size:14px;color:#333;margin:0 0 10px;border-left:3px solid #1a73e8;padding-left:10px">
            Tendances de la semaine
          </h2>
          <div style="background:#fff;border-radius:6px;padding:14px 16px;
                      box-shadow:0 1px 3px rgba(0,0,0,.08);line-height:2">
            {words_html}
          </div>
        </div>"""

    @staticmethod
    def _build_html(
        articles: list[Article],
        lookback_days: int = 7,
        word_freq: dict[str, int] | None = None,
    ) -> str:
        by_category: dict[str, list[Article]] = {}
        for art in articles:
            by_category.setdefault(art.category, []).append(art)

        MAX_PER_CATEGORY = 6

        sections = ""
        for category, items in sorted(by_category.items()):
            shown = items[:MAX_PER_CATEGORY]
            remaining = len(items) - len(shown)
            rows = "".join(
                _article_row(art)
                for art in shown
            )
            more_row = (
                f"""<tr><td colspan="3" style="padding:6px 12px;font-size:12px;color:#aaa;font-style:italic">
                  + {remaining} article{"s" if remaining > 1 else ""} supplémentaire{"s" if remaining > 1 else ""} dans le rapport complet
                </td></tr>"""
                if remaining > 0 else ""
            )
            sections += f"""
            <h2 style="font-size:15px;color:#333;margin:28px 0 8px;border-left:3px solid #1a73e8;padding-left:10px">{category}</h2>
            <table style="width:100%;border-collapse:collapse;background:#fff;border-radius:6px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08)">
              {rows}
              {more_row}
            </table>"""

        now = datetime.now(tz=timezone.utc)
        date_end = now.strftime("%d/%m/%Y")
        date_start = (now - timedelta(days=lookback_days)).strftime("%d/%m/%Y")
        week = now.strftime("semaine %W — %B %Y")
        word_cloud = Mailer._build_word_cloud_html(word_freq or {})

        return f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;background:#f5f5f5;padding:24px;color:#222">
  <div style="max-width:700px;margin:0 auto">
    <h1 style="font-size:20px;color:#1a73e8;margin-bottom:4px">Veille Rénovation Énergétique</h1>
    <p style="color:#888;font-size:13px;margin-top:0">{week} · {len(articles)} articles · collecte du {date_start} au {date_end}</p>
    <p style="font-size:12px;color:#999;background:#f0f0f0;border-radius:4px;padding:8px 12px;margin:12px 0 0">
      <strong style="color:#666">Score de pertinence</strong> — chaque article est noté selon le nombre de mots-clés détectés dans son titre et son résumé.
      Un mot-clé présent dans le <strong>titre</strong> compte <strong>2 points</strong> ; dans le résumé uniquement, <strong>1 point</strong>.
      Les articles sont triés par score décroissant au sein de chaque rubrique.
    </p>
    {word_cloud}
    {sections}
    <p style="font-size:11px;color:#bbb;margin-top:32px;text-align:center">
      Généré automatiquement par veille-renovation
    </p>
  </div>
</body>
</html>"""


def _article_row(art: Article) -> str:
    topics_html = topic_badges_html(art.topics)
    sentiment_html = sentiment_badge_html(art.sentiment_label, art.sentiment_score)
    kw_html = " ".join(
        f'<span style="background:#e8f0fe;color:#1a73e8;padding:1px 6px;'
        f'border-radius:4px;font-size:11px">{kw}</span>'
        for kw in art.nlp_keywords[:4]
    )
    meta_line = " &nbsp;".join(filter(None, [topics_html, kw_html]))
    score_cell = f'<div style="color:#aaa;font-size:12px">score {art.score}</div>'
    if sentiment_html:
        score_cell += f'<div style="margin-top:2px">{sentiment_html}</div>'
    return f"""
    <tr>
      <td style="padding:8px 12px;border-bottom:1px solid #f0f0f0;color:#555;font-size:13px;white-space:nowrap;vertical-align:top">{art.source}</td>
      <td style="padding:8px 12px;border-bottom:1px solid #f0f0f0;vertical-align:top">
        <a href="{art.url}" style="color:#1a73e8;text-decoration:none;font-size:14px">{art.title}</a>
        <div style="margin-top:4px;font-size:12px;color:#888">{", ".join(art.matched_keywords)}</div>
        <div style="margin-top:5px">{meta_line}</div>
      </td>
      <td style="padding:8px 12px;border-bottom:1px solid #f0f0f0;white-space:nowrap;text-align:right;vertical-align:top">{score_cell}</td>
    </tr>"""
