"""Page Newsletter — envoi et historique."""

import pandas as pd
import streamlit as st

from frontend.api_client import (
    APIError,
    get_newsletter_logs,
    get_weeks,
    send_newsletter,
    trigger_collect,
)

st.set_page_config(page_title="Newsletter", page_icon="✉️", layout="wide")
st.title("✉️ Newsletter")

# ── Chargement des semaines ────────────────────────────────────────────────────

try:
    weeks_data = get_weeks()
except APIError as e:
    st.error(str(e))
    st.stop()

week_labels = [w["week"] for w in weeks_data] if weeks_data else []

# ── Envoi ──────────────────────────────────────────────────────────────────────

st.subheader("Envoyer la newsletter")

col_week, col_rcpt = st.columns([1, 2])

with col_week:
    if week_labels:
        selected_week = st.selectbox("Semaine", week_labels, index=0)
    else:
        selected_week = st.text_input("Semaine (ex: 2026-W22)", value="")

with col_rcpt:
    extra_input = st.text_input(
        "Destinataires supplémentaires",
        placeholder="emma@optimmo-energies.com, gabriel@optimmo-energies.com",
        help="Séparés par des virgules. Ton adresse est toujours incluse via le .env.",
    )

extra_recipients = [e.strip() for e in extra_input.split(",") if e.strip()]

col_btn1, col_btn2, _ = st.columns([1, 1, 2])

with col_btn1:
    if st.button("✉️ Envoyer", type="primary", use_container_width=True):
        with st.spinner("Envoi en cours…"):
            try:
                result = send_newsletter(
                    week=selected_week or None,
                    extra_recipients=extra_recipients or None,
                )
                if result["sent"]:
                    rcpts = ", ".join(result["recipients"])
                    st.success(f"Newsletter {result['week']} envoyée à : {rcpts} ({result['articles_sent']} articles)")
                elif result["articles_sent"] == 0:
                    st.warning(f"Aucun article en base pour {result['week']}. Lancez d'abord une collecte.")
                else:
                    st.error("Email non configuré — vérifiez EMAIL_SENDER / EMAIL_PASSWORD dans le .env.")
            except APIError as e:
                st.error(str(e))

with col_btn2:
    days = st.session_state.get("collect_days", 7)
    if st.button("🔄 Collecter + Envoyer", use_container_width=True):
        with st.spinner("Collecte en cours (peut prendre 30-60 s)…"):
            try:
                collect_result = trigger_collect(days=days)
                st.info(f"Collecte terminée : {collect_result['new']} nouveaux articles ({collect_result['week']})")
            except APIError as e:
                st.error(str(e))
                st.stop()
        with st.spinner("Envoi en cours…"):
            try:
                result = send_newsletter(
                    week=selected_week or None,
                    extra_recipients=extra_recipients or None,
                )
                if result["sent"]:
                    rcpts = ", ".join(result["recipients"])
                    st.success(f"Newsletter {result['week']} envoyée à : {rcpts} ({result['articles_sent']} articles)")
                else:
                    st.warning("Collecte OK mais envoi non effectué — vérifiez la configuration email.")
            except APIError as e:
                st.error(str(e))

with st.expander("⚙️ Options de collecte"):
    st.session_state["collect_days"] = st.slider("Jours en arrière", 1, 30, 7)

st.divider()

# ── Historique ─────────────────────────────────────────────────────────────────

st.subheader("Historique des envois")

try:
    logs = get_newsletter_logs()
except APIError as e:
    st.error(str(e))
    st.stop()

if not logs:
    st.info("Aucun envoi enregistré.")
else:
    df = pd.DataFrame(logs)
    st.dataframe(
        df[["week", "sent_at", "articles_count", "recipients", "status", "error_message"]],
        column_config={
            "week": st.column_config.TextColumn("Semaine", width="small"),
            "sent_at": st.column_config.DatetimeColumn("Envoyé le", format="DD/MM/YYYY HH:mm"),
            "articles_count": st.column_config.NumberColumn("Articles", format="%d", width="small"),
            "recipients": st.column_config.ListColumn("Destinataires"),
            "status": st.column_config.TextColumn("Statut", width="small"),
            "error_message": st.column_config.TextColumn("Erreur"),
        },
        hide_index=True,
        use_container_width=True,
    )
