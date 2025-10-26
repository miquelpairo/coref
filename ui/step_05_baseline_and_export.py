# -*- coding: utf-8 -*-
"""
Paso 5: Cargar Baseline, Aplicar Corrección y Exportar
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
    Renderiza el paso combinado de baseline y exportacion (Paso 5).
    """
    st.markdown("## PASO 6 DE 7: Cargar Baseline, Aplicar Correccion y Exportar")
    
    if not has_kit_data():
        st.error("No hay datos del Standard Kit. Vuelve al Paso 3.")
        return
    
    if not has_correction_data():
        st.error("No hay datos de correccion calculados. Vuelve al Paso 4.")
        return
    
    kit_data = st.session_state.kit_data
    lamp_new = kit_data['lamp_new']
    spectral_cols = kit_data['spectral_cols']
    
    # SECCION 1: CARGAR BASELINE
    st.markdown("### Paso 5.1: Cargar Baseline de la Lampara Nueva")
    render_baseline_upload_section(lamp_new, spectral_cols)
    
    # SECCION 2: APLICAR CORRECCION Y EXPORTAR (solo si hay baseline cargado)
    if has_baseline_data():
        st.markdown("---")
        st.markdown("### Paso 5.2: Aplicar Correccion y Exportar")
        render_correction_and_export_section()


def render_baseline_upload_section(lamp_new, spectral_cols):
    """
    Renderiza la seccion de carga de baseline.
    
    Args:
        lamp_new (str): Nombre de la lampara nueva
        spectral_cols (list): Columnas espectrales
    """
    instructions_text = INSTRUCTIONS['baseline_load'].format(
        lamp_name=lamp_new,
        n_channels=len(spectral_cols)
    )
    st.info(instructions_text)
    
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
                
        except Exception as e:
            st.error(f"Error al procesar el archivo: {str(e)}")


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
    
    # Visualizar baseline
    with st.expander("Ver espectro del baseline cargado"):
        fig = plot_baseline_spectrum(ref_spectrum, title="Baseline Cargado")
        st.plotly_chart(fig, use_container_width=True)
    
    # Guardar datos
    save_baseline_data(
        ref_spectrum=ref_spectrum,
        header=header,
        df_baseline=None,
        origin='ref'
    )
    
    st.success("Baseline cargado correctamente. Continua con la aplicacion de la correccion.")


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
        st.metric("Sys Temp (C)", f"{df_baseline['sys_temp'].iloc[0]:.2f}")
        st.metric("TEC Temp (C)", f"{df_baseline['tec_temp'].iloc[0]:.2f}")
    
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
    
    # Visualizar baseline
    with st.expander("Ver espectro del baseline cargado"):
        fig = plot_baseline_spectrum(ref_spectrum, title="Baseline")
        st.plotly_chart(fig, use_container_width=True)
    
    # Guardar datos
    save_baseline_data(
        ref_spectrum=ref_spectrum,
        header=None,
        df_baseline=df_baseline,
        origin='csv'
    )
    
    st.success("Baseline cargado correctamente. Continua con la aplicacion de la correccion.")


def validate_and_display_dimensions(baseline_length, tsv_length):
    """
    Valida y muestra el resultado de la comparacion de dimensiones.
    """
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
    with st.expander("Ver comparacion de valores del baseline"):
        render_baseline_comparison_values(ref_spectrum, ref_corrected)
    
    # Visualizacion comparativa
    st.markdown("#### Comparacion: Baseline Original vs Corregido")
    fig_comp = plot_baseline_comparison(ref_spectrum, ref_corrected, spectral_cols)
    st.plotly_chart(fig_comp, use_container_width=True)
    
    # Descargar comparacion detallada
    render_comparison_download(ref_spectrum, ref_corrected, mean_diff)
    
    # Exportar archivos corregidos
    st.markdown("---")
    st.markdown("#### Exportar Archivos Corregidos")
    render_export_options(ref_corrected, header, df_baseline, origin, lamp_new)
    
    # Simulacion del efecto de la correccion
    st.markdown("---")
    st.markdown("#### Simulacion: Efecto de la Correccion")
    render_correction_simulation(
        df, df_ref_grouped, spectral_cols, 
        lamp_ref, lamp_new, common_ids,
        ref_spectrum, ref_corrected
    )
    
    # Exportar TSV corregido
    render_tsv_export(df, spectral_cols, lamp_new, ref_spectrum, ref_corrected)
    
    # Proceso completado
    st.markdown("---")
    render_completion_message()
    
    # Generar informe
    st.markdown("---")
    render_report_section(kit_data, baseline_data, ref_corrected, origin)
    
    # Navegación al siguiente paso
    st.markdown("---")
    st.markdown("### Siguiente Paso: Validacion")
    st.info("""
    **Paso 6 - Validacion (Opcional pero recomendado):**
    
    Verifica que el ajuste fue exitoso midiendo nuevamente el Standard Kit 
    con el baseline corregido instalado.
    """)
    
    col_next, col_restart = st.columns([3, 1])
    
    with col_next:
        if st.button("Continuar a Validacion", type="primary", use_container_width=True):
            st.session_state.unsaved_changes = False  # Limpiar flag
            from session_manager import go_to_next_step
            go_to_next_step()
            st.rerun()
    
    with col_restart:
        if st.button("Reiniciar proceso", use_container_width=True):
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
        st.write("**Ultimos 5 valores:**")
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
        "Descargar comparacion detallada (CSV)",
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
                "Descargar .ref corregido",
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
            "Descargar .csv corregido",
            data=csv_bytes,
            file_name=f"baseline_{lamp_new}_corregido.csv",
            mime="text/csv",
            key="download_csv",
            use_container_width=True
        )


def render_correction_simulation(df, df_ref_grouped, spectral_cols, 
                                 lamp_ref, lamp_new, common_ids,
                                 ref_spectrum, ref_corrected):
    """Renderiza la simulacion del efecto de la correccion."""
    st.info("""
    A continuacion se muestra como quedarian los espectros de la lampara nueva despues de 
    aplicar el baseline corregido, comparados con los espectros de la lampara de referencia.
    """)
    
    # Obtener df_new_grouped desde session_state
    kit_data = st.session_state.kit_data
    df_new_grouped = kit_data['df_new_grouped']
    
    # Simular espectros corregidos (AHORA CON 4 PARAMETROS)
    df_new_corr = simulate_corrected_spectra(
        df_new_grouped,      # 1. DataFrame agrupado
        spectral_cols,       # 2. Columnas espectrales
        ref_spectrum,        # 3. Baseline original
        ref_corrected        # 4. Baseline corregido
    )
    
    # Obtener muestras usadas y no usadas
    used_ids = st.session_state.get('selected_ids', list(common_ids))
    other_ids = [i for i in common_ids if i not in used_ids]
    
    # Grafico de muestras usadas
    st.markdown("**Muestras usadas en la correccion**")
    fig_used = plot_corrected_spectra_comparison(
        df_ref_grouped, df_new_corr, spectral_cols,
        "Referencia", "Nueva (corregida)", used_ids,
        title="Referencia vs Nueva (corregida) - usadas en la correccion"
    )
    st.plotly_chart(fig_used, use_container_width=True)
    
    # Grafico de muestras no usadas (validacion)
    if len(other_ids) > 0:
        st.markdown("**Muestras no usadas (validacion)**")
        fig_other = plot_corrected_spectra_comparison(
            df_ref_grouped, df_new_corr, spectral_cols,
            "Referencia", "Nueva (corregida)", other_ids,
            title="Referencia vs Nueva (corregida) - NO usadas"
        )
        st.plotly_chart(fig_other, use_container_width=True)
    else:
        st.info("Todas las muestras comunes estan siendo usadas para calcular la correccion.")

def render_tsv_export(df, spectral_cols, lamp_new, ref_spectrum, ref_corrected):
    """
    Renderiza la exportacion del TSV con espectros corregidos.
    """
    # Obtener df_new_grouped desde session_state
    kit_data = st.session_state.kit_data
    df_new_grouped = kit_data['df_new_grouped']
    
    # Simular espectros corregidos (AHORA CON 4 PARAMETROS)
    df_new_corr = simulate_corrected_spectra(
        df_new_grouped,
        spectral_cols,
        ref_spectrum,
        ref_corrected
    )
    
    # Exportar como CSV
    csv_bytes = io.StringIO()
    df_new_corr.to_csv(csv_bytes, index=True, index_label='ID')
    
    st.download_button(
        "Descargar espectros corregidos (CSV)",
        data=csv_bytes.getvalue(),
        file_name=f"espectros_nueva_corregidos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )

def render_completion_message():
    """Muestra el mensaje de proceso completado."""
    st.success("""
    **Proceso Completado**

    **Proximos pasos:**
    1. Descarga el baseline corregido en el formato adecuado (.ref o .csv)
    2. Copia el archivo a la ubicacion correspondiente en tu sistema
    3. Verifica el ajuste midiendo nuevamente el White Standard sin linea base
    4. Los espectros de ambas lamparas deberian estar ahora alineados

    **Recordatorio:** Asegurate de haber realizado el backup de los archivos originales.
    """)


def render_report_section(kit_data, baseline_data, ref_corrected, origin):
    """Renderiza la seccion de generacion de informe."""
    st.markdown("#### Generar Informe del Proceso")
    
    if st.button("Generar Informe Completo", use_container_width=True, type="primary"):
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
                label="Descargar Informe HTML",
                data=html_content,
                file_name=filename,
                mime="text/html",
                use_container_width=True
            )
            st.success("Informe generado correctamente")
            
        except Exception as e:
            st.error(f"Error al generar el informe: {str(e)}")