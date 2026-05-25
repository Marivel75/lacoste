"""Orchestrateur du pipeline de veille.

Enchaîne : collecte RSS → filtrage par mots-clés → analyse NLP → écriture
en base + email optionnel. Chaque run est tracé dans collection_runs.
Point d'entrée : VeillePipeline(config).run().
"""

import json
import logging

from src.config import Config
from src.db.init_db import init_db
from src.db.session import SessionLocal
from src.mailer import Mailer
from src.pipeline.fetcher import SourceFetcher
from src.pipeline.filter import KeywordFilter
from src.pipeline.nlp import analyse_article, count_term_frequencies
from src.services.article_service import current_week, upsert_articles
from src.services.collection_run_service import log_run

logger = logging.getLogger(__name__)


class VeillePipeline:

    def __init__(self, config: Config):
        init_db()
        self.config = config
        self.fetcher = SourceFetcher()
        self.filter = KeywordFilter(config.keywords)
        self.mailer = (
            Mailer(config.email_sender, config.email_password, config.email_recipients)
            if config.email_enabled else None
        )

    def run(self) -> dict:
        """Exécute le pipeline complet et retourne un résumé du run."""
        week = current_week()
        db = SessionLocal()
        articles_fetched = 0
        articles_new = 0

        try:
            logger.info("=== Veille Rénovation — collecte sur %d jours ===", self.config.lookback_days)

            logger.info("--- Récupération des articles (%d sources) ---", len(self.config.sources))
            articles = self.fetcher.fetch_all(self.config.sources)

            logger.info("--- Filtrage par mots-clés (score min : %d) ---", self.config.min_score)
            filtered = self.filter.filter(
                articles,
                min_score=self.config.min_score,
                lookback_days=self.config.lookback_days,
            )

            logger.info("--- Analyse NLP ---")
            for art in filtered:
                result = analyse_article(art.title, art.summary)
                art.nlp_keywords = result["nlp_keywords"]
                art.topics = result["topics"]
                art.sentiment_score = result["sentiment_score"]
                art.sentiment_label = result["sentiment_label"]

            all_texts = [f"{a.title} {a.summary}" for a in articles]
            word_freq = count_term_frequencies(all_texts, top_n=30)
            self._save_word_freq(word_freq, week)

            logger.info("--- Écriture en base ---")
            articles_fetched, articles_new = upsert_articles(db, filtered, week)
            log_run(db, week, articles_fetched, articles_new, "success")

            if self.mailer:
                logger.info("--- Envoi email ---")
                self.mailer.send(filtered, self.config.lookback_days, word_freq)
            else:
                logger.info("Email désactivé (EMAIL_SENDER / EMAIL_PASSWORD / EMAIL_RECIPIENTS non configurés)")

            logger.info(
                "=== Terminé : %d nouveaux / %d filtrés → %s ===",
                articles_new, articles_fetched, week,
            )
            return {"week": week, "fetched": articles_fetched, "new": articles_new}

        except Exception as exc:
            log_run(db, week, articles_fetched, articles_new, "error", str(exc))
            raise

        finally:
            db.close()

    def _save_word_freq(self, word_freq: dict, week: str) -> None:
        path = self.config.data_dir / f"wordfreq_{week}.json"
        self.config.data_dir.mkdir(exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(word_freq, f, ensure_ascii=False, indent=2)
        logger.info("Fréquences de mots sauvegardées : %s", path)
