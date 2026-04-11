import streamlit as st
import google.generativeai as genai
from PIL import Image
from fpdf import FPDF
import datetime

# ==========================================
# 1. CONFIGURATION & MODÈLE (GEMINI 2.5)
# ==========================================
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Clé API manquante dans les Secrets Streamlit.")
    st.stop()

# Utilisation du modèle 2.5 Flash avec ta nouvelle clé
model = genai.GenerativeModel('gemini-2.5-flash')

st.set_page_config(page_title="Tuteur IA 5ème - V3.0", layout="wide")

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
        matiere_choisie = st.selectbox("Choisis ta matière :", matieres)
        matiere_finale = matiere_choisie
        if matiere_choisie == "Autre":
            matiere_finale = st.text_input("Précise la matière :")
            
    with col2:
        sujet = st.text_input("Sur quel sujet travailles-tu ?", placeholder="Ex: Les fractions...")

    st.markdown("---")

if lancer:
    if not sujet or (matiere_choisie == "Autre" and not matiere_finale):
        st.warning("⚠️ Précise le sujet et la matière avant de commencer.")
    else:
        st.session_state.seance_lancee = True
        st.session_state.messages = []
        
        # PROMPT SYSTÈME : LOGIQUE PAS-À-PAS ET BLAGUES
        contexte_systeme = f"""Tu es un tuteur de 5ème. Matière : {matiere_finale}. Sujet : {sujet}.
CONSIGNES :
1. Démarre TOUJOURS par 1 ou 2 blagues/devinettes.
2. NE DONNE JAMAIS l'exercice complet d'un coup.
3. Propose une seule micro-étape ou question à la fois (travail ligne par ligne).
4. Utilise le tutoiement.
5. Marque la synthèse finale avec [EXPORT] quand l'exercice est terminé.
"""
        st.session_state.messages.append({"role": "system", "content": contexte_systeme})
        
        try:
            instruction = f"Commence par tes blagues puis introduis la première étape de {matiere_finale} sur {sujet}."
            res = model.generate_content(instruction)
            st.session_state.messages.append({"role": "assistant", "content": res.text})
        except Exception as e:
            # Affichage de l'erreur réelle pour comprendre le blocage
            st.error(f"Erreur technique : {e}")

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
                # On envoie l'historique complet pour garder le fil "pas-à-pas"
                historique = ""
                for m in st.session_state.messages:
                    historique += f"{m['role']}: {m['content']}\n"
                
                response = model.generate_content(historique)
                st.markdown(response.text.replace("[EXPORT]", "").strip())
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"Erreur technique : {e}")

# ==========================================
# 4. SIDEBAR : PDF & PHOTOS
# ==========================================
with st.sidebar:
    st.header("🖼️ Documents")
    photo = st.file_uploader("Photo du cours :", type=["png", "jpg", "jpeg"])
    st.markdown("---")
    
    if st.session_state.seance_lancee:
        if st.button("📝 Générer mon PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(190, 10, f"Révisions : {matiere_finale}", ln=True, align='C')
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
                pdf_bytes = bytes(pdf.output())
                st.download_button("📥 Télécharger le PDF", pdf_bytes, "fiche.pdf", "application/pdf")
            else:
                st.info("Finis un exercice pour voir le bouton de téléchargement.")
