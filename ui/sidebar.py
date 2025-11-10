# -*- coding: utf-8 -*-
"""
Componente de barra lateral con progreso del proceso
"""
import streamlit as st
from config import STEPS
from session_manager import get_current_step


@st.dialog("⚠️ Cambios sin guardar")
def confirm_navigation_dialog(target_step, step_name):
    """
    Diálogo modal para confirmar navegación con cambios sin guardar.
    """
    st.write("Tienes cambios sin guardar en el paso actual.")
    st.write(f"¿Deseas navegar a **{step_name}** de todos modos?")
    st.caption("Los cambios no guardados se perderán.")
    
    st.markdown("")  # Espaciado
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✓ Sí, continuar", key="confirm_yes", use_container_width=True, type="primary"):
            st.session_state.unsaved_changes = False
            st.session_state.step = target_step
            st.session_state.pending_navigation = None
            st.session_state.pending_navigation_name = None
            st.rerun()
    with col2:
        if st.button("✗ Cancelar", key="confirm_no", use_container_width=True):
            st.session_state.pending_navigation = None
            st.session_state.pending_navigation_name = None
            st.rerun()


def render_sidebar():
    """
    Renderiza la barra lateral con el progreso de los pasos.
    """
    with st.sidebar:
        st.markdown("## Progreso")
        
        current_step = get_current_step()
        
        # Inicializar estados
        if 'pending_navigation' not in st.session_state:
            st.session_state.pending_navigation = None
        if 'pending_navigation_name' not in st.session_state:
            st.session_state.pending_navigation_name = None
        
        # Mostrar advertencia de cambios sin guardar
        if st.session_state.get('unsaved_changes', False):
            st.warning("⚠️ Cambios sin guardar")
        
        # Renderizar cada paso con su estado
        for step_idx, step_name in STEPS.items():
            step_number = step_idx
            
            if step_idx < current_step:
                # Paso completado - CLICKABLE
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
                            # Guardar destino y mostrar diálogo
                            st.session_state.pending_navigation = step_idx
                            st.session_state.pending_navigation_name = step_name
                            st.rerun()
                        else:
                            # Navegar directamente
                            st.session_state.step = step_idx
                            st.rerun()
                    
            elif step_idx == current_step:
                # Paso actual — botón verde (mismo type que completados) y flecha a la izquierda. No clicable.
                col1, col2 = st.columns([0.1, 0.9])
                with col1:
                    st.markdown('''
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <!-- Círculo verde para coherencia visual con completados -->
                            <circle cx="12" cy="12" r="10" stroke="#64B445" stroke-width="2" fill="none"/>
                            <!-- Flecha indicando "estás aquí" -->
                            <path d="M8 12h8m-4-4l4 4-4 4" stroke="#64B445" stroke-width="2" fill="none" stroke-linecap="round"/>
                        </svg>
                    ''', unsafe_allow_html=True)
                with col2:
                    st.button(
                        f"**{step_number}. {step_name}**",
                        key=f"current_step_{step_idx}",
                        use_container_width=True,
                        type="secondary",  # ⚠️ Pon aquí el MISMO type que uses en los completados (secondary o primary)
                        disabled=True       # no clicable
                    )
                
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
        
        # Información adicional
        total_steps = len(STEPS)
        completed = current_step
        progress = min(completed / total_steps, 1.0)
        
        st.progress(progress)
        st.caption(f"Paso {completed} de {total_steps}")
        
        st.markdown("---")
        
        # Leyenda
        st.caption("✓ Completado | → Actual | ○ Pendiente")
        st.caption("Haz clic en los pasos completados ✓ para revisarlos")
    
    # CRÍTICO: Mostrar diálogo FUERA del sidebar
    if st.session_state.get('pending_navigation') is not None:
        target_step = st.session_state.pending_navigation
        target_name = st.session_state.get('pending_navigation_name', f'Paso {target_step}')
        confirm_navigation_dialog(target_step, target_name)