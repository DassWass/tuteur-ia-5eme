import streamlit as st
import google.generativeai as genai
from PIL import Image
from fpdf import FPDF
import datetime

# ==========================================
# 1. CONFIGURATION & SÉCURITÉ DU MODÈLE
# ==========================================
# Vérification de la clé API dans les Secrets
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("⚠️ Clé API manquante dans les Secrets Streamlit.")
    st.stop()

# Système de sélection automatique du modèle pour éviter l'erreur 404
@st.cache_resource
def load_model():
    # Liste des noms à tester par ordre de priorité
    test_names = ['gemini-1.5-flash-latest', 'gemini-1.5-flash', 'gemini-2.5-flash']
    for name in test_names:
        try:
            m = genai.GenerativeModel(name)
            # Test de connexion ultra-léger
            m.generate_content("ping") 
            return m, name
        except:
            continue
    return genai.GenerativeModel('gemini-2.5-flash'), 'gemini-2.5-flash'

model, active_model_name = load_model()

# Configuration de la page
st.set_page_config(page_title="Tuteur IA 5ème - V4.0", layout="wide")

# Style CSS pour le bouton ROUGE
st.markdown(f"""
    <style>
    div.stButton > button:first-child {{
        background-color: #ff4b4b;
        color: white;
        border-radius: 10px;
        border: none;
        font-weight: bold;
        padding: 0.6rem 1.2rem;
    }}
    div.stButton > button:hover {{
        background-color: #ff0000;
        color: white;
        border: none;
    }}
    </style>
""", unsafe_allow_html=True)

# Initialisation de la session
if "seance_lancee" not in st.session_state:
    st.session_state.seance_lancee = False
if "messages" not in st.session_state:
    st.session_state.messages = []

# ==========================================
# 2. INTERFACE DE RÉGLAGES
# ==========================================
with st.container():
    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        lancer = st.button("🚀 LANCER LES EXERCICES")
    with col_info:
        st.title("📚 Ton Tuteur Personnel de 5ème")
        st.caption(f"Modèle actif : {active_model_name}")
    
    col1, col2 = st.columns(2)
    with col1:
        matieres = ["Mathématiques", "Français", "Histoire-Géo", "SVT", "Physique-Chimie", "Anglais", "Espagnol", "Autre"]
        matiere_choisie = st.selectbox("1. Choisis ta matière :", matieres)
        matiere_finale = matiere_choisie
        if matiere_choisie == "Autre":
            matiere_finale = st.text_input("Précise la matière :")
            
    with col2:
        sujet = st.text_input("2. Sur quel sujet travailles-tu ?", placeholder="Ex: Les pourcentages...")

    st.markdown("---")

# Logique de lancement de séance
if lancer:
    if not sujet or (matiere_choisie == "Autre" and not matiere_finale):
        st.warning("⚠️ Renseigne le sujet et la matière avant de commencer.")
    else:
        st.session_state.seance_lancee = True
        st.session_state.messages = []
        
        # PROMPT SYSTÈME : PÉDAGOGIE PAS-À-PAS
        contexte_systeme = f"""Tu es un tuteur de 5ème. Matière : {matiere_finale}. Sujet : {sujet}.
CONSIGNES STRICTES :
1. Démarre TOUJOURS par 1 ou 2 blagues/devinettes pour 13 ans.
2. NE DONNE JAMAIS l'exercice complet d'un coup.
3. Travaille LIGNE PAR LIGNE : donne une seule micro-étape, puis attends la réponse de l'élève.
4. Si l'élève bloque, donne un indice progressif.
5. Utilise le tutoiement.
6. Ne marque la synthèse avec [EXPORT] qu'à la toute fin, une fois l'exercice fini et corrigé.
"""
        st.session_state.messages.append({"role": "system", "content": contexte_systeme})
        
        try:
            prompt_init = f"Fais tes blagues puis introduis la première étape de {matiere_finale} sur {sujet}."
            res = model.generate_content(prompt_init)
            st.session_state.messages.append({"role": "assistant", "content": res.text})
        except Exception as e:
            st.error(f"Erreur technique : {e}")

# ==========================================
# 3. CHAT INTERACTIF
# ==========================================
if st.session_state.seance_lancee:
    # Affichage de l'historique
    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"].replace("[EXPORT]", "").strip())

    # Entrée utilisateur
    if prompt := st.chat_input("Ta réponse au tuteur..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Réponse de l'IA
        with st.chat_message("assistant"):
            try:
                # Construction d'un historique textuel propre
                full_history = ""
                for m in st.session_state.messages:
                    role_tag = "TUTEUR" if m["role"] == "assistant" else "ELEVE" if m["role"] == "user" else "SYSTEM"
                    full_history += f"{role_tag}: {m['content']}\n"
                
                response = model.generate_content(full_history)
                texte_ia = response.text
                
                st.markdown(texte_ia.replace("[EXPORT]", "").strip())
                st.session_state.messages.append({"role": "assistant", "content": texte_ia})
            except Exception as e:
                st.error(f"Erreur technique : {e}")

# ==========================================
# 4. BARRE LATÉRALE : PHOTOS & PDF
# ==========================================
with st.sidebar:
    st.header("🖼️ Aide & Documents")
    photo = st.file_uploader("Une photo de ton cours ?", type=["png", "jpg", "jpeg"])
    
    st.markdown("---")
    st.subheader("📥 Ton PDF de révision")
    
    if st.session_state.seance_lancee:
        # Création du PDF uniquement sur demande
        if st.button("📝 Préparer mon fichier PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(190, 10, f"Fiche de Révision : {matiere_finale}", ln=True, align='C')
            pdf.set_font("Arial", "", 12)
            pdf.cell(190, 10, f"Sujet : {sujet}", ln=True, align='C')
            pdf.ln(10)

            export_content = ""
            for m in st.session_state.messages:
                if m["role"] == "assistant" and "[EXPORT]" in m["content"]:
                    txt = m["content"].replace("[EXPORT]", "").strip()
                    pdf.set_font("Arial", "B", 12)
                    pdf.cell(190, 10, "Résumé de l'exercice :", ln=True)
                    pdf.set_font("Arial", "", 11)
                    pdf.multi_cell(190, 8, txt)
                    pdf.ln(5)
                    export_content += txt

            if export_content:
                pdf_bytes = bytes(pdf.output())
                st.download_button(
                    label="📥 Télécharger ma fiche (PDF)",
                    data=pdf_bytes,
                    file_name=f"fiche_{matiere_finale}.pdf",
                    mime="application/pdf"
                )
            else:
                st.info("L'IA n'a pas encore créé de résumé [EXPORT]. Finis un exercice avec elle !")
    else:
        st.info("Commence une séance pour activer les options.")
