import logging
from pathlib import Path

from .config import Config
from .fetcher import SourceFetcher
from .filter import KeywordFilter
from .exporter import CSVExporter
from .mailer import Mailer
import json
from .nlp import analyse_article, count_term_frequencies

logger = logging.getLogger(__name__)


class VeillePipeline:

    def __init__(self, config: Config):
        self.config = config
        self.fetcher = SourceFetcher()
        self.filter = KeywordFilter(config.keywords)
        self.exporter = CSVExporter(config.data_dir)
        self.mailer = (
            Mailer(config.email_sender, config.email_password, config.email_recipients)
            if config.email_enabled else None
        )

    def run(self) -> Path:
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
        self._save_word_freq(word_freq)

        logger.info("--- Export CSV ---")
        path = self.exporter.export(filtered)

        if self.mailer:
            logger.info("--- Envoi email ---")
            self.mailer.send(filtered, self.config.lookback_days, word_freq)
        else:
            logger.info("Email désactivé (EMAIL_SENDER / EMAIL_PASSWORD / EMAIL_RECIPIENTS non configurés)")

        logger.info("=== Terminé : %d articles exportés → %s ===", len(filtered), path)
        return path

    def _save_word_freq(self, word_freq: dict) -> None:
        from datetime import datetime, timezone
        week = datetime.now(tz=timezone.utc).strftime("%Y-W%W")
        path = self.config.data_dir / f"wordfreq_{week}.json"
        self.config.data_dir.mkdir(exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(word_freq, f, ensure_ascii=False, indent=2)
        logger.info("Fréquences de mots sauvegardées : %s", path)
