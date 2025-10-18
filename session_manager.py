"""
Gestión del estado de sesión de Streamlit
"""
import streamlit as st
from datetime import datetime


def initialize_session_state():
    """
    Inicializa todas las variables del session_state si no existen.
    Esta función se llama al inicio de cada ejecución de la app.
    """
    
    # Estado del flujo
    if 'step' not in st.session_state:
        st.session_state.step = -1
    
    # Datos de los diferentes pasos
    if 'client_data' not in st.session_state:
        st.session_state.client_data = None
    
    if 'wstd_data' not in st.session_state:
        st.session_state.wstd_data = None
    
    if 'kit_data' not in st.session_state:
        st.session_state.kit_data = None
    
    if 'baseline_data' not in st.session_state:
        st.session_state.baseline_data = None
    
    # Flags de control
    if 'backup_done' not in st.session_state:
        st.session_state.backup_done = False
    
    # Selección de muestras
    if 'selected_ids' not in st.session_state:
        st.session_state.selected_ids = []
    
    if 'pending_selection' not in st.session_state:
        st.session_state.pending_selection = []


def reset_session_state():
    """
    Reinicia todos los datos del session_state.
    Útil para comenzar un nuevo proceso desde cero.
    """
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    initialize_session_state()


def go_to_step(step_number):
    """
    Navega a un paso específico del proceso.
    
    Args:
        step_number (int): Número del paso al que navegar (-1 a 5)
    """
    st.session_state.step = step_number
    st.rerun()


def go_to_previous_step():
    """
    Retrocede al paso anterior del proceso.
    No permite retroceder antes del paso -1.
    """
    st.session_state.step = max(-1, st.session_state.step - 1)
    st.rerun()


def go_to_next_step():
    """
    Avanza al siguiente paso del proceso.
    """
    st.session_state.step += 1
    st.rerun()


def save_client_data(client_name, sensor_sn, contact_person='', contact_email='', 
                     equipment_model='', location='', notes=''):
    """
    Guarda los datos del cliente en el session_state.
    
    Args:
        client_name (str): Nombre del cliente
        sensor_sn (str): Número de serie del sensor
        contact_person (str): Persona de contacto
        contact_email (str): Email de contacto
        equipment_model (str): Modelo del equipo
        location (str): Ubicación
        notes (str): Notas adicionales
    """
    st.session_state.client_data = {
        'client_name': client_name,
        'contact_person': contact_person,
        'contact_email': contact_email,
        'sensor_sn': sensor_sn,
        'equipment_model': equipment_model,
        'location': location,
        'notes': notes,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }


def save_default_client_data():
    """
    Guarda datos de cliente por defecto (cuando se omite el paso).
    """
    st.session_state.client_data = {
        'client_name': 'No especificado',
        'contact_person': '',
        'contact_email': '',
        'sensor_sn': 'No especificado',
        'equipment_model': '',
        'location': '',
        'notes': '',
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }


def save_wstd_data(df, grouped, spectral_cols, lamps):
    """
    Guarda los datos del diagnóstico WSTD.
    
    Args:
        df (pd.DataFrame): DataFrame con las mediciones WSTD
        grouped (pd.DataFrame): DataFrame agrupado por lámpara
        spectral_cols (list): Lista de nombres de columnas espectrales
        lamps (list): Lista de nombres de lámparas
    """
    st.session_state.wstd_data = {
        'df': df,
        'grouped': grouped,
        'spectral_cols': spectral_cols,
        'lamps': lamps
    }


def save_kit_data(df, df_ref_grouped, df_new_grouped, spectral_cols, 
                  lamp_ref, lamp_new, common_ids):
    """
    Guarda los datos del Standard Kit.
    
    Args:
        df (pd.DataFrame): DataFrame completo con todas las mediciones
        df_ref_grouped (pd.DataFrame): Mediciones de lámpara de referencia agrupadas
        df_new_grouped (pd.DataFrame): Mediciones de lámpara nueva agrupadas
        spectral_cols (list): Lista de columnas espectrales
        lamp_ref (str): Nombre de la lámpara de referencia
        lamp_new (str): Nombre de la lámpara nueva
        common_ids (list): IDs comunes entre ambas lámparas
    """
    st.session_state.kit_data = {
        'df': df,
        'df_ref_grouped': df_ref_grouped,
        'df_new_grouped': df_new_grouped,
        'spectral_cols': spectral_cols,
        'lamp_ref': lamp_ref,
        'lamp_new': lamp_new,
        'common_ids': common_ids
    }


def update_kit_data_with_correction(mean_diff):
    """
    Actualiza los datos del kit con la corrección calculada.
    
    Args:
        mean_diff (np.array): Array con la diferencia promedio espectral
    """
    if st.session_state.kit_data is not None:
        st.session_state.kit_data['mean_diff'] = mean_diff


def save_baseline_data(ref_spectrum, header, df_baseline, origin):
    """
    Guarda los datos del baseline cargado.
    
    Args:
        ref_spectrum (np.array): Espectro del baseline
        header (np.array): Cabecera del archivo .ref (None si es CSV)
        df_baseline (pd.DataFrame): DataFrame del baseline CSV (None si es .ref)
        origin (str): Tipo de archivo ('ref' o 'csv')
    """
    st.session_state.baseline_data = {
        'ref_spectrum': ref_spectrum,
        'header': header,
        'df_baseline': df_baseline,
        'origin': origin
    }


def update_selected_samples(selected_ids):
    """
    Actualiza la lista de muestras seleccionadas para la corrección.
    
    Args:
        selected_ids (list): Lista de IDs de muestras seleccionadas
    """
    st.session_state.selected_ids = list(selected_ids)


def update_pending_selection(pending_ids):
    """
    Actualiza la selección pendiente (antes de confirmar).
    
    Args:
        pending_ids (list): Lista de IDs pendientes de confirmar
    """
    st.session_state.pending_selection = list(pending_ids)


def get_current_step():
    """
    Obtiene el paso actual del proceso.
    
    Returns:
        int: Número del paso actual
    """
    return st.session_state.step


def has_client_data():
    """
    Verifica si hay datos del cliente guardados.
    
    Returns:
        bool: True si hay datos del cliente
    """
    return st.session_state.client_data is not None


def has_wstd_data():
    """
    Verifica si hay datos de WSTD guardados.
    
    Returns:
        bool: True si hay datos de WSTD
    """
    return st.session_state.wstd_data is not None


def has_kit_data():
    """
    Verifica si hay datos del kit guardados.
    
    Returns:
        bool: True si hay datos del kit
    """
    return st.session_state.kit_data is not None


def has_baseline_data():
    """
    Verifica si hay datos de baseline guardados.
    
    Returns:
        bool: True si hay datos de baseline
    """
    return st.session_state.baseline_data is not None


def has_correction_data():
    """
    Verifica si hay datos de corrección calculados.
    
    Returns:
        bool: True si hay corrección calculada
    """
    return (st.session_state.kit_data is not None and 
            'mean_diff' in st.session_state.kit_data)
