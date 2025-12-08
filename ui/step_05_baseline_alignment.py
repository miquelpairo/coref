# -*- coding: utf-8 -*-
"""
Paso 5: Alineamiento de Baseline (Opcional, solo si falla validación)
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
    Renderiza el paso de Alineamiento de Baseline (Paso 5).
    Solo se llega aquí si la validación (Paso 4) indica RMS ≥ 0.002
    """
    st.markdown("## PASO 5 DE 5: Alineamiento de Baseline")
    
    st.info("""
    ### ⚙️ Alineamiento de Baseline
    
    Has llegado aquí porque el RMS del White Standard es ≥ 0.002.
    
    **En este paso:**
    1. Cargas el baseline actual del equipo
    2. Calculamos la corrección necesaria
    3. Exportas el baseline corregido
    4. Lo instalas en el equipo
    5. Vuelves al Paso 4 para validar
    """)
    
    with st.expander("🔍 Ver procedimiento completo", expanded=False):
        st.markdown(INSTRUCTIONS.get('alignment_procedure', 'Procedimiento de alineamiento'))
    
    st.markdown("---")
    
    # ==========================================
    # SECCIÓN 1: CARGAR BASELINE
    # ==========================================
    st.markdown("### 1️⃣ Cargar Baseline Actual")
    st.info("Sube el archivo de baseline actual del equipo (.ref o .csv)")
    baseline_loaded = render_baseline_upload_section()
    
    if not baseline_loaded:
        st.warning("👇 Carga el baseline actual para continuar")
        return
    
    # ==========================================
    # SECCIÓN 2: OBTENER DATOS DE VALIDACIÓN
    # ==========================================
    st.markdown("---")
    st.markdown("### 2️⃣ Datos de Validación")
    
    # Obtener datos del Paso 4
    if 'validation_data' not in st.session_state:
        st.error("❌ No hay datos de validación del Paso 4")
        st.info("Vuelve al Paso 4 para realizar la validación primero")
        return
    
    val_data = st.session_state.validation_data
    diff_white = val_data['diff']
    spectral_cols = val_data['spectral_cols']
    
    st.success(f"✅ Datos de validación cargados (White ID: {val_data['white_id']})")
    st.info(f"📊 RMS detectado: {val_data['rms']:.6f}")
    
    # Mostrar estadísticas de la corrección necesaria
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Corrección máxima", f"{np.max(np.abs(diff_white)):.6f}")
    
    with col2:
        st.metric("Corrección media", f"{np.mean(np.abs(diff_white)):.6f}")
    
    with col3:
        st.metric("Desv. estándar", f"{np.std(diff_white):.6f}")
    
    st.markdown("---")
    
    # ==========================================
    # SECCIÓN 3: APLICAR CORRECCIÓN
    # ==========================================
    st.markdown("### 3️⃣ Aplicar Corrección al Baseline")
    
    baseline_data = st.session_state.baseline_current
    ref_spectrum = baseline_data['spectrum']
    
    # Validar dimensiones
    if len(ref_spectrum) != len(diff_white):
        st.error(f"""
        ❌ Error de dimensiones:
        - Baseline: {len(ref_spectrum)} puntos
        - Corrección: {len(diff_white)} puntos
        """)
        return
    
    # Aplicar corrección
    ref_corrected = apply_baseline_correction(ref_spectrum, diff_white)
    
    st.success("✅ Corrección aplicada al baseline")
    
    # Guardar corrección para compatibilidad
    st.session_state.correction_vector = diff_white
    
    # Comparación visual
    with st.expander("📊 Comparación: Baseline Original vs Corregido", expanded=False):
        fig = plot_baseline_comparison(ref_spectrum, ref_corrected, spectral_cols)
        st.plotly_chart(fig, use_container_width=True)
    
    # Descargar tabla de comparación
    df_comparison = pd.DataFrame({
        "Canal": range(1, len(ref_spectrum) + 1),
        "baseline_original": ref_spectrum,
        "baseline_corregido": ref_corrected,
        "correccion_aplicada": diff_white
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
    
    # ==========================================
    # SECCIÓN 4: EXPORTAR BASELINE CORREGIDO
    # ==========================================
    st.markdown("### 4️⃣ Exportar Baseline Corregido")
    
    col_exp1, col_exp2 = st.columns(2)
    
    # Exportar .REF
    with col_exp1:
        st.markdown("**Formato .ref (binario)**")
        if baseline_data['origin'] == 'ref' and baseline_data['header'] is not None:
            st.info("✅ Cabecera original preservada")
            ref_bytes = export_ref_file(ref_corrected, baseline_data['header'])
            
            original_name = baseline_data['filename']
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            name_parts = original_name.rsplit('.', 1)
            if len(name_parts) == 2:
                new_filename = f"{name_parts[0]}_BLAD_{timestamp}.{name_parts[1]}"
            else:
                new_filename = f"{original_name}_BLAD_{timestamp}"

            st.download_button(
                "📥 Descargar .ref ajustado",
                data=ref_bytes,
                file_name=new_filename,
                mime="application/octet-stream",
                key="download_ref_alignment",
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
        
        original_name = baseline_data['filename']
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name_parts = original_name.rsplit('.', 1)
        if len(name_parts) == 2:
            new_filename_csv = f"{name_parts[0]}_BLAD_{timestamp}.csv"
        else:
            new_filename_csv = f"{original_name}_BLAD_{timestamp}.csv"

        st.download_button(
            "📥 Descargar .csv ajustado",
            data=csv_bytes,
            file_name=new_filename_csv,
            mime="text/csv",
            key="download_csv_alignment",
            use_container_width=True
        )
    
    st.markdown("---")
    
    # ==========================================
    # NAVEGACIÓN: VOLVER A VALIDACIÓN
    # ==========================================
    render_navigation_section()


def render_baseline_upload_section():
    """
    Sección 1: Carga del baseline (.ref o .csv).
    Returns True si el baseline está cargado.
    """
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
                
                # Guardar también en baseline_data para compatibilidad
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
                
                # Guardar también en baseline_data para compatibilidad
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
        
        # Asegurar que baseline_data también esté guardado
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


def render_navigation_section():
    """
    Navegación para volver a validación (Paso 4)
    """
    st.markdown("### ⬅️ Volver a Validación")
    
    st.warning("""
    **⚠️ PRÓXIMOS PASOS:**
    
    1. ✅ Descarga el baseline corregido
    2. ✅ Cópialo al equipo (reemplaza el anterior)
    3. ✅ Reinicia SX Suite
    4. ✅ Haz clic en "Volver a Validación"
    5. ✅ Mide de nuevo el White Standard
    """)
    
    if st.button("⬅️ Volver a Validación (Paso 4)", type="primary", use_container_width=True):
        # Marcar que venimos del alineamiento
        st.session_state.came_from_alignment = True
        st.session_state.unsaved_changes = False
        
        # Volver al paso 4
        st.session_state.step = 4
        st.rerun()