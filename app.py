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

# Optimisation : Température basse (0.3) et forçage du JSON natif
GENERATION_CONFIG = genai.GenerationConfig(
    temperature=0.3,
    response_mime_type="application/json"
)

# ==========================================
# SYSTEM PROMPTS (Bridés niveau 5ème + Style Officiel)
# ==========================================
SYSTEM_BASE = """Tu es un tuteur super sympa, bienveillant et patient pour des élèves de 5ème (12-13 ans).

RÈGLE ABSOLUE 1 - PÉRIMÈTRE : Tu dois STRICTEMENT te limiter au programme officiel de l'Éducation Nationale française pour la classe de 5ème (début du Cycle 4). 
Ne propose JAMAIS de notions, de formules ou de vocabulaire vus en 4ème, 3ème ou au lycée.

RÈGLE ABSOLUE 2 - SOURCES ET STYLE : Inspire-toi DIRECTEMENT des manuels scolaires français classiques (Nathan, Hatier, Bordas, Sésamath) et des plateformes de révision reconnues (Lumni, Kartable). Tes énoncés, QCM et problèmes doivent avoir la même rigueur, la même structure, le même vocabulaire et le même type de mise en situation que les exercices officiels donnés en classe.

Utilise le tutoiement, des emojis et un ton jeune et motivant.
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

NIVEAUX DE DIFFICULTÉ (Strictement limités au programme de 5ème) :
- facile : définition simple, notion de base du cours.
- moyen : relation entre deux notions, application directe d'une règle simple.
- difficile : synthèse ou réflexion nécessitant 2 étapes maximum. ATTENTION : Le niveau "difficile" ne signifie pas passer au programme du lycée. Cela doit rester faisable par un élève de 12 ans.

Le niveau sera précisé dans chaque prompt.
Ton format de sortie doit obligatoirement suivre l'un des schémas JSON suivants :

{"format":"qcm","difficulty":"facile","question":"...","choices":{"A":"...","B":"...","C":"...","D":"..."},"correct":"A","explanation":"... emoji"}
{"format":"qcm_inverse","difficulty":"moyen","answer":"La réponse donnée","choices":{"A":"Question A ?","B":"Question B ?","C":"Question C ?","D":"Question D ?"},"correct":"B","explanation":"... emoji"}
{"format":"vrai_faux","difficulty":"facile","statement":"Affirmation à évaluer (vraie ou fausse)","correct":true,"explanation":"Explication complète avec emoji"}
{"format":"trous","difficulty":"facile","instruction":"Complète la phrase","text":"[BLANK_0] est ... [BLANK_1] ...","blanks":["mot1","mot2"],"explanation":"... emoji"}
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

NIVEAUX DE DIFFICULTÉ (Strictement limités au programme de 5ème) :
- facile : une étape, données simples, application directe du cours.
- moyen : 2 étapes, données réalistes, raisonnement guidé.
- difficile : cas un peu plus complexe à 2 ou 3 étapes maximum. Ne sors JAMAIS du programme de 5ème.

Le niveau sera précisé dans chaque prompt.
Ton format de sortie doit obligatoirement suivre l'un des schémas JSON suivants :

{"format":"libre","difficulty":"moyen","problem":"Énoncé complet et clair","solution":"Réponse courte et précise","explanation":"Solution étape par étape emoji","hint":"Indice utile sans spoiler"}
{"format":"trous","difficulty":"facile","instruction":"Complète","text":"[BLANK_0] ... [BLANK_1] ...","blanks":["réponse1","réponse2"],"explanation":"... emoji"}
{"format":"ordre","difficulty":"moyen","instruction":"Remets ces étapes dans le bon ordre","items_shuffled":["Étape C","Étape A","Étape D","Étape B"],"correct_order":["Étape A","Étape B","Étape C","Étape D"],"explanation":"... emoji"}
{"format":"ouvert","difficulty":"difficile","prompt":"Texte de compréhension ou question ouverte à développer","criteria":["critère 1 attendu","critère 2 attendu","critère 3 attendu"],"explanation":"Ce que la réponse idéale devrait contenir"}

Pour évaluer une réponse libre, tu recevras : EVAL|libre|<solution_attendue>|<réponse_élève>
Pour évaluer un exercice ouvert : EVAL|ouvert|<criteria_json>|<réponse_élève>
Réponds UNIQUEMENT avec : {"correct":true,"feedback":"Message encourageant 2-3 phrases avec emoji"}
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
# GEMINI HELPERS
# ==========================================
def make_model(system_prompt: str):
    return genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=system_prompt,
        generation_config=GENERATION_CONFIG,
    )

def creer_chat(matiere: str, sujet: str, ui_type: str):
    base = SYSTEM_COURS if ui_type == "cours" else SYSTEM_EXERCICE
    system = base + f"\n\nMatière : {matiere}\nSujet : {sujet}"
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

def generate_next(chat_session, matiere: str, sujet: str, difficulty: str, is_first: bool) -> tuple:
    diff_label = DIFFICULTY_LABELS[difficulty]
    if is_first:
        prompt = f"Génère la première question de niveau {diff_label} pour {matiere} — sujet : {sujet}. Commence par une courte blague, puis format JSON."
    else:
        prompt = (
            f"Prochaine question de niveau {diff_label} sur {sujet}. "
            "CONTRAINTE MAJEURE : Change l'angle d'approche, le contexte de l'énoncé, ou les valeurs numériques. "
            "L'exercice doit être STRICTEMENT DIFFÉRENT de tous ceux que tu as déjà posés."
        )
    
    try:
        response = chat_session.send_message(prompt)
        return parse_json_response(response.text), response.text
    except Exception as e:
        return None, f"❌ Erreur de génération : {e}"

def evaluate_answer(chat_session, fmt: str, expected, student_answer: str) -> dict:
    if fmt == "ouvert":
        prompt = f"EVAL|ouvert|{json.dumps(expected, ensure_ascii=False)}|{student_answer}"
    else:
        prompt = f"EVAL|libre|{expected}|{student_answer}"
    
    try:
        response = chat_session.send_message(prompt)
        data = parse_json_response(response.text)
        return data if data else {"correct": False, "feedback": "Je n'ai pas pu évaluer ta réponse, réessaie ! 🤔"}
    except Exception as e:
        return {"correct": False, "feedback": f"Petit bug technique, réessaie ! ({e})"}

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

def next_question_button(chat_session, matiere: str, sujet: str, mode: str, default_label: str = "➡️ Question suivante"):
    st.markdown('<div class="launch-btn">', unsafe_allow_html=True)
    
    btn_label = "💀 Voir mon score final" if (mode == "exercice" and st.session_state.vies <= 0) else default_label
    
    if st.button(btn_label, use_container_width=True, key="next_q_btn"):
        if mode == "exercice" and st.session_state.vies <= 0:
            st.session_state.game_over = True
            st.rerun()
            
        with st.spinner("Chargement... ⚡"):
            try:
                data, raw = generate_next(chat_session, matiere, sujet, st.session_state.difficulty, False)
                if data:
                    init_question(data)
                else:
                    st.session_state.messages.append({"role": "assistant", "content": raw})
            except Exception as e:
                st.error(f"❌ Erreur lors de la génération : {e}")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def analyser_photo(image: Image.Image, matiere: str, ui_type: str) -> str:
    base = SYSTEM_EXERCICE if ui_type == "exercice" else SYSTEM_COURS
    model = make_model(base)
    prompt = "Voici une photo d'examen blanc. Analyse les types et le niveau des exercices. Génère 2 ou 3 exercices similaires."
    return model.generate_content([image, prompt]).text

def remove_emojis(text):
    return text.encode('ascii', 'ignore').decode('ascii')

def generer_pdf(matiere: str, sujet: str, mode: str, messages: list) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(15, 15, 15)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 14, remove_emojis("Fiche de révision - Classe de 5ème"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, remove_emojis(f"Matière : {matiere}  |  Sujet : {sujet}  |  Mode : {mode}"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, remove_emojis("Contenu de la séance :"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("Helvetica", "", 11)
    
    for msg in messages:
        if msg["role"] == "assistant":
            clean_text = remove_emojis(msg["content"])
            pdf.multi_cell(0, 7, clean_text)
            pdf.ln(3)
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
    st.markdown('<div class="launch-btn">', unsafe_allow_html=True)
    if st.button("🚀 Lancer ma séance !", use_container_width=True):
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
                        chat.send_message(f"Contexte examen blanc :\n{exercices_photo}\nUtilise-le comme base.")

                    data, raw = generate_next(chat, matiere_choisie, sujet, "facile", True)
                    if data:
                        init_question(data)
                    else:
                        st.session_state.messages.append({"role": "assistant", "content": raw})
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erreur au démarrage : {e}")
    st.markdown("</div>", unsafe_allow_html=True)

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
            hearts = "❤️" * st.session_state.vies + "🖤" * (3 - st.session_state.vies)
            st.markdown(f'<div class="lives-display">{hearts}</div>', unsafe_allow_html=True)

    st.markdown("---")

    # Écran Game Over
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
            with st.spinner("On repart avec de nouveaux exercices ! 🚀"):
                try:
                    prompt_restart = (
                        f"L'élève a perdu ses vies et recommence l'entraînement sur le sujet : {sujet}. "
                        f"Génère une nouvelle question de niveau {DIFFICULTY_LABELS['facile']}. "
                        "IMPORTANT : C'est un nouvel essai, invente un problème TOTALEMENT INÉDIT "
                        "(nouveau contexte, nouveaux chiffres, nouvel angle) que tu n'as pas encore "
                        "utilisé dans cette séance. Ne fais aucune phrase d'intro, format JSON uniquement."
                    )
                    response = chat.send_message(prompt_restart)
                    data = parse_json_response(response.text)
                    if data: 
                        init_question(data)
                    else:
                        st.session_state.messages.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error(f"❌ Erreur lors du redémarrage : {e}")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # Affichage de la question courante
    elif q:
        answered = st.session_state.answered

        # ---- QCM ----
        if fmt in ("qcm", "qcm_inverse"):
            st.markdown(f"### ❓ {q.get('question', q.get('answer',''))}")
            choices = q.get("choices", {})
            correct = q.get("correct", "")
            ch_cols = st.columns(2)
            for i, (key, val) in enumerate(choices.items()):
                css = "choice-btn"
                if answered:
                    if key == correct: css = "choice-correct"
                    elif key == st.session_state.last_choice: css = "choice-wrong"

                with ch_cols[i % 2]:
                    st.markdown(f'<div class="{css}">', unsafe_allow_html=True)
                    if st.button(f"{key}. {val}", key=f"qcm_{key}", use_container_width=True, disabled=answered):
                        st.session_state.last_choice = key
                        if key == correct: handle_correct(mode)
                        else: handle_wrong(mode)
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

            if answered:
                if st.session_state.last_answer_correct: st.success(f"✅ {q.get('explanation','')}")
                else: st.error(f"❌ La réponse était **{correct}**. {q.get('explanation','')}")
                next_question_button(chat, matiere, sujet, mode)

        # ---- VRAI/FAUX ----
        elif fmt == "vrai_faux":
            st.markdown(f"### ✅❌ {q.get('statement','')}")
            correct_vf = q.get("correct", True)
            vf_cols = st.columns(2)
            
            with vf_cols[0]:
                if st.button("✅ Vrai", disabled=answered, use_container_width=True):
                    st.session_state.vf_choice = True
                    if True == correct_vf: handle_correct(mode)
                    else: handle_wrong(mode)
                    st.rerun()
            with vf_cols[1]:
                if st.button("❌ Faux", disabled=answered, use_container_width=True):
                    st.session_state.vf_choice = False
                    if False == correct_vf: handle_correct(mode)
                    else: handle_wrong(mode)
                    st.rerun()
                    
            if answered:
                if st.session_state.last_answer_correct: st.success(f"✅ {q.get('explanation','')}")
                else: st.error(f"❌ C'était **{'VRAI' if correct_vf else 'FAUX'}**. {q.get('explanation','')}")
                next_question_button(chat, matiere, sujet, mode)

        # ---- TROUS ----
        elif fmt == "trous":
            st.markdown(f"### ✏️ {q.get('instruction','')}")
            display = re.sub(r"\[BLANK_\d+\]", '___', q.get("text", ""))
            st.info(display)
            
            blanks = q.get("blanks", [])
            student_answers = [st.text_input(f"Blanc {i+1} :", disabled=answered) for i in range(len(blanks))]
            
            if not answered:
                if st.button("✅ Valider"):
                    if all(a.strip() for a in student_answers):
                        if all(s.strip().lower() == c.strip().lower() for s, c in zip(student_answers, blanks)):
                            handle_correct(mode)
                        else:
                            handle_wrong(mode)
                        st.rerun()
            else:
                for i, c in enumerate(blanks):
                    st.write(f"Blanc {i+1} attendu : **{c}**")
                st.markdown(f"*{q.get('explanation','')}*")
                next_question_button(chat, matiere, sujet, mode)

        # ---- PAIRES ----
        elif fmt == "paires":
            st.markdown(f"### 🔗 {q.get('instruction','')}")
            pairs = q.get("pairs", [])
            shuffled = st.session_state.paires_shuffled
            
            for i, pair in enumerate(pairs):
                col_l, col_r = st.columns(2)
                col_l.write(f"→ {pair['left']}")
                if answered:
                    col_r.write(f"Ton choix : {st.session_state.get(f'pair_{i}')} | Correct : **{pair['right']}**")
                else:
                    with col_r:
                        st.selectbox("", shuffled, key=f"pair_{i}", label_visibility="collapsed")
                        
            if not answered:
                if st.button("✅ Valider les associations"):
                    if all(st.session_state.get(f"pair_{i}") == p["right"] for i, p in enumerate(pairs)):
                        handle_correct(mode)
                    else:
                        handle_wrong(mode)
                    st.rerun()
            else:
                st.markdown(f"*{q.get('explanation','')}*")
                next_question_button(chat, matiere, sujet, mode)

        # ---- ORDRE ----
        elif fmt == "ordre":
            st.markdown(f"### 🔀 {q.get('instruction','')}")
            items_shuffled = q.get("items_shuffled", [])
            correct_order  = q.get("correct_order", [])
            
            for pos in range(len(correct_order)):
                st.selectbox(f"Position {pos+1} :", items_shuffled, key=f"ordre_{pos}", disabled=answered)
                
            if not answered:
                if st.button("✅ Valider l'ordre"):
                    if [st.session_state.get(f"ordre_{p}") for p in range(len(correct_order))] == correct_order:
                        handle_correct(mode)
                    else:
                        handle_wrong(mode)
                    st.rerun()
            else:
                st.error("Bon ordre : " + " ➡️ ".join(correct_order))
                st.markdown(f"*{q.get('explanation','')}*")
                next_question_button(chat, matiere, sujet, mode)

        # ---- LIBRE / OUVERT ----
        elif fmt in ("libre", "ouvert"):
            st.markdown("### 📝 Problème")
            st.info(q.get("problem", q.get("prompt", "")))
            
            if q.get("hint") and not st.session_state.hint_revealed:
                if st.button("💡 Voir un indice"):
                    st.session_state.hint_revealed = True
                    st.rerun()
            elif st.session_state.hint_revealed:
                st.warning(f"💡 Indice : {q.get('hint','')}")

            student_answer = st.text_area("Ta réponse :", disabled=answered)
            
            if not answered:
                if st.button("✅ Valider ma réponse"):
                    if student_answer.strip():
                        with st.spinner("Vérification... 🔍"):
                            exp = q.get("solution") if fmt == "libre" else q.get("criteria")
                            res = evaluate_answer(chat, fmt, exp, student_answer)
                            st.session_state.eval_result = res
                            if res.get("correct"): handle_correct(mode)
                            else: handle_wrong(mode)
                        st.rerun()
            else:
                res = st.session_state.eval_result or {}
                if res.get("correct"): st.success(f"✅ {res.get('feedback','')}")
                else: st.error(f"❌ {res.get('feedback','')}\n\nAttendu : **{q.get('solution','')}**\n*{q.get('explanation','')}*")
                next_question_button(chat, matiere, sujet, mode)

    # Export PDF basique
    st.markdown("---")
    with st.expander("📥 Exporter ma séance en PDF"):
        if st.button("📄 Générer le fichier"):
            try:
                pdf_bytes = generer_pdf(matiere, sujet, mode, st.session_state.messages)
                st.download_button("⬇️ Télécharger", pdf_bytes, file_name="seance.pdf", mime="application/pdf")
            except Exception as e:
                st.error(f"❌ Erreur PDF : {e}")
