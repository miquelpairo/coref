"""
Plotly Visualization Utilities
===============================
Funciones reutilizables para crear gráficos interactivos con Plotly.
Parte del ecosistema COREF.

Author: Miquel
Date: 2024
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from typing import List, Optional, Tuple, Set, Dict


# Paleta de colores corporativa para gráficos
PLOT_COLORS = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
]


# =============================================================================
# FUNCIONES ORIGINALES (Espectros COREF)
# =============================================================================

def create_overlay_plot(spectra_list: List[np.ndarray], names: List[str], 
                       visible_spectra: List[bool]) -> go.Figure:
    """
    Crea gráfico con todos los espectros superpuestos.
    
    Args:
        spectra_list: Lista de arrays numpy con espectros
        names: Lista de nombres/etiquetas para cada espectro
        visible_spectra: Lista de booleanos indicando visibilidad inicial
        
    Returns:
        Figura de Plotly configurada
    """
    fig = go.Figure()
    channels = list(range(1, len(spectra_list[0]) + 1))
    
    for i, (spectrum, name, visible) in enumerate(zip(spectra_list, names, visible_spectra)):
        color = PLOT_COLORS[i % len(PLOT_COLORS)]
        
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
                         reference_idx: int, visible_spectra: List[bool],
                         residuals: List[np.ndarray] = None) -> go.Figure:
    """
    Crea gráfico de residuales respecto a un espectro de referencia.
    
    Args:
        spectra_list: Lista de arrays numpy con espectros
        names: Lista de nombres/etiquetas
        reference_idx: Índice del espectro de referencia
        visible_spectra: Lista de booleanos indicando visibilidad
        residuals: Residuales pre-calculados (opcional)
        
    Returns:
        Figura de Plotly configurada
    """
    # Si no se proporcionan residuales, calcularlos
    if residuals is None:
        from core.spectrum_analysis import calculate_residuals
        residuals = calculate_residuals(spectra_list, reference_idx)
    
    channels = list(range(1, len(spectra_list[0]) + 1))
    fig = go.Figure()
    
    for i, (residual, name, visible) in enumerate(zip(residuals, names, visible_spectra)):
        if i == reference_idx:
            continue
        
        color = PLOT_COLORS[i % len(PLOT_COLORS)]
        
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


def create_rms_heatmap(spectra_list: List[np.ndarray], names: List[str],
                      absolute_scale: bool = False) -> go.Figure:
    """
    Crea un mapa de calor mostrando las diferencias RMS entre todos los pares.
    
    Args:
        spectra_list: Lista de arrays numpy con espectros
        names: Lista de nombres/etiquetas
        absolute_scale: Si True, usa escala absoluta 0-0.015 con umbrales fijos
        
    Returns:
        Figura de Plotly configurada
    """
    from core.spectrum_analysis import calculate_rms_matrix
    
    rms_matrix = calculate_rms_matrix(spectra_list)
    n_spectra = len(spectra_list)
    
    if absolute_scale:
        # Escala absoluta para white references
        colorscale = [
            [0.0, '#4caf50'],      # Verde (excelente) 0-0.005
            [0.333, '#8bc34a'],    # Verde claro
            [0.667, '#ffc107'],    # Amarillo (aceptable) 0.005-0.01
            [1.0, '#f44336']       # Rojo (revisar) >0.01
        ]
        
        fig = go.Figure(data=go.Heatmap(
            z=rms_matrix,
            x=names,
            y=names,
            colorscale=colorscale,
            zmin=0,
            zmax=0.015,
            text=np.round(rms_matrix, 6),
            texttemplate='%{text}',
            textfont={"size": 10},
            colorbar=dict(
                title="RMS (AU)",
                tickvals=[0, 0.002, 0.005, 0.01, 0.015],
                ticktext=['0.000', '0.002<br>(Exc)', '0.005<br>(Bueno)', '0.010<br>(Acept)', '0.015']
            )
        ))
        
        title_text = 'Matriz de Diferencias RMS - Escala Absoluta'
    else:
        # Escala relativa (auto)
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
        
        title_text = 'Matriz de Diferencias RMS'
    
    fig.update_layout(
        title=title_text,
        height=max(400, 50 * n_spectra),
        template='plotly_white'
    )
    
    return fig


def create_correlation_heatmap(corr_matrix: np.ndarray, names: List[str]) -> go.Figure:
    """
    Crea un mapa de calor de la matriz de correlación.
    
    Args:
        corr_matrix: Matriz de correlación NxN
        names: Lista de nombres/etiquetas
        
    Returns:
        Figura de Plotly configurada
    """
    n_spectra = len(names)
    
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix,
        x=names,
        y=names,
        colorscale='RdYlGn',
        zmin=0.99,
        zmax=1.0,
        text=np.round(corr_matrix, 6),
        texttemplate='%{text}',
        textfont={"size": 10},
        colorbar=dict(title="Correlación")
    ))
    
    fig.update_layout(
        title='Matriz de Correlación Espectral',
        height=max(400, 50 * n_spectra),
        template='plotly_white'
    )
    
    return fig


# =============================================================================
# NUEVAS FUNCIONES PARA TSV VALIDATION REPORTS
# =============================================================================

def apply_plotly_theme(fig: go.Figure, title: str = None, 
                      height: int = 600, show_legend: bool = True) -> go.Figure:
    """
    Aplica tema consistente a figuras de Plotly.
    
    Args:
        fig: Figura de Plotly
        title: Título del gráfico (opcional)
        height: Altura en píxeles
        show_legend: Si mostrar leyenda
        
    Returns:
        Figura con tema aplicado
    """
    layout_updates = {
        'template': 'plotly_white',
        'height': height,
        'hovermode': 'closest',
        'showlegend': show_legend
    }
    
    if title:
        layout_updates['title'] = {
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18}
        }
    
    if show_legend:
        layout_updates['legend'] = dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        )
    
    fig.update_layout(**layout_updates)
    return fig


def create_parity_plot(df: pd.DataFrame, 
                      result_col: str,
                      reference_col: str,
                      removed_indices: Set[int],
                      sample_groups: Dict[int, str],
                      group_labels: Dict[str, str],
                      sample_groups_config: Dict[str, Dict]) -> Optional[Tuple[go.Figure, float, float, float, int]]:
    """
    Crea un gráfico parity (Reference vs Result) con grupos y puntos eliminados.
    
    Args:
        df: DataFrame con los datos
        result_col: Nombre de columna Result
        reference_col: Nombre de columna Reference
        removed_indices: Set de índices marcados para eliminar
        sample_groups: Dict {idx: group_name}
        group_labels: Dict {group_key: custom_label}
        sample_groups_config: Configuración visual de grupos (símbolos, colores)
        
    Returns:
        Tupla (figura, r2, rmse, bias, n) o None si no hay datos válidos
    """
    # Filtrar datos válidos
    mask = df[result_col].notna() & df[reference_col].notna()
    df_valid = df[mask].copy()
    
    if len(df_valid) == 0:
        return None
    
    # Separar por estado (eliminados/agrupados/normales)
    df_removed = df_valid[df_valid.index.isin(removed_indices)]
    df_active = df_valid[~df_valid.index.isin(removed_indices)]
    
    # Calcular estadísticas solo con muestras activas
    if len(df_active) > 0:
        ref_vals = df_active[reference_col].values
        res_vals = df_active[result_col].values
        
        # R²
        ss_res = np.sum((res_vals - ref_vals) ** 2)
        ss_tot = np.sum((ref_vals - np.mean(ref_vals)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        # RMSE
        rmse = np.sqrt(np.mean((res_vals - ref_vals) ** 2))
        
        # BIAS
        bias = np.mean(res_vals - ref_vals)
        
        n = len(df_active)
    else:
        r2 = rmse = bias = 0
        n = 0
    
    # Crear figura
    fig = go.Figure()
    
    # Línea 1:1
    all_vals = pd.concat([df_valid[reference_col], df_valid[result_col]])
    min_val, max_val = all_vals.min(), all_vals.max()
    margin = (max_val - min_val) * 0.1
    
    fig.add_trace(go.Scatter(
        x=[min_val - margin, max_val + margin],
        y=[min_val - margin, max_val + margin],
        mode='lines',
        line=dict(color='gray', dash='dash', width=1),
        name='1:1',
        showlegend=False,
        hoverinfo='skip'
    ))
    
    # Agrupar muestras activas por grupo
    groups_to_plot = {"none": df_active[~df_active.index.isin(sample_groups.keys())]}
    
    for group_key in ["Set 1", "Set 2", "Set 3", "Set 4"]:
        group_indices = [idx for idx, g in sample_groups.items() 
                        if g == group_key and idx in df_active.index]
        if group_indices:
            groups_to_plot[group_key] = df_active.loc[group_indices]
    
    # Plotear grupos activos
    for group_key, df_group in groups_to_plot.items():
        if len(df_group) == 0:
            continue
        
        config = sample_groups_config.get(group_key, sample_groups_config["none"])
        label = group_labels.get(group_key, group_key) if group_key != "none" else "Sin grupo"
        
        # Preparar customdata: [row_index, date_str]
        customdata = []
        for idx in df_group.index:
            date_val = df_group.loc[idx, "Date"] if "Date" in df_group.columns else None
            date_str = date_val.strftime("%Y-%m-%d %H:%M") if pd.notna(date_val) else "N/A"
            customdata.append([int(idx), date_str])
        
        fig.add_trace(go.Scatter(
            x=df_group[reference_col],
            y=df_group[result_col],
            mode='markers',
            name=label,
            marker=dict(
                symbol=config['symbol'],
                size=config['size'],
                color=config['color'],
                line=dict(width=1, color='white')
            ),
            customdata=customdata,
            hovertemplate=(
                '<b>Muestra %{customdata[0]}</b><br>' +
                'Reference: %{x:.3f}<br>' +
                'Result: %{y:.3f}<br>' +
                'Fecha: %{customdata[1]}<br>' +
                '<extra></extra>'
            )
        ))
    
    # Plotear muestras eliminadas (semi-transparentes)
    if len(df_removed) > 0:
        customdata_removed = []
        for idx in df_removed.index:
            date_val = df_removed.loc[idx, "Date"] if "Date" in df_removed.columns else None
            date_str = date_val.strftime("%Y-%m-%d %H:%M") if pd.notna(date_val) else "N/A"
            customdata_removed.append([int(idx), date_str])
        
        fig.add_trace(go.Scatter(
            x=df_removed[reference_col],
            y=df_removed[result_col],
            mode='markers',
            name='Marcadas para eliminar',
            marker=dict(
                symbol='x',
                size=8,
                color='red',
                opacity=0.4
            ),
            customdata=customdata_removed,
            hovertemplate=(
                '<b>Muestra %{customdata[0]} (ELIMINAR)</b><br>' +
                'Reference: %{x:.3f}<br>' +
                'Result: %{y:.3f}<br>' +
                'Fecha: %{customdata[1]}<br>' +
                '<extra></extra>'
            )
        ))
    
    # Layout
    param_name = result_col.replace("Result ", "")
    fig.update_layout(
        title=f'Parity Plot: {param_name}',
        xaxis_title=f'Reference {param_name}',
        yaxis_title=f'Result {param_name}',
        template='plotly_white',
        height=600,
        hovermode='closest',
        showlegend=True
    )
    
    return fig, r2, rmse, bias, n


def create_residuum_plot(df: pd.DataFrame,
                        result_col: str,
                        reference_col: str,
                        residuum_col: str,
                        removed_indices: Set[int]) -> go.Figure:
    """
    Crea gráfico de residuales vs Reference.
    
    Args:
        df: DataFrame con los datos
        result_col: Nombre de columna Result
        reference_col: Nombre de columna Reference
        residuum_col: Nombre de columna Residuum
        removed_indices: Set de índices marcados para eliminar
        
    Returns:
        Figura de Plotly
    """
    mask = df[residuum_col].notna() & df[reference_col].notna()
    df_valid = df[mask].copy()
    
    df_active = df_valid[~df_valid.index.isin(removed_indices)]
    df_removed = df_valid[df_valid.index.isin(removed_indices)]
    
    fig = go.Figure()
    
    # Línea en y=0
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    # Puntos activos
    if len(df_active) > 0:
        fig.add_trace(go.Scatter(
            x=df_active[reference_col],
            y=df_active[residuum_col],
            mode='markers',
            name='Activas',
            marker=dict(size=8, color='blue', opacity=0.6)
        ))
    
    # Puntos eliminados
    if len(df_removed) > 0:
        fig.add_trace(go.Scatter(
            x=df_removed[reference_col],
            y=df_removed[residuum_col],
            mode='markers',
            name='Marcadas para eliminar',
            marker=dict(size=8, color='red', symbol='x', opacity=0.4)
        ))
    
    param_name = result_col.replace("Result ", "")
    fig.update_layout(
        title=f'Residuales: {param_name}',
        xaxis_title=f'Reference {param_name}',
        yaxis_title='Residuum',
        template='plotly_white',
        height=400,
        showlegend=True
    )
    
    return fig


def create_residuum_histogram(df: pd.DataFrame,
                              residuum_col: str,
                              removed_indices: Set[int]) -> go.Figure:
    """
    Crea histograma de residuales.
    
    Args:
        df: DataFrame con los datos
        residuum_col: Nombre de columna Residuum
        removed_indices: Set de índices marcados para eliminar
        
    Returns:
        Figura de Plotly
    """
    mask = df[residuum_col].notna()
    df_valid = df[mask].copy()
    
    df_active = df_valid[~df_valid.index.isin(removed_indices)]
    
    fig = go.Figure()
    
    if len(df_active) > 0:
        fig.add_trace(go.Histogram(
            x=df_active[residuum_col],
            nbinsx=30,
            name='Residuales',
            marker_color='steelblue',
            opacity=0.7
        ))
    
    param_name = residuum_col.replace("Residuum ", "")
    fig.update_layout(
        title=f'Distribución de Residuales: {param_name}',
        xaxis_title='Residuum',
        yaxis_title='Frecuencia',
        template='plotly_white',
        height=400,
        showlegend=False
    )
    
    return fig

# Añadir a plotly_utils.py

def create_samples_by_month_chart(df: pd.DataFrame) -> go.Figure:
    """
    Crea gráfico de barras agrupadas por archivo mostrando muestras por mes.
    
    Args:
        df: DataFrame con columnas: Mes, Muestras, Archivo
        
    Returns:
        Figura de Plotly
    """
    fig = go.Figure()
    
    for fname, group_df in df.groupby("Archivo"):
        fig.add_bar(
            x=group_df["Mes"],
            y=group_df["Muestras"],
            name=fname,
        )
    
    fig.update_layout(
        barmode="group",
        height=400,
        title="Nº de muestras por mes (por archivo)",
        xaxis_title="Mes",
        yaxis_title="Nº de muestras",
        template="plotly_white",
    )
    
    return fig