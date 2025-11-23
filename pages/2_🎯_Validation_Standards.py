"""
Standard Validation Tool
========================
Herramienta dedicada para validación de estándares ópticos NIR.
Verifica alineamiento espectral post-mantenimiento.


"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List, Tuple
import sys
from pathlib import Path
from datetime import datetime

# Añadir directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from core.file_handlers import load_tsv_file, get_spectral_columns
from auth import check_password
from buchi_streamlit_theme import apply_buchi_styles

apply_buchi_styles()

# Corregir estilos del sidebar para mejor contraste
st.markdown("""
<style>
    /* Sidebar general */
    [data-testid="stSidebar"] {
        background-color: #2c5f3f;
    }
    
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    
    /* Headers y títulos */
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: white !important;
    }
    
    /* Labels - completamente invisibles, solo texto blanco */
    [data-testid="stSidebar"] label {
        color: white !important;
        font-weight: 500 !important;
        font-size: 14px !important;
        margin-bottom: 8px !important;
        display: block !important;
        background: none !important;
        border: none !important;
        padding: 0 !important;
        box-shadow: none !important;
    }
    
    /* CRÍTICO: Eliminar borde verde de label de file uploader */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] > label,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] label {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
    }
    
    /* File uploader - contenedor principal */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] {
        width: 100% !important;
        margin-bottom: 20px !important;
    }
    
    /* Área de drop - diseño limpio y compacto */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section {
        background-color: rgba(255, 255, 255, 0.1) !important;
        border: 2px dashed rgba(255, 255, 255, 0.3) !important;
        border-radius: 8px !important;
        padding: 20px !important;
        text-align: center !important;
        width: 100% !important;
        box-sizing: border-box !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section:hover {
        border-color: rgba(255, 255, 255, 0.5) !important;
        background-color: rgba(255, 255, 255, 0.15) !important;
    }
    
    /* Texto "Drag and drop" */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] small {
        color: rgba(255, 255, 255, 0.8) !important;
        font-size: 13px !important;
    }
    
    /* Botón "Browse files" - Verde Buchi */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button[kind="secondary"] {
        background-color: #7cb342 !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 8px 20px !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        margin-top: 10px !important;
        cursor: pointer !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button[kind="secondary"]:hover {
        background-color: #689f38 !important;
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(0,0,0,0.2) !important;
    }
    
    /* Archivo cargado - estilo badge */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid="stMarkdownContainer"] {
        background-color: rgba(124, 179, 66, 0.2) !important;
        border: 1px solid #7cb342 !important;
        border-radius: 6px !important;
        padding: 10px 12px !important;
        margin-top: 10px !important;
        color: white !important;
        font-size: 13px !important;
    }
    
    /* Botón X para eliminar - más visible */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button[kind="icon"] {
        color: #ff5252 !important;
        background-color: rgba(255, 82, 82, 0.1) !important;
        border-radius: 4px !important;
        padding: 4px !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button[kind="icon"]:hover {
        background-color: rgba(255, 82, 82, 0.2) !important;
        color: #ff1744 !important;
    }
    
    /* Dividers */
    [data-testid="stSidebar"] hr {
        border-color: rgba(255, 255, 255, 0.2) !important;
        margin: 20px 0 !important;
    }
    
    /* Expander */
    [data-testid="stSidebar"] [data-testid="stExpander"] {
        background-color: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stExpander"] summary {
        color: white !important;
    }
    
    /* Info boxes */
    [data-testid="stSidebar"] .stAlert {
        background-color: rgba(124, 179, 66, 0.15) !important;
        border: 1px solid rgba(124, 179, 66, 0.3) !important;
        border-radius: 8px !important;
        color: white !important;
    }
    
    /* Inputs - FONDO BLANCO con texto oscuro */
    [data-testid="stSidebar"] input[type="number"],
    [data-testid="stSidebar"] input[type="text"] {
        background-color: white !important;
        color: #333333 !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        border-radius: 6px !important;
        padding: 8px 12px !important;
    }
    
    [data-testid="stSidebar"] input[type="number"]:focus,
    [data-testid="stSidebar"] input[type="text"]:focus {
        border-color: #7cb342 !important;
        box-shadow: 0 0 0 1px #7cb342 !important;
    }
    
    /* Selects */
    [data-testid="stSidebar"] select {
        background-color: white !important;
        color: #333333 !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        border-radius: 6px !important;
    }
    
    /* Number input - botones +/- GRISES OSCUROS sobre blanco */
    [data-testid="stSidebar"] button[kind="icon"] svg {
        color: #333333 !important;
        fill: #333333 !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stNumberInput"] button {
        background-color: #f0f0f0 !important;
        color: #333333 !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stNumberInput"] button:hover {
        background-color: #e0e0e0 !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stNumberInput"] button svg {
        color: #333333 !important;
        fill: #333333 !important;
    }
</style>
""", unsafe_allow_html=True)

if not check_password():
    st.stop()

# ============================================================================
# CONFIGURACIÓN DE UMBRALES
# ============================================================================

DEFAULT_THRESHOLDS = {
    'correlation': 0.999,
    'max_diff': 0.02,
    'rms': 0.015
}

CRITICAL_REGIONS = [(1100, 1200), (1400, 1500), (1600, 1700)]

# ============================================================================
# FUNCIONES DE VALIDACIÓN
# ============================================================================

def validate_standard(reference: np.ndarray, current: np.ndarray, 
                     thresholds: Dict) -> Dict:
    """
    Valida un estándar comparando medición actual vs referencia.
    
    Returns:
        Dict con métricas y veredicto
    """
    # Asegurar que son float
    reference = np.asarray(reference, dtype=np.float64)
    current = np.asarray(current, dtype=np.float64)
    
    # 1. Correlación espectral
    ref_norm = (reference - np.mean(reference)) / (np.std(reference) + 1e-10)
    curr_norm = (current - np.mean(current)) / (np.std(current) + 1e-10)
    correlation = np.sum(ref_norm * curr_norm) / len(ref_norm)
    
    # 2. Diferencias
    diff = current - reference
    max_diff = np.abs(diff).max()
    rms = np.sqrt(np.mean(diff**2))
    mean_diff = np.mean(diff)
    
    # 3. Evaluación contra umbrales
    checks = {
        'correlation': correlation >= thresholds['correlation'],
        'max_diff': max_diff <= thresholds['max_diff'],
        'rms': rms <= thresholds['rms']
    }
    
    all_pass = all(checks.values())
    
    return {
        'correlation': correlation,
        'max_diff': max_diff,
        'rms': rms,
        'mean_diff': mean_diff,
        'checks': checks,
        'pass': all_pass,
        'diff': diff
    }


def detect_spectral_shift(reference: np.ndarray, current: np.ndarray, 
                         window: int = 5) -> Tuple[bool, float]:
    """
    Detecta si hay un shift sistemático en longitud de onda.
    
    Returns:
        (tiene_shift, magnitud_promedio_shift)
    """
    # Calcular correlación cruzada
    correlation = np.correlate(reference, current, mode='same')
    peak_pos = np.argmax(correlation)
    center = len(correlation) // 2
    
    shift = peak_pos - center
    
    # Si shift > window píxeles, considerarlo significativo
    has_shift = abs(shift) > window
    
    return has_shift, float(shift)


def find_common_ids(df_ref: pd.DataFrame, df_curr: pd.DataFrame) -> pd.DataFrame:
    """
    Encuentra IDs comunes entre referencia y actual, emparejando solo por ID.
    Si hay múltiples filas con el mismo ID, toma la primera.
    
    Returns:
        DataFrame con columnas: ID, ref_note, curr_note, ref_idx, curr_idx
    """
    # Validar que los DataFrames no están vacíos
    if len(df_ref) == 0 or len(df_curr) == 0:
        return pd.DataFrame(columns=['ID', 'ref_note', 'curr_note', 'ref_idx', 'curr_idx'])
    
    # Validar que tienen columna 'ID'
    if 'ID' not in df_ref.columns or 'ID' not in df_curr.columns:
        return pd.DataFrame(columns=['ID', 'ref_note', 'curr_note', 'ref_idx', 'curr_idx'])
    
    # Validar que tienen columna 'Note'
    if 'Note' not in df_ref.columns or 'Note' not in df_curr.columns:
        return pd.DataFrame(columns=['ID', 'ref_note', 'curr_note', 'ref_idx', 'curr_idx'])
    
    # Crear listas para almacenar los resultados
    ref_data = []
    for id_val in df_ref['ID'].unique():
        if pd.isna(id_val):  # Saltar IDs nulos
            continue
        mask = df_ref['ID'] == id_val
        indices = df_ref[mask].index
        if len(indices) > 0:
            first_idx = indices[0]
            ref_data.append({
                'ID': id_val,
                'ref_note': df_ref.loc[first_idx, 'Note'] if 'Note' in df_ref.columns else '',
                'ref_idx': first_idx
            })
    
    curr_data = []
    for id_val in df_curr['ID'].unique():
        if pd.isna(id_val):  # Saltar IDs nulos
            continue
        mask = df_curr['ID'] == id_val
        indices = df_curr[mask].index
        if len(indices) > 0:
            first_idx = indices[0]
            curr_data.append({
                'ID': id_val,
                'curr_note': df_curr.loc[first_idx, 'Note'] if 'Note' in df_curr.columns else '',
                'curr_idx': first_idx
            })
    
    # Validar que encontramos datos
    if len(ref_data) == 0 or len(curr_data) == 0:
        return pd.DataFrame(columns=['ID', 'ref_note', 'curr_note', 'ref_idx', 'curr_idx'])
    
    # Crear DataFrames
    df_ref_ids = pd.DataFrame(ref_data)
    df_curr_ids = pd.DataFrame(curr_data)
    
    # Hacer merge solo por ID
    matches = df_ref_ids.merge(df_curr_ids, on='ID', how='inner')
    
    return matches[['ID', 'ref_note', 'curr_note', 'ref_idx', 'curr_idx']]

def analyze_critical_regions(reference: np.ndarray, current: np.ndarray,
                            regions: List[Tuple[int, int]], 
                            num_channels: int) -> pd.DataFrame:
    """
    Analiza diferencias en regiones espectrales críticas.
    Asume rango 900-1700 nm para 256 píxeles.
    """
    wavelength_per_pixel = 800 / num_channels  # (1700-900)/256
    start_wl = 900
    end_wl = 1700
    
    results = []
    
    for wl_start, wl_end in regions:
        # Verificar si la región está dentro del rango del instrumento
        if wl_end < start_wl or wl_start > end_wl:
            results.append({
                'Región (nm)': f"{wl_start}-{wl_end}",
                'Canales': "Fuera de rango",
                'Max |Δ|': "N/A",
                'RMS': "N/A",
                'Media Δ': "N/A"
            })
            continue
        
        # Ajustar región a los límites del instrumento
        wl_start_adjusted = max(wl_start, start_wl)
        wl_end_adjusted = min(wl_end, end_wl)
        
        # Convertir wavelength a índices de píxel
        px_start = int((wl_start_adjusted - start_wl) / wavelength_per_pixel)
        px_end = int((wl_end_adjusted - start_wl) / wavelength_per_pixel)
        
        px_start = max(0, px_start)
        px_end = min(num_channels, px_end)
        
        # Verificar que hay al menos algunos píxeles en la región
        if px_end <= px_start:
            results.append({
                'Región (nm)': f"{wl_start}-{wl_end}",
                'Canales': "Región muy pequeña",
                'Max |Δ|': "N/A",
                'RMS': "N/A",
                'Media Δ': "N/A"
            })
            continue
        
        # Extraer región
        ref_region = reference[px_start:px_end]
        curr_region = current[px_start:px_end]
        
        # Calcular métricas
        diff_region = curr_region - ref_region
        
        region_label = f"{wl_start}-{wl_end}"
        if wl_start_adjusted != wl_start or wl_end_adjusted != wl_end:
            region_label += f" *"  # Asterisco si fue ajustado
        
        results.append({
            'Región (nm)': region_label,
            'Canales': f"{px_start}-{px_end}",
            'Max |Δ|': f"{np.abs(diff_region).max():.6f}",
            'RMS': f"{np.sqrt(np.mean(diff_region**2)):.6f}",
            'Media Δ': f"{np.mean(diff_region):.6f}"
        })
    
    return pd.DataFrame(results)


# ============================================================================
# VISUALIZACIONES
# ============================================================================

def create_validation_plot(reference: np.ndarray, current: np.ndarray,
                          diff: np.ndarray, sample_label: str) -> go.Figure:
    """Crea gráfico de 3 paneles para validación."""
    
    channels = list(range(1, len(reference) + 1))
    
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=(
            f'Espectros: Referencia vs Actual ({sample_label})',
            'Diferencia (Actual - Referencia)',
            'Diferencia Acumulada'
        ),
        vertical_spacing=0.1,
        row_heights=[0.4, 0.3, 0.3]
    )
    
    # Panel 1: Overlay
    fig.add_trace(
        go.Scatter(x=channels, y=reference, name='Referencia',
                  line=dict(color='blue', width=2)),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=channels, y=current, name='Actual',
                  line=dict(color='red', width=2, dash='dash')),
        row=1, col=1
    )
    
    # Panel 2: Diferencia
    fig.add_trace(
        go.Scatter(x=channels, y=diff, name='Δ',
                  line=dict(color='green', width=2),
                  fill='tozeroy', fillcolor='rgba(0,255,0,0.1)'),
        row=2, col=1
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray", 
                  opacity=0.5, row=2, col=1)
    
    # Panel 3: Diferencia acumulada
    cumsum_diff = np.cumsum(diff)
    fig.add_trace(
        go.Scatter(x=channels, y=cumsum_diff, name='Σ Δ',
                  line=dict(color='purple', width=2)),
        row=3, col=1
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray", 
                  opacity=0.5, row=3, col=1)
    
    fig.update_xaxes(title_text="Canal espectral", row=3, col=1)
    fig.update_yaxes(title_text="Absorbancia", row=1, col=1)
    fig.update_yaxes(title_text="Δ Absorbancia", row=2, col=1)
    fig.update_yaxes(title_text="Σ Δ", row=3, col=1)
    
    fig.update_layout(
        height=900,
        showlegend=True,
        template='plotly_white',
        hovermode='x unified'
    )
    
    return fig


# ============================================================================
# INTERFAZ PRINCIPAL
# ============================================================================

def main():
    st.title("🎯 Standard Validation Tool")
    st.markdown("**Validación automática de estándares ópticos post-mantenimiento**")
    st.divider()
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuración")
        
        # Upload de archivos
        ref_file = st.file_uploader(
            "📁 Referencia pre-mantenimiento (TSV)",
            type=['tsv'],
            help="Mediciones de estándares antes del mantenimiento"
        )
        
        curr_file = st.file_uploader(
            "📁 Medición post-mantenimiento (TSV)",
            type=['tsv'],
            help="Mediciones de estándares después del mantenimiento"
        )
        
        st.divider()
        
        # Ajuste de umbrales
        with st.expander("🎚️ Ajustar Umbrales"):
            corr_threshold = st.number_input(
                "Correlación mínima:",
                min_value=0.990,
                max_value=1.000,
                value=DEFAULT_THRESHOLDS['correlation'],
                step=0.001,
                format="%.3f"
            )
            
            max_diff_threshold = st.number_input(
                "Diferencia máxima (AU):",
                min_value=0.001,
                max_value=0.100,
                value=DEFAULT_THRESHOLDS['max_diff'],
                step=0.001,
                format="%.3f"
            )
            
            rms_threshold = st.number_input(
                "RMS máximo:",
                min_value=0.001,
                max_value=0.100,
                value=DEFAULT_THRESHOLDS['rms'],
                step=0.001,
                format="%.3f"
            )
            
            thresholds = {
                'correlation': corr_threshold,
                'max_diff': max_diff_threshold,
                'rms': rms_threshold
            }
        
        if 'thresholds' not in locals():
            thresholds = DEFAULT_THRESHOLDS
        
        st.divider()
        st.markdown("""
        **Regiones críticas:**
        - 1100-1200 nm (O-H)
        - 1400-1500 nm (Humedad)
        - 1600-1700 nm (C-H)
        """)
    
    # Área principal
    if not ref_file or not curr_file:
        st.info("👈 Carga ambos archivos para comenzar la validación automática")
        
        st.markdown("""
        ### Funcionamiento:
        
        1. **Carga archivos TSV** con mediciones de estándares ópticos
        2. **Detección automática** de IDs comunes entre ambos archivos
        3. **Validación de todos los estándares** encontrados
        4. **Tabla resumen** con resultados y análisis detallado
        
        **Umbrales por defecto:**
        - Correlación espectral: ≥ 0.999
        - Diferencia máxima: ≤ 0.02 AU
        - RMS: ≤ 0.015
        """)
        
        return
    
    # Cargar archivos
    try:
        with st.spinner("Cargando archivos y detectando estándares comunes..."):
            df_ref = load_tsv_file(ref_file)
            df_curr = load_tsv_file(curr_file)
            
            spectral_cols_ref = get_spectral_columns(df_ref)
            spectral_cols_curr = get_spectral_columns(df_curr)
            
            if len(spectral_cols_ref) != len(spectral_cols_curr):
                st.error("❌ Los archivos tienen diferente número de canales espectrales")
                return
            
            num_channels = len(spectral_cols_ref)
            
            # Encontrar IDs comunes
            matches = find_common_ids(df_ref, df_curr)
            
            if len(matches) == 0:
                st.error("❌ No se encontraron IDs comunes entre los archivos")
                st.info("💡 Asegúrate de que los campos ID y Note coinciden en ambos archivos")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("IDs en Referencia")
                    st.dataframe(df_ref[['ID', 'Note']], use_container_width=True)
                with col2:
                    st.subheader("IDs en Actual")
                    st.dataframe(df_curr[['ID', 'Note']], use_container_width=True)
                
                return
            
            st.success(f"✅ {len(matches)} estándar(es) común(es) detectado(s)")
            
    except Exception as e:
        st.error(f"❌ Error al cargar archivos: {str(e)}")
        return
    
    st.divider()
    
    # VALIDACIÓN AUTOMÁTICA DE TODOS LOS ESTÁNDARES
    st.header("📊 Resultados de Validación")
    
    all_results = []
    all_validation_data = []  # Para guardar datos completos para análisis detallado
    
    with st.spinner(f"Validando {len(matches)} estándar(es)..."):
        for idx, row in matches.iterrows():
            sample_id = row['ID']
            ref_note = row['ref_note']
            curr_note = row['curr_note']
            ref_idx = row['ref_idx']
            curr_idx = row['curr_idx']
            
            # Extraer espectros
            reference = df_ref.loc[ref_idx, spectral_cols_ref].astype(float).values
            current = df_curr.loc[curr_idx, spectral_cols_curr].astype(float).values
            
            # Validar
            validation_results = validate_standard(reference, current, thresholds)
            has_shift, shift_magnitude = detect_spectral_shift(reference, current)
            
            # Determinar estado
            if validation_results['pass'] and not has_shift:
                estado = "✅ OK"
                estado_sort = 0
            elif validation_results['pass'] and has_shift:
                estado = "⚠️ Revisar"
                estado_sort = 1
            else:
                estado = "❌ Fallo"
                estado_sort = 2
            
            all_results.append({
                'Estado': estado,
                '_sort': estado_sort,
                'ID': sample_id,
                'Note (Ref)': ref_note,
                'Note (Actual)': curr_note,
                'Correlación': f"{validation_results['correlation']:.6f}",
                'Max Δ (AU)': f"{validation_results['max_diff']:.6f}",
                'RMS': f"{validation_results['rms']:.6f}",
                'Shift (px)': f"{shift_magnitude:.1f}" if has_shift else "0.0"
            })
            
            # Guardar datos completos para análisis detallado
            all_validation_data.append({
                'id': sample_id,
                'ref_note': ref_note,
                'curr_note': curr_note,
                'reference': reference,
                'current': current,
                'diff': validation_results['diff'],
                'validation_results': validation_results,
                'has_shift': has_shift,
                'shift_magnitude': shift_magnitude
            })
    
    # Crear DataFrame de resultados
    results_df = pd.DataFrame(all_results)
    results_df = results_df.sort_values('_sort').drop('_sort', axis=1)
    
    # Resumen general
    n_ok = sum(1 for r in all_results if r['Estado'] == "✅ OK")
    n_warn = sum(1 for r in all_results if r['Estado'] == "⚠️ Revisar")
    n_fail = sum(1 for r in all_results if r['Estado'] == "❌ Fallo")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Estándares", len(matches))
    with col2:
        st.metric("✅ Validados", n_ok)
    with col3:
        st.metric("⚠️ Revisar", n_warn)
    with col4:
        st.metric("❌ Fallidos", n_fail)
    
    st.divider()
    
    # Tabla resumen
    st.subheader("Resumen de Validaciones")
    st.dataframe(results_df, use_container_width=True, hide_index=True)
    
    # Exportar resumen
    csv = results_df.to_csv(index=False)
    st.download_button(
        label="📥 Descargar Resumen (CSV)",
        data=csv,
        file_name=f"validation_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )
    
    st.divider()
    
    # Análisis detallado por estándar
    st.subheader("Análisis Detallado por Estándar")

    # Filtro de búsqueda
    search_filter = st.text_input(
        "🔍 Buscar estándar por ID:",
        placeholder="Escribe para filtrar...",
        help="Filtra la lista de estándares por ID"
    )

    # Filtrar lista según búsqueda
    if search_filter:
        filtered_indices = [
            i for i in range(len(all_validation_data))
            if search_filter.lower() in str(all_validation_data[i]['id']).lower()
        ]
    else:
        filtered_indices = list(range(len(all_validation_data)))

    if len(filtered_indices) == 0:
        st.warning("⚠️ No se encontraron estándares que coincidan con la búsqueda")
        return

    # Mostrar cuántos resultados
    if search_filter:
        st.caption(f"Mostrando {len(filtered_indices)} de {len(all_validation_data)} estándares")

    # Selector con lista filtrada
    selected_sample_filtered = st.selectbox(
        "Selecciona estándar:",
        filtered_indices,
        format_func=lambda x: f"{all_validation_data[x]['id']} - {all_validation_data[x]['ref_note']}",
        key="sample_selector"
    )

    sample_data = all_validation_data[selected_sample_filtered]
    
    # Tabs de análisis detallado
    tab1, tab2, tab3 = st.tabs([
        "📈 Gráficos",
        "📋 Regiones Críticas",
        "📄 Métricas"
    ])
    
    with tab1:
        sample_label = f"{sample_data['id']} (Ref: {sample_data['ref_note']} | Act: {sample_data['curr_note']})"
        fig = create_validation_plot(
            sample_data['reference'],
            sample_data['current'],
            sample_data['diff'],
            sample_label
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        regions_df = analyze_critical_regions(
            sample_data['reference'],
            sample_data['current'],
            CRITICAL_REGIONS,
            num_channels
        )
        st.dataframe(regions_df, use_container_width=True, hide_index=True)
        st.caption("* = Región ajustada a rango del instrumento (900-1700 nm)")
    
    with tab3:
        val_res = sample_data['validation_results']
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Métricas Calculadas")
            metrics_data = {
                'Métrica': ['Correlación', 'Max Diferencia', 'RMS', 'Media Δ', 'Shift Espectral'],
                'Valor': [
                    f"{val_res['correlation']:.6f}",
                    f"{val_res['max_diff']:.6f} AU",
                    f"{val_res['rms']:.6f}",
                    f"{val_res['mean_diff']:.6f}",
                    f"{sample_data['shift_magnitude']:.1f} px" if sample_data['has_shift'] else "No detectado"
                ]
            }
            st.dataframe(pd.DataFrame(metrics_data), use_container_width=True, hide_index=True)
        
        with col2:
            st.markdown("### Evaluación")
            checks_data = {
                'Criterio': ['Correlación', 'Diferencia Máxima', 'RMS'],
                'Umbral': [
                    f"≥ {thresholds['correlation']}",
                    f"≤ {thresholds['max_diff']} AU",
                    f"≤ {thresholds['rms']}"
                ],
                'Estado': [
                    "✅ OK" if val_res['checks']['correlation'] else "❌ Fallo",
                    "✅ OK" if val_res['checks']['max_diff'] else "❌ Fallo",
                    "✅ OK" if val_res['checks']['rms'] else "❌ Fallo"
                ]
            }
            st.dataframe(pd.DataFrame(checks_data), use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()