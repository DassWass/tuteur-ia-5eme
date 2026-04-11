import streamlit as st
import google.generativeai as genai
from PIL import Image
from fpdf import FPDF
import datetime

# ==========================================
# 1. CONFIGURATION & MODÈLE
# ==========================================
# Vérification de la clé API
if "GEMINI_API_KEY" not in st.secrets:
    st.error("Clé API introuvable dans les Secrets Streamlit !")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
# On utilise la version validée ensemble
model = genai.GenerativeModel('gemini-2.5-flash')

st.set_page_config(page_title="Tuteur IA 5ème - V2.2", layout="wide")

# Style CSS pour le bouton ROUGE
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
            matiere_finale = st.text_input("Précise la matière :")
            
    with col2:
        sujet = st.text_input("2. Sur quel sujet veux-tu t'entraîner ?", placeholder="Ex: Les fractions...")

    st.markdown("---")

if lancer:
    if not sujet or (matiere_choisie == "Autre" and not matiere_finale):
        st.warning("⚠️ Renseigne la matière et le sujet !")
    else:
        st.session_state.seance_lancee = True
        st.session_state.messages = []
        
        # PROMPT SYSTÈME "PAS À PAS" (SCROLLING LOGIC)
        contexte_systeme = f"""Tu es un tuteur de 5ème. Matière : {matiere_finale}. Sujet : {sujet}.
CONSIGNES STRICTES :
1. Commence par 1 ou 2 blagues/devinettes.
2. NE DONNE JAMAIS un exercice complet. Donne une ligne d'énoncé, puis pose une question sur la PREMIÈRE étape.
3. Attends la réponse. Guide l'élève pas à pas.
4. Utilise le tutoiement.
5. Marque la synthèse finale avec [EXPORT] uniquement quand tout est fini."""
        
        st.session_state.messages.append({"role": "system", "content": contexte_systeme})
        
        try:
            # On envoie une instruction claire pour le démarrage
            response = model.generate_content(f"Agis en tant que tuteur de 5ème. Sujet: {sujet}. Commence par tes blagues puis introduis la première micro-étape.")
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"Erreur au démarrage : {e}")

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
                # On construit un prompt qui contient tout l'historique pour maintenir la logique pas à pas
                full_prompt = ""
                for m in st.session_state.messages:
                    role_label = "INSTRUCTION:" if m["role"] == "system" else "ELEVE:" if m["role"] == "user" else "TUTEUR:"
                    full_prompt += f"{role_label} {m['content']}\n"
                
                response = model.generate_content(full_prompt)
                st.markdown(response.text.replace("[EXPORT]", "").strip())
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                # DEBUG MODE : On affiche la vraie erreur
                st.error("Désolé, j'ai un souci technique.")
                st.expander("Détails techniques pour l'admin").write(e)

# ==========================================
# 4. BARRE LATÉRALE : PHOTOS & PDF
# ==========================================
with st.sidebar:
    st.header("🖼️ Documents")
    photo = st.file_uploader("Photo du cours :", type=["png", "jpg", "jpeg"])
    st.markdown("---")
    st.subheader("📥 Exportation PDF")
    
    if st.session_state.seance_lancee:
        if st.button("Générer le PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(190, 10, f"Fiche : {matiere_finale}", ln=True, align='C')
            pdf.ln(10)

            export_content = ""
            for msg in st.session_state.messages:
                if msg["role"] == "assistant" and "[EXPORT]" in msg["content"]:
                    texte = msg["content"].replace("[EXPORT]", "").strip()
                    pdf.set_font("Arial", "", 11)
                    pdf.multi_cell(190, 8, texte)
                    pdf.ln(5)
                    export_content += texte

            if export_content:
                pdf_bytes = bytes(pdf.output())
                st.download_button(label="📄 Télécharger PDF", data=pdf_bytes, file_name="fiche_revision.pdf", mime="application/pdf")
            else:
                st.warning("Aucun contenu finalisé [EXPORT] pour le moment.")
