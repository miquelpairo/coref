# -*- coding: utf-8 -*-
"""
Baseline Offset Adjustment Tool
================================
Herramienta para aplicar corrección de offset manual a baseline.
Útil para fine-tuning después de validación con estándares ópticos.
"""

import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime
from pathlib import Path
import sys
from typing import Dict, List, Tuple

# Añadir directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from core.file_handlers import (
    load_ref_file,
    load_csv_baseline,
    export_ref_file,
    export_csv_file
)
from utils.plotting import plot_baseline_comparison
from auth import check_password
from buchi_streamlit_theme import apply_buchi_styles
from core.file_handlers import load_tsv_file, get_spectral_columns
from typing import Dict
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
    
    # ==========================================
    # SECCIÓN 1: CARGAR BASELINE
    # ==========================================
    st.markdown("### 1️⃣ Cargar Baseline")
    st.info("Sube el archivo de baseline que deseas ajustar (.ref o .csv)")
    
    baseline_loaded = render_baseline_upload_section()
    
    if not baseline_loaded:
        st.warning("👇 Carga el baseline para continuar")
        return
    
    st.divider()
    
    # ==========================================
    # SECCIÓN 2: CONFIGURAR OFFSET
    # ==========================================
    st.markdown("### 2️⃣ Configurar Offset")
    
    render_offset_configuration_section()
    
    st.divider()
    
    # ==========================================
    # SECCIÓN 3: VISUALIZACIÓN
    # ==========================================
    st.markdown("### 3️⃣ Visualización del Ajuste")
    
    render_visualization_section()
    
    st.divider()
    
    # ==========================================
    # SECCIÓN 4 (OPCIONAL): SIMULACIÓN CON ESTÁNDARES
    # ==========================================
    st.markdown("### 4️⃣ Simulación con Estándares Ópticos (Opcional)")
    
    render_standards_simulation_section()
    
    st.divider()
    
    # ==========================================
    # SECCIÓN 5: EXPORTAR
    # ==========================================
    st.markdown("### 5️⃣ Exportar Baseline Ajustado")
    
    render_export_section()

def render_baseline_upload_section():
    """
    Sección 1: Carga del baseline (.ref o .csv).
    Returns True si el baseline está cargado.
    """
    
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
                
                # Guardar en session_state
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
                
                # Guardar en session_state
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
    
    # Si ya existe baseline cargado previamente
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


def render_offset_configuration_section():
    """
    Sección 2: Configuración del offset.
    """
    if 'baseline_offset_tool' not in st.session_state:
        return
    
    st.info("""
    Introduce el valor de offset a aplicar. Un valor positivo aumentará todos los valores 
    del baseline, un valor negativo los disminuirá.
    
    **Recomendación:** Usa valores pequeños (< 0.010 AU) para evitar cambios drásticos.
    """)
    
    # Inicializar valor si no existe
    if 'offset_value' not in st.session_state:
        st.session_state.offset_value = 0.000
    
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col1:
        # Input de offset con callback
        def update_offset():
            st.session_state.offset_value = st.session_state.offset_input
        
        offset_value = st.number_input(
            "Offset a aplicar (AU):",
            min_value=-0.100,
            max_value=0.100,
            value=st.session_state.offset_value,
            step=0.001,
            format="%.6f",
            key="offset_input",
            help="Valor de offset vertical uniforme a aplicar al baseline",
            on_change=update_offset
        )
    
    with col2:
        st.markdown("#### Presets")
        
        def reset_offset():
            st.session_state.offset_value = 0.000
        
        def add_offset():
            st.session_state.offset_value = st.session_state.offset_value + 0.005
        
        def subtract_offset():
            st.session_state.offset_value = st.session_state.offset_value - 0.005
        
        if st.button("Resetear (0)", use_container_width=True, on_click=reset_offset):
            pass
        
        if st.button("+0.005", use_container_width=True, on_click=add_offset):
            pass
        
        if st.button("-0.005", use_container_width=True, on_click=subtract_offset):
            pass
    
    with col3:
        # Información del ajuste
        baseline_data = st.session_state.baseline_offset_tool
        original_mean = np.mean(baseline_data['spectrum'])
        new_mean = original_mean + st.session_state.offset_value
        
        st.markdown("#### Información")
        st.write(f"**Original:** {original_mean:.6f} AU")
        st.write(f"**Ajustado:** {new_mean:.6f} AU")
        st.write(f"**Cambio:** {st.session_state.offset_value:+.6f} AU")
        
        # Indicador visual
        if abs(st.session_state.offset_value) < 0.003:
            st.success("✅ Cambio pequeño")
        elif abs(st.session_state.offset_value) < 0.008:
            st.info("ℹ️ Cambio moderado")
        else:
            st.warning("⚠️ Cambio significativo")

def render_visualization_section():
    """
    Sección 3: Visualización comparativa.
    """
    if 'baseline_offset_tool' not in st.session_state:
        return
    
    baseline_data = st.session_state.baseline_offset_tool
    ref_spectrum = baseline_data['spectrum']
    offset_value = st.session_state.get('offset_value', 0.0)
    
    # Aplicar offset
    adjusted_spectrum = ref_spectrum - offset_value
    
    # Crear gráfico comparativo
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
    """
    Sección 4: Exportar baseline ajustado.
    """
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
            st.download_button(
                "📥 Descargar .ref ajustado",
                data=ref_bytes,
                file_name=f"baseline_offset_{offset_value:+.6f}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ref",
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
        
        st.download_button(
            "📥 Descargar .csv ajustado",
            data=csv_bytes,
            file_name=f"baseline_offset_{offset_value:+.6f}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            key="download_csv_offset",
            use_container_width=True
        )
    
    st.markdown("---")
    
    # Notas importantes
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

# ============================================================================
# SECCIÓN DE SIMULACIÓN CON ESTÁNDARES ÓPTICOS
# ============================================================================

def validate_standard_simple(reference: np.ndarray, current: np.ndarray) -> Dict:
    """
    Valida un estándar comparando medición vs referencia.
    Versión simplificada sin umbrales.
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
    
    return {
        'correlation': correlation,
        'max_diff': max_diff,
        'rms': rms,
        'mean_diff': mean_diff,
        'diff': diff
    }


def find_common_ids_simple(df_ref: pd.DataFrame, df_curr: pd.DataFrame) -> pd.DataFrame:
    """
    Encuentra IDs comunes entre referencia y actual.
    Versión simplificada.
    """
    if len(df_ref) == 0 or len(df_curr) == 0:
        return pd.DataFrame(columns=['ID', 'ref_note', 'curr_note', 'ref_idx', 'curr_idx'])
    
    if 'ID' not in df_ref.columns or 'ID' not in df_curr.columns:
        return pd.DataFrame(columns=['ID', 'ref_note', 'curr_note', 'ref_idx', 'curr_idx'])
    
    # Crear listas para almacenar los resultados
    ref_data = []
    for id_val in df_ref['ID'].unique():
        if pd.isna(id_val):
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
        if pd.isna(id_val):
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
    
    if len(ref_data) == 0 or len(curr_data) == 0:
        return pd.DataFrame(columns=['ID', 'ref_note', 'curr_note', 'ref_idx', 'curr_idx'])
    
    # Crear DataFrames y merge
    df_ref_ids = pd.DataFrame(ref_data)
    df_curr_ids = pd.DataFrame(curr_data)
    matches = df_ref_ids.merge(df_curr_ids, on='ID', how='inner')
    
    return matches[['ID', 'ref_note', 'curr_note', 'ref_idx', 'curr_idx']]

def render_standards_selection_interface(matches: pd.DataFrame) -> List[str]:
    """
    Interfaz de selección de estándares para simulación.
    Similar a la de baseline_alignment.
    
    Returns:
        Lista de IDs seleccionados
    """
    common_ids = matches['ID'].tolist()
    
    # Inicializar selección
    if 'sim_selected_ids' not in st.session_state:
        st.session_state.sim_selected_ids = common_ids.copy()
    
    if 'sim_pending_selection' not in st.session_state:
        st.session_state.sim_pending_selection = common_ids.copy()
    
    # Tabla de selección
    df_samples = pd.DataFrame({
        'ID': common_ids,
        'Note (Ref)': matches['ref_note'].tolist(),
        'Note (Actual)': matches['curr_note'].tolist(),
        'Usar en simulación': [
            id_ in st.session_state.sim_pending_selection 
            for id_ in common_ids
        ]
    })
    
    st.info("Selecciona los estándares que deseas incluir en la simulación")
    
    with st.form("form_select_standards_sim", clear_on_submit=False):
        edited = st.data_editor(
            df_samples,
            use_container_width=True,
            hide_index=True,
            disabled=['ID', 'Note (Ref)', 'Note (Actual)'],
            column_config={
                "Usar en simulación": st.column_config.CheckboxColumn(
                    "✓ Simular",
                    help="Marcar para incluir en la simulación",
                    default=True,
                )
            },
            key="editor_select_standards_sim"
        )
        
        col_a, col_b, col_c, col_d = st.columns([1, 1, 1, 2])
        btn_all = col_a.form_submit_button("✅ Todos", use_container_width=True)
        btn_none = col_b.form_submit_button("❌ Ninguno", use_container_width=True)
        btn_invert = col_c.form_submit_button("🔄 Invertir", use_container_width=True)
        btn_confirm = col_d.form_submit_button("🚀 Confirmar Selección", type="primary", use_container_width=True)
    
    if btn_all:
        st.session_state.sim_pending_selection = common_ids.copy()
        st.rerun()
    
    if btn_none:
        st.session_state.sim_pending_selection = []
        st.rerun()
    
    if btn_invert:
        inverted = [id_ for id_ in common_ids if id_ not in st.session_state.sim_pending_selection]
        st.session_state.sim_pending_selection = inverted
        st.rerun()
    
    if btn_confirm:
        try:
            pending = edited.loc[edited['Usar en simulación'], 'ID'].tolist()
            st.session_state.sim_pending_selection = pending
            st.session_state.sim_selected_ids = pending
            st.session_state.sim_selection_confirmed = True
            st.success(f"✅ Selección confirmada: {len(st.session_state.sim_selected_ids)} estándar(es)")
        except Exception as e:
            st.error(f"Error al confirmar selección: {str(e)}")
    else:
        # Actualizar pending mientras se edita
        if isinstance(edited, pd.DataFrame):
            try:
                pending = edited.loc[edited['Usar en simulación'], 'ID'].tolist()
                st.session_state.sim_pending_selection = pending
            except Exception:
                pass
    
    st.caption(
        f"Pendientes: {len(st.session_state.sim_pending_selection)} - "
        f"Confirmados: {len(st.session_state.get('sim_selected_ids', []))}"
    )
    
    return st.session_state.sim_selected_ids

def create_simulation_comparison_plot(original_metrics: Dict, simulated_metrics: Dict, 
                                      offset_value: float) -> go.Figure:
    """
    Crea gráfico comparativo de métricas antes y después del offset.
    """
    metrics = ['Correlación', 'Max Δ (AU)', 'RMS', 'Offset Medio']
    original_values = [
        original_metrics['correlation'],
        original_metrics['max_diff'],
        original_metrics['rms'],
        abs(original_metrics['mean_diff'])
    ]
    simulated_values = [
        simulated_metrics['correlation'],
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
        title=f"Impacto del Offset en Métricas de Validación",
        barmode='group',
        yaxis_title="Valor",
        template='plotly_white',
        height=400
    )
    
    return fig


def render_standards_simulation_section():
    """
    Sección opcional: Simular impacto del offset en estándares ópticos.
    """
    
    st.info("""
    Carga dos archivos TSV con mediciones de estándares ópticos para simular 
    cómo el offset afecta las métricas de validación.
    
    **Uso típico:**
    - Referencia: Mediciones con baseline antigua (antes de mantenimiento)
    - Actual: Mediciones con baseline nueva (después de mantenimiento)
    - Simula: ¿Qué métricas obtendría si aplico este offset a la baseline nueva?
    """)
        
    col1, col2 = st.columns(2)
    
    with col1:
        ref_tsv = st.file_uploader(
            "TSV Referencia:",
            type=['tsv'],
            key="ref_tsv_simulation",
            help="Mediciones de referencia (baseline antigua)"
        )
    
    with col2:
        curr_tsv = st.file_uploader(
            "TSV Actual:",
            type=['tsv'],
            key="curr_tsv_simulation",
            help="Mediciones actuales (baseline nueva)"
        )
    
    if not ref_tsv or not curr_tsv:
        st.info("👆 Carga ambos archivos TSV para comenzar la simulación")
        return
    
    # Cargar archivos
    try:
        with st.spinner("⏳ Cargando archivos TSV..."):
            df_ref = load_tsv_file(ref_tsv)
            df_curr = load_tsv_file(curr_tsv)
            
            spectral_cols_ref = get_spectral_columns(df_ref)
            spectral_cols_curr = get_spectral_columns(df_curr)
            
            if len(spectral_cols_ref) != len(spectral_cols_curr):
                st.error("❌ Los archivos tienen diferente número de canales espectrales")
                return
            
            # Encontrar IDs comunes
            matches = find_common_ids_simple(df_ref, df_curr)
            
            if len(matches) == 0:
                st.error("❌ No se encontraron IDs comunes entre los archivos")
                return
            
        st.success(f"✅ {len(matches)} estándar(es) común(es) detectado(s)")
        
        st.markdown("---")
        
        # ==========================================
        # SECCIÓN: SELECCIÓN DE ESTÁNDARES
        # ==========================================
        st.markdown("#### 📋 Selección de Estándares")
        
        selected_ids = render_standards_selection_interface(matches)
        
        # Verificar si se confirmó la selección
        if not st.session_state.get('sim_selection_confirmed', False):
            st.info("👆 Ajusta la selección y presiona **'Confirmar Selección'** para continuar")
            return
        
        # Filtrar matches según selección
        matches_filtered = matches[matches['ID'].isin(selected_ids)].copy()
        
        if len(matches_filtered) == 0:
            st.warning("⚠️ No hay estándares seleccionados")
            return
        
        st.markdown("---")
        
        # Botón para cambiar selección
        if st.button("🔄 Cambiar Selección de Estándares", use_container_width=False):
            st.session_state.sim_selection_confirmed = False
            st.rerun()
        
        # Obtener offset configurado
        offset_value = st.session_state.get('offset_value', 0.0)
        
        # ==========================================
        # VALIDAR TODOS LOS ESTÁNDARES
        # ==========================================
        
        all_validation_original = []
        all_validation_simulated = []
        
        with st.spinner(f"⏳ Calculando métricas para {len(matches)} estándar(es)..."):
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
                # Como baseline se RESTA, el efecto en el espectro es OPUESTO
                current_simulated = current_original + offset_value
                
                # Calcular métricas sin offset
                metrics_original = validate_standard_simple(reference, current_original)
                
                # Calcular métricas con offset
                metrics_simulated = validate_standard_simple(reference, current_simulated)
                
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
        
        st.markdown("---")
        
        # ==========================================
        # SECCIÓN: ANÁLISIS GLOBAL
        # ==========================================
        st.markdown("#### 📊 Análisis Global del Kit")
        
        # Gráfico overlay de todos los estándares
        with st.expander("📈 Vista Global de Todos los Estándares", expanded=True):
            st.info("""
            Comparación simultánea de todos los espectros. Las líneas sólidas azules 
            son la referencia, las líneas rojas son mediciones sin offset, y las líneas 
            verdes son la simulación con offset aplicado.
            """)
            
            # Crear gráfico overlay
            fig_overlay = create_overlay_simulation_plot(
                all_validation_original,
                all_validation_simulated,
                offset_value
            )
            st.plotly_chart(fig_overlay, use_container_width=True)
        
        # Estadísticas globales
        st.markdown("#### 📈 Estadísticas Globales del Kit")
        st.caption(f"Análisis agregado de {len(selected_ids)} estándar(es) seleccionado(s)")
        
        # Crear tabla de estadísticas comparativas
        stats_comparison = create_global_statistics_comparison(
            all_validation_original,
            all_validation_simulated
        )
        st.dataframe(stats_comparison, use_container_width=True, hide_index=True)
        
        # Métricas destacadas
        col1, col2, col3 = st.columns(3)
        
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
        if abs(global_offset_sim) < 0.003:
            st.success(f"✅ **Excelente corrección**: El offset simulado ({offset_value:+.6f} AU) reduce el bias global a nivel despreciable ({global_offset_sim:+.6f} AU)")
        elif abs(global_offset_sim) < abs(global_offset_orig):
            reduction = (1 - abs(global_offset_sim)/abs(global_offset_orig)) * 100
            st.info(f"ℹ️ **Mejora significativa**: El offset reduce el bias en {reduction:.1f}%. Bias residual: {global_offset_sim:+.6f} AU")
        else:
            st.warning(f"⚠️ **Empeoramiento**: El offset aplicado ({offset_value:+.6f} AU) aumenta el bias global. Considera ajustar el valor.")
        
        st.divider()
        
        # ==========================================
        # SECCIÓN: ANÁLISIS INDIVIDUAL
        # ==========================================
        st.markdown("#### 🔍 Análisis Individual por Estándar")
        
        # Selector de estándar
        selected_idx = st.selectbox(
            "Selecciona estándar para ver detalles:",
            range(len(matches_filtered)),
            format_func=lambda x: f"{matches_filtered.iloc[x]['ID']} - {matches_filtered.iloc[x]['ref_note']}",
            key="standard_selector_sim"
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
        tab1, tab2 = st.tabs([
            "📈 Gráficos Comparativos",
            "📊 Métricas Detalladas"
        ])
        
        with tab1:
            # Gráfico espectral
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
            # Mostrar comparación en columnas
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("##### Sin Offset")
                st.metric("Correlación", f"{metrics_original['correlation']:.6f}")
                st.metric("Max Δ", f"{metrics_original['max_diff']:.6f} AU")
                st.metric("RMS", f"{metrics_original['rms']:.6f}")
                st.metric("Offset Medio", f"{metrics_original['mean_diff']:+.6f} AU")
            
            with col2:
                st.markdown(f"##### Con Offset ({offset_value:+.6f} AU)")
                st.metric("Correlación", f"{metrics_simulated['correlation']:.6f}")
                st.metric("Max Δ", f"{metrics_simulated['max_diff']:.6f} AU")
                st.metric("RMS", f"{metrics_simulated['rms']:.6f}")
                st.metric("Offset Medio", f"{metrics_simulated['mean_diff']:+.6f} AU")
            
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
                'Offset_Simulado': sim['validation_results']['mean_diff']
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
        
    except Exception as e:
        st.error(f"❌ Error en simulación: {str(e)}")
        import traceback
        st.code(traceback.format_exc())


def create_overlay_simulation_plot(validation_original: List[Dict], 
                                   validation_simulated: List[Dict],
                                   offset_value: float) -> go.Figure:
    """
    Crea gráfico overlay comparando original vs simulado.
    """
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
            hovertemplate=f'<b>{sample_label}</b><br>Canal: %{{x}}<br>Abs: %{{y:.6f}}<extra></extra>'  # ✅ CORREGIDO
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
            hovertemplate=f'<b>{sample_label}</b><br>Canal: %{{x}}<br>Abs: %{{y:.6f}}<extra></extra>'  # ✅ CORREGIDO
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
            hovertemplate=f'<b>{sample_label}</b><br>Canal: %{{x}}<br>Abs: %{{y:.6f}}<extra></extra>'  # ✅ CORREGIDO
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
    """
    Crea tabla comparativa de estadísticas globales.
    """
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
        'Métrica': ['Correlación', 'Max Δ (AU)', 'RMS', 'Offset Medio (AU)'] * 2,
        'Estado': ['Original']*4 + ['Simulado']*4,
        'Media': [
            f"{np.mean(corr_orig):.6f}",
            f"{np.mean(max_orig):.6f}",
            f"{np.mean(rms_orig):.6f}",
            f"{np.mean(off_orig):.6f}",
            f"{np.mean(corr_sim):.6f}",
            f"{np.mean(max_sim):.6f}",
            f"{np.mean(rms_sim):.6f}",
            f"{np.mean(off_sim):.6f}"
        ],
        'Desv. Est.': [
            f"{np.std(corr_orig):.6f}",
            f"{np.std(max_orig):.6f}",
            f"{np.std(rms_orig):.6f}",
            f"{np.std(off_orig):.6f}",
            f"{np.std(corr_sim):.6f}",
            f"{np.std(max_sim):.6f}",
            f"{np.std(rms_sim):.6f}",
            f"{np.std(off_sim):.6f}"
        ]
    }
    
    return pd.DataFrame(stats)
    
if __name__ == "__main__":
    main()