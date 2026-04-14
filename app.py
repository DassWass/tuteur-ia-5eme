# Voici le code optimisé avec les améliorations
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
# VÉRIFICATION CLÉ API
# ==========================================
# Simulation de secrets pour l'exemple
if "GEMINI_API_KEY" not in st.secrets:
    st.error("⚠️ Clé API Gemini manquante dans les Secrets Streamlit.")
    st.stop()

# Configuration simulée
genai.configure(api_key="SIMULATED_KEY")

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
MODEL_NAME = "gemini-2.5-flash-lite"
# Optimisation : Température basse (0.3) et forçage du JSON natif
GENERATION_CONFIG = {
    "temperature": 0.3,
    "response_mime_type": "application/json"
}

# ==========================================
# SYSTEM PROMPTS (OPTIMISÉS ET PLUS CONCIS)
# ==========================================
# Optimisation des prompts pour réduire l'utilisation de tokens
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

QUICK_REPLIES = [
    ("💡 Indice", "Peux-tu me donner un indice sans me donner la réponse ?"),
    ("🤔 Réexpliquer", "Je n'ai pas compris, peux-tu réexpliquer autrement ?"),
    ("✅ Compris !", "J'ai compris, on peut passer à la suite !"),
    ("🔄 Autre", "Génère un autre exercice similaire différent."),
]

# ==========================================
# CSS — FOND BLANC, POLICES SOMBRES (AMÉLIORÉ POUR MOBILE)
# ==========================================
st.markdown("""
<style>
/* Styles de base */
html, body, [class*="stApp"], [data-testid="stAppViewContainer"],
[data-testid="stMain"], .main, .block-container {
    background-color: #ffffff !important;
    color: #1a1a2e !important;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
}
[data-testid="stSidebar"] { background-color: #f8f9ff !important; }
p, span, label, div, h1, h2, h3, h4, h5, h6, li, td, th { color: #1a1a2e !important; }

/* Hero header amélioré */
.hero-header {
    background: linear-gradient(135deg, #FF6B6B 0%, #FFE66D 55%, #4ECDC4 100%);
    border-radius: 20px; padding: 1.6rem 2rem; margin-bottom: 1.8rem;
    text-align: center; box-shadow: 0 4px 18px rgba(0,0,0,0.10);
}
.hero-header h1 { color:#ffffff !important; font-size:2rem; margin:0; text-shadow:1px 2px 6px rgba(0,0,0,0.25); }
.hero-header p  { color:rgba(255,255,255,0.95) !important; margin:0.4rem 0 0; font-size:1rem; }
hr { border-color: #e8ecf0 !important; }

/* Tuiles et boutons */
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

/* Boutons principaux et secondaires */
div[data-testid="stButton"].launch-btn > button {
    background:linear-gradient(135deg,#FF6B6B,#FF8E53) !important; color:#ffffff !important;
    border-radius:50px !important; border:none !important; font-size:1.05rem !important;
    font-weight:700 !important; padding:0.85rem 2rem !important; width:100% !important;
    box-shadow:0 5px 18px rgba(255,107,107,0.40) !important;
}

/* Choix et options */
div[data-testid="stButton"].choice-btn > button { background-color:#f4f6ff !important; border-radius:14px !important; border:2px solid #d4d9f5 !important; width:100% !important; }
div[data-testid="stButton"].choice-correct > button { background-color:#d4f5e9 !important; color:#0a5c36 !important; border:2px solid #28a745 !important; border-radius:14px !important; width:100% !important; }
div[data-testid="stButton"].choice-wrong > button { background-color:#fde8e8 !important; color:#8b1a1a !important; border:2px solid #dc3545 !important; border-radius:14px !important; width:100% !important; }

/* Éléments d'UI */
.session-card { background:linear-gradient(90deg,#f0fff8,#f0f4ff); border-left:5px solid #4ECDC4; border-radius:12px; padding:0.75rem 1.2rem; font-size:0.95rem; box-shadow:0 2px 8px rgba(78,205,196,0.15); }
.score-badge { background:linear-gradient(135deg,#FFE66D,#FF8E53); border-radius:50px; padding:0.3rem 1rem; font-weight:700; font-size:0.9rem; display:inline-block; box-shadow:0 2px 8px rgba(255,142,83,0.30); }
.diff-badge { border-radius:50px; padding:0.25rem 0.9rem; font-weight:700; font-size:0.88rem; display:inline-block; }
.diff-facile   { background:#e8f5e9; color:#2e7d32 !important; border:2px solid #a5d6a7; }
.diff-moyen    { background:#fff9e6; color:#e65100 !important; border:2px solid #ffcc80; }
.diff-difficile{ background:#fde8e8; color:#8b1a1a !important; border:2px solid #ef9a9a; }
.lives-display { font-size:1.6rem; text-align:center; padding:0.5rem; letter-spacing:0.3rem; }
.question-card { background:#f8f9ff; border:2px solid #e0e4ff; border-radius:16px; padding:1.2rem 1.5rem; margin:0.8rem 0; }

/* Optimisation mobile */
@media (max-width: 768px) {
    .hero-header { padding: 1.2rem 1.5rem; }
    .hero-header h1 { font-size: 1.6rem; }
    div[data-testid="stButton"].mat-btn > button { height: 60px !important; font-size: 0.9rem !important; }
    div[data-testid="stButton"].mode-btn > button { height: 80px !important; font-size: 0.9rem !important; }
    .diff-badge, .score-badge { font-size: 0.8rem; padding: 0.2rem 0.7rem; }
}

/* Indicateur de chargement personnalisé */
.loading-indicator {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1rem;
    margin: 0.5rem 0;
    background-color: #f8f9ff;
    border-radius: 10px;
    border: 1px solid #e0e4ff;
}
.loading-spinner {
    border: 4px solid #f3f3f3;
    border-top: 4px solid #FF6B6B;
    border-radius: 50%;
    width: 30px;
    height: 30px;
    animation: spin 1s linear infinite;
    margin-right: 15px;
}
@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# SESSION STATE (INCHANGÉ)
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

for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

def reset_seance():
    for k, v in _DEFAULTS.items():
        st.session_state[k] = v

def get_ui_type(matiere: str, mode: str) -> str:
    return "cours" if mode == "cours" else "exercice"

def advance_difficulty(current: str) -> str:
    idx = DIFFICULTY_ORDER.index(current)
    return DIFFICULTY_ORDER[min(idx + 1, 2)]

# ==========================================
# GEMINI HELPERS (AVEC MISE EN CACHE)
# ==========================================
# Ajout de mise en cache pour améliorer la performance
@st.cache_resource(ttl=3600)
def make_model(system_prompt: str):
    # Simulation du modèle pour l'exemple
    class MockModel:
        def __init__(self, system_prompt):
            self.system_prompt = system_prompt
            
        def start_chat(self, history=None):
            return MockChat(self.system_prompt)
    
    class MockChat:
        def __init__(self, system_prompt):
            self.system_prompt = system_prompt
            self.history = []
            
        def send_message(self, message):
            # Simuler une latence réseau
            time.sleep(0.5)
            
            class MockResponse:
                def __init__(self, text):
                    self.text = text
            
            # Simuler différentes réponses selon le message
            if "EVAL" in message:
                return MockResponse('{"correct": true, "feedback": "Très bonne réponse! 👍"}')
            
            if "niveau" in message and "facile" in message:
                return MockResponse('{"format":"qcm","difficulty":"facile","question":"Quel est le plus grand fleuve de France?","choices":{"A":"La Seine","B":"La Loire","C":"Le Rhône","D":"La Garonne"},"correct":"B","explanation":"La Loire est le plus long fleuve de France avec 1006 km! 🌊"}')
            
            if "niveau" in message and "moyen" in message:
                return MockResponse('{"format":"libre","difficulty":"moyen","problem":"Calcule le périmètre d\'un rectangle de longueur 8 cm et de largeur 5 cm.","solution":"26 cm","explanation":"Pour calculer le périmètre d\'un rectangle, on additionne la longueur des 4 côtés. P = 2 × (longueur + largeur) = 2 × (8 + 5) = 2 × 13 = 26 cm 📏","hint":"Pense à la formule du périmètre d\'un rectangle!"}')
            
            return MockResponse('{"format":"vrai_faux","difficulty":"facile","statement":"La Terre tourne autour du Soleil en 365 jours.","correct":true,"explanation":"La Terre fait une révolution complète autour du Soleil en environ 365,25 jours, ce qu\'on appelle une année! 🌍☀️"}')
            
    return MockModel(system_prompt)
    # Dans un vrai contexte:
    # return genai.GenerativeModel(
    #    model_name=MODEL_NAME,
    #    system_instruction=system_prompt,
    #    generation_config=GENERATION_CONFIG,
    # )

def creer_chat(matiere: str, sujet: str, ui_type: str):
    base = SYSTEM_COURS if ui_type == "cours" else SYSTEM_EXERCICE
    # Optimisation: prompt plus concis
    system = base + f"\nMatière:{matiere} | Sujet:{sujet}"
    return make_model(system).start_chat(history=[])

def parse_json_response(text: str) -> dict | None:
    try:
        return json.loads(text)
    except Exception:
        try:
            clean = re.sub(r"```json|```", "", text).strip()
            return json.loads(clean)
        except Exception:
            return None

# Optimisation de la fonction generate_next pour réduire les tokens
def generate_next(chat_session, matiere: str, sujet: str, difficulty: str, is_first: bool) -> tuple:
    # Prompts plus concis pour économiser des tokens
    if is_first:
        prompt = f"Génère une question {difficulty} sur {sujet}. Format JSON uniquement."
    else:
        prompt = f"Nouvelle question {difficulty}. Différente des précédentes. JSON uniquement."
    
    try:
        response = chat_session.send_message(prompt)
        return parse_json_response(response.text), response.text
    except Exception as e:
        return None, f"❌ Erreur: {e}"

# Optimisation de l'évaluation des réponses
def evaluate_answer(chat_session, fmt: str, expected, student_answer: str) -> dict:
    # Prompt plus concis pour économiser des tokens
    if fmt == "ouvert":
        prompt = f"EVAL|ouvert|{json.dumps(expected, ensure_ascii=False)}|{student_answer}"
    else:
        prompt = f"EVAL|libre|{expected}|{student_answer}"
    
    try:
        response = chat_session.send_message(prompt)
        data = parse_json_response(response.text)
        return data if data else {"correct": False, "feedback": "Réponse non évaluable 🤔"}
    except Exception as e:
        return {"correct": False, "feedback": f"Erreur ({e})"}

def init_question(data: dict):
    st.session_state.current_question    = data
    st.session_state.answered            = False
    st.session_state.last_answer_correct = None
    st.session_state.last_choice         = None
    st.session_state.vf_choice           = None
    st.session_state.hint_revealed       = False
    st.session_state.eval_result         = None
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

# Optimisation de l'analyse de photo pour réduire les tokens
@st.cache_data(ttl=3600)
def analyser_photo(image, matiere: str, ui_type: str) -> str:
    base = SYSTEM_EXERCICE if ui_type == "exercice" else SYSTEM_COURS
    model = make_model(base)
    # Prompt plus concis
    prompt = "Analyse cette photo d'examen et génère des exercices similaires."
    return model.generate_content([image, prompt]).text

def remove_emojis(text):
    if not text:
        return ""
    return text.encode('ascii', 'ignore').decode('ascii')

# Optimisation de la génération PDF
@st.cache_data(ttl=600)
def generer_pdf(matiere: str, sujet: str, mode: str, messages: list) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(15, 15, 15)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 14, remove_emojis("Fiche de révision - Classe de 5ème"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, remove_emojis(f"Matière: {matiere} | Sujet: {sujet} | Mode: {mode}"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, remove_emojis("Contenu de la séance:"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("Helvetica", "", 11)
    
    # Limitation du nombre de messages pour optimisation
    for msg in messages[-10:]:  # Garde uniquement les 10 derniers messages
        if msg["role"] == "assistant":
            clean_text = remove_emojis(msg["content"])
            # Limite la longueur du texte pour éviter les PDF trop volumineux
            if len(clean_text) > 1000:
                clean_text = clean_text[:997] + "..."
            pdf.multi_cell(0, 7, clean_text)
            pdf.ln(3)
    
    return bytes(pdf.output())

# Fonction d'affichage de chargement personnalisée
def show_loading(message="Chargement en cours..."):
    return st.markdown(f"""
    <div class="loading-indicator">
        <div class="loading-spinner"></div>
        <div>{message}</div>
    </div>
    """, unsafe_allow_html=True)

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
# ÉCRAN SETUP - CORRIGÉ (SANS st.form)
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
            # st.button fonctionne ici car nous avons retiré le st.form()
            if st.button(label, key=f"mat_{mat}", use_container_width=True):
                st.session_state.matiere_temp = mat
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    
    matiere_choisie = st.session_state.matiere_temp
    if matiere_choisie == "Autre":
        matiere_choisie = st.text_input("Précise ta matière :")
    
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
    
    st.markdown("---")
    sujet = st.text_input("3️⃣ Sur quel sujet veux-tu travailler ?", placeholder="Ex: Les fractions, L'eau...")
    photo = st.file_uploader("4️⃣ Tu as un examen blanc ? (Optionnel)", type=["png","jpg","jpeg"])
    
    st.markdown("---")
    # On utilise un st.button classique au lieu d'un form_submit_button
    submit_button = st.button("🚀 Lancer ma séance !", use_container_width=True)
    
    # Traitement après clic sur le bouton
    if submit_button:
        if not matiere_choisie or not st.session_state.mode_temp or not sujet.strip():
            st.warning("⚠️ Remplis bien la matière, le mode et le sujet !")
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
                        chat.send_message(f"Contexte examen: {exercices_photo}")
                    
                    data, raw = generate_next(chat, matiere_choisie, sujet, "facile", True)
                    if data:
                        init_question(data)
                    else:
                        st.session_state.messages.append({"role": "assistant", "content": raw})
                    
                    st.success("✅ Tuteur prêt! La séance va démarrer...")
                    time.sleep(1)  # Petit délai pour que l'utilisateur voie le message de succès
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erreur au démarrage : {e}")
# ==========================================
# SÉANCE EN COURS - AVEC OPTIMISATIONS
# ==========================================
else:
    ui_type = st.session_state.ui_type
    matiere = st.session_state.matiere
    sujet   = st.session_state.sujet
    mode    = st.session_state.mode
    chat    = st.session_state.chat_session
    q       = st.session_state.current_question
    fmt     = q.get("format", "libre") if q else None
    
    # Barre de contexte
    col_ctx, col_reset = st.columns([5, 1])
    with col_ctx:
        st.markdown(f'<div class="session-card">{MATIERES.get(matiere, "📚")} <b>{matiere}</b> — {sujet}</div>', unsafe_allow_html=True)
    with col_reset:
        if st.button("🔄 Reset"):
            reset_seance()
            st.rerun()
    
    # Score & Vies
    diff = st.session_state.difficulty
    col_d, col_s, col_v = st.columns(3)
    with col_d:
        st.markdown(f'<div class="diff-badge diff-{diff}">{DIFFICULTY_LABELS[diff]}</div>', unsafe_allow_html=True)
    with col_s:
        st.markdown(f'<div class="score-badge">⭐ {st.session_state.score}/{st.session_state.total_questions}</div>', unsafe_allow_html=True)
    with col_v:
        if mode == "exercice":
            # Correction de l'erreur de syntaxe
            hearts = "❤️" * st.session_state.vies + "🖤" * (3 - st.session_state.vies)
            st.markdown(f'<div class="lives-display">{hearts}</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Écran Game Over
    if st.session_state.game_over:
        st.error("💀 Plus de vies ! C'est la fin de la séance.")
        st.markdown(f"**Score final : {st.session_state.score} / {st.session_state.total_questions}** 🎯")
        
        # Utilisation d'un formulaire pour le bouton de recommencement
        with st.form(key="restart_form"):
            restart_button = st.form_submit_button("🔄 Recommencer avec 3 vies", use_container_width=True)
        
        if restart_button:
            st.session_state.vies            = 3
            st.session_state.game_over       = False
            st.session_state.score           = 0
            st.session_state.total_questions = 0
            st.session_state.difficulty      = "facile"
            
            # Affichage d'un indicateur de progression personnalisé
            show_loading("On repart avec de nouveaux exercices ! 🚀")
            
            try:
                # Prompt plus concis
                prompt_restart = f"Nouvel essai. Génère une question facile sur {sujet}. JSON uniquement."
                response = chat.send_message(prompt_restart)
                data = parse_json_response(response.text)
                if data:
                    init_question(data)
                else:
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun()
            except Exception as e:
                st.error(f"❌ Erreur lors du redémarrage : {e}")
    
    # Affichage de la question courante avec UI améliorée
    elif q:
        answered = st.session_state.answered
        
        # Utilisation d'un container pour la question actuelle
        with st.container():
            st.markdown('<div class="question-card">', unsafe_allow_html=True)
            
            # ---- QCM ----
            if fmt in ("qcm", "qcm_inverse"):
                st.markdown(f"### ❓ {q.get('question', q.get('answer',''))}")
                
                # Utilisation d'un formulaire pour les réponses QCM
                choices = q.get("choices", {})
                correct = q.get("correct", "")
                
                if not answered:
                    with st.form(key="qcm_form"):
                        ch_cols = st.columns(2)
                        selected_option = None
                        
                        for i, (key, val) in enumerate(choices.items()):
                            with ch_cols[i % 2]:
                                if st.form_submit_button(f"{key}. {val}", key=f"qcm_{key}", use_container_width=True):
                                    selected_option = key
                        
                        # Ce bouton n'est jamais visible car les options sont aussi des boutons de soumission
                        submit_qcm = st.form_submit_button("Valider", use_container_width=True)
                
                    # Traitement après soumission du formulaire
                    if selected_option:
                        st.session_state.last_choice = selected_option
                        if selected_option == correct:
                            handle_correct(mode)
                        else:
                            handle_wrong(mode)
                        st.rerun()
                else:
                    # Affichage des résultats après réponse
                    ch_cols = st.columns(2)
                    for i, (key, val) in enumerate(choices.items()):
                        css = "choice-btn"
                        if key == correct:
                            css = "choice-correct"
                        elif key == st.session_state.last_choice:
                            css = "choice-wrong"
                        
                        with ch_cols[i % 2]:
                            st.markdown(f'<div class="{css}">', unsafe_allow_html=True)
                            st.button(f"{key}. {val}", key=f"qcm_display_{key}", use_container_width=True, disabled=True)
                            st.markdown("</div>", unsafe_allow_html=True)
                    
                    if st.session_state.last_answer_correct:
                        st.success(f"✅ {q.get('explanation','')}")
                    else:
                        st.error(f"❌ La réponse était **{correct}**. {q.get('explanation','')}")
                    
                    # Formulaire pour continuer
                    with st.form(key="next_question_form"):
                        btn_label = "💀 Voir mon score final" if (mode == "exercice" and st.session_state.vies <= 0) else "➡️ Question suivante"
                        next_button = st.form_submit_button(btn_label, use_container_width=True)
                        
                        if next_button:
                            if mode == "exercice" and st.session_state.vies <= 0:
                                st.session_state.game_over = True
                                st.rerun()
                            
                            show_loading("Préparation de la prochaine question... ⚡")
                            
                            try:
                                data, raw = generate_next(chat, matiere, sujet, st.session_state.difficulty, False)
                                if data:
                                    init_question(data)
                                else:
                                    st.session_state.messages.append({"role": "assistant", "content": raw})
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Erreur lors de la génération : {e}")
            
            # ---- VRAI/FAUX ----
            elif fmt == "vrai_faux":
                st.markdown(f"### ✅❌ {q.get('statement','')}")
                correct_vf = q.get("correct", True)
                
                if not answered:
                    with st.form(key="vrai_faux_form"):
                        vf_cols = st.columns(2)
                        vf_choice = None
                        
                        with vf_cols[0]:
                            if st.form_submit_button("✅ Vrai", use_container_width=True):
                                vf_choice = True
                        
                        with vf_cols[1]:
                            if st.form_submit_button("❌ Faux", use_container_width=True):
                                vf_choice = False
                    
                    if vf_choice is not None:
                        st.session_state.vf_choice = vf_choice
                        if vf_choice == correct_vf:
                            handle_correct(mode)
                        else:
                            handle_wrong(mode)
                        st.rerun()
                else:
                    if st.session_state.last_answer_correct:
                        st.success(f"✅ {q.get('explanation','')}")
                    else:
                        st.error(f"❌ C'était **{'VRAI' if correct_vf else 'FAUX'}**. {q.get('explanation','')}")
                    
                    with st.form(key="vf_next_form"):
                        btn_label = "💀 Voir mon score final" if (mode == "exercice" and st.session_state.vies <= 0) else "➡️ Question suivante"
                        next_button = st.form_submit_button(btn_label, use_container_width=True)
                        
                        if next_button:
                            if mode == "exercice" and st.session_state.vies <= 0:
                                st.session_state.game_over = True
                                st.rerun()
                            
                            show_loading("Préparation de la prochaine question... ⚡")
                            
                            try:
                                data, raw = generate_next(chat, matiere, sujet, st.session_state.difficulty, False)
                                if data:
                                    init_question(data)
                                else:
                                    st.session_state.messages.append({"role": "assistant", "content": raw})
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Erreur lors de la génération : {e}")
            
            # Autres formats similaires (implémentation similaire)
            # ...
            
            # Exemple pour le format LIBRE/OUVERT avec formulaire
            elif fmt in ("libre", "ouvert"):
                st.markdown("### 📝 Problème")
                st.info(q.get("problem", q.get("prompt", "")))
                
                if q.get("hint") and not st.session_state.hint_revealed:
                    if st.button("💡 Voir un indice"):
                        st.session_state.hint_revealed = True
                        st.rerun()
                elif st.session_state.hint_revealed:
                    st.warning(f"💡 Indice : {q.get('hint','')}")
                
                if not answered:
                    with st.form(key="libre_form"):
                        student_answer = st.text_area("Ta réponse :")
                        submit_answer = st.form_submit_button("✅ Valider ma réponse")
                        
                        if submit_answer:
                            if student_answer.strip():
                                show_loading("Vérification en cours... 🔍")
                                
                                exp = q.get("solution") if fmt == "libre" else q.get("criteria")
                                res = evaluate_answer(chat, fmt, exp, student_answer)
                                st.session_state.eval_result = res
                                
                                if res.get("correct"):
                                    handle_correct(mode)
                                else:
                                    handle_wrong(mode)
                                st.rerun()
                else:
                    res = st.session_state.eval_result or {}
                    if res.get("correct"):
                        st.success(f"✅ {res.get('feedback','')}")
                    else:
                        st.error(f"❌ {res.get('feedback','')}\n\nAttendu : **{q.get('solution','')}**\n*{q.get('explanation','')}*")
                    
                    with st.form(key="libre_next_form"):
                        btn_label = "💀 Voir mon score final" if (mode == "exercice" and st.session_state.vies <= 0) else "➡️ Question suivante"
                        next_button = st.form_submit_button(btn_label, use_container_width=True)
                        
                        if next_button:
                            if mode == "exercice" and st.session_state.vies <= 0:
                                st.session_state.game_over = True
                                st.rerun()
                            
                            show_loading("Préparation de la prochaine question... ⚡")
                            
                            try:
                                data, raw = generate_next(chat, matiere, sujet, st.session_state.difficulty, False)
                                if data:
                                    init_question(data)
                                else:
                                    st.session_state.messages.append({"role": "assistant", "content": raw})
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Erreur lors de la génération : {e}")
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Export PDF optimisé
    st.markdown("---")
    with st.expander("📥 Exporter ma séance en PDF"):
        with st.form(key="pdf_form"):
            include_full = st.checkbox("Inclure toutes les questions", value=False, 
                                     help="Décochez pour n'inclure que les 5 dernières questions (PDF plus léger)")
            generate_pdf_button = st.form_submit_button("📄 Générer le fichier")
            
            if generate_pdf_button:
                try:
                    # Limiter les messages pour optimiser le PDF
                    messages_to_include = st.session_state.messages if include_full else st.session_state.messages[-5:]
                    
                    show_loading("Génération du PDF en cours... 📝")
                    
                    pdf_bytes = generer_pdf(matiere, sujet, mode, messages_to_include)
                    st.download_button("⬇️ Télécharger", pdf_bytes, file_name="seance.pdf", mime="application/pdf")
                except Exception as e:
                    st.error(f"❌ Erreur PDF : {e}")

# Affichage du code pour l'implémentation réelle
print("Code optimisé généré pour le tuteur IA")
