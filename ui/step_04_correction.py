"""
Paso 5: Cálculo de Corrección Espectral (OPCIONAL)
"""
import streamlit as st
import pandas as pd
import numpy as np
import io
from config import MESSAGES
from session_manager import (
    has_kit_data,
    update_kit_data_with_correction,
    go_to_next_step
)
from core.spectral_processing import calculate_spectral_correction
from utils.plotting import plot_correction_differences, plot_correction_summary


def render_correction_step():
    """
    Renderiza el paso de cálculo de corrección espectral (Paso 5).
    Este paso es completamente OPCIONAL e INDEPENDIENTE.
    """
    st.markdown("## PASO 5 DE 7: Cálculo de Corrección Espectral")
    
    # Información sobre que este paso es opcional
    st.info("""
    ### ℹ️ Este paso es OPCIONAL e INDEPENDIENTE
    
    **Puedes elegir:**
    - ✅ **Calcular la corrección** - Si tienes datos del Standard Kit del Paso 4
    - ⏭️ **Omitir este paso** - Si solo quieres documentar otras mediciones
    - 📄 **Generar informe** - Con los datos que tengas disponibles
    
    Si omites este paso, no podrás generar el baseline corregido en el Paso 6.
    """)
    
    # Verificar si hay datos del Standard Kit
    if not has_kit_data():
        st.warning("""
        ⚠️ No hay datos del Standard Kit cargados.
        
        **Puedes:**
        - Volver al Paso 4 para cargar el Standard Kit
        - Omitir este paso y continuar
        - Generar un informe con los datos disponibles de otros pasos
        """)
        
        # Mostrar sección de informe y navegación
        render_report_section_standalone()
        render_navigation_without_data()
        return
    
    # Marcar cambios sin guardar al calcular corrección
    st.session_state.unsaved_changes = True
    
    # Obtener datos del kit
    kit_data = st.session_state.kit_data
    df_ref_grouped = kit_data['df_ref_grouped']
    df_new_grouped = kit_data['df_new_grouped']
    spectral_cols = kit_data['spectral_cols']
    lamp_ref = kit_data['lamp_ref']
    lamp_new = kit_data['lamp_new']
    common_ids = kit_data['common_ids']
    
    # Información del proceso
    st.info(f"""
    **Calculando la diferencia espectral promedio entre:**
    - Estado de referencia: **{lamp_ref}**
    - Estado actual: **{lamp_new}**
    - Basado en **{len(common_ids)} muestras** comunes
    """)
    
    # Obtener muestras seleccionadas para corrección
    ids_for_corr = st.session_state.get('selected_ids', list(common_ids))
    
    if len(ids_for_corr) == 0:
        st.warning("⚠️ No has seleccionado ninguna muestra. Se usarán todas por defecto.")
        ids_for_corr = list(common_ids)
    
    # Identificar muestras NO usadas (para validación)
    ids_not_used = [id_ for id_ in common_ids if id_ not in ids_for_corr]
    
    # Calcular corrección
    mean_diff = calculate_spectral_correction(
        df_ref_grouped, 
        df_new_grouped, 
        ids_for_corr
    )
    
    # Crear DataFrame con resultados detallados (TODAS las muestras)
    df_diff = build_correction_dataframe(
        df_ref_grouped, df_new_grouped, 
        mean_diff, common_ids, lamp_ref, lamp_new
    )
    
    # ============================================
    # GRÁFICO 1: Muestras usadas en la corrección
    # ============================================
    with st.expander("📊 Ver Diferencias Espectrales - Muestras Usadas", expanded=False):
        st.markdown("### Diferencias Espectrales - Muestras Usadas")
        
        if len(ids_for_corr) < len(common_ids):
            st.info(f"ℹ️ Mostrando {len(ids_for_corr)} de {len(common_ids)} muestras (usadas en la corrección)")
        else:
            st.info(f"ℹ️ Mostrando todas las {len(ids_for_corr)} muestras")
        
        fig_used = plot_correction_differences(df_diff, ids_for_corr, ids_for_corr)
        st.plotly_chart(fig_used, use_container_width=True)
    
    # ============================================
    # GRÁFICO 2: Validación en muestras NO usadas
    # ============================================
    if len(ids_not_used) > 0:
        with st.expander("✅ Ver Validación - Muestras NO Usadas", expanded=False):
            st.markdown("### Validación - Muestras NO Usadas en la Corrección")
            st.info(f"""
            ℹ️ Mostrando {len(ids_not_used)} muestras que **NO** se usaron para calcular la corrección.
            
            Este gráfico muestra cómo la corrección calculada afecta a muestras independientes,
            permitiendo validar que la corrección es robusta y generalizable.
            """)
            
            fig_validation = plot_correction_differences(df_diff, ids_not_used, ids_not_used)
            st.plotly_chart(fig_validation, use_container_width=True)
            
            # Estadísticas de validación
            render_validation_statistics(df_diff, ids_not_used, mean_diff)
    else:
        st.info("ℹ️ Todas las muestras se están usando para la corrección. No hay muestras de validación disponibles.")
    
    # Estadísticas de corrección
    render_correction_statistics(mean_diff)
    
    # Descargar tabla de corrección
    render_download_correction_table(df_diff, lamp_ref, lamp_new)
    
    # Guardar corrección en session_state
    update_kit_data_with_correction(mean_diff)
    
    # Simulación del efecto de la corrección
    render_correction_simulation_preview()
    
    # Navegación
    st.markdown("---")
    st.markdown("### Siguiente Paso")
    
    col_continue, col_skip = st.columns([3, 1])
    
    with col_continue:
        if st.button("✅ Continuar al Paso 6", type="primary", use_container_width=True):
            st.session_state.unsaved_changes = False
            go_to_next_step()
    
    with col_skip:
        if st.button("⏭️ Omitir paso", use_container_width=True, key="skip_step_correction"):
            st.session_state.unsaved_changes = False
            go_to_next_step()


def build_correction_dataframe(df_ref_grouped, df_new_grouped, mean_diff, 
                               common_ids, lamp_ref, lamp_new):
    """
    Construye un DataFrame con todos los detalles de la corrección.
    
    Args:
        df_ref_grouped (pd.DataFrame): Mediciones de referencia
        df_new_grouped (pd.DataFrame): Mediciones nuevas
        mean_diff (np.array): Vector de corrección promedio
        common_ids (list): IDs comunes
        lamp_ref (str): Nombre lámpara referencia
        lamp_new (str): Nombre lámpara nueva
        
    Returns:
        pd.DataFrame: DataFrame con detalles de corrección
    """
    df_diff = pd.DataFrame({"Canal": range(1, len(mean_diff) + 1)})
    
    # Agregar columnas por muestra
    for id_ in common_ids:
        df_diff[f"{lamp_ref}_{id_}"] = df_ref_grouped.loc[id_].values
        df_diff[f"{lamp_new}_{id_}"] = df_new_grouped.loc[id_].values
        df_diff[f"DIF_{id_}"] = (
            df_ref_grouped.loc[id_].values - df_new_grouped.loc[id_].values
        )
    
    df_diff["CORRECCION_PROMEDIO"] = mean_diff
    
    return df_diff


def render_correction_statistics(mean_diff):
    """
    Renderiza las estadísticas de la corrección calculada.
    
    Args:
        mean_diff (np.array): Vector de corrección promedio
    """
    st.markdown("### 📊 Estadísticas de la Corrección")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        max_corr = np.max(np.abs(mean_diff))
        st.metric("Corrección máxima", f"{max_corr:.4f}")
    
    with col2:
        mean_corr = np.mean(np.abs(mean_diff))
        st.metric("Corrección media", f"{mean_corr:.4f}")
    
    with col3:
        std_corr = np.std(mean_diff)
        st.metric("Desviación estándar", f"{std_corr:.4f}")


def render_download_correction_table(df_diff, lamp_ref, lamp_new):
    """
    Renderiza el botón de descarga de la tabla de corrección.
    
    Args:
        df_diff (pd.DataFrame): DataFrame con corrección
        lamp_ref (str): Nombre lámpara referencia
        lamp_new (str): Nombre lámpara nueva
    """
    csv_diff = io.StringIO()
    df_diff.to_csv(csv_diff, index=False)
    
    st.download_button(
        "📥 Descargar tabla de corrección (CSV)",
        data=csv_diff.getvalue(),
        file_name=f"correccion_{lamp_ref}_vs_{lamp_new}.csv",
        mime="text/csv",
        use_container_width=True
    )


def render_validation_statistics(df_diff, ids_not_used, mean_diff):
    """
    Renderiza estadísticas de las muestras de validación.
    
    Args:
        df_diff (pd.DataFrame): DataFrame con diferencias
        ids_not_used (list): IDs no usados en corrección
        mean_diff (np.array): Vector de corrección promedio
    """
    st.markdown("#### 📈 Estadísticas de Validación")
    
    # Calcular diferencias promedio por muestra de validación
    validation_diffs = []
    for id_ in ids_not_used:
        diff_col = f"DIF_{id_}"
        if diff_col in df_diff.columns:
            sample_diff = df_diff[diff_col].values
            validation_diffs.append(sample_diff)
    
    if validation_diffs:
        validation_diffs = np.array(validation_diffs)
        validation_mean = np.mean(validation_diffs, axis=0)
        
        # Comparar con la corrección calculada
        residual = validation_mean - mean_diff
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            max_residual = np.max(np.abs(residual))
            st.metric(
                "Residuo máximo", 
                f"{max_residual:.6f}",
                help="Diferencia máxima entre la corrección calculada y las muestras de validación"
            )
        
        with col2:
            mean_residual = np.mean(np.abs(residual))
            st.metric(
                "Residuo medio", 
                f"{mean_residual:.6f}",
                help="Diferencia media entre la corrección calculada y las muestras de validación"
            )
        
        with col3:
            std_residual = np.std(residual)
            st.metric(
                "Desv. estándar residuo", 
                f"{std_residual:.6f}",
                help="Variabilidad del residuo"
            )
        
        # Interpretación
        if max_residual < 0.01:
            st.success("✅ Excelente validación: Las muestras no usadas muestran diferencias muy similares a la corrección calculada.")
        elif max_residual < 0.05:
            st.info("ℹ️ Buena validación: Las muestras no usadas son consistentes con la corrección.")
        else:
            st.warning("⚠️ Atención: Hay diferencias significativas en las muestras de validación. Considera revisar la selección de muestras.")
            

def render_correction_simulation_preview():
    """
    Renderiza una vista previa de cómo quedará el efecto de la corrección.
    """
    st.markdown("---")
    st.markdown("### 🔮 Simulación: Vista Previa del Efecto de la Corrección")
    
    st.info("""
    A continuación se muestra una **simulación** de cómo quedarían los espectros del estado actual
    después de aplicar el baseline corregido, comparados con los espectros del estado de referencia.
    
    ⚠️ **Nota:** Esta es solo una simulación. El baseline corregido aún no se ha generado. 
    Podrás descargarlo en el siguiente paso (Paso 6).
    """)
    
    # Obtener datos necesarios
    kit_data = st.session_state.kit_data
    df_ref_grouped = kit_data['df_ref_grouped']
    df_new_grouped = kit_data['df_new_grouped']
    spectral_cols = kit_data['spectral_cols']
    lamp_ref = kit_data['lamp_ref']
    lamp_new = kit_data['lamp_new']
    common_ids = kit_data['common_ids']
    mean_diff = kit_data['mean_diff']
    
    # Para simular, necesitamos crear un baseline ficticio
    # Asumimos que el baseline original es aproximadamente el promedio de los espectros
    # Esta es una aproximación para la simulación
    baseline_approx = np.mean([df_ref_grouped.loc[id_].values for id_ in common_ids], axis=0)
    baseline_corrected_approx = baseline_approx - mean_diff
    
    # Simular espectros corregidos
    from core.spectral_processing import simulate_corrected_spectra
    df_new_corr = simulate_corrected_spectra(
        df_new_grouped,
        spectral_cols,
        baseline_approx,
        baseline_corrected_approx
    )
    
    # Obtener muestras usadas y no usadas
    used_ids = st.session_state.get('selected_ids', list(common_ids))
    other_ids = [i for i in common_ids if i not in used_ids]
    
    # Gráfico de muestras usadas - ANTES Y DESPUÉS
    with st.expander("📊 Ver simulación - Muestras usadas en la corrección", expanded=False):
        st.markdown("**Muestras usadas en la corrección (simulación)**")
        
        from utils.plotting import plot_corrected_spectra_comparison
        
        # GRÁFICO 1: SIN corrección
        st.markdown("*ANTES: Sin corrección aplicada*")
        fig_before_used = plot_corrected_spectra_comparison(
            df_ref_grouped, 
            df_new_grouped,  # ← SIN CORRECCIÓN
            spectral_cols,
            "Referencia", "Nueva (original)", 
            used_ids,
            title="Referencia vs Nueva (original) - muestras usadas"
        )
        st.plotly_chart(fig_before_used, use_container_width=True)
        
        # GRÁFICO 2: CON corrección (simulado)
        st.markdown("*DESPUÉS: Con corrección aplicada (simulación)*")
        fig_after_used = plot_corrected_spectra_comparison(
            df_ref_grouped, 
            df_new_corr,  # ← CON CORRECCIÓN
            spectral_cols,
            "Referencia", "Nueva (simulación corregida)", 
            used_ids,
            title="Simulación: Referencia vs Nueva (corregida) - muestras usadas"
        )
        st.plotly_chart(fig_after_used, use_container_width=True)
    
    # Gráfico de muestras no usadas (validación)
    if len(other_ids) > 0:
        with st.expander("✅ Ver simulación - Muestras no usadas (validación)", expanded=False):
            st.markdown("**Muestras no usadas (simulación de validación)**")
            
            # GRÁFICO 1: SIN corrección
            st.markdown("*ANTES: Sin corrección aplicada*")
            fig_before = plot_corrected_spectra_comparison(
                df_ref_grouped, 
                df_new_grouped,  # ← SIN CORRECCIÓN
                spectral_cols,
                "Referencia", "Nueva (original)", 
                other_ids,
                title="Referencia vs Nueva (original) - NO usadas"
            )
            st.plotly_chart(fig_before, use_container_width=True)
            
            # GRÁFICO 2: CON corrección (simulado)
            st.markdown("*DESPUÉS: Con corrección aplicada (simulación)*")
            fig_after = plot_corrected_spectra_comparison(
                df_ref_grouped, 
                df_new_corr,  # ← CON CORRECCIÓN (simulado)
                spectral_cols,
                "Referencia", "Nueva (simulación corregida)", 
                other_ids,
                title="Simulación: Referencia vs Nueva (corregida) - NO usadas"
            )
            st.plotly_chart(fig_after, use_container_width=True)
    else:
        st.info("ℹ️ Todas las muestras comunes están siendo usadas para calcular la corrección.")


def render_report_section_standalone():
    """
    Renderiza sección de informe cuando no hay datos de corrección.
    """
    st.markdown("---")
    st.markdown("### 📄 Generar Informe")
    
    st.info("""
    Puedes generar un informe con los datos disponibles de otros pasos 
    (diagnóstico inicial, muestras de control, etc.)
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


def render_navigation_without_data():
    """
    Renderiza navegación cuando no hay datos del Standard Kit.
    """
    st.markdown("---")
    st.markdown("### Navegación")
    
    col_back, col_skip = st.columns([1, 2])
    
    with col_back:
        if st.button("← Volver al Paso 4", use_container_width=True):
            st.session_state.unsaved_changes = False
            st.session_state.current_step = 4
            st.rerun()
    
    with col_skip:
        if st.button("⏭️ Omitir y continuar al Paso 6", type="primary", use_container_width=True):
            st.session_state.unsaved_changes = False
            go_to_next_step()
            st.rerun()