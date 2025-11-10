"""
Utilidades para análisis de muestras de control
"""
import pandas as pd
import numpy as np
import re
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from config import CONTROL_SAMPLES_CONFIG


_NUM_RE = re.compile(r"[-+]?\d+(?:[.,]\d+)?")

def _to_float_maybe(s: str):
    """Devuelve float si puede; si no, np.nan. Limpia >, < y soporta coma decimal."""
    if s is None:
        return np.nan
    s = str(s).strip()
    if not s or s.lower() == "nan":
        return np.nan
    # quita símbolos tipo '>' '<'
    s = s.replace(">", "").replace("<", "").strip()
    # intenta regex por si hay texto alrededor
    m = _NUM_RE.search(s)
    if not m:
        return np.nan
    val = m.group(0).replace(",", ".")
    try:
        return float(val)
    except ValueError:
        return np.nan

def extract_predictions_from_results(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extrae predicciones de la columna 'Result' o 'Results' cuando los valores
    vienen sin nombre, p. ej.:  '>19.9 ; 13.6 ; 16.6 ; 2.6 ; 4.3 ; 5.000 ; >19.9 ; >89.0 ; ...'
    Asigna columnas Param1, Param2, ... según posición.
    """
    # detecta columna válida
    result_col = next((c for c in ("Result", "Results") if c in df.columns), None)
    if result_col is None:
        return pd.DataFrame()

    out = []
    max_params = 0

    for _, row in df.iterrows():
        results_str = str(row.get(result_col, "")).strip()
        rec = {"ID": row.get("ID", None)}

        # separa por ';' y también por ','
        raw_parts = []
        for chunk in results_str.split(";"):
            raw_parts.extend(chunk.split(","))

        # limpia y convierte
        values = []
        for part in raw_parts:
            part = part.strip()
            if not part:
                continue
            values.append(_to_float_maybe(part))

        # asigna Param1..ParamN
        for i, val in enumerate(values, start=1):
            rec[f"Param{i}"] = val

        max_params = max(max_params, len(values))
        out.append(rec)

    # construye DataFrame; pandas alinea claves y rellena faltantes con NaN
    pred_df = pd.DataFrame(out)

    # asegura columnas Param1..ParamN en orden
    param_cols = [f"Param{i}" for i in range(1, max_params + 1)]
    ordered_cols = ["ID"] + param_cols
    for c in param_cols:
        if c not in pred_df.columns:
            pred_df[c] = np.nan
    pred_df = pred_df[ordered_cols]

    return pred_df

_PARAM_RE = re.compile(r"^Param(\d+)$")

def get_prediction_parameters(df: pd.DataFrame) -> list:
    if df is None or df.empty:
        return []
    params = []
    for c in df.columns:
        m = _PARAM_RE.match(str(c))
        if m:
            params.append((int(m.group(1)), str(c)))
    params.sort(key=lambda x: x[0])
    return [c for _, c in params]

def compare_predictions(df_initial: pd.DataFrame,
                        df_final: pd.DataFrame,
                        common_ids: list,
                        df_original_initial: pd.DataFrame = None,  # ⭐ NUEVO
                        df_original_final: pd.DataFrame = None) -> pd.DataFrame:  # ⭐ NUEVO
    """
    Compara predicciones usando merges por ID, param a param.
    Devuelve un DF ancho con columnas:
      ID, Recipe, Param1_initial, Param1_final, Param1_diff, Param1_diff_pct, ...
    """
    if df_initial is None or df_final is None or not len(common_ids):
        return pd.DataFrame()

    # Normaliza ID a str y recorta espacios
    df_initial = df_initial.copy()
    df_final   = df_final.copy()
    df_initial['ID'] = df_initial['ID'].astype(str).str.strip()
    df_final['ID']   = df_final['ID'].astype(str).str.strip()
    common_ids = [str(x).strip() for x in common_ids]

    # Filtra solo IDs comunes
    ini = df_initial[df_initial['ID'].isin(common_ids)].copy()
    fin = df_final[df_final['ID'].isin(common_ids)].copy()

    # Asegura solo una fila por ID
    ini = ini.drop_duplicates(subset=['ID'], keep='first')
    fin = fin.drop_duplicates(subset=['ID'], keep='first')

    # Detecta parámetros en orden
    p_ini = get_prediction_parameters(ini)
    p_fin = get_prediction_parameters(fin)
    common_params = [p for p in p_ini if p in p_fin]
    if not common_params:
        return pd.DataFrame()

    # Fuerza numérico
    for col in common_params:
        ini[col] = pd.to_numeric(ini[col], errors='coerce')
        fin[col] = pd.to_numeric(fin[col], errors='coerce')

    # Base con IDs comunes
    base = pd.DataFrame({'ID': common_ids})
    base = base.merge(ini[['ID']], on='ID', how='inner')
    
    # ⭐ NUEVO: Añadir Recipe desde los DataFrames originales si existen
    if df_original_initial is not None and 'Recipe' in df_original_initial.columns:
        df_original_initial = df_original_initial.copy()
        df_original_initial['ID'] = df_original_initial['ID'].astype(str).str.strip()
        recipe_col = df_original_initial[['ID', 'Recipe']].drop_duplicates(subset=['ID'])
        base = base.merge(recipe_col, on='ID', how='left')
    elif df_original_final is not None and 'Recipe' in df_original_final.columns:
        df_original_final = df_original_final.copy()
        df_original_final['ID'] = df_original_final['ID'].astype(str).str.strip()
        recipe_col = df_original_final[['ID', 'Recipe']].drop_duplicates(subset=['ID'])
        base = base.merge(recipe_col, on='ID', how='left')

    # Para cada parámetro, mergea inicial y final y calcula difs
    out = base.copy()
    for p in common_params:
        a = ini[['ID', p]].rename(columns={p: f'{p}_initial'})
        b = fin[['ID', p]].rename(columns={p: f'{p}_final'})
        out = out.merge(a, on='ID', how='left')
        out = out.merge(b, on='ID', how='left')

        # difs
        out[f'{p}_diff'] = out[f'{p}_final'] - out[f'{p}_initial']
        out[f'{p}_diff_pct'] = np.where(
            out[f'{p}_initial'].abs() > 1e-6,
            (out[f'{p}_diff'] / out[f'{p}_initial']) * 100.0,
            np.nan
        )

    return out

def get_prediction_status(diff_pct):
    """
    Determina el estado de la predicción basado en la diferencia porcentual.
    
    Args:
        diff_pct (float): Diferencia porcentual
        
    Returns:
        str: 'good', 'warning', o 'bad'
    """
    abs_diff = abs(diff_pct)
    
    if np.isnan(abs_diff):
        return 'warning'
    
    if abs_diff < CONTROL_SAMPLES_CONFIG['prediction_tolerance']['good']:
        return 'good'
    elif abs_diff < CONTROL_SAMPLES_CONFIG['prediction_tolerance']['warning']:
        return 'warning'
    else:
        return 'bad'


def plot_spectra_comparison(df_initial, df_final, spectral_cols, common_ids):
    """
    Genera un gráfico comparativo de espectros iniciales vs finales.
    
    Args:
        df_initial (pd.DataFrame): Mediciones iniciales
        df_final (pd.DataFrame): Mediciones finales
        spectral_cols (list): Columnas espectrales
        common_ids (list): IDs comunes para comparar
        
    Returns:
        plotly.graph_objects.Figure: Gráfico interactivo
    """
    # Crear subplots: uno para espectros, otro para diferencias
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(
            'Espectros - Inicial (antes) vs Final (después del ajuste)',
            'Diferencias espectrales (Final - Inicial)'
        ),
        vertical_spacing=0.12,
        row_heights=[0.6, 0.4]
    )
    
    channels = list(range(1, len(spectral_cols) + 1))
    colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']
    
    for i, sample_id in enumerate(common_ids):
        color = colors[i % len(colors)]
        
        # Espectro inicial
        initial_row = df_initial[df_initial['ID'] == sample_id]
        if not initial_row.empty:
            spectrum_initial = initial_row[spectral_cols].values[0]
            
            fig.add_trace(
                go.Scatter(
                    x=channels,
                    y=spectrum_initial,
                    mode='lines',
                    name=f'{sample_id} (Inicial)',
                    line=dict(color=color, width=2, dash='dash'),
                    hovertemplate=f'{sample_id} (Inicial)<br>Canal: %{{x}}<br>Valor: %{{y:.6f}}<extra></extra>',
                    legendgroup=sample_id
                ),
                row=1, col=1
            )
        
        # Espectro final
        final_row = df_final[df_final['ID'] == sample_id]
        if not final_row.empty:
            spectrum_final = final_row[spectral_cols].values[0]
            
            fig.add_trace(
                go.Scatter(
                    x=channels,
                    y=spectrum_final,
                    mode='lines',
                    name=f'{sample_id} (Final)',
                    line=dict(color=color, width=2),
                    hovertemplate=f'{sample_id} (Final)<br>Canal: %{{x}}<br>Valor: %{{y:.6f}}<extra></extra>',
                    legendgroup=sample_id
                ),
                row=1, col=1
            )
            
            # Diferencia
            if not initial_row.empty:
                diff = spectrum_final - spectrum_initial
                
                fig.add_trace(
                    go.Scatter(
                        x=channels,
                        y=diff,
                        mode='lines',
                        name=f'{sample_id} (Δ)',
                        line=dict(color=color, width=1.5),
                        hovertemplate=f'{sample_id} (Diferencia)<br>Canal: %{{x}}<br>Δ: %{{y:.6f}}<extra></extra>',
                        legendgroup=sample_id,
                        showlegend=False
                    ),
                    row=2, col=1
                )
    
    # Línea de referencia en y=0 para el subplot de diferencias
    fig.add_hline(
        y=0, 
        line_dash="dash", 
        line_color="gray", 
        opacity=0.5,
        row=2, col=1
    )
    
    # Layout
    fig.update_xaxes(title_text="Canal espectral", row=1, col=1)
    fig.update_xaxes(title_text="Canal espectral", row=2, col=1)
    fig.update_yaxes(title_text="Valor espectral", row=1, col=1)
    fig.update_yaxes(title_text="Diferencia", row=2, col=1)
    
    fig.update_layout(
        height=900,
        showlegend=True,
        hovermode='closest',
        template='plotly_white',
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        )
    )
    
    return fig


def plot_predictions_comparison(comparison_df, parameters):
    """
    Genera un gráfico de barras comparando predicciones iniciales vs finales.
    
    Args:
        comparison_df (pd.DataFrame): DataFrame con comparación de predicciones
        parameters (list): Lista de parámetros a graficar
        
    Returns:
        plotly.graph_objects.Figure: Gráfico interactivo
    """
    # Determinar el número de subplots necesarios
    n_params = len(parameters)
    
    if n_params == 0:
        return None
    
    # Crear subplots (máximo 3 columnas)
    n_cols = min(3, n_params)
    n_rows = (n_params + n_cols - 1) // n_cols
    
    fig = make_subplots(
        rows=n_rows,
        cols=n_cols,
        subplot_titles=[f'{param}' for param in parameters],
        vertical_spacing=0.15,
        horizontal_spacing=0.12
    )
    
    for idx, param in enumerate(parameters):
        row = idx // n_cols + 1
        col = idx % n_cols + 1
        
        col_initial = f'{param}_initial'
        col_final = f'{param}_final'
        
        if col_initial not in comparison_df.columns or col_final not in comparison_df.columns:
            continue
        
        sample_ids = comparison_df['ID'].tolist()
        values_initial = comparison_df[col_initial].tolist()
        values_final = comparison_df[col_final].tolist()
        
        # Barras para valores iniciales
        fig.add_trace(
            go.Bar(
                x=sample_ids,
                y=values_initial,
                name='Inicial',
                marker_color='lightblue',
                showlegend=(idx == 0),  # Solo mostrar leyenda una vez
                hovertemplate='%{x}<br>Inicial: %{y:.2f}<extra></extra>'
            ),
            row=row, col=col
        )
        
        # Barras para valores finales
        fig.add_trace(
            go.Bar(
                x=sample_ids,
                y=values_final,
                name='Final',
                marker_color='darkblue',
                showlegend=(idx == 0),
                hovertemplate='%{x}<br>Final: %{y:.2f}<extra></extra>'
            ),
            row=row, col=col
        )
        
        # Actualizar ejes
        fig.update_xaxes(tickangle=-45, row=row, col=col)
    
    # Layout general
    fig.update_layout(
        height=400 * n_rows,
        showlegend=True,
        template='plotly_white',
        barmode='group'
    )
    
    return fig


def calculate_spectral_metrics(df_initial, df_final, spectral_cols, common_ids):
    """
    Calcula métricas espectrales para evaluar la mejora.
    
    Args:
        df_initial (pd.DataFrame): Mediciones iniciales
        df_final (pd.DataFrame): Mediciones finales
        spectral_cols (list): Columnas espectrales
        common_ids (list): IDs comunes
        
    Returns:
        dict: Diccionario con métricas
    """
    metrics = {}
    
    for sample_id in common_ids:
        initial_row = df_initial[df_initial['ID'] == sample_id]
        final_row = df_final[df_final['ID'] == sample_id]
        
        if initial_row.empty or final_row.empty:
            continue
        
        spectrum_initial = initial_row[spectral_cols].values[0]
        spectrum_final = final_row[spectral_cols].values[0]
        
        # Calcular diferencia
        diff = spectrum_final - spectrum_initial
        
        # Métricas
        metrics[sample_id] = {
            'mean_diff': np.mean(diff),
            'std_diff': np.std(diff),
            'max_diff': np.max(np.abs(diff)),
            'rmse': np.sqrt(np.mean(diff**2)),
            'correlation': np.corrcoef(spectrum_initial, spectrum_final)[0, 1]
        }
    
    return metrics