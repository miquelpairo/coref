"""
Paso 2: Diagnóstico WSTD (White Standard)
"""
import streamlit as st
import pandas as pd
import numpy as np
import io
from config import INSTRUCTIONS, MESSAGES, SPECIAL_IDS, WSTD_THRESHOLDS, DIAGNOSTIC_STATUS
from session_manager import save_wstd_data, go_to_next_step
from core.file_handlers import load_tsv_file, get_spectral_columns
from utils.validators import validate_wstd_measurements
from utils.plotting import plot_wstd_spectra, plot_wstd_difference


def render_wstd_step():
    """
    Renderiza el paso de diagnóstico inicial con WSTD (Paso 1).
    """
    st.markdown("## 📍 PASO 1 DE 5: Diagnóstico Inicial")
    st.markdown(INSTRUCTIONS['wstd'])

    st.markdown("---")
    wstd_file = st.file_uploader(
        "📁 Sube el archivo TSV con las mediciones de WSTD", 
        type="tsv", 
        key="wstd_upload"
    )

    col_skip1, col_skip2 = st.columns([3, 1])
    with col_skip2:
        if st.button("⏭️ Omitir paso", key="skip_step1"):
            go_to_next_step()

    if wstd_file:
        try:
            # Cargar archivo
            df = load_tsv_file(wstd_file)
            
            # Filtrar mediciones WSTD
            df_wstd = df[df["ID"].str.upper() == SPECIAL_IDS['wstd']].copy()
            
            if len(df_wstd) == 0:
                st.error(MESSAGES['error_no_wstd'])
                st.info("Verifica que hayas etiquetado correctamente las mediciones del White Standard.")
                return
            
            # Obtener columnas espectrales
            spectral_cols = get_spectral_columns(df)
            
            # Convertir columnas espectrales a numérico
            df_wstd[spectral_cols] = df_wstd[spectral_cols].apply(pd.to_numeric, errors="coerce")
            
            # Obtener lámparas
            lamps = [lamp for lamp in df_wstd["Note"].unique() if pd.notna(lamp)]
            
            # Validación básica
            if not validate_wstd_measurements(df_wstd, lamps):
                return
            
            # Mostrar información básica
            st.success(MESSAGES['success_file_loaded'])
            st.write(f"**Mediciones WSTD encontradas:** {len(df_wstd)}")
            st.write(f"**Lámparas detectadas:** {', '.join(lamps)}")
            st.write(f"**Canales espectrales:** {len(spectral_cols)}")
            
            # Agrupar por lámpara
            df_wstd_grouped = df_wstd.groupby("Note")[spectral_cols].mean()
            
            # Visualización
            st.markdown("### 📊 Diagnóstico Visual")
            fig = plot_wstd_spectra(df_wstd_grouped, spectral_cols, lamps)
            st.pyplot(fig)
            
            # Métricas de diagnóstico
            st.markdown("### 📈 Métricas de Diagnóstico")
            render_diagnostic_metrics(df_wstd_grouped, lamps)
            
            # Guardar datos
            save_wstd_data(
                df=df_wstd,
                grouped=df_wstd_grouped,
                spectral_cols=spectral_cols,
                lamps=lamps
            )
            
            st.markdown("---")
            if st.button("➡️ Continuar al Paso 2", type="primary", use_container_width=True):
                go_to_next_step()
                
        except Exception as e:
            st.error(f"❌ Error al procesar el archivo: {str(e)}")


def render_diagnostic_metrics(df_wstd_grouped, lamps):
    """
    Renderiza las métricas de diagnóstico para cada lámpara.
    
    Args:
        df_wstd_grouped (pd.DataFrame): DataFrame agrupado por lámpara
        lamps (list): Lista de nombres de lámparas
    """
    cols = st.columns(len(df_wstd_grouped))
    
    for i, lamp in enumerate(df_wstd_grouped.index):
        spectrum = df_wstd_grouped.loc[lamp].values
        
        with cols[i]:
            st.markdown(f"**{lamp}**")
            
            # Calcular métricas
            max_val = np.max(np.abs(spectrum))
            mean_val = np.mean(np.abs(spectrum))
            std_val = np.std(spectrum)
            
            # Mostrar métricas
            st.metric("Desv. máxima", f"{max_val:.4f}")
            st.metric("Desv. media", f"{mean_val:.4f}")
            st.metric("Desv. estándar", f"{std_val:.4f}")
            
            # Estado del diagnóstico
            status = get_diagnostic_status(max_val)
            display_diagnostic_status(status)


def get_diagnostic_status(max_deviation):
    """
    Determina el estado del diagnóstico basado en la desviación máxima.
    
    Args:
        max_deviation (float): Desviación máxima absoluta
        
    Returns:
        str: Estado ('good', 'warning', o 'bad')
    """
    if max_deviation < WSTD_THRESHOLDS['good']:
        return 'good'
    elif max_deviation < WSTD_THRESHOLDS['warning']:
        return 'warning'
    else:
        return 'bad'


def display_diagnostic_status(status):
    """
    Muestra el estado del diagnóstico con el formato apropiado.
    
    Args:
        status (str): Estado del diagnóstico ('good', 'warning', 'bad')
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
