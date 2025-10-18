"""
Paso 6: Aplicar Corrección, Exportar y Generar Informe
"""
import streamlit as st
import pandas as pd
import numpy as np
import io
import json
from datetime import datetime
from config import MESSAGES
from session_manager import (
    has_kit_data,
    has_baseline_data,
    has_correction_data,
    reset_session_state
)
from core.spectral_processing import (
    apply_baseline_correction,
    simulate_corrected_spectra
)
from core.file_handlers import export_ref_file, export_csv_file
from core.report_generator import generate_html_report
from utils.plotting import (
    plot_baseline_comparison,
    plot_corrected_spectra_comparison
)


def render_export_step():
    """
    Renderiza el paso de exportación y generación de informe (Paso 5).
    """
    st.markdown("## 📍 PASO 5 DE 5: Aplicar Corrección y Exportar")
    
    # Validar que existan todos los datos necesarios
    if not has_kit_data() or not has_baseline_data():
        st.error("❌ Faltan datos. Vuelve a los pasos anteriores.")
        return
    
    if not has_correction_data():
        st.error("❌ No hay datos de corrección calculados. Vuelve al Paso 3.")
        return
    
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
    
    # Aplicar corrección
    ref_corrected = apply_baseline_correction(ref_spectrum, mean_diff)
    st.success(MESSAGES['success_correction_applied'])
    
    # Mostrar comparación de valores
    render_baseline_comparison_values(ref_spectrum, ref_corrected)
    
    # Visualización comparativa
    st.markdown("### 📊 Comparación: Baseline Original vs Corregido")
    fig_comp = plot_baseline_comparison(ref_spectrum, ref_corrected, spectral_cols)
    st.pyplot(fig_comp)
    
    # Descargar comparación detallada
    render_comparison_download(ref_spectrum, ref_corrected, mean_diff)
    
    # Exportar archivos corregidos
    st.markdown("---")
    st.markdown("### 💾 Exportar Archivos Corregidos")
    render_export_options(
        ref_corrected, header, df_baseline, 
        origin, lamp_new
    )
    
    # Simulación del efecto de la corrección
    st.markdown("---")
    render_correction_simulation(
        df, df_ref_grouped, spectral_cols, 
        lamp_ref, lamp_new, common_ids,
        ref_spectrum, ref_corrected
    )
    
    # Exportar TSV corregido para verificación
    render_tsv_export(df, spectral_cols, lamp_new, ref_spectrum, ref_corrected)
    
    # Proceso completado
    st.markdown("---")
    render_completion_message()
    
    # Generar informe
    st.markdown("---")
    render_report_section(
        kit_data, baseline_data, 
        ref_corrected, origin
    )
    
    # Botón reiniciar
    st.markdown("---")
    if st.button("🔄 Reiniciar proceso", use_container_width=True):
        reset_session_state()


def render_baseline_comparison_values(ref_spectrum, ref_corrected):
    """
    Muestra comparación de valores del baseline.
    
    Args:
        ref_spectrum (np.array): Baseline original
        ref_corrected (np.array): Baseline corregido
    """
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
    """
    Renderiza botón de descarga de comparación detallada.
    
    Args:
        ref_spectrum (np.array): Baseline original
        ref_corrected (np.array): Baseline corregido
        mean_diff (np.array): Vector de corrección
    """
    df_comparison = pd.DataFrame({
        "Canal": range(1, len(ref_spectrum) + 1),
        "baseline_original": ref_spectrum,
        "baseline_corregido": ref_corrected,
        "correccion_aplicada": mean_diff
    })
    
    csv_comp = io.StringIO()
    df_comparison.to_csv(csv_comp, index=False)
    
    st.download_button(
        "📄 Descargar comparación detallada (CSV)",
        data=csv_comp.getvalue(),
        file_name=f"comparacion_baseline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )


def render_export_options(ref_corrected, header, df_baseline, origin, lamp_new):
    """
    Renderiza las opciones de exportación de archivos.
    
    Args:
        ref_corrected (np.array): Baseline corregido
        header (np.array): Cabecera del .ref
        df_baseline (pd.DataFrame): DataFrame del baseline CSV
        origin (str): Tipo de archivo original ('ref' o 'csv')
        lamp_new (str): Nombre de la lámpara nueva
    """
    col_exp1, col_exp2 = st.columns(2)
    
    # Exportar .REF
    with col_exp1:
        st.markdown("#### 📄 Formato .ref (binario)")
        if origin == 'ref' and header is not None:
            st.info("✓ Cabecera original del sensor preservada")
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
        st.markdown("#### 📄 Formato .csv (nuevo software)")
        if origin == 'csv' and df_baseline is not None:
            st.success("✓ Metadatos originales preservados")
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


def render_correction_simulation(df, df_ref_grouped, spectral_cols, 
                                 lamp_ref, lamp_new, common_ids,
                                 ref_spectrum, ref_corrected):
    """
    Renderiza la simulación del efecto de la corrección.
    
    Args:
        df (pd.DataFrame): DataFrame completo
        df_ref_grouped (pd.DataFrame): Mediciones de referencia
        spectral_cols (list): Columnas espectrales
        lamp_ref (str): Lámpara de referencia
        lamp_new (str): Lámpara nueva
        common_ids (list): IDs comunes
        ref_spectrum (np.array): Baseline original
        ref_corrected (np.array): Baseline corregido
    """
    st.markdown("### 🔬 Simulación: Efecto de la Corrección")
    st.info("""
    A continuación se muestra cómo quedarían los espectros de la lámpara nueva después de 
    aplicar el baseline corregido, comparados con los espectros de la lámpara de referencia.
    """)
    
    # Simular espectros corregidos
    df_new_corr = simulate_corrected_spectra(
        df, spectral_cols, lamp_new, 
        ref_spectrum, ref_corrected
    )
    
    # Obtener muestras usadas y no usadas
    used_ids = st.session_state.get('selected_ids', list(common_ids))
    other_ids = [i for i in common_ids if i not in used_ids]
    
    # Gráfico de muestras usadas
    st.markdown("#### ✅ Muestras usadas en la corrección")
    fig_used = plot_corrected_spectra_comparison(
        df_ref_grouped, df_new_corr, spectral_cols,
        lamp_ref, lamp_new, used_ids,
        title=f"{lamp_ref} (referencia) vs {lamp_new} (corregido) — usadas en la corrección"
    )
    st.pyplot(fig_used)
    
    # Gráfico de muestras no usadas (validación)
    if len(other_ids) > 0:
        st.markdown("#### 🔎 Muestras no usadas (validación)")
        fig_other = plot_corrected_spectra_comparison(
            df_ref_grouped, df_new_corr, spectral_cols,
            lamp_ref, lamp_new, other_ids,
            title=f"{lamp_ref} (referencia) vs {lamp_new} (corregido) — NO usadas"
        )
        st.pyplot(fig_other)
    else:
        st.info("Todas las muestras comunes están siendo usadas para calcular la corrección.")


def render_tsv_export(df, spectral_cols, lamp_new, ref_spectrum, ref_corrected):
    """
    Renderiza la exportación del TSV con espectros corregidos.
    
    Args:
        df (pd.DataFrame): DataFrame completo
        spectral_cols (list): Columnas espectrales
        lamp_new (str): Lámpara nueva
        ref_spectrum (np.array): Baseline original
        ref_corrected (np.array): Baseline corregido
    """
    df_new_corr = simulate_corrected_spectra(
        df, spectral_cols, lamp_new,
        ref_spectrum, ref_corrected
    )
    
    df_export_tsv = df.copy()
    df_export_tsv.loc[df_export_tsv["Note"] == lamp_new, spectral_cols] = df_new_corr[spectral_cols]
    
    tsv_bytes = io.StringIO()
    df_export_tsv.to_csv(tsv_bytes, sep="\t", index=False)
    
    st.download_button(
        "📥 Descargar TSV completo con espectros corregidos (verificación)",
        data=tsv_bytes.getvalue(),
        file_name=f"espectros_{lamp_new}_corregidos.tsv",
        mime="text/tab-separated-values",
        use_container_width=True
    )


def render_completion_message():
    """
    Muestra el mensaje de proceso completado.
    """
    st.success("""
    ### ✅ Proceso Completado

    **Próximos pasos:**
    1. Descarga el baseline corregido en el formato adecuado (.ref o .csv)
    2. Copia el archivo a la ubicación correspondiente en tu sistema
    3. Verifica el ajuste midiendo nuevamente el White Standard sin línea base
    4. Los espectros de ambas lámparas deberían estar ahora alineados

    💾 **Recordatorio:** Asegúrate de haber realizado el backup de los archivos originales.
    """)


def render_report_section(kit_data, baseline_data, ref_corrected, origin):
    """
    Renderiza la sección de generación de informe.
    
    Args:
        kit_data (dict): Datos del kit
        baseline_data (dict): Datos del baseline
        ref_corrected (np.array): Baseline corregido
        origin (str): Tipo de archivo
    """
    st.markdown("### 📋 Generar Informe del Proceso")
    
    if st.button("📄 Generar Informe Completo", use_container_width=True, type="primary"):
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
