"""
Spectrum Comparison Tool
=========================
Aplicación para comparar múltiples espectros NIR y analizar sus diferencias.
Parte del ecosistema COREF de herramientas de calibración NIR.

Author: Miquel
Date: 2024
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Tuple
import sys
from pathlib import Path
from buchi_streamlit_theme import apply_buchi_styles

# Añadir directorio raíz al path para imports
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))


# Importar módulos de COREF
from core.file_handlers import load_tsv_file, get_spectral_columns
from auth import check_password  # ← AÑADIR ESTO


# Aplicar estilos corporativos Buchi
apply_buchi_styles()

# Corregir estilos del sidebar para mejor contraste
st.markdown("""
<style>
    /* Sidebar general */
    [data-testid="stSidebar"] {
        background-color: #2c5f3f;
    }
    
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    
    /* Headers y títulos */
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: white !important;
    }
    
    /* Labels - completamente invisibles, solo texto blanco */
    [data-testid="stSidebar"] label {
        color: white !important;
        font-weight: 500 !important;
        font-size: 14px !important;
        margin-bottom: 8px !important;
        display: block !important;
        background: none !important;
        border: none !important;
        padding: 0 !important;
        box-shadow: none !important;
    }
    
    /* CRÍTICO: Eliminar borde verde de label de file uploader */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] > label,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] label {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
    }
    
    /* File uploader - contenedor principal */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] {
        width: 100% !important;
        margin-bottom: 20px !important;
    }
    
    /* Área de drop - diseño limpio y compacto */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section {
        background-color: rgba(255, 255, 255, 0.1) !important;
        border: 2px dashed rgba(255, 255, 255, 0.3) !important;
        border-radius: 8px !important;
        padding: 20px !important;
        text-align: center !important;
        width: 100% !important;
        box-sizing: border-box !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section:hover {
        border-color: rgba(255, 255, 255, 0.5) !important;
        background-color: rgba(255, 255, 255, 0.15) !important;
    }
    
    /* Texto "Drag and drop" */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] small {
        color: rgba(255, 255, 255, 0.8) !important;
        font-size: 13px !important;
    }
    
    /* Botón "Browse files" - Verde Buchi */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button[kind="secondary"] {
        background-color: #7cb342 !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 8px 20px !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        margin-top: 10px !important;
        cursor: pointer !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button[kind="secondary"]:hover {
        background-color: #689f38 !important;
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(0,0,0,0.2) !important;
    }
    
    /* Archivo cargado - estilo badge */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid="stMarkdownContainer"] {
        background-color: rgba(124, 179, 66, 0.2) !important;
        border: 1px solid #7cb342 !important;
        border-radius: 6px !important;
        padding: 10px 12px !important;
        margin-top: 10px !important;
        color: white !important;
        font-size: 13px !important;
    }
    
    /* Botón X para eliminar - más visible */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button[kind="icon"] {
        color: #ff5252 !important;
        background-color: rgba(255, 82, 82, 0.1) !important;
        border-radius: 4px !important;
        padding: 4px !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button[kind="icon"]:hover {
        background-color: rgba(255, 82, 82, 0.2) !important;
        color: #ff1744 !important;
    }
    
    /* Dividers */
    [data-testid="stSidebar"] hr {
        border-color: rgba(255, 255, 255, 0.2) !important;
        margin: 20px 0 !important;
    }
    
    /* Expander */
    [data-testid="stSidebar"] [data-testid="stExpander"] {
        background-color: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stExpander"] summary {
        color: white !important;
    }
    
    /* Info boxes */
    [data-testid="stSidebar"] .stAlert {
        background-color: rgba(124, 179, 66, 0.15) !important;
        border: 1px solid rgba(124, 179, 66, 0.3) !important;
        border-radius: 8px !important;
        color: white !important;
    }
    
    /* Inputs - FONDO BLANCO con texto oscuro */
    [data-testid="stSidebar"] input[type="number"],
    [data-testid="stSidebar"] input[type="text"] {
        background-color: white !important;
        color: #333333 !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        border-radius: 6px !important;
        padding: 8px 12px !important;
    }
    
    [data-testid="stSidebar"] input[type="number"]:focus,
    [data-testid="stSidebar"] input[type="text"]:focus {
        border-color: #7cb342 !important;
        box-shadow: 0 0 0 1px #7cb342 !important;
    }
    
    /* Selects */
    [data-testid="stSidebar"] select {
        background-color: white !important;
        color: #333333 !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        border-radius: 6px !important;
    }
    
    /* Number input - botones +/- GRISES OSCUROS sobre blanco */
    [data-testid="stSidebar"] button[kind="icon"] svg {
        color: #333333 !important;
        fill: #333333 !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stNumberInput"] button {
        background-color: #f0f0f0 !important;
        color: #333333 !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stNumberInput"] button:hover {
        background-color: #e0e0e0 !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stNumberInput"] button svg {
        color: #333333 !important;
        fill: #333333 !important;
    }
</style>
""", unsafe_allow_html=True)


# VERIFICACIÓN DE AUTENTICACIÓN
if not check_password():
    st.stop()

# ============================================================================
# FUNCIONES DE PROCESAMIENTO
# ============================================================================

def validate_spectra_compatibility(spectra_list: List[np.ndarray]) -> Tuple[bool, str]:
    """Valida que todos los espectros tengan el mismo número de píxeles."""
    if len(spectra_list) < 2:
        return False, "Se necesitan al menos 2 espectros para comparar"
    
    pixel_counts = [len(spec) for spec in spectra_list]
    
    if len(set(pixel_counts)) > 1:
        msg = "⚠️ Los espectros tienen diferente número de píxeles:\n"
        for i, count in enumerate(pixel_counts, 1):
            msg += f"  - Espectro {i}: {count} píxeles\n"
        return False, msg
    
    return True, f"✅ {len(spectra_list)} espectros compatibles ({pixel_counts[0]} píxeles cada uno)"


def calculate_statistics(spectra_list: List[np.ndarray], names: List[str], 
                         num_channels: int) -> pd.DataFrame:
    """Calcula estadísticas descriptivas para cada espectro."""
    stats = []
    
    for name, spectrum in zip(names, spectra_list):
        stats.append({
            'Espectro': name,
            'Canales': num_channels,
            'Min': f"{spectrum.min():.6f}",
            'Max': f"{spectrum.max():.6f}",
            'Media': f"{spectrum.mean():.6f}",
            'Desv. Est.': f"{spectrum.std():.6f}",
            'Rango': f"{spectrum.max() - spectrum.min():.6f}"
        })
    
    return pd.DataFrame(stats)


def calculate_residuals(spectra_list: List[np.ndarray], reference_idx: int) -> List[np.ndarray]:
    """Calcula residuales de todos los espectros respecto a uno de referencia."""
    reference = spectra_list[reference_idx]
    residuals = []
    
    for i, spectrum in enumerate(spectra_list):
        if i == reference_idx:
            residuals.append(np.zeros_like(reference))
        else:
            residuals.append(spectrum - reference)
    
    return residuals


# ============================================================================
# FUNCIONES DE VISUALIZACIÓN
# ============================================================================

def create_overlay_plot(spectra_list: List[np.ndarray], names: List[str], 
                       visible_spectra: List[bool]) -> go.Figure:
    """Crea gráfico con todos los espectros superpuestos."""
    colors = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
    ]
    
    fig = go.Figure()
    channels = list(range(1, len(spectra_list[0]) + 1))
    
    for i, (spectrum, name, visible) in enumerate(zip(spectra_list, names, visible_spectra)):
        color = colors[i % len(colors)]
        
        fig.add_trace(go.Scatter(
            x=channels,
            y=spectrum,
            mode='lines',
            name=name,
            line=dict(color=color, width=2),
            visible=True if visible else 'legendonly',
            hovertemplate='<b>%{fullData.name}</b><br>' +
                         'Canal: %{x}<br>' +
                         'Valor: %{y:.6f}<br>' +
                         '<extra></extra>'
        ))
    
    fig.update_layout(
        title={
            'text': 'Comparación de Espectros',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20}
        },
        xaxis_title='Canal espectral',
        yaxis_title='Absorbancia',
        hovermode='closest',
        template='plotly_white',
        height=600,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.15,
            xanchor="center",
            x=0.5
        )
    )
    
    return fig


def create_residuals_plot(spectra_list: List[np.ndarray], names: List[str], 
                         reference_idx: int, visible_spectra: List[bool]) -> go.Figure:
    """Crea gráfico de residuales respecto a un espectro de referencia."""
    colors = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
    ]
    
    residuals = calculate_residuals(spectra_list, reference_idx)
    channels = list(range(1, len(spectra_list[0]) + 1))
    
    fig = go.Figure()
    
    for i, (residual, name, visible) in enumerate(zip(residuals, names, visible_spectra)):
        if i == reference_idx:
            continue
        
        color = colors[i % len(colors)]
        
        fig.add_trace(go.Scatter(
            x=channels,
            y=residual,
            mode='lines',
            name=f"{name} - {names[reference_idx]}",
            line=dict(color=color, width=2),
            visible=True if visible else 'legendonly',
            hovertemplate='<b>%{fullData.name}</b><br>' +
                         'Canal: %{x}<br>' +
                         'Δ: %{y:.6f}<br>' +
                         '<extra></extra>'
        ))
    
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    fig.update_layout(
        title={
            'text': f'Residuales vs. Referencia: {names[reference_idx]}',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20}
        },
        xaxis_title='Canal espectral',
        yaxis_title='Residual',
        hovermode='closest',
        template='plotly_white',
        height=600,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.15,
            xanchor="center",
            x=0.5
        )
    )
    
    return fig


def create_residuals_heatmap(spectra_list: List[np.ndarray], names: List[str]) -> go.Figure:
    """Crea un mapa de calor mostrando las diferencias RMS entre todos los pares."""
    n_spectra = len(spectra_list)
    rms_matrix = np.zeros((n_spectra, n_spectra))
    
    for i in range(n_spectra):
        for j in range(n_spectra):
            if i == j:
                rms_matrix[i, j] = 0
            else:
                diff = spectra_list[i] - spectra_list[j]
                rms_matrix[i, j] = np.sqrt(np.mean(diff**2))
    
    fig = go.Figure(data=go.Heatmap(
        z=rms_matrix,
        x=names,
        y=names,
        colorscale='RdYlGn_r',
        text=np.round(rms_matrix, 6),
        texttemplate='%{text}',
        textfont={"size": 10},
        colorbar=dict(title="RMS")
    ))
    
    fig.update_layout(
        title='Matriz de Diferencias RMS',
        height=max(400, 50 * n_spectra),
        template='plotly_white'
    )
    
    return fig

def calculate_correlation_matrix(spectra_list: List[np.ndarray], names: List[str]) -> np.ndarray:
    """Calcula matriz de correlación entre todos los espectros."""
    n_spectra = len(spectra_list)
    corr_matrix = np.ones((n_spectra, n_spectra))  # Inicializar con 1s
    
    for i in range(n_spectra):
        for j in range(i+1, n_spectra):  # Solo calcular triángulo superior
            try:
                # Validar, aplanar y CONVERTIR A FLOAT
                spec_i = np.asarray(spectra_list[i], dtype=np.float64).flatten()
                spec_j = np.asarray(spectra_list[j], dtype=np.float64).flatten()
                
                # Validaciones
                if len(spec_i) != len(spec_j) or len(spec_i) < 2:
                    corr_matrix[i, j] = np.nan
                    corr_matrix[j, i] = np.nan
                    continue
                
                if np.any(~np.isfinite(spec_i)) or np.any(~np.isfinite(spec_j)):
                    corr_matrix[i, j] = np.nan
                    corr_matrix[j, i] = np.nan
                    continue
                
                # Normalizar
                spec_i_norm = (spec_i - np.mean(spec_i)) / (np.std(spec_i) + 1e-10)
                spec_j_norm = (spec_j - np.mean(spec_j)) / (np.std(spec_j) + 1e-10)
                
                # Correlación manual
                corr = np.sum(spec_i_norm * spec_j_norm) / len(spec_i_norm)
                
                if np.isfinite(corr):
                    corr_matrix[i, j] = corr
                    corr_matrix[j, i] = corr
                else:
                    corr_matrix[i, j] = np.nan
                    corr_matrix[j, i] = np.nan
                    
            except Exception as e:
                print(f"Error calculando correlación ({i},{j}): {e}")
                corr_matrix[i, j] = np.nan
                corr_matrix[j, i] = np.nan
    
    return corr_matrix


# ============================================================================
# INTERFAZ PRINCIPAL
# ============================================================================

def main():
    """Función principal de la aplicación."""
    
    st.title("📊 NIR Spectrum Comparison Tool")
    st.markdown("**Herramienta de comparación de espectros NIR - COREF Suite**")
    st.divider()
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuración")
        
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
        st.markdown("""
        **Versión:** 1.0  
        **Parte de:** Baseline correction tool  
        """)
    
    # Área principal
    if not uploaded_files:
        st.info("👈 Sube al menos 1 archivo TSV para comenzar")
        st.markdown("""
        ### Características:
        - **Overlay de espectros**: Visualiza todos los espectros simultáneamente
        - **Análisis de residuales**: Compara contra cualquier referencia
        - **Estadísticas**: Métricas clave por espectro
        - **Matriz RMS**: Cuantifica variabilidad entre pares
        - **Selección de filas**: Elige qué mediciones comparar (incluso del mismo archivo)
        """)
        return
    
    # Cargar y procesar archivos
    with st.spinner("Cargando espectros..."):
        all_data = []  # Lista de tuplas (df, spectral_cols, filename)
        
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
    
    selected_spectra = []  # Lista de arrays numpy con espectros seleccionados
    spectrum_labels = []   # Lista de labels "ID + Note + fila"
    
    for idx, (df, spectral_cols, filename) in enumerate(all_data):
        with st.expander(f"**{filename}** ({len(df)} filas disponibles)", expanded=(idx==0)):
            
            # Filtro de búsqueda y opción de agrupamiento
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
                # Convertir columnas espectrales a numérico
                df_filtered_numeric = df_filtered.copy()
                df_filtered_numeric[spectral_cols] = df_filtered_numeric[spectral_cols].apply(pd.to_numeric, errors='coerce')
                
                # Agrupar y promediar
                df_aggregated = df_filtered_numeric.groupby(['ID', 'Note'], as_index=False).agg({
                    **{col: 'mean' for col in spectral_cols}
                })
                
                # Contar réplicas
                replica_counts = df_filtered.groupby(['ID', 'Note']).size().reset_index(name='N_replicas')
                df_aggregated = df_aggregated.merge(replica_counts, on=['ID', 'Note'], how='left')
                
                # Crear identificador único para cada grupo
                df_aggregated['Group_Key'] = df_aggregated['ID'].astype(str) + '|||' + df_aggregated['Note'].astype(str)
                
                # Crear tabla de visualización
                df_display = df_aggregated[['ID', 'Note', 'N_replicas', 'Group_Key']].copy()
                df_display.insert(0, 'Grupo', range(len(df_display)))
                
                st.caption(f"Mostrando {len(df_aggregated)} grupos (de {len(df_filtered)} filas)")
                
                # Guardar referencia al dataframe completo agrupado
                if f'df_grouped_{idx}' not in st.session_state or st.session_state.get(f'needs_refresh_{idx}', False):
                    st.session_state[f'df_grouped_{idx}'] = df_aggregated
                    st.session_state[f'needs_refresh_{idx}'] = False
                
            else:
                # Modo normal (sin agrupar) - MANTENER ÍNDICES ORIGINALES
                df_display = df_filtered[['ID', 'Note']].copy()
                # NO hacer reset_index, usar los índices reales del dataframe
                df_display.insert(0, 'Fila', df_display.index)
                
                if search_term:
                    st.caption(f"Mostrando {len(df_filtered)} de {len(df)} filas")
            
            # Botones de control - AÑADIR 5ª COLUMNA
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                select_all = st.button("✅ Seleccionar todo", key=f'select_all_{idx}', use_container_width=True)
            
            with col2:
                deselect_all = st.button("❌ Deseleccionar todo", key=f'deselect_all_{idx}', use_container_width=True)
            
            with col3:
                invert_sel = st.button("🔄 Invertir selección", key=f'invert_{idx}', use_container_width=True)
            
            with col4:
                confirm = st.button("✔️ Confirmar", key=f'confirm_{idx}', type="primary", use_container_width=True)
            
            with col5:
                reset = st.button("🗑️ Limpiar", key=f'reset_{idx}', use_container_width=True, help="Resetear toda la selección")
            
            # Procesar botón de reset PRIMERO
            if reset:
                # Limpiar TODOS los estados relacionados con este archivo
                keys_to_delete = [
                    f'confirmed_{idx}',
                    f'grouped_{idx}',
                    f'confirmed_group_keys_{idx}',
                    f'confirmed_indices_{idx}',
                    f'df_grouped_{idx}',
                    f'needs_refresh_{idx}',
                    f'select_state_{idx}',
                    f'previous_selection_{idx}'
                ]
                for key in keys_to_delete:
                    if key in st.session_state:
                        del st.session_state[key]
                
                st.success("🗑️ Selección limpiada. Vuelve a marcar las filas que necesites.")
                st.rerun()
            
            # Aplicar acciones de botones
            default_selection = False
            if select_all:
                default_selection = True
            elif deselect_all:
                default_selection = False
            
            df_display.insert(0, 'Seleccionar', default_selection)
            
            # Configurar columnas del editor
            if group_by_sample:
                disabled_cols = ['Grupo', 'ID', 'Note', 'N_replicas', 'Group_Key']
                column_config = {
                    "Grupo": st.column_config.NumberColumn(
                        "Grupo",
                        help="Identificador del grupo",
                        width="small"
                    ),
                    "N_replicas": st.column_config.NumberColumn(
                        "Réplicas",
                        help="Número de réplicas promediadas",
                        width="small"
                    ),
                    "Group_Key": None  # Ocultar esta columna
                }
            else:
                disabled_cols = ['Fila', 'ID', 'Note']
                column_config = {
                    "Fila": st.column_config.NumberColumn(
                        "Fila",
                        help="Índice de fila original",
                        width="small"
                    )
                }
            
            edited_df = st.data_editor(
                df_display,
                hide_index=True,
                use_container_width=True,
                disabled=disabled_cols,
                key=f'selector_{idx}',
                column_config=column_config
            )
            
            # Invertir después del editor
            if invert_sel:
                edited_df['Seleccionar'] = ~edited_df['Seleccionar']
            
            # Obtener índices seleccionados
            selected_rows = edited_df[edited_df['Seleccionar'] == True]
            
            if group_by_sample:
                # Obtener las claves de grupo seleccionadas
                selected_group_keys = selected_rows['Group_Key'].tolist()
                n_selected = len(selected_group_keys)
            else:
                # Obtener índices reales del dataframe original
                original_indices = selected_rows['Fila'].tolist()
                n_selected = len(original_indices)
            
            if n_selected > 0:
                st.info(f"📝 {n_selected} {'grupos' if group_by_sample else 'filas'} marcados (presiona ✔️ Confirmar para aplicar)")
            
            # SOLO agregar si se confirmó
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
                    # Modo agrupado
                    confirmed_group_keys = st.session_state.get(f'confirmed_group_keys_{idx}', [])
                    
                    if len(confirmed_group_keys) > 0:
                        st.success(f"✔️ Selección activa: {len(confirmed_group_keys)} grupos (réplicas promediadas)")
                        
                        # Usar dataframe agrupado guardado
                        df_grouped = st.session_state.get(f'df_grouped_{idx}')
                        
                        if df_grouped is not None:
                            # Filtrar por las claves seleccionadas
                            df_selected_groups = df_grouped[df_grouped['Group_Key'].isin(confirmed_group_keys)]
                            
                            for _, row in df_selected_groups.iterrows():
                                spectrum = row[spectral_cols].values
                                label = f"{row['ID']} | {row['Note']} | Promedio ({int(row['N_replicas'])} rép.)"
                                selected_spectra.append(spectrum)
                                spectrum_labels.append(label)
                else:
                    # Modo individual
                    confirmed_indices = st.session_state.get(f'confirmed_indices_{idx}', [])
                    
                    if len(confirmed_indices) > 0:
                        st.success(f"✔️ Selección activa: {len(confirmed_indices)} filas")
                        
                        # Usar los índices REALES del dataframe original
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
        
        fig_residuals = create_residuals_plot(
            selected_spectra, 
            spectrum_labels, 
            reference_idx,
            st.session_state.visible_spectra
        )
        st.plotly_chart(fig_residuals, use_container_width=True)
        
        with st.expander("📊 Estadísticas de Residuales"):
            residuals = calculate_residuals(selected_spectra, reference_idx)
            
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
        
    with st.expander("🔗 Correlación con Referencia"):
        reference_idx_corr = st.selectbox(
            "Selecciona espectro de referencia:",
            range(len(spectrum_labels)),
            format_func=lambda x: f"{x+1}. {spectrum_labels[x]}",
            key="corr_ref_selector"
        )
        
        corr_stats = []
        ref_spectrum = selected_spectra[reference_idx_corr]
        
        # CONVERTIR A FLOAT64 explícitamente
        ref_flat = np.asarray(ref_spectrum, dtype=np.float64).flatten()
        
        for i, (spectrum, label) in enumerate(zip(selected_spectra, spectrum_labels)):
            if i != reference_idx_corr:
                try:
                    # CONVERTIR A FLOAT64 explícitamente
                    spec_flat = np.asarray(spectrum, dtype=np.float64).flatten()
                    
                    # Validación de compatibilidad
                    if len(ref_flat) != len(spec_flat):
                        st.error(f"Error en {label}: diferentes longitudes ({len(ref_flat)} vs {len(spec_flat)})")
                        continue
                    
                    if len(ref_flat) < 2:
                        st.error(f"Error en {label}: espectro demasiado corto ({len(ref_flat)} puntos)")
                        continue
                    
                    # Verificar que no hay NaN o Inf
                    if np.any(~np.isfinite(ref_flat)) or np.any(~np.isfinite(spec_flat)):
                        st.error(f"Error en {label}: contiene valores NaN o Inf")
                        continue
                    
                    # Normalizar
                    ref_norm = (ref_flat - np.mean(ref_flat)) / (np.std(ref_flat) + 1e-10)
                    spec_norm = (spec_flat - np.mean(spec_flat)) / (np.std(spec_flat) + 1e-10)
                    
                    # Correlación de Pearson manual
                    correlation = np.sum(ref_norm * spec_norm) / len(ref_norm)
                    
                    # Validar resultado
                    if not np.isfinite(correlation):
                        st.error(f"Error en {label}: correlación no válida")
                        continue
                    
                    corr_stats.append({
                        'Espectro': label,
                        'Correlación': f"{correlation:.8f}",
                        'Estado': '✅ Excelente' if correlation > 0.999 else ('✓ Bueno' if correlation > 0.995 else '⚠️ Revisar')
                    })
                    
                except Exception as e:
                    st.error(f"Error procesando {label}: {str(e)}")
                    continue
        
        if corr_stats:
            st.dataframe(pd.DataFrame(corr_stats), use_container_width=True, hide_index=True)
        else:
            st.warning("No se pudieron calcular correlaciones")
        
    # TAB 4: Matriz RMS
    with tab4:
        st.subheader("Matriz de Diferencias RMS")
        
        # Toggle para cambiar entre escala relativa y absoluta
        col_toggle, col_info = st.columns([1, 3])
        with col_toggle:
            use_absolute_scale = st.checkbox(
                "Escala absoluta",
                value=True,
                help="Usar umbrales fijos en vez de escala relativa"
            )
        
        with col_info:
            if use_absolute_scale:
                st.info("📏 **Escala absoluta para white references**: Verde < 0.005 AU | Amarillo < 0.01 AU | Rojo ≥ 0.01 AU")
            else:
                st.info("📊 **Escala relativa**: Colores basados en valores mín/máx de los espectros comparados")
        
        # Crear heatmap según el modo seleccionado
        if use_absolute_scale:
            # Escala absoluta para white references
            n_spectra = len(selected_spectra)
            rms_matrix = np.zeros((n_spectra, n_spectra))
            
            for i in range(n_spectra):
                for j in range(n_spectra):
                    if i == j:
                        rms_matrix[i, j] = 0
                    else:
                        diff = selected_spectra[i] - selected_spectra[j]
                        rms_matrix[i, j] = np.sqrt(np.mean(diff**2))
            
            # Escala de colores personalizada con umbrales absolutos
            colorscale = [
                [0.0, '#4caf50'],      # Verde (excelente) 0-0.005
                [0.333, '#8bc34a'],    # Verde claro
                [0.667, '#ffc107'],    # Amarillo (aceptable) 0.005-0.01
                [1.0, '#f44336']       # Rojo (revisar) >0.01
            ]
            
            fig_heatmap = go.Figure(data=go.Heatmap(
                z=rms_matrix,
                x=spectrum_labels,
                y=spectrum_labels,
                colorscale=colorscale,
                zmin=0,
                zmax=0.015,  # Escala fija
                text=np.round(rms_matrix, 6),
                texttemplate='%{text}',
                textfont={"size": 10},
                colorbar=dict(
                    title="RMS (AU)",
                    tickvals=[0, 0.002, 0.005, 0.01, 0.015],
                    ticktext=['0.000', '0.002<br>(Exc)', '0.005<br>(Bueno)', '0.010<br>(Acept)', '0.015']
                )
            ))
            
            fig_heatmap.update_layout(
                title='Matriz de Diferencias RMS - Escala Absoluta',
                height=max(400, 50 * n_spectra),
                template='plotly_white'
            )
        else:
            # Escala relativa (original)
            fig_heatmap = create_residuals_heatmap(selected_spectra, spectrum_labels)
        
        st.plotly_chart(fig_heatmap, use_container_width=True)
        
        # Análisis de similitud
        with st.expander("🔍 Análisis de Similitud"):
            n_spectra = len(selected_spectra)
            rms_values = []
            
            for i in range(n_spectra):
                for j in range(i+1, n_spectra):
                    diff = selected_spectra[i] - selected_spectra[j]
                    rms = np.sqrt(np.mean(diff**2))
                    max_diff = np.abs(diff).max()
                    
                    # Evaluar según umbrales
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
            
            rms_df = pd.DataFrame(rms_values)
            rms_df = rms_df.sort_values('RMS')
            
            st.markdown("**Pares más similares:**")
            st.dataframe(rms_df.head(5), use_container_width=True, hide_index=True)
            
            st.markdown("**Pares que requieren atención:**")
            problem_pairs = rms_df[rms_df['Evaluación'].str.contains('❌|⚠️')]
            if len(problem_pairs) > 0:
                st.dataframe(problem_pairs, use_container_width=True, hide_index=True)
            else:
                st.success("✅ Todas las comparaciones están en rango excelente/bueno")
        
        st.divider()
        
        # Matriz de correlación (sin cambios)
        st.subheader("Matriz de Correlación Espectral")
        st.markdown("Valores más cercanos a 1.0 indican mayor similitud")
        st.caption("⚠️ Nota: La correlación puede no ser apropiada para espectros muy planos (white references)")
        
        corr_matrix = calculate_correlation_matrix(selected_spectra, spectrum_labels)
        
        fig_corr = go.Figure(data=go.Heatmap(
            z=corr_matrix,
            x=spectrum_labels,
            y=spectrum_labels,
            colorscale='RdYlGn',
            zmin=0.99,
            zmax=1.0,
            text=np.round(corr_matrix, 6),
            texttemplate='%{text}',
            textfont={"size": 10},
            colorbar=dict(title="Correlación")
        ))
        
        fig_corr.update_layout(
            title='Matriz de Correlación Espectral',
            height=max(400, 50 * len(selected_spectra)),
            template='plotly_white'
        )
        
        st.plotly_chart(fig_corr, use_container_width=True)


if __name__ == "__main__":
    main()