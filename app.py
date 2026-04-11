import streamlit as st
import google.generativeai as genai
from PIL import Image
from fpdf import FPDF
import datetime

# ==========================================
# 1. CONFIGURATION & MODÈLE
# ==========================================
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

st.set_page_config(page_title="Tuteur IA 5ème - V2.1", layout="wide")

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
        liste_matieres = ["Mathématiques", "Français", "Histoire-Géo", "SVT", "Physique-Chimie", "Anglais", "Espagnol", "Autre"]
        matiere_choisie = st.selectbox("1. Choisis ta matière :", liste_matieres)
        matiere_finale = matiere_choisie
        if matiere_choisie == "Autre":
            matiere_finale = st.text_input("Précise la matière :", placeholder="Ex: Musique...")
            
    with col2:
        sujet = st.text_input("2. Sur quel sujet veux-tu t'entraîner ?", placeholder="Ex: Les fractions...")

    st.markdown("---")

if lancer:
    if not sujet or (matiere_choisie == "Autre" and not matiere_finale):
        st.warning("⚠️ Renseigne la matière et le sujet !")
    else:
        st.session_state.seance_lancee = True
        st.session_state.messages = []
        # PROMPT SYSTÈME "STEP-BY-STEP"
        contexte_systeme = f"""Tu es un tuteur scolaire de 5ème expert en pédagogie active. 
Matière : {matiere_finale}. Sujet : {sujet}.

RÈGLES D'INTERACTION STRICTES :
1. LE BRISE-GLACE : Commence TOUJOURS par 1 ou 2 blagues/devinettes.
2. PAS À PAS : Ne propose JAMAIS un exercice complet d'un coup. Donne l'énoncé, puis pose une question sur la PREMIÈRE étape uniquement.
3. LIGNE PAR LIGNE : Attends la réponse de l'élève. Si c'est juste, félicite-le et donne la micro-étape suivante. Si c'est faux, donne un indice sans donner la réponse.
4. UN SEUL DÉFI : Tu ne dois jamais écrire plus de 3 phrases à la fois.
5. EXPORT : N'utilise la balise [EXPORT] QUE lorsque l'exercice est ENTIÈREMENT terminé et corrigé, pour en faire une fiche de synthèse propre. Ne la mets pas pendant la discussion par étapes.
"""
        
        try:
            prompt_initial = f"Fais 1 ou 2 blagues courtes, puis salue l'élève pour sa leçon de {matiere_finale} sur {sujet}."
            reponse_initiale = model.generate_content(prompt_initial)
            st.session_state.messages.append({"role": "assistant", "content": reponse_initiale.text})
        except:
            st.session_state.messages.append({"role": "assistant", "content": "Salut ! Prêt à bosser ?"})

# ==========================================
# 3. INTERFACE DE DISCUSSION
# ==========================================
if st.session_state.seance_lancee:
    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"].replace("[EXPORT]", "").strip())

    if prompt := st.chat_input("Réponds ici..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                historique_ia = [msg["content"] for msg in st.session_state.messages]
                response = model.generate_content(historique_ia)
                st.markdown(response.text.replace("[EXPORT]", "").strip())
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except:
                st.error("Problème de connexion. Réessaie ?")

# ==========================================
# 4. BARRE LATÉRALE : PHOTOS & PDF
# ==========================================
with st.sidebar:
    st.header("🖼️ Documents")
    photo = st.file_uploader("Photo du cours :", type=["png", "jpg", "jpeg"])
    st.markdown("---")
    st.subheader("📥 Exportation PDF")
    
    if st.session_state.seance_lancee:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(190, 10, f"Fiche : {matiere_finale}", ln=True, align='C')
        pdf.ln(10)

        export_content = ""
        for msg in st.session_state.messages:
            if msg["role"] == "assistant" and "[EXPORT]" in msg["content"]:
                texte_nettoye = msg["content"].replace("[EXPORT]", "").strip()
                pdf.set_font("Arial", "", 11)
                pdf.multi_cell(190, 8, texte_nettoye)
                pdf.ln(5)
                export_content += texte_nettoye

        if export_content:
            pdf_bytes = bytes(pdf.output())
            st.download_button(label="📄 Télécharger PDF", data=pdf_bytes, file_name=f"fiche.pdf", mime="application/pdf")
        else:
            st.info("Aucun contenu [EXPORT] trouvé.")
