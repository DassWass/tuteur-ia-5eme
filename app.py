import streamlit as st
import google.generativeai as genai
from PIL import Image
from fpdf import FPDF
import datetime

# ==========================================
# 1. CONFIGURATION & MODÈLE
# ==========================================
# On sécurise l'accès à la clé API
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Configure la clé GEMINI_API_KEY dans les Secrets Streamlit.")
    st.stop()

# On utilise la version LATEST pour avoir du quota et de la stabilité
model = genai.GenerativeModel('gemini-1.5-flash-latest')

st.set_page_config(page_title="Tuteur IA 5ème", layout="wide")

# Style CSS pour le bouton ROUGE "Lancer"
st.markdown("""
    <style>
    div.stButton > button:first-child {
        background-color: #ff4b4b;
        color: white;
        border-radius: 10px;
        border: none;
        font-weight: bold;
        padding: 0.6rem 1.2rem;
    }
    div.stButton > button:hover {
        background-color: #ff0000;
        color: white;
        border: none;
    }
    </style>
""", unsafe_allow_html=True)

# Initialisation des variables de session
if "seance_lancee" not in st.session_state:
    st.session_state.seance_lancee = False
if "messages" not in st.session_state:
    st.session_state.messages = []

# ==========================================
# 2. CONFIGURATION DE LA SÉANCE
# ==========================================
with st.container():
    col_btn, col_titre = st.columns([1, 3])
    with col_btn:
        lancer = st.button("🚀 LANCER LES EXERCICES")
    with col_titre:
        st.title("📚 Ton Tuteur Personnel de 5ème")
    
    col1, col2 = st.columns(2)
    with col1:
        matieres = ["Mathématiques", "Français", "Histoire-Géo", "SVT", "Physique-Chimie", "Anglais", "Espagnol", "Autre"]
        matiere_choisie = st.selectbox("1. Choisis ta matière :", matieres)
        matiere_finale = matiere_choisie
        if matiere_choisie == "Autre":
            matiere_finale = st.text_input("Précise la matière :")
            
    with col2:
        sujet = st.text_input("2. Sur quel sujet travailles-tu ?", placeholder="Ex: Les fractions...")

    st.markdown("---")

if lancer:
    if not sujet or (matiere_choisie == "Autre" and not matiere_finale):
        st.warning("⚠️ Précise le sujet et la matière avant de commencer.")
    else:
        st.session_state.seance_lancee = True
        st.session_state.messages = []
        
        # PROMPT SYSTÈME : LA LOI DU PAS-À-PAS
        contexte_systeme = f"""Tu es un tuteur de 5ème (13 ans). Matière : {matiere_finale}. Sujet : {sujet}.
MISSION :
1. Démarre TOUJOURS par 1 ou 2 blagues/devinettes.
2. NE DONNE JAMAIS l'exercice complet. Propose une micro-étape, puis attends la réponse de l'élève.
3. Travaille ligne par ligne. Sois encourageant.
4. Synthèse finale taguée [EXPORT] uniquement à la fin de l'exercice corrigé.
"""
        st.session_state.messages.append({"role": "system", "content": contexte_systeme})
        
        try:
            prompt_init = f"Commence la séance de {matiere_finale} sur {sujet} par tes blagues puis la première étape."
            res = model.generate_content(prompt_init)
            st.session_state.messages.append({"role": "assistant", "content": res.text})
        except Exception as e:
            st.error("Souci de connexion au démarrage.")

# ==========================================
# 3. CHAT INTERACTIF
# ==========================================
if st.session_state.seance_lancee:
    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"].replace("[EXPORT]", "").strip())

    if prompt := st.chat_input("Ta réponse..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                # Historique simple pour l'IA
                historique = ""
                for m in st.session_state.messages:
                    historique += f"{m['role']}: {m['content']}\n"
                
                response = model.generate_content(historique)
                st.markdown(response.text.replace("[EXPORT]", "").strip())
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except:
                st.error("Petit hoquet de l'IA, réessaie ton message.")

# ==========================================
# 4. SIDEBAR : PDF & PHOTOS
# ==========================================
with st.sidebar:
    st.header("🖼️ Aide & Export")
    photo = st.file_uploader("Une photo de ton cours ?", type=["png", "jpg", "jpeg"])
    
    st.markdown("---")
    if st.session_state.seance_lancee:
        if st.button("📝 Préparer mon PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(190, 10, f"Fiche : {matiere_finale}", ln=True, align='C')
            pdf.ln(10)

            export_txt = ""
            for m in st.session_state.messages:
                if m["role"] == "assistant" and "[EXPORT]" in m["content"]:
                    txt = m["content"].replace("[EXPORT]", "").strip()
                    pdf.set_font("Arial", "", 11)
                    pdf.multi_cell(190, 8, txt)
                    pdf.ln(5)
                    export_txt += txt

            if export_txt:
                pdf_
