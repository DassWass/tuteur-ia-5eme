import streamlit as st
import google.generativeai as genai
from PIL import Image
from fpdf import FPDF
import json
import re

st.set_page_config(
    page_title="Tuteur IA — 5ème",
    layout="centered",
    page_icon="🎓",
    initial_sidebar_state="collapsed",
)

# ==========================================
# GESTION DES CLÉS API (FALLBACK ANTI-QUOTA)
# ==========================================
def _load_api_keys():
    if "GEMINI_API_KEYS" in st.secrets:
        return list(st.secrets["GEMINI_API_KEYS"])
    if "GEMINI_API_KEY" in st.secrets:
        return [st.secrets["GEMINI_API_KEY"]]
    st.error("Clé API Gemini manquante dans les Secrets Streamlit.")
    st.stop()

API_KEYS = _load_api_keys()

if "current_api_index" not in st.session_state:
    st.session_state.current_api_index = 0

def _configure_api():
    idx = st.session_state.current_api_index
    if idx >= len(API_KEYS):
        st.error("Toutes les clés API sont épuisées (quota atteint). Reviens plus tard !")
        st.stop()
    genai.configure(api_key=API_KEYS[idx])

_configure_api()

def switch_to_next_key() -> bool:
    st.session_state.current_api_index += 1
    if st.session_state.current_api_index < len(API_KEYS):
        _configure_api()
        return True
    return False

# ==========================================
# CONSTANTES & CONFIGURATION IA
# ==========================================
MATIERES = {
    "Mathématiques":   "🔢",
    "Français":        "📖",
    "Histoire-Géo":    "🌍",
    "SVT":             "🌱",
    "Physique-Chimie": "⚗️",
    "Anglais":         "🇬🇧",
    "Espagnol":        "🇪🇸",
    "Autre":           "📝",
}
MATIERES_VIES      = {"Mathématiques", "Physique-Chimie", "Histoire-Géo", "SVT"}
MATIERES_FLASHCARD = {"Français", "Anglais", "Espagnol", "Autre"}

DIFFICULTY_ORDER  = ["facile", "moyen", "difficile"]
DIFFICULTY_LABELS = {
    "facile":    "🟢 Facile",
    "moyen":     "🟡 Moyen",
    "difficile": "🔴 Difficile",
}

MODEL_NAME = "gemini-2.5-flash-lite-preview-06-17"

GENERATION_CONFIG = genai.GenerationConfig(
    temperature=0.4,
    response_mime_type="application/json",
)

QUICK_REPLIES = [
    ("💡 Un indice",         "Je bloque, peux-tu me donner un indice ?"),
    ("🤔 J'ai pas compris",  "Je n'ai pas compris, peux-tu réexpliquer autrement ?"),
    ("✅ J'ai compris !",    "J'ai compris, on peut passer à la suite !"),
    ("🔄 Autre exercice",    "Peux-tu me proposer un exercice similaire différent ?"),
]

# ==========================================
# SYSTEM PROMPTS
# ==========================================
SYSTEM_BASE = """Tu es un tuteur super sympa, bienveillant et patient pour des élèves de 5ème (collège, 12-13 ans).
Utilise TOUJOURS le tutoiement, des emojis et un ton jeune et motivant.
Tes réponses JSON doivent être UNIQUEMENT du JSON valide, sans balises markdown, sans texte avant ou après.
RÈGLE: Strictement limité au programme de 5ème."""

SYSTEM_QCM = SYSTEM_BASE + """
Tu génères des QCM pour aider l'élève à comprendre et assimiler son cours.
Pour CHAQUE question, réponds UNIQUEMENT avec ce JSON :
{
  "question": "La question claire et précise",
  "choices": {"A": "...", "B": "...", "C": "...", "D": "..."},
  "correct": "A",
  "explanation": "Explication courte et encourageante (2-3 phrases, avec emoji)"
}
Génère des questions sur la compréhension du cours. Une seule bonne réponse parmi les 4.
Les mauvaises réponses doivent être plausibles."""

SYSTEM_VIES = SYSTEM_BASE + """
Tu génères des problèmes et exercices d'application à réponse libre.
Pour CHAQUE exercice, réponds UNIQUEMENT avec ce JSON :
{
  "problem": "L'énoncé complet du problème, clair et adapté au niveau 5ème",
  "solution": "La réponse exacte attendue (courte : un nombre, une date, un mot...)",
  "explanation": "Explication détaillée avec les étapes de raisonnement (3-4 phrases, avec emoji)",
  "hint": "Un indice utile qui guide sans donner la réponse"
}
Pour évaluer une réponse, tu recevras : EVAL|<solution>|<réponse_élève>
Réponds UNIQUEMENT avec : {"correct": true/false, "feedback": "Message encourageant (2-3 phrases, emoji)"}
Niveaux: facile (1 étape), moyen (2 étapes), difficile (2-3 étapes max)."""

SYSTEM_FLASHCARD = SYSTEM_BASE + """
Tu génères des flashcards pour mémoriser vocabulaire, règles ou conjugaisons.
Pour CHAQUE flashcard, réponds UNIQUEMENT avec ce JSON :
{
  "front": "Ce qui est affiché sur le recto (mot, expression, question)",
  "back": "La réponse complète au verso",
  "hint": "Un petit indice (peut être vide: '')",
  "example": "Un exemple d'usage en contexte (phrase courte)"
}"""

# ==========================================
# CSS
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

div[data-testid="stButton"].mat-btn > button {
    height:76px !important; border-radius:16px !important; font-weight:700 !important;
    background-color:#f4f6ff !important; border:2px solid #d4d9f5 !important;
    color:#1a1a2e !important; box-shadow:0 2px 6px rgba(0,0,0,0.06) !important;
    white-space:pre-line !important; line-height:1.4 !important; transition:all 0.18s ease !important;
}
div[data-testid="stButton"].mat-btn > button:hover {
    background-color:#4ECDC4 !important; color:#ffffff !important;
    border-color:#4ECDC4 !important; transform:translateY(-3px) !important;
}
div[data-testid="stButton"].mat-btn-selected > button {
    height:76px !important; border-radius:16px !important; font-weight:700 !important;
    background-color:#FF6B6B !important; color:#ffffff !important; border-color:#FF6B6B !important;
    box-shadow:0 4px 14px rgba(255,107,107,0.4) !important;
    white-space:pre-line !important; line-height:1.4 !important;
}
div[data-testid="stButton"].mode-btn > button {
    height:96px !important; border-radius:18px !important; font-size:0.95rem !important;
    font-weight:700 !important; background-color:#f4f6ff !important; border:2px solid #d4d9f5 !important;
    color:#1a1a2e !important; white-space:pre-line !important; line-height:1.5 !important;
    transition:all 0.18s !important; box-shadow:0 2px 6px rgba(0,0,0,0.06) !important;
}
div[data-testid="stButton"].mode-btn > button:hover {
    background-color:#FF8E53 !important; color:#ffffff !important; border-color:#FF8E53 !important;
}
div[data-testid="stButton"].mode-btn-selected > button {
    height:96px !important; border-radius:18px !important; font-size:0.95rem !important;
    font-weight:700 !important; background-color:#FF6B6B !important; color:#ffffff !important;
    border-color:#FF6B6B !important; white-space:pre-line !important; line-height:1.5 !important;
}

div[data-testid="stButton"].choice-btn > button {
    background-color:#f4f6ff !important; border-radius:14px !important; border:2px solid #d4d9f5 !important;
    width:100% !important; font-weight:600 !important; transition:all 0.15s !important;
}
div[data-testid="stButton"].choice-btn > button:hover {
    background-color:#4ECDC4 !important; color:#ffffff !important; border-color:#4ECDC4 !important;
}
div[data-testid="stButton"].choice-correct > button {
    background-color:#d4f5e9 !important; color:#0a5c36 !important;
    border:2px solid #28a745 !important; border-radius:14px !important; width:100% !important; font-weight:700 !important;
}
div[data-testid="stButton"].choice-wrong > button {
    background-color:#fde8e8 !important; color:#8b1a1a !important;
    border:2px solid #dc3545 !important; border-radius:14px !important; width:100% !important; font-weight:700 !important;
}

.session-card {
    background:linear-gradient(90deg,#f0fff8,#f0f4ff); border-left:5px solid #4ECDC4;
    border-radius:12px; padding:0.75rem 1.2rem; font-size:0.95rem;
    box-shadow:0 2px 8px rgba(78,205,196,0.15);
}
.score-badge {
    background:linear-gradient(135deg,#FFE66D,#FF8E53); border-radius:50px;
    padding:0.3rem 1rem; font-weight:700; font-size:0.9rem; display:inline-block;
    box-shadow:0 2px 8px rgba(255,142,83,0.30);
}
.diff-badge { border-radius:50px; padding:0.25rem 0.9rem; font-weight:700; font-size:0.88rem; display:inline-block; }
.diff-facile    { background:#e8f5e9; color:#2e7d32 !important; border:2px solid #a5d6a7; }
.diff-moyen     { background:#fff9e6; color:#e65100 !important; border:2px solid #ffcc80; }
.diff-difficile { background:#fde8e8; color:#8b1a1a !important; border:2px solid #ef9a9a; }
.lives-display  { font-size:1.6rem; text-align:center; padding:0.5rem; letter-spacing:0.3rem; }
.question-card  { background:#f8f9ff; border:2px solid #e0e4ff; border-radius:16px; padding:1.2rem 1.5rem; margin:0.8rem 0; }
.section-title  { font-size:1.05rem; font-weight:700; color:#1a1a2e !important; margin:1.2rem 0 0.6rem; }

.flashcard-front {
    background:linear-gradient(135deg,#4ECDC4,#2a9d8f); border-radius:20px; padding:2.5rem;
    text-align:center; color:#ffffff !important; font-size:1.4rem; font-weight:700;
    min-height:150px; display:flex; align-items:center; justify-content:center;
    box-shadow:0 8px 24px rgba(78,205,196,0.35); margin:1rem 0;
}
.flashcard-back {
    background:linear-gradient(135deg,#FF8E53,#FF6B6B); border-radius:20px; padding:2rem;
    text-align:center; color:#ffffff !important; font-size:1.1rem; min-height:150px;
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    box-shadow:0 8px 24px rgba(255,107,107,0.35); margin:1rem 0;
}
.flashcard-back strong { color:#ffffff !important; }
.flashcard-example {
    margin-top:0.8rem; font-style:italic; font-size:0.9rem; opacity:0.92;
    border-top:1px solid rgba(255,255,255,0.35); padding-top:0.6rem;
    width:100%; color:#ffffff !important;
}

div[data-testid="stButton"].qr-btn > button {
    background-color:#f4f6ff !important; color:#1a1a2e !important; border-radius:50px !important;
    border:2px solid #d4d9f5 !important; font-size:0.82rem !important; font-weight:600 !important;
    transition:all 0.15s !important;
}
div[data-testid="stButton"].qr-btn > button:hover {
    background-color:#4ECDC4 !important; color:#ffffff !important; border-color:#4ECDC4 !important;
}

[data-testid="stChatMessage"] {
    background-color:#f8f9ff !important; border-radius:14px !important; border:1px solid #e8ecf0 !important;
}
[data-testid="stCaptionContainer"] p { color:#6b7280 !important; }

@media (max-width: 768px) {
    .hero-header { padding:1.2rem 1.5rem; }
    .hero-header h1 { font-size:1.6rem; }
    div[data-testid="stButton"].mat-btn > button { height:60px !important; font-size:0.9rem !important; }
    div[data-testid="stButton"].mode-btn > button { height:80px !important; font-size:0.9rem !important; }
}
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
    "ui_type":               "",
    "chat_session":          None,
    "messages":              [],
    "quick_reply_triggered": None,
    "current_question":      None,
    "answered":              False,
    "last_answer_correct":   None,
    "score":                 0,
    "total_questions":       0,
    "consecutive_wrong":     0,
    "difficulty":            "facile",
    "vies":                  3,
    "game_over":             False,
    "hint_revealed":         False,
    "eval_result":           None,
    "last_choice":           None,
    "card_revealed":         False,
}

for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

def reset_seance():
    for k, v in _DEFAULTS.items():
        st.session_state[k] = v

def get_ui_type(matiere: str, mode: str) -> str:
    if mode == "cours":
        return "qcm"
    if matiere in MATIERES_VIES:
        return "vies"
    return "flashcard"

def update_difficulty(is_correct: bool):
    current = st.session_state.difficulty
    idx = DIFFICULTY_ORDER.index(current)
    if is_correct:
        st.session_state.consecutive_wrong = 0
        st.session_state.difficulty = DIFFICULTY_ORDER[min(idx + 1, 2)]
    else:
        st.session_state.consecutive_wrong += 1
        if st.session_state.consecutive_wrong >= 2:
            st.session_state.difficulty = DIFFICULTY_ORDER[max(idx - 1, 0)]
            st.session_state.consecutive_wrong = 0

# ==========================================
# GEMINI HELPERS
# ==========================================

def _make_model(system_prompt: str):
    return genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=system_prompt,
        generation_config=GENERATION_CONFIG,
    )

def creer_chat(matiere: str, sujet: str, ui_type: str):
    if ui_type == "vies":
        base = SYSTEM_VIES
    elif ui_type == "flashcard":
        base = SYSTEM_FLASHCARD
    else:
        base = SYSTEM_QCM
    system = base + f"\n\nMatière : {matiere}\nSujet : {sujet}"
    return _make_model(system).start_chat(history=[])

def parse_json_response(text: str) -> dict | None:
    try:
        return json.loads(text)
    except Exception:
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

def _call_with_retry(fn):
    max_retries = len(API_KEYS)
    for attempt in range(max_retries):
        try:
            return fn(), None
        except Exception as e:
            err = str(e).lower()
            if "429" in err or "quota" in err or "exhausted" in err or "resource_exhausted" in err:
                st.toast("Quota API atteint, bascule sur la clé de secours...", icon="🔄")
                if not switch_to_next_key():
                    return None, "Toutes les clés API sont épuisées."
            elif "404" in err or "not found" in err:
                return None, f"Modèle introuvable. Vérifie le nom du modèle ({MODEL_NAME})."
            else:
                return None, f"Erreur inattendue : {e}"
    return None, "Échec après plusieurs tentatives."

def generate_next(chat_session, sujet: str, difficulty: str, is_first: bool) -> tuple:
    if is_first:
        prompt = f"Génère la première question/exercice sur le sujet : {sujet}. Commence par une courte blague rigolote (1 ligne), puis génère le JSON."
    else:
        prompt = f"Question/exercice suivant de niveau {difficulty}. Différent des précédents. JSON uniquement."

    result, err = _call_with_retry(lambda: chat_session.send_message(prompt))
    if err:
        return None, f"❌ {err}"
    data = parse_json_response(result.text)
    return data, result.text

def evaluate_answer(chat_session, solution: str, student_answer: str) -> dict:
    prompt = f"EVAL|{solution}|{student_answer}"
    result, err = _call_with_retry(lambda: chat_session.send_message(prompt))
    if err:
        return {"correct": False, "feedback": f"Erreur : {err}"}
    data = parse_json_response(result.text)
    return data if data else {"correct": False, "feedback": "Réponse non évaluable. Réessaie !"}

def init_question(data: dict):
    st.session_state.current_question    = data
    st.session_state.answered            = False
    st.session_state.last_answer_correct = None
    st.session_state.last_choice         = None
    st.session_state.hint_revealed       = False
    st.session_state.eval_result         = None
    st.session_state.card_revealed       = False

def handle_correct():
    st.session_state.score           += 1
    st.session_state.total_questions += 1
    st.session_state.answered         = True
    st.session_state.last_answer_correct = True
    update_difficulty(True)

def handle_wrong(deduct_life: bool = False):
    st.session_state.total_questions += 1
    st.session_state.answered         = True
    st.session_state.last_answer_correct = False
    update_difficulty(False)
    if deduct_life:
        st.session_state.vies -= 1
        if st.session_state.vies <= 0:
            st.session_state.game_over = True

def analyser_photo(image: Image.Image, ui_type: str) -> str:
    base = SYSTEM_VIES if ui_type == "vies" else SYSTEM_QCM
    model = _make_model(base)
    response = model.generate_content([
        image,
        "Analyse cette photo d'examen et génère des exercices similaires (données différentes, sans corrections)."
    ])
    return response.text

def remove_emojis(text: str) -> str:
    if not text:
        return ""
    return text.encode("ascii", "ignore").decode("ascii")

def generer_pdf(matiere: str, sujet: str, mode: str, messages: list) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(15, 15, 15)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 14, remove_emojis("Fiche de revision - Classe de 5eme"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, remove_emojis(f"Matiere: {matiere} | Sujet: {sujet} | Mode: {mode}"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, remove_emojis("Contenu de la seance :"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("Helvetica", "", 11)
    for msg in messages:
        if msg["role"] == "assistant":
            clean = remove_emojis(msg["content"])
            if len(clean) > 1000:
                clean = clean[:997] + "..."
            pdf.multi_cell(0, 7, clean)
            pdf.ln(3)
    pdf.ln(6)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(8)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Mes notes :", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    for _ in range(10):
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(9)
    return bytes(pdf.output())

def load_next_question():
    chat  = st.session_state.chat_session
    sujet = st.session_state.sujet
    diff  = st.session_state.difficulty
    data, raw = generate_next(chat, sujet, diff, False)
    if data:
        init_question(data)
    else:
        st.session_state.messages.append({"role": "assistant", "content": raw})

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
        matiere_choisie = st.text_input(
            "Précise ta matière :", placeholder="Ex: Technologie, Latin, Musique..."
        )

    st.markdown("---")
    st.markdown('<p class="section-title">2️⃣ Qu\'est-ce que tu veux faire ?</p>', unsafe_allow_html=True)

    mode_cols = st.columns(2)
    modes = {
        "cours":    ("📚", "Comprendre le cours",  "QCM sur les notions clés"),
        "exercice": ("✏️", "Faire des exercices",   "Problèmes, flashcards"),
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

    if st.session_state.matiere_temp and st.session_state.mode_temp:
        ui = get_ui_type(st.session_state.matiere_temp, st.session_state.mode_temp)
        infos = {
            "qcm":       "🧠 Mode QCM — 4 propositions, clique sur la bonne réponse !",
            "vies":      "❤️ Mode Exercices — 3 vies, problèmes à résoudre librement",
            "flashcard": "🃏 Mode Flashcards — recto / verso, teste ta mémoire !",
        }
        st.info(infos[ui])

    st.markdown("---")
    sujet = st.text_input(
        "3️⃣ Sur quel sujet veux-tu travailler ?",
        placeholder="Ex: Les fractions, La Révolution française, Les volcans...",
    )

    st.markdown('<p class="section-title">4️⃣ Tu as un examen blanc ? <span style="font-weight:400;color:#6b7280">(optionnel)</span></p>', unsafe_allow_html=True)
    st.caption("L'IA analyse ta copie et génère des exercices du même type pour t'entraîner.")
    photo = st.file_uploader("Dépose une photo ici", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
    if photo:
        st.image(photo, caption="Photo reçue ✅", width=260)

    st.markdown("---")
    if st.button("🚀 Lancer ma séance !", use_container_width=True):
        if not matiere_choisie or matiere_choisie == "Autre":
            st.warning("Choisis une matière !")
            st.stop()
        if not st.session_state.mode_temp:
            st.warning("Choisis un mode (cours ou exercices) !")
            st.stop()
        if not sujet.strip():
            st.warning("Dis-moi sur quel sujet tu veux travailler !")
            st.stop()

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
                    with st.spinner("Analyse de ta copie..."):
                        exercices_photo = analyser_photo(img, ui_type)
                    chat.send_message(
                        f"Contexte examen blanc fourni par l'élève :\n{exercices_photo}\n"
                        "Utilise ces exercices comme base pour les premières questions."
                    )

                data, raw = generate_next(chat, sujet, "facile", True)
                if data:
                    init_question(data)
                else:
                    st.session_state.messages.append({"role": "assistant", "content": raw})

                st.rerun()
            except Exception as e:
                st.error(f"Erreur au démarrage : {e}")

# ==========================================
# SÉANCE EN COURS
# ==========================================
else:
    ui_type  = st.session_state.ui_type
    matiere  = st.session_state.matiere
    sujet    = st.session_state.sujet
    mode     = st.session_state.mode
    chat     = st.session_state.chat_session
    q        = st.session_state.current_question
    answered = st.session_state.answered

    col_ctx, col_reset = st.columns([5, 1])
    with col_ctx:
        emoji_mat  = MATIERES.get(matiere, "📚")
        mode_label = "📚 Cours" if mode == "cours" else "✏️ Exercices"
        st.markdown(
            f'<div class="session-card">{emoji_mat} <b>{matiere}</b> — {sujet} &nbsp;|&nbsp; {mode_label}</div>',
            unsafe_allow_html=True,
        )
    with col_reset:
        if st.button("🔄 Reset", use_container_width=True):
            reset_seance()
            st.rerun()

    diff = st.session_state.difficulty
    col_d, col_s, col_v = st.columns(3)
    with col_d:
        st.markdown(f'<div class="diff-badge diff-{diff}">{DIFFICULTY_LABELS[diff]}</div>', unsafe_allow_html=True)
    with col_s:
        st.markdown(
            f'<div class="score-badge">⭐ {st.session_state.score}/{st.session_state.total_questions}</div>',
            unsafe_allow_html=True,
        )
    with col_v:
        if ui_type == "vies":
            hearts = "❤️" * st.session_state.vies + "🖤" * (3 - st.session_state.vies)
            st.markdown(f'<div class="lives-display">{hearts}</div>', unsafe_allow_html=True)

    st.markdown("---")

    # ══════════════════════════════════════════════
    # GAME OVER
    # ══════════════════════════════════════════════
    if st.session_state.game_over:
        st.error("Plus de vies ! C'est la fin de la séance.")
        st.markdown(f"**Score final : {st.session_state.score} / {st.session_state.total_questions}** 🎯")
        if st.button("🔄 Recommencer avec 3 vies", use_container_width=True):
            st.session_state.vies            = 3
            st.session_state.game_over       = False
            st.session_state.score           = 0
            st.session_state.total_questions = 0
            st.session_state.consecutive_wrong = 0
            st.session_state.difficulty      = "facile"
            with st.spinner("On repart ! 🚀"):
                data, raw = generate_next(chat, sujet, "facile", True)
                if data:
                    init_question(data)
                else:
                    st.session_state.messages.append({"role": "assistant", "content": raw})
            st.rerun()

    # ══════════════════════════════════════════════
    # MODE QCM
    # ══════════════════════════════════════════════
    elif ui_type == "qcm" and q:
        with st.container():
            st.markdown('<div class="question-card">', unsafe_allow_html=True)
            st.markdown(f"### ❓ {q.get('question', '')}")
            st.markdown("")

            choices = q.get("choices", {})
            correct = q.get("correct", "")

            ch_cols = st.columns(2)
            for i, (key, val) in enumerate(choices.items()):
                if answered:
                    if key == correct:
                        css = "choice-correct"
                    elif key == st.session_state.last_choice and key != correct:
                        css = "choice-wrong"
                    else:
                        css = "choice-btn"
                else:
                    css = "choice-btn"

                with ch_cols[i % 2]:
                    st.markdown(f'<div class="{css}">', unsafe_allow_html=True)
                    if st.button(f"{key}. {val}", key=f"qcm_{key}", use_container_width=True, disabled=answered):
                        st.session_state.last_choice = key
                        if key == correct:
                            handle_correct()
                        else:
                            handle_wrong(deduct_life=False)
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

            if answered:
                if st.session_state.last_answer_correct:
                    st.success(f"✅ Bravo ! {q.get('explanation', '')}")
                else:
                    st.error(f"❌ Pas tout à fait... La bonne réponse était **{correct}**. {q.get('explanation', '')}")
                st.markdown("")
                if st.button("➡️ Question suivante", use_container_width=True, key="qcm_next"):
                    with st.spinner("Chargement..."):
                        load_next_question()
                    st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════
    # MODE VIES (exercices libres)
    # ══════════════════════════════════════════════
    elif ui_type == "vies" and q:
        with st.container():
            st.markdown('<div class="question-card">', unsafe_allow_html=True)
            st.markdown("### 📝 Problème")
            st.info(q.get("problem", q.get("question", "Énoncé non disponible.")))

            if q.get("hint") and not st.session_state.hint_revealed:
                if st.button("💡 Voir un indice"):
                    st.session_state.hint_revealed = True
                    st.rerun()
            elif st.session_state.hint_revealed:
                st.warning(f"💡 Indice : {q.get('hint', '')}")

            st.markdown("")
            if not answered:
                student_answer = st.text_input(
                    "✏️ Ta réponse :",
                    placeholder="Écris ta réponse ici...",
                    key="student_answer_input",
                )
                if st.button("✅ Valider ma réponse", use_container_width=True):
                    if not student_answer.strip():
                        st.warning("Écris ta réponse avant de valider !")
                    else:
                        with st.spinner("Ton tuteur vérifie... 🔍"):
                            res = evaluate_answer(chat, q.get("solution", ""), student_answer.strip())
                        st.session_state.eval_result = res
                        if res.get("correct"):
                            handle_correct()
                        else:
                            handle_wrong(deduct_life=True)
                        st.rerun()
            else:
                res = st.session_state.eval_result or {}
                if res.get("correct"):
                    st.success(f"✅ {res.get('feedback', '')}")
                else:
                    st.error(
                        f"❌ {res.get('feedback', '')}  \n"
                        f"La bonne réponse était : **{q.get('solution', '')}**  \n"
                        f"*{q.get('explanation', '')}*"
                    )

                if not st.session_state.game_over:
                    st.markdown("")
                    if st.button("➡️ Exercice suivant", use_container_width=True, key="vies_next"):
                        with st.spinner("Chargement..."):
                            load_next_question()
                        st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════
    # MODE FLASHCARD
    # ══════════════════════════════════════════════
    elif ui_type == "flashcard" and q:
        total = st.session_state.total_questions
        score = st.session_state.score
        col_sc = st.columns(3)
        with col_sc[0]: st.markdown(f"✅ **{score}** sus")
        with col_sc[1]: st.markdown(f"📚 **{total}** cartes")
        with col_sc[2]:
            ratio = int(score / total * 100) if total > 0 else 0
            st.markdown(f"🎯 **{ratio}%**")

        st.markdown("")
        st.markdown(
            f'<div class="flashcard-front">{q.get("front", "")}</div>',
            unsafe_allow_html=True,
        )
        if q.get("hint"):
            st.caption(f"💡 Indice : {q['hint']}")

        if not st.session_state.card_revealed:
            col_r = st.columns([1, 2, 1])
            with col_r[1]:
                if st.button("🔄 Retourner la carte", use_container_width=True):
                    st.session_state.card_revealed = True
                    st.rerun()
        else:
            example_html = ""
            if q.get("example"):
                example_html = f'<div class="flashcard-example">📝 {q["example"]}</div>'
            st.markdown(
                f'<div class="flashcard-back">'
                f'<div><strong>{q.get("back", "")}</strong></div>'
                f'{example_html}'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.markdown("#### Tu savais ?")
            eval_cols = st.columns(3)
            evals = [("✅ Je savais !", 1), ("🤔 Presque...", 0), ("❌ Je savais pas", 0)]
            for idx, (label, pts) in enumerate(evals):
                with eval_cols[idx]:
                    if st.button(label, key=f"fc_eval_{idx}", use_container_width=True):
                        st.session_state.total_questions += 1
                        st.session_state.score           += pts
                        with st.spinner("Prochaine carte..."):
                            load_next_question()
                        st.rerun()

    # Filet de sécurité : JSON invalide
    elif not st.session_state.game_over:
        st.warning("Oups, le tuteur a eu un petit hoquet de réflexion (format invalide).")
        if st.button("🔄 Retenter une génération", use_container_width=True):
            with st.spinner("Génération en cours..."):
                load_next_question()
            st.rerun()

    # ══════════════════════════════════════════════
    # CHAT LIBRE
    # ══════════════════════════════════════════════
    st.markdown("---")
    with st.expander("💬 Poser une question au tuteur"):
        for msg in st.session_state.messages:
            avatar = "🎓" if msg["role"] == "assistant" else "🧑‍🎓"
            with st.chat_message(msg["role"], avatar=avatar):
                st.markdown(msg["content"])

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
            st.session_state.messages.append({"role": "user", "content": user_msg})
            result, err = _call_with_retry(lambda: chat.send_message(user_msg))
            if result:
                raw = re.sub(r"```json.*?```", "", result.text, flags=re.DOTALL).strip()
                st.session_state.messages.append({"role": "assistant", "content": raw})
            elif err:
                st.error(err)
            st.rerun()

        if user_input := st.chat_input("✏️ Pose ta question..."):
            st.session_state.messages.append({"role": "user", "content": user_input})
            result, err = _call_with_retry(lambda: chat.send_message(user_input))
            if result:
                raw = re.sub(r"```json.*?```", "", result.text, flags=re.DOTALL).strip()
                st.session_state.messages.append({"role": "assistant", "content": raw})
            elif err:
                st.error(err)
            st.rerun()

    # ══════════════════════════════════════════════
    # EXPORT PDF
    # ══════════════════════════════════════════════
    with st.expander("📥 Exporter ma séance en PDF"):
        st.caption("Génère une fiche imprimable avec le contenu de ta séance.")
        include_full = st.checkbox("Inclure toutes les questions", value=False)
        if st.button("📄 Générer ma fiche PDF"):
            try:
                msgs = st.session_state.messages if include_full else st.session_state.messages[-10:]
                with st.spinner("Génération du PDF..."):
                    pdf_bytes = generer_pdf(matiere, sujet, mode, msgs)
                st.download_button(
                    label="⬇️ Télécharger le PDF",
                    data=pdf_bytes,
                    file_name=f"seance_{matiere.lower().replace(' ', '_')}.pdf",
                    mime="application/pdf",
                )
            except Exception as e:
                st.error(f"Erreur PDF : {e}")

    # Ballons si bonne performance
    total_q = st.session_state.total_questions
    if total_q >= 5 and st.session_state.score / total_q >= 0.8:
        st.balloons()
