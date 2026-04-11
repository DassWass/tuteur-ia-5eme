import streamlit as st
import google.generativeai as genai

# 1. Configuration de la clé API (sécurisée pour le cloud)
# L'application ira chercher la clé dans le coffre-fort de Streamlit
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# 2. Configuration de la page
st.set_page_config(page_title="Tuteur 5ème", layout="wide")
st.title("📚 Ton Tuteur Personnel")

# 3. La Barre Latérale (Le Cockpit)
with st.sidebar:
    st.header("⚙️ Paramètres de la séance")
    matiere = st.selectbox("Choisis ta matière :", ["Mathématiques", "Français", "Histoire-Géo", "SVT"])
    chapitre = st.text_input("Sur quel chapitre travailles-tu ?")
    
    if st.button("Lancer la séance"):
        st.session_state.messages = []
        
        # Le Prompt Système Sécurisé
        contexte = f"""Tu es un tuteur scolaire virtuel spécialement conçu pour accompagner un élève de 5ème (environ 13 ans) du système éducatif français. Ton rôle est de l'aider à réviser et à comprendre ses cours. La matière étudiée aujourd'hui est : {matiere}, et le chapitre est : {chapitre}.

RÈGLES DE COMPORTEMENT ET DE PÉDAGOGIE (STRICTES) :
1. Pédagogie Socratique : Ne donne JAMAIS la réponse exacte immédiatement. Pose des questions progressives pour aider l'élève à trouver la solution par lui-même. S'il se trompe, explique-lui son erreur avec bienveillance.
2. Ton et Style : Utilise le tutoiement ("tu"). Sois toujours encourageant, patient et positif. Utilise un langage clair, simple et intègre quelques emojis.
3. Source des connaissances : Tu dois IMPÉRATIVEMENT et UNIQUEMENT te baser sur le programme officiel du Ministère de l'Éducation Nationale français pour la classe de 5ème.

RÈGLES DE SÉCURITÉ ET INTERDITS (ABSOLUS) :
Tu as l'interdiction stricte d'aborder des sujets concernant : la vie personnelle, la religion, la sexualité, ou la politique.
Si l'élève aborde ces sujets, réponds exactement : "Je suis un assistant dédié uniquement à tes révisions scolaires. Reprenons notre exercice de {matiere}."
"""
        st.session_state.messages.append({"role": "system", "content": contexte})
        st.session_state.messages.append({"role": "assistant", "content": f"Salut ! Prêt à travailler sur le chapitre '{chapitre}' en {matiere} ? Que veux-tu faire en premier ?"})

# 4. La Fenêtre Principale (Le Chat)
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Configure ta séance dans le menu à gauche pour commencer !"}]

for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

if prompt := st.chat_input("Écris ton message ici..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    response = model.generate_content(prompt) 
    
    with st.chat_message("assistant"):
        st.markdown(response.text)
    st.session_state.messages.append({"role": "assistant", "content": response.text})
