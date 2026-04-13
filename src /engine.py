# ==========================================
# engine.py — Moteur IA & Logique Métier
# ==========================================

import json
import re
import random

import google.generativeai as genai
from fpdf import FPDF
from PIL import Image

from config import MODEL_NAME, DIFFICULTY_ORDER, DIFFICULTY_LABELS
from prompts import (
    build_system_prompt,
    build_first_prompt,
    build_next_prompt,
    build_restart_prompt,
    build_eval_prompt,
    SYSTEM_COURS,
    SYSTEM_EXERCICE,
)

# ── Configuration Gemini ───────────────────────────────────────────────────────
# Température basse (0.3) + forçage JSON natif pour des réponses stables
GENERATION_CONFIG = genai.GenerationConfig(
    temperature=0.3,
    response_mime_type="application/json",
)


# ── Helpers internes ───────────────────────────────────────────────────────────

def _make_model(system_prompt: str):
    """Instancie un modèle Gemini avec le prompt système donné."""
    return genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=system_prompt,
        generation_config=GENERATION_CONFIG,
    )


def parse_json_response(text: str) -> dict | None:
    """Tente de parser une réponse texte en dict JSON."""
    try:
        return json.loads(text)
    except Exception:
        try:
            clean = re.sub(r"```json|```", "", text).strip()
            return json.loads(clean)
        except Exception:
            return None


# ── Session de chat ────────────────────────────────────────────────────────────

def creer_chat(matiere: str, sujet: str, ui_type: str):
    """Crée et retourne une session de chat Gemini configurée."""
    system = build_system_prompt(ui_type, matiere, sujet)
    return _make_model(system).start_chat(history=[])


# ── Génération de questions ────────────────────────────────────────────────────

def generate_next(
    chat_session,
    matiere: str,
    sujet: str,
    difficulty: str,
    is_first: bool,
) -> tuple[dict | None, str]:
    """
    Génère la prochaine question via Gemini.
    Retourne (data_dict, raw_text). data_dict est None en cas d'échec.
    """
    diff_label = DIFFICULTY_LABELS[difficulty]
    prompt = (
        build_first_prompt(matiere, sujet, diff_label)
        if is_first
        else build_next_prompt(sujet, diff_label)
    )
    try:
        response = chat_session.send_message(prompt)
        return parse_json_response(response.text), response.text
    except Exception as e:
        return None, f"❌ Erreur de génération : {e}"


def generate_restart(
    chat_session,
    sujet: str,
    difficulty: str = "facile",
) -> tuple[dict | None, str]:
    """Génère une nouvelle question après un game over."""
    diff_label = DIFFICULTY_LABELS[difficulty]
    prompt = build_restart_prompt(sujet, diff_label)
    try:
        response = chat_session.send_message(prompt)
        return parse_json_response(response.text), response.text
    except Exception as e:
        return None, f"❌ Erreur au redémarrage : {e}"


# ── Évaluation de réponse libre ────────────────────────────────────────────────

def evaluate_answer(
    chat_session,
    fmt: str,
    expected,
    student_answer: str,
) -> dict:
    """
    Envoie la réponse de l'élève à Gemini pour évaluation.
    Retourne un dict {"correct": bool, "feedback": str}.
    """
    prompt = build_eval_prompt(fmt, expected, student_answer)
    try:
        response = chat_session.send_message(prompt)
        data = parse_json_response(response.text)
        return data if data else {
            "correct": False,
            "feedback": "Je n'ai pas pu évaluer ta réponse, réessaie ! 🤔",
        }
    except Exception as e:
        return {"correct": False, "feedback": f"Petit bug technique, réessaie ! ({e})"}


# ── Analyse de photo d'examen ──────────────────────────────────────────────────

def analyser_photo(image: Image.Image, matiere: str, ui_type: str) -> str:
    """Analyse une photo d'examen blanc et retourne des exercices similaires."""
    base = SYSTEM_EXERCICE if ui_type == "exercice" else SYSTEM_COURS
    model = _make_model(base)
    prompt = (
        "Voici une photo d'examen blanc. "
        "Analyse les types et le niveau des exercices. "
        "Génère 2 ou 3 exercices similaires."
    )
    return model.generate_content([image, prompt]).text


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


def handle_wrong(session_state, mode: str) -> None:
    """Applique les effets d'une mauvaise réponse."""
    session_state.total_questions    += 1
    session_state.answered            = True
    session_state.last_answer_correct = False
    if mode == "exercice":
        session_state.vies -= 1


# ── Export PDF ─────────────────────────────────────────────────────────────────

def _remove_emojis(text: str) -> str:
    return text.encode("ascii", "ignore").decode("ascii")


def generer_pdf(matiere: str, sujet: str, mode: str, messages: list) -> bytes:
    """Génère un PDF récapitulatif de la séance et retourne les bytes."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(15, 15, 15)

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(
        0, 14,
        _remove_emojis("Fiche de révision - Classe de 5ème"),
        align="C", new_x="LMARGIN", new_y="NEXT",
    )

    pdf.set_font("Helvetica", "", 12)
    pdf.cell(
        0, 8,
        _remove_emojis(f"Matière : {matiere}  |  Sujet : {sujet}  |  Mode : {mode}"),
        align="C", new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(8)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, _remove_emojis("Contenu de la séance :"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_font("Helvetica", "", 11)
    for msg in messages:
        if msg["role"] == "assistant":
            pdf.multi_cell(0, 7, _remove_emojis(msg["content"]))
            pdf.ln(3)

    return bytes(pdf.output())
