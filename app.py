import streamlit as st
import google.generativeai as genai
from PIL import Image

# ==========================================
# 1. CONFIGURATION INITIALE
# ==========================================
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash-latest')

st.set_page_config(page_title="Tuteur 5ème", layout="wide")
st.title("📚 Ton Tuteur Personnel")

# ==========================================
# 2. LA BARRE LATÉRALE (Paramètres & Photo)
# ==========================================
with st.sidebar:
    st.header("⚙️ Paramètres de la séance")
    matiere = st.selectbox("Choisis ta matière :", ["Mathématiques", "Français", "Histoire-Géo", "SVT"])
    chapitre = st.text_input("Sur quel chapitre travailles-tu ?")
    
    st.markdown("---")
    st.subheader("📸 Ajouter un document")
    st.info("Glisse la photo de ton cours ou de ton exercice ici.")
    fichier_photo = st.file_uploader("", type=["png", "jpg", "jpeg"])
    st.markdown("---")
    
    if st.button("Lancer la séance"):
        # Réinitialisation de la discussion
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
# 3. LA FENÊTRE PRINCIPALE (Le Chat)
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Configure ta séance dans le menu à gauche pour commencer !"}]

# Affichage de l'historique
for msg in st.session_state.messages:
    if msg["role"] != "system":
        # On masque la balise [EXPORT] pour que l'élève ne la voie pas à l'écran
        contenu_affichage = msg["content"].replace("[EXPORT]", "").strip()
        with st.chat_message(msg["role"]):
            st.markdown(contenu_affichage)

# ==========================================
# 4. GESTION DES NOUVEAUX MESSAGES
# ==========================================
if prompt := st.chat_input("Écris ton message ici..."):
    with st.chat_message("user"):
        st.markdown(prompt)
        
        # Affichage de la photo si elle existe
        image_a_envoyer = None
        if fichier_photo is not None:
            image_a_envoyer = Image.open(fichier_photo)
            st.image(image_a_envoyer, caption="Document joint", width=300)

    # Sauvegarde du message utilisateur
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Préparation du paquet pour Gemini (Texte + Photo)
    contenu_pour_gemini = [prompt]
    if image_a_envoyer is not None:
        contenu_pour_gemini.append(image_a_envoyer)
    
    # Appel à l'IA
    response = model.generate_content(contenu_pour_gemini) 
    
    # Affichage de la réponse IA (sans la balise [EXPORT])
    texte_reponse = response.text
    contenu_affichage = texte_reponse.replace("[EXPORT]", "").strip()
    
    with st.chat_message("assistant"):
        st.markdown(contenu_affichage)
        
    # Sauvegarde de la réponse IA dans l'historique (AVEC la balise pour l'export)
    st.session_state.messages.append({"role": "assistant", "content": texte_reponse})

# ==========================================
# 5. L'EXPORT DES DOCUMENTS (Menu de gauche)
# ==========================================
st.sidebar.subheader("📥 Tes Documents")

texte_export = f"--- Fiches et Exercices : {matiere} ({chapitre}) ---\n\n"
documents_trouves = False

for msg in st.session_state.messages:
    if msg["role"] == "assistant" and "[EXPORT]" in msg["content"]:
        documents_trouves = True
        contenu_nettoye = msg["content"].replace("[EXPORT]", "").strip()
        texte_export += f"{contenu_nettoye}\n\n"
        texte_export += "--------------------------------------------------\n\n"

if documents_trouves:
    st.sidebar.download_button(
        label="📄 Télécharger les fiches/exercices",
        data=texte_export,
        file_name=f"documents_{matiere}.txt",
        mime="text/plain"
    )
else:
    st.sidebar.info("💡 Demande à l'IA de générer un exercice ou une fiche de synthèse pour voir le bouton de téléchargement apparaître ici.")
