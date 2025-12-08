# -*- coding: utf-8 -*-
"""
Paso 4: Validación del Alineamiento (Verificación primero)
"""
import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime
from config import INSTRUCTIONS, MESSAGES, VALIDATION_THRESHOLDS
from session_manager import (
    has_reference_tsv,
    get_reference_tsv,
    reset_session_state,
    go_to_next_step
)
from core.file_handlers import load_tsv_file, get_spectral_columns
from core.spectral_processing import (
    find_common_samples,
    calculate_spectral_correction
)
from utils.plotting import plot_kit_spectra
from utils.validators import validate_common_samples


def render_validation_step():
    """
    Paso 4: Validación del alineamiento.
    
    Primero verifica si el equipo está correctamente alineado.
    - Si RMS < 0.002: Validación exitosa → Generar informe
    - Si RMS ≥ 0.002: Alineamiento necesario → Ir a Paso 5
    """
    st.markdown("## PASO 4 DE 5: Validación del Alineamiento")
    
    st.info("""
    ### 🎯 Objetivo
    Verificar si el equipo está correctamente alineado midiendo el White Standard.
    
    **Proceso:**
    1. Mide el White Standard con el baseline actual
    2. Comparamos con la referencia del Paso 3
    3. **Si está bien alineado** (RMS < 0.002) → Generar informe y finalizar ✅
    4. **Si necesita ajuste** (RMS ≥ 0.002) → Ir al Paso 5 para alinear ⚙️
    """)
    
    # Inicializar contador de iteraciones si no existe
    if 'alignment_iterations' not in st.session_state:
        st.session_state.alignment_iterations = 0
    
    # Si viene del Paso 5, incrementar contador
    if st.session_state.get('came_from_alignment', False):
        st.session_state.alignment_iterations += 1
        st.session_state.came_from_alignment = False
        st.info(f"📊 Iteración #{st.session_state.alignment_iterations} - Validando ajuste aplicado")
    
    st.markdown("---")
    
    # ============================================
    # Si se fuerza el informe aunque no cumpla umbral
    # ============================================
    if st.session_state.get('force_report', False):
        st.error(f"""
        ⚠️ **ADVERTENCIA**: Generando informe sin cumplir el umbral de calidad
        
        El RMS actual ({st.session_state.validation_data['rms']:.6f}) es mayor que el umbral recomendado (0.002).
        El informe incluirá esta advertencia.
        """)
        
        st.markdown("---")
        render_report_generation()
        
        st.markdown("---")
        if st.button("🔄 Volver a validación", use_container_width=True):
            st.session_state.force_report = False
            st.rerun()
        
        return  # No mostrar el resto del paso
    
    # ==========================================
    # SECCIÓN 1: TSV REFERENCIA (PASO 3)
    # ==========================================
    st.markdown("### 1️⃣ TSV de Referencia (Paso 3)")
    
    if not has_reference_tsv():
        st.error("❌ No hay TSV de referencia. Vuelve al Paso 3.")
        return
    
    ref_data = get_reference_tsv()
    df_ref_full = ref_data['df']
    spectral_cols_ref = ref_data['spectral_cols']
    
    # Filtrar por índices seleccionados en Paso 3
    if 'selected_wstd_indices' in st.session_state and st.session_state.selected_wstd_indices:
        df_ref = df_ref_full.loc[st.session_state.selected_wstd_indices].copy()
        st.success(f"✅ TSV de referencia: {len(df_ref)} filas del Paso 3")
    else:
        df_ref = df_ref_full.copy()
        st.warning(f"⚠️ TSV de referencia cargado ({len(df_ref)} filas) - No hay selección del Paso 3")
    
    with st.expander("🔎 Ver datos de referencia", expanded=False):
        if 'selected_wstd_indices' in st.session_state and st.session_state.selected_wstd_indices:
            display_df = df_ref[['ID', 'Note']].copy()
            display_df.insert(0, 'Índice original', st.session_state.selected_wstd_indices)
            st.dataframe(display_df, use_container_width=True)
        else:
            st.dataframe(df_ref[['ID', 'Note']].head(10), use_container_width=True)
        st.write(f"**Total de filas:** {len(df_ref)}")
    
    st.markdown("---")
    
    # ==========================================
    # SECCIÓN 2: MEDIR NUEVO
    # ==========================================
    st.markdown("### 2️⃣ Medir White Standard")
    
    if st.session_state.alignment_iterations == 0:
        st.info("""
        **Primera medición:**
        1. Con el baseline actual del equipo
        2. Mide el MISMO White Standard del Paso 3
        3. Exporta el TSV y cárgalo aquí
        """)
    else:
        st.warning(f"""
        **Iteración #{st.session_state.alignment_iterations}:**
        
        Verificando el baseline corregido del Paso 5:
        1. ✅ Confirma que instalaste el nuevo baseline
        2. ✅ Reinicia SX Suite
        3. ✅ Mide de nuevo el mismo White Standard
        4. ✅ Carga el TSV aquí
        """)
    
    new_file = st.file_uploader(
        "Archivo TSV con medición actual",
        type=["tsv", "txt", "csv"],
        key=f"validation_tsv_iter_{st.session_state.alignment_iterations}"
    )
    
    if not new_file:
        st.warning("👇 Carga el TSV con las mediciones")
        return
    
    # Cargar y procesar TSV
    try:
        df_new = load_tsv_file(new_file)
        spectral_cols_new = get_spectral_columns(df_new)
        
        st.success(f"✅ TSV cargado ({len(df_new)} mediciones)")
        
        # Validar dimensiones
        if len(spectral_cols_ref) != len(spectral_cols_new):
            st.error(f"""
            ❌ Error de dimensiones:
            - Referencia: {len(spectral_cols_ref)} canales
            - Nuevo: {len(spectral_cols_new)} canales
            """)
            return
        
        with st.expander("🔎 Ver datos del nuevo TSV"):
            st.dataframe(df_new[['ID', 'Note']].head(10), use_container_width=True)
        
    except Exception as e:
        st.error(f"❌ Error al cargar TSV: {str(e)}")
        return
    
    spectral_cols = spectral_cols_ref
    
    st.markdown("---")
    
    # ==========================================
    # SECCIÓN 3: SELECCIÓN DE FILAS
    # ==========================================
    st.markdown("### 3️⃣ Seleccionar filas a usar")
    
    st.info("✅ Marca las filas que corresponden al White Standard")
    
    # Crear tabla con índice visible
    df_display = df_new[['ID', 'Note']].copy()
    df_display.insert(0, 'Seleccionar', False)
    
    edited_df = st.data_editor(
        df_display,
        hide_index=False,
        use_container_width=True,
        disabled=['ID', 'Note'],
        key=f'validation_row_selector_iter_{st.session_state.alignment_iterations}'
    )
    
    selected_indices = edited_df[edited_df['Seleccionar'] == True].index.tolist()
    
    if len(selected_indices) == 0:
        st.warning("⚠️ Selecciona al menos una fila")
        return
    
    df_new_selected = df_new.loc[selected_indices].copy()
    
    st.success(f"✅ {len(df_new_selected)} filas seleccionadas")
    
    st.markdown("---")
    
    # ==========================================
    # SECCIÓN 4: COMPARACIÓN Y DECISIÓN
    # ==========================================
    st.markdown("### 4️⃣ Evaluación del Alineamiento")
    
    # Convertir a numérico
    df_ref[spectral_cols] = df_ref[spectral_cols].apply(pd.to_numeric, errors="coerce")
    df_new_selected[spectral_cols] = df_new_selected[spectral_cols].apply(pd.to_numeric, errors="coerce")
    
    # Agrupar por ID (promedio)
    df_ref_grouped = df_ref.groupby("ID")[spectral_cols].mean()
    df_new_grouped = df_new_selected.groupby("ID")[spectral_cols].mean()
    
    # Encontrar IDs comunes
    common_ids = find_common_samples(df_ref_grouped, df_new_grouped)
    
    if not validate_common_samples(common_ids):
        return
    
    # Filtrar solo comunes
    df_ref_grouped = df_ref_grouped.loc[common_ids]
    df_new_grouped = df_new_grouped.loc[common_ids]
    
    st.success(f"✅ {len(common_ids)} ID(s) común(es) encontrado(s)")
    st.info(f"📋 IDs: {', '.join(str(x) for x in common_ids)}")
    
    # Identificar White Standard
    white_id = st.selectbox(
        "Selecciona el White Standard",
        options=list(common_ids),
        key=f"white_id_select_iter_{st.session_state.alignment_iterations}",
        help="Selecciona el ID que corresponde al White Standard"
    )
    
    # Calcular diferencia del White
    ref_white_spectrum = df_ref_grouped.loc[white_id].values
    new_white_spectrum = df_new_grouped.loc[white_id].values
    diff_white = ref_white_spectrum - new_white_spectrum
    
    # Calcular RMS
    rms_white = np.sqrt(np.mean(diff_white**2))
    max_diff_white = np.max(np.abs(diff_white))
    mean_diff_white = np.mean(np.abs(diff_white))
    
    # Mostrar métricas
    st.markdown(f"##### Métricas del White Standard: **{white_id}**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("RMS", f"{rms_white:.6f}")
    
    with col2:
        st.metric("Dif. Máxima", f"{max_diff_white:.6f}")
    
    with col3:
        st.metric("Dif. Media", f"{mean_diff_white:.6f}")
    
    # Visualización
    with st.expander("📊 Ver comparación del White Standard", expanded=True):
        fig = plot_white_comparison_simple(
            ref_white_spectrum,
            new_white_spectrum,
            diff_white,
            spectral_cols,
            rms_white,
            white_id
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # ==========================================
    # DECISIÓN BASADA EN RMS
    # ==========================================
    threshold_rms = 0.002
    
    # Guardar datos para el informe
    validation_data = {
        'white_id': white_id,
        'ref_spectrum': ref_white_spectrum,
        'new_spectrum': new_white_spectrum,
        'diff': diff_white,
        'rms': rms_white,
        'max_diff': max_diff_white,
        'mean_diff': mean_diff_white,
        'selected_ids': list(common_ids),
        'spectral_cols': spectral_cols,
        'iterations_needed': st.session_state.alignment_iterations,
        'df_ref_val': df_ref_grouped,
        'df_new_val': df_new_grouped,
        'common_ids': list(common_ids),
        'lamp_ref': 'Referencia (Paso 3)',
        'lamp_new': 'Nueva medición'
    }
    
    st.session_state.validation_data = validation_data
    
    if rms_white >= threshold_rms:
        st.session_state.pre_correction_data = {
            'df_ref_val': df_ref_grouped.copy(),
            'df_new_val': df_new_grouped.copy(),
            'common_ids': list(common_ids),
            'spectral_cols': spectral_cols
        }
    
    if rms_white < threshold_rms:
        # ✅ VALIDACIÓN EXITOSA
        render_validation_success(rms_white, white_id)
    else:
        # ⚠️ NECESITA ALINEAMIENTO
        render_alignment_needed(rms_white, white_id)


def render_validation_success(rms, white_id):
    """
    Renderiza resultado de validación exitosa
    """
    st.success(f"""
    ✅ **VALIDACIÓN EXITOSA**
    
    **White Standard ({white_id}):** RMS = {rms:.6f} < 0.002
    
    El equipo está correctamente alineado y listo para usar.
    """)
    
    # Evaluar calidad
    if rms < VALIDATION_THRESHOLDS['excellent']:
        st.success("🌟 **Calidad:** EXCELENTE")
    elif rms < VALIDATION_THRESHOLDS['good']:
        st.success("✅ **Calidad:** MUY BUENO")
    elif rms < VALIDATION_THRESHOLDS['acceptable']:
        st.info("ℹ️ **Calidad:** ACEPTABLE")
    
    # Mostrar iteraciones si hubo
    if st.session_state.alignment_iterations > 0:
        st.info(f"📊 **Iteraciones necesarias:** {st.session_state.alignment_iterations}")
    
    st.markdown("---")
    
    # Guardar status final
    st.session_state.validation_data['final_status'] = 'SUCCESS'
    
    # Botón para generar informe
    st.markdown("### 📄 Generar Informe Final")
    
    render_report_generation()
    
    st.markdown("---")
    
    # Reset
    if st.button("🔄 Finalizar y reiniciar proceso", use_container_width=True):
        st.session_state.unsaved_changes = False
        reset_session_state()
        st.rerun()


def render_alignment_needed(rms, white_id):
    """
    Renderiza resultado cuando necesita alineamiento
    """
    st.warning(f"""
    ⚠️ **ALINEAMIENTO NECESARIO**
    
    **White Standard ({white_id}):** RMS = {rms:.6f} ≥ 0.002
    
    El equipo necesita alineamiento de baseline.
    """)
    
    st.session_state.validation_data['final_status'] = 'NEEDS_ALIGNMENT'
    
    st.markdown("---")
    st.markdown("### ➡️ Opciones")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Opción 1: Continuar Alineamiento")
        st.info("""
        **Recomendado**: Ve al Paso 5 para ajustar el baseline.
        
        En el Paso 5 podrás:
        1. Cargar el baseline actual
        2. Calcular la corrección necesaria
        3. Exportar el baseline corregido
        4. Volver a este paso para validar
        """)
        
        if st.button("➡️ Ir a Alineamiento (Paso 5)", type="primary", use_container_width=True):
            st.session_state.unsaved_changes = False
            go_to_next_step()
    
    with col2:
        st.markdown("#### Opción 2: Finalizar sin cumplir umbral")
        st.error("""
        ⚠️ **No recomendado**: Genera el informe con el estado actual 
        aunque no se cumpla el umbral de RMS < 0.002.
        
        El informe indicará claramente que el alineamiento no fue exitoso.
        """)
        
        if st.button("📄 Generar Informe (sin cumplir umbral)", use_container_width=True):
            st.session_state.validation_data['final_status'] = 'FAILED_THRESHOLD'
            st.session_state.force_report = True
            # No cambiar de paso, solo marcar para mostrar generación de informe
            st.rerun()

def render_report_generation():
    """
    Renderiza sección de generación de informes
    """
    st.info("""
    El informe incluirá:
    - Datos del cliente y equipo
    - Métricas del White Standard
    - Gráficos comparativos
    - Conclusiones
    """)
    
    if 'validation_report_html' not in st.session_state:
        st.session_state.validation_report_html = None
    
    if st.button("📥 Generar Informe", use_container_width=True, type="primary", key="btn_generate_report"):
        try:
            val_data = st.session_state.get('validation_data')
            
            if not val_data:
                st.error("❌ No hay datos de validación disponibles")
                return
            
            # Generar informe
            val_data = st.session_state.get('validation_data')
            baseline_data = st.session_state.get('baseline_data')
            correction_vector = st.session_state.get('correction_vector')
            iterations = val_data.get('iterations_needed', 0)

            if iterations > 0 and baseline_data is not None and correction_vector is not None:
                # Caso 2: Hubo alineamiento
                
                # Usar datos pre-corrección para mostrar medición ANTES del ajuste
                pre_corr = st.session_state.get('pre_correction_data')
                
                if pre_corr:
                    kit_data = {
                        'df': None,
                        'df_ref_grouped': pre_corr['df_ref_val'],      # Referencia (Paso 3)
                        'df_new_grouped': pre_corr['df_new_val'],      # ANTES de corregir
                        'spectral_cols': pre_corr['spectral_cols'],
                        'lamp_ref': val_data['lamp_ref'],
                        'lamp_new': val_data['lamp_new'],
                        'common_ids': pre_corr['common_ids'],
                        'mean_diff': correction_vector                  # Corrección aplicada
                    }
                else:
                    # Fallback si no hay pre_correction_data (no debería pasar)
                    kit_data = {
                        'df': None,
                        'df_ref_grouped': val_data['df_ref_val'],
                        'df_new_grouped': val_data['df_new_val'],
                        'spectral_cols': val_data['spectral_cols'],
                        'lamp_ref': val_data['lamp_ref'],
                        'lamp_new': val_data['lamp_new'],
                        'common_ids': val_data['common_ids'],
                        'mean_diff': correction_vector
                    }
                
                from core.report_generator import generate_validation_report
                html_content = generate_validation_report(
                    kit_data=kit_data,  # No usamos kit_data en nuevo flujo
                    baseline_data=baseline_data,
                    ref_corrected=baseline_data['ref_spectrum'] - correction_vector,
                    origin=baseline_data.get('origin'),
                    validation_data=val_data,
                    mean_diff_before=correction_vector,  # La corrección que se aplicó
                    mean_diff_after=val_data['diff']     # La diferencia final
                )
            else:
                # Caso 1: Sin alineamiento o datos incompletos
                from core.report_generator import generate_partial_report
                html_content = generate_partial_report(
                    kit_data=None,
                    baseline_data=None,
                    ref_corrected=None,
                    origin=None,
                    validation_data=val_data,
                    mean_diff_before=None,
                    mean_diff_after=val_data['diff']
                )
            
            st.session_state.validation_report_html = html_content
            st.success("✅ Informe generado correctamente")
            
        except Exception as e:
            st.error(f"❌ Error al generar informe: {e}")
            import traceback
            st.code(traceback.format_exc())
    
    # Botón de descarga
    if st.session_state.validation_report_html:
        client_data = st.session_state.get('client_data', {})
        filename = f"Informe_{client_data.get('sensor_sn', 'sensor')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        st.download_button(
            "⬇️ Descargar Informe HTML",
            data=st.session_state.validation_report_html.encode("utf-8"),
            file_name=filename,
            mime="text/html",
            use_container_width=True
        )


def plot_white_comparison_simple(ref_spectrum, new_spectrum, diff, spectral_cols, rms, sample_id):
    """
    Gráfico simple de comparación
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(
            f'Espectros de {sample_id} (RMS = {rms:.6f})',
            'Diferencia (Nuevo - Referencia)'
        ),
        vertical_spacing=0.12,
        row_heights=[0.6, 0.4]
    )
    
    channels = list(range(1, len(ref_spectrum) + 1))
    
    # Subplot 1: Espectros
    fig.add_trace(
        go.Scatter(
            x=channels,
            y=ref_spectrum,
            name='Referencia (Paso 3)',
            line=dict(color='blue', width=2)
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=channels,
            y=new_spectrum,
            name='Nueva medición',
            line=dict(color='red', width=2, dash='dash')
        ),
        row=1, col=1
    )
    
    # Subplot 2: Diferencia
    fig.add_trace(
        go.Scatter(
            x=channels,
            y=diff,
            name='Diferencia',
            line=dict(color='orange', width=2),
            fill='tozeroy',
            fillcolor='rgba(255, 165, 0, 0.3)'
        ),
        row=2, col=1
    )
    
    fig.add_hline(y=0, line_dash="dot", line_color="gray", row=2, col=1)
    fig.add_hline(y=0.002, line_dash="dash", line_color="red", opacity=0.5, row=2, col=1)
    fig.add_hline(y=-0.002, line_dash="dash", line_color="red", opacity=0.5, row=2, col=1)
    
    fig.update_xaxes(title_text="Canal espectral", row=2, col=1)
    fig.update_yaxes(title_text="Absorbancia", row=1, col=1)
    fig.update_yaxes(title_text="Diferencia", row=2, col=1)
    
    fig.update_layout(
        height=700,
        showlegend=True,
        hovermode='x unified',
        template='plotly_white'
    )
    
    return fig