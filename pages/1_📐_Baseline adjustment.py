# -*- coding: utf-8 -*-
import streamlit as st
from config import PAGE_CONFIG
from session_manager import initialize_session_state
from ui.sidebar import render_sidebar
from ui.step_00_client_info import render_client_info_step
from ui.step_01_backup import render_backup_step
from ui.step_02_wstd import render_wstd_step
from ui.step_05_baseline_alignment import render_baseline_alignment_step  # ⭐ NUEVO
from ui.step_04_validation import render_validation_step
from ui.utilities import render_utilities_section
from auth import check_password, logout
from buchi_streamlit_theme import apply_buchi_styles
import streamlit.components.v1 as components

def main():
    """Aplicacion principal de Baseline Adjustment Tool"""
    

    
    # Aplicar estilos corporativos Buchi
    apply_buchi_styles()
    
    # Verificar autenticacion
    if not check_password():
        st.stop()
    
    # Inicializar estado de sesion
    initialize_session_state()
    
    # Hook post-rerun: si vengo de un cambio de paso, sube al top
    if st.session_state.get("_scroll_to_top"):
        components.html(
            """
            <script>
              // intenta en raiz y en contenedores comunes de Streamlit
              (function(){
                const doc = window.parent?.document || document;
                const mains = doc.querySelectorAll('section.main, main, body, html');
                // Mover scroll del documento
                doc.documentElement.scrollTo({top: 0, left: 0, behavior: 'auto'});
                doc.body.scrollTop = 0;
                // Por si el contenedor principal controla el scroll:
                mains.forEach(el => { try { el.scrollTo(0,0); } catch(e){} });
              })();
            </script>
            """,
            height=0,
        )
        st.session_state._scroll_to_top = False
    
    # Header principal con boton de logout
    col1, col2 = st.columns([5, 1])
    with col1:
        st.title("Baseline Adjustment Tool")
        st.markdown("### Asistente para ajuste de linea base en espectrometros NIR")
    with col2:
        st.markdown("")  # Espaciado
        if st.button("Cerrar Sesion", use_container_width=True, key="logout_btn"):
            logout()
    
    # Sidebar con progreso (incluye el diálogo modal)
    render_sidebar()
    
    # ⭐ CRÍTICO: Si hay navegación pendiente, NO renderizar el paso actual
    # El diálogo modal se encarga de la navegación
    if st.session_state.get('pending_navigation') is not None:
        # Mostrar mensaje temporal mientras se confirma
        st.info("⏳ Confirma la navegación en el diálogo que aparece arriba...")
        st.stop()  # Detener renderizado del paso actual
    
    # Router de pasos (⭐ ACTUALIZADO A 5 PASOS)
    current_step = st.session_state.step
    if current_step == 1:
        render_client_info_step()
    elif current_step == 2:
        render_backup_step()
    elif current_step == 3:
        render_wstd_step()
    elif current_step == 4:
        render_validation_step()           # ← NUEVO: Validación primero
    elif current_step == 5:
        render_baseline_alignment_step()   # ← NUEVO: Alineamiento después
    
    # Seccion de utilidades (siempre visible)
    st.markdown("---")
    render_utilities_section()

if __name__ == "__main__":
    main()