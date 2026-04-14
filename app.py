import streamlit as st
import google.generativeai as genai
from PIL import Image
from fpdf import FPDF
import json
import re
import random
import time

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
# GESTION DES CLÉS API (FALLBACK ANTI-QUOTA)
# ==========================================
if "GEMINI_API_KEYS" not in st.secrets:
    st.error("⚠️ 'GEMINI_API_KEYS' (sous forme de liste) manquante dans les Secrets Streamlit.")
    st.stop()

if "current_api_index" not in st.session_state:
    st.session_state.current_api_index = 0

def get_working_api_key():
    keys = st.secrets["GEMINI_API_KEYS"]
    if st.session_state.current_api_index >= len(keys):
        st.error("🚨 Toutes les clés API sont épuisées (Quota atteint). Reviens plus tard !")
        st.stop()
    return keys[st.session_state.current_api_index]

# Configuration initiale de l'API
genai.configure(api_key=get_working_api_key())

def switch_to_next_key() -> bool:
    """Passe à la clé de secours et reconfigure l'API. Retourne False si plus de clés."""
    st.session_state.current_api_index += 1
    keys = st.secrets["GEMINI_API_KEYS"]
    
    if st.session_state.current_api_index < len(keys):
        nouvelle_cle = keys[st.session_state.current_api_index]
        genai.configure(api_key=nouvelle_cle)
        return True
    return False

# ==========================================
# CONSTANTES & CONFIGURATION IA
# ==========================================
MATIERES = {
    "Mathématiques":  "🔢",
    "Français":       "📖",
    "Histoire-Géo":   "🌍",
    "SVT":            "🌱",
    "Physique-Chimie":"⚗️",
    "Anglais":        "🇬🇧",
    "Espagnol":       "🇪🇸",
    "Autre":          "📝",
}
DIFFICULTY_ORDER  = ["facile", "moyen", "difficile"]
DIFFICULTY_LABELS = {
    "facile":    "🟢 Facile",
    "moyen":     "🟡 Moyen",
    "difficile": "🔴 Difficile",
}

# Modèle recommandé : gemini-1.5-flash ou gemini-2.5-flash
MODEL_NAME = "gemini-1.5-flash" 

GENERATION_CONFIG = {
    "temperature": 0.3,
    "response_mime_type": "application/json"
}

# ==========================================
# SYSTEM PROMPTS (OPTIMISÉS)
# ==========================================
SYSTEM_BASE = """Tuteur pour élèves de 5ème (12-13 ans). 
RÈGLE 1: Strictement limité au programme de 5ème.
RÈGLE 2: Style inspiré des manuels scolaires (Nathan, Hatier). 
Ton jeune et motivant avec emojis."""

SYSTEM_COURS = SYSTEM_BASE + """
Génère des questions selon ces formats par matière:
- Maths/Physique: qcm ou vrai_faux
- SVT: qcm ou trous
- Histoire-Géo: qcm, qcm_inverse ou trous
- Langues: paires
- Français: qcm
Niveaux: facile (notions de base), moyen (application directe), difficile (2 étapes max).
Format JSON uniquement."""

SYSTEM_EXERCICE = SYSTEM_BASE + """
Génère des exercices selon ces formats par matière:
- Maths/Physique: libre ou schéma
- SVT: libre, ordre ou schéma
- Histoire-Géo: libre
- Langues: ouvert
- Français: libre
Niveaux: facile (1 étape), moyen (2 étapes), difficile (2-3 étapes max).
Format JSON uniquement."""

# ==========================================
# CSS — FOND BLANC, POLICES SOMBRES
# ==========================================
st.markdown("""
<style>
html, body, [class*="stApp"], [data-testid="stAppViewContainer"],
[data-testid="stMain"], .main, .block-container {
    background-color: #ffffff !important;
    color: #1a1a2e !important;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
}
[data-testid="stSidebar"] { background-color: #f8f9ff !important; }
p, span, label, div, h1, h2, h3, h4, h5, h6, li, td, th { color: #1a1a2e !important; }

.hero-header {
    background: linear-gradient(135deg, #FF6B6B 0%, #FFE66D 55%, #4ECDC4 100%);
    border-radius: 20px; padding: 1.6rem 2rem; margin-bottom: 1.8rem;
    text-align: center; box-shadow: 0 4px 18px rgba(0,0,0,0.10);
}
.hero-header h1 { color:#ffffff !important; font-size:2rem; margin:0; text-shadow:1px 2px 6px rgba(0,0,0,0.25); }
.hero-header p  { color:rgba(255,255,255,0.95) !important; margin:0.4rem 0 0; font-size:1rem; }
hr { border-color: #e8ecf0 !important; }

div[data-testid="stButton"].mat-btn > button, div[data-testid="stButton"].mode-btn > button {
    border-radius:16px !important; font-weight:700 !important; background-color:#f4f6ff !important;
    border:2px solid #d4d9f5 !important; color:#1a1a2e !important; box-shadow:0 2px 6px rgba(0,0,0,0.06) !important;
}
div[data-testid="stButton"].mat-btn-selected > button, div[data-testid="stButton"].mode-btn-selected > button {
    background-color:#FF6B6B !important; color:#ffffff !important; border-color:#FF6B6B !important;
    box-shadow:0 4px 14px rgba(255,107,107,0.4) !important;
}
div[data-testid="stButton"].mat-btn > button { height:76px !important; }
div[data-testid="stButton"].mode-btn > button { height:96px !important; }

div[data-testid="stButton"].choice-btn > button { background-color:#f4f6ff !important; border-radius:14px !important; border:2px solid #d4d9f5 !important; width:100% !important; }
div[data-testid="stButton"].choice-correct > button { background-color:#d4f5e9 !important; color:#0a5c36 !important; border:2px solid #28a745 !important; border-radius:14px !important; width:100% !important; }
div[data-testid="stButton"].choice-wrong > button { background-color:#fde8e8 !important; color:#8b1a1a !important; border:2px solid #dc3545 !important; border-radius:14px !important; width:100% !important; }

.session-card { background:linear-gradient(90deg,#f0fff8,#f0f4ff); border-left:5px solid #4ECDC4; border-radius:12px; padding:0.75rem 1.2rem; font-size:0.95rem; box-shadow:0 2px 8px rgba(78,205,196,0.15); }
.score-badge { background:linear-gradient(135deg,#FFE66D,#FF8E5
