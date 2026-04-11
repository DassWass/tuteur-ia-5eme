import streamlit as st
import google.generativeai as genai
from PIL import Image
from fpdf import FPDF
import datetime
import json
import re

# ==========================================#
# 1. CONFIGURATION & SÉCURITÉ DU MODÈLE
# ==========================================#

# Vérification de la clé API dans les Secrets
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("⚠️ Clé API manquante dans les Secrets Streamlit.")
    st.stop()

# Utilisation de gemini-1.5-flash pour la rapidité et la stabilité
active_model_name = 'gemini-1.5-flash'
model = genai.GenerativeModel(active_model_name)

# Configuration de la page EN MODE WIDE pour les colonnes
st.set_page_config(page_title="Tuteur IA 5ème", layout="wide")

# ==========================================#
# 2. STYLE CSS AVANCÉ (CORRECTION VISIBILITÉ)
# ==========================================#

st.markdown("""
    <style>
    /* 1. Force le fond de l'application en blanc */
    [data-testid="stAppViewContainer"] {
        background-color: #ffffff;
    }
    
    /* 2. Force le fond de la sidebar en gris très clair pour le contraste */
    [data-testid="stSidebar"] {
        background-color: #f3f4f6;
    }

    /* 3. Force la couleur du texte en noir partout (app et sidebar) */
    [data-testid="stAppViewContainer"], [data-testid="stSidebar"], .stMarkdown, p, div, label {
        color: #1f2937 !important;
    }
    
    /* 4. Force la couleur des étiquettes (labels) de la sidebar */
    .stSidebar label {
        color: #374151 !important;
        font-weight: 600;
    }

    /* 5. Force la couleur du texte dans les champs d'entrée */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
        color: #1f2937 !important;
        background-color: white !important;
    }

    /* Zone d'exercice */
    .exercise-zone {
        background-color: #f0f7ff;
        border: 2px solid #3b82f6;
        border-radius: 15px;
        padding: 15px;
        color: #1e3a8a !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .exercise-zone .exercise-title {
        color: #1e40af;
        font-size: 1.3rem;
        font-weight: bold;
        margin-bottom: 10px;
    }

    /* Boutons Vrai/Faux */
    div.stButton > button.btn-vrai {
        background-color: #22c55e !important;
        color: white !important;
        width: 100% !important;
    }
    div.stButton > button.btn-faux {
        background-color: #ef4444 !important;
        color: white !important;
        width: 100% !important;
    }

    /* Bouton Lancer en bleu */
    div.stButton > button[key="launch_btn"] {
        background-color: #3b82f6 !important;
        color: white !important;
        font-weight: bold !important;
        border-radius: 10px !important;
        width: 100% !important;
    }
    </style>
""", unsafe_allow_html=True)

# Initialisation de la session
if "messages" not in st.session_state:
    st.session_state.messages = []
if "active_exercise_data" not in st.session_state:
    st.session_state.active_exercise_data = None
if "input_text_disabled" not in st.session_state:
    st.session_state.input_text_disabled = False

# ==========================================#
# 3. INTERFACE PRINCIPALE (WIDE LAYOUT)
# ==========================================#

st.title("📚 Tuteur IA 5ème - Édition Ludique")

# Création des colonnes : [3, 1]
col_chat, col_dynamique = st.columns([3, 1])

# ==========================================#
# GAUCHE : COLONNE CONVERSATION
# ==========================================#

with col_chat:
    # Affichage de l'historique
    for msg in st.session_state.messages:
        if msg["role"] != "system":
            icon = "🧑" if msg["role"] == "user" else "🤖"
            with st.chat_message(msg["role"], avatar=icon):
                clean_content = re.sub(r'\[\[EXERCISE_DATA\]\].*?\[\[END_EXERCISE\]\]', '', msg["content"], flags=re.DOTALL)
                st.markdown(clean_content)

    # Zone de saisie utilisateur
    input_text = st.chat_input("Réponds au tuteur ici...", disabled=st.session_state.input_text_disabled)
    
    # La logique de chat est gérée dans la section 5

# ==========================================#
# DROITE : COLONNE DYNAMIQUE (Zone d'Exercice)
# ==========================================#

with col_dynamique:
    st.markdown('<div class="exercise-zone"><div class="exercise-title">🎯 Zone d\'Exercice</div>', unsafe_allow_html=True)
    
    exercise_found = False
    
    # On vérifie si un exercice est présent dans le dernier message de l'assistant
    if st.session_state.messages:
        for msg in reversed(st.session_state.messages):
            if msg["role"] == "assistant":
                match = re.search(r'\[\[EXERCISE_DATA\]\](.*?)\[\[END_EXERCISE\]\]', msg["content"], flags=re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(1).strip())
                        exercise_found = True
                        st.markdown(f'<strong>Question :</strong> {data["question"]}', unsafe_allow_html=True)
                        
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("VRAI 👍", key="true_btn", use_container_width=True):
                                st.session_state.messages.append({"role": "user", "content": "Je pense que c'est VRAI"})
                                st.rerun()
                        with c2:
                            if st.button("FAUX 👎", key="false_btn", use_container_width=True):
                                st.session_state.messages.append({"role": "user", "content": "Je pense que c'est FAUX"})
                                st.rerun()
                        
                        # Désactiver l'entrée texte quand l'exercice est actif
                        st.session_state.input_text_disabled = True
                        break
                    except:
                        pass
                else:
                    break
    
    if not exercise_found:
        st.write("L'IA prépare la suite...")
        st.session_state.input_text_disabled = False

    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================#
# 4. BARRE LATÉRALE (Configuration)
# ==========================================#

with st.sidebar:
    st.header("⚙️ Configuration")
    
    matieres = ["Mathématiques", "Français", "Histoire-Géo", "SVT", "Physique-Chimie", "Anglais"]
    matiere_choisie = st.selectbox("1. Choisis ta matière :", matieres)
    sujet = st.text_input("2. Sur quel sujet travailles-tu ?", placeholder="Ex: Les fractions...")

    st.markdown("---")
    
    # LE BOUTON DE LANCEMENT QUI MANQUAIT !
    if st.button("🚀 LANCER LES RÉVISIONS", key="launch_btn"):
        if not sujet:
            st.warning("⚠️ Renseigne le sujet avant de commencer.")
        else:
            # Initialisation
            st.session_state.messages = []
            
            # PROMPT SYSTÈME
            contexte_systeme = f"""Tu es un tuteur scolaire pour un élève de 5ème. 
Matière : {matiere_choisie}. Sujet : {sujet}.

RÈGLES :
1. Démarre par 1 blague courte.
2. PAS-À-PAS : Guide l'élève ligne par ligne.
3. Pour chaque question, utilise ce format JSON pour activer les boutons :
   [[EXERCISE_DATA]] {{ "type": "vrai_faux", "question": "Ta question ?" }} [[END_EXERCISE]]
4. Sois très encourageant. Tutoiement.
"""
            st.session_state.messages.append({"role": "system", "content": contexte_systeme})
            
            # Premier appel pour les blagues
            try:
                res = model.generate_content("Fais ta blague puis introduis le premier exercice.")
                st.session_state.messages.append({"role": "assistant", "content": res.text})
                st.rerun()
            except:
                st.error("Erreur technique.")

# ==========================================#
# 5. LOGIQUE DE RÉPONSE IA
# ==========================================#

if input_text:
    # 1. Ajouter le message de l'utilisateur
    st.session_state.messages.append({"role": "user", "content": input_text})
    
    # 2. Vérifier si une session est déjà lancée (si un message système est présent)
    has_system_prompt = any(m["role"] == "system" for m in st.session_state.messages)
    
    if not has_system_prompt:
        # Si non lancée, on l'invite à cliquer sur le bouton
        with st.chat_message("assistant", avatar="🤖"):
            st.warning("⚠️ S'il te plaît, configure la matière et le sujet dans la barre latérale, puis clique sur '🚀 LANCER LES RÉVISIONS' pour commencer.")
    else:
        # Si lancée, on fait l'appel IA
        with st.chat_message("assistant", avatar="🤖"):
            try:
                # Préparation de l'historique pour Gemini
                full_prompt = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
                
                # Génération
                res = model.generate_content(full_prompt)
                texte_ia = res.text
                
                st.session_state.messages.append({"role": "assistant", "content": texte_ia})
                st.rerun()
                
            except:
                st.error("Erreur de l'IA (Quota, etc.).")
