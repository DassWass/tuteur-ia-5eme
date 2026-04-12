import streamlit as st
import google.generativeai as genai
from PIL import Image
from fpdf import FPDF
import json
import re
import random

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
# CONSTANTES
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
GENERATION_CONFIG = genai.GenerationConfig(temperature=0.7)

# ==========================================
# SYSTEM PROMPTS
# ==========================================
SYSTEM_BASE = """Tu es un tuteur super sympa, bienveillant et patient pour des élèves de 5ème (12-13 ans).
Utilise le tutoiement, des emojis et un ton jeune et motivant.
Tes réponses JSON doivent être UNIQUEMENT du JSON valide, sans balises markdown, sans texte avant ou après.
"""

SYSTEM_COURS = SYSTEM_BASE + """
Tu génères des questions pour aider l'élève à COMPRENDRE et MÉMORISER son cours.

FORMATS À UTILISER SELON LA MATIÈRE (respecte strictement ces règles) :
- Mathématiques / Physique-Chimie → qcm OU vrai_faux (choisis selon le sujet)
- SVT → qcm OU trous (choisis selon le sujet)
- Histoire-Géo → qcm, qcm_inverse OU trous (choisis le plus adapté)
- Anglais / Espagnol → paires (toujours pour cette matière, pour mémoriser le vocabulaire)
- Français → qcm uniquement
- Autre → qcm

NIVEAUX DE DIFFICULTÉ :
- facile : définition simple, notion de base
- moyen : relation entre deux notions, application directe
- difficile : synthèse, comparaison, raisonnement

Le niveau sera précisé dans chaque prompt.

FORMATS JSON (UNIQUEMENT le JSON, sans markdown) :

qcm :
{"format":"qcm","difficulty":"facile","question":"...","choices":{"A":"...","B":"...","C":"...","D":"..."},"correct":"A","explanation":"... emoji"}

qcm_inverse :
{"format":"qcm_inverse","difficulty":"moyen","answer":"La réponse donnée","choices":{"A":"Question A ?","B":"Question B ?","C":"Question C ?","D":"Question D ?"},"correct":"B","explanation":"... emoji"}

vrai_faux :
{"format":"vrai_faux","difficulty":"facile","statement":"Affirmation à évaluer (vraie ou fausse)","correct":true,"explanation":"Explication complète avec emoji"}

trous :
{"format":"trous","difficulty":"facile","instruction":"Complète la phrase","text":"[BLANK_0] est ... [BLANK_1] ...","blanks":["mot1","mot2"],"explanation":"... emoji"}

paires :
{"format":"paires","difficulty":"facile","instruction":"Associe chaque élément à sa définition","pairs":[{"left":"...","right":"..."},{"left":"...","right":"..."},{"left":"...","right":"..."},{"left":"...","right":"..."}],"explanation":"... emoji"}
"""

SYSTEM_EXERCICE = SYSTEM_BASE + """
Tu génères des exercices d'APPLICATION pour que l'élève s'entraîne.

FORMATS À UTILISER SELON LA MATIÈRE (respecte strictement ces règles) :
- Mathématiques / Physique-Chimie → libre OU schéma_libre (problème ou schéma à décrire/compléter)
  * Pour un schéma : génère un format "libre" avec un énoncé qui décrit un schéma à compléter ou légender
- SVT → libre OU ordre OU schéma_libre (choisis le plus adapté : ordre pour les cycles/processus, schéma pour anatomie)
- Histoire-Géo → libre uniquement
- Anglais / Espagnol → ouvert (compréhension de texte OU production écrite avec critères)
- Français → libre uniquement (problème de langue, rédaction guidée)
- Autre → libre

RÈGLE SCHÉMA : pour Maths/Physique/SVT, si le sujet s'y prête (géométrie, circuit électrique, cellule, appareil digestif...),
génère un exercice "libre" dont l'énoncé décrit un schéma à compléter, à légender ou à analyser.
L'élève répond par du texte libre (ex: "la mitochondrie", "12 cm", "résistance en série").

NIVEAUX DE DIFFICULTÉ :
- facile : une étape, données simples, application directe
- moyen : 2-3 étapes, données réalistes, raisonnement guidé
- difficile : cas complexe, multi-étapes, transfert de compétences

Le niveau sera précisé dans chaque prompt.

FORMATS JSON (UNIQUEMENT le JSON, sans markdown) :

libre :
{"format":"libre","difficulty":"moyen","problem":"Énoncé complet et clair (peut décrire un schéma à compléter)","solution":"Réponse courte et précise","explanation":"Solution étape par étape emoji","hint":"Indice utile sans spoiler"}

trous :
{"format":"trous","difficulty":"facile","instruction":"Complète","text":"[BLANK_0] ... [BLANK_1] ...","blanks":["réponse1","réponse2"],"explanation":"... emoji"}

ordre :
{"format":"ordre","difficulty":"moyen","instruction":"Remets ces étapes dans le bon ordre","items_shuffled":["Étape C","Étape A","Étape D","Étape B"],"correct_order":["Étape A","Étape B","Étape C","Étape D"],"explanation":"... emoji"}

ouvert :
{"format":"ouvert","difficulty":"difficile","prompt":"Texte de compréhension ou question ouverte à développer","criteria":["critère 1 attendu","critère 2 attendu","critère 3 attendu"],"explanation":"Ce que la réponse idéale devrait contenir"}

Pour évaluer une réponse libre, tu recevras :
EVAL|libre|<solution_attendue>|<réponse_élève>
Pour évaluer un exercice ouvert :
EVAL|ouvert|<criteria_json>|<réponse_élève>
Réponds UNIQUEMENT avec :
{"correct":true,"feedback":"Message encourageant 2-3 phrases avec emoji"}
"""

SYSTEM_FLASHCARD = SYSTEM_BASE + """
Tu génères des flashcards pour mémoriser vocabulaire, règles ou conjugaisons.

{"format":"flashcard","front":"Mot ou expression recto","back":"Traduction ou définition verso","hint":"Indice optionnel (vide si pas utile)","example":"Exemple d'usage en contexte"}

Génère une flashcard par message. JSON uniquement.
"""

QUICK_REPLIES = [
    ("💡 Indice",       "Peux-tu me donner un indice sans me donner la réponse ?"),
    ("🤔 Réexpliquer", "Je n'ai pas compris, peux-tu réexpliquer autrement ?"),
    ("✅ Compris !",    "J'ai compris, on peut passer à la suite !"),
    ("🔄 Autre",        "Génère un autre exercice similaire différent."),
]

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

p, span, label, div, h1, h2, h3, h4, h5, h6, li, td, th {
    color: #1a1a2e !important;
}

/* ── Hero ── */
.hero-header {
    background: linear-gradient(135deg, #FF6B6B 0%, #FFE66D 55%, #4ECDC4 100%);
    border-radius: 20px; padding: 1.6rem 2rem; margin-bottom: 1.8rem;
    text-align: center; box-shadow: 0 4px 18px rgba(0,0,0,0.10);
}
.hero-header h1 { color:#ffffff !important; font-size:2rem; margin:0; text-shadow:1px 2px 6px rgba(0,0,0,0.25); }
.hero-header p  { color:rgba(255,255,255,0.95) !important; margin:0.4rem 0 0; font-size:1rem; }

hr { border-color: #e8ecf0 !important; }

/* ── Tuiles matières ── */
div[data-testid="stButton"].mat-btn > button {
    height:76px !important; border-radius:16px !important; font-size:0.88rem !important;
    font-weight:700 !important; background-color:#f4f6ff !important;
    border:2px solid #d4d9f5 !important; color:#1a1a2e !important;
    white-space:pre-line !important; line-height:1.4 !important; transition:all 0.18s ease !important;
    box-shadow:0 2px 6px rgba(0,0,0,0.06) !important;
}
div[data-testid="stButton"].mat-btn > button:hover {
    background-color:#4ECDC4 !important; color:#ffffff !important;
    border-color:#4ECDC4 !important; transform:translateY(-3px) !important;
}
div[data-testid="stButton"].mat-btn-selected > button {
    background-color:#FF6B6B !important; color:#ffffff !important;
    border-color:#FF6B6B !important; box-shadow:0 4px 14px rgba(255,107,107,0.4) !important;
    height:76px !important; border-radius:16px !important; font-size:0.88rem !important;
    font-weight:700 !important; white-space:pre-line !important; line-height:1.4 !important;
}

/* ── Tuiles mode ── */
div[data-testid="stButton"].mode-btn > button {
    height:96px !important; border-radius:18px !important; font-size:0.95rem !important;
    font-weight:700 !important; background-color:#fff8f0 !important;
    border:2px solid #ffd9b3 !important; color:#1a1a2e !important;
    white-space:pre-line !important; line-height:1.5 !important; transition:all 0.18s !important;
    box-shadow:0 2px 6px rgba(0,0,0,0.06) !important;
}
div[data-testid="stButton"].mode-btn > button:hover {
    background-color:#FF8E53 !important; color:#ffffff !important; border-color:#FF8E53 !important;
}
div[data-testid="stButton"].mode-btn-selected > button {
    background-color:#FF6B6B !important; color:#ffffff !important; border-color:#FF6B6B !important;
    height:96px !important; border-radius:18px !important; font-size:0.95rem !important;
    font-weight:700 !important; white-space:pre-line !important; line-height:1.5 !important;
}

/* ── Bouton principal ── */
div[data-testid="stButton"].launch-btn > button {
    background:linear-gradient(135deg,#FF6B6B,#FF8E53) !important; color:#ffffff !important;
    border-radius:50px !important; border:none !important; font-size:1.05rem !important;
    font-weight:700 !important; padding:0.85rem 2rem !important; width:100% !important;
    box-shadow:0 5px 18px rgba(255,107,107,0.40) !important; transition:all 0.2s !important;
}
div[data-testid="stButton"].launch-btn > button:hover { transform:translateY(-2px) !important; }

/* ── Choix QCM ── */
div[data-testid="stButton"].choice-btn > button {
    background-color:#f4f6ff !important; color:#1a1a2e !important;
    border-radius:14px !important; border:2px solid #d4d9f5 !important;
    font-size:0.95rem !important; font-weight:600 !important;
    padding:0.75rem 1rem !important; text-align:left !important;
    transition:all 0.15s !important; width:100% !important;
    box-shadow:0 2px 5px rgba(0,0,0,0.05) !important;
}
div[data-testid="stButton"].choice-btn > button:hover {
    background-color:#4ECDC4 !important; color:#ffffff !important; border-color:#4ECDC4 !important;
}
div[data-testid="stButton"].choice-correct > button {
    background-color:#d4f5e9 !important; color:#0a5c36 !important;
    border:2px solid #28a745 !important; border-radius:14px !important;
    font-size:0.95rem !important; font-weight:700 !important;
    width:100% !important; padding:0.75rem 1rem !important;
}
div[data-testid="stButton"].choice-wrong > button {
    background-color:#fde8e8 !important; color:#8b1a1a !important;
    border:2px solid #dc3545 !important; border-radius:14px !important;
    font-size:0.95rem !important; font-weight:700 !important;
    width:100% !important; padding:0.75rem 1rem !important;
}

/* ── Boutons Vrai/Faux ── */
div[data-testid="stButton"].vf-true > button {
    background-color:#d4f5e9 !important; color:#0a5c36 !important;
    border:3px solid #28a745 !important; border-radius:16px !important;
    font-size:1.1rem !important; font-weight:700 !important; width:100% !important; padding:1rem !important;
}
div[data-testid="stButton"].vf-false > button {
    background-color:#fde8e8 !important; color:#8b1a1a !important;
    border:3px solid #dc3545 !important; border-radius:16px !important;
    font-size:1.1rem !important; font-weight:700 !important; width:100% !important; padding:1rem !important;
}
div[data-testid="stButton"].vf-neutral > button {
    background-color:#f4f6ff !important; color:#1a1a2e !important;
    border:2px solid #d4d9f5 !important; border-radius:16px !important;
    font-size:1.1rem !important; font-weight:700 !important; width:100% !important; padding:1rem !important;
    transition:all 0.15s !important;
}
div[data-testid="stButton"].vf-neutral > button:hover {
    background-color:#4ECDC4 !important; color:#ffffff !important; border-color:#4ECDC4 !important;
}

/* ── Reset / quick replies ── */
div[data-testid="stButton"].reset-btn > button {
    background:transparent !important; border:2px solid #d4d9f5 !important;
    color:#6b7280 !important; border-radius:50px !important; font-size:0.82rem !important;
}
div[data-testid="stButton"].reset-btn > button:hover { border-color:#FF6B6B !important; color:#FF6B6B !important; }
div[data-testid="stButton"].qr-btn > button {
    background-color:#f4f6ff !important; color:#1a1a2e !important;
    border-radius:50px !important; border:2px solid #d4d9f5 !important;
    font-size:0.82rem !important; font-weight:600 !important; transition:all 0.15s !important;
}
div[data-testid="stButton"].qr-btn > button:hover {
    background-color:#4ECDC4 !important; color:#ffffff !important; border-color:#4ECDC4 !important;
}

/* ── Carte contexte ── */
.session-card {
    background:linear-gradient(90deg,#f0fff8,#f0f4ff);
    border-left:5px solid #4ECDC4; border-radius:12px;
    padding:0.75rem 1.2rem; font-size:0.95rem; color:#1a1a2e !important;
    box-shadow:0 2px 8px rgba(78,205,196,0.15);
}

/* ── Badges ── */
.score-badge {
    background:linear-gradient(135deg,#FFE66D,#FF8E53);
    border-radius:50px; padding:0.3rem 1rem; font-weight:700;
    color:#1a1a2e !important; font-size:0.9rem; display:inline-block;
    box-shadow:0 2px 8px rgba(255,142,83,0.30);
}
.diff-badge {
    border-radius:50px; padding:0.25rem 0.9rem; font-weight:700;
    font-size:0.88rem; display:inline-block;
}
.diff-facile   { background:#e8f5e9; color:#2e7d32 !important; border:2px solid #a5d6a7; }
.diff-moyen    { background:#fff9e6; color:#e65100 !important; border:2px solid #ffcc80; }
.diff-difficile{ background:#fde8e8; color:#8b1a1a !important; border:2px solid #ef9a9a; }

/* ── Vies ── */
.lives-display { font-size:1.6rem; text-align:center; padding:0.5rem; letter-spacing:0.3rem; }

/* ── Question card ── */
.question-card {
    background:#f8f9ff; border:2px solid #e0e4ff;
    border-radius:16px; padding:1.2rem 1.5rem; margin:0.8rem 0;
    color:#1a1a2e !important;
}
.question-card p { color:#1a1a2e !important; }

/* ── Trous display ── */
.trous-text {
    background:#f0f4ff; border:2px solid #d4d9f5; border-radius:12px;
    padding:1rem 1.4rem; font-size:1.05rem; line-height:2;
    color:#1a1a2e !important;
}
.blank-placeholder {
    display:inline-block; min-width:80px; border-bottom:3px solid #FF6B6B;
    margin:0 4px; color:#FF6B6B !important; font-weight:700;
    text-align:center;
}

/* ── Paires ── */
.pair-left {
    background:#e8f4fd; border:2px solid #90caf9; border-radius:10px;
    padding:0.5rem 1rem; font-weight:600; color:#0d47a1 !important;
    display:flex; align-items:center; height:100%;
}

/* ── Flashcard ── */
.flashcard-front {
    background:linear-gradient(135deg,#667eea,#764ba2);
    border-radius:20px; padding:2.5rem; text-align:center;
    color:#ffffff !important; font-size:1.4rem; font-weight:700;
    min-height:150px; display:flex; align-items:center; justify-content:center;
    box-shadow:0 8px 24px rgba(102,126,234,0.35); margin:1rem 0;
}
.flashcard-back {
    background:linear-gradient(135deg,#f093fb,#f5576c);
    border-radius:20px; padding:2rem; text-align:center;
    color:#ffffff !important; font-size:1.1rem; min-height:150px;
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    box-shadow:0 8px 24px rgba(245,87,108,0.35); margin:1rem 0;
}
.flashcard-back strong { color:#ffffff !important; }
.flashcard-example {
    margin-top:0.8rem; font-style:italic; font-size:0.9rem;
    opacity:0.92; border-top:1px solid rgba(255,255,255,0.35);
    padding-top:0.6rem; width:100%; color:#ffffff !important;
}

/* ── Misc ── */
[data-testid="stTextInput"] input {
    background-color:#f8f9ff !important; color:#1a1a2e !important;
    border:2px solid #d4d9f5 !important; border-radius:10px !important;
}
[data-testid="stTextArea"] textarea {
    background-color:#f8f9ff !important; color:#1a1a2e !important;
    border:2px solid #d4d9f5 !important; border-radius:10px !important;
}
[data-testid="stSelectbox"] > div { background-color:#f8f9ff !important; }
[data-testid="stExpander"] {
    background-color:#f8f9ff !important; border:1px solid #e8ecf0 !important; border-radius:12px !important;
}
[data-testid="stChatMessage"] {
    background-color:#f8f9ff !important; border-radius:14px !important; border:1px solid #e8ecf0 !important;
}
[data-testid="stCaptionContainer"] p { color:#6b7280 !important; }
[data-testid="stAlert"] p { color:inherit !important; }
.section-title { font-size:1.05rem; font-weight:700; color:#1a1a2e !important; margin:1.2rem 0 0.6rem; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# SESSION STATE
# ==========================================
_DEFAULTS = {
    "seance_lancee":         False,
    "matiere_temp":          "",
    "mode_temp":             "",
    "matiere":               "",
    "sujet":                 "",
    "mode":                  "",
    "ui_type":               "",        # "cours" | "exercice" | "flashcard"

    "chat_session":          None,
    "messages":              [],
    "quick_replies_on":      True,
    "quick_reply_triggered": None,

    "current_question":      None,
    "answered":              False,
    "last_answer_correct":   None,
    "score":                 0,
    "total_questions":       0,

    # Difficulté progressive
    "difficulty":            "facile",

    # Vies (mode exercice uniquement)
    "vies":                  3,
    "game_over":             False,

    # Formats spécifiques
    "hint_revealed":         False,
    "eval_result":           None,      # {correct, feedback} pour libre/ouvert
    "last_choice":           None,      # pour QCM
    "vf_choice":             None,      # True/False pour vrai_faux
    "paires_shuffled":       [],        # droites mélangées pour éviter de remélanger
    "card_revealed":         False,     # flashcard recto/verso
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


def reset_seance():
    for k, v in _DEFAULTS.items():
        st.session_state[k] = v


def get_ui_type(matiere: str, mode: str) -> str:
    # Français suit maintenant les modes cours/exercice (QCM + problème libre)
    # Flashcard supprimé du mapping public
    return "cours" if mode == "cours" else "exercice"


def advance_difficulty(current: str) -> str:
    idx = DIFFICULTY_ORDER.index(current)
    return DIFFICULTY_ORDER[min(idx + 1, 2)]


# ==========================================
# GEMINI HELPERS
# ==========================================
def make_model(system_prompt: str):
    return genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=system_prompt,
        generation_config=GENERATION_CONFIG,
    )


def creer_chat(matiere: str, sujet: str, ui_type: str):
    if ui_type == "flashcard":
        base = SYSTEM_FLASHCARD
    elif ui_type == "cours":
        base = SYSTEM_COURS
    else:
        base = SYSTEM_EXERCICE
    system = base + f"\n\nMatière : {matiere}\nSujet : {sujet}"
    return make_model(system).start_chat(history=[])


def parse_json_response(text: str) -> dict | None:
    try:
        clean = re.sub(r"```json|```", "", text).strip()
        return json.loads(clean)
    except Exception:
        try:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass
    return None


def generate_next(chat_session, matiere: str, sujet: str, difficulty: str, is_first: bool) -> tuple:
    """Génère la prochaine question/exercice en transmettant le niveau souhaité."""
    diff_label = DIFFICULTY_LABELS[difficulty]
    if is_first:
        prompt = (
            f"Génère la première question/exercice de niveau {diff_label} "
            f"pour {matiere} — sujet : {sujet}. "
            "Commence par une courte blague rigolote (1 ligne), puis JSON uniquement."
        )
    else:
        prompt = f"Prochaine question/exercice de niveau {diff_label} sur {sujet}. JSON uniquement."
    response = chat_session.send_message(prompt)
    return parse_json_response(response.text), response.text


def generate_flashcard(chat_session, matiere: str, sujet: str, is_first: bool) -> tuple:
    if is_first:
        prompt = (
            f"On travaille sur {matiere} — sujet : {sujet}. "
            "Commence par une courte blague (1 ligne), puis première flashcard JSON."
        )
    else:
        prompt = "Flashcard suivante. JSON uniquement."
    response = chat_session.send_message(prompt)
    return parse_json_response(response.text), response.text


def evaluate_answer(chat_session, fmt: str, expected, student_answer: str) -> dict:
    if fmt == "ouvert":
        prompt = f"EVAL|ouvert|{json.dumps(expected, ensure_ascii=False)}|{student_answer}"
    else:
        prompt = f"EVAL|libre|{expected}|{student_answer}"
    response = chat_session.send_message(prompt)
    data = parse_json_response(response.text)
    return data if data else {"correct": False, "feedback": "Je n'ai pas pu évaluer ta réponse, réessaie ! 🤔"}


def init_question(data: dict):
    """Initialise la session pour une nouvelle question et gère les paires."""
    st.session_state.current_question    = data
    st.session_state.answered            = False
    st.session_state.last_answer_correct = None
    st.session_state.last_choice         = None
    st.session_state.vf_choice           = None
    st.session_state.hint_revealed       = False
    st.session_state.eval_result         = None
    st.session_state.card_revealed       = False
    # Mélange des paires une seule fois à l'affichage
    if data.get("format") == "paires":
        rights = [p["right"] for p in data.get("pairs", [])]
        random.shuffle(rights)
        st.session_state.paires_shuffled = rights


def handle_correct(mode: str):
    st.session_state.score           += 1
    st.session_state.total_questions += 1
    st.session_state.answered         = True
    st.session_state.last_answer_correct = True
    st.session_state.difficulty       = advance_difficulty(st.session_state.difficulty)


def handle_wrong(mode: str):
    st.session_state.total_questions += 1
    st.session_state.answered         = True
    st.session_state.last_answer_correct = False
    if mode == "exercice":
        st.session_state.vies -= 1
        if st.session_state.vies <= 0:
            st.session_state.game_over = True


def next_question_button(chat_session, matiere: str, sujet: str, mode: str, label: str = "➡️ Question suivante"):
    """Bouton générique 'question suivante'."""
    st.markdown('<div class="launch-btn">', unsafe_allow_html=True)
    if st.button(label, use_container_width=True, key="next_q_btn"):
        with st.spinner("Chargement... ⚡"):
            try:
                data, raw = generate_next(
                    chat_session, matiere, sujet,
                    st.session_state.difficulty, False
                )
                if data:
                    init_question(data)
                else:
                    st.session_state.messages.append({"role": "assistant", "content": raw})
            except Exception as e:
                st.error(f"❌ {e}")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def analyser_photo(image: Image.Image, matiere: str, ui_type: str) -> str:
    base = SYSTEM_EXERCICE if ui_type == "exercice" else SYSTEM_COURS
    model = make_model(base)
    prompt = (
        f"Voici une photo d'examen blanc de {matiere} (niveau 5ème). "
        "Analyse les types et le niveau des exercices. "
        "Génère 2 ou 3 exercices similaires avec des données différentes, numérotés."
    )
    return model.generate_content([image, prompt]).text


def generer_pdf(matiere: str, sujet: str, mode: str, messages: list) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(15, 15, 15)
    pdf.set_fill_color(255, 107, 107)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 14, "Fiche de revision - Classe de 5eme", ln=True, align="C", fill=True)
    pdf.set_text_color(80, 80, 80)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"Matiere : {matiere}  |  Sujet : {sujet}  |  Mode : {mode}", ln=True, align="C")
    pdf.ln(8)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Contenu de la seance :", ln=True)
    pdf.ln(3)
    pdf.set_font("Arial", "", 11)
    for msg in messages:
        if msg["role"] == "assistant":
            safe = msg["content"].encode("latin-1", errors="replace").decode("latin-1")
            pdf.multi_cell(0, 7, safe)
            pdf.ln(3)
    pdf.ln(6)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(8)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Mes notes :", ln=True)
    pdf.ln(4)
    for _ in range(10):
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(9)
    return bytes(pdf.output())


# ==========================================
# HEADER
# ==========================================
st.markdown("""
<div class="hero-header">
    <h1>🎓 Ton Tuteur Personnel</h1>
    <p>Révise, progresse et prends confiance en toi ! 💪</p>
</div>
""", unsafe_allow_html=True)


# ==========================================
# ÉCRAN SETUP
# ==========================================
if not st.session_state.seance_lancee:

    st.markdown('<p class="section-title">1️⃣ Choisis ta matière</p>', unsafe_allow_html=True)
    cols = st.columns(4)
    for i, (mat, emoji) in enumerate(MATIERES.items()):
        is_sel = st.session_state.matiere_temp == mat
        css    = "mat-btn-selected" if is_sel else "mat-btn"
        label  = f"{'✅ ' if is_sel else ''}{emoji}\n{mat}"
        with cols[i % 4]:
            st.markdown(f'<div class="{css}">', unsafe_allow_html=True)
            if st.button(label, key=f"mat_{mat}", use_container_width=True):
                st.session_state.matiere_temp = mat
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    matiere_choisie = st.session_state.matiere_temp
    if matiere_choisie == "Autre":
        matiere_choisie = st.text_input("Précise ta matière :", placeholder="Ex: Technologie, Latin...")

    st.markdown("---")
    st.markdown('<p class="section-title">2️⃣ Qu\'est-ce que tu veux faire ?</p>', unsafe_allow_html=True)
    mode_cols = st.columns(2)
    modes = {
        "cours":    ("📚", "Comprendre le cours",  "QCM, vrai/faux, trous, paires"),
        "exercice": ("✏️", "Faire des exercices",   "Problèmes, schémas, remise en ordre"),
    }
    for i, (mode_key, (emoji, titre, desc)) in enumerate(modes.items()):
        is_sel = st.session_state.mode_temp == mode_key
        css    = "mode-btn-selected" if is_sel else "mode-btn"
        label  = f"{'✅ ' if is_sel else ''}{emoji} {titre}\n{desc}"
        with mode_cols[i]:
            st.markdown(f'<div class="{css}">', unsafe_allow_html=True)
            if st.button(label, key=f"mode_{mode_key}", use_container_width=True):
                st.session_state.mode_temp = mode_key
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # Info dynamique
    if st.session_state.matiere_temp and st.session_state.mode_temp:
        mat  = st.session_state.matiere_temp
        mode = st.session_state.mode_temp
        infos_cours = {
            "Mathématiques":  "🧠 QCM ou Vrai/Faux pour tester ta compréhension",
            "Physique-Chimie":"🧠 QCM ou Vrai/Faux pour tester ta compréhension",
            "SVT":            "🧠 QCM ou phrases à trous selon le sujet",
            "Histoire-Géo":   "🧠 QCM, QCM inversé ou phrases à trous",
            "Anglais":        "🃏 Associer des paires de vocabulaire",
            "Espagnol":       "🃏 Associer des paires de vocabulaire",
            "Français":       "🧠 QCM sur les notions de cours",
            "Autre":          "🧠 QCM sur les notions clés",
        }
        infos_exo = {
            "Mathématiques":  "✏️ Problèmes et schémas à compléter",
            "Physique-Chimie":"✏️ Problèmes et schémas à compléter",
            "SVT":            "✏️ Problèmes, schémas ou remise en ordre",
            "Histoire-Géo":   "✏️ Problèmes et exercices libres",
            "Anglais":        "✏️ Compréhension de texte ou exercice ouvert",
            "Espagnol":       "✏️ Compréhension de texte ou exercice ouvert",
            "Français":       "✏️ Problèmes et exercices de langue",
            "Autre":          "✏️ Problèmes et exercices libres",
        }
        info = infos_cours.get(mat, "🧠 Questions de cours") if mode == "cours" else infos_exo.get(mat, "✏️ Exercices pratiques")
        st.info(info)

    st.markdown("---")
    st.markdown('<p class="section-title">3️⃣ Sur quel sujet veux-tu travailler ?</p>', unsafe_allow_html=True)
    sujet = st.text_input(
        "", placeholder="Ex: Les fractions, La Révolution française, Les volcans...",
        label_visibility="collapsed",
    )

    st.markdown('<p class="section-title">4️⃣ Tu as un examen blanc ? <span style="font-weight:400;color:#6b7280">(optionnel)</span></p>', unsafe_allow_html=True)
    st.caption("📷 L'IA analyse ta copie et génère des exercices du même type.")
    photo = st.file_uploader("Dépose une photo ici", type=["png","jpg","jpeg"], label_visibility="collapsed")
    if photo:
        st.image(photo, caption="Photo reçue ✅", width=260)

    st.markdown("---")
    st.markdown('<div class="launch-btn">', unsafe_allow_html=True)
    lancer = st.button("🚀 Lancer ma séance !", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if lancer:
        if not matiere_choisie or matiere_choisie == "Autre":
            st.warning("⚠️ Choisis une matière !")
        elif not st.session_state.mode_temp:
            st.warning("⚠️ Choisis un mode !")
        elif not sujet.strip():
            st.warning("⚠️ Dis-moi sur quel sujet tu veux travailler !")
        else:
            with st.spinner("Ton tuteur se prépare... 🎯"):
                try:
                    ui_type = get_ui_type(matiere_choisie, st.session_state.mode_temp)
                    chat    = creer_chat(matiere_choisie, sujet, ui_type)
                    st.session_state.chat_session  = chat
                    st.session_state.matiere       = matiere_choisie
                    st.session_state.sujet         = sujet
                    st.session_state.mode          = st.session_state.mode_temp
                    st.session_state.ui_type       = ui_type
                    st.session_state.seance_lancee = True

                    if photo:
                        img = Image.open(photo)
                        exercices_photo = analyser_photo(img, matiere_choisie, ui_type)
                        chat.send_message(
                            f"Contexte examen blanc :\n{exercices_photo}\n"
                            "Utilise-le comme base pour les premières questions."
                        )

                    data, raw = generate_next(chat, matiere_choisie, sujet, "facile", True)
                    if data:
                        init_question(data)
                    else:
                        st.session_state.messages.append({"role": "assistant", "content": raw})
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erreur au démarrage : {e}")


# ==========================================
# SÉANCE EN COURS
# ==========================================
else:
    ui_type = st.session_state.ui_type
    matiere = st.session_state.matiere
    sujet   = st.session_state.sujet
    mode    = st.session_state.mode
    chat    = st.session_state.chat_session
    q       = st.session_state.current_question
    fmt     = q.get("format", "libre") if q else None

    # ── Barre contexte ──
    col_ctx, col_reset = st.columns([5, 1])
    with col_ctx:
        emoji_mat  = MATIERES.get(matiere, "📚")
        mode_label = "📚 Cours" if mode == "cours" else "✏️ Exercices"
        st.markdown(
            f'<div class="session-card">{emoji_mat} <b>{matiere}</b> — {sujet} &nbsp;|&nbsp; {mode_label}</div>',
            unsafe_allow_html=True,
        )
    with col_reset:
        st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
        if st.button("🔄 Reset", use_container_width=True):
            reset_seance()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Difficulté + score + vies ──
    diff = st.session_state.difficulty
    diff_css = f"diff-{diff}"
    col_d, col_s, col_v = st.columns(3)
    with col_d:
        st.markdown(f'<div class="diff-badge {diff_css}">{DIFFICULTY_LABELS[diff]}</div>', unsafe_allow_html=True)
    with col_s:
        st.markdown(f'<div class="score-badge">⭐ {st.session_state.score}/{st.session_state.total_questions}</div>', unsafe_allow_html=True)
    with col_v:
        if mode == "exercice":
            hearts = "❤️" * st.session_state.vies + "🖤" * (3 - st.session_state.vies)
            st.markdown(f'<div class="lives-display" style="font-size:1.2rem">{hearts}</div>', unsafe_allow_html=True)

    st.markdown("---")

    # ── Game over ──
    if st.session_state.game_over:
        st.error("💀 Plus de vies ! C'est la fin de la séance.")
        st.markdown(f"**Score final : {st.session_state.score} / {st.session_state.total_questions}** 🎯")
        st.markdown('<div class="launch-btn">', unsafe_allow_html=True)
        if st.button("🔄 Recommencer avec 3 vies", use_container_width=True):
            st.session_state.vies            = 3
            st.session_state.game_over       = False
            st.session_state.score           = 0
            st.session_state.total_questions = 0
            st.session_state.difficulty      = "facile"
            with st.spinner("On repart ! 🚀"):
                data, raw = generate_next(chat, matiere, sujet, "facile", False)
                if data:
                    init_question(data)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    elif q:
        answered = st.session_state.answered

        # ════════════════════════════════
        # QCM
        # ════════════════════════════════
        if fmt in ("qcm", "qcm_inverse"):
            if fmt == "qcm":
                st.markdown(f"### ❓ {q.get('question','')}")
            else:
                st.markdown("### 🔁 QCM Inversé — Quelle est la bonne question ?")
                st.markdown(f'<div class="question-card"><strong>Réponse donnée :</strong> {q.get("answer","")}</div>', unsafe_allow_html=True)

            choices = q.get("choices", {})
            correct = q.get("correct", "")
            ch_cols = st.columns(2)
            for i, (key, val) in enumerate(choices.items()):
                if answered:
                    if key == correct:           css = "choice-correct"
                    elif key == st.session_state.last_choice: css = "choice-wrong"
                    else:                        css = "choice-btn"
                else:
                    css = "choice-btn"
                with ch_cols[i % 2]:
                    st.markdown(f'<div class="{css}">', unsafe_allow_html=True)
                    if st.button(f"{key}. {val}", key=f"qcm_{key}", use_container_width=True, disabled=answered):
                        st.session_state.last_choice = key
                        if key == correct: handle_correct(mode)
                        else:              handle_wrong(mode)
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

            if answered:
                if st.session_state.last_answer_correct:
                    st.success(f"✅ Bravo ! {q.get('explanation','')}")
                else:
                    st.error(f"❌ La bonne réponse était **{correct}**. {q.get('explanation','')}")
                if not st.session_state.game_over:
                    next_question_button(chat, matiere, sujet, mode)

        # ════════════════════════════════
        # VRAI / FAUX
        # ════════════════════════════════
        elif fmt == "vrai_faux":
            st.markdown("### ✅❌ Vrai ou Faux ?")
            st.markdown(f'<div class="question-card">{q.get("statement","")}</div>', unsafe_allow_html=True)

            correct_vf = q.get("correct", True)
            vf_cols = st.columns(2)

            if answered:
                choice_was_correct = st.session_state.vf_choice == correct_vf
                with vf_cols[0]:
                    css = "vf-true" if correct_vf else ("vf-false" if not st.session_state.vf_choice else "vf-neutral")
                    st.markdown(f'<div class="{css}">', unsafe_allow_html=True)
                    st.button("✅ Vrai", key="vf_v", use_container_width=True, disabled=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                with vf_cols[1]:
                    css = "vf-false" if not correct_vf else ("vf-true" if st.session_state.vf_choice else "vf-neutral")
                    st.markdown(f'<div class="{css}">', unsafe_allow_html=True)
                    st.button("❌ Faux", key="vf_f", use_container_width=True, disabled=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                if st.session_state.last_answer_correct:
                    st.success(f"✅ Exactement ! {q.get('explanation','')}")
                else:
                    label = "VRAI" if correct_vf else "FAUX"
                    st.error(f"❌ C'était **{label}** ! {q.get('explanation','')}")
                if not st.session_state.game_over:
                    next_question_button(chat, matiere, sujet, mode)
            else:
                with vf_cols[0]:
                    st.markdown('<div class="vf-neutral">', unsafe_allow_html=True)
                    if st.button("✅ Vrai", key="vf_v", use_container_width=True):
                        st.session_state.vf_choice = True
                        if True == correct_vf: handle_correct(mode)
                        else:                  handle_wrong(mode)
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
                with vf_cols[1]:
                    st.markdown('<div class="vf-neutral">', unsafe_allow_html=True)
                    if st.button("❌ Faux", key="vf_f", use_container_width=True):
                        st.session_state.vf_choice = False
                        if False == correct_vf: handle_correct(mode)
                        else:                   handle_wrong(mode)
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

        # ════════════════════════════════
        # TROUS
        # ════════════════════════════════
        elif fmt == "trous":
            st.markdown(f"### ✏️ {q.get('instruction','Complète la phrase')}")
            text     = q.get("text", "")
            blanks   = q.get("blanks", [])
            # Affiche le texte avec les blancs remplacés par ___
            display  = re.sub(r"\[BLANK_\d+\]", '<span class="blank-placeholder">___</span>', text)
            st.markdown(f'<div class="trous-text">{display}</div>', unsafe_allow_html=True)
            st.markdown("")

            student_answers = []
            for i, correct_blank in enumerate(blanks):
                ans = st.text_input(f"Blanc {i+1} :", key=f"blank_{i}", disabled=answered)
                student_answers.append(ans)

            if not answered:
                st.markdown('<div class="launch-btn">', unsafe_allow_html=True)
                if st.button("✅ Valider", use_container_width=True, key="trous_valider"):
                    if all(a.strip() for a in student_answers):
                        results = [s.strip().lower() == c.strip().lower() for s, c in zip(student_answers, blanks)]
                        all_ok  = all(results)
                        if all_ok: handle_correct(mode)
                        else:      handle_wrong(mode)
                        st.rerun()
                    else:
                        st.warning("⚠️ Remplis tous les blancs avant de valider !")
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                # Feedback par blanc
                for i, (s, c) in enumerate(zip(student_answers, blanks)):
                    if s.strip().lower() == c.strip().lower():
                        st.success(f"Blanc {i+1} : ✅ **{c}**")
                    else:
                        st.error(f"Blanc {i+1} : ❌ Tu as écrit « {s} » → réponse attendue : **{c}**")
                st.markdown(f"*{q.get('explanation','')}*")
                if not st.session_state.game_over:
                    next_question_button(chat, matiere, sujet, mode)

        # ════════════════════════════════
        # PAIRES
        # ════════════════════════════════
        elif fmt == "paires":
            st.markdown(f"### 🔗 {q.get('instruction','Associe les éléments')}")
            pairs   = q.get("pairs", [])
            shuffled = st.session_state.paires_shuffled or [p["right"] for p in pairs]

            for i, pair in enumerate(pairs):
                col_l, col_r = st.columns(2)
                with col_l:
                    st.markdown(f'<div class="pair-left">→ {pair["left"]}</div>', unsafe_allow_html=True)
                with col_r:
                    if answered:
                        chosen = st.session_state.get(f"pair_{i}", "")
                        if chosen == pair["right"]:
                            st.success(f"✅ {chosen}")
                        else:
                            st.error(f"❌ {chosen} → correct : **{pair['right']}**")
                    else:
                        st.selectbox("", shuffled, key=f"pair_{i}", label_visibility="collapsed")

            if not answered:
                st.markdown('<div class="launch-btn">', unsafe_allow_html=True)
                if st.button("✅ Valider les associations", use_container_width=True, key="paires_valider"):
                    results = [st.session_state.get(f"pair_{i}") == p["right"] for i, p in enumerate(pairs)]
                    if all(results): handle_correct(mode)
                    else:            handle_wrong(mode)
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                results = [st.session_state.get(f"pair_{i}") == p["right"] for i, p in enumerate(pairs)]
                if all(results):
                    st.success(f"✅ Parfait ! {q.get('explanation','')}")
                else:
                    nb_ok = sum(results)
                    st.error(f"❌ {nb_ok}/{len(pairs)} bonnes associations. {q.get('explanation','')}")
                if not st.session_state.game_over:
                    next_question_button(chat, matiere, sujet, mode)

        # ════════════════════════════════
        # ORDRE
        # ════════════════════════════════
        elif fmt == "ordre":
            st.markdown(f"### 🔀 {q.get('instruction','Remets dans le bon ordre')}")
            items_shuffled = q.get("items_shuffled", [])
            correct_order  = q.get("correct_order", [])

            st.caption("Les étapes ci-dessous sont mélangées. Pour chaque position, choisis la bonne étape.")
            st.markdown("")

            for pos in range(len(correct_order)):
                st.selectbox(
                    f"Position {pos+1} :",
                    items_shuffled,
                    key=f"ordre_{pos}",
                    disabled=answered,
                )

            if not answered:
                st.markdown('<div class="launch-btn">', unsafe_allow_html=True)
                if st.button("✅ Valider l'ordre", use_container_width=True, key="ordre_valider"):
                    student_order = [st.session_state.get(f"ordre_{p}") for p in range(len(correct_order))]
                    all_ok = student_order == correct_order
                    if all_ok: handle_correct(mode)
                    else:      handle_wrong(mode)
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                student_order = [st.session_state.get(f"ordre_{p}") for p in range(len(correct_order))]
                all_ok = student_order == correct_order
                if all_ok:
                    st.success(f"✅ Ordre parfait ! {q.get('explanation','')}")
                else:
                    st.error("❌ Pas tout à fait... Voici le bon ordre :")
                    for i, step in enumerate(correct_order):
                        st.markdown(f"**{i+1}.** {step}")
                    st.markdown(f"*{q.get('explanation','')}*")
                if not st.session_state.game_over:
                    next_question_button(chat, matiere, sujet, mode)

        # ════════════════════════════════
        # LIBRE
        # ════════════════════════════════
        elif fmt == "libre":
            st.markdown("### 📝 Problème")
            st.info(q.get("problem", ""))

            if not st.session_state.hint_revealed:
                if st.button("💡 Voir un indice"):
                    st.session_state.hint_revealed = True
                    st.rerun()
            else:
                st.warning(f"💡 **Indice :** {q.get('hint','')}")

            if not answered:
                student_answer = st.text_input("✏️ Ta réponse :", placeholder="Écris ta réponse ici...", key="libre_input")
                st.markdown('<div class="launch-btn">', unsafe_allow_html=True)
                if st.button("✅ Valider ma réponse", use_container_width=True, key="libre_valider"):
                    if not student_answer.strip():
                        st.warning("⚠️ Écris ta réponse avant de valider !")
                    else:
                        with st.spinner("Ton tuteur vérifie... 🔍"):
                            result = evaluate_answer(chat, "libre", q.get("solution",""), student_answer.strip())
                            st.session_state.eval_result = result
                            if result.get("correct"): handle_correct(mode)
                            else:                      handle_wrong(mode)
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                result = st.session_state.eval_result or {}
                if result.get("correct"):
                    st.success(f"✅ {result.get('feedback','')}")
                else:
                    st.error(
                        f"❌ {result.get('feedback','')}  \n"
                        f"Réponse attendue : **{q.get('solution','')}**  \n"
                        f"*{q.get('explanation','')}*"
                    )
                if not st.session_state.game_over:
                    next_question_button(chat, matiere, sujet, mode, "➡️ Exercice suivant")

        # ════════════════════════════════
        # OUVERT
        # ════════════════════════════════
        elif fmt == "ouvert":
            st.markdown("### 💬 Exercice ouvert")
            st.info(q.get("prompt", ""))
            st.caption("Développe ta réponse en plusieurs phrases.")

            if not answered:
                student_answer = st.text_area("✏️ Ta réponse :", placeholder="Rédige ta réponse ici...", height=150, key="ouvert_input")
                st.markdown('<div class="launch-btn">', unsafe_allow_html=True)
                if st.button("✅ Envoyer ma réponse", use_container_width=True, key="ouvert_valider"):
                    if not student_answer.strip():
                        st.warning("⚠️ Écris ta réponse avant d'envoyer !")
                    else:
                        with st.spinner("Ton tuteur lit ta réponse... 📖"):
                            result = evaluate_answer(chat, "ouvert", q.get("criteria",[]), student_answer.strip())
                            st.session_state.eval_result = result
                            if result.get("correct"): handle_correct(mode)
                            else:                      handle_wrong(mode)
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                result = st.session_state.eval_result or {}
                if result.get("correct"):
                    st.success(f"✅ {result.get('feedback','')}")
                else:
                    st.error(f"❌ {result.get('feedback','')}  \n*{q.get('explanation','')}*")
                if not st.session_state.game_over:
                    next_question_button(chat, matiere, sujet, mode, "➡️ Exercice suivant")

        # ════════════════════════════════
        # FLASHCARD (Français si gardé)
        # ════════════════════════════════
        elif fmt == "flashcard":
            card = q
            st.markdown(f'<div class="flashcard-front">{card.get("front","")}</div>', unsafe_allow_html=True)
            if card.get("hint"):
                st.caption(f"💡 {card['hint']}")
            if not st.session_state.card_revealed:
                col_r = st.columns([1,2,1])
                with col_r[1]:
                    if st.button("🔄 Retourner la carte", use_container_width=True):
                        st.session_state.card_revealed = True
                        st.rerun()
            else:
                ex = f'<div class="flashcard-example">📝 {card["example"]}</div>' if card.get("example") else ""
                st.markdown(
                    f'<div class="flashcard-back"><strong>{card.get("back","")}</strong>{ex}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown("#### Tu savais ?")
                ec = st.columns(3)
                for idx, (lbl, pts) in enumerate([("✅ Je savais !", 1), ("🤔 Presque...", 0), ("❌ Je savais pas", 0)]):
                    with ec[idx]:
                        if st.button(lbl, key=f"eval_{idx}", use_container_width=True):
                            st.session_state.total_questions += 1
                            st.session_state.score           += pts
                            with st.spinner("Prochaine carte..."):
                                data, raw = generate_flashcard(chat, matiere, sujet, False)
                                if data: init_question(data)
                                else:    st.session_state.messages.append({"role":"assistant","content":raw})
                            st.rerun()

    # ════════════════════════════════════════
    # CHAT LIBRE
    # ════════════════════════════════════════
    st.markdown("---")
    with st.expander("💬 Poser une question au tuteur"):
        for msg in st.session_state.messages:
            avatar = "🎓" if msg["role"] == "assistant" else "🧑‍🎓"
            with st.chat_message(msg["role"], avatar=avatar):
                st.markdown(msg["content"])

        st.session_state.quick_replies_on = st.toggle("Boutons rapides", value=st.session_state.quick_replies_on)
        if st.session_state.quick_replies_on:
            qr_cols = st.columns(len(QUICK_REPLIES))
            for i, (label, text) in enumerate(QUICK_REPLIES):
                with qr_cols[i]:
                    st.markdown('<div class="qr-btn">', unsafe_allow_html=True)
                    if st.button(label, key=f"qr_{i}", use_container_width=True):
                        st.session_state.quick_reply_triggered = text
                    st.markdown("</div>", unsafe_allow_html=True)

        if st.session_state.quick_reply_triggered:
            user_msg = st.session_state.quick_reply_triggered
            st.session_state.quick_reply_triggered = None
            st.session_state.messages.append({"role":"user","content":user_msg})
            try:
                resp = st.session_state.chat_session.send_message(user_msg)
                raw  = re.sub(r"```json.*?```", "", resp.text, flags=re.DOTALL).strip()
                st.session_state.messages.append({"role":"assistant","content":raw})
            except Exception as e:
                st.error(f"❌ {e}")
            st.rerun()

        if user_input := st.chat_input("✏️ Pose ta question..."):
            st.session_state.messages.append({"role":"user","content":user_input})
            try:
                resp = st.session_state.chat_session.send_message(user_input)
                raw  = re.sub(r"```json.*?```", "", resp.text, flags=re.DOTALL).strip()
                st.session_state.messages.append({"role":"assistant","content":raw})
            except Exception as e:
                st.error(f"❌ {e}")
            st.rerun()

    # ════════════════════════════════════════
    # EXPORT PDF
    # ════════════════════════════════════════
    with st.expander("📥 Exporter ma séance en PDF"):
        st.caption("Génère une fiche imprimable avec le contenu de ta séance.")
        if st.button("📄 Générer ma fiche PDF"):
            try:
                pdf_bytes = generer_pdf(matiere, sujet, mode, st.session_state.messages)
                st.download_button(
                    label="⬇️ Télécharger le PDF",
                    data=pdf_bytes,
                    file_name=f"seance_{matiere.lower().replace(' ','_')}.pdf",
                    mime="application/pdf",
                )
            except Exception as e:
                st.error(f"❌ Erreur PDF : {e}")

    # Ballons si bonne performance
    if st.session_state.total_questions >= 5 and st.session_state.score / st.session_state.total_questions >= 0.8:
        st.balloons()
