# ==========================================
# app.py — Point d'entrée Streamlit
# ==========================================

import logging

import google.generativeai as genai
import streamlit as st
from PIL import Image

from core.components import render_seance, render_setup
from core.engine import analyser_photo, generate_next, init_question
from core.utils import init_session_state, load_css, reset_session_state

logger = logging.getLogger("tuteur_ia.app")

# ==========================================
# CONFIG PAGE
# ==========================================
st.set_page_config(
    page_title="🎓 Tuteur IA — 5ème",
    layout="centered",
    page_icon="🎓",
    initial_sidebar_state="collapsed",
)

# ==========================================
# VÉRIFICATION CLÉ API
# ==========================================
if "GEMINI_API_KEY" not in st.secrets:
    st.error("⚠️ Clé API Gemini manquante dans les Secrets Streamlit.")
    st.stop()
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# ==========================================
# CSS & SESSION STATE
# ==========================================
load_css("assets/style.css")
init_session_state()

# ==========================================
# HEADER
# ==========================================
st.markdown(
    """
    <div class="hero-header">
        <h1>🎓 Ton Tuteur Personnel</h1>
        <p>Révise, progresse et prends confiance en toi ! 💪</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ==========================================
# CALLBACKS
# ==========================================

def _on_launch(matiere: str, sujet: str, mode: str, photo) -> None:
    """
    Callback déclenché par render_setup() au clic sur « Lancer ma séance ».
    Crée le chat, analyse la photo si présente, génère la première question.
    """
    from core.engine import creer_chat

    ui_type = "cours" if mode == "cours" else "exercice"

    with st.spinner("Ton tuteur se prépare... 🎯"):
        try:
            chat = creer_chat(matiere, sujet, ui_type)

            st.session_state.chat_session  = chat
            st.session_state.matiere       = matiere
            st.session_state.sujet         = sujet
            st.session_state.mode          = mode
            st.session_state.ui_type       = ui_type
            st.session_state.seance_lancee = True

            # Contexte examen blanc (optionnel)
            if photo:
                img = Image.open(photo)
                exercices_photo = analyser_photo(img, matiere, ui_type)
                if exercices_photo:
                    chat.send_message(
                        f"Contexte examen blanc :\n{exercices_photo}\nUtilise-le comme base."
                    )

            # Première question
            data, error = generate_next(chat, matiere, sujet, "facile", True)
            if data:
                init_question(data, st.session_state)
            else:
                st.error(error or "Erreur lors de la génération de la première question.")

            st.rerun()

        except Exception as exc:
            logger.error("Erreur au démarrage : %s", exc, exc_info=True)
            st.error(f"❌ Erreur au démarrage : {exc}")


def _on_reset() -> None:
    """Callback de reset complet de la séance."""
    reset_session_state()
    logger.info("Séance réinitialisée par l'utilisateur.")


# ==========================================
# POINT D'ENTRÉE
# ==========================================
if not st.session_state.seance_lancee:
    render_setup(on_launch=_on_launch)
else:
    render_seance(on_reset=_on_reset)
