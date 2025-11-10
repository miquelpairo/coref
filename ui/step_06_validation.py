# -*- coding: utf-8 -*-
"""
Paso 7: Validacion Post-Correccion + Muestras de Control
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
    get_control_samples_initial,  # ⭐ NUEVO
    save_control_samples_final,   # ⭐ NUEVO
    has_control_samples_initial   # ⭐ NUEVO
)
from core.file_handlers import load_tsv_file, get_spectral_columns
from core.spectral_processing import (
    group_measurements_by_lamp, 
    find_common_samples,
    calculate_spectral_correction
)
from utils.plotting import plot_kit_spectra, plot_correction_differences
from utils.validators import validate_common_samples
# ⭐ NUEVO: Importar utilidades de muestras de control
from utils.control_samples import (
    extract_predictions_from_results,
    get_prediction_parameters,
    compare_predictions,
    get_prediction_status,
    plot_spectra_comparison,
    plot_predictions_comparison,
    calculate_spectral_metrics
)


def render_validation_step():
    st.markdown("## PASO 7 DE 7: Validación Post-Corrección")

    if not has_kit_data() or not has_correction_data():
        st.error("❌ No hay datos de corrección previos. Completa primero los pasos anteriores.")
        return

    # 1) Standard Kit
    render_standard_kit_validation()

    # 2) Muestras de Control
    st.markdown("---")
    render_control_samples_validation()

    # 3) 👉 Botón de informe (ÚNICO punto donde se renderiza)
    st.markdown("---")
    render_validation_report_entrypoint()   # <— aquí y solo aquí

    # 4) Reset
    st.markdown("---")
    if st.button("🔄 Finalizar y reiniciar proceso", use_container_width=True):
        st.session_state.unsaved_changes = False
        reset_session_state()
        st.rerun()


def render_standard_kit_validation():
    """
    Renderiza la sección de validación con Standard Kit (funcionalidad original).
    """
    st.markdown("### 📊 Validación con Standard Kit")
    
    kit_data = st.session_state.kit_data
    mean_diff_original = kit_data['mean_diff']
    
    # Instrucciones
    st.info(f"""
    **Instrucciones para la validación con Standard Kit:**
    
    1. **Instala el baseline corregido** en tu espectrómetro (archivo .ref o .csv del Paso 6)
    2. **Reinicia el equipo** si es necesario según el fabricante
    3. **Mide el Standard Kit** nuevamente con ambas lámparas
    4. **Exporta las mediciones** a 2 archivos TSV separados
    5. **Sube los archivos** aquí abajo
    
    El sistema comparará las diferencias espectrales ANTES y DESPUÉS de la corrección
    para verificar que el ajuste fue exitoso.
    """)
    
    # Uploaders de validación
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 1️⃣ TSV Referencia (validación)")
        ref_val_file = st.file_uploader(
            "Sube el TSV de REFERENCIA para validación",
            type=["tsv", "txt", "csv"],
            key="ref_validation_upload",
            help="Mediciones de referencia después de instalar baseline corregido"
        )
    
    with col2:
        st.markdown("#### 2️⃣ TSV Nueva Lámpara (validación)")
        new_val_file = st.file_uploader(
            "Sube el TSV de NUEVA lámpara para validación",
            type=["tsv", "txt", "csv"],
            key="new_validation_upload",
            help="Mediciones de nueva lámpara después de instalar baseline corregido"
        )
    
    if ref_val_file and new_val_file:
        try:
            process_validation_files(
                ref_val_file,
                new_val_file,
                mean_diff_original
            )
        except Exception as e:
            st.error(f"❌ Error al procesar los archivos: {str(e)}")
            import traceback
            st.error(traceback.format_exc())


def render_control_samples_validation():
    """
    ⭐ Renderiza la sección de validación con muestras de control.
    - Muestra SIEMPRE el botón de informe al final.
    - Si no hay muestras de control iniciales, solo informa y permite generar informe base.
    - Si hay iniciales y subes las finales, hace la comparativa y luego muestra el botón.
    """
    st.markdown("### 🧪 Validación con Muestras de Control")

    # Caso 1: No hay muestras de control iniciales guardadas
    if not has_control_samples_initial():
        st.info("""
        ℹ️ **No se cargaron muestras de control en el Paso 3**
        
        La validación con muestras de control es opcional. Si deseas usarla en futuros ajustes:
        - Carga muestras de control en el Paso 3 (Diagnóstico Inicial)
        - Podrás comparar automáticamente las predicciones antes/después del ajuste
        """)
        # Botón de informe siempre visible
        render_validation_report_entrypoint()
        return  # ← Importante: no intentes acceder a control_initial

    # Caso 2: Sí hay control inicial → seguimos
    control_initial = get_control_samples_initial()
    initial_sample_ids = control_initial.get('sample_ids', [])

    st.markdown(INSTRUCTIONS['validation_control'])

    st.success(f"""
    ✅ **Muestras de control iniciales detectadas**
    
    Se midieron **{len(initial_sample_ids)} muestras** en el Paso 3:
    - {', '.join(initial_sample_ids) if initial_sample_ids else '—'}
    
    📝 **Ahora mide las MISMAS muestras** con el baseline corregido instalado.
    """)

    # Uploader para las mediciones finales de control
    control_final_file = st.file_uploader(
        "Sube el archivo TSV con las muestras de control DESPUÉS del ajuste",
        type="tsv",
        key="control_final_upload",
        help="Usa los mismos IDs que en el Paso 3 para poder comparar"
    )

    if control_final_file:
        try:
            # Procesa el TSV final y muestra la comparativa
            process_control_samples_final(control_final_file, control_initial)
        except Exception as e:
            st.error(f"❌ Error al procesar muestras de control finales: {str(e)}")
            import traceback
            st.error(traceback.format_exc())




def process_control_samples_final(control_final_file, control_initial):
    """
    ⭐ NUEVA FUNCIÓN: Procesa las muestras de control finales y realiza la comparación.
    """
    # Cargar archivo
    df_final = load_tsv_file(control_final_file)
    
    # Verificar que tenga la columna Result
    if 'Result' not in df_final.columns:
        st.error(MESSAGES['error_no_predictions'])
        return
    
    st.success(MESSAGES['success_file_loaded'])
    
    # Obtener datos iniciales
    df_initial = control_initial['df']
    spectral_cols = control_initial['spectral_cols']
    initial_sample_ids = control_initial['sample_ids']
    
    # Mostrar preview con Recipe si existe
    st.markdown("#### Muestras detectadas en el archivo final:")
    preview_cols = ['ID', 'Note', 'Recipe', 'Result']
    available_cols = [col for col in preview_cols if col in df_final.columns]
    st.dataframe(df_final[available_cols], use_container_width=True)
    
    # Seleccionar muestras finales
    st.markdown("#### Selecciona las muestras que corresponden a las de control:")
    st.info("✅ Deberían coincidir con los IDs de las muestras iniciales")
    
    # Incluir Recipe en el selector si existe
    df_final_display = df_final[['ID', 'Note']].copy()
    
    if 'Recipe' in df_final.columns:
        df_final_display['Recipe'] = df_final['Recipe']
    
    df_final_display.insert(0, 'Usar como Control Final', False)
    
    # Deshabilitar Recipe si existe
    disabled_cols = ['ID', 'Note', 'Recipe'] if 'Recipe' in df_final.columns else ['ID', 'Note']
    
    edited_final = st.data_editor(
        df_final_display,
        hide_index=False,
        use_container_width=True,
        disabled=disabled_cols,
        key='control_final_selector'
    )
    
    selected_final_indices = edited_final[edited_final['Usar como Control Final'] == True].index.tolist()
    
    if len(selected_final_indices) == 0:
        st.warning("⚠️ No has seleccionado ninguna muestra de control final")
        return
    
    df_final_selected = df_final.loc[selected_final_indices].copy()
    final_sample_ids = df_final_selected['ID'].tolist()
    
    st.success(f"✅ {len(df_final_selected)} muestras de control finales seleccionadas")
    
    # Mostrar recetas finales si existen
    if 'Recipe' in df_final_selected.columns:
        recipes_final = df_final_selected['Recipe'].dropna().unique()
        if len(recipes_final) > 0:
            recipes_str = ', '.join([str(r) for r in recipes_final])
            st.info(f"📋 **Recetas detectadas en muestras finales:** {recipes_str}")
    
    # Encontrar IDs comunes
    common_ids = list(set(initial_sample_ids) & set(final_sample_ids))
    
    if len(common_ids) == 0:
        st.error(MESSAGES['error_no_common_control'])
        st.write("**IDs iniciales:**", initial_sample_ids)
        st.write("**IDs finales:**", final_sample_ids)
        return
    
    st.success(f"✅ {len(common_ids)} muestras comunes encontradas: {', '.join(common_ids)}")
    
    # ⭐ NUEVO: Validar que las recetas coincidan para los IDs comunes
    if 'Recipe' in df_initial.columns and 'Recipe' in df_final_selected.columns:
        # Filtrar solo IDs comunes para la comparación
        df_initial_common = df_initial[df_initial['ID'].isin(common_ids)].copy()
        df_final_common = df_final_selected[df_final_selected['ID'].isin(common_ids)].copy()
        
        # Normalizar IDs
        df_initial_common['ID'] = df_initial_common['ID'].astype(str).str.strip()
        df_final_common['ID'] = df_final_common['ID'].astype(str).str.strip()
        
        # Crear diccionarios de Recipe por ID
        recipe_initial = df_initial_common.set_index('ID')['Recipe'].to_dict()
        recipe_final = df_final_common.set_index('ID')['Recipe'].to_dict()
        
        # Verificar coincidencias
        mismatches = []
        for sample_id in common_ids:
            recipe_ini = recipe_initial.get(sample_id)
            recipe_fin = recipe_final.get(sample_id)
            
            # Comparar solo si ambos tienen Recipe (no son NaN)
            if pd.notna(recipe_ini) and pd.notna(recipe_fin):
                if str(recipe_ini).strip() != str(recipe_fin).strip():
                    mismatches.append({
                        'ID': sample_id,
                        'Recipe_Inicial': recipe_ini,
                        'Recipe_Final': recipe_fin
                    })
        
        # Mostrar advertencia si hay diferencias
        if mismatches:
            st.error("❌ **ERROR CRÍTICO: Recetas no coinciden**")
            st.warning("""
            ⚠️ Las siguientes muestras tienen diferentes recetas (calibraciones) entre las mediciones 
            inicial y final. Esto invalida la comparación porque las diferencias observadas pueden 
            deberse al cambio de calibración y no al ajuste de baseline.
            """)
            
            df_mismatches = pd.DataFrame(mismatches)
            st.dataframe(df_mismatches, use_container_width=True)
            
            st.error("""
            **Acciones recomendadas:**
            1. Verifica que las muestras finales se midieron con la MISMA receta que las iniciales
            2. Si cambiaste de receta, debes medir nuevamente las muestras de control con la receta original
            3. El ajuste de baseline NO cambia la receta/calibración a usar
            """)
            
            # Preguntar si quiere continuar de todos modos
            st.markdown("---")
            if st.checkbox("⚠️ Entiendo el riesgo y quiero continuar de todos modos", key="force_continue"):
                st.warning("Continuando con la validación a pesar de las diferencias en recetas...")
            else:
                st.info("Proceso detenido. Corrige las recetas antes de continuar.")
                return  # ← Detiene el proceso aquí
        else:
            st.success("✅ Recetas coinciden correctamente entre mediciones iniciales y finales")
    
    # Guardar muestras finales
    spectral_cols_final = get_spectral_columns(df_final)
    save_control_samples_final(
        df=df_final_selected,
        spectral_cols=spectral_cols_final,
        sample_ids=final_sample_ids
    )
    
    # Filtrar solo IDs comunes
    df_initial_common = df_initial[df_initial['ID'].isin(common_ids)].copy()
    df_final_common = df_final_selected[df_final_selected['ID'].isin(common_ids)].copy()
    
    # Realizar análisis comparativo
    render_control_samples_analysis(
        df_initial_common,
        df_final_common,
        spectral_cols,
        spectral_cols_final,
        common_ids
    )

def render_control_samples_analysis(df_initial, df_final, spectral_cols_initial, 
                                    spectral_cols_final, common_ids):
    """
    ⭐ ACTUALIZADO: Renderiza el análisis comparativo de muestras de control.
    """
    # --- Normaliza IDs ---
    df_initial = df_initial.copy()
    df_final = df_final.copy()
    df_initial['ID'] = df_initial['ID'].astype(str).str.strip()
    df_final['ID']   = df_final['ID'].astype(str).str.strip()
    common_ids = [str(x).strip() for x in common_ids]

    st.markdown("---")
    st.markdown("### 📈 Análisis Comparativo de Muestras de Control")

    # ========== 1️⃣ COMPARACIÓN ESPECTRAL ==========
    st.markdown("#### 1️⃣ Comparación Espectral")

    # Verificar compatibilidad de columnas espectrales
    if len(spectral_cols_initial) != len(spectral_cols_final):
        st.warning(f"""
        ⚠️ Los archivos tienen diferente número de canales espectrales:
        - Inicial: {len(spectral_cols_initial)} canales
        - Final: {len(spectral_cols_final)} canales
        """)
        spectral_cols = spectral_cols_initial[:min(len(spectral_cols_initial), len(spectral_cols_final))]
    else:
        spectral_cols = spectral_cols_initial

    with st.expander("📊 Ver Comparación de Espectros", expanded=True):
        fig_spectra = plot_spectra_comparison(
            df_initial, df_final, spectral_cols, common_ids
        )
        st.plotly_chart(fig_spectra, use_container_width=True)

    # Métricas espectrales
    st.markdown("##### Métricas Espectrales")
    spectral_metrics = calculate_spectral_metrics(
        df_initial, df_final, spectral_cols, common_ids
    )
    render_spectral_metrics_table(spectral_metrics)

    # ========== 2️⃣ COMPARACIÓN DE PREDICCIONES ==========
    st.markdown("---")
    st.markdown("#### 2️⃣ Comparación de Predicciones")

    # Extraer predicciones (acepta Result o Results en extract_predictions_from_results)
    predictions_initial = extract_predictions_from_results(df_initial)
    predictions_final   = extract_predictions_from_results(df_final)

    # DEBUG útil si algo falla
    if predictions_initial.empty or predictions_final.empty:
        st.warning("⚠️ No se pudieron extraer las predicciones de uno o ambos archivos")
        st.caption("Columnas df_initial: " + ", ".join(df_initial.columns.astype(str)))
        st.caption("Columnas df_final: " +   ", ".join(df_final.columns.astype(str)))
        st.write("df_initial HEAD:"); st.dataframe(df_initial.head())
        st.write("df_final HEAD:");   st.dataframe(df_final.head())
        return

    # Asegura IDs tipo str sin espacios
    predictions_initial['ID'] = predictions_initial['ID'].astype(str).str.strip()
    predictions_final['ID']   = predictions_final['ID'].astype(str).str.strip()

    # Parámetros ordenados Param1..ParamN
    params_initial = get_prediction_parameters(predictions_initial)
    params_final   = get_prediction_parameters(predictions_final)
    common_params  = [p for p in params_initial if p in params_final]
    if not common_params:
        st.warning("⚠️ No hay parámetros comunes (ParamN) entre inicial y final.")
        st.write("Params inicial:", params_initial)
        st.write("Params final:", params_final)
        return

    # ⭐ MODIFICADO: Pasar también df_initial y df_final para capturar Recipe
    comparison_df = compare_predictions(
        predictions_initial, 
        predictions_final, 
        common_ids,
        df_original_initial=df_initial,  # ← NUEVO
        df_original_final=df_final        # ← NUEVO
    )
    
    if comparison_df.empty:
        st.warning("⚠️ No hay datos de predicciones para comparar")
        st.write("IDs comunes:", common_ids)
        st.write("Predicciones iniciales (IDs + primeros params):")
        st.dataframe(predictions_initial[['ID'] + params_initial[:5]].head(), use_container_width=True)
        st.write("Predicciones finales (IDs + primeros params):")
        st.dataframe(predictions_final[['ID'] + params_final[:5]].head(), use_container_width=True)
        return

    st.success(f"✅ Parámetros detectados: {', '.join(common_params)}")

    # Gráfico de barras de predicciones
    with st.expander("📊 Ver Comparación de Predicciones", expanded=True):
        fig_pred = plot_predictions_comparison(comparison_df, common_params)
        if fig_pred:
            st.plotly_chart(fig_pred, use_container_width=True)

    # ⭐ MODIFICADO: Tabla de comparación detallada con expander y scroll horizontal
    with st.expander("📋 Ver Tabla de Comparación Detallada", expanded=False):
        st.markdown("##### Tabla de Comparación Detallada")
        render_predictions_comparison_table(comparison_df, common_params)

    # ========== CONCLUSIÓN ==========
    st.markdown("---")
    render_control_samples_conclusion(comparison_df, common_params)

    # Descargar resultados
    render_control_samples_download(comparison_df, spectral_metrics)

def render_spectral_metrics_table(spectral_metrics):
    """
    ⭐ NUEVA FUNCIÓN: Renderiza tabla con métricas espectrales.
    """
    metrics_data = []
    for sample_id, metrics in spectral_metrics.items():
        metrics_data.append({
            'Muestra': sample_id,
            'Diferencia Media': f"{metrics['mean_diff']:.6f}",
            'Desv. Estándar': f"{metrics['std_diff']:.6f}",
            'Dif. Máxima': f"{metrics['max_diff']:.6f}",
            'RMSE': f"{metrics['rmse']:.6f}",
            'Correlación': f"{metrics['correlation']:.4f}"
        })
    
    df_metrics = pd.DataFrame(metrics_data)
    st.dataframe(df_metrics, use_container_width=True)


def render_predictions_comparison_table(comparison_df, parameters):
    """
    ⭐ ACTUALIZADO: Renderiza tabla con comparación de predicciones incluyendo Recipe.
    Usa contenedor con scroll horizontal para tablas anchas.
    """
    display_data = []
    
    for _, row in comparison_df.iterrows():
        sample_id = row['ID']
        sample_data = {'Muestra': sample_id}
        
        # ⭐ NUEVO: Añadir Recipe si existe
        if 'Recipe' in row.index and pd.notna(row['Recipe']):
            sample_data['Receta'] = row['Recipe']
        
        for param in parameters:
            col_initial = f'{param}_initial'
            col_final = f'{param}_final'
            col_diff = f'{param}_diff'
            col_diff_pct = f'{param}_diff_pct'
            
            if all(col in row.index for col in [col_initial, col_final, col_diff, col_diff_pct]):
                initial_val = row[col_initial]
                final_val = row[col_final]
                diff_abs = row[col_diff]
                diff_pct = row[col_diff_pct]
                
                # Determinar estado
                status = get_prediction_status(diff_pct)
                status_icon = {'good': '🟢', 'warning': '🟡', 'bad': '🔴'}[status]
                
                sample_data[f'{param} Inicial'] = f"{initial_val:.2f}"
                sample_data[f'{param} Final'] = f"{final_val:.2f}"
                sample_data[f'{param} Δ'] = f"{diff_abs:+.2f}"
                sample_data[f'{param} Δ%'] = f"{diff_pct:+.2f}% {status_icon}" if not np.isnan(diff_pct) else "N/A"
        
        display_data.append(sample_data)
    
    df_display = pd.DataFrame(display_data)
    
    # ⭐ NUEVO: Reordenar columnas para que Recipe esté al inicio
    if 'Receta' in df_display.columns:
        cols = ['Muestra', 'Receta'] + [c for c in df_display.columns if c not in ['Muestra', 'Receta']]
        df_display = df_display[cols]
    
    # ⭐ NUEVO: Usar contenedor con altura fija para scroll horizontal
    st.dataframe(
        df_display, 
        use_container_width=True,
        height=400  # Altura fija con scroll vertical si hay muchas filas
    )

def render_control_samples_conclusion(comparison_df, parameters):
    """
    ⭐ ACTUALIZADO: Renderiza conclusión del análisis de muestras de control.
    Incluye información de recetas si está disponible.
    """
    st.markdown("### 🎯 Conclusión: Validación con Muestras de Control")
    
    # ⭐ NUEVO: Mostrar información de recetas si existe
    if 'Recipe' in comparison_df.columns:
        recipes = comparison_df['Recipe'].dropna().unique()
        if len(recipes) > 0:
            recipes_str = ', '.join([str(r) for r in recipes])
            st.info(f"📋 **Recetas analizadas:** {recipes_str}")
    
    # Analizar mejoras/empeoramientos
    good_count = 0
    warning_count = 0
    bad_count = 0
    
    for param in parameters:
        col_diff_pct = f'{param}_diff_pct'
        if col_diff_pct in comparison_df.columns:
            for diff_pct in comparison_df[col_diff_pct]:
                status = get_prediction_status(diff_pct)
                if status == 'good':
                    good_count += 1
                elif status == 'warning':
                    warning_count += 1
                else:
                    bad_count += 1
    
    total_comparisons = good_count + warning_count + bad_count
    
    if total_comparisons == 0:
        st.info("ℹ️ No hay suficientes datos para evaluar el impacto del ajuste")
        return
    
    # Porcentajes
    good_pct = (good_count / total_comparisons) * 100
    warning_pct = (warning_count / total_comparisons) * 100
    bad_pct = (bad_count / total_comparisons) * 100
    
    # Mostrar resumen
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("🟢 Excelente", f"{good_count}", f"{good_pct:.1f}%")
    
    with col2:
        st.metric("🟡 Aceptable", f"{warning_count}", f"{warning_pct:.1f}%")
    
    with col3:
        st.metric("🔴 Revisar", f"{bad_count}", f"{bad_pct:.1f}%")
    
    # Conclusión basada en resultados
    st.markdown("---")
    
    if good_pct >= 80:
        st.success(f"""
        ✅ **EXCELENTE: Ajuste muy exitoso**
        
        El {good_pct:.1f}% de las predicciones muestran reproducibilidad excelente (< 0.5% de variación).
        El ajuste de baseline ha mejorado significativamente la consistencia del equipo.
        """)
    elif good_pct + warning_pct >= 80:
        st.success(f"""
        ✅ **BUENO: Ajuste exitoso**
        
        El {good_pct + warning_pct:.1f}% de las predicciones están dentro de rangos aceptables.
        El ajuste de baseline funciona correctamente.
        """)
    elif good_pct + warning_pct >= 60:
        st.info(f"""
        ℹ️ **ACEPTABLE: Ajuste parcial**
        
        El {good_pct + warning_pct:.1f}% de las predicciones son aceptables, pero hay un {bad_pct:.1f}% 
        que requiere revisión.
        
        **Recomendaciones:**
        - Verifica las muestras con mayor variación
        - Considera repetir mediciones de las muestras problemáticas
        - Revisa las condiciones ambientales durante las mediciones
        """)
    else:
        st.warning(f"""
        ⚠️ **ATENCIÓN: Resultados inconsistentes**
        
        Solo el {good_pct + warning_pct:.1f}% de las predicciones son aceptables.
        
        **Acciones recomendadas:**
        1. Verifica que el baseline corregido se instaló correctamente
        2. Reinicia el equipo NIR completamente
        3. Revisa la estabilidad térmica del equipo
        4. Considera repetir el proceso de ajuste
        5. Verifica el estado de las lámparas y ópticas
        """)

def render_control_samples_download(comparison_df, spectral_metrics):
    """
    ⭐ NUEVA FUNCIÓN: Renderiza botones de descarga para resultados de control.
    """
    st.markdown("---")
    st.markdown("### 💾 Descargar Resultados")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Descargar comparación de predicciones
        csv_predictions = io.StringIO()
        comparison_df.to_csv(csv_predictions, index=False)
        
        st.download_button(
            "📥 Descargar Comparación de Predicciones (CSV)",
            data=csv_predictions.getvalue(),
            file_name=f"control_predictions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        # Descargar métricas espectrales
        metrics_data = []
        for sample_id, metrics in spectral_metrics.items():
            row = {'Muestra': sample_id}
            row.update(metrics)
            metrics_data.append(row)
        
        df_metrics = pd.DataFrame(metrics_data)
        csv_metrics = io.StringIO()
        df_metrics.to_csv(csv_metrics, index=False)
        
        st.download_button(
            "📥 Descargar Métricas Espectrales (CSV)",
            data=csv_metrics.getvalue(),
            file_name=f"control_spectral_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )


# ========== FUNCIONES ORIGINALES (sin cambios) ==========

def process_validation_files(ref_val_file, new_val_file, mean_diff_original):
    """
    Procesa los archivos de validacion (2 archivos separados).
    
    Args:
        ref_val_file: Archivo TSV de referencia
        new_val_file: Archivo TSV de nueva lampara
        mean_diff_original (np.array): Diferencia espectral original (antes de correccion)
    """
    # Marcar cambios sin guardar
    st.session_state.unsaved_changes = True
    
    # Cargar ambos archivos
    df_ref_val = load_tsv_file(ref_val_file)
    df_new_val = load_tsv_file(new_val_file)
    
    # Obtener columnas espectrales
    spectral_cols_ref = get_spectral_columns(df_ref_val)
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
    
    # Filtrar muestras (excluir WSTD)
    df_ref_val_kit = df_ref_val[df_ref_val["ID"].str.upper() != "WSTD"].copy()
    df_new_val_kit = df_new_val[df_new_val["ID"].str.upper() != "WSTD"].copy()
    
    if len(df_ref_val_kit) == 0:
        st.error("No se encontraron muestras validas en el archivo de REFERENCIA")
        return
    
    if len(df_new_val_kit) == 0:
        st.error("No se encontraron muestras validas en el archivo de NUEVA lampara")
        return
    
    # Obtener informacion basica
    sample_ids_ref = df_ref_val_kit["ID"].unique()
    sample_ids_new = df_new_val_kit["ID"].unique()
    
    # Mostrar informacion
    st.success("✅ Archivos de validacion cargados correctamente")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Archivo Referencia:**")
        st.write(f"- Mediciones: {len(df_ref_val_kit)}")
        st.write(f"- Muestras: {len(sample_ids_ref)}")
    
    with col2:
        st.markdown("**Archivo Nueva:**")
        st.write(f"- Mediciones: {len(df_new_val_kit)}")
        st.write(f"- Muestras: {len(sample_ids_new)}")
    
    # Agrupar mediciones por ID
    df_ref_val_grouped = df_ref_val_kit.groupby("ID")[spectral_cols].mean()
    df_new_val_grouped = df_new_val_kit.groupby("ID")[spectral_cols].mean()
    
    # Encontrar muestras comunes
    common_ids_val = find_common_samples(df_ref_val_grouped, df_new_val_grouped)
    
    if not validate_common_samples(common_ids_val):
        return
    
    # Filtrar solo muestras comunes
    df_ref_val_grouped = df_ref_val_grouped.loc[common_ids_val]
    df_new_val_grouped = df_new_val_grouped.loc[common_ids_val]
    
    st.success(f"✅ Muestras comunes encontradas: {len(common_ids_val)}")
    
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
            "Referencia", "Nueva",  # Nombres genericos
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
    
    # ⬇️ GUARDA before/after en sesión para el informe
    st.session_state.validation_stats = {
        'mean_diff_before': mean_diff_original,
        'mean_diff_after': mean_diff_after,
    }
    
    # Guardar datos de validacion en session_state para el informe
    st.session_state.validation_data = {
        'df_ref_val': df_ref_val,
        'df_new_val': df_new_val,
        'lamp_ref': 'Referencia',  # Nombre generico
        'lamp_new': 'Nueva',        # Nombre generico
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

def render_validation_report_section(mean_diff_before, mean_diff_after):
    
    """
    Renderiza la seccion de generacion de informe de validacion.
    """
    st.markdown("---")
    st.markdown("#### 📄 Generar Informe Completo de Validación")
    
    if st.button("📥 Generar Informe con Validación", use_container_width=True, type="primary"):
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
            st.success("✅ Informe de validación generado correctamente")
            
        except Exception as e:
            st.error(f"❌ Error al generar el informe: {str(e)}")
            import traceback
            st.error(traceback.format_exc())

def render_validation_report_entrypoint():
    """
    Muestra SIEMPRE el botón de informe.
    - Si hay validación (before/after + validation_data): usa generate_validation_report.
    - Si NO hay validación aún: usa generate_html_report (informe base sin sección de validación).
    """
    st.markdown("---")
    st.markdown("#### 📄 Generar Informe Completo de Validación")

    kit_data = st.session_state.kit_data
    baseline_data = st.session_state.baseline_data

    stats = st.session_state.get('validation_stats')
    valdata = st.session_state.get('validation_data')

    mean_diff_before = (stats or {}).get('mean_diff_before', kit_data['mean_diff'])
    mean_diff_after  = (stats or {}).get('mean_diff_after', None)

    if st.button("📥 Generar Informe", use_container_width=True, type="primary", key="btn_report_validation_global"):
        try:
            from core.spectral_processing import apply_baseline_correction
            ref_corrected = apply_baseline_correction(baseline_data['ref_spectrum'], kit_data['mean_diff'])
            origin = baseline_data['origin']

            # Ruta 1: informe completo con validación (si hay after + validation_data)
            if (mean_diff_after is not None) and (valdata is not None):
                from core.report_generator import generate_validation_report
                html_content = generate_validation_report(
                    kit_data,
                    baseline_data,
                    ref_corrected,
                    origin,
                    valdata,
                    mean_diff_before,
                    mean_diff_after
                )
            # Ruta 2: informe base sin validación
            else:
                from core.report_generator import generate_html_report
                html_content = generate_html_report(
                    kit_data,
                    baseline_data,
                    ref_corrected,
                    origin
                )

            client_data = st.session_state.client_data or {}
            filename = f"Informe_Validacion_{client_data.get('sensor_sn','sensor')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

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
            import traceback
            st.error(traceback.format_exc())