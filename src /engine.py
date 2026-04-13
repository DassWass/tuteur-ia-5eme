import streamlit as st
import google.generativeai as genai
import json
import re
import random
from PIL import Image

from .config import _DEFAULTS, MODEL_NAME, GENERATION_CONFIG, DIFFICULTY_ORDER, DIFFICULTY_LABELS
from .prompts import SYSTEM_COURS, SYSTEM_EXERCICE

MODEL_NAME        = "gemini-2.5-flash-preview-05-20"

GENERATION_CONFIG = genai.GenerationConfig(
    temperature=0.3,
    response_mime_type="application/json"
)


def reset_seance():
    for k, v in _DEFAULTS.items():
        st.session_state[k] = v

def get_ui_type(matiere: str, mode: str) -> str:
    return "cours" if mode == "cours" else "exercice"

def advance_difficulty(current: str) -> str:
    idx = DIFFICULTY_ORDER.index(current)
    return DIFFICULTY_ORDER[min(idx + 1, 2)]

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

def analyser_photo(image: Image.Image, matiere: str, ui_type: str) -> str:
    base = SYSTEM_EXERCICE if ui_type == "exercice" else SYSTEM_COURS
    model = make_model(base)
    prompt = "Voici une photo d'examen blanc. Analyse les types et le niveau des exercices. Génère 2 ou 3 exercices similaires."
    return model.generate_content([image, prompt]).text
