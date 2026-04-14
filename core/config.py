# ==========================================
# core/config.py — Constantes & Configuration
# ==========================================

# ── Modèle IA ──────────────────────────────────────────────────────────────────
MODEL_NAME = "gemini-2.5-flash-lite"

# ── Matières disponibles ───────────────────────────────────────────────────────
MATIERES: dict[str, str] = {
    "Mathématiques":   "🔢",
    "Français":        "📖",
    "Histoire-Géo":    "🌍",
    "SVT":             "🌱",
    "Physique-Chimie": "⚗️",
    "Anglais":         "🇬🇧",
    "Espagnol":        "🇪🇸",
    "Autre":           "📝",
}

# ── Difficulté ─────────────────────────────────────────────────────────────────
DIFFICULTY_ORDER: list[str] = ["facile", "moyen", "difficile"]
DIFFICULTY_LABELS: dict[str, str] = {
    "facile":    "🟢 Facile",
    "moyen":     "🟡 Moyen",
    "difficile": "🔴 Difficile",
}

# ── Valeurs par défaut du session state ───────────────────────────────────────
# IMPORTANT : les valeurs mutables (listes, dicts) sont copiées via
# utils.init_session_state() pour éviter le partage de références entre resets.
SESSION_DEFAULTS: dict = {
    "seance_lancee":         False,
    "matiere_temp":          "",
    "mode_temp":             "",
    "matiere":               "",
    "sujet":                 "",
    "mode":                  "",
    "ui_type":               "",
    "chat_session":          None,
    "messages":              [],        # liste — doit être deepcopied
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
    "paires_shuffled":       [],        # liste — doit être deepcopied
}
