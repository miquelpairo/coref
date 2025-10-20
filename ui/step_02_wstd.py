"""
Paso 2: Diagnostico WSTD (White Standard)
"""
import streamlit as st
import pandas as pd
import numpy as np
import io
from config import INSTRUCTIONS, MESSAGES, SPECIAL_IDS, WSTD_THRESHOLDS, DIAGNOSTIC_STATUS
from session_manager import save_wstd_data, go_to_next_step
from core.file_handlers import load_tsv_file, get_spectral_columns
from utils.validators import validate_wstd_measurements
from utils.plotting import plot_wstd_spectra


def render_wstd_step():
    """
    Renderiza el paso de diagnostico inicial con WSTD (Paso 1).
    """
    st.markdown("## PASO 3 DE 7: Diagnostico Inicial")
    st.markdown(INSTRUCTIONS['wstd'])
    st.markdown("---")
    
    wstd_file = st.file_uploader(
        "Sube el archivo TSV con las mediciones de WSTD", 
        type="tsv", 
        key="wstd_upload"
    )
    
    # Marcar cambios sin guardar si se sube archivo
    if wstd_file:
        st.session_state.unsaved_changes = True
    
    col_skip1, col_skip2 = st.columns([3, 1])
    with col_skip2:
        if st.button("Omitir paso", key="skip_step1"):
            st.session_state.unsaved_changes = False  # Limpiar flag tambi¨¦n al omitir
            go_to_next_step()
    
    if wstd_file:
        try:
            df = load_tsv_file(wstd_file)
            df_wstd = df[df["ID"].str.upper() == SPECIAL_IDS['wstd']].copy()
            
            if len(df_wstd) == 0:
                st.error(MESSAGES['error_no_wstd'])
                st.info("Verifica que hayas etiquetado correctamente las mediciones del White Standard.")
                return
            
            spectral_cols = get_spectral_columns(df)
            df_wstd[spectral_cols] = df_wstd[spectral_cols].apply(pd.to_numeric, errors="coerce")
            lamps = [lamp for lamp in df_wstd["Note"].unique() if pd.notna(lamp)]
            
            if not validate_wstd_measurements(df_wstd, lamps):
                return
            
            st.success(MESSAGES['success_file_loaded'])
            st.write(f"**Mediciones WSTD encontradas:** {len(df_wstd)}")
            st.write(f"**Lamparas detectadas:** {', '.join(lamps)}")
            st.write(f"**Canales espectrales:** {len(spectral_cols)}")
            
            df_wstd_grouped = df_wstd.groupby("Note")[spectral_cols].mean()
            
            st.markdown("### Diagnostico Visual")
            fig = plot_wstd_spectra(df_wstd_grouped, spectral_cols, lamps)
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("### Metricas de Diagnostico")
            render_diagnostic_metrics(df_wstd_grouped, lamps)
            
            save_wstd_data(
                df=df_wstd,
                grouped=df_wstd_grouped,
                spectral_cols=spectral_cols,
                lamps=lamps
            )
            
            # Bot¨®n de navegaci¨®n
            st.markdown("---")
            if st.button("Continuar al Paso 4", type="primary", use_container_width=True):
                st.session_state.unsaved_changes = False  # Limpiar flag
                go_to_next_step()
                
        except Exception as e:
            st.error(f"Error al procesar el archivo: {str(e)}")


def render_diagnostic_metrics(df_wstd_grouped, lamps):
    """
    Renderiza las metricas de diagnostico para cada lampara.
    """
    cols = st.columns(len(df_wstd_grouped))
    
    for i, lamp in enumerate(df_wstd_grouped.index):
        spectrum = df_wstd_grouped.loc[lamp].values
        
        with cols[i]:
            st.markdown(f"**{lamp}**")
            
            max_val = np.max(np.abs(spectrum))
            mean_val = np.mean(np.abs(spectrum))
            std_val = np.std(spectrum)
            
            st.metric("Desv. maxima", f"{max_val:.4f}")
            st.metric("Desv. media", f"{mean_val:.4f}")
            st.metric("Desv. estandar", f"{std_val:.4f}")
            
            status = get_diagnostic_status(max_val)
            display_diagnostic_status(status)


def get_diagnostic_status(max_deviation):
    """
    Determina el estado del diagnostico basado en la desviacion maxima.
    """
    if max_deviation < WSTD_THRESHOLDS['good']:
        return 'good'
    elif max_deviation < WSTD_THRESHOLDS['warning']:
        return 'warning'
    else:
        return 'bad'


def display_diagnostic_status(status):
    """
    Muestra el estado del diagnostico con el formato apropiado.
    """
    status_config = DIAGNOSTIC_STATUS[status]
    icon = status_config['icon']
    label = status_config['label']
    color = status_config['color']
    
    if color == 'green':
        st.success(f"{icon} {label}")
    elif color == 'warning':
        st.warning(f"{icon} {label}")
    else:
        st.error(f"{icon} {label}")