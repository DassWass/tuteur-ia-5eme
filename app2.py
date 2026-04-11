import streamlit as st
import google.generativeai as genai
from PIL import Image
from fpdf import FPDF
import datetime
import json
import re

# ==========================================
# 1. CONFIGURATION & SÉCURITÉ DU MODÈLE
# ==========================================
# Vérification de la clé API dans les Secrets
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("⚠️ Clé API manquante dans les Secrets Streamlit.")
    st.stop()

# MODÈLE ACTIF : Gemini 2.5 Flash (Quota limité à 20/jour sur plan gratuit !)
# Si blocage rapide, remplace par : 'gemini-1.5-flash-latest'
# active_model_name = 'gemini-1.5-flash-latest'
active_model_name = 'gemini-2.5-flash'
model = genai.GenerativeModel(active_model_name)

# Configuration de la page EN MODE WIDE pour les colonnes
st.set_page_config(page_title="Tuteur IA 5ème - Édition Ludique", layout="wide")

# ==========================================
# 2. STYLE CSS AVANCÉ (Ludique & Interactif)
# ==========================================
# Pour reproduire les gros boutons verts/rouges, rounded corners, shadows, etc.
st.markdown("""
    <style>
    /* Global Styling */
    [data-testid="stAppViewContainer"] {
        background-color: #f9fafb;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #f3f4f6;
    }
    div.stButton > button.btn-pdf {
        background-color: #3b82f6;
        color: white;
        width: 100%;
    }

    /* Column 2 Exercise Zone Styling */
    .exercise-zone {
        background-color: #eff6ff;
        border: 2px solid #93c5fd;
        border-radius: 20px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        text-align: center;
    }
    .exercise-title {
        color: #1e40af;
        font-size: 1.4rem;
        font-weight: bold;
        margin-bottom: 15px;
    }
    .exercise-question {
        background-color: white;
        border-radius: 12px;
        padding: 15px;
        font-size: 1.2rem;
        border: 1px solid #e5e7eb;
        margin-bottom: 25px;
    }

    /* Dynamic Buttons Styling (colors VRAI/FAUX) */
    div.stButton > button.btn-vrai {
        background-color: #16a34a !important; /* Vert VRAI */
        color: white !important;
        font-weight: bold !important;
        font-size: 1.3rem !important;
        border-radius: 12px !important;
        padding: 1rem 2rem !important;
        border: none !important;
        width: 100% !important;
        cursor: pointer;
    }
    div.stButton > button.btn-vrai:hover {
        background-color: #15803d !important; /* Vert Hover */
    }
    div.stButton > button.btn-faux {
        background-color: #dc2626 !important; /* Rouge FAUX */
        color: white !important;
        font-weight: bold !important;
        font-size: 1.3rem !important;
        border-radius: 12px !important;
        padding: 1rem 2rem !important;
        border: none !important;
        width: 100% !important;
        cursor: pointer;
    }
    div.stButton > button.btn-faux:hover {
        background-color: #b91c1c !important; /* Rouge Hover */
    }

    /* Default streamling buttons to rounded for ludic feel */
    div.stButton > button {
        border-radius: 10px !important;
    }
    </style>
""", unsafe_allow_html=True)

# Initialisation de la session
if "config_validated" not in st.session_state:
    st.session_state.config_validated = False
if "messages" not in st.session_state:
    st.session_state.messages = []
if "active_exercise_data" not in st.session_state:
    st.session_state.active_exercise_data = None
if "input_text_disabled" not in st.session_state:
    st.session_state.input_text_disabled = False

# ==========================================
# 3. INTERFACE PRINCIPALE (WIDE LAYOUT)
# ==========================================
st.title("📚 Tuteur IA 5ème - Édition Ludique")

# Création des colonnes : [3, 1] donne 3/4 chat, 1/4 zone dynamique
col_chat, col_dynamique = st.columns([3, 1])

# ==========================================
# GAUCHE : COLONNE CONVERSATION
# ==========================================
with col_chat:
    # Affichage de l'historique
    for msg in st.session_state.messages:
        if msg["role"] != "system":
            # Icônes de chat friendly
            icon = "🧑" if msg["role"] == "user" else "🤖"
            with st.chat_message(msg["role"], avatar=icon):
                # On enlève les balises techniques pour l'élève
                clean_content = re.sub(r'\[\[EXERCISE_DATA\]\].*?\[\[END_EXERCISE\]\]', '', msg["content"], flags=re.DOTALL)
                st.markdown(clean_content.replace("[EXPORT]", "").strip())

    # Zone de saisie utilisateur
    # Elle est désactivée si un exercice dynamique est actif pour forcer le bouton
    input_text = st.chat_input("Réponds au tuteur ici...", disabled=st.session_state.input_text_disabled)
    if input_text:
        st.session_state.messages.append({"role": "user", "content": input_text})
        # Lancement de la logique de réponse de l'IA (après la saisie ou le bouton)
        st.rerun()

# ==========================================
# DROITE : COLONNE DYNAMIQUE (Zone d'Exercice)
# ==========================================
with col_dynamique:
    # Header de la zone dynamique
    st.markdown('<div class="exercise-zone"><div class="exercise-title">🎯 Zone d\'Exercice Dynamique</div>', unsafe_allow_html=True)

    # placeholder pour placeholder
    placeholder_text = '<div style="color: #6b7280; font-style: italic;">Attend que le tuteur te propose un exercice...</div>'
    
    # DÉTECTION ET AFFICHAGE D'UN EXERCICE ACTIF
    # On regarde le dernier message de l'IA pour voir s'il contient des données structurées
    for msg in reversed(st.session_state.messages):
        if msg["role"] == "assistant":
            # Cherche [[EXERCISE_DATA]]...[[END_EXERCISE]]
            match = re.search(r'\[\[EXERCISE_DATA\]\](.*?)\[\[END_EXERCISE\]\]', msg["content"], flags=re.DOTALL)
            if match:
                exercise_raw = match.group(1).strip()
                try:
                    # Conversion des données JSON fournies par l'IA
                    exercise_data = json.loads(exercise_raw)
                    st.session_state.active_exercise_data = exercise_data
                    st.session_state.input_text_disabled = True # Désactivé la saisie texte
                    break # Trouvé, on arrête la boucle
                except json.JSONDecodeError:
                    pass
    else:
        # Aucun exercice actif trouvé, reset
        st.session_state.active_exercise_data = None
        st.session_state.input_text_disabled = False

    # Affichage de l'exercice s'il existe
    if st.session_state.active_exercise_data:
        data = st.session_state.active_exercise_data
        st.markdown(f'<div class="exercise-question">{data["question"]}</div>', unsafe_allow_html=True)
        
        # LOGIQUE DYNAMIQUE DES BOUTONS (ex: Vrai/Faux)
        if data["type"] == "vrai_faux":
            c1, c2 = st.columns(2)
            with c1:
                # Bouton VRAI avec style "btn-vrai"
                if st.button("VRAI 👍", key="true_btn"):
                    # Simule l'envoi d'un message standard
                    st.session_state.messages.append({"role": "user", "content": "Je pense que c'est VRAI"})
                    # Effacer l'exercice actif pour la suite
                    st.session_state.active_exercise_data = None
                    st.rerun()
            with c2:
                # Bouton FAUX avec style "btn-faux"
                if st.button("FAUX 👎", key="false_btn"):
                    # Simule l'envoi d'un message standard
                    st.session_state.messages.append({"role": "user", "content": "Je pense que c'est FAUX"})
                    st.session_state.active_exercise_data = None
                    st.rerun()
            # Injection du CSS spécifiques aux boutons par Key
            st.markdown(f'<style>div[data-testid="stColumn"]:nth-of-type(1) div[data-testid="stVerticalBlock"] > div.stButton > button[key="true_btn"] {{ background-color: #16a34a !important; color: white !important; font-weight: bold !important; font-size: 1.3rem !important; border-radius: 12px !important; padding: 1rem 2rem !important; border: none !important; width: 100% !important; }} div[data-testid="stColumn"]:nth-of-type(1) div[data-testid="stVerticalBlock"] > div.stButton > button[key="true_btn"]:hover {{ background-color: #15803d !important; }}</style>', unsafe_allow_html=True)
            st.markdown(f'<style>div[data-testid="stColumn"]:nth-of-type(2) div[data-testid="stVerticalBlock"] > div.stButton > button[key="false_btn"] {{ background-color: #dc2626 !important; color: white !important; font-weight: bold !important; font-size: 1.3rem !important; border-radius: 12px !important; padding: 1rem 2rem !important; border: none !important; width: 100% !important; }} div[data-testid="stColumn"]:nth-of-type(2) div[data-testid="stVerticalBlock"] > div.stButton > button[key="false_btn"]:hover {{ background-color: #b91c1c !important; }}</style>', unsafe_allow_html=True)

        elif data["type"] == "placeholder":
            st.markdown("Attend la suite...")
            
    else:
        st.markdown(placeholder_text, unsafe_allow_html=True)

    # Fermeture du div de la zone
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 4. BARRE LATÉRALE (Paramètres & PDF)
# ==========================================
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Verrouillage de la sidebar si la séance est en cours
    disabled_config = len(st.session_state.messages) > 0
    
    matieres = ["Mathématiques", "Français", "Histoire-Géo", "SVT", "Physique-Chimie", "Anglais", "Espagnol", "Autre"]
    matiere_choisie = st.selectbox("1. Choisis ta matière :", matieres, disabled=disabled_config)
    matiere_finale = matiere_choisie
    if matiere_choisie == "Autre":
        matiere_finale = st.text_input("Précise la matière :", disabled=disabled_config)
            
    sujet = st.text_input("2. Sur quel sujet travailles-tu ?", placeholder="Ex: Les fractions...", disabled=disabled_config)

    st.markdown("---")
    
    if not disabled_config:
        # Le bouton de lancement
        if st.button("🚀 LANCER LES RÉVISIONS"):
            if not sujet or (matiere_choisie == "Autre" and not matiere_finale):
                st.warning("⚠️ Renseigne la matière et le sujet avant de commencer.")
            else:
                st.session_state.messages = []
                st.session_state.active_exercise_data = None
                
                # PROMPT SYSTÈME : LA LOI DU PAS-À-PAS LUDIQUE
                contexte_systeme = f"""Tu es un tuteur scolaire bienveillant pour un élève de 5ème (13 ans). 
Matière : {matiere_finale}. Sujet : {sujet}.

RÈGLES D'INTERACTION STRICTES (PAS À PAS LUDIQUE) :
1. LE BRISE-GLACE : Démarre TOUJOURS par 1 ou 2 blagues courtes pour dérider l'élève.
2. PAS-À-PAS : Ne donne JAMAIS l'exercice complet. Guide l'élève ligne par ligne.
3. EXERCICE DYNAMIQUE : Pour chaque exercice, tu dois fournir un message d'introduction pédagogique, SUIVI de données structurées.
   FORMAT EXERCICE (VF) : [[EXERCISE_DATA]] {{ "type": "vrai_faux", "question": "TA QUESTION LUDIQUE ICI", "options": ["Vrai 👍", "Faux 👎"] }} [[END_EXERCISE]]
4. CORRECTION : Si c'est juste, félicite-le et donne la micro-étape suivante. Si c'est faux, donne un indice.
5. TUTOIEMENT : Utilise le tutoiement, sois très encourageant.
6. EXPORT : N'utilise la balise [EXPORT] QUE lorsque l'exercice est ENTIÈREMENT terminé et corrigé, pour en faire une fiche de synthèse propre.
"""
                st.session_state.messages.append({"role": "system", "content": contexte_systeme})
                
                try:
                    prompt_init = f"Commence la séance de {matiere_finale} sur {sujet} par tes blagues puis introduis la première étape de révision."
                    res = model.generate_content(prompt_init)
                    st.session_state.messages.append({"role": "assistant", "content": res.text})
                    st.rerun()
                except Exception as e:
                    st.error("Problème technique au démarrage. Vérifie ton quota ou ta clé.")
    
    # SECTION PDF
    if len(st.session_state.messages) > 0:
        st.markdown("---")
        st.subheader("📥 Exportation")
        # On ne récupère que ce qui est tagué [EXPORT]
        export_txt = ""
        for m in st.session_state.messages:
            if m["role"] == "assistant" and "[EXPORT]" in m["content"]:
                # On nettoie le texte
                cleaned = m["content"].replace("[EXPORT]", "").strip()
                cleaned = re.sub(r'\[\[EXERCISE_DATA\]\].*?\[\[END_EXERCISE\]\]', '', cleaned, flags=re.DOTALL)
                export_txt += cleaned + "\n\n"

        if export_txt:
            # Création du PDF
            pdf = FPDF()
            pdf.add_page()
            # Font standard Arial supportée par défaut
            pdf.set_font("Arial", "B", 16)
            pdf.cell(190, 10, f"Tuteur IA - Fiche {matiere_finale}", ln=True, align='C')
            pdf.set_font("Arial", "", 12)
            pdf.cell(190, 10, f"Sujet : {sujet}", ln=True, align='C')
            pdf.ln(10)
            pdf.set_font("Arial", "", 11)
            # Nettoyage pour PDF (remplacement des accents pour Arial si besoin, fpdf2 gère mieux)
            try:
                # Fpdf2 convert unicode
                pdf.multi_cell(190, 8, export_txt)
                pdf_bytes = bytes(pdf.output())
                # Bouton PDF bleu
                st.download_button(
                    label="📄 Télécharger ma fiche (PDF)",
                    data=pdf_bytes,
                    file_name=f"tuteur_{matiere_finale}.pdf",
                    mime="application/pdf",
                    key="btn-pdf-blue"
                )
                st.markdown(f'<style>div.stButton > button[key="btn-pdf-blue"] {{ background-color: #3b82f6 !important; color: white !important; width: 100% !important; }}</style>', unsafe_allow_html=True)
            except Exception:
                st.error("Désolé, problème technique de génération du PDF (Unicode).")
        else:
            st.info("💡 Demande un résumé ([EXPORT]) à l'IA pour activer le PDF.")

# ==========================================
# 5. LOGIQUE DE RÉPONSE IA (Si Séance Lancée)
# ==========================================
if st.session_state.config_validated and len(st.session_state.messages) > 0:
    # On vérifie si la dernière message vient de l'utilisateur
    if st.session_state.messages[-1]["role"] == "user":
        # Appel IA avec historique complet
        with st.chat_message("assistant", avatar="🤖"):
            try:
                # Préparation de l'historique textuel propre pour Gemini
                full_prompt = ""
                for m in st.session_state.messages:
                    role_tag = "SYSTEM" if m["role"] == "system" else "ELEVE" if m["role"] == "user" else "TUTEUR"
                    full_prompt += f"{role_tag}: {m['content']}\n"
                
                # Génération de la réponse
                response = model.generate_content(full_prompt)
                texte_ia = response.text
                
                # Sauvegarde de la réponse technique
                st.session_state.messages.append({"role": "assistant", "content": texte_ia})
                st.rerun() # Pour relancer la détection de l'exercice dynamique
                
            except Exception as e:
                # DEBUG MODE : On affiche la vraie erreur
                st.error(f"⚠️ Erreur technique de l'IA (Quota, Clé ou Modèle). Désolé ! Erreur : {e}")
                st.info("Le quota Gemini 2.5 est très faible sur plan gratuit (20/jour). Attends un peu ou change de modèle.")
