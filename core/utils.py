# ==========================================
# core/utils.py — Utilitaires transversaux
# ==========================================

import copy
import logging
import os
import pathlib

import streamlit as st

from core.config import SESSION_DEFAULTS

# ── Logger ─────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("tuteur_ia")


# ── Session state ──────────────────────────────────────────────────────────────

def init_session_state() -> None:
    """
    Initialise les clés manquantes du session state Streamlit.
    Utilise deepcopy pour éviter que les valeurs mutables (listes, dicts)
    soient partagées entre différentes sessions ou resets.
    """
    for key, value in SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = copy.deepcopy(value)


def reset_session_state() -> None:
    """
    Remet toutes les clés du session state à leurs valeurs par défaut.
    Utilise deepcopy pour garantir des objets indépendants.
    """
    for key, value in SESSION_DEFAULTS.items():
        st.session_state[key] = copy.deepcopy(value)
    logger.info("Session state réinitialisé.")


# ── Chargement du CSS ──────────────────────────────────────────────────────────

def load_css(relative_path: str = "assets/style.css") -> None:
    """
    Injecte le fichier CSS dans la page Streamlit.
    Le chemin est résolu relativement à la racine du projet
    (répertoire du fichier appelant ou répertoire courant).
    """
    # Cherche d'abord depuis le répertoire courant (racine du projet)
    css_path = pathlib.Path(relative_path)
    if not css_path.exists():
        # Fallback : relatif au fichier utils.py lui-même
        css_path = pathlib.Path(__file__).parent.parent / relative_path

    if not css_path.exists():
        logger.warning("Fichier CSS introuvable : %s", css_path)
        return

    css_content = css_path.read_text(encoding="utf-8")
    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    logger.debug("CSS chargé depuis %s", css_path)
