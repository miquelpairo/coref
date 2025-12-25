# -*- coding: utf-8 -*-
"""
Baseline Offset Adjustment Tool (OPTIMIZED)
============================================
Herramienta para aplicar corrección de offset manual a baseline.
Útil para fine-tuning después de validación con estándares ópticos.

OPTIMIZADO: Usa funciones compartidas de core.standards_analysis
"""

import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime
from pathlib import Path
import sys
from typing import Dict, List

# Añadir directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from core.file_handlers import (
    load_ref_file,
    load_csv_baseline,
    export_ref_file,
    export_csv_file,
    load_tsv_file,
    get_spectral_columns
)
from utils.plotting import plot_baseline_comparison
from auth import check_password
from buchi_streamlit_theme import apply_buchi_styles
from config import DEFAULT_VALIDATION_THRESHOLDS, CRITICAL_REGIONS, OFFSET_LIMITS

# ===== IMPORTAR FUNCIONES COMPARTIDAS =====
from core.standards_analysis import (
    validate_standard,
    detect_spectral_shift,
    find_common_ids,
    analyze_critical_regions,
    create_validation_plot,
    create_validation_overlay_plot,
    create_global_statistics_table
)

import plotly.graph_objects as go
from plotly.subplots import make_subplots

apply_buchi_styles()


if not check_password():
    st.stop()


def main():
    st.title("🎚️ Baseline Offset Adjustment")
    st.markdown("**Aplicar corrección de offset vertical al baseline**")
    
    # Info inicial
    st.info("""
    Esta herramienta permite aplicar una corrección de offset uniforme al baseline,
    preservando completamente la forma espectral.
    
    **Casos de uso:**
    - Fine-tuning después de validación con estándares ópticos
    - Corrección de bias sistemático detectado en mediciones
    - Ajuste manual para minimizar diferencias con equipo de referencia
    
    **Ventajas del ajuste por offset:**
    - ✅ Preserva la forma espectral (no distorsiona)
    - ✅ Simple y predecible
    - ✅ Fácil de revertir
    - ✅ Bajo riesgo de introducir artefactos
    """)
    
    st.divider()
    
    # ===== SIDEBAR: CONFIGURACIÓN =====
    with st.sidebar:
        st.markdown("### ⚙️ Configuración")
        st.markdown("---")
        
        # Configuración de offset
        with st.expander("🎚️ Configuración de Offset", expanded=True):
            if 'offset_value' not in st.session_state:
                st.session_state.offset_value = 0.000
            
            offset_value = st.number_input(
                "Offset a aplicar (AU):",
                min_value=-0.500,
                max_value=0.500,
                value=st.session_state.offset_value,
                step=0.001,
                format="%.6f",
                help="Valor de offset vertical uniforme a aplicar al baseline",
                key="offset_input"
            )
            st.session_state.offset_value = offset_value
            
            st.markdown("**Presets:**")
            col1, col2 = st.columns(2)
            if col1.button("Reset (0)", use_container_width=True):
                st.session_state.offset_value = 0.000
                st.rerun()
            if col2.button("+0.005", use_container_width=True):
                st.session_state.offset_value += 0.005
                st.rerun()
            if col1.button("-0.005", use_container_width=True):
                st.session_state.offset_value -= 0.005
                st.rerun()
            
            # Indicador visual
            st.markdown("---")
            st.markdown("**Estado del Offset:**")
            if abs(st.session_state.offset_value) < 0.003:
                st.success("✅ Cambio pequeño")
            elif abs(st.session_state.offset_value) < 0.008:
                st.info("ℹ️ Cambio moderado")
            else:
                st.warning("⚠️ Cambio significativo")
        
        st.divider()
        
        # NUEVA SECCIÓN: Umbrales de Validación
        with st.expander("📊 Umbrales de Validación", expanded=False):
            st.caption("Define criterios para evaluar la mejora post-offset")
            
            corr_threshold = st.number_input(
                "Correlación objetivo:",
                min_value=0.990,
                max_value=1.000,
                value=DEFAULT_VALIDATION_THRESHOLDS['correlation'],
                step=0.001,
                format="%.4f",
                help="Correlación mínima deseable"
            )
            
            max_diff_threshold = st.number_input(
                "Max Δ objetivo (AU):",
                min_value=0.001,
                max_value=0.100,
                value=DEFAULT_VALIDATION_THRESHOLDS['max_diff'],
                step=0.001,
                format="%.4f",
                help="Diferencia máxima deseable"
            )
            
            rms_threshold = st.number_input(
                "RMS objetivo:",
                min_value=0.001,
                max_value=0.100,
                value=DEFAULT_VALIDATION_THRESHOLDS['rms'],
                step=0.001,
                format="%.4f",
                help="RMS máximo deseable"
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
            """)
    
    # ==========================================
    # SECCIÓN 1: CARGAR TSV Y SELECCIÓN DE ESTÁNDARES
    # ==========================================
    st.markdown("### 1️⃣ Cargar Estándares Ópticos y Selección")
    
    standards_loaded = render_standards_upload_and_selection_section()
    
    if not standards_loaded:
        st.warning("👇 Carga los archivos TSV para continuar")
        return
    
    st.divider()
    
    # ==========================================
    # SECCIÓN 2: ANÁLISIS GLOBAL DEL KIT
    # ==========================================
    st.markdown("### 2️⃣ Análisis Global del Kit")
    
    render_global_kit_analysis_section(thresholds)
    
    st.divider()
    
    # ==========================================
    # SECCIÓN 3: CARGAR BASELINE
    # ==========================================
    st.markdown("### 3️⃣ Cargar Baseline")
    st.info("Sube el archivo de baseline que deseas ajustar (.ref o .csv)")
    
    baseline_loaded = render_baseline_upload_section()
    
    if not baseline_loaded:
        st.warning("👇 Carga el baseline para continuar")
        return
    
    st.divider()
    
    # ==========================================
    # SECCIÓN 4: VISUALIZACIÓN BASELINE
    # ==========================================
    st.markdown("### 4️⃣ Visualización del Ajuste de Baseline")
    
    render_visualization_section()
    
    st.divider()
    
    # ==========================================
    # SECCIÓN 5: EXPORTAR
    # ==========================================
    st.markdown("### 5️⃣ Exportar Baseline Ajustado")
    
    render_export_section()
    
    st.divider()
    
    # ==========================================
    # SECCIÓN 6: GENERAR INFORME
    # ==========================================
    st.markdown("### 6️⃣ Generar Informe de Ajuste de Offset")

    render_report_generation_section()

    st.divider()
    
    # ==========================================
    # SECCIÓN 7: NOTAS IMPORTANTES
    # ==========================================
    render_important_notes_section()


# ============================================================================
# SECCIÓN 1: CARGAR TSV Y SELECCIÓN DE ESTÁNDARES
# ============================================================================

def render_standards_upload_and_selection_section():
    """
    Sección 1: Carga de TSV con estándares ópticos y selección de muestras.
    Returns True si hay estándares cargados y seleccionados.
    """
    
    st.info("""
    Carga dos archivos TSV con mediciones de estándares ópticos para calcular 
    el offset necesario basado en la comparación espectral.
    
    **Uso típico:**
    - Referencia: Mediciones con baseline antigua (antes de mantenimiento)
    - Actual: Mediciones con baseline nueva (después de mantenimiento)
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        ref_tsv = st.file_uploader(
            "TSV Referencia:",
            type=['tsv'],
            key="ref_tsv_offset",
            help="Mediciones de referencia (baseline antigua)"
        )
    
    with col2:
        curr_tsv = st.file_uploader(
            "TSV Actual:",
            type=['tsv'],
            key="curr_tsv_offset",
            help="Mediciones actuales (baseline nueva)"
        )
    
    if not ref_tsv or not curr_tsv:
        st.info("👆 Carga ambos archivos TSV para comenzar")
        return False
    
    # Cargar archivos usando funciones compartidas
    try:
        with st.spinner("⏳ Cargando archivos TSV..."):
            df_ref = load_tsv_file(ref_tsv)
            df_curr = load_tsv_file(curr_tsv)
            
            spectral_cols_ref = get_spectral_columns(df_ref)
            spectral_cols_curr = get_spectral_columns(df_curr)
            
            if len(spectral_cols_ref) != len(spectral_cols_curr):
                st.error("❌ Los archivos tienen diferente número de canales espectrales")
                return False
            
            # Encontrar IDs comunes usando función compartida
            matches = find_common_ids(df_ref, df_curr)
            
            if len(matches) == 0:
                st.error("❌ No se encontraron IDs comunes entre los archivos")
                return False
        
        st.success(f"✅ {len(matches)} estándar(es) común(es) detectado(s)")
        
        # Guardar en session_state
        st.session_state.standards_data = {
            'df_ref': df_ref,
            'df_curr': df_curr,
            'spectral_cols_ref': spectral_cols_ref,
            'spectral_cols_curr': spectral_cols_curr,
            'matches': matches,
            'ref_filename': ref_tsv.name,
            'curr_filename': curr_tsv.name
        }
        
        st.markdown("---")
        
        # ==========================================
        # SELECCIÓN DE ESTÁNDARES
        # ==========================================
        st.markdown("#### 📋 Selección de Estándares")
        
        selected_ids = render_standards_selection_interface(matches)
        
        # Verificar si se confirmó la selección
        if not st.session_state.get('standards_selection_confirmed', False):
            st.info("👆 Ajusta la selección y presiona **'Confirmar Selección'** para continuar")
            return False
        
        # Filtrar matches según selección
        matches_filtered = matches[matches['ID'].isin(selected_ids)].copy()
        
        if len(matches_filtered) == 0:
            st.warning("⚠️ No hay estándares seleccionados")
            return False
        
        # Guardar matches filtrados
        st.session_state.standards_data['matches_filtered'] = matches_filtered
        
        # Botón para cambiar selección
        if st.button("🔄 Cambiar Selección de Estándares", use_container_width=False):
            st.session_state.standards_selection_confirmed = False
            st.rerun()
        
        return True
        
    except Exception as e:
        st.error(f"❌ Error al cargar archivos TSV: {str(e)}")
        import traceback
        with st.expander("🔍 Ver detalles del error"):
            st.code(traceback.format_exc())
        return False


def render_standards_selection_interface(matches: pd.DataFrame) -> List[str]:
    """Interfaz de selección de estándares"""
    common_ids = matches['ID'].tolist()
    
    # Inicializar selección
    if 'standards_selected_ids' not in st.session_state:
        st.session_state.standards_selected_ids = common_ids.copy()
    
    if 'standards_pending_selection' not in st.session_state:
        st.session_state.standards_pending_selection = common_ids.copy()
    
    # Tabla de selección
    df_samples = pd.DataFrame({
        'ID': common_ids,
        'Note (Ref)': matches['ref_note'].tolist(),
        'Note (Actual)': matches['curr_note'].tolist(),
        'Usar para cálculo': [
            id_ in st.session_state.standards_pending_selection 
            for id_ in common_ids
        ]
    })
    
    st.info("Selecciona los estándares que deseas incluir en el cálculo del offset")
    
    with st.form("form_select_standards_offset", clear_on_submit=False):
        edited = st.data_editor(
            df_samples,
            use_container_width=True,
            hide_index=True,
            disabled=['ID', 'Note (Ref)', 'Note (Actual)'],
            column_config={
                "Usar para cálculo": st.column_config.CheckboxColumn(
                    "✓ Incluir",
                    help="Marcar para incluir en el cálculo",
                    default=True,
                )
            },
            key="editor_select_standards_offset"
        )
        
        col_a, col_b, col_c, col_d = st.columns([1, 1, 1, 2])
        btn_all = col_a.form_submit_button("✅ Todos", use_container_width=True)
        btn_none = col_b.form_submit_button("❌ Ninguno", use_container_width=True)
        btn_invert = col_c.form_submit_button("🔄 Invertir", use_container_width=True)
        btn_confirm = col_d.form_submit_button("🚀 Confirmar Selección", type="primary", use_container_width=True)
    
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
            pending = edited.loc[edited['Usar para cálculo'], 'ID'].tolist()
            st.session_state.standards_pending_selection = pending
            st.session_state.standards_selected_ids = pending
            st.session_state.standards_selection_confirmed = True
            st.success(f"✅ Selección confirmada: {len(st.session_state.standards_selected_ids)} estándar(es)")
        except Exception as e:
            st.error(f"Error al confirmar selección: {str(e)}")
    else:
        # Actualizar pending mientras se edita
        if isinstance(edited, pd.DataFrame):
            try:
                pending = edited.loc[edited['Usar para cálculo'], 'ID'].tolist()
                st.session_state.standards_pending_selection = pending
            except Exception:
                pass
    
    st.caption(
        f"Pendientes: {len(st.session_state.standards_pending_selection)} - "
        f"Confirmados: {len(st.session_state.get('standards_selected_ids', []))}"
    )
    
    return st.session_state.standards_selected_ids


# ============================================================================
# SECCIÓN 2: ANÁLISIS GLOBAL DEL KIT
# ============================================================================

def render_global_kit_analysis_section(thresholds: Dict):
    """
    Sección 2: Análisis global del kit con estándares.
    MEJORADO: Ahora incluye evaluación contra umbrales
    """
    if 'standards_data' not in st.session_state:
        return
    
    standards_data = st.session_state.standards_data
    df_ref = standards_data['df_ref']
    df_curr = standards_data['df_curr']
    spectral_cols_ref = standards_data['spectral_cols_ref']
    spectral_cols_curr = standards_data['spectral_cols_curr']
    matches_filtered = standards_data['matches_filtered']
    
    offset_value = st.session_state.get('offset_value', 0.0)
    
    # Calcular validaciones para todos los estándares seleccionados
    all_validation_original = []
    all_validation_simulated = []
    
    with st.spinner(f"⏳ Calculando métricas para {len(matches_filtered)} estándar(es)..."):
        for idx, row in matches_filtered.iterrows():
            sample_id = row['ID']
            ref_note = row['ref_note']
            curr_note = row['curr_note']
            ref_idx = row['ref_idx']
            curr_idx = row['curr_idx']
            
            # Extraer espectros
            reference = df_ref.loc[ref_idx, spectral_cols_ref].astype(float).values
            current_original = df_curr.loc[curr_idx, spectral_cols_curr].astype(float).values
            
            # Simular espectro con offset aplicado
            current_simulated = current_original + offset_value
            
            # Calcular métricas sin offset (CON UMBRALES)
            metrics_original = validate_standard(reference, current_original, thresholds)
            
            # Calcular métricas con offset (CON UMBRALES)
            metrics_simulated = validate_standard(reference, current_simulated, thresholds)
            
            # Guardar datos completos
            all_validation_original.append({
                'id': sample_id,
                'ref_note': ref_note,
                'curr_note': curr_note,
                'reference': reference,
                'current': current_original,
                'diff': metrics_original['diff'],
                'validation_results': metrics_original
            })
            
            all_validation_simulated.append({
                'id': sample_id,
                'ref_note': ref_note,
                'curr_note': curr_note,
                'reference': reference,
                'current': current_simulated,
                'diff': metrics_simulated['diff'],
                'validation_results': metrics_simulated
            })
    
    # Guardar en session_state para uso posterior
    st.session_state.validation_results = {
        'original': all_validation_original,
        'simulated': all_validation_simulated
    }
    
    # Gráfico overlay de todos los estándares usando función compartida
    with st.expander("📈 Vista Global de Todos los Estándares", expanded=True):
        st.info("""
        Comparación simultánea de todos los espectros. Las líneas sólidas azules 
        son la referencia, las líneas rojas son mediciones sin offset, y las líneas 
        verdes son la simulación con offset aplicado.
        """)
        
        fig_overlay = create_overlay_simulation_plot(
            all_validation_original,
            all_validation_simulated,
            offset_value
        )
        st.plotly_chart(fig_overlay, use_container_width=True)
    
    # Estadísticas globales usando función compartida
    st.markdown("#### 📈 Estadísticas Globales del Kit")
    st.caption(f"Análisis agregado de {len(matches_filtered)} estándar(es) seleccionado(s)")
    
    # Crear tabla de estadísticas comparativas
    stats_comparison = create_global_statistics_comparison(
        all_validation_original,
        all_validation_simulated
    )
    st.dataframe(stats_comparison, use_container_width=True, hide_index=True)
    
    # Métricas destacadas con evaluación contra umbrales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_corr_orig = np.mean([d['validation_results']['correlation'] for d in all_validation_original])
        avg_corr_sim = np.mean([d['validation_results']['correlation'] for d in all_validation_simulated])
        delta_corr = avg_corr_sim - avg_corr_orig
        
        st.metric(
            "Correlación Media", 
            f"{avg_corr_sim:.6f}",
            delta=f"{delta_corr:+.6f}",
            help=f"Original: {avg_corr_orig:.6f} | Simulado: {avg_corr_sim:.6f}"
        )
        # Evaluación contra umbral
        if avg_corr_sim >= thresholds['correlation']:
            st.success(f"✅ > {thresholds['correlation']}")
        else:
            st.warning(f"⚠️ < {thresholds['correlation']}")
    
    with col2:
        avg_max_orig = np.mean([d['validation_results']['max_diff'] for d in all_validation_original])
        avg_max_sim = np.mean([d['validation_results']['max_diff'] for d in all_validation_simulated])
        delta_max = avg_max_sim - avg_max_orig
        
        st.metric(
            "Max Δ Media", 
            f"{avg_max_sim:.6f} AU",
            delta=f"{delta_max:+.6f} AU",
            delta_color="inverse" if delta_max < 0 else "normal",
            help=f"Original: {avg_max_orig:.6f} | Simulado: {avg_max_sim:.6f}"
        )
        # Evaluación contra umbral
        if avg_max_sim <= thresholds['max_diff']:
            st.success(f"✅ < {thresholds['max_diff']}")
        else:
            st.warning(f"⚠️ > {thresholds['max_diff']}")
    
    with col3:
        avg_rms_orig = np.mean([d['validation_results']['rms'] for d in all_validation_original])
        avg_rms_sim = np.mean([d['validation_results']['rms'] for d in all_validation_simulated])
        delta_rms = avg_rms_sim - avg_rms_orig
        
        st.metric(
            "RMS Media", 
            f"{avg_rms_sim:.6f}",
            delta=f"{delta_rms:+.6f}",
            delta_color="inverse" if delta_rms < 0 else "normal",
            help=f"Original: {avg_rms_orig:.6f} | Simulado: {avg_rms_sim:.6f}"
        )
        # Evaluación contra umbral
        if avg_rms_sim <= thresholds['rms']:
            st.success(f"✅ < {thresholds['rms']}")
        else:
            st.warning(f"⚠️ > {thresholds['rms']}")
    
    with col4:
        # Contar cuántos estándares pasan todos los umbrales
        n_pass_orig = sum(1 for d in all_validation_original if d['validation_results'].get('pass', False))
        n_pass_sim = sum(1 for d in all_validation_simulated if d['validation_results'].get('pass', False))
        
        st.metric(
            "Estándares OK",
            f"{n_pass_sim}/{len(matches_filtered)}",
            delta=f"{n_pass_sim - n_pass_orig:+d}",
            delta_color="normal" if n_pass_sim >= n_pass_orig else "inverse",
            help="Número de estándares que pasan todos los umbrales"
        )
    
    st.markdown("---")
    
    # Offset global del kit
    global_offset_orig = np.mean([d['validation_results']['mean_diff'] for d in all_validation_original])
    global_offset_sim = np.mean([d['validation_results']['mean_diff'] for d in all_validation_simulated])
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            "🎯 Offset Global (Original)", 
            f"{global_offset_orig:.6f} AU",
            help="Offset medio sin corrección aplicada"
        )
    
    with col2:
        st.metric(
            "🎯 Offset Global (Simulado)", 
            f"{global_offset_sim:.6f} AU",
            delta=f"{global_offset_sim - global_offset_orig:+.6f} AU",
            delta_color="inverse" if abs(global_offset_sim) < abs(global_offset_orig) else "normal",
            help="Offset medio con corrección aplicada"
        )
    
    # Evaluación del offset simulado
    if abs(global_offset_sim) < OFFSET_LIMITS['negligible']:
        st.success(f"✅ **Excelente corrección**: El offset simulado ({offset_value:+.6f} AU) reduce el bias global a nivel despreciable ({global_offset_sim:+.6f} AU)")
    elif abs(global_offset_sim) < abs(global_offset_orig):
        reduction = (1 - abs(global_offset_sim)/abs(global_offset_orig)) * 100
        st.info(f"ℹ️ **Mejora significativa**: El offset reduce el bias en {reduction:.1f}%. Bias residual: {global_offset_sim:+.6f} AU")
    else:
        st.warning(f"⚠️ **Empeoramiento**: El offset aplicado ({offset_value:+.6f} AU) aumenta el bias global. Considera ajustar el valor.")
    
    # Análisis individual por estándar (usando funciones compartidas)
    st.markdown("---")
    st.markdown("#### 🔍 Análisis Individual por Estándar")
    
    # Selector de estándar
    selected_idx = st.selectbox(
        "Selecciona estándar para ver detalles:",
        range(len(matches_filtered)),
        format_func=lambda x: f"{matches_filtered.iloc[x]['ID']} - {matches_filtered.iloc[x]['ref_note']}",
        key="standard_selector_global"
    )
    
    row = matches_filtered.iloc[selected_idx]
    sample_id = row['ID']
    
    # Obtener datos del estándar seleccionado
    data_orig = all_validation_original[selected_idx]
    data_sim = all_validation_simulated[selected_idx]
    
    reference = data_orig['reference']
    current_original = data_orig['current']
    current_simulated = data_sim['current']
    
    metrics_original = data_orig['validation_results']
    metrics_simulated = data_sim['validation_results']
    
    # Tabs de análisis detallado
    tab1, tab2, tab3 = st.tabs([
        "📈 Gráficos Comparativos",
        "📋 Regiones Críticas",
        "📊 Métricas Detalladas"
    ])
    
    with tab1:
        # Gráfico espectral comparativo
        channels = list(range(1, len(reference) + 1))
        
        fig_spectra = make_subplots(
            rows=2, cols=1,
            subplot_titles=(
                f'Espectros: Referencia vs Actual (Original y Simulado) - {sample_id}',
                'Diferencias vs Referencia'
            ),
            vertical_spacing=0.15,
            row_heights=[0.6, 0.4]
        )
        
        # Panel 1: Overlay de espectros
        fig_spectra.add_trace(
            go.Scatter(x=channels, y=reference, name='Referencia',
                      line=dict(color='blue', width=2)),
            row=1, col=1
        )
        fig_spectra.add_trace(
            go.Scatter(x=channels, y=current_original, name='Actual (Original)',
                      line=dict(color='red', width=2, dash='dash')),
            row=1, col=1
        )
        fig_spectra.add_trace(
            go.Scatter(x=channels, y=current_simulated, name=f'Actual + Offset ({offset_value:+.6f})',
                      line=dict(color='green', width=2, dash='dot')),
            row=1, col=1
        )
        
        # Panel 2: Diferencias
        diff_original = current_original - reference
        diff_simulated = current_simulated - reference
        
        fig_spectra.add_trace(
            go.Scatter(x=channels, y=diff_original, name='Δ Original',
                      line=dict(color='red', width=2),
                      fill='tozeroy', fillcolor='rgba(255,0,0,0.1)'),
            row=2, col=1
        )
        fig_spectra.add_trace(
            go.Scatter(x=channels, y=diff_simulated, name='Δ Simulado',
                      line=dict(color='green', width=2),
                      fill='tozeroy', fillcolor='rgba(0,255,0,0.1)'),
            row=2, col=1
        )
        
        fig_spectra.add_hline(y=0, line_dash="dash", line_color="gray", 
                             opacity=0.5, row=2, col=1)
        
        fig_spectra.update_xaxes(title_text="Canal espectral", row=2, col=1)
        fig_spectra.update_yaxes(title_text="Absorbancia", row=1, col=1)
        fig_spectra.update_yaxes(title_text="Δ Absorbancia", row=2, col=1)
        
        fig_spectra.update_layout(
            height=700,
            showlegend=True,
            template='plotly_white',
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_spectra, use_container_width=True)
    
    with tab2:
        # Usar función compartida para analizar regiones críticas
        st.markdown("**Original (sin offset):**")
        regions_orig = analyze_critical_regions(
            reference, current_original,
            CRITICAL_REGIONS,
            len(reference)
        )
        st.dataframe(regions_orig, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.markdown("**Simulado (con offset):**")
        regions_sim = analyze_critical_regions(
            reference, current_simulated,
            CRITICAL_REGIONS,
            len(reference)
        )
        st.dataframe(regions_sim, use_container_width=True, hide_index=True)
        st.caption("* = Región ajustada a rango del instrumento (900-1700 nm)")
    
    with tab3:
        # Mostrar comparación en columnas
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("##### Sin Offset")
            st.metric("Correlación", f"{metrics_original['correlation']:.6f}")
            st.metric("Max Δ", f"{metrics_original['max_diff']:.6f} AU")
            st.metric("RMS", f"{metrics_original['rms']:.6f}")
            st.metric("Offset Medio", f"{metrics_original['mean_diff']:+.6f} AU")
            
            # Evaluación contra umbrales
            if metrics_original.get('pass', False):
                st.success("✅ Pasa todos los umbrales")
            else:
                st.warning("⚠️ Falla umbrales")
        
        with col2:
            st.markdown(f"##### Con Offset ({offset_value:+.6f} AU)")
            st.metric("Correlación", f"{metrics_simulated['correlation']:.6f}")
            st.metric("Max Δ", f"{metrics_simulated['max_diff']:.6f} AU")
            st.metric("RMS", f"{metrics_simulated['rms']:.6f}")
            st.metric("Offset Medio", f"{metrics_simulated['mean_diff']:+.6f} AU")
            
            # Evaluación contra umbrales
            if metrics_simulated.get('pass', False):
                st.success("✅ Pasa todos los umbrales")
            else:
                st.warning("⚠️ Falla umbrales")
        
        with col3:
            st.markdown("##### Δ Cambio")
            delta_corr = metrics_simulated['correlation'] - metrics_original['correlation']
            delta_max = metrics_simulated['max_diff'] - metrics_original['max_diff']
            delta_rms = metrics_simulated['rms'] - metrics_original['rms']
            delta_offset = metrics_simulated['mean_diff'] - metrics_original['mean_diff']
            
            st.metric("Correlación", f"{delta_corr:+.6f}")
            st.metric("Max Δ", f"{delta_max:+.6f} AU")
            st.metric("RMS", f"{delta_rms:+.6f}")
            st.metric("Offset Medio", f"{delta_offset:+.6f} AU")
        
        # Gráfico comparativo de barras
        fig_comparison = create_simulation_comparison_plot(
            metrics_original, 
            metrics_simulated, 
            offset_value
        )
        st.plotly_chart(fig_comparison, use_container_width=True)
    
    # Exportar datos de simulación completa
    st.markdown("---")
    
    export_data = []
    for i, (orig, sim) in enumerate(zip(all_validation_original, all_validation_simulated)):
        export_data.append({
            'ID': orig['id'],
            'Note': orig['ref_note'],
            'Corr_Original': orig['validation_results']['correlation'],
            'Corr_Simulado': sim['validation_results']['correlation'],
            'MaxDiff_Original': orig['validation_results']['max_diff'],
            'MaxDiff_Simulado': sim['validation_results']['max_diff'],
            'RMS_Original': orig['validation_results']['rms'],
            'RMS_Simulado': sim['validation_results']['rms'],
            'Offset_Original': orig['validation_results']['mean_diff'],
            'Offset_Simulado': sim['validation_results']['mean_diff'],
            'Pass_Original': orig['validation_results'].get('pass', False),
            'Pass_Simulado': sim['validation_results'].get('pass', False)
        })
    
    df_export = pd.DataFrame(export_data)
    csv_export = df_export.to_csv(index=False)
    
    st.download_button(
        "📥 Descargar Resumen Completo de Simulación (CSV)",
        data=csv_export,
        file_name=f"simulation_summary_offset_{offset_value:+.6f}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )


# ============================================================================
# FUNCIONES AUXILIARES PARA VISUALIZACIÓN
# ============================================================================

def create_simulation_comparison_plot(original_metrics: Dict, simulated_metrics: Dict, 
                                      offset_value: float) -> go.Figure:
    """Crea gráfico comparativo de métricas antes y después del offset"""
    metrics = ['Max Δ (AU)', 'RMS', 'Offset Medio']
    original_values = [
        original_metrics['max_diff'],
        original_metrics['rms'],
        abs(original_metrics['mean_diff'])
    ]
    simulated_values = [
        simulated_metrics['max_diff'],
        simulated_metrics['rms'],
        abs(simulated_metrics['mean_diff'])
    ]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Sin Offset',
        x=metrics,
        y=original_values,
        marker_color='lightblue',
        text=[f"{v:.6f}" for v in original_values],
        textposition='outside'
    ))
    
    fig.add_trace(go.Bar(
        name=f'Con Offset ({offset_value:+.6f} AU)',
        x=metrics,
        y=simulated_values,
        marker_color='lightgreen',
        text=[f"{v:.6f}" for v in simulated_values],
        textposition='outside'
    ))
    
    fig.update_layout(
        title="Impacto del Offset en Métricas de Validación",
        barmode='group',
        yaxis_title="Valor",
        template='plotly_white',
        height=400,
        yaxis=dict(
            range=[0, max(max(original_values), max(simulated_values)) * 1.15]
        )
    )
    
    return fig


def create_overlay_simulation_plot(validation_original: List[Dict], 
                                   validation_simulated: List[Dict],
                                   offset_value: float) -> go.Figure:
    """Crea gráfico overlay comparando original vs simulado"""
    colors_ref = ['#1f77b4', '#2ca02c', '#9467bd', '#8c564b', '#e377c2']
    colors_orig = ['#ff7f0e', '#d62728', '#ff69b4', '#ffa500', '#dc143c']
    colors_sim = ['#00cc00', '#00ff00', '#90ee90', '#32cd32', '#00fa9a']
    
    fig = go.Figure()
    
    if len(validation_original) == 0:
        return fig
    
    channels = list(range(1, len(validation_original[0]['reference']) + 1))
    
    # Añadir espectros de referencia
    for i, data in enumerate(validation_original):
        color = colors_ref[i % len(colors_ref)]
        sample_label = f"{data['id']} - Ref"
        
        fig.add_trace(go.Scatter(
            x=channels,
            y=data['reference'],
            mode='lines',
            name=sample_label,
            line=dict(color=color, width=2),
            legendgroup='reference',
            hovertemplate=f'<b>{sample_label}</b><br>Canal: %{{x}}<br>Abs: %{{y:.6f}}<extra></extra>'
        ))
    
    # Añadir espectros originales
    for i, data in enumerate(validation_original):
        color = colors_orig[i % len(colors_orig)]
        sample_label = f"{data['id']} - Orig"
        
        fig.add_trace(go.Scatter(
            x=channels,
            y=data['current'],
            mode='lines',
            name=sample_label,
            line=dict(color=color, width=2, dash='dash'),
            legendgroup='original',
            hovertemplate=f'<b>{sample_label}</b><br>Canal: %{{x}}<br>Abs: %{{y:.6f}}<extra></extra>'
        ))
    
    # Añadir espectros simulados
    for i, data in enumerate(validation_simulated):
        color = colors_sim[i % len(colors_sim)]
        sample_label = f"{data['id']} - Sim"
        
        fig.add_trace(go.Scatter(
            x=channels,
            y=data['current'],
            mode='lines',
            name=sample_label,
            line=dict(color=color, width=2, dash='dot'),
            legendgroup='simulated',
            hovertemplate=f'<b>{sample_label}</b><br>Canal: %{{x}}<br>Abs: %{{y:.6f}}<extra></extra>'
        ))
    
    fig.update_layout(
        title={
            'text': f'Comparación Global: Original vs Simulado (Offset: {offset_value:+.6f} AU)',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18, 'color': '#2c5f3f'}
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
            font=dict(size=9)
        )
    )
    
    return fig


def create_global_statistics_comparison(validation_original: List[Dict],
                                        validation_simulated: List[Dict]) -> pd.DataFrame:
    """Crea tabla comparativa de estadísticas globales"""
    if len(validation_original) == 0:
        return pd.DataFrame()
    
    # Recopilar métricas originales
    corr_orig = [d['validation_results']['correlation'] for d in validation_original]
    max_orig = [d['validation_results']['max_diff'] for d in validation_original]
    rms_orig = [d['validation_results']['rms'] for d in validation_original]
    off_orig = [d['validation_results']['mean_diff'] for d in validation_original]
    
    # Recopilar métricas simuladas
    corr_sim = [d['validation_results']['correlation'] for d in validation_simulated]
    max_sim = [d['validation_results']['max_diff'] for d in validation_simulated]
    rms_sim = [d['validation_results']['rms'] for d in validation_simulated]
    off_sim = [d['validation_results']['mean_diff'] for d in validation_simulated]
    
    stats = {
        'Métrica': ['Correlación', 'Max Δ (AU)', 'RMS', 'Offset Medio (AU)'],
        'Media Original': [
            f"{np.mean(corr_orig):.6f}",
            f"{np.mean(max_orig):.6f}",
            f"{np.mean(rms_orig):.6f}",
            f"{np.mean(off_orig):.6f}"
        ],
        'Media Simulado': [
            f"{np.mean(corr_sim):.6f}",
            f"{np.mean(max_sim):.6f}",
            f"{np.mean(rms_sim):.6f}",
            f"{np.mean(off_sim):.6f}"
        ],
        'Desv. Est. Original': [
            f"{np.std(corr_orig):.6f}",
            f"{np.std(max_orig):.6f}",
            f"{np.std(rms_orig):.6f}",
            f"{np.std(off_orig):.6f}"
        ],
        'Desv. Est. Simulado': [
            f"{np.std(corr_sim):.6f}",
            f"{np.std(max_sim):.6f}",
            f"{np.std(rms_sim):.6f}",
            f"{np.std(off_sim):.6f}"
        ]
    }
    
    return pd.DataFrame(stats)


# ============================================================================
# SECCIÓN 3-7: BASELINE, VISUALIZACIÓN, EXPORTAR, INFORME, NOTAS
# (Mantener código original de estas secciones - NO necesitan optimización)
# ============================================================================

def render_baseline_upload_section():
    """Sección 3: Carga del baseline (.ref o .csv)"""
    baseline_file = st.file_uploader(
        "Archivo baseline:",
        type=["ref", "csv"],
        key="baseline_upload_offset",
        help="Selecciona el archivo de baseline a ajustar"
    )
    
    if baseline_file:
        file_extension = baseline_file.name.split('.')[-1].lower()
        
        try:
            if file_extension == 'ref':
                header, ref_spectrum = load_ref_file(baseline_file)
                
                st.success("✅ Baseline .ref cargado correctamente")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Cabecera:**")
                    st.write(f"X1 = {header[0]:.6e}")
                    st.write(f"X2 = {header[1]:.6e}")
                    st.write(f"X3 = {header[2]:.6e}")
                
                with col2:
                    st.metric("Puntos espectrales", len(ref_spectrum))
                    st.metric("Valor medio", f"{np.mean(ref_spectrum):.6f} AU")
                
                st.session_state.baseline_offset_tool = {
                    'spectrum': ref_spectrum,
                    'header': header,
                    'df_baseline': None,
                    'origin': 'ref',
                    'filename': baseline_file.name
                }
                
                return True
                
            elif file_extension == 'csv':
                df_baseline, ref_spectrum = load_csv_baseline(baseline_file)
                
                st.success("✅ Baseline .csv cargado correctamente")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("NIR Pixels", int(df_baseline['nir_pixels'].iloc[0]))
                    st.metric("Timestamp", df_baseline['time_stamp'].iloc[0])
                
                with col2:
                    st.metric("Puntos espectrales", len(ref_spectrum))
                    st.metric("Valor medio", f"{np.mean(ref_spectrum):.6f} AU")
                
                st.session_state.baseline_offset_tool = {
                    'spectrum': ref_spectrum,
                    'header': None,
                    'df_baseline': df_baseline,
                    'origin': 'csv',
                    'filename': baseline_file.name
                }
                
                return True
                
        except Exception as e:
            st.error(f"❌ Error al cargar baseline: {str(e)}")
            import traceback
            with st.expander("🔍 Ver detalles del error"):
                st.code(traceback.format_exc())
            return False
    
    if 'baseline_offset_tool' in st.session_state:
        baseline_data = st.session_state.baseline_offset_tool
        st.success(f"✅ Baseline cargado: {baseline_data['filename']}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Puntos espectrales", len(baseline_data['spectrum']))
        with col2:
            st.metric("Valor medio", f"{np.mean(baseline_data['spectrum']):.6f} AU")
        
        return True
    
    return False


def render_visualization_section():
    """Sección 4: Visualización comparativa del baseline"""
    if 'baseline_offset_tool' not in st.session_state:
        return
    
    baseline_data = st.session_state.baseline_offset_tool
    ref_spectrum = baseline_data['spectrum']
    offset_value = st.session_state.get('offset_value', 0.0)
    
    # Aplicar offset
    adjusted_spectrum = ref_spectrum - offset_value
    
    st.info("Comparación visual entre baseline original y ajustado")
    
    # Crear columnas espectrales dummy (canales 1 a N)
    num_channels = len(ref_spectrum)
    spectral_cols = [str(i) for i in range(1, num_channels + 1)]
    
    fig = plot_baseline_comparison(ref_spectrum, adjusted_spectrum, spectral_cols)
    
    # Actualizar título del gráfico
    fig.update_layout(
        title=f"Baseline Original vs Ajustado (Offset: {offset_value:+.6f} AU)"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Información del ajuste aplicado
    original_mean = np.mean(ref_spectrum)
    new_mean = np.mean(adjusted_spectrum)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Media Original", f"{original_mean:.6f} AU")
    
    with col2:
        st.metric("Media Ajustada", f"{new_mean:.6f} AU")
    
    with col3:
        st.metric("Cambio Aplicado", f"{offset_value:+.6f} AU")
    
    # Estadísticas del ajuste
    with st.expander("📊 Estadísticas Detalladas", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Baseline Original")
            st.write(f"**Mínimo:** {np.min(ref_spectrum):.6f} AU")
            st.write(f"**Máximo:** {np.max(ref_spectrum):.6f} AU")
            st.write(f"**Media:** {np.mean(ref_spectrum):.6f} AU")
            st.write(f"**Desv. Est.:** {np.std(ref_spectrum):.6f} AU")
        
        with col2:
            st.markdown("#### Baseline Ajustado")
            st.write(f"**Mínimo:** {np.min(adjusted_spectrum):.6f} AU")
            st.write(f"**Máximo:** {np.max(adjusted_spectrum):.6f} AU")
            st.write(f"**Media:** {np.mean(adjusted_spectrum):.6f} AU")
            st.write(f"**Desv. Est.:** {np.std(adjusted_spectrum):.6f} AU")
    
    # Tabla de comparación descargable
    df_comparison = pd.DataFrame({
        "Canal": range(1, len(ref_spectrum) + 1),
        "baseline_original": ref_spectrum,
        "baseline_ajustado": adjusted_spectrum,
        "offset_aplicado": offset_value
    })
    
    csv_comp = io.StringIO()
    df_comparison.to_csv(csv_comp, index=False)
    
    st.download_button(
        "📥 Descargar Tabla de Comparación (CSV)",
        data=csv_comp.getvalue(),
        file_name=f"comparacion_offset_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )


def render_export_section():
    """Sección 5: Exportar baseline ajustado"""
    if 'baseline_offset_tool' not in st.session_state:
        return
    
    baseline_data = st.session_state.baseline_offset_tool
    ref_spectrum = baseline_data['spectrum']
    offset_value = st.session_state.get('offset_value', 0.0)
    
    # Verificar que hay cambio
    if abs(offset_value) < 0.000001:
        st.warning("⚠️ El offset es 0.000 - No hay cambios que exportar")
        return
    
    # Aplicar offset
    adjusted_spectrum = ref_spectrum - offset_value
    
    st.info(f"""
    **Resumen del ajuste:**
    - Offset aplicado: {offset_value:+.6f} AU
    - Cambio en media: {offset_value:+.6f} AU
    - Forma espectral: Preservada ✅
    """)
    
    col_exp1, col_exp2 = st.columns(2)
    
    # Exportar .REF
    with col_exp1:
        st.markdown("**Formato .ref (binario)**")
        if baseline_data['origin'] == 'ref' and baseline_data['header'] is not None:
            st.success("✅ Cabecera original preservada")
            ref_bytes = export_ref_file(adjusted_spectrum, baseline_data['header'])
            # Generar nombre conservando el original con NEW_timestamp
            original_name = baseline_data['filename']
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            name_parts = original_name.rsplit('.', 1)
            if len(name_parts) == 2:
                new_filename = f"{name_parts[0]}_OFFSAD_{timestamp}.{name_parts[1]}"
            else:
                new_filename = f"{original_name}_OFFSAD_{timestamp}"

            st.download_button(
                "📥 Descargar .ref ajustado",
                data=ref_bytes,
                file_name=new_filename,
                mime="application/octet-stream",
                key="download_ref_offset",
                use_container_width=True
            )
        else:
            st.warning("⚠️ No disponible (archivo original no era .ref)")
    
    # Exportar .CSV
    with col_exp2:
        st.markdown("**Formato .csv (nuevo software)**")
        if baseline_data['origin'] == 'csv' and baseline_data['df_baseline'] is not None:
            st.success("✅ Metadatos originales preservados")
            csv_bytes = export_csv_file(adjusted_spectrum, df_baseline=baseline_data['df_baseline'])
        else:
            st.info("ℹ️ Usando metadatos por defecto")
            csv_bytes = export_csv_file(adjusted_spectrum)
        
        # Generar nombre conservando el original con NEW_timestamp
        original_name = baseline_data['filename']
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name_parts = original_name.rsplit('.', 1)
        if len(name_parts) == 2:
            new_filename_csv = f"{name_parts[0]}_OFFSAD_{timestamp}.csv"
        else:
            new_filename_csv = f"{original_name}_OFFSAD_{timestamp}.csv"

        st.download_button(
            "📥 Descargar .csv ajustado",
            data=csv_bytes,
            file_name=new_filename_csv,
            mime="text/csv",
            key="download_csv_offset",
            use_container_width=True
        )


def render_report_generation_section():
    """Sección 6: Generación de informe HTML"""
    # Verificar que hay datos necesarios
    if 'standards_data' not in st.session_state:
        st.warning("⚠️ Necesitas cargar los archivos TSV primero")
        return
    
    if 'baseline_offset_tool' not in st.session_state:
        st.warning("⚠️ Necesitas cargar el baseline primero")
        return
    
    if 'validation_results' not in st.session_state:
        st.warning("⚠️ Necesitas calcular las métricas primero (ve a la sección de Análisis Global)")
        return
    
    st.info("""
    Completa la información del servicio para generar un informe HTML profesional 
    con todos los resultados del ajuste de offset.
    """)
    
    st.markdown("#### 📋 Información del Servicio")
    
    col1, col2 = st.columns(2)
    
    with col1:
        sensor_serial = st.text_input(
            "Número de Serie del Sensor:",
            placeholder="Ej: NIR-2024-001",
            help="Número de serie único del equipo NIR",
            key="report_sensor_serial"
        )
        
        customer_name = st.text_input(
            "Cliente:",
            placeholder="Ej: Universidad de Barcelona",
            help="Nombre del cliente o institución",
            key="report_customer"
        )
    
    with col2:
        technician_name = st.text_input(
            "Técnico Responsable:",
            placeholder="Ej: Juan Pérez",
            help="Nombre del técnico que realizó el servicio de mantenimiento",
            key="report_technician"
        )
        
        service_notes = st.text_area(
            "Notas del Servicio:",
            placeholder="Ej: Cambio de lámpara halógena, ajuste de offset por bias sistemático detectado...",
            help="Observaciones relevantes del mantenimiento y razón del ajuste",
            height=100,
            key="report_notes"
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
                        from core.offset_adjustment_report_generator import generate_offset_adjustment_report
                        
                        # Obtener datos necesarios
                        standards_data = st.session_state.standards_data
                        baseline_data = st.session_state.baseline_offset_tool
                        validation_results = st.session_state.validation_results
                        offset_value = st.session_state.get('offset_value', 0.0)
                        
                        # Calcular offsets globales
                        global_offset_orig = np.mean([
                            d['validation_results']['mean_diff'] 
                            for d in validation_results['original']
                        ])
                        global_offset_sim = np.mean([
                            d['validation_results']['mean_diff'] 
                            for d in validation_results['simulated']
                        ])
                        
                        # Aplicar offset al baseline
                        baseline_adjusted = baseline_data['spectrum'] - offset_value
                        
                        # Preparar datos para el reporte
                        report_data = {
                            'sensor_serial': sensor_serial,
                            'customer_name': customer_name,
                            'technician_name': technician_name,
                            'service_notes': service_notes,
                            'offset_value': offset_value,
                            'validation_data_original': validation_results['original'],
                            'validation_data_simulated': validation_results['simulated'],
                            'global_offset_original': global_offset_orig,
                            'global_offset_simulated': global_offset_sim,
                            'baseline_original': baseline_data['spectrum'],
                            'baseline_adjusted': baseline_adjusted,
                            'ref_filename': standards_data.get('ref_filename', 'referencia.tsv'),
                            'curr_filename': standards_data.get('curr_filename', 'actual.tsv'),
                            'baseline_filename': baseline_data['filename']
                        }
                        
                        html_content = generate_offset_adjustment_report(report_data)
                        
                        # Descargar
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"OFFSET_Adjustment_Report_{sensor_serial.replace(' ', '_')}_{timestamp}.html"
                        
                        st.success("✅ Informe generado correctamente")
                        
                        st.download_button(
                            label="💾 Descargar Informe HTML",
                            data=html_content,
                            file_name=filename,
                            mime="text/html",
                            use_container_width=True,
                            key="download_report"
                        )
                        
                    except Exception as e:
                        st.error(f"❌ Error al generar informe: {str(e)}")
                        with st.expander("🔍 Ver detalles del error"):
                            import traceback
                            st.code(traceback.format_exc())


def render_important_notes_section():
    """Sección 7: Notas importantes y recomendaciones"""
    with st.expander("ℹ️ Notas Importantes", expanded=False):
        st.markdown("""
        ### Recomendaciones después del ajuste:
        
        1. **Verificar con estándares ópticos**
           - Mide los mismos estándares con el baseline ajustado
           - Comprueba que el bias se ha corregido
        
        2. **Documentar el cambio**
           - Anota el offset aplicado en el log del equipo
           - Guarda una copia del baseline original
        
        3. **Validar calibraciones**
           - Verifica que las calibraciones activas siguen siendo válidas
           - Si es necesario, actualiza slope/bias
        
        4. **Límite de reproducibilidad**
           - Offsets < 0.003 AU pueden estar dentro del ruido instrumental
           - Offsets > 0.010 AU deberían investigarse (posible problema de hardware)
        
        ### ¿Cuándo usar esta herramienta?
        
        ✅ **Casos apropiados:**
        - Corrección de bias sistemático detectado en validación
        - Fine-tuning después de ajuste con white standards
        - Alineamiento con equipo de referencia
        
        ❌ **NO usar para:**
        - Problemas de ruido o deriva espectral (requiere servicio técnico)
        - Desalineamientos ópticos (requiere ajuste mecánico)
        - Compensar problemas de calibración (recalibrar en su lugar)
        """)


if __name__ == "__main__":
    main()