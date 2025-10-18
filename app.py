import streamlit as st
from config import PAGE_CONFIG, STEPS
from session_manager import initialize_session_state
from ui.sidebar import render_sidebar
from ui.step_00_client_info import render_client_info_step
from ui.step_01_backup import render_backup_step
from ui.step_02_wstd import render_wstd_step
from ui.step_03_kit import render_kit_step
from ui.step_04_correction import render_correction_step
from ui.step_05_baseline import render_baseline_step
from ui.step_06_export import render_export_step
from ui.utilities import render_utilities_section


def main():
    """Aplicación principal de Baseline Adjustment Tool"""
    
    # Configuración de la página
    st.set_page_config(**PAGE_CONFIG)
    
    # Inicializar estado de sesión
    initialize_session_state()
    
    # Header principal
    st.title("🔧 Baseline Adjustment Tool")
    st.markdown("### Asistente para ajuste de línea base en espectrómetros NIR")
    
    # Sidebar con progreso
    render_sidebar()
    
    # Router de pasos
    current_step = st.session_state.step
    
    if current_step == -1:
        render_client_info_step()
    elif current_step == 0:
        render_backup_step()
    elif current_step == 1:
        render_wstd_step()
    elif current_step == 2:
        render_kit_step()
    elif current_step == 3:
        render_correction_step()
    elif current_step == 4:
        render_baseline_step()
    elif current_step == 5:
        render_export_step()
    
    # Sección de utilidades (siempre visible)
    st.markdown("---")
    render_utilities_section()


if __name__ == "__main__":
    main()
