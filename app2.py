import streamlit as st
import google.generativeai as genai
from PIL import Image
from fpdf import FPDF
import json
import re

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
    "Mathématiques": "🔢",
    "Français":       "📖",
    "Histoire-Géo":   "🌍",
    "SVT":            "🌱",
    "Physique-Chimie":"⚗️",
    "Anglais":        "🇬🇧",
    "Espagnol":       "🇪🇸",
    "Autre":          "📝",
}

# Matières avec système de vies (mode exercice)
MATIERES_VIES = {"Mathématiques", "Physique-Chimie", "Histoire-Géo", "SVT"}
# Matières avec flashcards (mode exercice)
MATIERES_FLASHCARD = {"Français", "Anglais", "Espagnol", "Autre"}

MODEL_NAME = "gemini-2.5-flash-lite"
GENERATION_CONFIG = genai.GenerationConfig(
    temperature=0.7,
)

# ── System prompts ──

SYSTEM_BASE = """Tu es un tuteur super sympa, bienveillant et patient pour des élèves de 5ème (collège, 12-13 ans).
Utilise TOUJOURS le tutoiement, des emojis et un ton jeune et motivant.
Tes réponses JSON doivent être UNIQUEMENT du JSON valide, sans balises markdown, sans texte avant ou après.
"""

SYSTEM_QCM = SYSTEM_BASE + """
Tu génères des QCM pour aider l'élève à comprendre et assimiler son cours.

Pour CHAQUE question, réponds UNIQUEMENT avec ce JSON (pas de markdown, pas de texte autour) :
{
  "question": "La question claire et précise",
  "choices": {
    "A": "Première proposition",
    "B": "Deuxième proposition",
    "C": "Troisième proposition",
    "D": "Quatrième proposition"
  },
  "correct": "A",
  "explanation": "Explication courte et encourageante de la bonne réponse (2-3 phrases max, avec emoji)"
}

RÈGLES :
- Questions adaptées au niveau 5ème, sur le cours (pas des calculs complexes)
- Une seule bonne réponse parmi les 4
- Les mauvaises réponses doivent être plausibles (pas trop faciles à éliminer)
- Varier les types : définitions, exemples, "lequel est faux", etc.
- Enchaîne 5 à 8 questions par séance pour couvrir le sujet
"""

SYSTEM_VIES = SYSTEM_BASE + """
Tu génères des problèmes et exercices d'application à réponse libre pour que l'élève s'entraîne.

Pour CHAQUE exercice, réponds UNIQUEMENT avec ce JSON :
{
  "problem": "L'énoncé complet du problème ou exercice, clair et adapté au niveau 5ème",
  "solution": "La réponse exacte attendue (courte : un nombre, une date, un mot, une formule...)",
  "explanation": "Explication détaillée de la solution avec les étapes de raisonnement (3-4 phrases, avec emoji)",
  "hint": "Un indice utile qui guide sans donner la réponse (ex: 'Pense à la formule P = ...')"
}

RÈGLES :
- Exercices progressifs : commence simple, augmente la difficulté
- L'énoncé doit être précis et sans ambiguïté
- La solution doit être courte et vérifiable (un résultat, pas une phrase entière)
- L'indice doit vraiment aider sans spoiler la réponse
- L'explication montre le raisonnement complet étape par étape

Pour évaluer une réponse de l'élève, tu recevras un message au format :
EVAL|<solution_attendue>|<réponse_élève>
Réponds UNIQUEMENT avec ce JSON :
{
  "correct": true ou false,
  "feedback": "Message encourageant avec explication (2-3 phrases, avec emoji)"
}
"""

SYSTEM_FLASHCARD = SYSTEM_BASE + """
Tu génères des flashcards pour mémoriser du vocabulaire, des règles ou des conjugaisons.

Pour CHAQUE flashcard, réponds UNIQUEMENT avec ce JSON :
{
  "front": "Ce qui est affiché sur le recto (mot, expression, question)",
  "back": "La réponse complète au verso",
  "hint": "Un petit indice optionnel pour aider (peut être vide: '')",
  "example": "Un exemple d'usage en contexte (phrase courte)"
}

RÈGLES :
- Recto : mot, expression, verbe à conjuguer, règle à compléter
- Verso : traduction, définition, conjugaison complète, règle entière
- Exemple toujours en contexte réel
- Génère les flashcards une par une — attends la validation de l'élève avant la suivante
"""

QUICK_REPLIES_CHAT = [
    ("💡 Un indice",        "Je bloque, peux-tu me donner un indice ?"),
    ("🤔 J'ai pas compris", "Je n'ai pas compris, peux-tu réexpliquer autrement ?"),
    ("✅ J'ai compris !",   "J'ai compris, on peut passer à la suite !"),
    ("🔄 Autre exercice",   "Peux-tu me proposer un exercice similaire différent ?"),
]

# ==========================================
# CSS
# ==========================================
st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

/* ── Hero ── */
.hero-header {
    background: linear-gradient(135deg, #FF6B6B 0%, #FFE66D 55%, #4ECDC4 100%);
    border-radius: 20px;
    padding: 1.6rem 2rem;
    margin-bottom: 1.8rem;
    text-align: center;
    box-shadow: 0 4px 18px rgba(0,0,0,0.12);
}
.hero-header h1 { color: white; font-size: 2rem; margin: 0; text-shadow: 1px 2px 4px rgba(0,0,0,0.2); }
.hero-header p  { color: rgba(255,255,255,0.92); margin: 0.4rem 0 0; font-size: 1rem; }

/* ── Tuiles matières ── */
div[data-testid="stButton"].mat-btn > button {
    height: 72px !important; border-radius: 16px !important; font-size: 0.88rem !important;
    font-weight: bold !important; background-color: #f8f9ff !important;
    border: 3px solid #e0e4ff !important; color: #333 !important;
    white-space: pre-line !important; line-height: 1.4 !important; transition: all 0.18s ease !important;
}
div[data-testid="stButton"].mat-btn > button:hover {
    background-color: #4ECDC4 !important; color: white !important;
    border-color: #4ECDC4 !important; transform: translateY(-3px) !important;
}
div[data-testid="stButton"].mat-btn-selected > button {
    background-color: #FF6B6B !important; color: white !important;
    border-color: #FF6B6B !important; box-shadow: 0 4px 14px rgba(255,107,107,0.4) !important;
    height: 72px !important; border-radius: 16px !important; font-size: 0.88rem !important;
    font-weight: bold !important; white-space: pre-line !important; line-height: 1.4 !important;
}

/* ── Modes (cours / exercice) ── */
div[data-testid="stButton"].mode-btn > button {
    height: 90px !important; border-radius: 18px !important; font-size: 1rem !important;
    font-weight: bold !important; background-color: #fff8f0 !important;
    border: 3px solid #ffe0b2 !important; color: #555 !important;
    white-space: pre-line !important; line-height: 1.5 !important; transition: all 0.18s !important;
}
div[data-testid="stButton"].mode-btn > button:hover {
    background-color: #FF8E53 !important; color: white !important; border-color: #FF8E53 !important;
}
div[data-testid="stButton"].mode-btn-selected > button {
    background-color: #FF6B6B !important; color: white !important;
    border-color: #FF6B6B !important; height: 90px !important; border-radius: 18px !important;
    font-size: 1rem !important; font-weight: bold !important;
    white-space: pre-line !important; line-height: 1.5 !important;
}

/* ── Bouton lancement ── */
div[data-testid="stButton"].launch-btn > button {
    background: linear-gradient(135deg, #FF6B6B, #FF8E53) !important;
    color: white !important; border-radius: 50px !important; border: none !important;
    font-size: 1.1rem !important; font-weight: bold !important;
    padding: 0.85rem 2rem !important; width: 100% !important;
    box-shadow: 0 5px 18px rgba(255,107,107,0.45) !important;
}

/* ── Boutons QCM / Vies ── */
div[data-testid="stButton"].choice-btn > button {
    background-color: #f0f4ff !important; color: #333 !important;
    border-radius: 14px !important; border: 2px solid #d0d8ff !important;
    font-size: 0.95rem !important; font-weight: 600 !important;
    padding: 0.7rem 1rem !important; text-align: left !important;
    transition: all 0.15s !important; width: 100% !important;
}
div[data-testid="stButton"].choice-btn > button:hover {
    background-color: #4ECDC4 !important; color: white !important;
    border-color: #4ECDC4 !important; transform: translateY(-2px) !important;
}
div[data-testid="stButton"].choice-correct > button {
    background-color: #d4edda !important; color: #155724 !important;
    border-color: #28a745 !important; font-weight: bold !important;
    height: auto !important; border-radius: 14px !important; font-size: 0.95rem !important;
}
div[data-testid="stButton"].choice-wrong > button {
    background-color: #f8d7da !important; color: #721c24 !important;
    border-color: #dc3545 !important; font-weight: bold !important;
    height: auto !important; border-radius: 14px !important; font-size: 0.95rem !important;
}

/* ── Flashcard ── */
.flashcard-front {
    background: linear-gradient(135deg, #667eea, #764ba2);
    border-radius: 20px; padding: 2.5rem; text-align: center;
    color: white; font-size: 1.4rem; font-weight: bold;
    min-height: 140px; display: flex; align-items: center; justify-content: center;
    box-shadow: 0 8px 24px rgba(102,126,234,0.4); margin: 1rem 0;
}
.flashcard-back {
    background: linear-gradient(135deg, #f093fb, #f5576c);
    border-radius: 20px; padding: 2rem; text-align: center;
    color: white; font-size: 1.1rem;
    min-height: 140px; display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    box-shadow: 0 8px 24px rgba(245,87,108,0.4); margin: 1rem 0;
}
.flashcard-example {
    margin-top: 0.8rem; font-style: italic; font-size: 0.9rem;
    opacity: 0.9; border-top: 1px solid rgba(255,255,255,0.3);
    padding-top: 0.6rem; width: 100%;
}

/* ── Vies ── */
.lives-display {
    font-size: 1.6rem; text-align: center; padding: 0.5rem;
    letter-spacing: 0.3rem;
}
.score-badge {
    background: linear-gradient(135deg, #FFE66D, #FF6B6B);
    border-radius: 50px; padding: 0.3rem 1rem;
    font-weight: bold; color: white; font-size: 0.9rem;
    display: inline-block;
}

/* ── Session card ── */
.session-card {
    background: linear-gradient(90deg, #f0fff4, #f0f4ff);
    border-left: 5px solid #4ECDC4; border-radius: 12px;
    padding: 0.75rem 1.2rem; font-size: 0.95rem; color: #333;
}

/* ── Reset btn ── */
div[data-testid="stButton"].reset-btn > button {
    background: transparent !important; border: 2px solid #ddd !important;
    color: #888 !important; border-radius: 50px !important; font-size: 0.82rem !important;
}
div[data-testid="stButton"].reset-btn > button:hover {
    border-color: #FF6B6B !important; color: #FF6B6B !important;
}

/* ── Quick replies ── */
div[data-testid="stButton"].qr-btn > button {
    background-color: #f0f4ff !important; color: #444 !important;
    border-radius: 50px !important; border: 2px solid #d0d8ff !important;
    font-size: 0.82rem !important; font-weight: 600 !important; transition: all 0.15s !important;
}
div[data-testid="stButton"].qr-btn > button:hover {
    background-color: #4ECDC4 !important; color: white !important; border-color: #4ECDC4 !important;
}
</style>
""", unsafe_allow_html=True)


# ==========================================
# SESSION STATE
# ==========================================
_DEFAULTS = {
    "seance_lancee":          False,
    "matiere_temp":           "",
    "mode_temp":              "",       # "cours" ou "exercice"
    "matiere":                "",
    "sujet":                  "",
    "mode":                   "",
    "ui_type":                "",       # "qcm" | "vies" | "flashcard"

    # Chat (fallback + mode cours QCM)
    "chat_session":           None,
    "messages":               [],
    "quick_replies_on":       True,
    "quick_reply_triggered":  None,

    # QCM / Vies partagé
    "current_question":       None,     # dict JSON parsé
    "answered":               False,    # a-t-on répondu à la question en cours ?
    "last_answer_correct":    None,
    "score":                  0,
    "total_questions":        0,

    # Vies uniquement
    "vies":                   3,
    "game_over":              False,
    "hint_revealed":          False,
    "eval_result":            None,   # dict {correct, feedback} après validation

    # Flashcard uniquement
    "card_revealed":          False,    # recto affiché ou recto+verso
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
    elif matiere in MATIERES_VIES:
        return "vies"
    else:
        return "flashcard"


# ==========================================
# GEMINI HELPERS
# ==========================================
def make_model(system_prompt: str):
    return genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=system_prompt,
        generation_config=GENERATION_CONFIG,
    )


def creer_chat(matiere: str, sujet: str):
    system = SYSTEM_QCM + f"\n\nMatière : {matiere}\nSujet : {sujet}"
    model = make_model(system)
    return model.start_chat(history=[])


def parse_json_response(text: str) -> dict | None:
    """Extrait et parse le JSON d'une réponse Gemini de manière robuste."""
    try:
        # Nettoie les balises markdown éventuelles
        clean = re.sub(r"```json|```", "", text).strip()
        return json.loads(clean)
    except Exception:
        try:
            # Tente d'extraire le premier objet JSON trouvé
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass
    return None


def generate_qcm(chat_session, matiere: str, sujet: str, mode: str) -> dict | None:
    """Demande une nouvelle question QCM ou exercice à l'IA."""
    if st.session_state.total_questions == 0:
        prompt = (
            f"Génère la première question pour aider l'élève à {'comprendre son cours de' if mode == 'cours' else 's\'entraîner sur'} "
            f"{matiere} — sujet : {sujet}. "
            "Commence par une courte blague rigolote (1 ligne), puis génère le JSON de la question."
        )
    else:
        prompt = (
            f"Question suivante sur {sujet}. "
            f"{'Augmente légèrement la difficulté.' if mode != 'cours' else 'Aborde un autre aspect du cours.'} "
            "Réponds uniquement avec le JSON."
        )

    response = chat_session.send_message(prompt)
    return parse_json_response(response.text), response.text


def generate_flashcard(chat_session, matiere: str, sujet: str) -> dict | None:
    """Demande une nouvelle flashcard à l'IA."""
    if st.session_state.total_questions == 0:
        prompt = (
            f"On va travailler sur {matiere} — sujet : {sujet}. "
            "Commence par une courte blague rigolote (1 ligne), "
            "puis génère la première flashcard en JSON."
        )
    else:
        prompt = "Flashcard suivante sur le même sujet. JSON uniquement."

    response = chat_session.send_message(prompt)
    return parse_json_response(response.text), response.text


def evaluate_answer(chat_session, solution: str, student_answer: str) -> dict:
    """Demande à l'IA d'évaluer la réponse libre de l'élève."""
    prompt = f"EVAL|{solution}|{student_answer}"
    response = chat_session.send_message(prompt)
    data = parse_json_response(response.text)
    if data:
        return data
    # Fallback si le parsing échoue
    return {"correct": False, "feedback": "Je n'ai pas pu évaluer ta réponse, réessaie ! 🤔"}


def analyser_photo(image: Image.Image, matiere: str) -> str:
    model = make_model(
        SYSTEM_VIES if matiere in MATIERES_VIES else SYSTEM_QCM
    )
    prompt = (
        f"Voici une photo d'examen blanc de {matiere} (niveau 5ème). "
        "Analyse les types et le niveau des exercices. "
        "Génère 2 ou 3 exercices similaires avec des données différentes, "
        "numérotés, sans les corrections."
    )
    response = model.generate_content([image, prompt])
    return response.text


def generer_pdf(matiere: str, sujet: str, mode: str, messages: list) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(15, 15, 15)
    pdf.set_fill_color(255, 107, 107)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 14, "Fiche d'exercice  -  Classe de 5eme", ln=True, align="C", fill=True)
    pdf.set_text_color(80, 80, 80)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"Matiere : {matiere}   |   Sujet : {sujet}   |   Mode : {mode}", ln=True, align="C")
    pdf.ln(8)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Contenu de la seance :", ln=True)
    pdf.ln(3)
    pdf.set_font("Arial", "", 11)
    for msg in messages:
        if msg["role"] == "assistant":
            content = msg["content"].replace("[SYNTHESE]", "").strip()
            safe = content.encode("latin-1", errors="replace").decode("latin-1")
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

    # ── 1. Matière ──
    st.markdown("### 1️⃣ Choisis ta matière")
    cols = st.columns(4)
    for i, (mat, emoji) in enumerate(MATIERES.items()):
        is_sel = st.session_state.matiere_temp == mat
        css = "mat-btn-selected" if is_sel else "mat-btn"
        label = f"{'✅ ' if is_sel else ''}{emoji}\n{mat}"
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

    # ── 2. Mode ──
    st.markdown("### 2️⃣ Qu'est-ce que tu veux faire ?")
    mode_cols = st.columns(2)

    modes = {
        "cours":    ("📚", "Comprendre le cours", "QCM pour tester tes connaissances"),
        "exercice": ("✏️", "Faire des exercices",  "Entraîne-toi avec des exercices"),
    }
    for i, (mode_key, (emoji, titre, desc)) in enumerate(modes.items()):
        is_sel = st.session_state.mode_temp == mode_key
        css = "mode-btn-selected" if is_sel else "mode-btn"
        label = f"{'✅ ' if is_sel else ''}{emoji} {titre}\n{desc}"
        with mode_cols[i]:
            st.markdown(f'<div class="{css}">', unsafe_allow_html=True)
            if st.button(label, key=f"mode_{mode_key}", use_container_width=True):
                st.session_state.mode_temp = mode_key
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # Info dynamique selon le combo matière + mode
    if st.session_state.matiere_temp and st.session_state.mode_temp:
        ui = get_ui_type(st.session_state.matiere_temp, st.session_state.mode_temp)
        infos = {
            "qcm":       "🧠 Mode QCM — 4 propositions, clique sur la bonne réponse !",
            "vies":      "❤️ Mode Exercices — 3 vies, ne te trompe pas trop ! 😅",
            "flashcard": "🃏 Mode Flashcards — recto / verso, teste ta mémoire !",
        }
        st.info(infos[ui])

    st.markdown("---")

    # ── 3. Sujet ──
    st.markdown("### 3️⃣ Sur quel sujet veux-tu travailler ?")
    sujet = st.text_input("", placeholder="Ex: Les fractions, La Révolution française, Les volcans...",
                          label_visibility="collapsed")

    # ── 4. Photo optionnelle ──
    st.markdown("### 4️⃣ Tu as un examen blanc ? *(optionnel)*")
    st.caption("📷 L'IA analyse ta copie et génère des exercices du même type.")
    photo = st.file_uploader("Dépose une photo ici", type=["png", "jpg", "jpeg"],
                             label_visibility="collapsed")
    if photo:
        st.image(photo, caption="Photo reçue ✅", width=260)

    st.markdown("---")

    # ── Lancement ──
    st.markdown('<div class="launch-btn">', unsafe_allow_html=True)
    lancer = st.button("🚀 Lancer ma séance !", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if lancer:
        if not matiere_choisie or matiere_choisie == "Autre":
            st.warning("⚠️ Choisis une matière !")
        elif not st.session_state.mode_temp:
            st.warning("⚠️ Choisis un mode (cours ou exercices) !")
        elif not sujet.strip():
            st.warning("⚠️ Dis-moi sur quel sujet tu veux travailler !")
        else:
            with st.spinner("Ton tuteur se prépare... 🎯"):
                try:
                    ui_type = get_ui_type(matiere_choisie, st.session_state.mode_temp)
                    chat = creer_chat(matiere_choisie, sujet)

                    st.session_state.chat_session  = chat
                    st.session_state.matiere       = matiere_choisie
                    st.session_state.sujet         = sujet
                    st.session_state.mode          = st.session_state.mode_temp
                    st.session_state.ui_type       = ui_type
                    st.session_state.seance_lancee = True

                    # Si photo : analyse et injecte en contexte
                    if photo:
                        img = Image.open(photo)
                        exercices_photo = analyser_photo(img, matiere_choisie)
                        # On stocke ça en premier message système
                        chat.send_message(
                            f"Contexte examen blanc fourni par l'élève :\n{exercices_photo}\n"
                            "Utilise ces exercices comme base pour les questions."
                        )

                    # Génère la première question
                    if ui_type in ("qcm", "vies"):
                        data, raw = generate_qcm(chat, matiere_choisie, sujet, st.session_state.mode_temp)
                        if data:
                            st.session_state.current_question = data
                        else:
                            st.session_state.messages.append({"role": "assistant", "content": raw})
                    else:  # flashcard
                        data, raw = generate_flashcard(chat, matiere_choisie, sujet)
                        if data:
                            st.session_state.current_question = data
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

    # ── Barre de contexte ──
    col_ctx, col_reset = st.columns([5, 1])
    with col_ctx:
        emoji_mat = MATIERES.get(matiere, "📚")
        mode_label = "📚 Cours" if mode == "cours" else "✏️ Exercices"
        st.markdown(
            f'<div class="session-card">'
            f'{emoji_mat} <b>{matiere}</b> — {sujet} &nbsp;|&nbsp; {mode_label}'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col_reset:
        st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
        if st.button("🔄 Reset", use_container_width=True):
            reset_seance()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    # ══════════════════════════════════════
    # MODE QCM (cours)
    # ══════════════════════════════════════
    if ui_type == "qcm":
        # Score
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.markdown(
                f'<div class="score-badge">⭐ Score : {st.session_state.score} / {st.session_state.total_questions}</div>',
                unsafe_allow_html=True,
            )

        q = st.session_state.current_question
        if q:
            st.markdown(f"### ❓ {q.get('question', '')}")
            st.markdown("")

            choices = q.get("choices", {})
            answered = st.session_state.answered
            correct  = q.get("correct", "")

            choice_cols = st.columns(2)
            for i, (key, val) in enumerate(choices.items()):
                # Détermine la couleur post-réponse
                if answered:
                    if key == correct:
                        css = "choice-correct"
                    elif key == st.session_state.get("last_choice") and key != correct:
                        css = "choice-wrong"
                    else:
                        css = "choice-btn"
                else:
                    css = "choice-btn"

                with choice_cols[i % 2]:
                    st.markdown(f'<div class="{css}">', unsafe_allow_html=True)
                    if st.button(f"{key}. {val}", key=f"qcm_{key}", use_container_width=True, disabled=answered):
                        st.session_state.answered    = True
                        st.session_state.last_choice = key
                        st.session_state.total_questions += 1
                        if key == correct:
                            st.session_state.score += 1
                            st.session_state.last_answer_correct = True
                        else:
                            st.session_state.last_answer_correct = False
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

            # Feedback post-réponse
            if answered:
                if st.session_state.last_answer_correct:
                    st.success(f"✅ Bravo ! {q.get('explanation', '')}")
                else:
                    st.error(f"❌ Pas tout à fait... La bonne réponse était **{correct}**. {q.get('explanation', '')}")

                st.markdown("")
                st.markdown('<div class="launch-btn">', unsafe_allow_html=True)
                if st.button("➡️ Question suivante", use_container_width=True):
                    with st.spinner("Chargement..."):
                        try:
                            data, raw = generate_qcm(
                                st.session_state.chat_session, matiere, sujet, mode
                            )
                            st.session_state.current_question = data if data else None
                            st.session_state.answered         = False
                            st.session_state.last_answer_correct = None
                            if not data:
                                st.session_state.messages.append({"role": "assistant", "content": raw})
                        except Exception as e:
                            st.error(f"❌ {e}")
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

    # ══════════════════════════════════════
    # MODE VIES (exercices Maths/Sciences/Histoire)
    # ══════════════════════════════════════
    elif ui_type == "vies":
        vies   = st.session_state.vies
        hearts = "❤️" * vies + "🖤" * (3 - vies)
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            st.markdown(f'<div class="lives-display">{hearts}</div>', unsafe_allow_html=True)
        with col_v2:
            st.markdown(
                f'<div class="score-badge" style="margin-top:0.6rem">⭐ {st.session_state.score} / {st.session_state.total_questions}</div>',
                unsafe_allow_html=True,
            )

        if st.session_state.game_over:
            st.error("💀 Plus de vies ! C'est la fin de la séance.")
            st.markdown(f"**Ton score final : {st.session_state.score} / {st.session_state.total_questions}** 🎯")
            st.markdown('<div class="launch-btn">', unsafe_allow_html=True)
            if st.button("🔄 Recommencer avec 3 vies", use_container_width=True):
                st.session_state.vies             = 3
                st.session_state.game_over        = False
                st.session_state.score            = 0
                st.session_state.total_questions  = 0
                st.session_state.answered         = False
                st.session_state.hint_revealed    = False
                st.session_state.eval_result      = None
                with st.spinner("On repart ! 🚀"):
                    try:
                        data, raw = generate_qcm(
                            st.session_state.chat_session, matiere, sujet, mode
                        )
                        st.session_state.current_question = data if data else None
                    except Exception as e:
                        st.error(f"❌ {e}")
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        else:
            q = st.session_state.current_question
            if q:
                # Énoncé du problème
                st.markdown("### 📝 Problème")
                st.info(q.get("problem", ""))

                # Indice (masqué par défaut)
                if not st.session_state.hint_revealed:
                    if st.button("💡 Voir un indice", key="hint_btn"):
                        st.session_state.hint_revealed = True
                        st.rerun()
                else:
                    st.warning(f"💡 **Indice :** {q.get('hint', '')}")

                st.markdown("")

                answered = st.session_state.answered

                if not answered:
                    # Champ de réponse libre
                    student_answer = st.text_input(
                        "✏️ Ta réponse :",
                        placeholder="Écris ta réponse ici...",
                        key="student_answer_input",
                    )
                    st.markdown('<div class="launch-btn">', unsafe_allow_html=True)
                    valider = st.button("✅ Valider ma réponse", use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)

                    if valider:
                        if not student_answer.strip():
                            st.warning("⚠️ Écris ta réponse avant de valider !")
                        else:
                            with st.spinner("Ton tuteur vérifie... 🔍"):
                                try:
                                    result = evaluate_answer(
                                        st.session_state.chat_session,
                                        q.get("solution", ""),
                                        student_answer.strip(),
                                    )
                                    st.session_state.eval_result      = result
                                    st.session_state.answered         = True
                                    st.session_state.total_questions += 1
                                    if result.get("correct"):
                                        st.session_state.score += 1
                                        st.session_state.last_answer_correct = True
                                    else:
                                        st.session_state.vies -= 1
                                        st.session_state.last_answer_correct = False
                                        if st.session_state.vies <= 0:
                                            st.session_state.game_over = True
                                except Exception as e:
                                    st.error(f"❌ {e}")
                            st.rerun()

                else:
                    # Feedback après validation
                    result = st.session_state.eval_result or {}
                    if result.get("correct"):
                        st.success(f"✅ {result.get('feedback', '')}")
                    else:
                        st.error(
                            f"❌ {result.get('feedback', '')} "
                            f"La bonne réponse était : **{q.get('solution', '')}**\n\n"
                            f"*{q.get('explanation', '')}*"
                        )
                        if st.session_state.game_over:
                            st.rerun()

                    if not st.session_state.game_over:
                        st.markdown('<div class="launch-btn">', unsafe_allow_html=True)
                        if st.button("➡️ Exercice suivant", use_container_width=True):
                            with st.spinner("Chargement..."):
                                try:
                                    data, raw = generate_qcm(
                                        st.session_state.chat_session, matiere, sujet, mode
                                    )
                                    st.session_state.current_question    = data if data else None
                                    st.session_state.answered            = False
                                    st.session_state.last_answer_correct = None
                                    st.session_state.hint_revealed       = False
                                    st.session_state.eval_result         = None
                                except Exception as e:
                                    st.error(f"❌ {e}")
                            st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)

    # ══════════════════════════════════════
    # MODE FLASHCARD (langues / Français)
    # ══════════════════════════════════════
    elif ui_type == "flashcard":
        card = st.session_state.current_question
        score = st.session_state.score
        total = st.session_state.total_questions

        col_sc = st.columns(3)
        with col_sc[0]:
            st.markdown(f"✅ **{score}** sus", unsafe_allow_html=False)
        with col_sc[1]:
            st.markdown(f"📚 **{total}** cartes", unsafe_allow_html=False)
        with col_sc[2]:
            ratio = int((score / total * 100)) if total > 0 else 0
            st.markdown(f"🎯 **{ratio}%**")

        st.markdown("")

        if card:
            # Recto toujours affiché
            st.markdown(
                f'<div class="flashcard-front">{card.get("front", "")}</div>',
                unsafe_allow_html=True,
            )

            # Indice optionnel
            if card.get("hint"):
                st.caption(f"💡 Indice : {card['hint']}")

            if not st.session_state.card_revealed:
                # Bouton retourner
                col_r = st.columns([1, 2, 1])
                with col_r[1]:
                    if st.button("🔄 Retourner la carte", use_container_width=True):
                        st.session_state.card_revealed = True
                        st.rerun()
            else:
                # Verso
                example_html = ""
                if card.get("example"):
                    example_html = f'<div class="flashcard-example">📝 {card["example"]}</div>'
                st.markdown(
                    f'<div class="flashcard-back">'
                    f'<div><strong>{card.get("back", "")}</strong></div>'
                    f'{example_html}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                st.markdown("#### Tu savais ?")
                eval_cols = st.columns(3)
                evals = [("✅ Je savais !", 1), ("🤔 Presque...", 0), ("❌ Je savais pas", 0)]
                for i, (label, pts) in enumerate(evals):
                    with eval_cols[i]:
                        if st.button(label, key=f"eval_{i}", use_container_width=True):
                            st.session_state.total_questions += 1
                            st.session_state.score           += pts
                            st.session_state.card_revealed   = False
                            st.session_state.answered        = True
                            with st.spinner("Prochaine carte..."):
                                try:
                                    data, raw = generate_flashcard(
                                        st.session_state.chat_session, matiere, sujet
                                    )
                                    st.session_state.current_question = data if data else None
                                    if not data:
                                        st.session_state.messages.append({"role": "assistant", "content": raw})
                                except Exception as e:
                                    st.error(f"❌ {e}")
                            st.rerun()

    # ══════════════════════════════════════
    # SECTION CHAT LIBRE (tous modes)
    # ══════════════════════════════════════
    st.markdown("---")
    with st.expander("💬 Poser une question au tuteur"):
        for msg in st.session_state.messages:
            avatar = "🎓" if msg["role"] == "assistant" else "🧑‍🎓"
            with st.chat_message(msg["role"], avatar=avatar):
                st.markdown(msg["content"])

        st.session_state.quick_replies_on = st.toggle(
            "Boutons rapides", value=st.session_state.quick_replies_on
        )
        if st.session_state.quick_replies_on:
            qr_cols = st.columns(len(QUICK_REPLIES_CHAT))
            for i, (label, text) in enumerate(QUICK_REPLIES_CHAT):
                with qr_cols[i]:
                    st.markdown('<div class="qr-btn">', unsafe_allow_html=True)
                    if st.button(label, key=f"qr_{i}", use_container_width=True):
                        st.session_state.quick_reply_triggered = text
                    st.markdown("</div>", unsafe_allow_html=True)

        if st.session_state.quick_reply_triggered:
            user_msg = st.session_state.quick_reply_triggered
            st.session_state.quick_reply_triggered = None
            st.session_state.messages.append({"role": "user", "content": user_msg})
            try:
                resp = st.session_state.chat_session.send_message(user_msg)
                raw = re.sub(r"```json.*?```", "", resp.text, flags=re.DOTALL).strip()
                st.session_state.messages.append({"role": "assistant", "content": raw})
            except Exception as e:
                st.error(f"❌ {e}")
            st.rerun()

        if user_input := st.chat_input("✏️ Pose ta question..."):
            st.session_state.messages.append({"role": "user", "content": user_input})
            try:
                resp = st.session_state.chat_session.send_message(user_input)
                raw = re.sub(r"```json.*?```", "", resp.text, flags=re.DOTALL).strip()
                st.session_state.messages.append({"role": "assistant", "content": raw})
            except Exception as e:
                st.error(f"❌ {e}")
            st.rerun()

    # ══════════════════════════════════════
    # EXPORT PDF
    # ══════════════════════════════════════
    st.markdown("---")
    with st.expander("📥 Exporter en PDF"):
        st.caption("Génère une fiche imprimable de ta séance.")
        if st.button("📄 Générer ma fiche PDF"):
            try:
                pdf_bytes = generer_pdf(matiere, sujet, mode, st.session_state.messages)
                st.download_button(
                    label="⬇️ Télécharger le PDF",
                    data=pdf_bytes,
                    file_name=f"seance_{matiere.lower().replace(' ', '_')}.pdf",
                    mime="application/pdf",
                )
            except Exception as e:
                st.error(f"❌ Erreur PDF : {e}")

    # Ballons si bonne séance
    if st.session_state.score >= 5 and st.session_state.total_questions >= 5:
        if st.session_state.score / st.session_state.total_questions >= 0.8:
            st.balloons()
