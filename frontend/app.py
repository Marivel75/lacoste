"""Page d'accueil — statut API et résumé de la semaine courante."""

import streamlit as st

from frontend.api_client import APIError, get_weeks, health

st.set_page_config(
    page_title="Veille Rénovation Énergétique",
    page_icon="🏠",
    layout="wide",
)

st.title("🏠 Veille Rénovation Énergétique")
st.caption("OPTIMMO Énergies — tableau de bord interne")

# ── Statut API ─────────────────────────────────────────────────────────────────

try:
    h = health()
    st.success(f"API en ligne — version {h.get('version', '?')}")
except APIError as e:
    st.error(str(e))
    st.stop()

# ── Résumé semaines ────────────────────────────────────────────────────────────

try:
    weeks = get_weeks()
except APIError as e:
    st.error(str(e))
    st.stop()

if not weeks:
    st.info("Aucune donnée en base. Lancez `make collect` pour démarrer la veille.")
    st.stop()

latest = weeks[0]
col1, col2, col3, col4 = st.columns(4)
col1.metric("Semaine courante", latest["week"])
col2.metric("Articles collectés", latest["article_count"])
col3.metric("Nouveaux articles", latest["articles_new"])
col4.metric("Statut dernier run", latest["status"] or "—")

st.divider()

st.subheader("Historique des collectes")
st.dataframe(
    weeks,
    column_config={
        "week": st.column_config.TextColumn("Semaine"),
        "article_count": st.column_config.NumberColumn("Articles", format="%d"),
        "articles_new": st.column_config.NumberColumn("Nouveaux", format="%d"),
        "run_at": st.column_config.DatetimeColumn("Dernière collecte", format="DD/MM/YYYY HH:mm"),
        "status": st.column_config.TextColumn("Statut"),
    },
    hide_index=True,
    use_container_width=True,
)
