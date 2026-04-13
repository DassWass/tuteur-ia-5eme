import streamlit as st
import google.generativeai as genai

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

MODEL_NAME        = "gemini-2.5-flash-lite"

GENERATION_CONFIG = genai.GenerationConfig(
    temperature=0.3,
    response_mime_type="application/json"
)

QUICK_REPLIES = [
    ("💡 Indice",       "Peux-tu me donner un indice sans me donner la réponse ?"),
    ("🤔 Réexpliquer", "Je n'ai pas compris, peux-tu réexpliquer autrement ?"),
    ("✅ Compris !",    "J'ai compris, on peut passer à la suite !"),
    ("🔄 Autre",        "Génère un autre exercice similaire différent."),
]

# ==========================================
# SESSION STATE DEFAULTS
# ==========================================
_DEFAULTS = {
    "seance_lancee":         False,
    "matiere_temp":          "",
    "mode_temp":             "",
    "matiere":               "",
    "sujet":                 "",
    "mode":                  "",
    "ui_type":               "", 
    "chat_session":          None,
    "messages":              [],
    "quick_replies_on":      True,
    "quick_reply_triggered": None,
    "current_question":      None,
    "answered":              False,
    "last_answer_correct":   None,
    "score":                 0,
    "total_questions":       0,
    "difficulty":            "facile",
    "vies":                  3,
    "game_over":             False,
    "hint_revealed":         False,
    "eval_result":           None, 
    "last_choice":           None, 
    "vf_choice":             None, 
    "paires_shuffled":       [], 
}

# ==========================================
# CSS — FOND BLANC, POLICES SOMBRES
# ==========================================
def apply_styles():
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

    /* ── Hero ── */
    .hero-header {
        background: linear-gradient(135deg, #FF6B6B 0%, #FFE66D 55%, #4ECDC4 100%);
        border-radius: 20px; padding: 1.6rem 2rem; margin-bottom: 1.8rem;
        text-align: center; box-shadow: 0 4px 18px rgba(0,0,0,0.10);
    }
    .hero-header h1 { color:#ffffff !important; font-size:2rem; margin:0; text-shadow:1px 2px 6px rgba(0,0,0,0.25); }
    .hero-header p  { color:rgba(255,255,255,0.95) !important; margin:0.4rem 0 0; font-size:1rem; }
    hr { border-color: #e8ecf0 !important; }

    /* ── Tuiles ── */
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

    /* ── Bouton principal ── */
    div[data-testid="stButton"].launch-btn > button {
        background:linear-gradient(135deg,#FF6B6B,#FF8E53) !important; color:#ffffff !important;
        border-radius:50px !important; border:none !important; font-size:1.05rem !important;
        font-weight:700 !important; padding:0.85rem 2rem !important; width:100% !important;
        box-shadow:0 5px 18px rgba(255,107,107,0.40) !important;
    }

    /* ── UI Éléments ── */
    div[data-testid="stButton"].choice-btn > button { background-color:#f4f6ff !important; border-radius:14px !important; border:2px solid #d4d9f5 !important; width:100% !important; }
    div[data-testid="stButton"].choice-correct > button { background-color:#d4f5e9 !important; color:#0a5c36 !important; border:2px solid #28a745 !important; border-radius:14px !important; width:100% !important; }
    div[data-testid="stButton"].choice-wrong > button { background-color:#fde8e8 !important; color:#8b1a1a !important; border:2px solid #dc3545 !important; border-radius:14px !important; width:100% !important; }

    .session-card { background:linear-gradient(90deg,#f0fff8,#f0f4ff); border-left:5px solid #4ECDC4; border-radius:12px; padding:0.75rem 1.2rem; font-size:0.95rem; box-shadow:0 2px 8px rgba(78,205,196,0.15); }
    .score-badge { background:linear-gradient(135deg,#FFE66D,#FF8E53); border-radius:50px; padding:0.3rem 1rem; font-weight:700; font-size:0.9rem; display:inline-block; box-shadow:0 2px 8px rgba(255,142,83,0.30); }
    .diff-badge { border-radius:50px; padding:0.25rem 0.9rem; font-weight:700; font-size:0.88rem; display:inline-block; }
    .diff-facile   { background:#e8f5e9; color:#2e7d32 !important; border:2px solid #a5d6a7; }
    .diff-moyen    { background:#fff9e6; color:#e65100 !important; border:2px solid #ffcc80; }
    .diff-difficile{ background:#fde8e8; color:#8b1a1a !important; border:2px solid #ef9a9a; }
    .lives-display { font-size:1.6rem; text-align:center; padding:0.5rem; letter-spacing:0.3rem; }
    .question-card { background:#f8f9ff; border:2px solid #e0e4ff; border-radius:16px; padding:1.2rem 1.5rem; margin:0.8rem 0; }
    </style>
    """, unsafe_allow_html=True)
