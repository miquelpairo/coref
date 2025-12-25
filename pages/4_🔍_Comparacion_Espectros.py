"""
Spectrum Comparison Tool
=========================
Aplicación para comparar múltiples espectros NIR y analizar sus diferencias.
Parte del ecosistema COREF de herramientas de calibración NIR.

Author: Miquel
Date: 2024
Version: 2.0 - Optimizada con modo White Reference
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import List
import sys
from pathlib import Path

# Añadir directorio raíz al path para imports
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Importar módulos de COREF
from core.file_handlers import load_tsv_file, get_spectral_columns
from core.spectrum_analysis import (
    validate_spectra_compatibility,
    calculate_statistics,
    calculate_residuals,
    calculate_correlation_matrix,
    calculate_rms_matrix
)
from core.plotly_utils import (
    create_overlay_plot,
    create_residuals_plot,
    create_rms_heatmap,
    create_correlation_heatmap
)
from auth import check_password
from buchi_streamlit_theme import apply_buchi_styles


# Aplicar estilos corporativos BUCHI
apply_buchi_styles()


# VERIFICACIÓN DE AUTENTICACIÓN
if not check_password():
    st.stop()


# ============================================================================
# INTERFAZ PRINCIPAL
# ============================================================================

def main():
    """Función principal de la aplicación."""
    
    st.title("📊 NIR Spectrum Comparison Tool")
    st.markdown("**Herramienta de comparación de espectros NIR - COREF Suite**")
    st.divider()
    
    # Sidebar (solo info)
    with st.sidebar:
        st.header("ℹ️ Información")
        st.markdown("""
        **Versión:** 2.0  
        **Parte de:** COREF Suite
        
        ### Características:
        - Overlay de espectros
        - Análisis de residuales
        - Estadísticas completas
        - Matriz RMS
        - Modo White Reference
        """)
    
    # Área principal - File uploader
    st.subheader("📁 Cargar Archivos")
    
    uploaded_files = st.file_uploader(
        "Selecciona archivos TSV",
        type=['tsv'],
        accept_multiple_files=True,
        help="Sube 1-10 archivos TSV. Puedes comparar espectros del mismo archivo o de varios."
    )
    
    if uploaded_files:
        n_files = len(uploaded_files)
        if n_files > 10:
            st.error(f"⚠️ {n_files} archivos. Máximo 10.")
            uploaded_files = uploaded_files[:10]
        else:
            st.success(f"✅ {n_files} archivo(s) cargado(s)")
    
    st.divider()
    
    if not uploaded_files:
        st.info("👆 Sube al menos 1 archivo TSV para comenzar")
        st.markdown("""
        ### 🎯 Funcionalidades:
        - **Overlay de espectros**: Visualiza todos los espectros simultáneamente
        - **Análisis de residuales**: Compara contra cualquier referencia
        - **Estadísticas**: Métricas clave por espectro
        - **Matriz RMS**: Cuantifica variabilidad entre pares
        - **Modo White Reference**: Umbrales estrictos para referencias blancas
        - **Selección de filas**: Elige qué mediciones comparar
        """)
        return
    
    # Cargar y procesar archivos
    with st.spinner("Cargando espectros..."):
        all_data = []
        
        for uploaded_file in uploaded_files:
            try:
                df = load_tsv_file(uploaded_file)
                spectral_cols = get_spectral_columns(df)
                all_data.append((df, spectral_cols, uploaded_file.name))
            except Exception as e:
                st.error(f"Error al cargar {uploaded_file.name}: {str(e)}")
                return
        
        if not all_data:
            st.error("❌ No se pudieron cargar espectros válidos")
            return
    
    # Mostrar selector de filas para cada archivo
    st.markdown("### 📋 Selección de Mediciones")
    st.info("Marca las filas que quieres incluir en la comparación de cada archivo")
    
    selected_spectra = []
    spectrum_labels = []
    
    for idx, (df, spectral_cols, filename) in enumerate(all_data):
        with st.expander(f"**{filename}** ({len(df)} filas disponibles)", expanded=(idx==0)):
            
            col_search, col_group = st.columns([3, 1])
            
            with col_search:
                search_term = st.text_input(
                    "🔍 Filtrar tabla (ID o Note):",
                    key=f'search_{idx}',
                    placeholder="Escribe para filtrar..."
                )
            
            with col_group:
                group_by_sample = st.checkbox(
                    "📊 Agrupar réplicas",
                    key=f'group_{idx}',
                    help="Agrupa y promedia filas con mismo ID y Note"
                )
            
            # Aplicar filtro
            df_filtered = df.copy()
            if search_term:
                mask = (
                    df['ID'].astype(str).str.contains(search_term, case=False, na=False) |
                    df['Note'].astype(str).str.contains(search_term, case=False, na=False)
                )
                df_filtered = df[mask].copy()
            
            # Aplicar agrupamiento si está activado
            if group_by_sample:
                df_filtered_numeric = df_filtered.copy()
                df_filtered_numeric[spectral_cols] = df_filtered_numeric[spectral_cols].apply(pd.to_numeric, errors='coerce')
                
                df_aggregated = df_filtered_numeric.groupby(['ID', 'Note'], as_index=False).agg({
                    **{col: 'mean' for col in spectral_cols}
                })
                
                replica_counts = df_filtered.groupby(['ID', 'Note']).size().reset_index(name='N_replicas')
                df_aggregated = df_aggregated.merge(replica_counts, on=['ID', 'Note'], how='left')
                df_aggregated['Group_Key'] = df_aggregated['ID'].astype(str) + '|||' + df_aggregated['Note'].astype(str)
                
                df_display = df_aggregated[['ID', 'Note', 'N_replicas', 'Group_Key']].copy()
                df_display.insert(0, 'Grupo', range(len(df_display)))
                
                st.caption(f"Mostrando {len(df_aggregated)} grupos (de {len(df_filtered)} filas)")
                
                if f'df_grouped_{idx}' not in st.session_state or st.session_state.get(f'needs_refresh_{idx}', False):
                    st.session_state[f'df_grouped_{idx}'] = df_aggregated
                    st.session_state[f'needs_refresh_{idx}'] = False
            else:
                df_display = df_filtered[['ID', 'Note']].copy()
                df_display.insert(0, 'Fila', df_display.index)
                
                if search_term:
                    st.caption(f"Mostrando {len(df_filtered)} de {len(df)} filas")
            
            # Botones de control
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                select_all = st.button("✅ Seleccionar todo", key=f'select_all_{idx}', use_container_width=True)
            with col2:
                deselect_all = st.button("❌ Deseleccionar todo", key=f'deselect_all_{idx}', use_container_width=True)
            with col3:
                invert_sel = st.button("🔄 Invertir", key=f'invert_{idx}', use_container_width=True)
            with col4:
                confirm = st.button("✔️ Confirmar", key=f'confirm_{idx}', type="primary", use_container_width=True)
            with col5:
                reset = st.button("🗑️ Limpiar", key=f'reset_{idx}', use_container_width=True, help="Resetear selección")
            
            # Procesar reset
            if reset:
                keys_to_delete = [
                    f'confirmed_{idx}', f'grouped_{idx}', f'confirmed_group_keys_{idx}',
                    f'confirmed_indices_{idx}', f'df_grouped_{idx}', f'needs_refresh_{idx}'
                ]
                for key in keys_to_delete:
                    if key in st.session_state:
                        del st.session_state[key]
                st.success("🗑️ Selección limpiada")
                st.rerun()
            
            # Aplicar acciones de botones
            default_selection = True if select_all else False
            df_display.insert(0, 'Seleccionar', default_selection)
            
            # Editor de datos
            if group_by_sample:
                disabled_cols = ['Grupo', 'ID', 'Note', 'N_replicas', 'Group_Key']
                column_config = {
                    "Grupo": st.column_config.NumberColumn("Grupo", width="small"),
                    "N_replicas": st.column_config.NumberColumn("Réplicas", width="small"),
                    "Group_Key": None
                }
            else:
                disabled_cols = ['Fila', 'ID', 'Note']
                column_config = {"Fila": st.column_config.NumberColumn("Fila", width="small")}
            
            edited_df = st.data_editor(
                df_display,
                hide_index=True,
                use_container_width=True,
                disabled=disabled_cols,
                key=f'selector_{idx}',
                column_config=column_config
            )
            
            if invert_sel:
                edited_df['Seleccionar'] = ~edited_df['Seleccionar']
            
            selected_rows = edited_df[edited_df['Seleccionar'] == True]
            
            if group_by_sample:
                selected_group_keys = selected_rows['Group_Key'].tolist()
                n_selected = len(selected_group_keys)
            else:
                original_indices = selected_rows['Fila'].tolist()
                n_selected = len(original_indices)
            
            if n_selected > 0:
                st.info(f"📝 {n_selected} {'grupos' if group_by_sample else 'filas'} marcados (presiona ✔️ Confirmar)")
            
            # Confirmar selección
            if confirm and n_selected > 0:
                st.session_state[f'confirmed_{idx}'] = True
                st.session_state[f'grouped_{idx}'] = group_by_sample
                
                if group_by_sample:
                    st.session_state[f'confirmed_group_keys_{idx}'] = selected_group_keys
                else:
                    st.session_state[f'confirmed_indices_{idx}'] = original_indices
                
                st.success(f"✅ {n_selected} {'grupos' if group_by_sample else 'filas'} confirmados")
            
            # Usar datos confirmados
            if st.session_state.get(f'confirmed_{idx}', False):
                is_grouped = st.session_state.get(f'grouped_{idx}', False)
                
                if is_grouped:
                    confirmed_group_keys = st.session_state.get(f'confirmed_group_keys_{idx}', [])
                    
                    if len(confirmed_group_keys) > 0:
                        st.success(f"✔️ Selección activa: {len(confirmed_group_keys)} grupos")
                        
                        df_grouped = st.session_state.get(f'df_grouped_{idx}')
                        
                        if df_grouped is not None:
                            df_selected_groups = df_grouped[df_grouped['Group_Key'].isin(confirmed_group_keys)]
                            
                            for _, row in df_selected_groups.iterrows():
                                spectrum = row[spectral_cols].values
                                label = f"{row['ID']} | {row['Note']} | Promedio ({int(row['N_replicas'])} rép.)"
                                selected_spectra.append(spectrum)
                                spectrum_labels.append(label)
                else:
                    confirmed_indices = st.session_state.get(f'confirmed_indices_{idx}', [])
                    
                    if len(confirmed_indices) > 0:
                        st.success(f"✔️ Selección activa: {len(confirmed_indices)} filas")
                        
                        df_selected = df.loc[confirmed_indices].copy()
                        df_selected[spectral_cols] = df_selected[spectral_cols].apply(pd.to_numeric, errors="coerce")
                        
                        for row_idx in confirmed_indices:
                            row = df_selected.loc[row_idx]
                            spectrum = row[spectral_cols].values
                            label = f"{row['ID']} | {row['Note']} | Fila {row_idx}"
                            selected_spectra.append(spectrum)
                            spectrum_labels.append(label)
    
    # Validar que haya al menos 2 espectros
    if len(selected_spectra) < 2:
        st.warning("⚠️ Selecciona al menos 2 mediciones en total para hacer la comparación")
        return
    
    # Validar compatibilidad
    is_valid, validation_msg = validate_spectra_compatibility(selected_spectra)
    
    if not is_valid:
        st.error(validation_msg)
        return
    else:
        st.success(validation_msg)
    
    st.divider()
    
    # ⭐ CHECKBOX MODO WHITE REFERENCE
    col1, col2 = st.columns([3, 1])
    with col1:
        white_ref_mode = st.checkbox(
            "🔬 Modo White Reference",
            value=False,
            help="Activa umbrales estrictos (RMS < 0.005) y oculta correlación"
        )
    with col2:
        if white_ref_mode:
            st.info("📏 Umbrales: 0.005 / 0.010 AU")
    
    st.divider()
    
    # Crear tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Overlay", 
        "📉 Residuales", 
        "📊 Estadísticas",
        "🔥 Matriz RMS"
    ])
    
    # Estado de visibilidad
    if 'visible_spectra' not in st.session_state or len(st.session_state.visible_spectra) != len(selected_spectra):
        st.session_state.visible_spectra = [True] * len(selected_spectra)
    
    # TAB 1: Overlay
    with tab1:
        st.subheader("Comparación de Espectros")
        
        with st.expander("🔧 Controlar Visibilidad", expanded=False):
            cols = st.columns(min(3, len(selected_spectra)))
            for i, label in enumerate(spectrum_labels):
                col_idx = i % len(cols)
                with cols[col_idx]:
                    st.session_state.visible_spectra[i] = st.checkbox(
                        label, 
                        value=st.session_state.visible_spectra[i],
                        key=f"vis_{i}"
                    )
        
        fig_overlay = create_overlay_plot(selected_spectra, spectrum_labels, st.session_state.visible_spectra)
        st.plotly_chart(fig_overlay, use_container_width=True)
    
    # TAB 2: Residuales
    with tab2:
        st.subheader("Análisis de Residuales")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            reference_idx = st.selectbox(
                "Selecciona espectro de referencia:",
                range(len(spectrum_labels)),
                format_func=lambda x: f"{x+1}. {spectrum_labels[x]}"
            )
        with col2:
            st.metric("Referencia #", reference_idx + 1)
        
        residuals = calculate_residuals(selected_spectra, reference_idx)
        fig_residuals = create_residuals_plot(
            selected_spectra, 
            spectrum_labels, 
            reference_idx,
            st.session_state.visible_spectra,
            residuals
        )
        st.plotly_chart(fig_residuals, use_container_width=True)
        
        with st.expander("📊 Estadísticas de Residuales"):
            residual_stats = []
            for i, (residual, label) in enumerate(zip(residuals, spectrum_labels)):
                if i != reference_idx:
                    residual_stats.append({
                        'Espectro': label,
                        'RMS': f"{np.sqrt(np.mean(residual**2)):.6f}",
                        'Max |Δ|': f"{np.abs(residual).max():.6f}",
                        'Media Δ': f"{np.mean(residual):.6f}",
                        'Desv. Est.': f"{np.std(residual):.6f}"
                    })
            
            if residual_stats:
                st.dataframe(pd.DataFrame(residual_stats), use_container_width=True, hide_index=True)
    
    # TAB 3: Estadísticas
    with tab3:
        st.subheader("Estadísticas Espectrales")
        
        num_channels = len(selected_spectra[0])
        stats_df = calculate_statistics(selected_spectra, spectrum_labels, num_channels)
        
        st.dataframe(stats_df, use_container_width=True, hide_index=True)
        
        csv = stats_df.to_csv(index=False)
        st.download_button(
            label="📥 Descargar CSV",
            data=csv,
            file_name="estadisticas_espectrales.csv",
            mime="text/csv"
        )
    
    # TAB 4: Matriz RMS
    with tab4:
        st.subheader("Matriz de Diferencias RMS")
        
        if white_ref_mode:
            st.info("📏 **Escala absoluta para white references**: Verde < 0.005 AU | Amarillo < 0.01 AU | Rojo ≥ 0.01 AU")
        else:
            st.info("📊 **Escala relativa**: Colores basados en valores mín/máx de los espectros comparados")
        
        fig_heatmap = create_rms_heatmap(selected_spectra, spectrum_labels, absolute_scale=white_ref_mode)
        st.plotly_chart(fig_heatmap, use_container_width=True)
        
        # Análisis de similitud
        with st.expander("🔍 Análisis de Similitud"):
            rms_matrix = calculate_rms_matrix(selected_spectra)
            n_spectra = len(selected_spectra)
            rms_values = []
            
            for i in range(n_spectra):
                for j in range(i+1, n_spectra):
                    rms = rms_matrix[i, j]
                    max_diff = np.abs(selected_spectra[i] - selected_spectra[j]).max()
                    
                    # Evaluar según modo
                    if white_ref_mode:
                        if rms < 0.002 and max_diff < 0.005:
                            evaluacion = "✅ Excelente"
                        elif rms < 0.005 and max_diff < 0.01:
                            evaluacion = "✓ Bueno"
                        elif rms < 0.01 and max_diff < 0.02:
                            evaluacion = "⚠️ Aceptable"
                        else:
                            evaluacion = "❌ Revisar"
                        
                        rms_values.append({
                            'Espectro A': spectrum_labels[i],
                            'Espectro B': spectrum_labels[j],
                            'RMS': f"{rms:.6f}",
                            'Max Diff': f"{max_diff:.6f}",
                            'Evaluación': evaluacion
                        })
                    else:
                        rms_values.append({
                            'Espectro A': spectrum_labels[i],
                            'Espectro B': spectrum_labels[j],
                            'RMS': f"{rms:.6f}"
                        })
            
            rms_df = pd.DataFrame(rms_values)
            rms_df = rms_df.sort_values('RMS')
            
            st.markdown("**Pares más similares:**")
            st.dataframe(rms_df.head(5), use_container_width=True, hide_index=True)
            
            if white_ref_mode:
                problem_pairs = rms_df[rms_df['Evaluación'].str.contains('❌|⚠️')]
                if len(problem_pairs) > 0:
                    st.markdown("**Pares que requieren atención:**")
                    st.dataframe(problem_pairs, use_container_width=True, hide_index=True)
                else:
                    st.success("✅ Todas las comparaciones están en rango excelente/bueno")
        
        # Correlación (solo si NO es modo White Reference)
        if not white_ref_mode:
            st.divider()
            st.subheader("Matriz de Correlación Espectral")
            st.markdown("Valores más cercanos a 1.0 indican mayor similitud")
            
            corr_matrix = calculate_correlation_matrix(selected_spectra, spectrum_labels)
            fig_corr = create_correlation_heatmap(corr_matrix, spectrum_labels)
            
            st.plotly_chart(fig_corr, use_container_width=True)


if __name__ == "__main__":
    main()