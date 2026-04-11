import streamlit as st
import google.generativeai as genai
from PIL import Image
from fpdf import FPDF
import datetime
import json
import re

# ==========================================#
# 1. CONFIGURATION & SÉCURITÉ
# ==========================================#

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("⚠️ Clé API manquante dans les Secrets Streamlit.")
    st.stop()

# Utilisation de gemini-1.5-flash pour la rapidité et la stabilité
active_model_name = 'gemini-1.5-flash'
model = genai.GenerativeModel(active_model_name)

st.set_page_config(page_title="Tuteur IA 5ème", layout="wide")

# ==========================================#
# 2. STYLE CSS (Correction Visibilité & Bouton Rouge)
# ==========================================#

st.markdown("""
    <style>
    /* Force la couleur du texte pour éviter le blanc sur blanc */
    html, body, [data-testid="stAppViewContainer"], .stMarkdown {
        color: #1f2937 !important;
    }
    
    [data-testid="stAppViewContainer"] {
        background-color: #ffffff;
    }

    /* Bouton Lancer en ROUGE en haut de la sidebar */
    div.stButton > button[key="launch_btn"] {
        background-color: #ef4444 !important;
        color: white !important;
        font-weight: bold !important;
        border: none !important;
        width: 100% !important;
        padding: 10px !important;
        margin-bottom: 20px !important;
    }

    /* Zone d'exercice */
    .exercise-zone {
        background-color: #f0f7ff;
        border: 2px solid #3b82f6;
        border-radius: 15px;
        padding: 15px;
        color: #1e3a8a !important;
    }

    /* Boutons Vrai/Faux */
    div.stButton > button.btn-vrai {
        background-color: #22c55e !important;
        color: white !important;
    }
    div.stButton > button.btn-faux {
        background-color: #ef4444 !important;
        color: white !important;
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
if "session_started" not in st.session_state:
    st.session_state.session_started = False

# ==========================================#
# 3. BARRE LATÉRALE (Configuration)
# ==========================================#

with st.sidebar:
    st.title("⚙️ Menu")
    
    # LE BOUTON ROUGE TOUT EN HAUT
    launch = st.button("🚀 LANCER LES RÉVISIONS", key="launch_btn")
    
    matieres = ["Mathématiques", "Français", "Histoire-Géo", "SVT", "Physique-Chimie", "Anglais"]
    matiere_choisie = st.selectbox("1. Choisis ta matière :", matieres)
    sujet = st.text_input("2. Sur quel sujet ?", placeholder="Ex: Les fractions...")

    if launch:
        if not sujet:
            st.warning("Précise un sujet !")
        else:
            st.session_state.messages = []
            st.session_state.session_started = True
            
            # PROMPT SYSTÈME MIS À JOUR
            system_prompt = f"""Tu es un tuteur pour un élève de 5ème. 
Matière : {matiere_choisie}. Sujet : {sujet}.

RÈGLES :
1. COMMENCE TOUJOURS par 1 ou 2 blagues/charades/devinettes ludiques pour briser la glace AVANT de donner l'exercice.
2. PAS-À-PAS : Ne génère jamais tout d'un coup. Un exercice à la fois.
3. INTERACTION : Pour chaque question, utilise ce format JSON pour activer les boutons :
   [[EXERCISE_DATA]] {{ "type": "vrai_faux", "question": "Ta question ici ?" }} [[END_EXERCISE]]
4. TON : Tutoiement, encourageant, fun.
"""
            st.session_state.messages.append({"role": "system", "content": system_prompt})
            
            # Premier appel
            try:
                intro_prompt = "Fais tes blagues puis introduis le premier exercice."
                res = model.generate_content([system_prompt, intro_prompt])
                st.session_state.messages.append({"role": "assistant", "content": res.text})
                st.rerun()
            except Exception as e:
                st.error(f"Erreur API : {e}")

# ==========================================#
# 4. INTERFACE PRINCIPALE
# ==========================================#

st.title("📚 Tuteur IA Interactif")

col_chat, col_ex = st.columns([2, 1])

with col_chat:
    # Affichage des messages
    for msg in st.session_state.messages:
        if msg["role"] != "system":
            role = "user" if msg["role"] == "user" else "assistant"
            with st.chat_message(role):
                # Nettoyage du JSON pour l'affichage
                clean_txt = re.sub(r'\[\[EXERCISE_DATA\]\].*?\[\[END_EXERCISE\]\]', '', msg["content"], flags=re.DOTALL)
                st.markdown(clean_txt)

    # Entrée utilisateur
    user_input = st.chat_input("Ta réponse ici...", disabled=st.session_state.input_text_disabled)
    
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Appel IA avec l'historique
        history = [{"role": m["role"], "parts": [m["content"]]} for m in st.session_state.messages]
        # Note: On transforme le format pour l'API Gemini
        try:
            # On simule un envoi simple pour la démo
            full_context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
            res = model.generate_content(full_context)
            st.session_state.messages.append({"role": "assistant", "content": res.text})
            st.rerun()
        except:
            st.error("Erreur de connexion.")

with col_ex:
    st.markdown('<div class="exercise-zone">', unsafe_allow_html=True)
    st.subheader("🎯 Exercice")
    
    # Détection de l'exercice dans le dernier message
    exercise_found = False
    if st.session_state.messages:
        last_msg = st.session_state.messages[-1]["content"]
        match = re.search(r'\[\[EXERCISE_DATA\]\](.*?)\[\[END_EXERCISE\]\]', last_msg, flags=re.DOTALL)
        
        if match:
            exercise_found = True
            try:
                data = json.loads(match.group(1).strip())
                st.write(data["question"])
                
                c1, c2 = st.columns(2)
                if c1.button("VRAI 👍", use_container_width=True):
                    st.session_state.messages.append({"role": "user", "content": "C'est VRAI"})
                    st.rerun()
                if c2.button("FAUX 👎", use_container_width=True):
                    st.session_state.messages.append({"role": "user", "content": "C'est FAUX"})
                    st.rerun()
                
                st.session_state.input_text_disabled = True
            except:
                st.error("Erreur de format d'exercice.")
        else:
            st.session_state.input_text_disabled = False
            st.write("L'IA prépare la suite...")
            
    st.markdown('</div>', unsafe_allow_html=True)
