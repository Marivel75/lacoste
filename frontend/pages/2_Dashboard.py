"""Page Dashboard — statistiques et tendances de la semaine."""

from collections import Counter

import pandas as pd
import plotly.express as px
import streamlit as st

from frontend.api_client import APIError, get_articles, get_weeks

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
st.title("📊 Dashboard")

# ── Chargement des semaines ────────────────────────────────────────────────────

try:
    weeks_data = get_weeks()
except APIError as e:
    st.error(str(e))
    st.stop()

if not weeks_data:
    st.info("Aucune donnée en base. Lancez `make collect`.")
    st.stop()

with st.sidebar:
    st.header("Semaine")
    week_labels = [w["week"] for w in weeks_data]
    selected_week = st.selectbox("Semaine", week_labels, index=0)

week_info = next(w for w in weeks_data if w["week"] == selected_week)

# ── Métriques ─────────────────────────────────────────────────────────────────

col1, col2, col3, col4 = st.columns(4)
col1.metric("Articles retenus", week_info["article_count"])
col2.metric("Nouveaux articles", week_info["articles_new"])
col3.metric("Statut run", week_info["status"] or "—")
col4.metric(
    "Dernière collecte",
    week_info["run_at"][:10] if week_info.get("run_at") else "—",
)

st.divider()

# ── Chargement des articles ────────────────────────────────────────────────────

try:
    articles = get_articles(week=selected_week, limit=200)
except APIError as e:
    st.error(str(e))
    st.stop()

if not articles:
    st.info("Aucun article pour cette semaine.")
    st.stop()

df = pd.DataFrame(articles)

# ── Graphiques ─────────────────────────────────────────────────────────────────

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Top sources")
    source_counts = df["source_name"].value_counts().reset_index()
    source_counts.columns = ["source", "articles"]
    fig = px.bar(
        source_counts.head(10),
        x="articles", y="source",
        orientation="h",
        color="articles",
        color_continuous_scale="Blues",
        labels={"articles": "Articles", "source": ""},
    )
    fig.update_layout(showlegend=False, coloraxis_showscale=False, height=350, margin=dict(l=0))
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("Répartition par catégorie")
    cat_counts = df["source_category"].value_counts().reset_index()
    cat_counts.columns = ["catégorie", "articles"]
    fig = px.pie(
        cat_counts,
        names="catégorie",
        values="articles",
        color_discrete_sequence=px.colors.qualitative.Set3,
        hole=0.4,
    )
    fig.update_layout(height=350, margin=dict(l=0))
    st.plotly_chart(fig, use_container_width=True)

# ── Topics ─────────────────────────────────────────────────────────────────────

st.subheader("Topics détectés")
all_topics = [t for topics in df["topics"] for t in (topics or [])]
if all_topics:
    topic_counts = Counter(all_topics).most_common(15)
    t_df = pd.DataFrame(topic_counts, columns=["topic", "occurrences"])
    fig = px.bar(
        t_df,
        x="topic", y="occurrences",
        color="occurrences",
        color_continuous_scale="Teal",
        labels={"occurrences": "Occurrences", "topic": ""},
    )
    fig.update_layout(showlegend=False, coloraxis_showscale=False, height=300, margin=dict(t=0))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Aucun topic détecté.")

# ── Mots-clés NLP ─────────────────────────────────────────────────────────────

st.subheader("Tendances — mots-clés NLP")
all_kw = [k for kws in df["nlp_keywords"] for k in (kws or [])]
if all_kw:
    kw_counts = Counter(all_kw).most_common(20)
    kw_df = pd.DataFrame(kw_counts, columns=["mot", "occurrences"])
    fig = px.bar(
        kw_df,
        x="mot", y="occurrences",
        color="occurrences",
        color_continuous_scale="Oranges",
        labels={"occurrences": "Occurrences", "mot": ""},
    )
    fig.update_layout(showlegend=False, coloraxis_showscale=False, height=300, margin=dict(t=0))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Aucun mot-clé NLP disponible.")

# ── Distribution des scores ────────────────────────────────────────────────────

st.subheader("Distribution des scores de pertinence")
fig = px.histogram(
    df, x="score", nbins=10,
    color_discrete_sequence=["#1a73e8"],
    labels={"score": "Score", "count": "Articles"},
)
fig.update_layout(height=250, margin=dict(t=0))
st.plotly_chart(fig, use_container_width=True)
