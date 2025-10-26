"""
Paso 2: Advertencia de Backup
"""
import streamlit as st
from config import INSTRUCTIONS, BASELINE_PATHS
from session_manager import go_to_next_step


def render_backup_step():
    """
    Renderiza la pantalla de advertencia de backup (Paso 1).
    """
    st.markdown("## PASO 2 de 7: Advertencia Importante")
    st.warning(INSTRUCTIONS['backup'])

    st.markdown("### Ubicaciones de los archivos baseline:")
    col1, col2 = st.columns(2)
    
    with col1:
        st.code(BASELINE_PATHS['old_software'], language="text")
        st.caption("📄 Archivos .ref (SX Suite ≤ 531)")
    
    with col2:
        st.code(BASELINE_PATHS['new_software'], language="text")
        st.caption("📄 Archivos .csv (SX Suite ≥ 557)")

    st.markdown("---")
    st.info(INSTRUCTIONS['backup_procedure'])

    st.markdown("---")
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button(" Ya realicé el backup, continuar", type="primary", use_container_width=True):
            st.session_state.backup_done = True
            go_to_next_step()
    
    with col_btn2:
        if st.button(" Omitir este paso (no recomendado)", use_container_width=True):
            st.session_state.backup_done = False
            go_to_next_step()
