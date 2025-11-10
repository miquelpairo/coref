# -*- coding: utf-8 -*-
"""
Paso 6: Cargar Baseline, Aplicar Corrección y Exportar (OPCIONAL)
"""
import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime
from config import INSTRUCTIONS, MESSAGES
from session_manager import (
    has_kit_data,
    save_baseline_data,
    has_baseline_data,
    has_correction_data,
    reset_session_state
)
from core.file_handlers import (
    load_ref_file, 
    load_csv_baseline,
    export_ref_file,
    export_csv_file
)
from core.spectral_processing import (
    apply_baseline_correction,
    simulate_corrected_spectra
)
from core.report_generator import generate_html_report
from utils.validators import validate_dimension_match
from utils.plotting import (
    plot_baseline_spectrum,
    plot_baseline_comparison,
    plot_corrected_spectra_comparison
)


def render_baseline_and_export_step():
    """
    Renderiza el paso combinado de baseline y exportacion (Paso 6).
    Este paso es completamente OPCIONAL e INDEPENDIENTE.
    """
    st.markdown("## PASO 6 DE 7: Cargar Baseline, Aplicar Corrección y Exportar")
    
    st.info("""
    ### ℹ️ Este paso es OPCIONAL e INDEPENDIENTE
    - ✅ **Cargar baseline y aplicar corrección** (si ya tienes Paso 5)
    - ⏭️ **Omitir este paso**
    - 📄 **Generar informe** con los datos disponibles
    """)

    has_kit  = has_kit_data()
    has_corr = has_correction_data()

    # Panel de estado
    with st.expander("Estado de dependencias", expanded=False):
        st.write(f"- Paso 4 (Standard Kit): {'✅ disponible' if has_kit else '❌ no cargado'}")
        st.write(f"- Paso 5 (Corrección):   {'✅ disponible' if has_corr else '❌ no calculada'}")

    # ⚠️ NO accedemos a st.session_state.kit_data si no hay kit
    if has_kit:
        kit_data = st.session_state.kit_data
        lamp_new = kit_data.get('lamp_new', 'Nueva')
        spectral_cols = kit_data.get('spectral_cols', None)
    else:
        kit_data = None
        lamp_new = "Nueva"
        spectral_cols = None  # sin TSV no se puede validar longitud

    # SECCIÓN 1: CARGAR BASELINE (siempre disponible)
    st.markdown("### Paso 6.1: Cargar Baseline (Opcional)")
    render_baseline_upload_section(lamp_new, spectral_cols)

    # SECCIÓN 2: APLICAR CORRECCIÓN+EXPORTAR solo cuando hay baseline + kit + corrección
    if has_baseline_data():
        st.markdown("---")
        st.markdown("### Paso 6.2: Aplicar Corrección y Exportar")

        if has_kit and has_corr:
            render_correction_and_export_section()
        else:
            st.warning("Para aplicar la corrección necesitas **Standard Kit (Paso 4)** y **Corrección (Paso 5)**.")
            render_skip_step_section()
    else:
        st.markdown("---")
        render_skip_step_section()


def render_baseline_upload_section(lamp_new, spectral_cols):
    """
    Renderiza la sección de carga de baseline (.ref o .csv).
    Puede ejecutarse incluso si no hay datos del Standard Kit,
    en cuyo caso no se valida el número de canales.
    """
    # === Instrucciones dinámicas ===
    if spectral_cols is None:
        st.info("""
        📁 **Carga un archivo de baseline (.ref o .csv)**  
        No se validará el número de canales porque aún no se han cargado
        los archivos del Standard Kit (Paso 4).
        """)
    else:
        instructions_text = INSTRUCTIONS['baseline_load'].format(
            n_channels=len(spectral_cols)
        )
        st.info(instructions_text)
    
    # === Uploader ===
    baseline_file = st.file_uploader(
        "Sube el archivo baseline (.ref o .csv)",
        type=["ref", "csv"],
        key="baseline_upload"
    )
    
    if baseline_file:
        # Marcar cambios sin guardar
        st.session_state.unsaved_changes = True
        
        file_extension = baseline_file.name.split('.')[-1].lower()
        
        try:
            if file_extension == 'ref':
                process_ref_file(baseline_file, spectral_cols, lamp_new)
            elif file_extension == 'csv':
                process_csv_file(baseline_file, spectral_cols, lamp_new)
            else:
                st.error("❌ Tipo de archivo no reconocido. Usa .ref o .csv.")
        except Exception as e:
            st.error(f"❌ Error al procesar el archivo: {str(e)}")
            import traceback
            st.error(traceback.format_exc())



def process_ref_file(file, spectral_cols, lamp_new):
    """
    Procesa un archivo .ref de baseline.
    """
    header, ref_spectrum = load_ref_file(file)
    
    st.success(MESSAGES['success_file_loaded'])
    
    # Mostrar informacion de la cabecera
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Valores de cabecera:**")
        st.write(f"X1 = {header[0]:.6e}")
        st.write(f"X2 = {header[1]:.6e}")
        st.write(f"X3 = {header[2]:.6e}")
    
    with col2:
        st.metric("Puntos espectrales", len(ref_spectrum))
        st.write("**Primeros 5 valores:**")
        st.write(ref_spectrum[:5])
    
    # Validar dimensiones
    if not validate_and_display_dimensions(len(ref_spectrum), len(spectral_cols)):
        return
    
    # Visualizar baseline en expander
    with st.expander("📊 Ver espectro del baseline cargado", expanded=False):
        fig = plot_baseline_spectrum(ref_spectrum, title="Baseline Cargado")
        st.plotly_chart(fig, use_container_width=True)
    
    # Guardar datos
    save_baseline_data(
        ref_spectrum=ref_spectrum,
        header=header,
        df_baseline=None,
        origin='ref'
    )
    
    st.success("Baseline cargado correctamente. Continúa con la aplicación de la corrección.")


def process_csv_file(file, spectral_cols, lamp_new):
    """
    Procesa un archivo .csv de baseline.
    """
    df_baseline, ref_spectrum = load_csv_baseline(file)
    
    st.success(MESSAGES['success_file_loaded'])
    
    # Mostrar metadatos
    nir_pixels = int(df_baseline['nir_pixels'].iloc[0])
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("NIR Pixels", nir_pixels)
        st.metric("Timestamp", df_baseline['time_stamp'].iloc[0])
    
    with col2:
        st.metric("Sys Temp (°C)", f"{df_baseline['sys_temp'].iloc[0]:.2f}")
        st.metric("TEC Temp (°C)", f"{df_baseline['tec_temp'].iloc[0]:.2f}")
    
    with col3:
        st.metric("Lamp Time", df_baseline['lamp_time'].iloc[0])
        st.metric("Puntos data", len(ref_spectrum))
    
    # Verificar consistencia interna
    if nir_pixels != len(ref_spectrum):
        st.warning(
            f"Inconsistencia: nir_pixels ({nir_pixels}) != "
            f"longitud data ({len(ref_spectrum)})"
        )
    
    # Validar dimensiones
    if not validate_and_display_dimensions(len(ref_spectrum), len(spectral_cols)):
        return
    
    # Visualizar baseline en expander
    with st.expander("📊 Ver espectro del baseline cargado", expanded=False):
        fig = plot_baseline_spectrum(ref_spectrum, title="Baseline")
        st.plotly_chart(fig, use_container_width=True)
    
    # Guardar datos
    save_baseline_data(
        ref_spectrum=ref_spectrum,
        header=None,
        df_baseline=df_baseline,
        origin='csv'
    )
    
    st.success("Baseline cargado correctamente. Continúa con la aplicación de la corrección.")


def validate_and_display_dimensions(baseline_length, tsv_length):
    """
    Valida dimensiones. Si tsv_length es None, no valida y deja continuar.
    """
    if tsv_length is None:
        st.info(f"No hay TSV del Standard Kit para validar canales. Puntos del baseline: {baseline_length}.")
        return True

    if not validate_dimension_match(baseline_length, tsv_length):
        error_msg = MESSAGES['error_dimension_mismatch'].format(
            baseline_points=baseline_length,
            tsv_channels=tsv_length
        )
        st.error(error_msg)
        return False
    else:
        success_msg = MESSAGES['success_dimension_match'].format(
            n_points=baseline_length
        )
        st.success(success_msg)
        return True


def render_skip_step_section():
    """
    Renderiza la sección para omitir este paso y continuar.
    """
    st.markdown("### ⏭️ Omitir este paso")
    
    st.info("""
    **Si decides omitir la carga y aplicación del baseline:**
    
    - Los datos de la corrección calculada se mantienen guardados (si existen)
    - Puedes volver a este paso más tarde si lo necesitas
    - Puedes continuar a validación o generar el informe con los datos actuales
    """)
    
    # Mostrar botón de informe parcial
    render_report_section_standalone()
    
    st.markdown("---")
    col_skip, col_restart = st.columns([3, 1])
    
    with col_skip:
        if st.button("⏭️ Omitir y continuar a Validación", type="primary", use_container_width=True):
            st.session_state.unsaved_changes = False
            from session_manager import go_to_next_step
            go_to_next_step()
            st.rerun()
    
    with col_restart:
        if st.button("🔄 Reiniciar proceso", use_container_width=True):
            st.session_state.unsaved_changes = False
            reset_session_state()
            st.rerun()


def render_correction_and_export_section():
    """
    Renderiza la seccion de aplicacion de correccion y exportacion.
    """
    # Obtener datos
    kit_data = st.session_state.kit_data
    baseline_data = st.session_state.baseline_data
    
    df_ref_grouped = kit_data['df_ref_grouped']
    df_new_grouped = kit_data['df_new_grouped']
    spectral_cols = kit_data['spectral_cols']
    lamp_ref = kit_data['lamp_ref']
    lamp_new = kit_data['lamp_new']
    common_ids = kit_data['common_ids']
    mean_diff = kit_data['mean_diff']
    df = kit_data['df']
    
    ref_spectrum = baseline_data['ref_spectrum']
    header = baseline_data['header']
    df_baseline = baseline_data['df_baseline']
    origin = baseline_data['origin']
    
    # Aplicar correccion
    ref_corrected = apply_baseline_correction(ref_spectrum, mean_diff)
    st.success(MESSAGES['success_correction_applied'])
    
    # Comparacion de valores
    with st.expander("📋 Ver comparación de valores del baseline", expanded=False):
        render_baseline_comparison_values(ref_spectrum, ref_corrected)
    
    # Visualizacion comparativa en expander
    with st.expander("📊 Ver Comparación: Baseline Original vs Corregido", expanded=False):
        st.markdown("#### Comparación: Baseline Original vs Corregido")
        fig_comp = plot_baseline_comparison(ref_spectrum, ref_corrected, spectral_cols)
        st.plotly_chart(fig_comp, use_container_width=True)
    
    # Descargar comparacion detallada
    render_comparison_download(ref_spectrum, ref_corrected, mean_diff)
    
    # Exportar archivos corregidos
    st.markdown("---")
    st.markdown("#### Exportar Archivos Corregidos")
    render_export_options(ref_corrected, header, df_baseline, origin, lamp_new)
        
    
    # Proceso completado
    st.markdown("---")
    render_completion_message()
    
    # Generar informe
    st.markdown("---")
    render_report_section(kit_data, baseline_data, ref_corrected, origin)
    
    # Navegación al siguiente paso
    st.markdown("---")
    st.markdown("### Siguiente Paso: Validación")
    st.info("""
    **Paso 7 - Validación (Opcional pero recomendado):**
    
    Si aplicaste el baseline corregido al equipo, puedes verificar que el ajuste 
    fue exitoso midiendo nuevamente muestras de control.
    """)
    
    col_next, col_restart = st.columns([3, 1])
    
    with col_next:
        if st.button("✅ Continuar a Validación", type="primary", use_container_width=True):
            st.session_state.unsaved_changes = False  # Limpiar flag
            from session_manager import go_to_next_step
            go_to_next_step()
            st.rerun()
    
    with col_restart:
        if st.button("🔄 Reiniciar proceso", use_container_width=True):
            st.session_state.unsaved_changes = False  # Limpiar flag
            reset_session_state()
            st.rerun()


def render_baseline_comparison_values(ref_spectrum, ref_corrected):
    """Muestra comparacion de valores del baseline."""
    col_val1, col_val2 = st.columns(2)
    
    with col_val1:
        st.write("**Primeros 5 valores:**")
        st.write(f"Original: {ref_spectrum[:5]}")
        st.write(f"Corregido: {ref_corrected[:5]}")
    
    with col_val2:
        st.write("**Últimos 5 valores:**")
        st.write(f"Original: {ref_spectrum[-5:]}")
        st.write(f"Corregido: {ref_corrected[-5:]}")


def render_comparison_download(ref_spectrum, ref_corrected, mean_diff):
    """Renderiza boton de descarga de comparacion detallada."""
    df_comparison = pd.DataFrame({
        "Canal": range(1, len(ref_spectrum) + 1),
        "baseline_original": ref_spectrum,
        "baseline_corregido": ref_corrected,
        "correccion_aplicada": mean_diff
    })
    
    csv_comp = io.StringIO()
    df_comparison.to_csv(csv_comp, index=False)
    
    st.download_button(
        "📥 Descargar comparación detallada (CSV)",
        data=csv_comp.getvalue(),
        file_name=f"comparacion_baseline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )


def render_export_options(ref_corrected, header, df_baseline, origin, lamp_new):
    """Renderiza las opciones de exportacion de archivos."""
    col_exp1, col_exp2 = st.columns(2)
    
    # Exportar .REF
    with col_exp1:
        st.markdown("**Formato .ref (binario)**")
        if origin == 'ref' and header is not None:
            st.info("Cabecera original del sensor preservada")
            ref_bytes = export_ref_file(ref_corrected, header)
            st.download_button(
                "📥 Descargar .ref corregido",
                data=ref_bytes,
                file_name=f"baseline_{lamp_new}_corregido.ref",
                mime="application/octet-stream",
                key="download_ref",
                use_container_width=True
            )
        else:
            st.error(MESSAGES['warning_no_header'])
    
    # Exportar .CSV
    with col_exp2:
        st.markdown("**Formato .csv (nuevo software)**")
        if origin == 'csv' and df_baseline is not None:
            st.success("Metadatos originales preservados")
            csv_bytes = export_csv_file(ref_corrected, df_baseline=df_baseline)
        else:
            st.warning(MESSAGES['warning_default_metadata'])
            csv_bytes = export_csv_file(ref_corrected)
        
        st.download_button(
            "📥 Descargar .csv corregido",
            data=csv_bytes,
            file_name=f"baseline_{lamp_new}_corregido.csv",
            mime="text/csv",
            key="download_csv",
            use_container_width=True
        )


def render_completion_message():
    """Muestra el mensaje de proceso completado."""
    st.success("""
    ✅ **Baseline Corregido Generado Exitosamente**

    **Próximos pasos recomendados:**
    1. Descarga el baseline corregido en el formato adecuado (.ref o .csv)
    2. Copia el archivo a la ubicación correspondiente en tu sistema
    3. Continúa al paso de validación para verificar el ajuste

    **Recordatorio:** Asegúrate de haber realizado el backup de los archivos originales.
    """)


def render_report_section(kit_data, baseline_data, ref_corrected, origin):
    """Renderiza la seccion de generacion de informe."""
    st.markdown("#### 📄 Generar Informe del Proceso")
    
    if st.button("📊 Generar Informe Completo", use_container_width=True, type="secondary"):
        try:
            html_content = generate_html_report(
                kit_data, 
                baseline_data, 
                ref_corrected, 
                origin
            )
            
            client_data = st.session_state.client_data or {}
            filename = f"Informe_Baseline_{client_data.get('sensor_sn', 'sensor')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            
            st.download_button(
                label="📥 Descargar Informe HTML",
                data=html_content,
                file_name=filename,
                mime="text/html",
                use_container_width=True
            )
            st.success("✅ Informe generado correctamente")
            
        except Exception as e:
            st.error(f"❌ Error al generar el informe: {str(e)}")


def render_report_section_standalone():
    """
    Renderiza sección de informe cuando no hay datos necesarios.
    """
    st.markdown("---")
    st.markdown("### 📄 Generar Informe")
    
    st.info("""
    Puedes generar un informe con los datos disponibles de otros pasos 
    (diagnóstico inicial, muestras de control, standard kit, etc.)
    """)
    
    if st.button("📊 Generar Informe Parcial", use_container_width=True, type="secondary"):
        try:
            from core.report_generator import generate_partial_report
            
            # Generar informe con lo que haya disponible
            html_content = generate_partial_report()
            
            client_data = st.session_state.get('client_data') or {}
            filename = f"Informe_Parcial_{client_data.get('sensor_sn', 'sensor')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            
            st.download_button(
                label="📥 Descargar Informe HTML",
                data=html_content,
                file_name=filename,
                mime="text/html",
                use_container_width=True
            )
            st.success("✅ Informe generado correctamente con los datos disponibles")
            
        except Exception as e:
            st.error(f"❌ Error al generar el informe: {str(e)}")
            st.info("💡 Asegúrate de haber completado al menos uno de los pasos anteriores")


def render_navigation_without_dependencies():
    """
    Renderiza navegación cuando no hay datos de dependencias.
    """
    st.markdown("---")
    st.markdown("### Navegación")
    
    col_back, col_skip = st.columns([1, 2])
    
    with col_back:
        if st.button("← Volver al Paso 5", use_container_width=True):
            st.session_state.unsaved_changes = False
            st.session_state.current_step = 5
            st.rerun()
    
    with col_skip:
        if st.button("⏭️ Omitir y continuar al Paso 7", type="primary", use_container_width=True):
            st.session_state.unsaved_changes = False
            from session_manager import go_to_next_step
            go_to_next_step()
            st.rerun()