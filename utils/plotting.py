"""
Funciones de visualización con Plotly
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import pandas as pd
from config import PLOT_CONFIG


def plot_wstd_spectra(df_wstd_grouped, spectral_cols, lamps):
    """
    Crea gráficos de espectros WSTD y diferencias.
    
    Args:
        df_wstd_grouped (pd.DataFrame): DataFrame agrupado por lámpara
        spectral_cols (list): Lista de columnas espectrales
        lamps (list): Lista de nombres de lámparas
        
    Returns:
        plotly.graph_objects.Figure: Figura con los gráficos
    """
    # Crear subplots (2 filas)
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(
            'Espectros del White Standard (sin línea base)',
            'Diferencia espectral' if len(df_wstd_grouped) == 2 else ''
        ),
        vertical_spacing=0.12
    )
    
    channels = list(range(1, len(spectral_cols) + 1))
    
    # Gráfico 1: Espectros de cada lámpara
    for lamp in df_wstd_grouped.index:
        spectrum = df_wstd_grouped.loc[lamp].values
        fig.add_trace(
            go.Scatter(
                x=channels,
                y=spectrum,
                mode='lines',
                name=lamp,
                line=dict(width=2),
                hovertemplate='Canal: %{x}<br>Intensidad: %{y:.4f}<extra></extra>'
            ),
            row=1, col=1
        )
    
    # Línea de referencia en 0
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5, row=1, col=1)
    
    # Gráfico 2: Diferencia entre lámparas
    if len(df_wstd_grouped) == 2:
        lamp1, lamp2 = df_wstd_grouped.index[0], df_wstd_grouped.index[1]
        diff = df_wstd_grouped.loc[lamp1].values - df_wstd_grouped.loc[lamp2].values
        
        fig.add_trace(
            go.Scatter(
                x=channels,
                y=diff,
                mode='lines',
                name=f'{lamp1} - {lamp2}',
                line=dict(width=2, color='red'),
                hovertemplate='Canal: %{x}<br>Diferencia: %{y:.4f}<extra></extra>'
            ),
            row=2, col=1
        )
        
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5, row=2, col=1)
    
    # Layout
    fig.update_xaxes(title_text="Canal espectral", row=1, col=1)
    fig.update_xaxes(title_text="Canal espectral", row=2, col=1)
    fig.update_yaxes(title_text="Intensidad", row=1, col=1)
    fig.update_yaxes(title_text="Diferencia", row=2, col=1)
    
    fig.update_layout(
        height=800,
        showlegend=True,
        hovermode='closest',
        template='plotly_white'
    )
    
    return fig


def plot_kit_spectra(df_ref_grouped, df_new_grouped, spectral_cols, 
                     lamp_ref, lamp_new, common_ids):
    """
    Crea gráfico comparativo de espectros del kit.
    
    Args:
        df_ref_grouped (pd.DataFrame): Mediciones de referencia
        df_new_grouped (pd.DataFrame): Mediciones nuevas
        spectral_cols (list): Columnas espectrales
        lamp_ref (str): Nombre lámpara referencia
        lamp_new (str): Nombre lámpara nueva
        common_ids (list): IDs comunes
        
    Returns:
        plotly.graph_objects.Figure: Figura con el gráfico
    """
    fig = go.Figure()
    
    channels = list(range(1, len(spectral_cols) + 1))
    
    # Colores alternados para mejor distinción
    colors_ref = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    colors_new = ['#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    
    for idx, id_ in enumerate(common_ids):
        color_ref = colors_ref[idx % len(colors_ref)]
        color_new = colors_new[idx % len(colors_new)]
        
        # Lámpara de referencia
        fig.add_trace(go.Scatter(
            x=channels,
            y=df_ref_grouped.loc[id_],
            mode='lines',
            name=f'{lamp_ref} - {id_}',
            line=dict(width=1.5, color=color_ref),
            opacity=0.8,
            hovertemplate=f'{lamp_ref} - {id_}<br>Canal: %{{x}}<br>Absorbancia: %{{y:.4f}}<extra></extra>'
        ))
        
        # Lámpara nueva
        fig.add_trace(go.Scatter(
            x=channels,
            y=df_new_grouped.loc[id_],
            mode='lines',
            name=f'{lamp_new} - {id_}',
            line=dict(width=1.5, dash='dash', color=color_new),
            opacity=0.8,
            hovertemplate=f'{lamp_new} - {id_}<br>Canal: %{{x}}<br>Absorbancia: %{{y:.4f}}<extra></extra>'
        ))
    
    fig.update_layout(
        title='Espectros promedio por muestra',
        xaxis_title='Canal espectral',
        yaxis_title='Absorbancia',
        height=600,
        hovermode='closest',
        template='plotly_white',
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=1.05
        )
    )
    
    return fig


def plot_correction_differences(df_diff, common_ids, selected_ids):
    """
    Crea gráfico de diferencias espectrales y corrección promedio.
    
    Args:
        df_diff (pd.DataFrame): DataFrame con diferencias y corrección
        common_ids (list): IDs comunes
        selected_ids (list): IDs seleccionados para corrección
        
    Returns:
        plotly.graph_objects.Figure: Figura con el gráfico
    """
    fig = go.Figure()
    
    # Graficar diferencias por muestra
    for id_ in common_ids:
        is_selected = id_ in selected_ids
        
        fig.add_trace(go.Scatter(
            x=df_diff["Canal"],
            y=df_diff[f"DIF_{id_}"],
            mode='lines',
            name=f"{'✓ ' if is_selected else '✗ '}{id_}",
            line=dict(
                width=1.5 if is_selected else 0.8,
                color='rgba(100, 100, 100, 0.7)' if is_selected else 'rgba(200, 200, 200, 0.3)'
            ),
            hovertemplate=f'{id_}<br>Canal: %{{x}}<br>Diferencia: %{{y:.4f}}<extra></extra>'
        ))
    
    # Graficar corrección promedio (destacada)
    fig.add_trace(go.Scatter(
        x=df_diff["Canal"],
        y=df_diff["CORRECCION_PROMEDIO"],
        mode='lines',
        name='Corrección Promedio',
        line=dict(width=3, color='red'),
        hovertemplate='Canal: %{x}<br>Corrección: %{y:.4f}<extra></extra>'
    ))
    
    # Línea de referencia
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    fig.update_layout(
        title='Diferencias espectrales por muestra',
        xaxis_title='Canal espectral',
        yaxis_title='Diferencia',
        height=600,
        hovermode='closest',
        template='plotly_white',
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=1.05
        )
    )
    
    return fig


def plot_correction_summary(mean_diff):
    """
    Crea un gráfico simple del vector de corrección.
    
    Args:
        mean_diff (np.array): Vector de corrección promedio
        
    Returns:
        plotly.graph_objects.Figure: Figura con el gráfico
    """
    fig = go.Figure()
    
    channels = list(range(1, len(mean_diff) + 1))
    
    fig.add_trace(go.Scatter(
        x=channels,
        y=mean_diff,
        mode='lines',
        name='Corrección',
        line=dict(width=2, color='red'),
        hovertemplate='Canal: %{x}<br>Corrección: %{y:.4f}<extra></extra>'
    ))
    
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    fig.update_layout(
        title='Vector de Corrección Espectral',
        xaxis_title='Canal espectral',
        yaxis_title='Corrección',
        height=500,
        hovermode='closest',
        template='plotly_white'
    )
    
    return fig


def plot_baseline_spectrum(baseline_spectrum, lamp_name):
    """
    Crea gráfico del espectro de baseline.
    
    Args:
        baseline_spectrum (np.array): Espectro del baseline
        lamp_name (str): Nombre de la lámpara
        
    Returns:
        plotly.graph_objects.Figure: Figura con el gráfico
    """
    fig = go.Figure()
    
    channels = list(range(1, len(baseline_spectrum) + 1))
    
    fig.add_trace(go.Scatter(
        x=channels,
        y=baseline_spectrum,
        mode='lines',
        name='Baseline',
        line=dict(width=2, color='blue'),
        hovertemplate='Canal: %{x}<br>Intensidad: %{y:.2f}<extra></extra>'
    ))
    
    fig.update_layout(
        title=f'Baseline original de {lamp_name}',
        xaxis_title='Canal espectral',
        yaxis_title='Intensidad',
        height=400,
        hovermode='closest',
        template='plotly_white'
    )
    
    return fig


def plot_baseline_comparison(baseline_original, baseline_corrected, spectral_cols):
    """
    Crea gráfico comparativo de baseline original vs corregido.
    
    Args:
        baseline_original (np.array): Baseline original
        baseline_corrected (np.array): Baseline corregido
        spectral_cols (list): Lista de columnas espectrales
        
    Returns:
        plotly.graph_objects.Figure: Figura con el gráfico
    """
    fig = go.Figure()
    
    channels = list(range(1, len(baseline_original) + 1))
    
    fig.add_trace(go.Scatter(
        x=channels,
        y=baseline_original,
        mode='lines',
        name='Baseline original',
        line=dict(width=2, color='blue'),
        hovertemplate='Canal: %{x}<br>Original: %{y:.2f}<extra></extra>'
    ))
    
    fig.add_trace(go.Scatter(
        x=channels,
        y=baseline_corrected,
        mode='lines',
        name='Baseline corregido',
        line=dict(width=2, dash='dash', color='red'),
        hovertemplate='Canal: %{x}<br>Corregido: %{y:.2f}<extra></extra>'
    ))
    
    fig.update_layout(
        title='Comparación: baseline original vs corregido',
        xaxis_title='Canal espectral',
        yaxis_title='Intensidad',
        height=500,
        hovermode='closest',
        template='plotly_white'
    )
    
    return fig


def plot_corrected_spectra_comparison(df_ref_grouped, df_corrected, spectral_cols, 
                                      lamp_ref, lamp_new, sample_ids, 
                                      title="Comparación de espectros"):
    """
    Crea gráfico comparando espectros de referencia vs corregidos.
    
    Args:
        df_ref_grouped (pd.DataFrame): Espectros de referencia
        df_corrected (pd.DataFrame): Espectros corregidos
        spectral_cols (list): Columnas espectrales
        lamp_ref (str): Nombre lámpara referencia
        lamp_new (str): Nombre lámpara nueva
        sample_ids (list): IDs de muestras a graficar
        title (str): Título del gráfico
        
    Returns:
        plotly.graph_objects.Figure: Figura con el gráfico
    """
    fig = go.Figure()
    
    channels = list(range(1, len(spectral_cols) + 1))
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
              '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    
    for idx, id_ in enumerate(sample_ids):
        color = colors[idx % len(colors)]
        
        spec_ref = df_ref_grouped.loc[id_].values
        spec_corr = df_corrected[df_corrected['ID'] == id_][spectral_cols].astype(float).mean().values
        
        # Referencia
        fig.add_trace(go.Scatter(
            x=channels,
            y=spec_ref,
            mode='lines',
            name=f'{lamp_ref} - {id_}',
            line=dict(width=1.5, color=color),
            opacity=0.85,
            hovertemplate=f'{lamp_ref} - {id_}<br>Canal: %{{x}}<br>Absorbancia: %{{y:.4f}}<extra></extra>'
        ))
        
        # Corregido
        fig.add_trace(go.Scatter(
            x=channels,
            y=spec_corr,
            mode='lines',
            name=f'{lamp_new} corregido - {id_}',
            line=dict(width=1.5, dash='dash', color=color),
            opacity=0.85,
            hovertemplate=f'{lamp_new} corregido - {id_}<br>Canal: %{{x}}<br>Absorbancia: %{{y:.4f}}<extra></extra>'
        ))
    
    fig.update_layout(
        title=title,
        xaxis_title='Canal espectral',
        yaxis_title='Absorbancia',
        height=700,
        hovermode='closest',
        template='plotly_white',
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=1.05
        )
    )
    
    return fig