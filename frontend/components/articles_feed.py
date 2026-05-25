"""Composant Streamlit — fil d'articles de veille rénovation énergétique."""

from __future__ import annotations

from collections import Counter

import streamlit as st

_TOPIC_COLORS: dict[str, str] = {
    "aides_financières": "#22c55e",
    "dpe_audit":         "#3b82f6",
    "réglementation":    "#a78bfa",
    "rénovation_geste":  "#f97316",
    "marché_immobilier": "#14b8a6",
    "études_données":    "#94a3b8",
}

_SENTIMENT_COLORS: dict[str, str] = {
    "positif":  "#22c55e",
    "négatif":  "#ef4444",
    "neutre":   "#94a3b8",
    "positive": "#22c55e",
    "negative": "#ef4444",
    "neutral":  "#94a3b8",
}

_SENTIMENT_ICONS: dict[str, str] = {
    "positif": "▲", "positive": "▲",
    "négatif": "▼", "negative": "▼",
    "neutre":  "●", "neutral":  "●",
}


def _score_color(score: int) -> str:
    if score >= 5:
        return "#22c55e"
    if score >= 3:
        return "#3b82f6"
    return "#94a3b8"


def _fmt_date(raw: str | None) -> str:
    if not raw:
        return "—"
    s = str(raw)
    if "T" in s:
        return s[:16].replace("T", " ")
    return s[:16]


def render_articles_feed(articles: list[dict]) -> None:
    """Affiche une liste d'articles sous forme de fil de cartes."""
    if not articles:
        st.info("Aucun article à afficher.")
        return

    for art in articles:
        title = art.get("title", "—")
        url = art.get("url", "")
        source = art.get("source_name", "—")
        category = art.get("source_category", "")
        published = _fmt_date(art.get("published_at") or art.get("collected_at"))
        score = art.get("score", 0)
        summary = (art.get("summary") or "").strip()
        keywords: list[str] = art.get("keywords") or []
        topics: list[str] = art.get("topics") or []
        sentiment_label = art.get("sentiment_label")
        sentiment_score = art.get("sentiment_score")

        score_color = _score_color(score)
        score_badge = (
            f'<span style="background:{score_color}22;color:{score_color};'
            f'border:1px solid {score_color}55;padding:1px 7px;border-radius:10px;'
            f'font-size:0.75em;font-weight:700">score {score}</span>'
        )

        sentiment_badge = ""
        if sentiment_label:
            s_color = _SENTIMENT_COLORS.get(sentiment_label, "#94a3b8")
            s_icon = _SENTIMENT_ICONS.get(sentiment_label, "●")
            s_score = f" {sentiment_score:+.2f}" if sentiment_score is not None else ""
            sentiment_badge = (
                f' &nbsp;·&nbsp; <span style="color:{s_color};font-weight:600">'
                f'{s_icon} {sentiment_label}{s_score}</span>'
            )

        cat_badge = (
            f' &nbsp;·&nbsp; <span style="color:#64748b;font-size:0.8em">{category}</span>'
            if category else ""
        )

        topic_spans = " ".join(
            f'<span style="background:{_TOPIC_COLORS.get(t, "#47556922")}22;'
            f'color:{_TOPIC_COLORS.get(t, "#64748b")};'
            f'border:1px solid {_TOPIC_COLORS.get(t, "#64748b")}55;'
            f'padding:1px 7px;border-radius:10px;font-size:0.75em;font-weight:600">'
            f'{t.replace("_", " ")}</span>'
            for t in topics
        )
        kw_spans = " ".join(
            f'<span style="background:#1e293b;color:#94a3b8;'
            f'padding:1px 6px;border-radius:4px;font-size:0.75em">{kw}</span>'
            for kw in keywords[:5]
        )
        tags = " ".join(filter(None, [topic_spans, kw_spans]))

        with st.container(border=True):
            st.html(
                f'<div style="font-size:0.8em;color:#8b949e;margin-bottom:2px">'
                f'{source}{cat_badge} &nbsp;·&nbsp; {published}'
                f' &nbsp;·&nbsp; {score_badge}{sentiment_badge}'
                f'</div>'
            )
            safe_title = title.replace("[", "\\[").replace("]", "\\]")
            if url:
                st.markdown(f"**[{safe_title}]({url})**")
            else:
                st.markdown(f"**{safe_title}**")
            if summary:
                preview = summary[:220] + ("…" if len(summary) > 220 else "")
                st.caption(preview)
            if tags:
                st.html(f'<div style="margin-top:4px">{tags}</div>')


def render_category_summary(articles: list[dict]) -> None:
    """Affiche un résumé par catégorie (nombre d'articles, score moyen, top source)."""
    if not articles:
        st.info("Aucun article à afficher.")
        return

    by_cat: dict[str, list[dict]] = {}
    for art in articles:
        by_cat.setdefault(art.get("source_category", "—"), []).append(art)

    st.markdown("#### Répartition par catégorie")
    header = st.columns([3, 1, 1, 2])
    header[0].markdown("**Catégorie**")
    header[1].markdown("**Articles**")
    header[2].markdown("**Score moy.**")
    header[3].markdown("**Top source**")

    for cat, arts in sorted(by_cat.items(), key=lambda x: -len(x[1])):
        avg_score = sum(a.get("score", 0) for a in arts) / len(arts)
        top_source = Counter(a.get("source_name", "") for a in arts).most_common(1)[0][0]
        color = _score_color(round(avg_score))
        cols = st.columns([3, 1, 1, 2])
        cols[0].write(cat)
        cols[1].write(len(arts))
        cols[2].markdown(
            f'<span style="color:{color};font-weight:600">{avg_score:.1f}</span>',
            unsafe_allow_html=True,
        )
        cols[3].write(top_source)
