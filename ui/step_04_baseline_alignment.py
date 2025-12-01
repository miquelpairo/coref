# -*- coding: utf-8 -*-
"""
Paso 4: Alineamiento de Baseline
Fusiona la funcionalidad de los antiguos pasos 4, 5 y 6
"""
import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime
from config import INSTRUCTIONS, MESSAGES
from session_manager import (
    has_reference_tsv,
    get_reference_tsv,
    go_to_next_step,
    save_kit_data,
    update_kit_data_with_correction
)
from core.file_handlers import (
    load_tsv_file, 
    get_spectral_columns,
    load_ref_file,
    load_csv_baseline,
    export_ref_file,
    export_csv_file
)
from core.spectral_processing import (
    find_common_samples,
    calculate_spectral_correction,
    apply_baseline_correction
)
from utils.plotting import (
    plot_kit_spectra,
    plot_correction_differences,
    plot_baseline_spectrum,
    plot_baseline_comparison
)
from utils.validators import validate_common_samples, validate_dimension_match


def render_baseline_alignment_step():
    """
    Renderiza el paso de Alineamiento de Baseline (Paso 4).
    Integra: carga de baseline, TSV ref/nuevo, cálculo de corrección y exportación.
    """
    st.markdown("## PASO 4 DE 5: Alineamiento de Baseline")
    
    # Usar instrucciones desde config
    st.info(INSTRUCTIONS['alignment_intro'])
    
    with st.expander("📋 Ver procedimiento completo", expanded=False):
        st.markdown(INSTRUCTIONS['alignment_procedure'])
    
    st.markdown("---")
    
    # ==========================================
    # SECCIÓN 1: CARGAR BASELINE
    # ==========================================
    st.markdown("### 1️⃣ Cargar Baseline Nueva")
    st.info(INSTRUCTIONS['alignment_baseline_upload'])
    baseline_loaded = render_baseline_upload_section()
    
    if not baseline_loaded:
        st.warning("👇 Carga el baseline nuevo para continuar")
        return
    
    # ==========================================
    # SECCIÓN 2: TSV REFERENCIA (PRE-CARGADO)
    # ==========================================
    st.markdown("---")
    st.markdown("### 2️⃣ TSV de Referencia")
    st.info(INSTRUCTIONS['alignment_ref_tsv'])
    ref_tsv_loaded = render_reference_tsv_section()
    
    if not ref_tsv_loaded:
        st.warning("⚠️ No hay TSV de referencia disponible. Vuelve al Paso 3 para cargarlo.")
        return
    
    # ==========================================
    # SECCIÓN 3: TSV NUEVA LÁMPARA
    # ==========================================
    st.markdown("---")
    st.markdown("### 3️⃣ TSV de Nueva Medición")
    st.info(INSTRUCTIONS['alignment_new_tsv'])
    new_tsv_loaded = render_new_tsv_section()
    
    if not new_tsv_loaded:
        st.warning("👇 Carga el TSV de la nueva medición para continuar")
        return
    
    # ==========================================
    # SECCIÓN 4: SELECCIÓN DE MUESTRAS
    # ==========================================
    st.markdown("---")
    st.markdown("### 4️⃣ Selección de Muestras")
    render_sample_selection_section()
    
    # ==========================================
    # SECCIÓN 5: VISUALIZACIÓN ESPECTROS
    # ==========================================
    st.markdown("---")
    st.markdown("### 5️⃣ Visualización de Espectros")
    render_spectra_visualization_section()
    
    # ==========================================
    # SECCIÓN 6: CÁLCULO DE CORRECCIÓN
    # ==========================================
    st.markdown("---")
    st.markdown("### 6️⃣ Cálculo de Corrección")
    correction_calculated = render_correction_calculation_section()
    
    if not correction_calculated:
        return
    
    # ==========================================
    # SECCIÓN 7: APLICAR Y EXPORTAR BASELINE CORREGIDO
    # ==========================================
    st.markdown("---")
    st.markdown("### 7️⃣ Baseline Corregido")
    render_corrected_baseline_section()
    
    # ==========================================
    # NAVEGACIÓN
    # ==========================================
    st.markdown("---")
    render_navigation_section()

def render_baseline_upload_section():
    """
    Sección 1: Carga del baseline (.ref o .csv).
    Returns True si el baseline está cargado.
    """
    st.info("Sube el archivo de baseline actual del equipo (.ref o .csv)")
    
    baseline_file = st.file_uploader(
        "Archivo baseline",
        type=["ref", "csv"],
        key="baseline_upload_alignment"
    )
    
    if baseline_file:
        st.session_state.unsaved_changes = True
        
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
                
                # Guardar en session_state temporal
                st.session_state.baseline_current = {
                    'spectrum': ref_spectrum,
                    'header': header,
                    'df_baseline': None,
                    'origin': 'ref',
                    'filename': baseline_file.name
                }
                
                # ⭐ NUEVO: Guardar también en baseline_data para compatibilidad con validación
                from session_manager import save_baseline_data
                save_baseline_data(
                    ref_spectrum=ref_spectrum,
                    header=header,
                    df_baseline=None,
                    origin='ref'
                )
                
                with st.expander("📊 Ver espectro del baseline", expanded=False):
                    fig = plot_baseline_spectrum(ref_spectrum, title="Baseline Actual")
                    st.plotly_chart(fig, use_container_width=True)
                
                return True
                
            elif file_extension == 'csv':
                df_baseline, ref_spectrum = load_csv_baseline(baseline_file)
                
                st.success("✅ Baseline .csv cargado correctamente")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("NIR Pixels", int(df_baseline['nir_pixels'].iloc[0]))
                    st.metric("Timestamp", df_baseline['time_stamp'].iloc[0])
                
                with col2:
                    st.metric("Sys Temp (°C)", f"{df_baseline['sys_temp'].iloc[0]:.2f}")
                    st.metric("Puntos espectrales", len(ref_spectrum))
                
                # Guardar en session_state temporal
                st.session_state.baseline_current = {
                    'spectrum': ref_spectrum,
                    'header': None,
                    'df_baseline': df_baseline,
                    'origin': 'csv',
                    'filename': baseline_file.name
                }
                
                # ⭐ NUEVO: Guardar también en baseline_data para compatibilidad con validación
                from session_manager import save_baseline_data
                save_baseline_data(
                    ref_spectrum=ref_spectrum,
                    header=None,
                    df_baseline=df_baseline,
                    origin='csv',
                )
                                
                with st.expander("📊 Ver espectro del baseline", expanded=False):
                    fig = plot_baseline_spectrum(ref_spectrum, title="Baseline Actual")
                    st.plotly_chart(fig, use_container_width=True)
                
                return True
                
        except Exception as e:
            st.error(f"❌ Error al cargar baseline: {str(e)}")
            import traceback
            st.error(traceback.format_exc())
            return False
    
    # Si ya existe baseline cargado previamente
    if 'baseline_current' in st.session_state:
        st.success("✅ Baseline ya cargado")
        
        # ⭐ NUEVO: Asegurar que baseline_data también esté guardado
        if 'baseline_data' not in st.session_state:
            from session_manager import save_baseline_data
            baseline_current = st.session_state.baseline_current
            save_baseline_data(
                ref_spectrum=baseline_current['spectrum'],
                header=baseline_current.get('header'),
                df_baseline=baseline_current.get('df_baseline'),
                origin=baseline_current['origin']
            )
        
        return True
    
    return False


def render_reference_tsv_section():
    """
    Sección 2: TSV de referencia (pre-cargado desde Paso 3).
    Returns True si hay TSV de referencia disponible.
    """
    if has_reference_tsv():
        ref_data = get_reference_tsv()
        df_ref = ref_data['df']
        spectral_cols = ref_data['spectral_cols']
        
        st.success(f"✅ TSV de referencia cargado desde Paso 3 ({len(df_ref)} mediciones)")
        
        # Mostrar preview
        with st.expander("🔍 Ver datos del TSV de referencia", expanded=False):
            st.dataframe(df_ref[['ID', 'Note']].head(10), use_container_width=True)
            st.write(f"**Total de filas:** {len(df_ref)}")
            st.write(f"**Canales espectrales:** {len(spectral_cols)}")
        
        # Opción de override (cargar otro archivo)
        if st.checkbox("🔄 Cargar otro archivo TSV de referencia", key="override_ref_tsv"):
            new_ref_file = st.file_uploader(
                "Nuevo archivo TSV de referencia",
                type=["tsv"],
                key="ref_tsv_override"
            )
            
            if new_ref_file:
                try:
                    df_ref_new = load_tsv_file(new_ref_file)
                    spectral_cols_new = get_spectral_columns(df_ref_new)
                    
                    st.success(f"✅ Nuevo TSV cargado ({len(df_ref_new)} mediciones)")
                    
                    # Actualizar session_state
                    from session_manager import save_reference_tsv
                    save_reference_tsv(df_ref_new, spectral_cols_new)
                    
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error al cargar nuevo TSV: {str(e)}")
        
        return True
    else:
        st.error("❌ No hay TSV de referencia disponible")
        st.info("Vuelve al Paso 3 para cargar el archivo TSV de referencia")
        return False


def render_new_tsv_section():
    """
    Sección 3: TSV de nueva medición.
    Returns True si está cargado.
    """
    st.info("Sube el TSV con las mediciones realizadas con el baseline actual")
    
    new_file = st.file_uploader(
        "Archivo TSV nueva medición",
        type=["tsv"],
        key="new_tsv_upload"
    )
    
    if new_file:
        st.session_state.unsaved_changes = True
        
        try:
            df_new = load_tsv_file(new_file)
            spectral_cols_new = get_spectral_columns(df_new)
            
            st.success(f"✅ TSV cargado correctamente ({len(df_new)} mediciones)")
            
            # Mostrar preview
            with st.expander("🔍 Ver datos del TSV", expanded=False):
                st.dataframe(df_new[['ID', 'Note']].head(10), use_container_width=True)
                st.write(f"**Total de filas:** {len(df_new)}")
                st.write(f"**Canales espectrales:** {len(spectral_cols_new)}")
            
            # Validar dimensiones con baseline
            baseline_length = len(st.session_state.baseline_current['spectrum'])
            
            if baseline_length != len(spectral_cols_new):
                st.error(f"""
                ❌ **Error de dimensiones:**
                - Baseline: {baseline_length} puntos
                - TSV: {len(spectral_cols_new)} canales
                
                Los archivos deben tener el mismo número de canales espectrales.
                """)
                return False
            
            st.success(f"✅ Dimensiones validadas: {len(spectral_cols_new)} canales")
            
            # Guardar en session_state temporal
            st.session_state.new_tsv = {
                'df': df_new,
                'spectral_cols': spectral_cols_new
            }
            
            return True
            
        except Exception as e:
            st.error(f"❌ Error al cargar TSV: {str(e)}")
            import traceback
            st.error(traceback.format_exc())
            return False
    
    # Si ya existe
    if 'new_tsv' in st.session_state:
        st.success("✅ TSV de nueva medición ya cargado")
        return True
    
    return False


def render_sample_selection_section():
    """
    Sección 4: Selección de muestras comunes para calcular la corrección.
    """
    # Obtener datos
    ref_data = get_reference_tsv()
    df_ref = ref_data['df']
    spectral_cols = ref_data['spectral_cols']
    
    df_new = st.session_state.new_tsv['df']
    
    # ⭐ CRÍTICO: Filtrar WSTD ANTES de agrupar
    df_ref_kit = df_ref[df_ref["ID"].str.upper() != "WSTD"].copy()
    df_new_kit = df_new[df_new["ID"].str.upper() != "WSTD"].copy()
    
    # Verificar que haya muestras después del filtrado
    if len(df_ref_kit) == 0:
        st.error("❌ No hay muestras en el archivo de referencia (todas son WSTD)")
        return
    
    if len(df_new_kit) == 0:
        st.error("❌ No hay muestras en el archivo nuevo (todas son WSTD)")
        return
    
    # Convertir a numérico
    df_ref_kit[spectral_cols] = df_ref_kit[spectral_cols].apply(pd.to_numeric, errors="coerce")
    df_new_kit[spectral_cols] = df_new_kit[spectral_cols].apply(pd.to_numeric, errors="coerce")
    
    # Agrupar por ID (promedio)
    df_ref_grouped = df_ref_kit.groupby("ID")[spectral_cols].mean()
    df_new_grouped = df_new_kit.groupby("ID")[spectral_cols].mean()
    
    # Encontrar muestras comunes
    common_ids = find_common_samples(df_ref_grouped, df_new_grouped)
    
    if not validate_common_samples(common_ids):
        return
    
    st.success(f"✅ {len(common_ids)} muestras comunes encontradas")
    
    # ⭐ CRÍTICO: Filtrar los DataFrames agrupados SOLO con IDs comunes
    df_ref_grouped = df_ref_grouped.loc[common_ids]
    df_new_grouped = df_new_grouped.loc[common_ids]
    
    # Guardar datos agrupados en session_state
    st.session_state.alignment_data = {
        'df_ref_grouped': df_ref_grouped,
        'df_new_grouped': df_new_grouped,
        'spectral_cols': spectral_cols,
        'common_ids': list(common_ids)
    }
    
    # Inicializar selección
    if 'selected_ids' not in st.session_state:
        st.session_state.selected_ids = list(common_ids)
    
    if 'pending_selection' not in st.session_state:
        st.session_state.pending_selection = list(common_ids)
    
    # Tabla de selección
    df_samples = pd.DataFrame({
        'ID': list(common_ids),
        'Usar en corrección': [
            i in st.session_state.pending_selection 
            for i in common_ids
        ]
    })
    
    with st.expander("🔍 Seleccionar muestras para el cálculo", expanded=True):
        with st.form("form_select_samples_alignment", clear_on_submit=False):
            edited = st.data_editor(
                df_samples,
                use_container_width=True,
                hide_index=True,
                disabled=['ID'],
                key="editor_select_samples_alignment"
            )
            
            col_a, col_b, col_c, col_d = st.columns([1, 1, 1, 2])
            btn_all = col_a.form_submit_button("Seleccionar todo")
            btn_none = col_b.form_submit_button("Deseleccionar todo")
            btn_invert = col_c.form_submit_button("Invertir selección")
            btn_confirm = col_d.form_submit_button("Confirmar selección", type="primary")
        
        if btn_all:
            st.session_state.pending_selection = list(common_ids)
            st.rerun()
        
        if btn_none:
            st.session_state.pending_selection = []
            st.rerun()
        
        if btn_invert:
            inverted = [i for i in common_ids if i not in st.session_state.pending_selection]
            st.session_state.pending_selection = inverted
            st.rerun()
        
        if btn_confirm:
            pending = edited.loc[edited['Usar en corrección'], 'ID'].tolist()
            st.session_state.pending_selection = pending
            st.session_state.selected_ids = pending
            st.success(f"✅ Selección confirmada: {len(st.session_state.selected_ids)} muestras")
        else:
            if isinstance(edited, pd.DataFrame):
                try:
                    pending = edited.loc[edited['Usar en corrección'], 'ID'].tolist()
                    st.session_state.pending_selection = pending
                except Exception:
                    pass
        
        st.caption(
            f"Pendientes: {len(st.session_state.pending_selection)} - "
            f"Confirmadas: {len(st.session_state.get('selected_ids', []))}"
        )


def render_spectra_visualization_section():
    """
    Sección 5: Visualización de espectros comparativos.
    """
    if 'alignment_data' not in st.session_state:
        return
    
    data = st.session_state.alignment_data
    df_ref_grouped = data['df_ref_grouped']
    df_new_grouped = data['df_new_grouped']
    spectral_cols = data['spectral_cols']
    common_ids = data['common_ids']
    
    selected_ids = st.session_state.get('selected_ids', list(common_ids))
    ids_to_plot = selected_ids if len(selected_ids) > 0 else list(common_ids)
    
    with st.expander("📊 Ver espectros comparativos", expanded=False):
        if len(ids_to_plot) < len(common_ids):
            st.info(f"Mostrando {len(ids_to_plot)} de {len(common_ids)} muestras (solo seleccionadas)")
        
        fig = plot_kit_spectra(
            df_ref_grouped, df_new_grouped,
            spectral_cols, 
            "Referencia", "Nueva",
            ids_to_plot
        )
        st.plotly_chart(fig, use_container_width=True)


def render_correction_calculation_section():
    """
    Sección 6: Cálculo automático de la corrección.
    Returns True si la corrección se calculó correctamente.
    """
    if 'alignment_data' not in st.session_state:
        return False
    
    data = st.session_state.alignment_data
    df_ref_grouped = data['df_ref_grouped']
    df_new_grouped = data['df_new_grouped']
    common_ids = data['common_ids']
    
    # Obtener muestras seleccionadas
    ids_for_corr = st.session_state.get('selected_ids', list(common_ids))
    
    if len(ids_for_corr) == 0:
        st.warning("⚠️ No has seleccionado ninguna muestra. Se usarán todas por defecto.")
        ids_for_corr = list(common_ids)
    
    # Calcular corrección
    mean_diff = calculate_spectral_correction(
        df_ref_grouped, 
        df_new_grouped, 
        ids_for_corr
    )
    
    st.success(f"✅ Corrección calculada usando {len(ids_for_corr)} muestras")
    
    # Estadísticas
    col1, col2, col3 = st.columns(3)
    
    with col1:
        max_corr = np.max(np.abs(mean_diff))
        st.metric("Corrección máxima", f"{max_corr:.6f}")
    
    with col2:
        mean_corr = np.mean(np.abs(mean_diff))
        st.metric("Corrección media", f"{mean_corr:.6f}")
    
    with col3:
        std_corr = np.std(mean_diff)
        st.metric("Desviación estándar", f"{std_corr:.6f}")
    
    # Guardar corrección
    st.session_state.correction_vector = mean_diff
    
    # ⭐ NUEVO: Guardar también en formato kit_data para compatibilidad con validación
    save_kit_data_for_validation()
    
    # Gráfico de corrección
    with st.expander("📊 Ver vector de corrección", expanded=False):
        fig = plot_correction_differences(
            build_correction_dataframe(df_ref_grouped, df_new_grouped, mean_diff, common_ids),
            ids_for_corr,
            ids_for_corr
        )
        st.plotly_chart(fig, use_container_width=True)
    
    return True


def build_correction_dataframe(df_ref_grouped, df_new_grouped, mean_diff, common_ids):
    """
    Construye DataFrame con detalles de la corrección.
    """
    df_diff = pd.DataFrame({"Canal": range(1, len(mean_diff) + 1)})
    
    for id_ in common_ids:
        df_diff[f"REF_{id_}"] = df_ref_grouped.loc[id_].values
        df_diff[f"NEW_{id_}"] = df_new_grouped.loc[id_].values
        df_diff[f"DIF_{id_}"] = (
            df_ref_grouped.loc[id_].values - df_new_grouped.loc[id_].values
        )
    
    df_diff["CORRECCION_PROMEDIO"] = mean_diff
    
    return df_diff


def render_corrected_baseline_section():
    """
    Sección 7: Aplicar corrección y exportar baseline corregido.
    """
    if 'correction_vector' not in st.session_state:
        st.warning("⚠️ Primero debes calcular la corrección")
        return
    
    baseline_data = st.session_state.baseline_current
    ref_spectrum = baseline_data['spectrum']
    mean_diff = st.session_state.correction_vector
    
    # Aplicar corrección
    ref_corrected = apply_baseline_correction(ref_spectrum, mean_diff)
    
    st.success("✅ Corrección aplicada al baseline")
    
    # Mostrar instrucciones finales
    st.info(INSTRUCTIONS['alignment_final'])
    
    # Comparación visual
    with st.expander("📊 Comparación: Baseline Original vs Corregido", expanded=False):
        spectral_cols = st.session_state.alignment_data['spectral_cols']
        fig = plot_baseline_comparison(ref_spectrum, ref_corrected, spectral_cols)
        st.plotly_chart(fig, use_container_width=True)
    
    # Descargar tabla de comparación
    df_comparison = pd.DataFrame({
        "Canal": range(1, len(ref_spectrum) + 1),
        "baseline_original": ref_spectrum,
        "baseline_corregido": ref_corrected,
        "correccion_aplicada": mean_diff
    })
    
    csv_comp = io.StringIO()
    df_comparison.to_csv(csv_comp, index=False)
    
    st.download_button(
        "📥 Descargar comparación (CSV)",
        data=csv_comp.getvalue(),
        file_name=f"comparacion_baseline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )
    
    st.markdown("---")
    st.markdown("#### 💾 Exportar Baseline Corregido")
    
    col_exp1, col_exp2 = st.columns(2)
    
    # Exportar .REF
    with col_exp1:
        st.markdown("**Formato .ref (binario)**")
        if baseline_data['origin'] == 'ref' and baseline_data['header'] is not None:
            st.info("✅ Cabecera original preservada")
            ref_bytes = export_ref_file(ref_corrected, baseline_data['header'])
            # Generar nombre conservando el original con NEW_timestamp
            original_name = baseline_data['filename']
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            name_parts = original_name.rsplit('.', 1)  # Separar nombre y extensión
            if len(name_parts) == 2:
                new_filename = f"{name_parts[0]}_BLAD_{timestamp}.{name_parts[1]}"
            else:
                new_filename = f"{original_name}_BLAD_{timestamp}"

            st.download_button(
                "📥 Descargar .ref ajustado",
                data=ref_bytes,
                file_name=new_filename,
                mime="application/octet-stream",
                key="download_ref_offset",
                use_container_width=True
            )
        else:
            st.warning("⚠️ No hay cabecera original (archivo no era .ref)")
    
    # Exportar .CSV
    with col_exp2:
        st.markdown("**Formato .csv (nuevo software)**")
        if baseline_data['origin'] == 'csv' and baseline_data['df_baseline'] is not None:
            st.info("✅ Metadatos originales preservados")
            csv_bytes = export_csv_file(ref_corrected, df_baseline=baseline_data['df_baseline'])
        else:
            st.warning("ℹ️ Usando metadatos por defecto")
            csv_bytes = export_csv_file(ref_corrected)
        
        # Generar nombre conservando el original con NEW_timestamp
        original_name = baseline_data['filename']
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name_parts = original_name.rsplit('.', 1)  # Separar nombre y extensión
        if len(name_parts) == 2:
            new_filename_csv = f"{name_parts[0]}_BLAD_{timestamp}.{name_parts[1]}"
        else:
            new_filename_csv = f"{original_name}_BLAD_{timestamp}"

        st.download_button(
            "📥 Descargar .csv ajustado",
            data=csv_bytes,
            file_name=new_filename_csv,
            mime="text/csv",
            key="download_csv_offset",
            use_container_width=True
        )
    


def render_navigation_section():
    """
    Navegación obligatoria al paso de verificación.
    """
    st.markdown("### ➡️ Siguiente Paso: Verificación Obligatoria")
    
    st.info("""
    **Paso 5 - Verificación de la baseline:**
    
    Para completar el proceso, debes verificar el ajuste midiendo nuevamente 
    las muestras de control con el baseline corregido aplicado.
    
    ⚠️ **Este paso es obligatorio** para validar la corrección y generar el informe final.
    """)
    
    if st.button("➡️ Ir a Verificación (Paso 5)", type="primary", use_container_width=True):
        st.session_state.unsaved_changes = False
        go_to_next_step()

def save_kit_data_for_validation():
    """
    Guarda los datos en formato kit_data para compatibilidad con el paso de validación.
    """
    if 'alignment_data' not in st.session_state:
        return
    
    if 'new_tsv' not in st.session_state:
        return
    
    if 'correction_vector' not in st.session_state:
        return
    
    # Preparar kit_data en el formato que espera validación
    alignment_data = st.session_state.alignment_data
    
    # Guardar usando la función de session_manager
    save_kit_data(
        df=st.session_state.new_tsv['df'],
        df_ref_grouped=alignment_data['df_ref_grouped'],
        df_new_grouped=alignment_data['df_new_grouped'],
        spectral_cols=alignment_data['spectral_cols'],
        lamp_ref='Referencia',
        lamp_new='Nueva',
        common_ids=alignment_data['common_ids']
    )
    
    # Y también guardar mean_diff
    update_kit_data_with_correction(st.session_state.correction_vector)