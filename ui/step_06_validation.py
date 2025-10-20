# -*- coding: utf-8 -*-
"""
Paso 6: Validacion Post-Correccion
"""
import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime
from config import INSTRUCTIONS, MESSAGES
from session_manager import has_kit_data, has_correction_data, reset_session_state
from core.file_handlers import load_tsv_file, get_spectral_columns
from core.spectral_processing import (
    group_measurements_by_lamp, 
    find_common_samples,
    calculate_spectral_correction
)
from utils.plotting import plot_kit_spectra, plot_correction_differences
from utils.validators import validate_common_samples


def render_validation_step():
    """
    Renderiza el paso de validacion post-correccion (Paso 6).
    """
    st.markdown("## PASO 7 DE 7: Validacion Post-Correccion")
    
    # Verificar que existan datos previos
    if not has_kit_data() or not has_correction_data():
        st.error("No hay datos de correccion previos. Completa primero los pasos anteriores.")
        return
    
    kit_data = st.session_state.kit_data
    lamp_ref = kit_data['lamp_ref']
    lamp_new = kit_data['lamp_new']
    mean_diff_original = kit_data['mean_diff']
    
    # Instrucciones
    st.info(f"""
    **Instrucciones para la validacion:**
    
    1. **Instala el baseline corregido** en tu espectrometro (archivo .ref o .csv del Paso 5)
    2. **Reinicia el equipo** si es necesario segun el fabricante
    3. **Mide el Standard Kit** nuevamente con ambas lamparas:
       - Lampara de referencia: **{lamp_ref}**
       - Lampara nueva: **{lamp_new}**
    4. **Exporta las mediciones** a formato TSV
    5. **Sube el archivo** aqui abajo
    
    El sistema comparara las diferencias espectrales ANTES y DESPUES de la correccion
    para verificar que el ajuste fue exitoso.
    """)
    
    st.markdown("---")
    
    # Uploader de archivo de validacion
    validation_file = st.file_uploader(
        "Sube el archivo TSV con las mediciones de validacion",
        type="tsv",
        key="validation_upload"
    )
    
    if validation_file:
        try:
            process_validation_file(
                validation_file, 
                lamp_ref, 
                lamp_new,
                mean_diff_original
            )
        except Exception as e:
            st.error(f"Error al procesar el archivo: {str(e)}")
    
    # Boton para volver a empezar
    st.markdown("---")
    if st.button("Finalizar y reiniciar proceso", use_container_width=True):
        reset_session_state()
        st.rerun()


def process_validation_file(file, lamp_ref_original, lamp_new_original, mean_diff_original):
    """
    Procesa el archivo de validacion.
    
    Args:
        file: Archivo TSV subido
        lamp_ref_original (str): Lampara de referencia original (del paso 3)
        lamp_new_original (str): Lampara nueva original (del paso 3)
        mean_diff_original (np.array): Diferencia espectral original (antes de correccion)
    """
    # Cargar archivo
    df_val = load_tsv_file(file)
    
    # Obtener columnas espectrales
    spectral_cols = get_spectral_columns(df_val)
    
    # Convertir columnas espectrales a numerico
    df_val[spectral_cols] = df_val[spectral_cols].apply(pd.to_numeric, errors="coerce")
    
    # Filtrar muestras (excluir WSTD)
    df_val_kit = df_val[df_val["ID"].str.upper() != "WSTD"].copy()
    
    if len(df_val_kit) == 0:
        st.error("No se encontraron muestras validas en el archivo.")
        return
    
    # Obtener informacion basica
    lamp_options = [lamp for lamp in df_val_kit["Note"].unique() if pd.notna(lamp)]
    sample_ids = df_val_kit["ID"].unique()
    
    # Mostrar informacion
    st.success("Archivo de validacion cargado correctamente")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Mediciones totales", len(df_val_kit))
    with col2:
        st.metric("Muestras unicas", len(sample_ids))
    with col3:
        st.metric("Lamparas detectadas", len(lamp_options))
    
    # Seleccion de lamparas para validacion
    st.markdown("### Identificacion de Lamparas")
    
    # Mostrar info de las lámparas originales
    st.info(f"""
    **Lamparas usadas en el ajuste original:**
    - Referencia: **{lamp_ref_original}**
    - Nueva: **{lamp_new_original}**
    
    Puedes mantener la misma configuracion o seleccionar otras si es necesario.
    """)
    
    lamp_ref, lamp_new = render_validation_lamp_selection(
        lamp_options, 
        lamp_ref_original, 
        lamp_new_original
    )
    
    # Verificar que sean lamparas diferentes
    if lamp_ref == lamp_new:
        st.error("Debes seleccionar lamparas diferentes para referencia y nueva.")
        return
    
    # Agrupar mediciones por lampara
    df_ref_val, df_new_val = group_measurements_by_lamp(
        df_val_kit, spectral_cols, lamp_ref, lamp_new
    )
    
    # Encontrar muestras comunes
    common_ids_val = find_common_samples(df_ref_val, df_new_val)
    
    if not validate_common_samples(common_ids_val):
        return
    
    # Filtrar solo muestras comunes
    df_ref_val = df_ref_val.loc[common_ids_val]
    df_new_val = df_new_val.loc[common_ids_val]
    
    st.success(f"Muestras comunes encontradas: {len(common_ids_val)}")
    
    # Seleccion de muestras para validacion
    render_validation_sample_selection(df_val_kit, common_ids_val, lamp_ref, lamp_new)
    
    # Visualizacion de espectros de validacion
    render_validation_spectra_visualization(
        df_ref_val, df_new_val, spectral_cols, 
        lamp_ref, lamp_new, common_ids_val
    )
    
    # Calcular diferencias en validacion
    render_validation_analysis(
        df_ref_val, df_new_val, spectral_cols,
        common_ids_val, mean_diff_original,
        lamp_ref, lamp_new
    )


def render_validation_lamp_selection(lamp_options, lamp_ref_default, lamp_new_default):
    """
    Renderiza los selectores para identificar lamparas en validacion.
    
    Args:
        lamp_options (list): Lista de lamparas disponibles
        lamp_ref_default (str): Lampara de referencia por defecto
        lamp_new_default (str): Lampara nueva por defecto
        
    Returns:
        tuple: (lamp_ref, lamp_new) nombres de las lamparas seleccionadas
    """
    col1, col2 = st.columns(2)
    
    # Determinar indices por defecto
    try:
        ref_index = lamp_options.index(lamp_ref_default)
    except ValueError:
        ref_index = 0
    
    try:
        new_index = lamp_options.index(lamp_new_default)
    except ValueError:
        new_index = min(1, len(lamp_options) - 1)
    
    with col1:
        lamp_ref = st.selectbox(
            "Selecciona la lampara de REFERENCIA", 
            lamp_options, 
            index=ref_index, 
            key="validation_lamp_ref_select"
        )
    
    with col2:
        lamp_new = st.selectbox(
            "Selecciona la lampara NUEVA", 
            lamp_options, 
            index=new_index, 
            key="validation_lamp_new_select"
        )
    
    return lamp_ref, lamp_new


def render_validation_sample_selection(df, common_ids, lamp_ref, lamp_new):
    """
    Renderiza la interfaz de seleccion de muestras para validacion.
    """
    st.markdown("### Seleccion de muestras para validacion")
    
    # Inicializar seleccion si no existe
    if 'validation_selected_ids' not in st.session_state:
        st.session_state.validation_selected_ids = list(common_ids)
    
    if 'validation_pending_selection' not in st.session_state:
        st.session_state.validation_pending_selection = list(st.session_state.validation_selected_ids)
    
    # Construir tabla de muestras
    df_samples = pd.DataFrame({
        'ID': list(common_ids),
        f'Mediciones {lamp_ref}': [
            len(df[(df['ID'] == i) & (df['Note'] == lamp_ref)]) 
            for i in common_ids
        ],
        f'Mediciones {lamp_new}': [
            len(df[(df['ID'] == i) & (df['Note'] == lamp_new)]) 
            for i in common_ids
        ],
        'Usar en validacion': [
            i in st.session_state.validation_pending_selection 
            for i in common_ids
        ]
    })
    
    with st.expander("Ver y seleccionar muestras"):
        with st.form("form_validation_samples", clear_on_submit=False):
            edited = st.data_editor(
                df_samples,
                use_container_width=True,
                hide_index=True,
                disabled=[f'Mediciones {lamp_ref}', f'Mediciones {lamp_new}'],
                key="editor_validation_samples"
            )
            
            col_a, col_b, col_c, col_d = st.columns([1, 1, 1, 2])
            btn_all = col_a.form_submit_button("Seleccionar todo")
            btn_none = col_b.form_submit_button("Deseleccionar todo")
            btn_invert = col_c.form_submit_button("Invertir seleccion")
            btn_confirm = col_d.form_submit_button("Confirmar seleccion", type="primary")
        
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
            st.success(f"Seleccion confirmada: {len(st.session_state.validation_selected_ids)} muestras.")
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


def render_validation_spectra_visualization(df_ref_val, df_new_val, spectral_cols,
                                           lamp_ref, lamp_new, common_ids):
    """
    Renderiza la visualizacion de espectros de validacion.
    """
    with st.expander("Ver espectros de validacion"):
        # Obtener muestras seleccionadas
        selected_ids = st.session_state.get('validation_selected_ids', list(common_ids))
        ids_to_plot = selected_ids if len(selected_ids) > 0 else list(common_ids)
        
        if len(ids_to_plot) < len(common_ids):
            st.info(f"Mostrando {len(ids_to_plot)} de {len(common_ids)} muestras (solo seleccionadas)")
        
        fig = plot_kit_spectra(
            df_ref_val, df_new_val,
            spectral_cols, lamp_ref, lamp_new, ids_to_plot
        )
        st.plotly_chart(fig, use_container_width=True)


def render_validation_analysis(df_ref_val, df_new_val, spectral_cols, common_ids,
                               mean_diff_original, lamp_ref, lamp_new):
    """
    Renderiza el analisis de validacion comparando antes y despues.
    """
    st.markdown("### Analisis de Validacion")
    
    # Obtener IDs seleccionados
    ids_for_val = st.session_state.get('validation_selected_ids', list(common_ids))
    
    if len(ids_for_val) == 0:
        st.warning("No has seleccionado ninguna muestra. Se usaran todas por defecto.")
        ids_for_val = list(common_ids)
    
    # Calcular diferencia despues de la correccion
    mean_diff_after = calculate_spectral_correction(
        df_ref_val,
        df_new_val,
        ids_for_val
    )
    
    # Guardar datos de validacion en session_state para el informe
    st.session_state.validation_data = {
        'df_ref_val': df_ref_val,
        'df_new_val': df_new_val,
        'lamp_ref': lamp_ref,
        'lamp_new': lamp_new,
        'common_ids': common_ids,
        'selected_ids': ids_for_val,
        'mean_diff_after': mean_diff_after,
        'spectral_cols': spectral_cols  # <- AGREGAR ESTA LINEA
    }
    
    
    # Crear DataFrame para visualizacion
    df_comparison = pd.DataFrame({
        "Canal": range(1, len(mean_diff_original) + 1),
        "Diferencia_ANTES": mean_diff_original,
        "Diferencia_DESPUES": mean_diff_after,
        "Mejora": mean_diff_original - mean_diff_after
    })
    
    # Visualizar diferencias ANTES vs DESPUES
    st.markdown("#### Comparacion: Antes vs Despues de la Correccion")
    fig_comparison = plot_validation_comparison(df_comparison)
    st.plotly_chart(fig_comparison, use_container_width=True)
    
    # Metricas de validacion
    render_validation_metrics(mean_diff_original, mean_diff_after)
    
    # Descargar datos de validacion
    render_validation_download(df_comparison, lamp_ref, lamp_new)
    
    # NUEVO: Generar informe completo
    render_validation_report_section(mean_diff_original, mean_diff_after)
    
    # Conclusion
    render_validation_conclusion(mean_diff_original, mean_diff_after)


def render_validation_report_section(mean_diff_before, mean_diff_after):
    """
    Renderiza la seccion de generacion de informe de validacion.
    """
    st.markdown("---")
    st.markdown("### 📋 Generar Informe Completo de Validacion")
    
    if st.button("📄 Generar Informe con Validacion", use_container_width=True, type="primary"):
        try:
            from core.report_generator import generate_validation_report
            
            # Obtener todos los datos necesarios
            kit_data = st.session_state.kit_data
            baseline_data = st.session_state.baseline_data
            validation_data = st.session_state.validation_data
            
            # Obtener baseline corregido (recalcular si es necesario)
            from core.spectral_processing import apply_baseline_correction
            ref_spectrum = baseline_data['ref_spectrum']
            mean_diff = kit_data['mean_diff']
            ref_corrected = apply_baseline_correction(ref_spectrum, mean_diff)
            origin = baseline_data['origin']
            
            # Generar informe
            html_content = generate_validation_report(
                kit_data,
                baseline_data,
                ref_corrected,
                origin,
                validation_data,
                mean_diff_before,
                mean_diff_after
            )
            
            client_data = st.session_state.client_data or {}
            filename = f"Informe_Validacion_{client_data.get('sensor_sn', 'sensor')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            
            st.download_button(
                label="📥 Descargar Informe HTML Completo",
                data=html_content,
                file_name=filename,
                mime="text/html",
                use_container_width=True
            )
            st.success("✅ Informe de validacion generado correctamente")
            
        except Exception as e:
            st.error(f"❌ Error al generar el informe: {str(e)}")
            import traceback
            st.error(traceback.format_exc())


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
    st.markdown("#### Metricas de Validacion")
    
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
            "Diferencia maxima",
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
            "Desviacion estandar",
            f"{std_after:.6f}",
            delta=f"{std_before - std_after:.6f}",
            delta_color="inverse"
        )
        st.caption(f"Antes: {std_before:.6f}")


def render_validation_download(df_comparison, lamp_ref, lamp_new):
    """
    Renderiza boton de descarga de datos de validacion.
    """
    csv_val = io.StringIO()
    df_comparison.to_csv(csv_val, index=False)
    
    st.download_button(
        "Descargar datos de validacion (CSV)",
        data=csv_val.getvalue(),
        file_name=f"validacion_{lamp_ref}_vs_{lamp_new}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )


def render_validation_conclusion(mean_diff_before, mean_diff_after):
    """
    Renderiza la conclusion del proceso de validacion.
    """
    st.markdown("---")
    st.markdown("### Conclusion")
    
    # Calcular mejora
    max_before = np.max(np.abs(mean_diff_before))
    max_after = np.max(np.abs(mean_diff_after))
    improvement = ((max_before - max_after) / max_before * 100) if max_before != 0 else 0
    
    # Umbrales de evaluacion
    if max_after < 0.001:  # Excelente
        st.success(f"""
        **EXCELENTE: Correccion muy exitosa**
        
        La diferencia maxima entre lamparas se redujo a {max_after:.6f} (mejora del {improvement:.1f}%).
        El ajuste de baseline es optimo y las lamparas estan perfectamente alineadas.
        """)
    elif max_after < 0.01:  # Bueno
        st.success(f"""
        **BUENO: Correccion exitosa**
        
        La diferencia maxima entre lamparas se redujo a {max_after:.6f} (mejora del {improvement:.1f}%).
        El ajuste de baseline funciona correctamente.
        """)
    elif improvement > 50:  # Aceptable pero hay mejora
        st.info(f"""
        **ACEPTABLE: Correccion parcial**
        
        La diferencia maxima se redujo en un {improvement:.1f}%, pero aun queda una diferencia de {max_after:.6f}.
        Considera revisar:
        - La calidad de las mediciones del Standard Kit
        - Las condiciones ambientales durante las mediciones
        - El estado de las lamparas
        """)
    else:  # Problema
        st.warning(f"""
        **ATENCION: Correccion insuficiente**
        
        La diferencia maxima solo mejoro un {improvement:.1f}%. Diferencia actual: {max_after:.6f}.
        
        **Recomendaciones:**
        1. Verifica que instalaste el baseline corregido correctamente
        2. Asegurate de que reiniciaste el equipo si es necesario
        3. Revisa que las mediciones se tomaron en condiciones estables
        4. Considera repetir el proceso de ajuste con diferentes muestras
        """)