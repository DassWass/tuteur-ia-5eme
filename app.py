import streamlit as st
import google.generativeai as genai
from PIL import Image

# ==========================================
# 1. CONFIGURATION INITIALE
# ==========================================
# Connexion sécurisée à l'API via le coffre-fort de Streamlit
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
# Utilisation de la version la plus récente et stable du modèle
model = genai.GenerativeModel('gemini-2.5-flash')

st.set_page_config(page_title="Tuteur 5ème", layout="wide")
st.title("📚 Ton Tuteur Personnel")

# ==========================================
# 2. LA BARRE LATÉRALE (Paramètres & Photo)
# ==========================================
with st.sidebar:
    st.header("⚙️ Paramètres de la séance")
    matiere = st.selectbox("Choisis ta matière :", ["Mathématiques", "Français", "Histoire-Géo", "SVT", "Physique-Chimie", "Anglais"])
    chapitre = st.text_input("Sur quel chapitre travailles-tu ?")
    
    st.markdown("---")
    st.subheader("📸 Ajouter un document")
    st.info("Glisse la photo de ton cours ou de ton exercice ici.")
    fichier_photo = st.file_uploader("", type=["png", "jpg", "jpeg"])
    st.markdown("---")
    
    if st.button("Lancer la séance"):
        # Réinitialisation de la discussion à chaque nouvelle séance
        st.session_state.messages = []
        
        # Le cerveau de l'IA (Prompt Système)
        contexte = f"""Tu es un tuteur scolaire virtuel spécialement conçu pour accompagner un élève de 5ème du système éducatif français. La matière étudiée aujourd'hui est : {matiere}, et le chapitre est : {chapitre}.

RÈGLES DE COMPORTEMENT (STRICTES) :
1. Pédagogie Socratique : Ne donne JAMAIS la réponse exacte immédiatement. Pose des questions progressives.
2. Ton : Utilise le tutoiement ("tu"). Sois encourageant et positif.
3. Source : Basé UNIQUEMENT sur le programme officiel du Ministère de l'Éducation Nationale français (5ème).
4. MARQUAGE DES DOCUMENTS : Lorsque tu proposes un exercice complet, un problème ou que tu rédiges une fiche de synthèse, tu dois OBLIGATOIREMENT commencer ton message par la balise exacte : [EXPORT]. Ne mets cette balise que pour les contenus utiles à réviser, pas pour la conversation classique.

INTERDITS (ABSOLUS) :
Aucune discussion sur la vie personnelle, la religion, la sexualité ou la politique. Réponds : "Je suis un assistant dédié à tes révisions scolaires." si ces sujets sont abordés.
"""
        st.session_state.messages.append({"role": "system", "content": contexte})
        st.session_state.messages.append({"role": "assistant", "content": f"Salut ! Prêt à travailler sur le chapitre '{chapitre}' en {matiere} ? Si tu as une photo de ton cours, ajoute-la dans le menu à gauche, puis dis-moi ce que tu veux faire ! 😉"})

# ==========================================
# 3. LA FENÊTRE PRINCIPALE (Affichage du Chat)
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Configure ta séance dans le menu à gauche pour commencer !"}]

# Affichage de l'historique visuel
for msg in st.session_state.messages:
    if msg["role"] != "system":
        # On masque la balise [EXPORT] pour que l'élève ne la voie pas à l'écran
        contenu_affichage = msg["content"].replace("[EXPORT]", "").strip()
        with st.chat_message(msg["role"]):
            st.markdown(contenu_affichage)

# ==========================================
# 4. GESTION DES NOUVEAUX MESSAGES & MÉMOIRE
# ==========================================
if prompt := st.chat_input("Écris ton message ici..."):
    with st.chat_message("user"):
        st.markdown(prompt)
        
        # Gestion de l'affichage de la photo pour l'élève
        image_a_envoyer = None
        if fichier_photo is not None:
            image_a_envoyer = Image.open(fichier_photo)
            st.image(image_a_envoyer, caption="Document joint", width=300)

    # Sauvegarde du message utilisateur dans la mémoire
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # --- PRÉPARATION DU PAQUET POUR GEMINI (Contexte + Historique + Message) ---
    contenu_pour_gemini = []
    
    # 1. On injecte les règles strictes
    if len(st.session_state.messages) > 0 and st.session_state.messages[0]["role"] == "system":
        contenu_pour_gemini.append("INSTRUCTIONS STRICTES : \n" + st.session_state.messages[0]["content"])
        
    # 2. On injecte l'historique de la conversation
    historique = "\nHISTORIQUE DE LA SÉANCE :\n"
    for msg in st.session_state.messages[1:-1]: # Tout sauf le system prompt et le message actuel
        role = "ÉLÈVE" if msg["role"] == "user" else "TUTEUR"
        historique += f"{role} : {msg['content']}\n"
    contenu_pour_gemini.append(historique)
    
    # 3. On ajoute la question actuelle de l'élève
    contenu_pour_gemini.append("\nNOUVEAU MESSAGE DE L'ÉLÈVE :\n"
