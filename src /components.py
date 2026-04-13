import streamlit as st
from src.engine import generate_next, init_question

def next_question_button(chat_session, matiere: str, sujet: str, mode: str, default_label: str = "➡️ Question suivante"):
    st.markdown('<div class="launch-btn">', unsafe_allow_html=True)
    
    btn_label = "💀 Voir mon score final" if (mode == "exercice" and st.session_state.vies <= 0) else default_label
    
    if st.button(btn_label, use_container_width=True, key="next_q_btn"):
        if mode == "exercice" and st.session_state.vies <= 0:
            st.session_state.game_over = True
            st.rerun()
            
        with st.spinner("Chargement... ⚡"):
            try:
                data, raw = generate_next(chat_session, matiere, sujet, st.session_state.difficulty, False)
                if data:
                    init_question(data)
                else:
                    st.session_state.messages.append({"role": "assistant", "content": raw})
            except Exception as e:
                st.error(f"❌ Erreur lors de la génération : {e}")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
