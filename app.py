# ==========================================
# app.py — Interface Streamlit (cœur de l'app)
# ==========================================
import sys
import os

# 1. On force l'ajout du dossier racine au chemin de Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import re
import streamlit as st
import google.generativeai as genai
from PIL import Image

from core.config import (
    APP_CSS,
    DIFFICULTY_LABELS,
    MATIERES,
    SESSION_DEFAULTS,
)
from core.engine import (
    creer_chat,
    generate_next,
    generate_restart,
    evaluate_answer,
    analyser_photo,
    generer_pdf,
    handle_correct,
    handle_wrong,
    init_question,
)

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
# CSS
# ==========================================
st.markdown(APP_CSS, unsafe_allow_html=True)

# ==========================================
# SESSION STATE
# ==========================================
for _k, _v in SESSION_DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


def reset_seance():
    for k, v in SESSION_DEFAULTS.items():
        st.session_state[k] = v


def get_ui_type(matiere: str, mode: str) -> str:
    return "cours" if mode == "cours" else "exercice"


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
# COMPOSANTS UI RÉUTILISABLES
# ==========================================

def _next_question_button(chat, matiere, sujet, mode, label="➡️ Question suivante"):
    """Bouton pour passer à la question suivante (ou terminer si game over)."""
    is_game_over_pending = mode == "exercice" and st.session_state.vies <= 0
    btn_label = "💀 Voir mon score final" if is_game_over_pending else label

    st.markdown('<div class="launch-btn">', unsafe_allow_html=True)
    if st.button(btn_label, use_container_width=True, key="next_q_btn"):
        if is_game_over_pending:
            st.session_state.game_over = True
            st.rerun()
        with st.spinner("Chargement... ⚡"):
            data, raw = generate_next(chat, matiere, sujet, st.session_state.difficulty, False)
            if data:
                init_question(data, st.session_state)
            else:
                st.session_state.messages.append({"role": "assistant", "content": raw})
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _render_score_bar(mode):
    """Affiche difficulté, score et vies."""
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


# ==========================================
# ÉCRAN SETUP
# ==========================================

def render_setup():
    # ── 1. Matière ──
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

    # ── 2. Mode ──
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

    # ── 3. Sujet & Photo ──
    sujet = st.text_input("3️⃣ Sur quel sujet veux-tu travailler ?", placeholder="Ex: Les fractions, L'eau...")
    photo = st.file_uploader("4️⃣ Tu as un examen blanc ? (Optionnel)", type=["png", "jpg", "jpeg"])

    st.markdown("---")

    # ── Lancement ──
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
                        init_question(data, st.session_state)
                    else:
                        st.session_state.messages.append({"role": "assistant", "content": raw})
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erreur au démarrage : {e}")
    st.markdown("</div>", unsafe_allow_html=True)


# ==========================================
# RENDU DES FORMATS DE QUESTIONS
# ==========================================

def _render_qcm(q, chat, matiere, sujet, mode):
    st.markdown(f"### ❓ {q.get('question', q.get('answer', ''))}")
    choices  = q.get("choices", {})
    correct  = q.get("correct", "")
    answered = st.session_state.answered
    ch_cols  = st.columns(2)

    for i, (key, val) in enumerate(choices.items()):
        css = "choice-btn"
        if answered:
            css = "choice-correct" if key == correct else ("choice-wrong" if key == st.session_state.last_choice else "choice-btn")
        with ch_cols[i % 2]:
            st.markdown(f'<div class="{css}">', unsafe_allow_html=True)
            if st.button(f"{key}. {val}", key=f"qcm_{key}", use_container_width=True, disabled=answered):
                st.session_state.last_choice = key
                handle_correct(st.session_state, mode) if key == correct else handle_wrong(st.session_state, mode)
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    if answered:
        if st.session_state.last_answer_correct:
            st.success(f"✅ {q.get('explanation', '')}")
        else:
            st.error(f"❌ La réponse était **{correct}**. {q.get('explanation', '')}")
        _next_question_button(chat, matiere, sujet, mode)


def _render_vrai_faux(q, chat, matiere, sujet, mode):
    st.markdown(f"### ✅❌ {q.get('statement', '')}")
    correct_vf = q.get("correct", True)
    answered   = st.session_state.answered
    vf_cols    = st.columns(2)

    with vf_cols[0]:
        if st.button("✅ Vrai", disabled=answered, use_container_width=True):
            st.session_state.vf_choice = True
            handle_correct(st.session_state, mode) if True == correct_vf else handle_wrong(st.session_state, mode)
            st.rerun()
    with vf_cols[1]:
        if st.button("❌ Faux", disabled=answered, use_container_width=True):
            st.session_state.vf_choice = False
            handle_correct(st.session_state, mode) if False == correct_vf else handle_wrong(st.session_state, mode)
            st.rerun()

    if answered:
        if st.session_state.last_answer_correct:
            st.success(f"✅ {q.get('explanation', '')}")
        else:
            st.error(f"❌ C'était **{'VRAI' if correct_vf else 'FAUX'}**. {q.get('explanation', '')}")
        _next_question_button(chat, matiere, sujet, mode)


def _render_trous(q, chat, matiere, sujet, mode):
    st.markdown(f"### ✏️ {q.get('instruction', '')}")
    display = re.sub(r"\[BLANK_\d+\]", "___", q.get("text", ""))
    st.info(display)

    blanks          = q.get("blanks", [])
    answered        = st.session_state.answered
    student_answers = [st.text_input(f"Blanc {i+1} :", disabled=answered) for i in range(len(blanks))]

    if not answered:
        if st.button("✅ Valider"):
            if all(a.strip() for a in student_answers):
                ok = all(s.strip().lower() == c.strip().lower() for s, c in zip(student_answers, blanks))
                handle_correct(st.session_state, mode) if ok else handle_wrong(st.session_state, mode)
                st.rerun()
    else:
        for i, c in enumerate(blanks):
            st.write(f"Blanc {i+1} attendu : **{c}**")
        st.markdown(f"*{q.get('explanation', '')}*")
        _next_question_button(chat, matiere, sujet, mode)


def _render_paires(q, chat, matiere, sujet, mode):
    st.markdown(f"### 🔗 {q.get('instruction', '')}")
    pairs    = q.get("pairs", [])
    shuffled = st.session_state.paires_shuffled
    answered = st.session_state.answered

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
            ok = all(st.session_state.get(f"pair_{i}") == p["right"] for i, p in enumerate(pairs))
            handle_correct(st.session_state, mode) if ok else handle_wrong(st.session_state, mode)
            st.rerun()
    else:
        st.markdown(f"*{q.get('explanation', '')}*")
        _next_question_button(chat, matiere, sujet, mode)


def _render_ordre(q, chat, matiere, sujet, mode):
    st.markdown(f"### 🔀 {q.get('instruction', '')}")
    items_shuffled = q.get("items_shuffled", [])
    correct_order  = q.get("correct_order", [])
    answered       = st.session_state.answered

    for pos in range(len(correct_order)):
        st.selectbox(f"Position {pos+1} :", items_shuffled, key=f"ordre_{pos}", disabled=answered)

    if not answered:
        if st.button("✅ Valider l'ordre"):
            student = [st.session_state.get(f"ordre_{p}") for p in range(len(correct_order))]
            handle_correct(st.session_state, mode) if student == correct_order else handle_wrong(st.session_state, mode)
            st.rerun()
    else:
        st.error("Bon ordre : " + " ➡️ ".join(correct_order))
        st.markdown(f"*{q.get('explanation', '')}*")
        _next_question_button(chat, matiere, sujet, mode)


def _render_libre_ouvert(q, chat, matiere, sujet, mode):
    st.markdown("### 📝 Problème")
    st.info(q.get("problem", q.get("prompt", "")))
    answered = st.session_state.answered
    fmt      = q.get("format", "libre")

    if q.get("hint") and not st.session_state.hint_revealed:
        if st.button("💡 Voir un indice"):
            st.session_state.hint_revealed = True
            st.rerun()
    elif st.session_state.hint_revealed:
        st.warning(f"💡 Indice : {q.get('hint', '')}")

    student_answer = st.text_area("Ta réponse :", disabled=answered)

    if not answered:
        if st.button("✅ Valider ma réponse"):
            if student_answer.strip():
                with st.spinner("Vérification... 🔍"):
                    exp = q.get("solution") if fmt == "libre" else q.get("criteria")
                    res = evaluate_answer(chat, fmt, exp, student_answer)
                    st.session_state.eval_result = res
                    handle_correct(st.session_state, mode) if res.get("correct") else handle_wrong(st.session_state, mode)
                st.rerun()
    else:
        res = st.session_state.eval_result or {}
        if res.get("correct"):
            st.success(f"✅ {res.get('feedback', '')}")
        else:
            st.error(f"❌ {res.get('feedback', '')}\n\nAttendu : **{q.get('solution', '')}**\n*{q.get('explanation', '')}*")
        _next_question_button(chat, matiere, sujet, mode)


# ==========================================
# ÉCRAN GAME OVER
# ==========================================

def render_game_over(chat, sujet, mode):
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
            data, raw = generate_restart(chat, sujet)
            if data:
                init_question(data, st.session_state)
            else:
                st.session_state.messages.append({"role": "assistant", "content": raw})
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# ==========================================
# ÉCRAN SÉANCE EN COURS
# ==========================================

def render_seance():
    matiere = st.session_state.matiere
    sujet   = st.session_state.sujet
    mode    = st.session_state.mode
    chat    = st.session_state.chat_session
    q       = st.session_state.current_question
    fmt     = q.get("format", "libre") if q else None

    # ── Barre de contexte ──
    col_ctx, col_reset = st.columns([5, 1])
    with col_ctx:
        st.markdown(
            f'<div class="session-card">{MATIERES.get(matiere, "📚")} <b>{matiere}</b> — {sujet}</div>',
            unsafe_allow_html=True,
        )
    with col_reset:
        if st.button("🔄 Reset"):
            reset_seance()
            st.rerun()

    _render_score_bar(mode)
    st.markdown("---")

    # ── Contenu principal ──
    if st.session_state.game_over:
        render_game_over(chat, sujet, mode)

    elif q:
        RENDERERS = {
            "qcm":        _render_qcm,
            "qcm_inverse":_render_qcm,
            "vrai_faux":  _render_vrai_faux,
            "trous":      _render_trous,
            "paires":     _render_paires,
            "ordre":      _render_ordre,
            "libre":      _render_libre_ouvert,
            "ouvert":     _render_libre_ouvert,
        }
        renderer = RENDERERS.get(fmt)
        if renderer:
            renderer(q, chat, matiere, sujet, mode)
        else:
            st.warning(f"⚠️ Format inconnu : {fmt}")

    # ── Export PDF ──
    st.markdown("---")
    with st.expander("📥 Exporter ma séance en PDF"):
        if st.button("📄 Générer le fichier"):
            try:
                pdf_bytes = generer_pdf(matiere, sujet, mode, st.session_state.messages)
                st.download_button(
                    "⬇️ Télécharger", pdf_bytes,
                    file_name="seance.pdf", mime="application/pdf",
                )
            except Exception as e:
                st.error(f"❌ Erreur PDF : {e}")


# ==========================================
# POINT D'ENTRÉE
# ==========================================
if not st.session_state.seance_lancee:
    render_setup()
else:
    render_seance()
