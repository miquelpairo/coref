"""
Paso 5: Cargar Baseline de la Lámpara Nueva
"""
import streamlit as st
import pandas as pd
import numpy as np
import json
from config import INSTRUCTIONS, MESSAGES
from session_manager import (
    has_kit_data,
    save_baseline_data,
    go_to_next_step
)
from core.file_handlers import load_ref_file, load_csv_baseline
from utils.validators import validate_dimension_match
from utils.plotting import plot_baseline_spectrum


def render_baseline_step():
    """
    Renderiza el paso de carga de baseline (Paso 4).
    """
    st.markdown("## 📍 PASO 4 DE 5: Cargar Baseline de la Lámpara Nueva")
    
    if not has_kit_data():
        st.error("❌ No hay datos del Standard Kit. Vuelve al Paso 2.")
        return
    
    kit_data = st.session_state.kit_data
    lamp_new = kit_data['lamp_new']
    spectral_cols = kit_data['spectral_cols']
    
    # Mostrar instrucciones
    instructions_text = INSTRUCTIONS['baseline_load'].format(
        lamp_name=lamp_new,
        n_channels=len(spectral_cols)
    )
    st.markdown(instructions_text)
    
    st.markdown("---")
    
    # Uploader de archivo
    baseline_file = st.file_uploader(
        "📁 Sube el archivo baseline (.ref o .csv)",
        type=["ref", "csv"], 
        key="baseline_upload"
    )
    
    col_skip1, col_skip2 = st.columns([3, 1])
    with col_skip2:
        if st.button("⏭️ Omitir paso", key="skip_step4"):
            go_to_next_step()
    
    if baseline_file:
        file_extension = baseline_file.name.split('.')[-1].lower()
        
        try:
            if file_extension == 'ref':
                process_ref_file(baseline_file, spectral_cols, lamp_new)
            elif file_extension == 'csv':
                process_csv_file(baseline_file, spectral_cols, lamp_new)
                
        except Exception as e:
            st.error(f"❌ Error al procesar el archivo: {str(e)}")


def process_ref_file(file, spectral_cols, lamp_new):
    """
    Procesa un archivo .ref de baseline.
    
    Args:
        file: Archivo subido
        spectral_cols (list): Lista de columnas espectrales
        lamp_new (str): Nombre de la lámpara nueva
    """
    header, ref_spectrum = load_ref_file(file)
    
    st.success(MESSAGES['success_file_loaded'])
    
    # Mostrar información de la cabecera
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Valores de cabecera:**")
        st.write(f"X1 = {header[0]:.6e}")
        st.write(f"X2 = {header[1]:.6e}")
        st.write(f"X3 = {header[2]:.6e}")
    
    with col2:
        st.metric("Puntos espectrales", len(ref_spectrum))
        st.write("**Primeros 5 valores:**")
        st.write(ref_spectrum[:5])
    
    # Validar dimensiones
    if not validate_and_display_dimensions(len(ref_spectrum), len(spectral_cols)):
        return
    
    # Visualizar baseline
    visualize_baseline(ref_spectrum, lamp_new)
    
    # Guardar datos
    save_baseline_data(
        ref_spectrum=ref_spectrum,
        header=header,
        df_baseline=None,
        origin='ref'
    )
    
    # Botón continuar
    render_continue_button()


def process_csv_file(file, spectral_cols, lamp_new):
    """
    Procesa un archivo .csv de baseline.
    
    Args:
        file: Archivo subido
        spectral_cols (list): Lista de columnas espectrales
        lamp_new (str): Nombre de la lámpara nueva
    """
    df_baseline, ref_spectrum = load_csv_baseline(file)
    
    st.success(MESSAGES['success_file_loaded'])
    
    # Mostrar metadatos
    nir_pixels = int(df_baseline['nir_pixels'].iloc[0])
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("NIR Pixels", nir_pixels)
        st.metric("Timestamp", df_baseline['time_stamp'].iloc[0])
    
    with col2:
        st.metric("Sys Temp (°C)", f"{df_baseline['sys_temp'].iloc[0]:.2f}")
        st.metric("TEC Temp (°C)", f"{df_baseline['tec_temp'].iloc[0]:.2f}")
    
    with col3:
        st.metric("Lamp Time", df_baseline['lamp_time'].iloc[0])
        st.metric("Puntos data", len(ref_spectrum))
    
    # Verificar consistencia interna
    if nir_pixels != len(ref_spectrum):
        st.warning(
            f"⚠️ Inconsistencia: nir_pixels ({nir_pixels}) ≠ "
            f"longitud data ({len(ref_spectrum)})"
        )
    
    # Validar dimensiones
    if not validate_and_display_dimensions(len(ref_spectrum), len(spectral_cols)):
        return
    
    # Visualizar baseline
    visualize_baseline(ref_spectrum, lamp_new)
    
    # Guardar datos
    save_baseline_data(
        ref_spectrum=ref_spectrum,
        header=None,
        df_baseline=df_baseline,
        origin='csv'
    )
    
    # Botón continuar
    render_continue_button()


def validate_and_display_dimensions(baseline_length, tsv_length):
    """
    Valida y muestra el resultado de la comparación de dimensiones.
    
    Args:
        baseline_length (int): Longitud del baseline
        tsv_length (int): Longitud de columnas espectrales del TSV
        
    Returns:
        bool: True si las dimensiones coinciden
    """
    if not validate_dimension_match(baseline_length, tsv_length):
        error_msg = MESSAGES['error_dimension_mismatch'].format(
            baseline_points=baseline_length,
            tsv_channels=tsv_length
        )
        st.error(error_msg)
        return False
    else:
        success_msg = MESSAGES['success_dimension_match'].format(
            n_points=baseline_length
        )
        st.success(success_msg)
        return True


def visualize_baseline(ref_spectrum, lamp_name):
    """
    Visualiza el espectro del baseline.
    
    Args:
        ref_spectrum (np.array): Espectro del baseline
        lamp_name (str): Nombre de la lámpara
    """
    fig = plot_baseline_spectrum(ref_spectrum, lamp_name)
    st.pyplot(fig)


def render_continue_button():
    """
    Renderiza los botones de navegación del paso.
    """
    st.markdown("---")
    col_continue, col_skip = st.columns([3, 1])
    
    with col_continue:
        if st.button("➡️ Continuar al Paso 5", type="primary", use_container_width=True):
            go_to_next_step()
    
    with col_skip:
        if st.button("⏭️ Omitir", key="skip_after_step4", use_container_width=True):
            go_to_next_step()
