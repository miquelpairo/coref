"""
Plotly Visualization Utilities
===============================
Funciones reutilizables para crear gráficos interactivos con Plotly.
Parte del ecosistema COREF.

Author: Miquel
Date: 2024
"""

import numpy as np
import plotly.graph_objects as go
from typing import List


# Paleta de colores corporativa para gráficos
PLOT_COLORS = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
]


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