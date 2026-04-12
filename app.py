

import streamlit as st
import google.generativeai as genai
from PIL import Image
from fpdf import FPDF

# ==========================================
# CONFIG PAGE (doit être en premier absolu)
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

QUICK_REPLIES = [
    ("💡 Un indice",        "Je bloque, peux-tu me donner un indice ?"),
    ("🤔 J'ai pas compris", "Je n'ai pas compris, peux-tu réexpliquer autrement ?"),
    ("✅ J'ai compris !",   "J'ai compris, on peut passer à la suite !"),
    ("🔄 Autre exercice",   "Peux-tu me proposer un exercice similaire différent ?"),
]

SYSTEM_PROMPT = """Tu es un tuteur super sympa, bienveillant et patient pour des élèves de 5ème (collège, 12-13 ans).
Ton objectif : générer des exercices adaptés au niveau 5ème et les corriger pas-à-pas avec l'élève.

RÈGLES PÉDAGOGIQUES — à respecter ABSOLUMENT :
1. Commence TOUJOURS la toute première réponse par une courte blague ou devinette rigolote pour détendre l'atmosphère.
2. Ne donne JAMAIS l'exercice complet en une seule fois — une seule sous-question à la fois.
3. Attends TOUJOURS la réponse de l'élève avant de continuer.
4. Si l'élève se trompe : encourage-le d'abord ("Presque ! Tu chauffes 🔥"), puis donne un petit indice SANS donner la réponse directement.
5. Si l'élève bloque encore après 2 tentatives : explique la solution avec des mots simples et un exemple concret.
6. Utilise TOUJOURS le tutoiement, des emojis et un ton jeune, chaleureux et motivant.
7. Tes messages doivent être COURTS : 3 à 5 lignes maximum, jamais de longs pavés.
8. Quand un exercice est entièrement terminé et corrigé, génère une synthèse courte précédée du tag [SYNTHESE].

RÉPONSES SPÉCIALES à gérer :
- "Je bloque, peux-tu me donner un indice ?" → donne un indice progressif et bienveillant.
- "Je n'ai pas compris, peux-tu réexpliquer autrement ?" → réexplique avec un exemple concret différent, encore plus simple.
- "J'ai compris, on peut passer à la suite !" → valide et passe à l'étape suivante.
- "Peux-tu me proposer un exercice similaire différent ?" → génère un nouvel exercice du même type avec des données différentes.
"""

# ==========================================
# CSS CHEERFUL
# ==========================================
st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

/* ── Hero header ── */
.hero-header {
    background: linear-gradient(135deg, #FF6B6B 0%, #FFE66D 55%, #4ECDC4 100%);
    border-radius: 20px;
    padding: 1.6rem 2rem;
    margin-bottom: 1.8rem;
    text-align: center;
    box-shadow: 0 4px 18px rgba(0,0,0,0.12);
}
.hero-header h1 {
    color: white; font-size: 2rem; margin: 0;
    text-shadow: 1px 2px 4px rgba(0,0,0,0.2);
}
.hero-header p {
    color: rgba(255,255,255,0.92); margin: 0.4rem 0 0; font-size: 1rem;
}

/* ── Tuiles matières ── */
div[data-testid="stButton"].mat-btn > button {
    height: 72px !important;
    border-radius: 16px !important;
    font-size: 0.88rem !important;
    font-weight: bold !important;
    background-color: #f8f9ff !important;
    border: 3px solid #e0e4ff !important;
    color: #333 !important;
    white-space: pre-line !important;
    line-height: 1.4 !important;
    transition: all 0.18s ease !important;
}
div[data-testid="stButton"].mat-btn > button:hover {
    background-color: #4ECDC4 !important;
    color: white !important;
    border-color: #4ECDC4 !important;
    transform: translateY(-3px) !important;
    box-shadow: 0 6px 16px rgba(78,205,196,0.35) !important;
}
div[data-testid="stButton"].mat-btn-selected > button {
    background-color: #FF6B6B !important;
    color: white !important;
    border-color: #FF6B6B !important;
    box-shadow: 0 4px 14px rgba(255,107,107,0.4) !important;
    height: 72px !important;
    border-radius: 16px !important;
    font-size: 0.88rem !important;
    font-weight: bold !important;
    white-space: pre-line !important;
    line-height: 1.4 !important;
}

/* ── Bouton principal lancement ── */
div[data-testid="stButton"].launch-btn > button {
    background: linear-gradient(135deg, #FF6B6B, #FF8E53) !important;
    color: white !important;
    border-radius: 50px !important;
    border: none !important;
    font-size: 1.1rem !important;
    font-weight: bold !important;
    padding: 0.85rem 2rem !important;
    width: 100% !important;
    box-shadow: 0 5px 18px rgba(255,107,107,0.45) !important;
    transition: all 0.2s !important;
}
div[data-testid="stButton"].launch-btn > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 24px rgba(255,107,107,0.55) !important;
}

/* ── Réponses rapides ── */
div[data-testid="stButton"].qr-btn > button {
    background-color: #f0f4ff !important;
    color: #444 !important;
    border-radius: 50px !important;
    border: 2px solid #d0d8ff !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    transition: all 0.15s !important;
}
div[data-testid="stButton"].qr-btn > button:hover {
    background-color: #4ECDC4 !important;
    color: white !important;
    border-color: #4ECDC4 !important;
    transform: translateY(-1px) !important;
}

/* ── Bouton reset ── */
div[data-testid="stButton"].reset-btn > button {
    background: transparent !important;
    border: 2px solid #ddd !important;
    color: #888 !important;
    border-radius: 50px !important;
    font-size: 0.82rem !important;
    transition: all 0.15s !important;
}
div[data-testid="stButton"].reset-btn > button:hover {
    border-color: #FF6B6B !important;
    color: #FF6B6B !important;
}

/* ── Carte contexte séance ── */
.session-card {
    background: linear-gradient(90deg, #f0fff4, #f0f4ff);
    border-left: 5px solid #4ECDC4;
    border-radius: 12px;
    padding: 0.75rem 1.2rem;
    font-size: 0.95rem;
    color: #333;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# SESSION STATE
# ==========================================
_DEFAULTS = {
    "seance_lancee":         False,
    "messages":              [],
    "chat_session":          None,
    "matiere":               "",
    "sujet":                 "",
    "matiere_temp":          "",
    "quick_replies_on":      True,
    "quick_reply_triggered": None,
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


def reset_seance():
    for k, v in _DEFAULTS.items():
        st.session_state[k] = v


# ==========================================
# GEMINI HELPERS
# ==========================================
MODEL_NAME = "gemini-2.5-flash-lite"

# Thinking désactivé : inutile pour du tutorat 5ème, et très coûteux en tokens
GENERATION_CONFIG = genai.GenerationConfig(
    temperature=0.7,
)


def creer_chat(matiere: str, sujet: str):
    """Crée un modèle avec system_instruction au niveau modèle + chat natif."""
    system = SYSTEM_PROMPT + f"\n\nMatière de la séance : {matiere}\nSujet de la séance : {sujet}"
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=system,
        generation_config=GENERATION_CONFIG,
    )
    return model.start_chat(history=[])


def analyser_photo(image: Image.Image, matiere: str) -> str:
    """Analyse un examen blanc (image) et retourne des exercices similaires."""
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=SYSTEM_PROMPT,
        generation_config=GENERATION_CONFIG,
    )
    prompt = (
        f"Voici une photo d'examen blanc de {matiere} (niveau 5ème). "
        "Analyse les types et le niveau de difficulté des exercices. "
        "Génère 2 ou 3 exercices similaires avec des données différentes. "
        "Présente-les clairement numérotés. N'inclus pas les corrections."
    )
    response = model.generate_content([image, prompt])
    return response.text


def generer_pdf(matiere: str, sujet: str, messages: list) -> bytes:
    """Génère un PDF imprimable avec les exercices du tuteur + lignes de réponse."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(15, 15, 15)

    # En-tête coloré
    pdf.set_fill_color(255, 107, 107)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 14, "Fiche d'exercice  -  Classe de 5eme", ln=True, align="C", fill=True)
    pdf.set_text_color(80, 80, 80)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"Matiere : {matiere}   |   Sujet : {sujet}", ln=True, align="C")
    pdf.ln(8)

    # Exercices (messages IA uniquement)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Exercice propose par ton tuteur IA :", ln=True)
    pdf.ln(3)
    pdf.set_font("Arial", "", 11)
    for msg in messages:
        if msg["role"] == "assistant":
            content = msg["content"].replace("[SYNTHESE]", "").strip()
            safe = content.encode("latin-1", errors="replace").decode("latin-1")
            pdf.multi_cell(0, 7, safe)
            pdf.ln(3)

    # Zone réponses élève
    pdf.ln(6)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(8)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Mes reponses :", ln=True)
    pdf.ln(4)
    for _ in range(12):
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
# ÉCRAN SETUP (pas de séance en cours)
# ==========================================
if not st.session_state.seance_lancee:

    # ── Sélection matière en tuiles ──
    st.markdown("### 1️⃣ Choisis ta matière")
    cols = st.columns(4)
    for i, (mat, emoji) in enumerate(MATIERES.items()):
        is_selected = (st.session_state.matiere_temp == mat)
        css_class = "mat-btn-selected" if is_selected else "mat-btn"
        label = f"{'✅ ' if is_selected else ''}{emoji}\n{mat}"
        with cols[i % 4]:
            st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
            if st.button(label, key=f"mat_{mat}", use_container_width=True):
                st.session_state.matiere_temp = mat
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    matiere_choisie = st.session_state.matiere_temp
    if matiere_choisie == "Autre":
        matiere_choisie = st.text_input(
            "Précise ta matière :",
            placeholder="Ex: Technologie, Latin, Musique..."
        )

    st.markdown("---")

    # ── Sujet ──
    st.markdown("### 2️⃣ Sur quel sujet veux-tu travailler ?")
    sujet = st.text_input(
        "",
        placeholder="Ex: Les fractions, La Révolution française, Les volcans...",
        label_visibility="collapsed",
    )

    # ── Photo examen (optionnel) ──
    st.markdown("### 3️⃣ Tu as un examen blanc à analyser ? *(optionnel)*")
    st.caption("📷 Upload une photo — l'IA génère des exercices du même type pour t'entraîner.")
    photo = st.file_uploader(
        "Dépose une photo ici",
        type=["png", "jpg", "jpeg"],
        label_visibility="collapsed",
    )
    if photo:
        st.image(photo, caption="Photo reçue ✅", width=260)

    st.markdown("---")

    # ── Bouton lancement ──
    st.markdown('<div class="launch-btn">', unsafe_allow_html=True)
    lancer = st.button("🚀 Lancer ma séance de révision !", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if lancer:
        if not matiere_choisie or matiere_choisie == "Autre":
            st.warning("⚠️ Choisis une matière avant de commencer !")
        elif not sujet.strip():
            st.warning("⚠️ Dis-moi sur quel sujet tu veux travailler !")
        else:
            with st.spinner("Ton tuteur se prépare... 🎯"):
                try:
                    chat = creer_chat(matiere_choisie, sujet)
                    st.session_state.chat_session = chat
                    st.session_state.matiere = matiere_choisie
                    st.session_state.sujet = sujet
                    st.session_state.seance_lancee = True

                    if photo:
                        img = Image.open(photo)
                        exercices_photo = analyser_photo(img, matiere_choisie)
                        prompt_init = (
                            f"L'élève a fourni un examen blanc. "
                            f"Voici des exercices similaires générés depuis sa photo :\n\n{exercices_photo}\n\n"
                            "Commence par ta blague habituelle, "
                            "puis propose le premier exercice micro-étape par micro-étape."
                        )
                    else:
                        prompt_init = (
                            "Commence par ta blague, puis démarre le premier exercice "
                            "sur le sujet défini, micro-étape par micro-étape."
                        )

                    response = chat.send_message(prompt_init)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response.text,
                    })
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Erreur au démarrage : {e}")


# ==========================================
# SÉANCE EN COURS
# ==========================================
else:

    # ── Barre contexte + reset ──
    col_ctx, col_reset = st.columns([5, 1])
    with col_ctx:
        emoji_mat = MATIERES.get(st.session_state.matiere, "📚")
        st.markdown(
            f'<div class="session-card">'
            f'{emoji_mat} <b>{st.session_state.matiere}</b>'
            f' — {st.session_state.sujet}</div>',
            unsafe_allow_html=True,
        )
    with col_reset:
        st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
        if st.button("🔄 Reset", use_container_width=True):
            reset_seance()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Toggle réponses rapides ──
    st.session_state.quick_replies_on = st.toggle(
        "💬 Boutons de réponse rapide",
        value=st.session_state.quick_replies_on,
    )

    st.markdown("---")

    # ── Historique chat ──
    for msg in st.session_state.messages:
        avatar = "🎓" if msg["role"] == "assistant" else "🧑‍🎓"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"].replace("[SYNTHESE]", "").strip())

    # ── Boutons réponses rapides ──
    if st.session_state.quick_replies_on:
        qr_cols = st.columns(len(QUICK_REPLIES))
        for i, (label, text) in enumerate(QUICK_REPLIES):
            with qr_cols[i]:
                st.markdown('<div class="qr-btn">', unsafe_allow_html=True)
                if st.button(label, key=f"qr_{i}", use_container_width=True):
                    st.session_state.quick_reply_triggered = text
                st.markdown("</div>", unsafe_allow_html=True)

    # ── Traitement réponse rapide ──
    if st.session_state.quick_reply_triggered:
        user_msg = st.session_state.quick_reply_triggered
        st.session_state.quick_reply_triggered = None
        st.session_state.messages.append({"role": "user", "content": user_msg})
        with st.chat_message("user", avatar="🧑‍🎓"):
            st.markdown(user_msg)
        with st.chat_message("assistant", avatar="🎓"):
            with st.spinner("Ton tuteur réfléchit... 🤔"):
                try:
                    resp = st.session_state.chat_session.send_message(user_msg)
                    ai_text = resp.text
                    st.markdown(ai_text.replace("[SYNTHESE]", "").strip())
                    st.session_state.messages.append({"role": "assistant", "content": ai_text})
                except Exception as e:
                    st.error(f"❌ Erreur : {e}")
        st.rerun()

    # ── Input texte libre ──
    if user_input := st.chat_input("✏️ Écris ta réponse ici..."):
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar="🧑‍🎓"):
            st.markdown(user_input)
        with st.chat_message("assistant", avatar="🎓"):
            with st.spinner("Ton tuteur réfléchit... 🤔"):
                try:
                    resp = st.session_state.chat_session.send_message(user_input)
                    ai_text = resp.text
                    st.markdown(ai_text.replace("[SYNTHESE]", "").strip())
                    st.session_state.messages.append({"role": "assistant", "content": ai_text})
                except Exception as e:
                    st.error(f"❌ Erreur : {e}")
        st.rerun()

    # ── Confettis si exercice terminé ──
    if any(
        "[SYNTHESE]" in m["content"]
        for m in st.session_state.messages
        if m["role"] == "assistant"
    ):
        st.balloons()
        st.success("🎉 Bravo, tu as fini l'exercice ! Lance-en un nouveau ou télécharge ta fiche.")

    # ── Export PDF ──
    st.markdown("---")
    with st.expander("📥 Faire l'exercice sur papier ? Exporte-le en PDF"):
        st.caption("Génère une fiche imprimable avec l'exercice et des lignes pour écrire tes réponses.")
        if st.button("📄 Générer ma fiche PDF"):
            try:
                pdf_bytes = generer_pdf(
                    st.session_state.matiere,
                    st.session_state.sujet,
                    st.session_state.messages,
                )
                st.download_button(
                    label="⬇️ Télécharger le PDF",
                    data=pdf_bytes,
                    file_name=f"exercice_{st.session_state.matiere.lower().replace(' ', '_')}.pdf",
                    mime="application/pdf",
                )
            except Exception as e:
                st.error(f"❌ Erreur PDF : {e}")
