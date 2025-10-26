# -*- coding: utf-8 -*-
"""
Componente de barra lateral con progreso del proceso
"""
import streamlit as st
from config import STEPS
from session_manager import get_current_step

def render_sidebar():
    """
    Renderiza la barra lateral con el progreso de los pasos.
    """
    with st.sidebar:
               
        st.markdown("## Progreso")
        
        current_step = get_current_step()
        
        # Renderizar cada paso con su estado
        for step_idx, step_name in STEPS.items():
            # Calcular numero de paso visible (1-7)
            step_number = step_idx
            
            if step_idx < current_step:
                # Paso completado - CLICKABLE con seguridad
                col1, col2 = st.columns([0.1, 0.9])
                with col1:
                    st.markdown('''
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <circle cx="12" cy="12" r="10" fill="white" stroke="#64B445" stroke-width="2"/>
                            <path d="M9 12l2 2 4-4" stroke="#000000" stroke-width="2" stroke-linecap="round"/>
                        </svg>
                    ''', unsafe_allow_html=True)
                with col2:
                    if st.button(
                        f"**{step_number}. {step_name}**",
                        key=f"nav_step_{step_idx}",
                        use_container_width=True,
                        type="secondary"
                    ):
                        # Verificar si hay cambios sin guardar
                        if st.session_state.get('unsaved_changes', False):
                            st.warning("Tienes cambios sin guardar en el paso actual")
                            if st.button("Continuar de todos modos", key=f"confirm_{step_idx}"):
                                st.session_state.unsaved_changes = False
                                st.session_state.step = step_idx
                                st.rerun()
                        else:
                            st.session_state.step = step_idx
                            st.rerun()
                    
            elif step_idx == current_step:
                # Paso actual - NO CLICKABLE
                col1, col2 = st.columns([0.1, 0.9])
                with col1:
                    st.markdown('''
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <circle cx="12" cy="12" r="10" stroke="#4DB9D2" stroke-width="2" fill="none"/>
                            <path d="M8 12h8m-4-4l4 4-4 4" stroke="#4DB9D2" stroke-width="2" fill="none" stroke-linecap="round"/>
                        </svg>
                    ''', unsafe_allow_html=True)
                with col2:
                    st.markdown(f"**{step_number}. {step_name}**")
                
            else:
                # Paso pendiente - NO CLICKABLE
                col1, col2 = st.columns([0.1, 0.9])
                with col1:
                    st.markdown('''
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <circle cx="12" cy="12" r="10" stroke="#999" stroke-width="2" fill="none"/>
                        </svg>
                    ''', unsafe_allow_html=True)
                with col2:
                    st.markdown(f"{step_number}. {step_name}")
        
        st.markdown("---")
        
        # Informacion adicional
        total_steps = len(STEPS)
        completed = current_step
        progress = min(completed / total_steps, 1.0)
        
        st.progress(progress)
        st.caption(f"Paso {completed} de {total_steps}")
        
        st.markdown("---")
        
        # Leyenda
        st.caption("Haz clic en los pasos completados para revisarlos")