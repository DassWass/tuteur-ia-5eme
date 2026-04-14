# ==========================================
# core/engine.py — Moteur IA & Logique Métier
# ==========================================

import json
import logging
import random
import re

import google.generativeai as genai
import streamlit as st
from fpdf import FPDF
from PIL import Image

from core.config import DIFFICULTY_LABELS, DIFFICULTY_ORDER, MODEL_NAME
from core.prompts import (
    SYSTEM_COURS,
    SYSTEM_EXERCICE,
    build_eval_prompt,
    build_first_prompt,
    build_next_prompt,
    build_restart_prompt,
    build_system_prompt,
)

logger = logging.getLogger("tuteur_ia.engine")

# ── Configuration Gemini ───────────────────────────────────────────────────────
# Température basse (0.3) + forçage JSON natif pour des réponses stables
GENERATION_CONFIG = genai.GenerationConfig(
    temperature=0.3,
    response_mime_type="application/json",
)


# ── Helpers internes ───────────────────────────────────────────────────────────

@st.cache_resource
def _get_cached_model(system_prompt: str):
    """
    Instancie (et met en cache) un modèle Gemini pour un system prompt donné.
    Le cache évite de recréer un objet modèle identique à chaque rerun Streamlit.
    """
    logger.debug("Création d'un nouveau modèle Gemini (cache miss).")
    return genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=system_prompt,
        generation_config=GENERATION_CONFIG,
    )


def parse_json_response(text: str) -> dict | None:
    """
    Tente de parser une réponse texte en dict JSON.
    Essaie d'abord un parse direct, puis nettoie les balises markdown.
    Retourne None si les deux tentatives échouent.
    """
    try:
        return json.loads(text)
    except Exception:
        pass
    try:
        clean = re.sub(r"```json|```", "", text).strip()
        return json.loads(clean)
    except Exception:
        logger.warning("Impossible de parser la réponse JSON : %s", text[:200])
        return None


# ── Session de chat ────────────────────────────────────────────────────────────

def creer_chat(matiere: str, sujet: str, ui_type: str):
    """Crée et retourne une session de chat Gemini configurée."""
    system = build_system_prompt(ui_type, matiere, sujet)
    model = _get_cached_model(system)
    return model.start_chat(history=[])


# ── Génération de questions ────────────────────────────────────────────────────
# Convention de retour unifiée : (data: dict | None, error: str | None)
# • Succès  → (dict, None)
# • Échec   → (None, message_d_erreur)

def generate_next(
    chat_session,
    matiere: str,
    sujet: str,
    difficulty: str,
    is_first: bool,
) -> tuple[dict | None, str | None]:
    """
    Génère la prochaine question via Gemini.
    Retourne (data, None) en cas de succès, (None, erreur) en cas d'échec.
    """
    diff_label = DIFFICULTY_LABELS[difficulty]
    prompt = (
        build_first_prompt(matiere, sujet, diff_label)
        if is_first
        else build_next_prompt(sujet, diff_label)
    )
    try:
        response = chat_session.send_message(prompt)
        data = parse_json_response(response.text)
        if data is None:
            return None, "La réponse de l'IA n'était pas au bon format. Réessaie ! 🤔"
        return data, None
    except Exception as exc:
        logger.error("generate_next — %s", exc, exc_info=True)
        return None, f"❌ Erreur de génération : {exc}"


def generate_restart(
    chat_session,
    sujet: str,
    difficulty: str = "facile",
) -> tuple[dict | None, str | None]:
    """
    Génère une nouvelle question après un game over.
    Retourne (data, None) en cas de succès, (None, erreur) en cas d'échec.
    """
    diff_label = DIFFICULTY_LABELS[difficulty]
    prompt = build_restart_prompt(sujet, diff_label)
    try:
        response = chat_session.send_message(prompt)
        data = parse_json_response(response.text)
        if data is None:
            return None, "La réponse de l'IA n'était pas au bon format. Réessaie ! 🤔"
        return data, None
    except Exception as exc:
        logger.error("generate_restart — %s", exc, exc_info=True)
        return None, f"❌ Erreur au redémarrage : {exc}"


# ── Évaluation de réponse libre ────────────────────────────────────────────────

def evaluate_answer(
    chat_session,
    fmt: str,
    expected,
    student_answer: str,
) -> dict:
    """
    Envoie la réponse de l'élève à Gemini pour évaluation.
    Retourne toujours un dict {"correct": bool, "feedback": str}.
    En cas d'erreur technique, retourne correct=False avec un message dédié.
    """
    prompt = build_eval_prompt(fmt, expected, student_answer)
    try:
        response = chat_session.send_message(prompt)
        data = parse_json_response(response.text)
        if data and "correct" in data:
            return data
        logger.warning("evaluate_answer — réponse inattendue : %s", response.text[:200])
        return {"correct": False, "feedback": "Je n'ai pas pu évaluer ta réponse, réessaie ! 🤔"}
    except Exception as exc:
        logger.error("evaluate_answer — %s", exc, exc_info=True)
        return {"correct": False, "feedback": f"Petit bug technique, réessaie ! ({exc})"}


# ── Analyse de photo d'examen ──────────────────────────────────────────────────

def analyser_photo(image: Image.Image, matiere: str, ui_type: str) -> str:
    """
    Analyse une photo d'examen blanc et retourne des exercices similaires.
    Utilise un modèle sans historique de chat (inférence ponctuelle).
    """
    base = SYSTEM_EXERCICE if ui_type == "exercice" else SYSTEM_COURS
    model = _get_cached_model(base)
    prompt = (
        "Voici une photo d'examen blanc. "
        "Analyse les types et le niveau des exercices. "
        "Génère 2 ou 3 exercices similaires."
    )
    try:
        result = model.generate_content([image, prompt])
        return result.text
    except Exception as exc:
        logger.error("analyser_photo — %s", exc, exc_info=True)
        return ""


# ── Logique de difficulté ──────────────────────────────────────────────────────

def advance_difficulty(current: str) -> str:
    """Passe au niveau de difficulté suivant (plafonne à 'difficile')."""
    idx = DIFFICULTY_ORDER.index(current)
    return DIFFICULTY_ORDER[min(idx + 1, len(DIFFICULTY_ORDER) - 1)]


# ── Gestion de l'état de la question ──────────────────────────────────────────

def init_question(data: dict, session_state) -> None:
    """Initialise le session state Streamlit pour une nouvelle question."""
    session_state.current_question    = data
    session_state.answered            = False
    session_state.last_answer_correct = None
    session_state.last_choice         = None
    session_state.vf_choice           = None
    session_state.hint_revealed       = False
    session_state.eval_result         = None

    if data.get("format") == "paires":
        rights = [p["right"] for p in data.get("pairs", [])]
        random.shuffle(rights)
        session_state.paires_shuffled = rights
    else:
        session_state.paires_shuffled = []


def handle_correct(session_state, mode: str) -> None:
    """Applique les effets d'une bonne réponse."""
    session_state.score              += 1
    session_state.total_questions    += 1
    session_state.answered            = True
    session_state.last_answer_correct = True
    session_state.difficulty          = advance_difficulty(session_state.difficulty)
    logger.info("Bonne réponse — score %d/%d", session_state.score, session_state.total_questions)


def handle_wrong(session_state, mode: str) -> None:
    """Applique les effets d'une mauvaise réponse."""
    session_state.total_questions    += 1
    session_state.answered            = True
    session_state.last_answer_correct = False
    if mode == "exercice":
        session_state.vies -= 1
    logger.info(
        "Mauvaise réponse — vies %s, score %d/%d",
        session_state.vies if mode == "exercice" else "N/A",
        session_state.score,
        session_state.total_questions,
    )


# ── Export PDF ─────────────────────────────────────────────────────────────────

def _strip_non_ascii(text: str) -> str:
    """Supprime les caractères non-ASCII (emojis inclus) pour la compatibilité FPDF."""
    return text.encode("ascii", "ignore").decode("ascii")


def generer_pdf(matiere: str, sujet: str, mode: str, messages: list) -> bytes:
    """Génère un PDF récapitulatif de la séance et retourne les bytes."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(15, 15, 15)

    # Titre
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(
        0, 14,
        _strip_non_ascii("Fiche de révision - Classe de 5ème"),
        align="C", new_x="LMARGIN", new_y="NEXT",
    )

    # Sous-titre
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(
        0, 8,
        _strip_non_ascii(f"Matière : {matiere}  |  Sujet : {sujet}  |  Mode : {mode}"),
        align="C", new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(8)

    # Contenu
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, _strip_non_ascii("Contenu de la séance :"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_font("Helvetica", "", 11)
    for msg in messages:
        if msg.get("role") == "assistant":
            pdf.multi_cell(0, 7, _strip_non_ascii(msg.get("content", "")))
            pdf.ln(3)

    return bytes(pdf.output())
