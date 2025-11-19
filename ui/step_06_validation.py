# -*- coding: utf-8 -*-
"""
Paso 7: Validacion Post-Correccion
"""
import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime
from config import INSTRUCTIONS, MESSAGES
from session_manager import (
    has_kit_data, 
    has_correction_data, 
    reset_session_state,
    has_reference_tsv,      # ⭐ AÑADIR
    get_reference_tsv,      # ⭐ AÑADIR
)
from core.file_handlers import load_tsv_file, get_spectral_columns
from core.spectral_processing import (
    group_measurements_by_lamp, 
    find_common_samples,
    calculate_spectral_correction
)
from utils.plotting import plot_kit_spectra, plot_correction_differences
from utils.validators import validate_common_samples


def render_validation_step():
    st.markdown("## PASO 7 DE 7: Validación Post-Corrección")

    has_kit = has_kit_data()
    has_corr = has_correction_data()

    # Standard Kit validation
    if has_kit and has_corr:
        render_standard_kit_validation()
    else:
        st.info("""
        ℹ️ **Validación con Standard Kit no disponible**  
        No se han encontrado datos suficientes de los pasos anteriores
        (Paso 4 y/o Paso 5).
        """)

    # Botón de informe
    st.markdown("---")
    render_validation_report_entrypoint(fallback_partial=True)

    # Reset
    st.markdown("---")
    if st.button("🔄 Finalizar y reiniciar proceso", use_container_width=True):
        st.session_state.unsaved_changes = False
        reset_session_state()
        st.rerun()


def render_standard_kit_validation():
    """
    Renderiza la sección de validación con External White Standard.
    """
    st.markdown("### 📊 Validación con External White Standard")
    
    kit_data = st.session_state.kit_data
    mean_diff_original = kit_data['mean_diff']
    
    # Instrucciones
    st.info(f"""
    **Instrucciones para la validación con External White Standard:**
    
    1. **Instala el baseline corregido** en tu espectrómetro (archivo .ref o .csv del Paso 6)
    2. **Reinicia SX-Server** para que cargue el nuevo baseline
    3. **Mide el External White Standard** con 3 repeticiones usando el **mismo ID que en el Paso 3**
    4. **Exporta las mediciones** a 1 archivo TSV
    5. **Sube aquí abajo el TSV recién medido** (DESPUÉS del ajuste)
    
    El sistema comparará las mediciones ANTES y DESPUÉS de la corrección para verificar 
    que el External White está correctamente alineado tras el ajuste de baseline.
    """)
    
    st.markdown("---")
    
    # ========== TSV REFERENCIA (PRE-CARGADO) ==========
    st.markdown("#### 1️⃣ TSV External White (ANTES - Paso 3)")
    
    # Verificar si hay TSV de referencia del Paso 3
    if has_reference_tsv():
        ref_data = get_reference_tsv()
        df_ref = ref_data['df']
        spectral_cols_ref = ref_data['spectral_cols']
        
        st.success(f"✅ TSV de referencia cargado automáticamente desde Paso 3 ({len(df_ref)} mediciones)")
        
        # Mostrar preview
        with st.expander("🔍 Ver datos del TSV de referencia", expanded=False):
            st.dataframe(df_ref[['ID', 'Note']].head(10), use_container_width=True)
            st.write(f"**Total de filas:** {len(df_ref)}")
            st.write(f"**Canales espectrales:** {len(spectral_cols_ref)}")
        
        # Opción de override (igual que en Paso 4)
        if st.checkbox("🔄 Cargar otro archivo TSV de referencia", key="override_ref_tsv_validation"):
            ref_val_file = st.file_uploader(
                "Nuevo archivo TSV del External White ANTES del ajuste",
                type=["tsv", "txt", "csv"],
                key="ref_validation_override"
            )
            
            if ref_val_file:
                try:
                    df_ref_override = load_tsv_file(ref_val_file)
                    spectral_cols_ref_override = get_spectral_columns(df_ref_override)
                    
                    st.success(f"✅ Nuevo TSV cargado ({len(df_ref_override)} mediciones)")
                    
                    # Usar el override temporalmente
                    df_ref = df_ref_override
                    spectral_cols_ref = spectral_cols_ref_override
                    
                except Exception as e:
                    st.error(f"❌ Error al cargar nuevo TSV: {str(e)}")
                    return
        
        # Guardar en variable temporal para usarlo después
        ref_val_file_data = {
            'df': df_ref,
            'spectral_cols': spectral_cols_ref
        }
        
    else:
        st.error("❌ No hay TSV de referencia disponible del Paso 3")
        st.info("Puedes cargar manualmente el archivo TSV del External White medido ANTES del ajuste:")
        
        ref_val_file = st.file_uploader(
            "Sube el TSV del External White ANTES del ajuste",
            type=["tsv", "txt", "csv"],
            key="ref_validation_manual"
        )
        
        if not ref_val_file:
            st.warning("⚠️ Necesitas cargar el TSV de referencia para continuar")
            return
        
        try:
            df_ref = load_tsv_file(ref_val_file)
            spectral_cols_ref = get_spectral_columns(df_ref)
            
            st.success(f"✅ TSV cargado ({len(df_ref)} mediciones)")
            
            ref_val_file_data = {
                'df': df_ref,
                'spectral_cols': spectral_cols_ref
            }
            
        except Exception as e:
            st.error(f"❌ Error al cargar TSV: {str(e)}")
            return
    
    # ========== TSV NUEVO (POST-AJUSTE) ==========
    st.markdown("---")
    st.markdown("#### 2️⃣ TSV External White (DESPUÉS - Post-ajuste)")
    
    new_val_file = st.file_uploader(
        "Sube el TSV del External White DESPUÉS del ajuste",
        type=["tsv", "txt", "csv"],
        key="new_validation_upload",
        help="Mediciones del External White con el baseline corregido instalado"
    )
    
    if new_val_file:
        try:
            # Procesar ambos archivos
            process_validation_files(
                ref_val_file_data,  # ← Ahora pasamos el dict con los datos
                new_val_file,
                mean_diff_original
            )
        except Exception as e:
            st.error(f"❌ Error al procesar los archivos: {str(e)}")
            import traceback
            st.error(traceback.format_exc())

def process_validation_files(ref_val_file_data, new_val_file, mean_diff_original):
    """
    Procesa los archivos de validacion.
    
    Args:
        ref_val_file_data: Dict con 'df' y 'spectral_cols' del TSV de referencia (pre-cargado)
        new_val_file: Archivo TSV de nueva medición (uploaded file)
        mean_diff_original (np.array): Diferencia espectral original (antes de correccion)
    """
    # Marcar cambios sin guardar
    st.session_state.unsaved_changes = True
    
    # Obtener datos de referencia (ya pre-cargados)
    df_ref_val = ref_val_file_data['df']
    spectral_cols_ref = ref_val_file_data['spectral_cols']
    
    # Cargar archivo nuevo
    df_new_val = load_tsv_file(new_val_file)
    
    # Obtener columnas espectrales
    spectral_cols_new = get_spectral_columns(df_new_val)
    
    # Validar compatibilidad
    if len(spectral_cols_ref) != len(spectral_cols_new):
        st.error(f"""
        Los archivos tienen diferente numero de canales espectrales:
        - Referencia: {len(spectral_cols_ref)} canales
        - Nueva: {len(spectral_cols_new)} canales
        """)
        return
    
    spectral_cols = spectral_cols_ref
    
    # Convertir columnas espectrales a numerico
    df_ref_val[spectral_cols] = df_ref_val[spectral_cols].apply(pd.to_numeric, errors="coerce")
    df_new_val[spectral_cols] = df_new_val[spectral_cols].apply(pd.to_numeric, errors="coerce")
    
    # Obtener IDs únicos
    sample_ids_ref = df_ref_val["ID"].unique()
    sample_ids_new = df_new_val["ID"].unique()
    
    # Mostrar informacion
    st.success("✅ Archivos de validacion cargados correctamente")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Archivo ANTES (Paso 3):**")
        st.write(f"- Mediciones: {len(df_ref_val)}")
        st.write(f"- IDs únicos: {len(sample_ids_ref)}")
        with st.expander("Ver IDs disponibles"):
            st.write(", ".join(str(x) for x in sample_ids_ref))
    
    with col2:
        st.markdown("**Archivo DESPUÉS (Post-ajuste):**")
        st.write(f"- Mediciones: {len(df_new_val)}")
        st.write(f"- IDs únicos: {len(sample_ids_new)}")
        with st.expander("Ver IDs disponibles"):
            st.write(", ".join(str(x) for x in sample_ids_new))
    
    # Agrupar mediciones por ID (promedio de repeticiones)
    df_ref_val_grouped = df_ref_val.groupby("ID")[spectral_cols].mean()
    df_new_val_grouped = df_new_val.groupby("ID")[spectral_cols].mean()
    
    # Encontrar IDs comunes
    common_ids_val = find_common_samples(df_ref_val_grouped, df_new_val_grouped)
    
    if not validate_common_samples(common_ids_val):
        return
    
    # Filtrar solo muestras comunes
    df_ref_val_grouped = df_ref_val_grouped.loc[common_ids_val]
    df_new_val_grouped = df_new_val_grouped.loc[common_ids_val]
    
    st.success(f"✅ IDs comunes encontrados: {len(common_ids_val)}")
    st.info(f"📋 IDs disponibles para validación: {', '.join(str(x) for x in common_ids_val)}")
    
    # Seleccion de muestras para validacion
    render_validation_sample_selection(common_ids_val)
    
    # Visualizacion de espectros de validacion
    render_validation_spectra_visualization(
        df_ref_val_grouped, df_new_val_grouped, spectral_cols, common_ids_val
    )
    
    # Calcular diferencias en validacion
    render_validation_analysis(
        df_ref_val_grouped, df_new_val_grouped, spectral_cols,
        common_ids_val, mean_diff_original
    )
    
def render_validation_sample_selection(common_ids):
    """
    Renderiza la interfaz de seleccion de muestras para validacion.
    """
    st.markdown("#### Selección de muestras para validación")
    
    # Inicializar seleccion si no existe
    if 'validation_selected_ids' not in st.session_state:
        st.session_state.validation_selected_ids = list(common_ids)
    
    if 'validation_pending_selection' not in st.session_state:
        st.session_state.validation_pending_selection = list(st.session_state.validation_selected_ids)
    
    # Construir tabla de muestras
    df_samples = pd.DataFrame({
        'ID': list(common_ids),
        'Usar en validacion': [
            i in st.session_state.validation_pending_selection 
            for i in common_ids
        ]
    })
    
    with st.expander("🔍 Ver y seleccionar muestras", expanded=False):
        with st.form("form_validation_samples", clear_on_submit=False):
            edited = st.data_editor(
                df_samples,
                use_container_width=True,
                hide_index=True,
                disabled=['ID'],
                key="editor_validation_samples"
            )
            
            col_a, col_b, col_c, col_d = st.columns([1, 1, 1, 2])
            btn_all = col_a.form_submit_button("Seleccionar todo")
            btn_none = col_b.form_submit_button("Deseleccionar todo")
            btn_invert = col_c.form_submit_button("Invertir seleccion")
            btn_confirm = col_d.form_submit_button("✓ Confirmar seleccion", type="primary")
        
        # Gestionar botones
        if btn_all:
            st.session_state.validation_pending_selection = list(common_ids)
            st.rerun()
        
        if btn_none:
            st.session_state.validation_pending_selection = []
            st.rerun()
        
        if btn_invert:
            inverted = [i for i in common_ids if i not in st.session_state.validation_pending_selection]
            st.session_state.validation_pending_selection = inverted
            st.rerun()
        
        if btn_confirm:
            pending = edited.loc[edited['Usar en validacion'], 'ID'].tolist()
            st.session_state.validation_pending_selection = pending
            st.session_state.validation_selected_ids = pending
            st.success(f"✅ Selección confirmada: {len(st.session_state.validation_selected_ids)} muestras.")
        else:
            if isinstance(edited, pd.DataFrame):
                try:
                    pending = edited.loc[edited['Usar en validacion'], 'ID'].tolist()
                    st.session_state.validation_pending_selection = pending
                except Exception:
                    pass
        
        st.caption(
            f"Seleccionadas (pendiente): {len(st.session_state.validation_pending_selection)} - "
            f"Confirmadas: {len(st.session_state.get('validation_selected_ids', []))}"
        )


def render_validation_spectra_visualization(df_ref_val, df_new_val, spectral_cols, common_ids):
    """
    Renderiza la visualizacion de espectros de validacion.
    """
    with st.expander("📊 Ver espectros de validación", expanded=False):
        # Obtener muestras seleccionadas
        selected_ids = st.session_state.get('validation_selected_ids', list(common_ids))
        ids_to_plot = selected_ids if len(selected_ids) > 0 else list(common_ids)
        
        if len(ids_to_plot) < len(common_ids):
            st.info(f"ℹ️ Mostrando {len(ids_to_plot)} de {len(common_ids)} muestras (solo seleccionadas)")
        
        fig = plot_kit_spectra(
            df_ref_val, df_new_val,
            spectral_cols, 
            "Referencia", "Nueva",
            ids_to_plot
        )
        st.plotly_chart(fig, use_container_width=True)


def render_validation_analysis(df_ref_val, df_new_val, spectral_cols, common_ids,
                               mean_diff_original):
    """
    Renderiza el analisis de validacion comparando antes y despues.
    """
    st.markdown("#### Análisis de Validación")
    
    # Obtener IDs seleccionados
    ids_for_val = st.session_state.get('validation_selected_ids', list(common_ids))
    
    if len(ids_for_val) == 0:
        st.warning("⚠️ No has seleccionado ninguna muestra. Se usaran todas por defecto.")
        ids_for_val = list(common_ids)
    
    # Calcular diferencia despues de la correccion
    mean_diff_after = calculate_spectral_correction(
        df_ref_val,
        df_new_val,
        ids_for_val
    )
    
    # Guarda before/after en sesión para el informe
    st.session_state.validation_stats = {
        'mean_diff_before': mean_diff_original,
        'mean_diff_after': mean_diff_after,
    }
    
    # Guardar datos de validacion en session_state para el informe
    st.session_state.validation_data = {
        'df_ref_val': df_ref_val,
        'df_new_val': df_new_val,
        'lamp_ref': 'Referencia',
        'lamp_new': 'Nueva',
        'common_ids': common_ids,
        'selected_ids': ids_for_val,
        'mean_diff_after': mean_diff_after,
        'spectral_cols': spectral_cols
    }
    
    # Crear DataFrame para visualizacion
    df_comparison = pd.DataFrame({
        "Canal": range(1, len(mean_diff_original) + 1),
        "Diferencia_ANTES": mean_diff_original,
        "Diferencia_DESPUES": mean_diff_after,
        "Mejora": mean_diff_original - mean_diff_after
    })
    
    # Visualizar diferencias ANTES vs DESPUES en expander
    with st.expander("📊 Ver Comparación: Antes vs Después de la Corrección", expanded=False):
        st.markdown("##### Comparación: Antes vs Después de la Corrección")
        fig_comparison = plot_validation_comparison(df_comparison)
        st.plotly_chart(fig_comparison, use_container_width=True)
    
    # Metricas de validacion
    render_validation_metrics(mean_diff_original, mean_diff_after)
    
    # Descargar datos de validacion
    render_validation_download(df_comparison)

    # Conclusion
    render_validation_conclusion(mean_diff_original, mean_diff_after)


def plot_validation_comparison(df_comparison):
    """
    Crea grafico comparando diferencias antes y despues.
    """
    import plotly.graph_objects as go
    
    fig = go.Figure()
    
    # Diferencia ANTES
    fig.add_trace(go.Scatter(
        x=df_comparison["Canal"],
        y=df_comparison["Diferencia_ANTES"],
        mode='lines',
        name='ANTES de correccion',
        line=dict(width=2, color='red'),
        hovertemplate='Canal: %{x}<br>Diferencia: %{y:.4f}<extra></extra>'
    ))
    
    # Diferencia DESPUES
    fig.add_trace(go.Scatter(
        x=df_comparison["Canal"],
        y=df_comparison["Diferencia_DESPUES"],
        mode='lines',
        name='DESPUES de correccion',
        line=dict(width=2, color='green'),
        hovertemplate='Canal: %{x}<br>Diferencia: %{y:.4f}<extra></extra>'
    ))
    
    # Linea de referencia
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    fig.update_layout(
        title='Diferencia espectral: ANTES vs DESPUES de aplicar correccion',
        xaxis_title='Canal espectral',
        yaxis_title='Diferencia',
        height=600,
        hovermode='closest',
        template='plotly_white',
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="right",
            x=0.99
        )
    )
    
    return fig


def render_validation_metrics(mean_diff_before, mean_diff_after):
    """
    Renderiza metricas de validacion.
    """
    st.markdown("##### Métricas de Validación")
    
    # Calcular metricas
    max_before = np.max(np.abs(mean_diff_before))
    max_after = np.max(np.abs(mean_diff_after))
    
    mean_before = np.mean(np.abs(mean_diff_before))
    mean_after = np.mean(np.abs(mean_diff_after))
    
    std_before = np.std(mean_diff_before)
    std_after = np.std(mean_diff_after)
    
    # Calcular mejora porcentual
    improvement_max = ((max_before - max_after) / max_before * 100) if max_before != 0 else 0
    improvement_mean = ((mean_before - mean_after) / mean_before * 100) if mean_before != 0 else 0
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Diferencia máxima",
            f"{max_after:.6f}",
            delta=f"{-improvement_max:.1f}%",
            delta_color="inverse"
        )
        st.caption(f"Antes: {max_before:.6f}")
    
    with col2:
        st.metric(
            "Diferencia media",
            f"{mean_after:.6f}",
            delta=f"{-improvement_mean:.1f}%",
            delta_color="inverse"
        )
        st.caption(f"Antes: {mean_before:.6f}")
    
    with col3:
        st.metric(
            "Desviación estándar",
            f"{std_after:.6f}",
            delta=f"{std_before - std_after:.6f}",
            delta_color="inverse"
        )
        st.caption(f"Antes: {std_before:.6f}")


def render_validation_download(df_comparison):
    """
    Renderiza boton de descarga de datos de validacion.
    """
    csv_val = io.StringIO()
    df_comparison.to_csv(csv_val, index=False)
    
    st.download_button(
        "📥 Descargar datos de validación (CSV)",
        data=csv_val.getvalue(),
        file_name=f"validacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )


def render_validation_conclusion(mean_diff_before, mean_diff_after):
    """
    Renderiza la conclusion del proceso de validacion.
    """
    st.markdown("---")
    st.markdown("##### Conclusión: Validación con Standard Kit")
    
    # Calcular mejora
    max_before = np.max(np.abs(mean_diff_before))
    max_after = np.max(np.abs(mean_diff_after))
    improvement = ((max_before - max_after) / max_before * 100) if max_before != 0 else 0
    
    # Umbrales de evaluacion
    if max_after < 0.001:  # Excelente
        st.success(f"""
        ✅ **EXCELENTE: Corrección muy exitosa**
        
        La diferencia máxima entre lámparas se redujo a {max_after:.6f} (mejora del {improvement:.1f}%).
        El ajuste de baseline es óptimo y las lámparas están perfectamente alineadas.
        """)
    elif max_after < 0.01:  # Bueno
        st.success(f"""
        ✅ **BUENO: Corrección exitosa**
        
        La diferencia máxima entre lámparas se redujo a {max_after:.6f} (mejora del {improvement:.1f}%).
        El ajuste de baseline funciona correctamente.
        """)
    elif improvement > 50:  # Aceptable pero hay mejora
        st.info(f"""
        ℹ️ **ACEPTABLE: Corrección parcial**
        
        La diferencia máxima se redujo en un {improvement:.1f}%, pero aún queda una diferencia de {max_after:.6f}.
        Considera revisar:
        - La calidad de las mediciones del Standard Kit
        - Las condiciones ambientales durante las mediciones
        - El estado de las lámparas
        """)
    else:  # Problema
        st.warning(f"""
        ⚠️ **ATENCIÓN: Corrección insuficiente**
        
        La diferencia máxima solo mejoró un {improvement:.1f}%. Diferencia actual: {max_after:.6f}.
        
        **Recomendaciones:**
        1. Verifica que instalaste el baseline corregido correctamente
        2. Asegúrate de que reiniciaste el equipo si es necesario
        3. Revisa que las mediciones se tomaron en condiciones estables
        4. Considera repetir el proceso de ajuste con diferentes muestras
        """)


def render_validation_report_entrypoint(fallback_partial: bool = False, preview: bool = False):
    """
    Genera el HTML del informe y ofrece descarga.
    """
    import traceback
    from core.spectral_processing import apply_baseline_correction

    st.markdown("#### 📄 Generar Informe")

    kit_data_value        = st.session_state.get('kit_data')
    baseline_data_value   = st.session_state.get('baseline_data')
    val_stats_value       = st.session_state.get('validation_stats') or {}
    valdata_value         = st.session_state.get('validation_data')

    mean_diff_before_val  = val_stats_value.get('mean_diff_before')
    mean_diff_after_val   = val_stats_value.get('mean_diff_after')

    has_kit       = kit_data_value is not None
    has_baseline  = baseline_data_value is not None
    has_after     = mean_diff_after_val is not None
    has_valdata   = valdata_value is not None

    # Inicializar html_content en session_state si no existe
    if 'validation_report_html' not in st.session_state:
        st.session_state.validation_report_html = None

    if st.button("📥 Generar Informe", use_container_width=True, type="primary", key="btn_generate_validation_report"):
        try:
            if has_kit and has_baseline and has_after and has_valdata:
                from core.report_generator import generate_validation_report
                ref_corrected_value = apply_baseline_correction(
                    baseline_data_value['ref_spectrum'],
                    kit_data_value['mean_diff']
                )
                origin_value = baseline_data_value.get('origin')
                html_content = generate_validation_report(
                    kit_data_value,
                    baseline_data_value,
                    ref_corrected_value,
                    origin_value,
                    valdata_value,
                    mean_diff_before_val,
                    mean_diff_after_val
                )

            elif has_kit and has_baseline:
                from core.report_generator import generate_html_report
                ref_corrected_value = apply_baseline_correction(
                    baseline_data_value['ref_spectrum'],
                    kit_data_value['mean_diff']
                )
                origin_value = baseline_data_value.get('origin')
                html_content = generate_html_report(
                    kit_data_value,
                    baseline_data_value,
                    ref_corrected_value,
                    origin_value
                )

            elif has_kit and not has_baseline:
                from core.report_generator import generate_partial_report
                html_content = generate_partial_report(
                    kit_data=kit_data_value,
                    baseline_data=None,
                    ref_corrected=None,
                    origin=None,
                    validation_data=valdata_value if (has_after and has_valdata) else None,
                    mean_diff_before=mean_diff_before_val if has_after else None,
                    mean_diff_after=mean_diff_after_val if has_after else None
                )

            elif fallback_partial:
                from core.report_generator import generate_partial_report
                html_content = generate_partial_report(
                    kit_data=kit_data_value,
                    baseline_data=baseline_data_value,
                    ref_corrected=None,
                    origin=None,
                    validation_data=valdata_value,
                    mean_diff_before=mean_diff_before_val,
                    mean_diff_after=mean_diff_after_val
                )
            else:
                st.error("❌ No hay datos suficientes para generar el informe.")
                return

            # Guardar en session_state
            st.session_state.validation_report_html = html_content
            st.success("✅ Informe generado correctamente")

        except Exception as e:
            st.error(f"❌ Error al generar el informe: {e}")
            st.code(traceback.format_exc())
            st.session_state.validation_report_html = f"""
            <html><body style="font-family:Arial">
              <h1>Informe parcial (error)</h1>
              <pre style="white-space:pre-wrap">{traceback.format_exc()}</pre>
            </body></html>
            """

    # Mostrar botón de descarga si existe el HTML
    if st.session_state.validation_report_html:
        client_data = st.session_state.get('client_data') or {}
        filename = f"Informe_Validacion_{client_data.get('sensor_sn','sensor')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

        st.download_button(
            label="⬇️ Descargar Informe HTML",
            data=st.session_state.validation_report_html.encode("utf-8"),
            file_name=filename,
            mime="text/html",
            use_container_width=True,
            key="btn_download_validation_report"
        )

        # Vista previa opcional
        if preview:
            if st.toggle("👁️ Previsualizar informe aquí", key="toggle_preview_validation"):
                try:
                    st.components.v1.html(st.session_state.validation_report_html, height=900, scrolling=True)
                except Exception:
                    with st.expander("Ver HTML (fallback)"):
                        st.code(st.session_state.validation_report_html, language="html")