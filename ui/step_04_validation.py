# -*- coding: utf-8 -*-
"""
Paso 4: Validación del Alineamiento (Verificación primero)
VERSIÓN OPTIMIZADA: Todos los mensajes desde config.py
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from config import INSTRUCTIONS, MESSAGES, VALIDATION_THRESHOLDS
from session_manager import (
    has_reference_tsv,
    get_reference_tsv,
    reset_session_state,
    go_to_next_step
)
from core.standards_analysis import create_white_comparison_plot
from core.file_handlers import load_tsv_file, get_spectral_columns
from core.spectral_processing import find_common_samples
from utils.validators import validate_common_samples


def render_validation_step():
    """
    Paso 4: Validación del alineamiento.
    
    Primero verifica si el equipo está correctamente alineado.
    - Si RMS < 0.005: Validación exitosa → Generar informe
    - Si RMS ≥ 0.005: Alineamiento necesario → Ir a Paso 5
    """
    st.markdown("## PASO 4 DE 5: Validación del Alineamiento")
    st.info(INSTRUCTIONS['validation_objective'])
    
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
        rms_val = st.session_state.validation_data['rms']
        st.error(f"""
        ⚠️ **ADVERTENCIA**: Generando informe sin cumplir el umbral de calidad
        
        El RMS actual ({rms_val:.6f}) es mayor que el umbral recomendado (0.002).
        El informe incluirá esta advertencia.
        """)
        
        st.markdown("---")
        render_report_generation()
        
        st.markdown("---")
        if st.button("🔄 Volver a validación", use_container_width=True):
            st.session_state.force_report = False
            st.rerun()
        
        return
    
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
        st.info(INSTRUCTIONS['validation_first_measurement'])
    else:
        iter_num = st.session_state.alignment_iterations
        st.warning(f"""
        **Iteración #{iter_num}:**
        
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
        fig = create_white_comparison_plot(
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
    threshold_rms = 0.005
    
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
        render_validation_success(rms_white, white_id)
    else:
        render_alignment_needed(rms_white, white_id)


def render_validation_success(rms, white_id):
    """
    Renderiza resultado de validación exitosa
    """
    success_msg = INSTRUCTIONS['validation_success_title'].format(white_id=white_id, rms=rms)
    st.success(success_msg)
    
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
    alignment_msg = INSTRUCTIONS['validation_alignment_needed'].format(white_id=white_id, rms=rms)
    st.warning(alignment_msg)
    
    st.session_state.validation_data['final_status'] = 'NEEDS_ALIGNMENT'
    
    st.markdown("---")
    st.markdown("### ➡️ Opciones")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Opción 1: Continuar Alineamiento")
        st.info(INSTRUCTIONS['validation_option_continue'])
        
        if st.button("➡️ Ir a Alineamiento (Paso 5)", type="primary", use_container_width=True):
            st.session_state.unsaved_changes = False
            go_to_next_step()
    
    with col2:
        st.markdown("#### Opción 2: Finalizar sin cumplir umbral")
        st.error(INSTRUCTIONS['validation_option_force'])
        
        if st.button("📄 Generar Informe (sin cumplir umbral)", use_container_width=True):
            st.session_state.validation_data['final_status'] = 'FAILED_THRESHOLD'
            st.session_state.force_report = True
            st.rerun()


def render_report_generation():
    """
    Renderiza sección de generación de informes
    """
    st.info(INSTRUCTIONS['validation_report_intro'])
    
    if 'validation_report_html' not in st.session_state:
        st.session_state.validation_report_html = None
    
    if st.button("📥 Generar Informe", use_container_width=True, type="primary", key="btn_generate_report"):
        try:
            val_data = st.session_state.get('validation_data')
            
            if not val_data:
                st.error("❌ No hay datos de validación disponibles")
                return
            
            baseline_data = st.session_state.get('baseline_data')
            correction_vector = st.session_state.get('correction_vector')
            iterations = val_data.get('iterations_needed', 0)

            if iterations > 0 and baseline_data is not None and correction_vector is not None:
                # Caso: Hubo alineamiento - Generar informe completo
                from core.report_generator import generate_html_report, generate_validation_section, generate_footer
                
                pre_corr = st.session_state.get('pre_correction_data')
                
                if pre_corr:
                    kit_data = {
                        'df': None,
                        'df_ref_grouped': pre_corr['df_ref_val'],
                        'df_new_grouped': pre_corr['df_new_val'],
                        'spectral_cols': pre_corr['spectral_cols'],
                        'lamp_ref': val_data['lamp_ref'],
                        'lamp_new': val_data['lamp_new'],
                        'common_ids': pre_corr['common_ids'],
                        'mean_diff': correction_vector
                    }
                else:
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
                
                # Generar informe completo (baseline adjustment)
                html_content = generate_html_report(
                    kit_data=kit_data,
                    baseline_data=baseline_data,
                    ref_corrected=baseline_data['ref_spectrum'] - correction_vector,
                    origin=baseline_data.get('origin'),
                    validation_data=val_data
                )
                
                # Añadir sección de validación
                validation_html = generate_validation_section(
                    val_data,
                    mean_diff_before=correction_vector,
                    mean_diff_after=val_data['diff']
                )
                
                # Insertar validación antes del footer
                footer_html = generate_footer()
                html_content = html_content.replace(footer_html, validation_html + footer_html)
                
            else:
                # Caso: Sin alineamiento - Generar informe parcial (solo validación)
                from core.report_generator import generate_partial_report
                
                mean_diff_before = np.zeros_like(val_data['diff'])
                
                html_content = generate_partial_report(
                    kit_data=None,
                    baseline_data=None,
                    ref_corrected=None,
                    origin=None,
                    validation_data=val_data,
                    mean_diff_before=mean_diff_before,
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
        filename = f"BASELINE_CHECK_REPORT_{client_data.get('sensor_sn', 'sensor')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        st.download_button(
            "⬇️ Descargar Informe HTML",
            data=st.session_state.validation_report_html.encode("utf-8"),
            file_name=filename,
            mime="text/html",
            use_container_width=True
        )