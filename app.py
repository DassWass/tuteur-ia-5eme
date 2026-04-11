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

st.set_page_config(page_title="Tuteur IA 5ème - V2", layout="wide")

# Style CSS pour le bouton ROUGE en haut à gauche
st.markdown("""
    <style>
    div.stButton > button:first-child {
        background-color: #ff4b4b;
        color: white;
        border-radius: 10px;
        border: none;
        font-weight: bold;
        padding: 0.5rem 1rem;
    }
    div.stButton > button:hover {
        background-color: #ff0000;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONFIGURATION DE LA SÉANCE (BLOQUANTE)
# ==========================================
if "seance_lancee" not in st.session_state:
    st.session_state.seance_lancee = False

# Zone de configuration en haut
with st.container():
    col_btn, col_vide = st.columns([1, 4])
    with col_btn:
        lancer = st.button("🚀 LANCER LES EXERCICES")

    st.title("📚 Ton Tuteur Personnel de 5ème")
    
    col1, col2 = st.columns(2)
    with col1:
        liste_matieres = ["Mathématiques", "Français", "Histoire-Géo", "SVT", "Physique-Chimie", "Anglais", "Espagnol", "Autre"]
        matiere_choisie = st.selectbox("1. Choisis ta matière :", liste_matieres)
        
        # Champ supplémentaire si "Autre"
        matiere_finale = matiere_choisie
        if matiere_choisie == "Autre":
            matiere_finale = st.text_input("Précise la matière :")
            
    with col2:
        sujet = st.text_input("2. Sur quel sujet veux-tu t'entraîner ?", placeholder="Ex: Les fractions, le passé composé...")

    st.markdown("---")

# Logique de lancement
if lancer:
    if not sujet or (matiere_choisie == "Autre" and not matiere_finale):
        st.warning("⚠️ Remplis la matière et le sujet avant de lancer !")
    else:
        st.session_state.seance_lancee = True
        st.session_state.messages = []
        
        # PROMPT SYSTÈME OPTIMISÉ V2
        contexte = f"""Tu es un tuteur scolaire pour un élève de 5ème (13 ans). 
Matière : {matiere_finale}. Sujet : {sujet}.

MISSIONS :
1. COMMENCE TOUJOURS par 1 ou 2 blagues, charades ou devinettes ludiques pour briser la glace.
2. Pose des questions progressives (Pédagogie Socratique).
3. Utilise le tutoiement, sois très encourageant.
4. Pour chaque exercice complet ou fiche, commence par [EXPORT].
5. INTERDIT : Vie perso, religion, sexe, politique. Réponds par la phrase de sécurité convenue.
"""
        st.session_state.messages.append({"role": "system", "content": contexte})
        
        # Premier message automatique avec blague
        try:
            premier_contact = model.generate_content(f"Fais 1 ou 2 blagues/devinettes pour un enfant de 13 ans, puis salue-le pour sa séance de {matiere_finale} sur {sujet}.")
            st.session_state.messages.append({"role": "assistant", "content": premier_contact.text})
        except:
            st.session_state.messages.append({"role": "assistant", "content": "Salut ! Prêt à bosser ? (Désolé, ma réserve de blagues est coincée, on commence ?)"})

# ==========================================
# 3. INTERFACE DE CHAT (SI LANCÉE)
# ==========================================
if st.session_state.seance_lancee:
    # Affichage des messages
    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"].replace("[EXPORT]", "").strip())

    # Zone de saisie
    if prompt := st.chat_input("Réponds ici..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Appel IA avec mémoire
        with st.chat_message("assistant"):
            try:
                # Reconstruction du contexte pour Gemini
                memoire = [msg["content"] for msg in st.session_state.messages]
                response = model.generate_content(memoire)
                texte_reponse = response.text
                st.markdown(texte_reponse.replace("[EXPORT]", "").strip())
                st.session_state.messages.append({"role": "assistant", "content": texte_reponse})
            except:
                st.error("Petit bug de connexion... Réessaie ?")

# ==========================================
# 4. EXPORT PDF (BARRE LATÉRALE)
# ==========================================
with st.sidebar:
    st.header("📸 Documents")
    fichier_photo = st.file_uploader("Ajoute une photo de ton cours :", type=["png", "jpg", "jpeg"])
    
    st.markdown("---")
    st.subheader("📥 Export")
    
    if st.session_state.seance_lancee:
        # Construction du contenu PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(190, 10, f"Fiche de Révision : {matiere_finale}", ln=True, align='C')
        pdf.set_font("Arial", "", 12)
        pdf.cell(190, 10, f"Sujet : {sujet} - Date : {datetime.date.today()}", ln=True, align='C')
        pdf.ln(10)

        export_content = ""
        for msg in st.session_state.messages:
            if msg["role"] == "assistant" and "[EXPORT]" in msg["content"]:
                text = msg["content"].replace("[EXPORT]", "").strip()
                pdf.multi_cell(190, 10, text)
                pdf.ln(5)
                export_content += text

        if export_content:
            if export_content:
            # On génère le PDF et on force la conversion en format 'bytes'
            pdf_output = bytes(pdf.output()) 
            
            st.download_button(
                label="📄 Télécharger ma fiche (PDF)",
                data=pdf_output,
                file_name=f"revision_{matiere_finale}.pdf",
                mime="application/pdf"
            )
            st.download_button(
                label="📄 Télécharger ma fiche (PDF)",
                data=pdf_output,
                file_name=f"revision_{matiere_finale}.pdf",
                mime="application/pdf"
            )
        else:
            st.info("L'IA n'a pas encore généré de fiche [EXPORT].")
    else:
        st.info("Lance une séance pour activer l'export.")
