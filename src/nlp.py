"""Analyse NLP des articles : mots-clés TF-IDF, topics, sentiment VADER."""

from __future__ import annotations

import logging
import re
import string
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stopwords français
# ---------------------------------------------------------------------------

_FR_STOPWORDS: frozenset[str] = frozenset([
    "le", "la", "les", "un", "une", "des", "de", "du", "en", "et", "est",
    "que", "qui", "dans", "au", "aux", "ce", "se", "sur", "par", "pour",
    "plus", "avec", "mais", "ou", "pas", "ne", "si", "son", "sa", "ses",
    "ils", "elles", "nous", "vous", "on", "leur", "leurs", "cet", "cette",
    "ces", "dont", "où", "car", "donc", "or", "ni", "car", "lui", "y",
    "être", "avoir", "faire", "tout", "très", "bien", "aussi", "comme",
    "plus", "moins", "même", "encore", "après", "avant", "entre", "sous",
    "lors", "dès", "selon", "vers", "depuis", "jusqu", "contre", "sans",
    "alors", "ainsi", "toujours", "déjà", "encore", "notamment", "soit",
    "afin", "dont", "cela", "celui", "celle", "ceux", "celles", "qui",
    "quand", "comment", "pourquoi", "quoi", "quel", "quelle", "quels",
    "quelles", "plusieurs", "chaque", "autre", "autres", "certains",
    "aucun", "aucune", "tous", "toutes", "rien", "quelques", "peu",
    "beaucoup", "trop", "tant", "tel", "telle", "tels", "telles",
    "lors", "an", "ans", "point", "liés", "lié", "peut", "va",
    "ont", "été", "fait", "faut", "dit", "mis", "via",
])

# ---------------------------------------------------------------------------
# Taxonomie de topics (rénovation énergétique)
# ---------------------------------------------------------------------------

_TOPIC_KEYWORDS: list[tuple[str, list[str]]] = [
    (
        "aides_financières",
        [
            "maprimerénov", "maprimerenov", "mpr", "cee", "éco-ptz", "eco-ptz",
            "anah", "subvention", "prime", "aide financière", "crédit d'impôt",
            "cite", "habiter mieux", "action logement", "dispositif",
        ],
    ),
    (
        "dpe_audit",
        [
            "dpe", "diagnostic de performance", "audit énergétique", "audit energetique",
            "étiquette énergétique", "classe énergie", "passoire thermique",
            "passoire énergétique", "classe f", "classe g", "classe e",
            "logement énergivore", "bilan thermique",
        ],
    ),
    (
        "réglementation",
        [
            "loi", "décret", "arrêté", "re2020", "bbc", "réglementation",
            "obligation", "interdiction", "location", "bail", "copropriété",
            "norme", "label", "certification", "plan national",
        ],
    ),
    (
        "rénovation_geste",
        [
            "isolation", "pompe à chaleur", "pac", "chaudière", "vmc",
            "menuiserie", "fenêtre", "double vitrage", "combles", "plancher",
            "rge", "reconnu garant", "travaux", "rénovation globale",
            "chauffage", "ventilation",
        ],
    ),
    (
        "marché_immobilier",
        [
            "vente", "achat", "immobilier", "propriétaire", "locataire",
            "loyer", "prix", "transaction", "bien immobilier", "logement",
            "résidence", "parc immobilier",
        ],
    ),
    (
        "études_données",
        [
            "étude", "rapport", "baromètre", "statistique", "chiffre",
            "observatoire", "données", "analyse", "enquête", "résultats",
            "bilan", "panorama",
        ],
    ),
]

_TOPIC_COLORS: dict[str, str] = {
    "aides_financières":  "#22c55e",
    "dpe_audit":          "#3b82f6",
    "réglementation":     "#a78bfa",
    "rénovation_geste":   "#f97316",
    "marché_immobilier":  "#14b8a6",
    "études_données":     "#94a3b8",
}

_SENTIMENT_COLORS: dict[str, str] = {
    "positive": "#22c55e",
    "negative": "#ef4444",
    "neutral":  "#94a3b8",
}

_SENTIMENT_ICONS: dict[str, str] = {
    "positive": "▲",
    "negative": "▼",
    "neutral":  "●",
}

# ---------------------------------------------------------------------------
# Nettoyage
# ---------------------------------------------------------------------------

def _clean(text: str) -> str:
    text = text.lower()
    text = re.sub(r"https?://\S+", " ", text)
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ---------------------------------------------------------------------------
# TF-IDF keyword extraction
# ---------------------------------------------------------------------------

def extract_keywords(text: str, top_n: int = 6) -> list[str]:
    """Extrait les top-N mots-clés via TF-IDF (français)."""
    if not text or not text.strip():
        return []
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
    except ImportError:
        logger.debug("scikit-learn non installé — extraction TF-IDF désactivée")
        return []

    cleaned = _clean(text)
    vectorizer = TfidfVectorizer(
        max_features=300,
        ngram_range=(1, 2),
        sublinear_tf=True,
        stop_words=list(_FR_STOPWORDS),
        min_df=1,
    )
    try:
        matrix = vectorizer.fit_transform([cleaned])
    except ValueError:
        return []

    feature_names: list[str] = vectorizer.get_feature_names_out().tolist()
    scores = matrix.toarray()[0]
    ranked = sorted(
        ((term, score) for term, score in zip(feature_names, scores) if score > 0),
        key=lambda x: x[1],
        reverse=True,
    )
    return [term for term, _ in ranked[:top_n]]


# ---------------------------------------------------------------------------
# Topic detection
# ---------------------------------------------------------------------------

def detect_topics(text: str) -> list[str]:
    """Classe l'article par topic(s) via la taxonomie rénovation."""
    lower = text.lower()
    matched = [
        topic
        for topic, keywords in _TOPIC_KEYWORDS
        if any(kw in lower for kw in keywords)
    ]
    return matched if matched else ["général"]


# ---------------------------------------------------------------------------
# Sentiment VADER (optionnel — entraîné sur anglais)
# ---------------------------------------------------------------------------

_vader = None


def _get_vader():
    global _vader
    if _vader is None:
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            _vader = SentimentIntensityAnalyzer()
        except ImportError:
            pass
    return _vader


def analyse_sentiment(text: str) -> tuple[float | None, str | None]:
    """Score VADER (compound −1 à +1) + label. Retourne (None, None) si VADER absent."""
    vader = _get_vader()
    if vader is None or not text:
        return None, None
    scores = vader.polarity_scores(text[:500])
    compound = round(scores["compound"], 4)
    if compound >= 0.05:
        label = "positive"
    elif compound <= -0.05:
        label = "negative"
    else:
        label = "neutral"
    return compound, label


# ---------------------------------------------------------------------------
# Pipeline complet
# ---------------------------------------------------------------------------

def analyse_article(title: str, summary: str = "") -> dict[str, Any]:
    """Analyse NLP complète d'un article : keywords TF-IDF + topics + sentiment."""
    full_text = f"{title} {summary}"
    return {
        "nlp_keywords": extract_keywords(full_text, top_n=6),
        "topics": detect_topics(full_text),
        "sentiment_score": analyse_sentiment(full_text)[0],
        "sentiment_label": analyse_sentiment(full_text)[1],
    }


# ---------------------------------------------------------------------------
# Nuage de mots (fréquences sur corpus)
# ---------------------------------------------------------------------------

def count_term_frequencies(texts: list[str], top_n: int = 30) -> dict[str, int]:
    """Fréquences des termes sur l'ensemble du corpus (pour nuage de mots)."""
    if not texts:
        return {}
    try:
        from sklearn.feature_extraction.text import CountVectorizer
    except ImportError:
        return {}
    cleaned = [_clean(t) for t in texts if t and t.strip()]
    if not cleaned:
        return {}
    vectorizer = CountVectorizer(
        max_features=top_n,
        stop_words=list(_FR_STOPWORDS),
        min_df=2,
        ngram_range=(1, 2),
    )
    try:
        matrix = vectorizer.fit_transform(cleaned)
    except ValueError:
        return {}
    feature_names: list[str] = vectorizer.get_feature_names_out().tolist()
    totals = matrix.toarray().sum(axis=0)
    return dict(
        sorted(zip(feature_names, totals.tolist()), key=lambda kv: kv[1], reverse=True)
    )


# ---------------------------------------------------------------------------
# Helpers email HTML
# ---------------------------------------------------------------------------

def topic_badges_html(topics: list[str]) -> str:
    spans = []
    for topic in topics:
        color = _TOPIC_COLORS.get(topic, "#64748b")
        label = topic.replace("_", " ")
        spans.append(
            f'<span style="background:{color}22;color:{color};border:1px solid {color}55;'
            f'padding:1px 7px;border-radius:10px;font-size:11px;font-weight:600;margin-right:3px">'
            f'{label}</span>'
        )
    return "".join(spans)


def sentiment_badge_html(label: str | None, score: float | None) -> str:
    if label is None:
        return ""
    color = _SENTIMENT_COLORS.get(label, "#94a3b8")
    icon = _SENTIMENT_ICONS.get(label, "●")
    score_str = f" {score:+.2f}" if score is not None else ""
    return (
        f'<span style="color:{color};font-size:11px;font-weight:600">'
        f'{icon} {label}{score_str}</span>'
    )
