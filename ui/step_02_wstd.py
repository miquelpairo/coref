"""
Paso 3: Diagnostico WSTD (White Standard) + Muestras de Control
"""
import streamlit as st
import pandas as pd
import numpy as np
import io
import plotly.graph_objects as go
from config import INSTRUCTIONS, MESSAGES, SPECIAL_IDS, WSTD_THRESHOLDS, DIAGNOSTIC_STATUS
from session_manager import (
    save_wstd_data,
    save_reference_tsv,  # ⭐ NUEVO - Para guardar TSV completo
    go_to_next_step,
    save_control_samples_initial
)
from core.file_handlers import load_tsv_file, get_spectral_columns
from utils.validators import validate_wstd_measurements
from utils.plotting import plot_wstd_spectra
from utils.control_samples import extract_predictions_from_results


def render_wstd_step():
    """
    Renderiza el paso de diagnostico inicial con WSTD (Paso 3).
    Incluye opción para cargar muestras de control.
    """
    st.markdown("## PASO 3 DE 5: Diagnóstico Inicial")  # ⭐ CAMBIADO: 3 DE 5
    st.markdown(INSTRUCTIONS['wstd'])
    st.markdown("---")
    
    # ========== SECCIÓN 1: EXTERNAL WHITE (OBLIGATORIO) ==========
    st.markdown("### 🔍 Diagnóstico External White (Obligatorio)")
    st.info("""
    📋 **Este archivo TSV se usará como referencia en el Paso 4 (Alineamiento de Baseline)**
    
    Asegúrate de medir con el baseline actual del equipo antes de cualquier ajuste.
    """)
    
    wstd_file = st.file_uploader(
        "Sube el archivo TSV con las mediciones de External White", 
        type="tsv", 
        key="wstd_upload"
    )
    
    if wstd_file:
        st.session_state.unsaved_changes = True
    
    wstd_processed = False
    
    if wstd_file:
        try:
            df = load_tsv_file(wstd_file)
            spectral_cols = get_spectral_columns(df)
            
            # ⭐ NUEVO: Guardar el TSV completo para usar en Paso 4
            save_reference_tsv(df, spectral_cols)
            st.success("✅ Archivo TSV guardado como referencia para el Paso 4")
            
            st.markdown("#### Selecciona las filas que corresponden a la referencia externa (External White)")
            st.info("✅ Marca las casillas de las mediciones que corresponden al White Standard.")
            
            # Crear tabla con índice visible
            df_display = df[['ID', 'Note']].copy()
            df_display.insert(0, 'Seleccionar', False)
            
            if 'wstd_selected_rows' not in st.session_state:
                st.session_state.wstd_selected_rows = []
            
            edited_df = st.data_editor(
                df_display,
                hide_index=False,
                use_container_width=True,
                disabled=['ID', 'Note'],
                key='wstd_row_selector'
            )
            
            selected_indices = edited_df[edited_df['Seleccionar'] == True].index.tolist()
            
            if len(selected_indices) == 0:
                st.warning("⚠️ No has seleccionado ninguna fila. Por favor, marca las mediciones External White para el diagnóstico.")
            else:
                df_wstd = df.loc[selected_indices].copy()
                
                st.success(f"✅ {len(df_wstd)} filas seleccionadas para análisis External White")
                
                # Mostrar info detallada
                st.write("**Filas seleccionadas:**")
                display_df = df_wstd[['ID', 'Note']].copy()
                display_df.insert(0, 'Índice fila', selected_indices)
                st.dataframe(display_df, use_container_width=True)
                
                df_wstd[spectral_cols] = df_wstd[spectral_cols].apply(pd.to_numeric, errors="coerce")
                
                st.write(f"**Canales espectrales:** {len(spectral_cols)}")
                
                # Envolver gráficos en expander
                with st.expander("📊 Ver Diagnóstico Visual", expanded=False):
                    st.markdown("#### Diagnóstico Visual")
                    fig = plot_wstd_individual(df_wstd, spectral_cols, selected_indices)
                    st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("#### Métricas de Diagnóstico")
                render_diagnostic_metrics(df_wstd, spectral_cols, selected_indices)
                
                save_wstd_data(
                    df=df_wstd,
                    grouped=None,
                    spectral_cols=spectral_cols,
                    lamps=None
                )
                
                wstd_processed = True
                
        except Exception as e:
            st.error(f"❌ Error al procesar el archivo: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
    
    # ========== SECCIÓN 2: MUESTRAS DE CONTROL (OPCIONAL) ==========
    st.markdown("---")
    st.markdown("### 🧪 Muestras de Control (Opcional pero Recomendado)")
    st.markdown(INSTRUCTIONS['control_samples'])
    
    control_file = st.file_uploader(
        "Sube el archivo TSV con las muestras de control (ANTES del ajuste)",
        type="tsv",
        key="control_initial_upload",
        help="Las muestras deben incluir la columna 'Result' con las predicciones"
    )
    
    control_processed = False
    
    if control_file:
        try:
            df_control = load_tsv_file(control_file)
            
            # Verificar que tenga la columna Result
            if 'Result' not in df_control.columns:
                st.error(MESSAGES['error_no_predictions'])
            else:
                st.success(MESSAGES['success_file_loaded'])
                
                # Mostrar preview de las muestras
                st.markdown("#### Muestras detectadas en el archivo:")
                preview_cols = ['ID', 'Note', 'Recipe', 'Result']
                available_cols = [col for col in preview_cols if col in df_control.columns]
                st.dataframe(df_control[available_cols], use_container_width=True)
                
                # Seleccionar muestras de control
                st.markdown("#### Selecciona las muestras de control:")
                st.info("✅ Estas muestras se medirán nuevamente al final para validar el ajuste.")
                
                df_control_display = df_control[['ID', 'Note']].copy()
                
                # Añadir Recipe si existe
                if 'Recipe' in df_control.columns:
                    df_control_display['Recipe'] = df_control['Recipe']
                
                df_control_display.insert(0, 'Usar como Control', False)
                
                # Deshabilitar Recipe si existe
                disabled_cols = ['ID', 'Note', 'Recipe'] if 'Recipe' in df_control.columns else ['ID', 'Note']
                
                edited_control = st.data_editor(
                    df_control_display,
                    hide_index=False,
                    use_container_width=True,
                    disabled=disabled_cols,
                    key='control_selector'
                )
                
                selected_control_indices = edited_control[edited_control['Usar como Control'] == True].index.tolist()
                
                if len(selected_control_indices) > 0:
                    df_control_selected = df_control.loc[selected_control_indices].copy()
                    
                    st.success(f"✅ {len(df_control_selected)} muestras de control seleccionadas")
                    
                    # Mostrar información de recetas si existe
                    if 'Recipe' in df_control_selected.columns:
                        recipes = df_control_selected['Recipe'].dropna().unique()
                        if len(recipes) > 0:
                            recipes_str = ', '.join([str(r) for r in recipes])
                            st.info(f"📋 **Recetas detectadas:** {recipes_str}")
                    
                    # Extraer predicciones
                    predictions_df = extract_predictions_from_results(df_control_selected)

                    if not predictions_df.empty:
                        st.markdown("#### Predicciones detectadas:")
                        st.dataframe(predictions_df, use_container_width=True)

                        # Normalizar y guardar
                        result_col = None
                        for c in ('Result', 'Results'):
                            if c in df_control_selected.columns:
                                result_col = c
                                break

                        df_to_save = df_control_selected.copy()
                        if result_col and result_col != 'Result':
                            df_to_save.rename(columns={result_col: 'Result'}, inplace=True)

                        df_to_save['ID'] = df_to_save['ID'].astype(str).str.strip()
                        
                        if 'Recipe' in df_control.columns and 'Recipe' not in df_to_save.columns:
                            df_to_save['Recipe'] = df_control.loc[selected_control_indices, 'Recipe']

                        spectral_cols = get_spectral_columns(df_control)

                        sample_ids = df_to_save['ID'].tolist()
                        save_control_samples_initial(
                            df=df_to_save,
                            spectral_cols=spectral_cols,
                            sample_ids=sample_ids
                        )

                        st.info(f"💾 {MESSAGES['success_control_initial']}")
                        st.info(f"📝 **Importante:** Anota estos IDs: {', '.join(sample_ids)}")
                        st.info("Los necesitarás al final del proceso para medir las mismas muestras.")
                        
                        control_processed = True
                    else:
                        st.warning("⚠️ No se pudieron extraer predicciones del campo Result")
                else:
                    st.warning("⚠️ No has seleccionado ninguna muestra de control")
                    
        except Exception as e:
            st.error(f"❌ Error al procesar muestras de control: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
    else:
        st.info("ℹ️ Puedes omitir las muestras de control y continuar solo con el diagnóstico WSTD")
    
    # ========== BOTONES DE NAVEGACIÓN ==========
    st.markdown("---")
    
    # ⭐ MODIFICADO: Solo permitir continuar si hay archivo WSTD cargado
    has_wstd = st.session_state.get('reference_tsv') is not None
    has_control = st.session_state.get('control_samples_initial') is not None
    
    if has_wstd:
        col_continue, col_space = st.columns([3, 1])
        
        # Mensaje informativo sobre qué datos están disponibles
        if wstd_processed and has_control:
            st.success("✅ TSV de referencia guardado y muestras de control seleccionadas")
        elif wstd_processed:
            st.success("✅ TSV de referencia guardado (muestras de control opcionales)")
        elif has_wstd:
            st.success("✅ TSV de referencia disponible del paso anterior")
        
        with col_continue:
            if st.button("✅ Continuar al Paso 4", type="primary", use_container_width=True):
                st.session_state.unsaved_changes = False
                go_to_next_step()
    else:
        st.warning("""
        ⚠️ **Debes cargar el archivo TSV de External White para continuar**
        
        Este archivo es necesario como referencia para el alineamiento de baseline en el Paso 4.
        """)


# ========== FUNCIONES DE VISUALIZACIÓN (sin cambios) ==========

def plot_wstd_individual(df_wstd, spectral_cols, selected_indices):
    """
    Crea gráfico con cada medición External White individual y sus diferencias.
    """
    from plotly.subplots import make_subplots
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(
            'Espectros External White - Desviación respecto a referencia ideal',
            'Diferencias entre mediciones External White'
        ),
        vertical_spacing=0.12
    )
    
    channels = list(range(1, len(spectral_cols) + 1))
    
    # Subplot 1: Espectros individuales
    for i, (idx, row) in enumerate(df_wstd.iterrows()):
        spectrum = row[spectral_cols].values
        label = f"Fila {selected_indices[i]}: {row['ID']}"
        
        fig.add_trace(
            go.Scatter(
                x=channels,
                y=spectrum,
                mode='lines',
                name=label,
                line=dict(width=1.5),
                hovertemplate=f'{label}<br>Canal: %{{x}}<br>Desviación: %{{y:.6f}}<extra></extra>'
            ),
            row=1, col=1
        )
    
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5, row=1, col=1)
    
    # Subplot 2: Diferencias entre mediciones
    if len(df_wstd) >= 2:
        spectra_list = [row[spectral_cols].values for idx, row in df_wstd.iterrows()]
        
        if len(df_wstd) == 2:
            diff = spectra_list[0] - spectra_list[1]
            label_diff = f"Fila {selected_indices[0]} - Fila {selected_indices[1]}"
            
            fig.add_trace(
                go.Scatter(
                    x=channels,
                    y=diff,
                    mode='lines',
                    name=label_diff,
                    line=dict(width=2, color='red'),
                    hovertemplate=f'{label_diff}<br>Canal: %{{x}}<br>Diferencia: %{{y:.6f}}<extra></extra>',
                    showlegend=False
                ),
                row=2, col=1
            )
        else:
            for i in range(1, len(spectra_list)):
                diff = spectra_list[0] - spectra_list[i]
                label_diff = f"Fila {selected_indices[0]} - Fila {selected_indices[i]}"
                
                fig.add_trace(
                    go.Scatter(
                        x=channels,
                        y=diff,
                        mode='lines',
                        name=label_diff,
                        line=dict(width=1.5),
                        hovertemplate=f'{label_diff}<br>Canal: %{{x}}<br>Diferencia: %{{y:.6f}}<extra></extra>',
                        showlegend=False
                    ),
                    row=2, col=1
                )
        
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5, row=2, col=1)
    
    fig.update_xaxes(title_text="Canal espectral", row=1, col=1)
    fig.update_xaxes(title_text="Canal espectral", row=2, col=1)
    fig.update_yaxes(title_text="Desviación", row=1, col=1)
    fig.update_yaxes(title_text="Diferencia", row=2, col=1)
    
    fig.update_layout(
        height=800,
        showlegend=True,
        hovermode='closest',
        template='plotly_white'
    )
    
    return fig


def render_diagnostic_metrics(df_wstd, spectral_cols, selected_indices):
    """
    Renderiza las métricas de diagnóstico para cada medición individual.
    """
    num_measurements = len(df_wstd)
    cols = st.columns(min(num_measurements, 4))
    
    for i, (idx, row) in enumerate(df_wstd.iterrows()):
        spectrum = row[spectral_cols].values
        
        col_idx = i % 4
        if i > 0 and col_idx == 0:
            cols = st.columns(min(num_measurements - i, 4))
        
        with cols[col_idx]:
            label = f"Fila {selected_indices[i]}: {row['ID']}"
            st.markdown(f"**{label}**")
            
            max_val = np.max(np.abs(spectrum))
            mean_val = np.mean(np.abs(spectrum))
            std_val = np.std(spectrum)
            
            st.metric("Desv. máxima", f"{max_val:.6f}")
            st.metric("Desv. media", f"{mean_val:.6f}")
            st.metric("Desv. estándar", f"{std_val:.6f}")
            
            status = get_diagnostic_status(max_val)
            display_diagnostic_status(status)
            
            with st.expander("Ver primeros valores"):
                st.write(f"Primeros 5 canales: {spectrum[:5]}")


def get_diagnostic_status(max_deviation):
    """
    Determina el estado del diagnóstico basado en la desviación máxima.
    """
    if max_deviation < WSTD_THRESHOLDS['good']:
        return 'good'
    elif max_deviation < WSTD_THRESHOLDS['warning']:
        return 'warning'
    else:
        return 'bad'


def display_diagnostic_status(status):
    """
    Muestra el estado del diagnóstico con el formato apropiado.
    """
    status_config = DIAGNOSTIC_STATUS[status]
    icon = status_config['icon']
    label = status_config['label']
    color = status_config['color']
    
    if color == 'green':
        st.success(f"{icon} {label}")
    elif color == 'warning':
        st.warning(f"{icon} {label}")
    else:
        st.error(f"{icon} {label}")