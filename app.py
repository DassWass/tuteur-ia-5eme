import streamlit as st
import google.generativeai as genai
from PIL import Image

# ==========================================
# 1. CONFIGURATION INITIALE
# ==========================================
# Connexion sécurisée
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
# Modèle optimisé
model = genai.GenerativeModel('gemini-2.5-flash')

st.set_page_config(page_title="Tuteur 5ème", layout="wide")
st.title("📚 Ton Tuteur Personnel")

# ==========================================
# 2. LA BARRE LATÉRALE (Paramètres)
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
        st.session_state.messages = []
        
        # Le cerveau de l'IA
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
        contenu_affichage = msg["content"].replace("[EXPORT]", "").strip()
        with st.chat_message(msg["role"]):
            st.markdown(contenu_affichage)

# ==========================================
# 4. GESTION DES MESSAGES & IA
# ==========================================
if prompt := st.chat_input("Écris ton message ici..."):
    # Affichage du message élève
    with st.chat_message("user"):
        st.markdown(prompt)
        image_a_envoyer = None
        if fichier_photo is not None:
            image_a_envoyer = Image.open(fichier_photo)
            st.image(image_a_envoyer, caption="Document joint", width=300)

    # Sauvegarde
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Préparation de la mémoire pour l'IA
    contenu_pour_gemini = []
    
    if len(st.session_state.messages) > 0 and st.session_state.messages[0]["role"] == "system":
        contenu_pour_gemini.append("INSTRUCTIONS STRICTES : \n" + st.session_state.messages[0]["content"])
        
    historique = "\nHISTORIQUE DE LA SÉANCE :\n"
    for msg in st.session_state.messages[1:-1]:
        role = "ÉLÈVE" if msg["role"] == "user" else "TUTEUR"
        historique += f"{role} : {msg['content']}\n"
    contenu_pour_gemini.append(historique)
    
    # La ligne corrigée est ici :
    contenu_pour_gemini.append("\nNOUVEAU MESSAGE DE L'ÉLÈVE :\n" + prompt)
    
    if image_a_envoyer is not None:
        contenu_pour_gemini.append(image_a_envoyer)
    
    # Appel à l'IA avec sécurité (Bloc Try/Except)
    with st.chat_message("assistant"):
        try:
            response = model.generate_content(contenu_pour_gemini) 
            texte_reponse = response.text
            contenu_affichage = texte_reponse.replace("[EXPORT]", "").strip()
            st.markdown(contenu_affichage)
            
            # On ne sauvegarde que si ça a marché
            st.session_state.messages.append({"role": "assistant", "content": texte_reponse})
            
        except Exception as e:
            # Message de secours si le serveur plante
            st.error("Oups, j'ai eu un petit trou de mémoire ou le réseau a coupé. Peux-tu reformuler ou réessayer ?")
            # On retire le message de l'élève de l'historique pour qu'il puisse réessayer proprement
            st.session_state.messages.pop()

# ==========================================
# 5. L'EXPORT DES DOCUMENTS
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
    st.sidebar.info("💡 Demande à l'IA de générer un exercice complet ou une fiche de synthèse pour voir le bouton de téléchargement apparaître ici.")
