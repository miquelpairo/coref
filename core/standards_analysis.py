# -*- coding: utf-8 -*-
"""
Standards Analysis - Shared Functions
======================================
Funciones compartidas para análisis de estándares ópticos NIR.
Usado por: Validation Standards y Offset Adjustment.

Author: Miquel
Date: December 2024
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import Dict, List, Tuple


# ============================================================================
# VALIDACIÓN Y MÉTRICAS
# ============================================================================

def validate_standard(reference: np.ndarray, current: np.ndarray, 
                     thresholds: Dict = None) -> Dict:
    """
    Valida un estándar comparando medición actual vs referencia.
    
    Args:
        reference: Espectro de referencia (array)
        current: Espectro actual (array)
        thresholds: Dict con umbrales {'correlation', 'max_diff', 'rms'} (opcional)
    
    Returns:
        Dict con métricas completas:
        {
            'correlation': float,
            'max_diff': float,
            'rms': float,
            'mean_diff': float,
            'diff': np.ndarray,
            'checks': dict (solo si thresholds proporcionado),
            'pass': bool (solo si thresholds proporcionado)
        }
    
    Examples:
        >>> ref = np.array([1.0, 1.1, 1.2])
        >>> curr = np.array([1.01, 1.11, 1.21])
        >>> result = validate_standard(ref, curr)
        >>> result['correlation']
        0.9999...
    """
    # Asegurar que son float64
    reference = np.asarray(reference, dtype=np.float64)
    current = np.asarray(current, dtype=np.float64)
    
    # 1. Correlación espectral (normalizada)
    ref_norm = (reference - np.mean(reference)) / (np.std(reference) + 1e-10)
    curr_norm = (current - np.mean(current)) / (np.std(current) + 1e-10)
    correlation = np.sum(ref_norm * curr_norm) / len(ref_norm)
    
    # 2. Diferencias
    diff = current - reference
    max_diff = np.abs(diff).max()
    rms = np.sqrt(np.mean(diff**2))
    mean_diff = np.mean(diff)
    
    result = {
        'correlation': correlation,
        'max_diff': max_diff,
        'rms': rms,
        'mean_diff': mean_diff,
        'diff': diff
    }
    
    # 3. Evaluación contra umbrales (solo si se proporcionan)
    if thresholds:
        checks = {
            'correlation': correlation >= thresholds['correlation'],
            'max_diff': max_diff <= thresholds['max_diff'],
            'rms': rms <= thresholds['rms']
        }
        result['checks'] = checks
        result['pass'] = all(checks.values())
    
    return result


def detect_spectral_shift(reference: np.ndarray, current: np.ndarray, 
                         window: int = 5) -> Tuple[bool, float]:
    """
    Detecta si hay un shift sistemático en longitud de onda.
    
    Args:
        reference: Espectro de referencia
        current: Espectro actual
        window: Ventana de píxeles para considerar shift significativo
    
    Returns:
        (tiene_shift, magnitud_promedio_shift_en_pixeles)
    
    Examples:
        >>> ref = np.array([1.0, 1.1, 1.2, 1.3, 1.4])
        >>> curr = np.array([1.3, 1.4, 1.5, 1.6, 1.7])  # shifted
        >>> has_shift, magnitude = detect_spectral_shift(ref, curr)
        >>> has_shift
        True
    """
    # Calcular correlación cruzada
    correlation = np.correlate(reference, current, mode='same')
    peak_pos = np.argmax(correlation)
    center = len(correlation) // 2
    
    shift = peak_pos - center
    
    # Si shift > window píxeles, considerarlo significativo
    has_shift = abs(shift) > window
    
    return has_shift, float(shift)


# ============================================================================
# BÚSQUEDA DE IDs COMUNES
# ============================================================================

def find_common_ids(df_ref: pd.DataFrame, df_curr: pd.DataFrame) -> pd.DataFrame:
    """
    Encuentra IDs comunes entre referencia y actual, emparejando solo por ID.
    Si hay múltiples filas con el mismo ID, toma la primera.
    
    Args:
        df_ref: DataFrame de referencia con columnas 'ID' y 'Note'
        df_curr: DataFrame actual con columnas 'ID' y 'Note'
    
    Returns:
        DataFrame con columnas: ID, ref_note, curr_note, ref_idx, curr_idx
        Devuelve DataFrame vacío si no hay coincidencias o faltan columnas.
    
    Examples:
        >>> df_ref = pd.DataFrame({'ID': [1, 2], 'Note': ['A', 'B']})
        >>> df_curr = pd.DataFrame({'ID': [2, 3], 'Note': ['B2', 'C']})
        >>> matches = find_common_ids(df_ref, df_curr)
        >>> len(matches)
        1
        >>> matches.iloc[0]['ID']
        2
    """
    # Validar que los DataFrames no están vacíos
    if len(df_ref) == 0 or len(df_curr) == 0:
        return pd.DataFrame(columns=['ID', 'ref_note', 'curr_note', 'ref_idx', 'curr_idx'])
    
    # Validar que tienen columna 'ID'
    if 'ID' not in df_ref.columns or 'ID' not in df_curr.columns:
        return pd.DataFrame(columns=['ID', 'ref_note', 'curr_note', 'ref_idx', 'curr_idx'])
    
    # Validar que tienen columna 'Note'
    if 'Note' not in df_ref.columns or 'Note' not in df_curr.columns:
        return pd.DataFrame(columns=['ID', 'ref_note', 'curr_note', 'ref_idx', 'curr_idx'])
    
    # Crear listas para almacenar los resultados
    ref_data = []
    for id_val in df_ref['ID'].unique():
        if pd.isna(id_val):  # Saltar IDs nulos
            continue
        mask = df_ref['ID'] == id_val
        indices = df_ref[mask].index
        if len(indices) > 0:
            first_idx = indices[0]
            ref_data.append({
                'ID': id_val,
                'ref_note': df_ref.loc[first_idx, 'Note'] if 'Note' in df_ref.columns else '',
                'ref_idx': first_idx
            })
    
    curr_data = []
    for id_val in df_curr['ID'].unique():
        if pd.isna(id_val):  # Saltar IDs nulos
            continue
        mask = df_curr['ID'] == id_val
        indices = df_curr[mask].index
        if len(indices) > 0:
            first_idx = indices[0]
            curr_data.append({
                'ID': id_val,
                'curr_note': df_curr.loc[first_idx, 'Note'] if 'Note' in df_curr.columns else '',
                'curr_idx': first_idx
            })
    
    # Validar que encontramos datos
    if len(ref_data) == 0 or len(curr_data) == 0:
        return pd.DataFrame(columns=['ID', 'ref_note', 'curr_note', 'ref_idx', 'curr_idx'])
    
    # Crear DataFrames
    df_ref_ids = pd.DataFrame(ref_data)
    df_curr_ids = pd.DataFrame(curr_data)
    
    # Hacer merge solo por ID
    matches = df_ref_ids.merge(df_curr_ids, on='ID', how='inner')
    
    return matches[['ID', 'ref_note', 'curr_note', 'ref_idx', 'curr_idx']]


# ============================================================================
# ANÁLISIS DE REGIONES CRÍTICAS
# ============================================================================

def analyze_critical_regions(reference: np.ndarray, current: np.ndarray,
                            regions: List[Tuple[int, int]], 
                            num_channels: int) -> pd.DataFrame:
    """
    Analiza diferencias en regiones espectrales críticas.
    Asume rango 900-1700 nm para 256 píxeles.
    
    Args:
        reference: Espectro de referencia
        current: Espectro actual
        regions: Lista de tuplas (wavelength_start, wavelength_end) en nm
        num_channels: Número total de canales espectrales
    
    Returns:
        DataFrame con columnas: Región (nm), Canales, Max |Δ|, RMS, Media Δ
    
    Examples:
        >>> ref = np.ones(256)
        >>> curr = np.ones(256) * 1.01
        >>> regions = [(1100, 1200), (1400, 1500)]
        >>> df = analyze_critical_regions(ref, curr, regions, 256)
        >>> len(df)
        2
    """
    wavelength_per_pixel = 800 / num_channels  # (1700-900)/num_channels
    start_wl = 900
    end_wl = 1700
    
    results = []
    
    for wl_start, wl_end in regions:
        # Verificar si la región está dentro del rango del instrumento
        if wl_end < start_wl or wl_start > end_wl:
            results.append({
                'Región (nm)': f"{wl_start}-{wl_end}",
                'Canales': "Fuera de rango",
                'Max |Δ|': "N/A",
                'RMS': "N/A",
                'Media Δ': "N/A"
            })
            continue
        
        # Ajustar región a los límites del instrumento
        wl_start_adjusted = max(wl_start, start_wl)
        wl_end_adjusted = min(wl_end, end_wl)
        
        # Convertir wavelength a índices de píxel
        px_start = int((wl_start_adjusted - start_wl) / wavelength_per_pixel)
        px_end = int((wl_end_adjusted - start_wl) / wavelength_per_pixel)
        
        px_start = max(0, px_start)
        px_end = min(num_channels, px_end)
        
        # Verificar que hay al menos algunos píxeles en la región
        if px_end <= px_start:
            results.append({
                'Región (nm)': f"{wl_start}-{wl_end}",
                'Canales': "Región muy pequeña",
                'Max |Δ|': "N/A",
                'RMS': "N/A",
                'Media Δ': "N/A"
            })
            continue
        
        # Extraer región
        ref_region = reference[px_start:px_end]
        curr_region = current[px_start:px_end]
        
        # Calcular métricas
        diff_region = curr_region - ref_region
        
        region_label = f"{wl_start}-{wl_end}"
        if wl_start_adjusted != wl_start or wl_end_adjusted != wl_end:
            region_label += f" *"  # Asterisco si fue ajustado
        
        results.append({
            'Región (nm)': region_label,
            'Canales': f"{px_start}-{px_end}",
            'Max |Δ|': f"{np.abs(diff_region).max():.6f}",
            'RMS': f"{np.sqrt(np.mean(diff_region**2)):.6f}",
            'Media Δ': f"{np.mean(diff_region):.6f}"
        })
    
    return pd.DataFrame(results)


# ============================================================================
# VISUALIZACIONES
# ============================================================================

def create_validation_plot(reference: np.ndarray, current: np.ndarray,
                          diff: np.ndarray, sample_label: str) -> go.Figure:
    """
    Crea gráfico de 3 paneles para validación individual.
    
    Args:
        reference: Espectro de referencia
        current: Espectro actual
        diff: Diferencia (current - reference)
        sample_label: Etiqueta de la muestra
    
    Returns:
        Figura de Plotly con 3 subplots
    """
    from plotly.subplots import make_subplots
    
    channels = list(range(1, len(reference) + 1))
    
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=(
            f'Espectros: Referencia vs Actual ({sample_label})',
            'Diferencia (Actual - Referencia)',
            'Diferencia Acumulada'
        ),
        vertical_spacing=0.1,
        row_heights=[0.4, 0.3, 0.3]
    )
    
    # Panel 1: Overlay
    fig.add_trace(
        go.Scatter(x=channels, y=reference, name='Referencia',
                  line=dict(color='blue', width=2)),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=channels, y=current, name='Actual',
                  line=dict(color='red', width=2, dash='dash')),
        row=1, col=1
    )
    
    # Panel 2: Diferencia
    fig.add_trace(
        go.Scatter(x=channels, y=diff, name='Δ',
                  line=dict(color='green', width=2),
                  fill='tozeroy', fillcolor='rgba(0,255,0,0.1)'),
        row=2, col=1
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray", 
                  opacity=0.5, row=2, col=1)
    
    # Panel 3: Diferencia acumulada
    cumsum_diff = np.cumsum(diff)
    fig.add_trace(
        go.Scatter(x=channels, y=cumsum_diff, name='Σ Δ',
                  line=dict(color='purple', width=2)),
        row=3, col=1
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray", 
                  opacity=0.5, row=3, col=1)
    
    fig.update_xaxes(title_text="Canal espectral", row=3, col=1)
    fig.update_yaxes(title_text="Absorbancia", row=1, col=1)
    fig.update_yaxes(title_text="Δ Absorbancia", row=2, col=1)
    fig.update_yaxes(title_text="Σ Δ", row=3, col=1)
    
    fig.update_layout(
        height=900,
        showlegend=True,
        template='plotly_white',
        hovermode='x unified'
    )
    
    return fig


def create_overlay_plot(validation_data: List[Dict], show_reference: bool = True,
                       show_current: bool = True) -> go.Figure:
    """
    Crea gráfico con overlay de todos los espectros de validación.
    
    Args:
        validation_data: Lista de diccionarios con datos de validación
            Cada dict debe tener: 'id', 'reference', 'current'
        show_reference: Si True, muestra espectros de referencia
        show_current: Si True, muestra espectros actuales
    
    Returns:
        Figura de Plotly con overlay
    """
    colors_ref = ['#1f77b4', '#2ca02c', '#9467bd', '#8c564b', '#e377c2', 
                  '#7f7f7f', '#bcbd22', '#17becf', '#ff9896', '#c5b0d5']
    colors_curr = ['#ff7f0e', '#d62728', '#ff69b4', '#ffa500', '#dc143c',
                   '#ff4500', '#ff1493', '#ff6347', '#ff8c00', '#ff00ff']
    
    fig = go.Figure()
    
    if len(validation_data) == 0:
        return fig
    
    channels = list(range(1, len(validation_data[0]['reference']) + 1))
    
    # Añadir espectros de referencia
    if show_reference:
        for i, data in enumerate(validation_data):
            color = colors_ref[i % len(colors_ref)]
            sample_label = f"{data['id']} - Ref"
            
            fig.add_trace(go.Scatter(
                x=channels,
                y=data['reference'],
                mode='lines',
                name=sample_label,
                line=dict(color=color, width=2),
                legendgroup='reference',
                hovertemplate=f'<b>{sample_label}</b><br>' +
                             'Canal: %{x}<br>' +
                             'Absorbancia: %{y:.6f}<br>' +
                             '<extra></extra>'
            ))
    
    # Añadir espectros actuales
    if show_current:
        for i, data in enumerate(validation_data):
            color = colors_curr[i % len(colors_curr)]
            sample_label = f"{data['id']} - Act"
            
            fig.add_trace(go.Scatter(
                x=channels,
                y=data['current'],
                mode='lines',
                name=sample_label,
                line=dict(color=color, width=2, dash='dash'),
                legendgroup='current',
                hovertemplate=f'<b>{sample_label}</b><br>' +
                             'Canal: %{x}<br>' +
                             'Absorbancia: %{y:.6f}<br>' +
                             '<extra></extra>'
            ))
    
    fig.update_layout(
        title={
            'text': 'Comparación Global de Todos los Estándares',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20, 'color': '#2c5f3f'}
        },
        xaxis_title='Canal espectral',
        yaxis_title='Absorbancia',
        hovermode='closest',
        template='plotly_white',
        height=600,
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            font=dict(size=10)
        )
    )
    
    return fig


def create_global_statistics_table(validation_data: List[Dict]) -> pd.DataFrame:
    """
    Crea tabla con estadísticas globales de todos los estándares.
    
    Args:
        validation_data: Lista de diccionarios con 'validation_results'
    
    Returns:
        DataFrame con estadísticas agregadas
    """
    if len(validation_data) == 0:
        return pd.DataFrame()
    
    # Recopilar métricas de todos los estándares
    all_correlations = []
    all_max_diffs = []
    all_rms = []
    all_mean_diffs = []
    
    for data in validation_data:
        val_res = data['validation_results']
        all_correlations.append(val_res['correlation'])
        all_max_diffs.append(val_res['max_diff'])
        all_rms.append(val_res['rms'])
        all_mean_diffs.append(val_res['mean_diff'])
    
    # Calcular estadísticas
    stats = {
        'Métrica': ['Correlación', 'Max Diferencia (AU)', 'RMS', 'Offset Medio (AU)'],
        'Mínimo': [
            f"{min(all_correlations):.6f}",
            f"{min(all_max_diffs):.6f}",
            f"{min(all_rms):.6f}",
            f"{min(all_mean_diffs):.6f}"
        ],
        'Máximo': [
            f"{max(all_correlations):.6f}",
            f"{max(all_max_diffs):.6f}",
            f"{max(all_rms):.6f}",
            f"{max(all_mean_diffs):.6f}"
        ],
        'Media': [
            f"{np.mean(all_correlations):.6f}",
            f"{np.mean(all_max_diffs):.6f}",
            f"{np.mean(all_rms):.6f}",
            f"{np.mean(all_mean_diffs):.6f}"
        ],
        'Desv. Est.': [
            f"{np.std(all_correlations):.6f}",
            f"{np.std(all_max_diffs):.6f}",
            f"{np.std(all_rms):.6f}",
            f"{np.std(all_mean_diffs):.6f}"
        ]
    }
    
    return pd.DataFrame(stats)