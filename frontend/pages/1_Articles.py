"""Page Articles — parcourir et filtrer les articles de veille."""

from __future__ import annotations

import streamlit as st

from frontend.api_client import APIError, get_articles, get_weeks
from frontend.components.articles_feed import render_articles_feed, render_category_summary

st.set_page_config(page_title="Articles", page_icon="📰", layout="wide")
st.header("📰 Articles de veille")

# ── Données cachées ────────────────────────────────────────────────────────────

@st.cache_data(ttl=120)
def _fetch_weeks():
    return get_weeks()


@st.cache_data(ttl=120)
def _fetch_articles(week, category, source, min_score, limit):
    return get_articles(
        week=week,
        category=category if category != "Toutes" else None,
        source=source if source != "Toutes" else None,
        min_score=min_score,
        limit=limit,
    )


# ── Chargement des semaines ────────────────────────────────────────────────────

try:
    weeks_data = _fetch_weeks()
except APIError as e:
    st.error(str(e))
    st.stop()

if not weeks_data:
    st.info("Aucune donnée en base. Lancez `make collect`.")
    st.stop()

week_labels = [w["week"] for w in weeks_data]

# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    if st.button("🔄 Rafraîchir", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.markdown("### Filtres")

    selected_week = st.selectbox("Semaine", week_labels, index=0)
    min_score = st.slider("Score minimum", 0, 10, 1)
    limit = st.slider("Nombre d'articles", 10, 200, 50, step=10)

# ── Chargement articles (sans filtre catégorie/source pour les listes) ─────────

try:
    all_articles = _fetch_articles(selected_week, None, None, min_score, 200)
except APIError as e:
    st.error(str(e))
    st.stop()

if not all_articles:
    st.info(f"Aucun article pour {selected_week} avec score ≥ {min_score}.")
    st.stop()

# Filtres catégorie et source (calculés depuis les articles chargés)
categories = ["Toutes"] + sorted({a["source_category"] for a in all_articles})
sources = ["Toutes"] + sorted({a["source_name"] for a in all_articles})

with st.sidebar:
    selected_category = st.selectbox("Catégorie", categories)
    selected_source = st.selectbox("Source", sources)

# Filtrage client-side
filtered = all_articles
if selected_category != "Toutes":
    filtered = [a for a in filtered if a["source_category"] == selected_category]
if selected_source != "Toutes":
    filtered = [a for a in filtered if a["source_name"] == selected_source]

displayed = filtered[:limit]

# ── Tabs ───────────────────────────────────────────────────────────────────────

st.caption(f"{len(displayed)} article(s) affiché(s) sur {len(filtered)} — {selected_week}")

with st.expander("ℹ️ Comment est calculé le score ?", expanded=False):
    st.markdown("""
Chaque article reçoit un **score de pertinence** calculé à partir des mots-clés définis dans `config/keywords.yml`.

| Correspondance | Points |
|---|---|
| Mot-clé trouvé dans le **titre** | **2 points** |
| Mot-clé trouvé dans le **résumé** uniquement | **1 point** |

Un même mot-clé ne compte qu'une seule fois, même s'il apparaît plusieurs fois.
Le score final est la **somme** des points de tous les mots-clés détectés.

**Exemple** — article avec les mots-clés *DPE* (titre) et *MaPrimeRénov* (résumé) :
- DPE dans le titre → 2 pts
- MaPrimeRénov dans le résumé → 1 pt
- **Score total : 3**

Les articles sont triés par score décroissant, puis par date de publication.
Le filtre **Score minimum** (sidebar) exclut les articles en dessous du seuil choisi.
""")

tab_feed, tab_summary = st.tabs(["📄 Articles", "📂 Par catégorie"])

with tab_feed:
    render_articles_feed(displayed)

with tab_summary:
    render_category_summary(filtered)
