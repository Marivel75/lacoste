"""Veille Rénovation Énergétique — Dashboard Streamlit."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent / "data"

TOPIC_COLORS = {
    "aides_financières":  "#22c55e",
    "dpe_audit":          "#3b82f6",
    "réglementation":     "#a78bfa",
    "rénovation_geste":   "#f97316",
    "marché_immobilier":  "#14b8a6",
    "études_données":     "#94a3b8",
    "général":            "#64748b",
}

SENTIMENT_COLORS = {
    "positive": "#22c55e",
    "negative": "#ef4444",
    "neutral":  "#94a3b8",
}

SENTIMENT_ICONS = {"positive": "▲", "negative": "▼", "neutral": "●"}

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _parse_week(filename: str) -> str:
    m = re.search(r"(\d{4}-W\d{2})", filename)
    return m.group(1) if m else filename


@st.cache_data(ttl=300)
def load_all_data() -> pd.DataFrame:
    files = sorted(DATA_DIR.glob("veille_*.csv"))
    if not files:
        return pd.DataFrame()
    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f, encoding="utf-8-sig", dtype=str)
            df["semaine"] = _parse_week(f.name)
            dfs.append(df)
        except Exception:
            pass
    if not dfs:
        return pd.DataFrame()
    combined = pd.concat(dfs, ignore_index=True)

    # Normalize
    combined["score"] = pd.to_numeric(combined.get("score", 0), errors="coerce").fillna(0).astype(int)
    combined["sentiment_score"] = pd.to_numeric(combined.get("sentiment_score"), errors="coerce")
    for col in ("categorie", "date_publication", "mots_cles_nlp", "sentiment_label", "topics", "thematiques", "source", "titre", "url"):
        if col not in combined.columns:
            combined[col] = ""
        combined[col] = combined[col].fillna("")

    return combined


@st.cache_data(ttl=300)
def load_word_freq(week: str) -> dict[str, int]:
    path = DATA_DIR / f"wordfreq_{week}.json"
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

def _chip(label: str, color: str) -> str:
    return (
        f'<span style="background:{color}22;color:{color};border:1px solid {color}55;'
        f'padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;'
        f'margin:2px 3px 2px 0;display:inline-block">'
        f'{label.replace("_", " ")}</span>'
    )


def _kw_chip(label: str) -> str:
    return (
        f'<span style="background:#e8f0fe;color:#1a73e8;padding:2px 7px;'
        f'border-radius:4px;font-size:11px;margin:2px 2px 2px 0;display:inline-block">'
        f'{label}</span>'
    )


def _topic_chips(topics_str: str) -> str:
    topics = [t.strip() for t in topics_str.split(",") if t.strip() and t.strip() != "général"]
    return "".join(_chip(t, TOPIC_COLORS.get(t, "#64748b")) for t in topics)


def _kw_chips(kw_str: str) -> str:
    kws = [k.strip() for k in kw_str.split(",") if k.strip()][:4]
    return "".join(_kw_chip(k) for k in kws)


def _sentiment_badge(label: str, score: float | None) -> str:
    if not label:
        return ""
    color = SENTIMENT_COLORS.get(label, "#94a3b8")
    icon = SENTIMENT_ICONS.get(label, "●")
    score_str = f" {score:+.2f}" if score is not None and not pd.isna(score) else ""
    return f'<span style="color:{color};font-size:12px;font-weight:600">{icon} {label}{score_str}</span>'

# ---------------------------------------------------------------------------
# Article card
# ---------------------------------------------------------------------------

def render_article_card(row: pd.Series) -> None:
    title = row.get("titre", "—") or "—"
    url = row.get("url", "") or ""
    source = row.get("source", "—") or "—"
    categorie = row.get("categorie", "") or ""
    date_pub = str(row.get("date_publication", "") or "")[:10]
    semaine = row.get("semaine", "") or ""
    score = int(row.get("score", 0))
    thematiques = row.get("thematiques", "") or ""
    topics_str = row.get("topics", "") or ""
    nlp_kw = row.get("mots_cles_nlp", "") or ""
    sentiment_label = row.get("sentiment_label", "") or ""
    sentiment_score_raw = row.get("sentiment_score")
    sentiment_score = float(sentiment_score_raw) if pd.notna(sentiment_score_raw) and sentiment_score_raw != "" else None

    meta_parts = [p for p in [source, categorie, date_pub, semaine] if p]
    meta_str = " · ".join(meta_parts)

    topic_html = _topic_chips(topics_str)
    kw_html = _kw_chips(nlp_kw)
    sent_html = _sentiment_badge(sentiment_label, sentiment_score)
    tags = " ".join(filter(None, [topic_html, kw_html]))

    score_color = "#1a73e8" if score >= 4 else "#f97316" if score >= 2 else "#94a3b8"

    with st.container(border=True):
        col_main, col_score = st.columns([10, 1])
        with col_main:
            st.html(f'<div style="font-size:0.8em;color:#8b949e;margin-bottom:2px">{meta_str}</div>')
            safe_title = title.replace("[", "\\[").replace("]", "\\]")
            st.markdown(f"**[{safe_title}]({url})**" if url else f"**{safe_title}**")
            if thematiques:
                st.caption(f"Mots-clés : {thematiques}")
            if tags:
                st.html(f'<div style="margin-top:4px">{tags}</div>')
        with col_score:
            st.html(
                f'<div style="text-align:right">'
                f'<div style="font-size:22px;font-weight:700;color:{score_color}">{score}</div>'
                f'<div style="font-size:10px;color:#aaa">score</div>'
                f'{"<div style=margin-top:4px>" + sent_html + "</div>" if sent_html else ""}'
                f'</div>'
            )

# ---------------------------------------------------------------------------
# Word cloud
# ---------------------------------------------------------------------------

def render_word_cloud(word_freq: dict[str, int]) -> None:
    if not word_freq:
        st.info("Nuage de mots non disponible — lancez `make run` pour générer les données.")
        return
    max_count = max(word_freq.values(), default=1)
    spans = []
    for term, count in list(word_freq.items())[:28]:
        ratio = count / max_count
        size = round(12 + ratio * 14)
        opacity = round(0.4 + ratio * 0.6, 2)
        weight = "700" if ratio > 0.55 else "400"
        spans.append(
            f'<span style="font-size:{size}px;color:#1a73e8;opacity:{opacity};'
            f'margin:4px 8px;display:inline-block;font-weight:{weight}">{term}</span>'
        )
    st.html(
        f'<div style="background:#f8faff;border-radius:8px;padding:16px 20px;'
        f'line-height:2.4;border:1px solid #dbeafe">{"".join(spans)}</div>'
    )

# ---------------------------------------------------------------------------
# App layout
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Veille Rénovation Énergétique",
    layout="wide",
    page_icon="🏠",
)
st.title("🏠 Veille Rénovation Énergétique")

df = load_all_data()
if df.empty:
    st.warning("Aucun rapport trouvé dans `data/`. Lancez `make run` pour collecter les articles.")
    st.stop()

all_weeks = sorted(df["semaine"].unique(), reverse=True)

tab_articles, tab_dashboard, tab_analytics = st.tabs(
    ["📄 Articles", "📊 Dashboard semaine", "📈 Analytics"]
)

# ===========================================================================
# TAB 1 — ARTICLES
# ===========================================================================

with tab_articles:

    # Sidebar filters
    with st.sidebar:
        st.markdown("### Filtres")
        if st.button("🔄 Rafraîchir", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        st.divider()

        selected_weeks = st.multiselect(
            "Semaine(s)", options=all_weeks, default=[all_weeks[0]]
        )
        sources = sorted(df["source"].replace("", pd.NA).dropna().unique())
        selected_sources = st.multiselect("Source", options=sources)

        cats = sorted(df["categorie"].replace("", pd.NA).dropna().unique())
        selected_cats = st.multiselect("Catégorie", options=cats)

        all_topics: set[str] = set()
        for t in df["topics"]:
            all_topics.update(x.strip() for x in str(t).split(",") if x.strip() and x.strip() != "général")
        selected_topics = st.multiselect("Topic NLP", options=sorted(all_topics))

        sentiments = sorted(df["sentiment_label"].replace("", pd.NA).dropna().unique())
        selected_sentiments = st.multiselect("Sentiment", options=sentiments)

        max_score = int(df["score"].max()) if not df.empty else 10
        min_score = st.slider("Score minimum", 0, max(max_score, 1), 0)

        sort_by = st.selectbox("Trier par", ["Score ↓", "Date ↓", "Score ↑"])

    # Apply filters
    filt = df.copy()
    if selected_weeks:
        filt = filt[filt["semaine"].isin(selected_weeks)]
    if selected_sources:
        filt = filt[filt["source"].isin(selected_sources)]
    if selected_cats:
        filt = filt[filt["categorie"].isin(selected_cats)]
    if selected_topics:
        filt = filt[
            filt["topics"].apply(
                lambda t: any(tp in [x.strip() for x in str(t).split(",")] for tp in selected_topics)
            )
        ]
    if selected_sentiments:
        filt = filt[filt["sentiment_label"].isin(selected_sentiments)]
    filt = filt[filt["score"] >= min_score]

    if sort_by == "Score ↓":
        filt = filt.sort_values("score", ascending=False)
    elif sort_by == "Score ↑":
        filt = filt.sort_values("score", ascending=True)
    elif sort_by == "Date ↓":
        filt = filt.sort_values("date_publication", ascending=False)

    col_info, col_dl = st.columns([5, 1])
    with col_info:
        st.caption(f"{len(filt)} article{'s' if len(filt) != 1 else ''} affiché{'s' if len(filt) != 1 else ''}")
    with col_dl:
        csv_bytes = (
            filt.drop(columns=["semaine"], errors="ignore")
            .to_csv(index=False, encoding="utf-8-sig")
            .encode("utf-8-sig")
        )
        st.download_button(
            "⬇ CSV", csv_bytes, "articles_filtrés.csv", "text/csv", use_container_width=True
        )

    for _, row in filt.iterrows():
        render_article_card(row)

# ===========================================================================
# TAB 2 — DASHBOARD SEMAINE
# ===========================================================================

with tab_dashboard:
    selected_week = st.selectbox("Semaine", options=all_weeks, index=0, key="dash_week")
    week_df = df[df["semaine"] == selected_week]
    word_freq = load_word_freq(selected_week)

    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Articles retenus", len(week_df))
    k2.metric("Sources actives", week_df["source"].nunique())
    avg_score = week_df["score"].mean() if not week_df.empty else 0
    k3.metric("Score moyen", f"{avg_score:.1f}")
    n_pos = (week_df["sentiment_label"] == "positive").sum()
    n_neg = (week_df["sentiment_label"] == "negative").sum()
    k4.metric("Positif / Négatif", f"{n_pos} / {n_neg}")

    st.divider()

    # Word cloud
    st.markdown("#### Tendances de la semaine")
    st.caption(
        "Termes les plus fréquents sur l'ensemble des articles collectés (avant filtrage par score)"
    )
    render_word_cloud(word_freq)

    st.divider()

    col_cat, col_topic = st.columns(2)

    with col_cat:
        st.markdown("#### Articles par catégorie")
        if not week_df.empty:
            cat_c = week_df["categorie"].replace("", pd.NA).dropna().value_counts().reset_index()
            cat_c.columns = ["Catégorie", "Articles"]
            fig = px.bar(
                cat_c, x="Articles", y="Catégorie", orientation="h",
                color="Articles", color_continuous_scale="Blues", height=280,
            )
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)

    with col_topic:
        st.markdown("#### Articles par topic")
        if not week_df.empty:
            rows = []
            for t_str in week_df["topics"]:
                for t in str(t_str).split(","):
                    t = t.strip()
                    if t and t != "général":
                        rows.append(t)
            if rows:
                tc = pd.Series(rows).value_counts().reset_index()
                tc.columns = ["Topic", "Articles"]
                fig = px.bar(
                    tc, x="Articles", y="Topic", orientation="h",
                    color="Topic", color_discrete_map=TOPIC_COLORS, height=280,
                )
                fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.markdown(f"#### Articles — {selected_week}")
    for _, row in week_df.sort_values("score", ascending=False).iterrows():
        render_article_card(row)

# ===========================================================================
# TAB 3 — ANALYTICS
# ===========================================================================

with tab_analytics:

    # --- Évolution hebdomadaire ---
    st.markdown("#### Évolution des articles retenus par semaine")
    weekly = df.groupby("semaine").size().reset_index(name="articles").sort_values("semaine")
    fig_line = px.line(weekly, x="semaine", y="articles", markers=True, height=280)
    fig_line.update_traces(line_color="#1a73e8", marker_color="#1a73e8")
    fig_line.update_layout(margin=dict(l=0, r=0, t=0, b=0),
                           xaxis_title="Semaine", yaxis_title="Articles")
    st.plotly_chart(fig_line, use_container_width=True)

    st.divider()

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### Répartition par catégorie")
        cat_all = df["categorie"].replace("", pd.NA).dropna().value_counts().reset_index()
        cat_all.columns = ["Catégorie", "Articles"]
        fig = px.pie(cat_all, names="Catégorie", values="Articles", hole=0.4, height=320)
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown("#### Répartition du sentiment")
        sent_s = df["sentiment_label"].replace("", pd.NA).dropna()
        if not sent_s.empty:
            sc = sent_s.value_counts().reset_index()
            sc.columns = ["Sentiment", "Articles"]
            fig = px.pie(
                sc, names="Sentiment", values="Articles", hole=0.4, height=320,
                color="Sentiment", color_discrete_map=SENTIMENT_COLORS,
            )
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Données de sentiment non disponibles.")

    st.divider()

    col_c, col_d = st.columns(2)

    with col_c:
        st.markdown("#### Top 10 sources")
        src_c = df["source"].replace("", pd.NA).dropna().value_counts().head(10).reset_index()
        src_c.columns = ["Source", "Articles"]
        fig = px.bar(
            src_c, x="Articles", y="Source", orientation="h",
            color="Articles", color_continuous_scale="Blues", height=340,
        )
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    with col_d:
        st.markdown("#### Distribution des scores")
        fig = px.histogram(
            df, x="score", nbins=12, height=340,
            labels={"score": "Score", "count": "Articles"},
            color_discrete_sequence=["#1a73e8"],
        )
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), yaxis_title="Articles")
        st.plotly_chart(fig, use_container_width=True)

    # Topics par semaine (si plusieurs semaines)
    if len(all_weeks) > 1:
        st.divider()
        st.markdown("#### Évolution des topics par semaine")
        topic_rows = []
        for _, row in df.iterrows():
            for t in str(row.get("topics", "")).split(","):
                t = t.strip()
                if t and t != "général":
                    topic_rows.append({"semaine": row["semaine"], "topic": t})
        if topic_rows:
            tp = pd.DataFrame(topic_rows).groupby(["semaine", "topic"]).size().reset_index(name="articles")
            fig = px.bar(
                tp, x="semaine", y="articles", color="topic",
                barmode="stack", height=320,
                color_discrete_map=TOPIC_COLORS,
                labels={"semaine": "Semaine", "articles": "Articles", "topic": "Topic"},
            )
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)
