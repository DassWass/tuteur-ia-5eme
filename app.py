import streamlit as st
import google.generativeai as genai
from PIL import Image # NOUVEAU : L'outil pour lire les photos

# 1. Configuration de la clé API
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

st.set_page_config(page_title="Tuteur 5ème", layout="wide")
st.title("📚 Ton Tuteur Personnel")

# 2. La Barre Latérale (Le Cockpit)
with st.sidebar:
    st.header("⚙️ Paramètres de la séance")
    matiere = st.selectbox("Choisis ta matière :", ["Mathématiques", "Français", "Histoire-Géo", "SVT"])
    chapitre = st.text_input("Sur quel chapitre travailles-tu ?")
    
    # NOUVEAU : Zone pour uploader une photo
    st.markdown("---")
    st.subheader("📸 Ajouter un document")
    st.info("Glisse la photo de ton cours ou de ton exercice ici.")
    fichier_photo = st.file_uploader("", type=["png", "jpg", "jpeg"])
    st.markdown("---")
    
    if st.button("Lancer la séance"):
        st.session_state.messages = []
        
        contexte = f"""Tu es un tuteur scolaire virtuel spécialement conçu pour accompagner un élève de 5ème du système éducatif français. La matière étudiée aujourd'hui est : {matiere}, et le chapitre est : {chapitre}.

RÈGLES DE COMPORTEMENT (STRICTES) :
1. Pédagogie Socratique : Ne donne JAMAIS la réponse exacte immédiatement. Pose des questions progressives.
2. Ton : Utilise le tutoiement ("tu"). Sois encourageant et positif.
3. Source : Basé UNIQUEMENT sur le programme officiel du Ministère de l'Éducation Nationale français (5ème).

INTERDITS (ABSOLUS) :
Aucune discussion sur la vie personnelle, la religion, la sexualité ou la politique. Réponds : "Je suis un assistant dédié à tes révisions scolaires." si ces sujets sont abordés.
"""
        st.session_state.messages.append({"role": "system", "content": contexte})
        st.session_state.messages.append({"role": "assistant", "content": f"Salut ! Prêt à travailler sur le chapitre '{chapitre}' en {matiere} ? Si tu as une photo de ton cours, ajoute-la dans le menu à gauche, puis dis-moi ce que tu veux faire ! 😉"})

# 3. La Fenêtre Principale (Le Chat)
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Configure ta séance dans le menu à gauche pour commencer !"}]

# Affichage de l'historique
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# 4. Quand l'élève envoie un message
if prompt := st.chat_input("Écris ton message ici..."):
    with st.chat_message("user"):
        st.markdown(prompt)
        
        # NOUVEAU : Si une photo est chargée, on l'affiche dans le chat
        image_a_envoyer = None
        if fichier_photo is not None:
            image_a_envoyer = Image.open(fichier_photo)
            st.image(image_a_envoyer, caption="Document joint", width=300)

    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # NOUVEAU : On prépare le paquet pour Gemini (Texte + Image si elle existe)
    contenu_pour_gemini = [prompt]
    if image_a_envoyer is not None:
        contenu_pour_gemini.append(image_a_envoyer)
    
    # On envoie le tout à l'IA
    response = model.generate_content(contenu_pour_gemini) 
    
    with st.chat_message("assistant"):
        st.markdown(response.text)
    st.session_state.messages.append({"role": "assistant", "content": response.text})
