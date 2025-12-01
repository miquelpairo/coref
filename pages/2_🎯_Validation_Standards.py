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
from config import DEFAULT_VALIDATION_THRESHOLDS, CRITICAL_REGIONS, OFFSET_LIMITS

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
    
    /* Number input - botones +/- GRISES OSCUROS sobre blanco */
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


def create_overlay_plot(validation_data: List[Dict], show_reference: bool = True,
                       show_current: bool = True) -> go.Figure:
    """
    Crea gráfico con overlay de todos los espectros de validación.
    
    Args:
        validation_data: Lista de diccionarios con datos de validación
        show_reference: Si True, muestra espectros de referencia
        show_current: Si True, muestra espectros actuales
    """
    colors_ref = ['#1f77b4', '#2ca02c', '#9467bd', '#8c564b', '#e377c2', 
                  '#7f7f7f', '#bcbd22', '#17becf', '#ff9896', '#c5b0d5']
    colors_curr = ['#ff7f0e', '#d62728', '#ff69b4', '#ffa500', '#dc143c',
                   '#ff4500', '#ff1493', '#ff6347', '#ff8c00', '#ff00ff']
    
    fig = go.Figure()
    
    if len(validation_data) == 0:
        return fig
    
    channels = list(range(1, len(validation_data[0]['reference']) + 1))
    
    # Añadir espectros de referencia
    if show_reference:
        for i, data in enumerate(validation_data):
            color = colors_ref[i % len(colors_ref)]
            sample_label = f"{data['id']} - Ref"
            
            fig.add_trace(go.Scatter(
                x=channels,
                y=data['reference'],
                mode='lines',
                name=sample_label,
                line=dict(color=color, width=2),
                legendgroup='reference',
                hovertemplate=f'<b>{sample_label}</b><br>' +
                             'Canal: %{x}<br>' +
                             'Absorbancia: %{y:.6f}<br>' +
                             '<extra></extra>'
            ))
    
    # Añadir espectros actuales
    if show_current:
        for i, data in enumerate(validation_data):
            color = colors_curr[i % len(colors_curr)]
            sample_label = f"{data['id']} - Act"
            
            fig.add_trace(go.Scatter(
                x=channels,
                y=data['current'],
                mode='lines',
                name=sample_label,
                line=dict(color=color, width=2, dash='dash'),
                legendgroup='current',
                hovertemplate=f'<b>{sample_label}</b><br>' +
                             'Canal: %{x}<br>' +
                             'Absorbancia: %{y:.6f}<br>' +
                             '<extra></extra>'
            ))
    
    fig.update_layout(
        title={
            'text': 'Comparación Global de Todos los Estándares',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20, 'color': '#2c5f3f'}
        },
        xaxis_title='Canal espectral',
        yaxis_title='Absorbancia',
        hovermode='closest',
        template='plotly_white',
        height=600,
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            font=dict(size=10)
        )
    )
    
    return fig


def create_global_statistics_table(validation_data: List[Dict]) -> pd.DataFrame:
    """
    Crea tabla con estadísticas globales de todos los estándares.
    """
    if len(validation_data) == 0:
        return pd.DataFrame()
    
    # Recopilar métricas de todos los estándares
    all_correlations = []
    all_max_diffs = []
    all_rms = []
    all_mean_diffs = []
    
    for data in validation_data:
        val_res = data['validation_results']
        all_correlations.append(val_res['correlation'])
        all_max_diffs.append(val_res['max_diff'])
        all_rms.append(val_res['rms'])
        all_mean_diffs.append(val_res['mean_diff'])
    
    # Calcular estadísticas
    stats = {
        'Métrica': ['Correlación', 'Max Diferencia (AU)', 'RMS', 'Offset Medio (AU)'],
        'Mínimo': [
            f"{min(all_correlations):.6f}",
            f"{min(all_max_diffs):.6f}",
            f"{min(all_rms):.6f}",
            f"{min(all_mean_diffs):.6f}"
        ],
        'Máximo': [
            f"{max(all_correlations):.6f}",
            f"{max(all_max_diffs):.6f}",
            f"{max(all_rms):.6f}",
            f"{max(all_mean_diffs):.6f}"
        ],
        'Media': [
            f"{np.mean(all_correlations):.6f}",
            f"{np.mean(all_max_diffs):.6f}",
            f"{np.mean(all_rms):.6f}",
            f"{np.mean(all_mean_diffs):.6f}"
        ],
        'Desv. Est.': [
            f"{np.std(all_correlations):.6f}",
            f"{np.std(all_max_diffs):.6f}",
            f"{np.std(all_rms):.6f}",
            f"{np.std(all_mean_diffs):.6f}"
        ]
    }
    
    return pd.DataFrame(stats)


# ============================================================================
# INTERFAZ PRINCIPAL
# ============================================================================

def main():
    st.title("🎯 Standard Validation Tool")
    st.markdown("**Validación automática de estándares ópticos post-mantenimiento**")
    
    # Info inicial
    st.info("""
    Esta herramienta valida que el alineamiento espectral del equipo se mantiene 
    correcto después de realizar mantenimiento (ej: cambio de lámpara).
    
    **Proceso:**
    1. Carga archivos TSV con mediciones antes y después del mantenimiento
    2. Selecciona los estándares a validar
    3. Analiza automáticamente la correlación y diferencias espectrales
    4. Genera informe detallado con resultados
    """)
    
    st.divider()
    
    # Sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Configuración")
        st.markdown("---")
        
        # Ajuste de umbrales
        with st.expander("🎚️ Ajustar Umbrales de Validación"):
            st.caption("Modifica los criterios de aceptación según tus necesidades")
            
            corr_threshold = st.number_input(
                "Correlación mínima:",
                min_value=0.990,
                max_value=1.000,
                value=DEFAULT_VALIDATION_THRESHOLDS['correlation'],
                step=0.001,
                format="%.3f",
                help="Similitud espectral mínima aceptable (valores cercanos a 1.0 = alta similitud)"
            )
            
            max_diff_threshold = st.number_input(
                "Diferencia máxima (AU):",
                min_value=0.001,
                max_value=0.100,
                value=DEFAULT_VALIDATION_THRESHOLDS['max_diff'],
                step=0.001,
                format="%.3f",
                help="Máxima desviación puntual permitida en absorbancia"
            )
            
            rms_threshold = st.number_input(
                "RMS máximo:",
                min_value=0.001,
                max_value=0.100,
                value=DEFAULT_VALIDATION_THRESHOLDS['rms'],
                step=0.001,
                format="%.3f",
                help="Error cuadrático medio máximo aceptable"
            )
            
            thresholds = {
                'correlation': corr_threshold,
                'max_diff': max_diff_threshold,
                'rms': rms_threshold
            }
        
        if 'thresholds' not in locals():
            thresholds = DEFAULT_VALIDATION_THRESHOLDS
        
        st.divider()
        
        # Info de regiones críticas
        with st.expander("ℹ️ Regiones Espectrales Críticas"):
            st.markdown("""
            **Regiones analizadas:**
            - **1100-1200 nm**: Enlaces O-H (hidroxilos)
            - **1400-1500 nm**: Agua / Humedad
            - **1600-1700 nm**: Enlaces C-H (grupos metilo)
            
            Estas regiones son especialmente sensibles a desalineamientos ópticos.
            """)
    
    # ==========================================
    # SECCIÓN: CARGA DE ARCHIVOS TSV
    # ==========================================
    st.markdown("### 📁 Carga de Archivos de Medición")

    st.info("""
    Carga dos archivos TSV con mediciones de estándares ópticos:

    **Uso típico:**
    - **Referencia**: Mediciones con baseline antigua (antes de mantenimiento)
    - **Actual**: Mediciones con baseline nueva (después de mantenimiento)
    """)

    col1, col2 = st.columns(2)

    with col1:
        ref_file = st.file_uploader(
            "Referencia pre-mantenimiento:",
            type=['tsv'],
            key="ref_tsv_validation",
            help="Archivo TSV con mediciones de estándares ANTES del mantenimiento (con baseline antigua)"
        )

    with col2:
        curr_file = st.file_uploader(
            "Medición post-mantenimiento:",
            type=['tsv'],
            key="curr_tsv_validation",
            help="Archivo TSV con mediciones de estándares DESPUÉS del mantenimiento (con baseline nueva)"
        )

    st.divider()
    
    # Área principal
    if not ref_file or not curr_file:
        st.info("👆 Carga ambos archivos para comenzar")
        
        with st.expander("📖 Guía de Uso", expanded=True):
            st.markdown("""
            ### ¿Cómo funciona esta herramienta?
            
            **1. Preparación**
            - Realiza mediciones de estándares ópticos ANTES del mantenimiento
            - Exporta las mediciones como archivo TSV (Referencia)
            
            **2. Mantenimiento**
            - Realiza el cambio de lámpara u otro mantenimiento
            - Instala el nuevo baseline corregido
            
            **3. Verificación**
            - Mide los mismos estándares con el nuevo baseline
            - Exporta las mediciones como archivo TSV (Post-mantenimiento)
            
            **4. Validación Automática**
            - Esta herramienta compara ambos conjuntos de mediciones
            - Detecta desviaciones, correlaciones y shifts espectrales
            - Genera un informe detallado
            
            ---
            
            **Umbrales por defecto:**
            - Correlación espectral: ≥ 0.999
            - Diferencia máxima: ≤ 0.02 AU
            - RMS: ≤ 0.015
            
            Estos valores se pueden ajustar en el panel lateral según tus requisitos.
            """)
        
        return
    
    # Cargar archivos
    try:
        with st.spinner("⏳ Cargando archivos y detectando estándares comunes..."):
            df_ref = load_tsv_file(ref_file)
            df_curr = load_tsv_file(curr_file)
            
            spectral_cols_ref = get_spectral_columns(df_ref)
            spectral_cols_curr = get_spectral_columns(df_curr)
            
            if len(spectral_cols_ref) != len(spectral_cols_curr):
                st.error("❌ Los archivos tienen diferente número de canales espectrales")
                st.info(f"""
                - Archivo referencia: {len(spectral_cols_ref)} canales
                - Archivo actual: {len(spectral_cols_curr)} canales
                
                Ambos archivos deben tener el mismo número de canales espectrales.
                """)
                return
            
            num_channels = len(spectral_cols_ref)
            
            # Encontrar IDs comunes
            matches = find_common_ids(df_ref, df_curr)
            
            if len(matches) == 0:
                st.error("❌ No se encontraron IDs comunes entre los archivos")
                st.info("💡 Verifica que:")
                st.markdown("""
                - Los campos **ID** y **Note** existen en ambos archivos
                - Los IDs utilizados son consistentes entre mediciones
                - Ambas mediciones incluyen los mismos estándares
                """)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("#### IDs en Referencia")
                    if 'ID' in df_ref.columns and 'Note' in df_ref.columns:
                        st.dataframe(df_ref[['ID', 'Note']], use_container_width=True)
                    else:
                        st.warning("Columnas ID o Note no encontradas")
                        
                with col2:
                    st.markdown("#### IDs en Actual")
                    if 'ID' in df_curr.columns and 'Note' in df_curr.columns:
                        st.dataframe(df_curr[['ID', 'Note']], use_container_width=True)
                    else:
                        st.warning("Columnas ID o Note no encontradas")
                
                return
            
        st.success(f"✅ {len(matches)} estándar(es) común(es) detectado(s)")
            
    except Exception as e:
        st.error(f"❌ Error al cargar archivos: {str(e)}")
        with st.expander("🔍 Ver detalles del error"):
            import traceback
            st.code(traceback.format_exc())
        return
    
    st.divider()
    
    # ==========================================
    # SECCIÓN 1: SELECCIÓN DE ESTÁNDARES
    # ==========================================
    st.markdown("### 1️⃣ Selección de Estándares a Validar")
    
    # Inicializar estado de selección
    common_ids = matches['ID'].tolist()

    if 'standards_selected_ids' not in st.session_state:
        st.session_state.standards_selected_ids = common_ids.copy()

    if 'standards_pending_selection' not in st.session_state:
        st.session_state.standards_pending_selection = common_ids.copy()

    # Crear DataFrame para mostrar
    df_samples = pd.DataFrame({
        'ID': common_ids,
        'Note (Ref)': matches['ref_note'].tolist(),
        'Note (Actual)': matches['curr_note'].tolist(),
        'Usar para validación': [
            id_ in st.session_state.standards_pending_selection 
            for id_ in common_ids
        ]
    })

    st.info("""
    Selecciona los estándares que deseas incluir en la validación. 
    Por defecto, todos los estándares comunes están seleccionados.
    """)

    # Usar formulario
    with st.form("form_select_standards_validation", clear_on_submit=False):
        edited = st.data_editor(
            df_samples,
            use_container_width=True,
            hide_index=True,
            disabled=['ID', 'Note (Ref)', 'Note (Actual)'],
            column_config={
                "Usar para validación": st.column_config.CheckboxColumn(
                    "✓ Incluir",
                    help="Marcar para incluir en la validación",
                    default=True,
                )
            },
            key="editor_select_standards_validation"
        )
        
        # Botones dentro del formulario
        col_a, col_b, col_c, col_d = st.columns(4)
        btn_all = col_a.form_submit_button("✅ Todos", use_container_width=True)
        btn_none = col_b.form_submit_button("❌ Ninguno", use_container_width=True)
        btn_invert = col_c.form_submit_button("🔄 Invertir", use_container_width=True)
        btn_confirm = col_d.form_submit_button("🚀 Confirmar Selección", type="primary", use_container_width=True)

    # Manejar acciones de botones
    if btn_all:
        st.session_state.standards_pending_selection = common_ids.copy()
        st.rerun()

    if btn_none:
        st.session_state.standards_pending_selection = []
        st.rerun()

    if btn_invert:
        inverted = [id_ for id_ in common_ids if id_ not in st.session_state.standards_pending_selection]
        st.session_state.standards_pending_selection = inverted
        st.rerun()

    if btn_confirm:
        try:
            pending = edited.loc[edited['Usar para validación'], 'ID'].tolist()
            st.session_state.standards_pending_selection = pending
            st.session_state.standards_selected_ids = pending
            st.session_state['validated'] = True
            st.rerun()
        except Exception as e:
            st.error(f"Error al confirmar selección: {str(e)}")
    else:
        # Actualizar pending mientras se edita
        if isinstance(edited, pd.DataFrame):
            try:
                pending = edited.loc[edited['Usar para validación'], 'ID'].tolist()
                st.session_state.standards_pending_selection = pending
            except Exception:
                pass

    # Mostrar contador
    st.caption(
        f"Pendientes: {len(st.session_state.standards_pending_selection)} - "
        f"Confirmados: {len(st.session_state.get('standards_selected_ids', []))}"
    )

    # Solo proceder si ya se validó
    if 'validated' not in st.session_state or not st.session_state['validated']:
        st.info("👆 Ajusta la selección y presiona **'Confirmar Selección'** para continuar")
        return

    # Recuperar selección guardada
    selected_ids = st.session_state.standards_selected_ids
    matches_filtered = matches[matches['ID'].isin(selected_ids)].copy()

    st.divider()

    # Botón para volver a la selección
    if st.button("🔄 Cambiar Selección de Estándares", use_container_width=False):
        st.session_state['validated'] = False
        st.rerun()
    
    # ==========================================
    # SECCIÓN 2: VALIDACIÓN AUTOMÁTICA
    # ==========================================
    st.markdown("### 2️⃣ Resultados de Validación")
    
    all_results = []
    all_validation_data = []
    
    with st.spinner(f"⏳ Validando {len(matches_filtered)} estándar(es)..."):
        for idx, row in matches_filtered.iterrows():
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
            
            # Guardar datos completos
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
        st.metric("Total Estándares", len(matches_filtered))
    with col2:
        st.metric("✅ Validados", n_ok)
    with col3:
        st.metric("⚠️ Revisar", n_warn)
    with col4:
        st.metric("❌ Fallidos", n_fail)
    
    st.markdown("---")
    
    # Tabla resumen
    st.markdown("#### 📋 Tabla Resumen")
    st.dataframe(results_df, use_container_width=True, hide_index=True)
    
    # Exportar resumen
    csv = results_df.to_csv(index=False)
    st.download_button(
        label="📥 Descargar Resumen (CSV)",
        data=csv,
        file_name=f"validation_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )
    
    st.divider()
    
    # ==========================================
    # SECCIÓN 3: ANÁLISIS GLOBAL
    # ==========================================
    st.markdown("### 3️⃣ Análisis Global")
    
    # Expandable para gráfico overlay
    with st.expander("📊 Vista Global de Todos los Estándares", expanded=False):
        st.info("""
        Comparación simultánea de todos los espectros validados. 
        Las líneas sólidas representan las mediciones de referencia (pre-mantenimiento) 
        y las líneas punteadas las mediciones actuales (post-mantenimiento).
        """)
        
        col1, col2 = st.columns([3, 1])
        
        with col2:
            show_ref = st.checkbox("Mostrar Referencia", value=True, key="show_ref_overlay")
            show_curr = st.checkbox("Mostrar Actual", value=True, key="show_curr_overlay")
        
        overlay_fig = create_overlay_plot(all_validation_data, show_ref, show_curr)
        st.plotly_chart(overlay_fig, use_container_width=True)
    
    # Estadísticas globales
    st.markdown("#### 📈 Estadísticas Globales del Kit")
    st.caption(f"Análisis agregado de {len(all_validation_data)} estándar(es)")
    
    stats_df = create_global_statistics_table(all_validation_data)
    st.dataframe(stats_df, use_container_width=True, hide_index=True)
    
    # Métricas destacadas
    col1, col2, col3 = st.columns(3)
    with col1:
        avg_corr = np.mean([d['validation_results']['correlation'] for d in all_validation_data])
        st.metric(
            "Correlación Media", 
            f"{avg_corr:.6f}", 
            delta="OK" if avg_corr >= thresholds['correlation'] else "Revisar",
            delta_color="normal" if avg_corr >= thresholds['correlation'] else "inverse"
        )
    with col2:
        avg_max_diff = np.mean([d['validation_results']['max_diff'] for d in all_validation_data])
        st.metric(
            "Max Δ Media", 
            f"{avg_max_diff:.6f} AU",
            delta="OK" if avg_max_diff <= thresholds['max_diff'] else "Revisar",
            delta_color="normal" if avg_max_diff <= thresholds['max_diff'] else "inverse"
        )
    with col3:
        avg_rms = np.mean([d['validation_results']['rms'] for d in all_validation_data])
        st.metric(
            "RMS Media", 
            f"{avg_rms:.6f}",
            delta="OK" if avg_rms <= thresholds['rms'] else "Revisar",
            delta_color="normal" if avg_rms <= thresholds['rms'] else "inverse"
        )
    
    st.markdown("---")
    
    # Offset global del kit
    global_offset = np.mean([d['validation_results']['mean_diff'] for d in all_validation_data])
    
    st.metric(
        "🎯 Offset Global del Kit", 
        f"{global_offset:.6f} AU",
        help="Desplazamiento sistemático promedio entre mediciones pre y post-mantenimiento"
    )
    
    if abs(global_offset) < OFFSET_LIMITS['negligible']:
        st.success("✅ Offset despreciable - Excelente alineamiento")
    elif abs(global_offset) < OFFSET_LIMITS['acceptable']:
        st.info("ℹ️ Offset pequeño - Alineamiento aceptable")
    else:
        st.warning(f"⚠️ Offset significativo detectado ({'+' if global_offset > 0 else ''}{global_offset:.6f} AU)")
    
    st.divider()
    
    # ==========================================
    # SECCIÓN 4: ANÁLISIS INDIVIDUAL
    # ==========================================
    st.markdown("### 4️⃣ Análisis Detallado por Estándar")
    st.info("Análisis individual de cada estándar con gráficos comparativos, diferencias espectrales y regiones críticas.")

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
            st.markdown("#### Métricas Calculadas")
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
            st.markdown("#### Evaluación")
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
    
    st.divider()
    
    # ==========================================
    # SECCIÓN 5: GENERACIÓN DE INFORME
    # ==========================================
    st.markdown("### 5️⃣ Generar Informe de Validación")
    st.info("""
    Completa la información del servicio para generar un informe HTML profesional 
    con todos los resultados de la validación.
    """)
    
    st.markdown("#### 📋 Información del Servicio")
    
    col1, col2 = st.columns(2)
    
    with col1:
        sensor_serial = st.text_input(
            "Número de Serie del Sensor:",
            placeholder="Ej: NIR-2024-001",
            help="Número de serie único del equipo NIR"
        )
        
        customer_name = st.text_input(
            "Cliente:",
            placeholder="Ej: Universidad de Barcelona",
            help="Nombre del cliente o institución"
        )
    
    with col2:
        technician_name = st.text_input(
            "Técnico Responsable:",
            placeholder="Ej: Juan Pérez",
            help="Nombre del técnico que realizó el servicio de mantenimiento"
        )
        
        service_notes = st.text_area(
            "Notas del Servicio:",
            placeholder="Ej: Cambio de lámpara halógena, ajuste óptico, limpieza de ventana...",
            help="Observaciones relevantes del mantenimiento realizado",
            height=100
        )
    
    st.markdown("---")
    
    # Botón de generación centrado
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("📥 Generar Informe HTML", type="primary", use_container_width=True):
            if not sensor_serial or not customer_name or not technician_name:
                st.error("❌ Por favor completa los campos obligatorios: Número de Serie, Cliente y Técnico")
            else:
                with st.spinner("⏳ Generando informe completo..."):
                    try:
                        from core.validation_kit_report_generator import generate_validation_report
                        
                        # Preparar datos para el reporte
                        report_data = {
                            'sensor_serial': sensor_serial,
                            'customer_name': customer_name,
                            'technician_name': technician_name,
                            'service_notes': service_notes,
                            'validation_data': all_validation_data,
                            'results_df': results_df,
                            'thresholds': thresholds,
                            'n_ok': n_ok,
                            'n_warn': n_warn,
                            'n_fail': n_fail,
                            'num_channels': num_channels,
                            'ref_filename': ref_file.name,
                            'curr_filename': curr_file.name
                        }
                        
                        html_content = generate_validation_report(report_data)
                        
                        # Descargar
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"Validation_Report_{sensor_serial.replace(' ', '_')}_{timestamp}.html"
                        
                        st.success("✅ Informe generado correctamente")
                        
                        st.download_button(
                            label="💾 Descargar Informe HTML",
                            data=html_content,
                            file_name=filename,
                            mime="text/html",
                            use_container_width=True
                        )
                        
                    except Exception as e:
                        st.error(f"❌ Error al generar informe: {str(e)}")
                        with st.expander("🔍 Ver detalles del error"):
                            import traceback
                            st.code(traceback.format_exc())


if __name__ == "__main__":
    main()