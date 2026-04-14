# ==========================================
# core/components.py — Composants UI Streamlit
# ==========================================

import re

import streamlit as st

from core.config import DIFFICULTY_LABELS, MATIERES
from core.engine import (
    evaluate_answer,
    generate_next,
    generate_restart,
    handle_correct,
    handle_wrong,
    init_question,
)

# ==========================================
# COMPOSANTS PARTAGÉS
# ==========================================

def render_score_bar(mode: str) -> None:
    """Affiche la barre difficulté / score / vies."""
    diff = st.session_state.difficulty
    col_d, col_s, col_v = st.columns(3)

    with col_d:
        st.markdown(
            f'<div class="diff-badge diff-{diff}">{DIFFICULTY_LABELS[diff]}</div>',
            unsafe_allow_html=True,
        )
    with col_s:
        st.markdown(
            f'<div class="score-badge">⭐ {st.session_state.score}'
            f'/{st.session_state.total_questions}</div>',
            unsafe_allow_html=True,
        )
    with col_v:
        if mode == "exercice":
            hearts = "❤️" * st.session_state.vies + "🖤" * (3 - st.session_state.vies)
            st.markdown(f'<div class="lives-display">{hearts}</div>', unsafe_allow_html=True)


def next_question_button(
    chat,
    matiere: str,
    sujet: str,
    mode: str,
    label: str = "➡️ Question suivante",
) -> None:
    """
    Bouton pour passer à la question suivante.
    Affiche 'Voir mon score final' si game over imminent.
    """
    is_game_over_pending = mode == "exercice" and st.session_state.vies <= 0
    btn_label = "💀 Voir mon score final" if is_game_over_pending else label

    st.markdown('<div class="launch-btn">', unsafe_allow_html=True)
    if st.button(btn_label, use_container_width=True, key="next_q_btn"):
        if is_game_over_pending:
            st.session_state.game_over = True
            st.rerun()
        with st.spinner("Chargement... ⚡"):
            data, error = generate_next(chat, matiere, sujet, st.session_state.difficulty, False)
            if data:
                init_question(data, st.session_state)
            else:
                st.error(error or "Erreur inconnue lors du chargement.")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# ==========================================
# RENDERERS DE FORMATS DE QUESTIONS
# ==========================================

def render_qcm(q: dict, chat, matiere: str, sujet: str, mode: str) -> None:
    """QCM classique et QCM inverse (même rendu)."""
    # Pour qcm_inverse, la « question » est en fait la réponse donnée
    question_text = q.get("question") or q.get("answer", "")
    st.markdown(f"### ❓ {question_text}")

    choices  = q.get("choices", {})
    correct  = q.get("correct", "")
    answered = st.session_state.answered
    ch_cols  = st.columns(2)

    for i, (key, val) in enumerate(choices.items()):
        if answered:
            if key == correct:
                css = "choice-correct"
            elif key == st.session_state.last_choice:
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
                    handle_correct(st.session_state, mode)
                else:
                    handle_wrong(st.session_state, mode)
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    if answered:
        if st.session_state.last_answer_correct:
            st.success(f"✅ {q.get('explanation', '')}")
        else:
            st.error(f"❌ La réponse était **{correct}**. {q.get('explanation', '')}")
        next_question_button(chat, matiere, sujet, mode)


def render_vrai_faux(q: dict, chat, matiere: str, sujet: str, mode: str) -> None:
    """Question vrai / faux."""
    st.markdown(f"### ✅❌ {q.get('statement', '')}")
    correct_vf = q.get("correct", True)
    answered   = st.session_state.answered
    vf_cols    = st.columns(2)

    with vf_cols[0]:
        if st.button("✅ Vrai", disabled=answered, use_container_width=True):
            st.session_state.vf_choice = True
            if True == correct_vf:
                handle_correct(st.session_state, mode)
            else:
                handle_wrong(st.session_state, mode)
            st.rerun()
    with vf_cols[1]:
        if st.button("❌ Faux", disabled=answered, use_container_width=True):
            st.session_state.vf_choice = False
            if False == correct_vf:
                handle_correct(st.session_state, mode)
            else:
                handle_wrong(st.session_state, mode)
            st.rerun()

    if answered:
        if st.session_state.last_answer_correct:
            st.success(f"✅ {q.get('explanation', '')}")
        else:
            label = "VRAI" if correct_vf else "FAUX"
            st.error(f"❌ C'était **{label}**. {q.get('explanation', '')}")
        next_question_button(chat, matiere, sujet, mode)


def render_trous(q: dict, chat, matiere: str, sujet: str, mode: str) -> None:
    """Texte à trous."""
    st.markdown(f"### ✏️ {q.get('instruction', '')}")
    display = re.sub(r"\[BLANK_\d+\]", "___", q.get("text", ""))
    st.info(display)

    blanks          = q.get("blanks", [])
    answered        = st.session_state.answered
    student_answers = [
        st.text_input(f"Blanc {i + 1} :", disabled=answered, key=f"trou_{i}")
        for i in range(len(blanks))
    ]

    if not answered:
        if st.button("✅ Valider"):
            if all(a.strip() for a in student_answers):
                ok = all(
                    s.strip().lower() == c.strip().lower()
                    for s, c in zip(student_answers, blanks)
                )
                handle_correct(st.session_state, mode) if ok else handle_wrong(st.session_state, mode)
                st.rerun()
    else:
        for i, c in enumerate(blanks):
            st.write(f"Blanc {i + 1} attendu : **{c}**")
        st.markdown(f"*{q.get('explanation', '')}*")
        next_question_button(chat, matiere, sujet, mode)


def render_paires(q: dict, chat, matiere: str, sujet: str, mode: str) -> None:
    """Association gauche ↔ droite."""
    st.markdown(f"### 🔗 {q.get('instruction', '')}")
    pairs    = q.get("pairs", [])
    shuffled = st.session_state.paires_shuffled
    answered = st.session_state.answered

    for i, pair in enumerate(pairs):
        col_l, col_r = st.columns(2)
        col_l.write(f"→ {pair['left']}")
        if answered:
            chosen  = st.session_state.get(f"pair_{i}")
            correct = pair["right"]
            col_r.write(f"Ton choix : {chosen} | Correct : **{correct}**")
        else:
            with col_r:
                st.selectbox("", shuffled, key=f"pair_{i}", label_visibility="collapsed")

    if not answered:
        if st.button("✅ Valider les associations"):
            ok = all(
                st.session_state.get(f"pair_{i}") == p["right"]
                for i, p in enumerate(pairs)
            )
            handle_correct(st.session_state, mode) if ok else handle_wrong(st.session_state, mode)
            st.rerun()
    else:
        st.markdown(f"*{q.get('explanation', '')}*")
        next_question_button(chat, matiere, sujet, mode)


def render_ordre(q: dict, chat, matiere: str, sujet: str, mode: str) -> None:
    """Remise en ordre d'éléments."""
    st.markdown(f"### 🔀 {q.get('instruction', '')}")
    items_shuffled = q.get("items_shuffled", [])
    correct_order  = q.get("correct_order", [])
    answered       = st.session_state.answered

    for pos in range(len(correct_order)):
        st.selectbox(
            f"Position {pos + 1} :",
            items_shuffled,
            key=f"ordre_{pos}",
            disabled=answered,
        )

    if not answered:
        if st.button("✅ Valider l'ordre"):
            student = [st.session_state.get(f"ordre_{p}") for p in range(len(correct_order))]
            if student == correct_order:
                handle_correct(st.session_state, mode)
            else:
                handle_wrong(st.session_state, mode)
            st.rerun()
    else:
        st.error("Bon ordre : " + " ➡️ ".join(correct_order))
        st.markdown(f"*{q.get('explanation', '')}*")
        next_question_button(chat, matiere, sujet, mode)


def render_libre_ouvert(q: dict, chat, matiere: str, sujet: str, mode: str) -> None:
    """Réponse libre ou exercice ouvert avec évaluation par l'IA."""
    st.markdown("### 📝 Problème")
    st.info(q.get("problem") or q.get("prompt", ""))
    answered = st.session_state.answered
    fmt      = q.get("format", "libre")

    # Indice optionnel
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
                    expected = q.get("solution") if fmt == "libre" else q.get("criteria")
                    res = evaluate_answer(chat, fmt, expected, student_answer)
                    st.session_state.eval_result = res
                    if res.get("correct"):
                        handle_correct(st.session_state, mode)
                    else:
                        handle_wrong(st.session_state, mode)
                st.rerun()
    else:
        res = st.session_state.eval_result or {}
        if res.get("correct"):
            st.success(f"✅ {res.get('feedback', '')}")
        else:
            solution = q.get("solution", "")
            explanation = q.get("explanation", "")
            st.error(
                f"❌ {res.get('feedback', '')}\n\n"
                f"Attendu : **{solution}**\n"
                f"*{explanation}*"
            )
        next_question_button(chat, matiere, sujet, mode)


# ── Registre des renderers ────────────────────────────────────────────────────
# Centralisé ici pour éviter de le dupliquer dans app.py et d'autres écrans.
RENDERERS: dict = {
    "qcm":         render_qcm,
    "qcm_inverse": render_qcm,
    "vrai_faux":   render_vrai_faux,
    "trous":       render_trous,
    "paires":      render_paires,
    "ordre":       render_ordre,
    "libre":       render_libre_ouvert,
    "ouvert":      render_libre_ouvert,
}


# ==========================================
# ÉCRAN GAME OVER
# ==========================================

def render_game_over(chat, sujet: str, mode: str) -> None:
    """Affiche l'écran de fin de partie et propose de recommencer."""
    st.error("💀 Plus de vies ! C'est la fin de la séance.")
    st.markdown(
        f"**Score final : {st.session_state.score} / {st.session_state.total_questions}** 🎯"
    )

    st.markdown('<div class="launch-btn">', unsafe_allow_html=True)
    if st.button("🔄 Recommencer avec 3 vies", use_container_width=True):
        st.session_state.vies            = 3
        st.session_state.game_over       = False
        st.session_state.score           = 0
        st.session_state.total_questions = 0
        st.session_state.difficulty      = "facile"
        with st.spinner("On repart avec de nouveaux exercices ! 🚀"):
            data, error = generate_restart(chat, sujet)
            if data:
                init_question(data, st.session_state)
            else:
                st.error(error or "Erreur inconnue.")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# ==========================================
# ÉCRAN SETUP
# ==========================================

def render_setup(on_launch) -> None:
    """
    Écran de configuration initiale de la séance.
    Appelle on_launch(matiere, sujet, mode) quand l'utilisateur valide.
    """
    # ── 1. Matière ──────────────────────────────────────────────────────────
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

    # ── 2. Mode ─────────────────────────────────────────────────────────────
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

    # ── 3. Sujet & Photo ─────────────────────────────────────────────────────
    sujet = st.text_input(
        "3️⃣ Sur quel sujet veux-tu travailler ?",
        placeholder="Ex: Les fractions, L'eau...",
    )
    photo = st.file_uploader(
        "4️⃣ Tu as un examen blanc ? (Optionnel)",
        type=["png", "jpg", "jpeg"],
    )

    st.markdown("---")

    # ── Lancement ────────────────────────────────────────────────────────────
    st.markdown('<div class="launch-btn">', unsafe_allow_html=True)
    if st.button("🚀 Lancer ma séance !", use_container_width=True):
        if not matiere_choisie or not st.session_state.mode_temp or not sujet.strip():
            st.warning("⚠️ Remplis bien la matière, le mode et le sujet !")
        else:
            on_launch(matiere_choisie, sujet, st.session_state.mode_temp, photo)
    st.markdown("</div>", unsafe_allow_html=True)


# ==========================================
# ÉCRAN SÉANCE EN COURS
# ==========================================

def render_seance(on_reset) -> None:
    """
    Écran principal de la séance.
    on_reset : callback appelé quand l'utilisateur clique sur Reset.
    """
    matiere = st.session_state.matiere
    sujet   = st.session_state.sujet
    mode    = st.session_state.mode
    chat    = st.session_state.chat_session
    q       = st.session_state.current_question
    fmt     = q.get("format", "libre") if q else None

    # ── Barre de contexte ───────────────────────────────────────────────────
    col_ctx, col_reset = st.columns([5, 1])
    with col_ctx:
        st.markdown(
            f'<div class="session-card">'
            f'{MATIERES.get(matiere, "📚")} <b>{matiere}</b> — {sujet}'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col_reset:
        if st.button("🔄 Reset"):
            on_reset()
            st.rerun()

    render_score_bar(mode)
    st.markdown("---")

    # ── Contenu principal ───────────────────────────────────────────────────
    if st.session_state.game_over:
        render_game_over(chat, sujet, mode)

    elif q:
        renderer = RENDERERS.get(fmt)
        if renderer:
            renderer(q, chat, matiere, sujet, mode)
        else:
            st.warning(f"⚠️ Format inconnu : {fmt}")

    # ── Export PDF ──────────────────────────────────────────────────────────
    st.markdown("---")
    _render_pdf_export(matiere, sujet, mode)


def _render_pdf_export(matiere: str, sujet: str, mode: str) -> None:
    """Section d'export PDF repliable."""
    from core.engine import generer_pdf
    with st.expander("📥 Exporter ma séance en PDF"):
        if st.button("📄 Générer le fichier"):
            try:
                pdf_bytes = generer_pdf(matiere, sujet, mode, st.session_state.messages)
                st.download_button(
                    "⬇️ Télécharger",
                    pdf_bytes,
                    file_name="seance.pdf",
                    mime="application/pdf",
                )
            except Exception as exc:
                st.error(f"❌ Erreur PDF : {exc}")
