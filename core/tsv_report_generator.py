"""
TSV Validation Reports - HTML Report Generator
===============================================
Funciones para generar reportes HTML con grupos personalizados
ACTUALIZADO: Leyendas en gráfico de espectros + Estadísticas por Grupo + Filtro Visual por Año/Mes/ID/Note
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import re
import json

import pandas as pd
import plotly.graph_objs as go
import numpy as np
from sklearn.metrics import mean_squared_error, r2_score

from core.report_utils import load_buchi_css, get_sidebar_styles, get_common_report_styles
from core.tsv_statistics import calculate_all_groups_statistics


@dataclass
class ReportResult:
    name: str
    html: str
    csv: pd.DataFrame


def _is_pixel_col(col: str, PIXEL_RE) -> bool:
    return bool(PIXEL_RE.fullmatch(str(col)))


def _safe_html_id(s: str) -> str:
    s = s.strip()
    s = s.replace(" ", "-").replace("/", "-").replace("\\", "-")
    s = re.sub(r"[^a-zA-Z0-9\-_]", "", s)
    return s or "param"


def create_layout(title: str, xaxis_title: str, yaxis_title: str) -> Dict:
    """Layout estándar para gráficos (leyenda debajo y centrada)"""
    return {
        "title": title,
        "xaxis_title": xaxis_title,
        "yaxis_title": yaxis_title,
        "showlegend": True,
        "height": 550,
        "dragmode": "zoom",
        "hovermode": "closest",
        "template": "plotly",
        "plot_bgcolor": "#E5ECF6",
        "paper_bgcolor": "white",
        "xaxis": {"gridcolor": "white"},
        "yaxis": {"gridcolor": "white"},
        "autosize": True,
        # Leyenda debajo y centrada
        "legend": {
            "orientation": "h",
            "x": 0.5,
            "y": -0.25,
            "xanchor": "center",
            "yanchor": "top",
        },
        # margen inferior suficiente para la leyenda
        "margin": {"l": 60, "r": 40, "t": 80, "b": 140},
    }


def plot_comparison_for_report(
    df: pd.DataFrame,
    result_col: str,
    reference_col: str,
    residuum_col: str,
    sample_groups: Dict[int, str] = None,
    group_labels: Dict[str, str] = None,
    SAMPLE_GROUPS: Dict = None
):
    """Versión para reportes finales CON soporte de grupos"""
    if sample_groups is None:
        sample_groups = {}
    if group_labels is None:
        group_labels = {}
    
    try:
        valid_mask = (
            df[reference_col].notna()
            & df[result_col].notna()
            & (df[reference_col] != 0)
            & (df[result_col] != 0)
        )

        x = df.loc[valid_mask, reference_col]
        y = df.loc[valid_mask, result_col]

        residuum_series = pd.to_numeric(df.loc[valid_mask, residuum_col], errors="coerce")
        aligned_mask = residuum_series.notna()

        x = x.loc[aligned_mask]
        y = y.loc[aligned_mask]
        residuum = residuum_series.loc[aligned_mask]

        if len(x) < 2 or len(y) < 2:
            return None

        original_indices = df.loc[valid_mask].loc[aligned_mask].index.tolist()

        hover_id = df.loc[valid_mask, "ID"] if "ID" in df.columns else pd.Series(range(len(valid_mask)))
        hover_date = df.loc[valid_mask, "Date"] if "Date" in df.columns else pd.Series([""] * len(valid_mask))
        hover_id = hover_id.loc[aligned_mask]
        hover_date = hover_date.loc[aligned_mask]

        r2 = float(r2_score(x, y))
        rmse = float(np.sqrt(mean_squared_error(x, y)))
        bias = float(np.mean(y - x))
        n = int(len(x))

        # Clasificar puntos por grupo
        points_by_group = {group: [] for group in SAMPLE_GROUPS.keys()}
        
        for i, idx in enumerate(original_indices):
            group = sample_groups.get(idx, 'none')
            points_by_group[group].append(i)

        # Parity plot CON GRUPOS
        fig_parity = go.Figure()
        
        for group_name, group_config in SAMPLE_GROUPS.items():
            if group_name == 'none':
                continue
            
            indices = points_by_group.get(group_name, [])
            if indices:
                custom_label = group_labels.get(group_name, group_name)
                display_label = f"{group_config['emoji']} {custom_label}"
                
                x_group = x.iloc[indices]
                y_group = y.iloc[indices]
                hovertext_group = [
                    f"{display_label}<br>Date: {hover_date.iloc[i]}<br>ID: {hover_id.iloc[i]}<br>Reference: {x.iloc[i]:.2f}<br>Result: {y.iloc[i]:.2f}"
                    for i in indices
                ]
                fig_parity.add_trace(go.Scatter(
                    x=x_group,
                    y=y_group,
                    mode="markers",
                    marker=dict(
                        color=group_config['color'],
                        size=group_config['size'],
                        symbol=group_config['symbol']
                    ),
                    hovertext=hovertext_group,
                    hoverinfo="text",
                    name=display_label
                ))
        
        # Puntos 'none'
        indices = points_by_group.get('none', [])
        if indices:
            group_config = SAMPLE_GROUPS['none']
            x_group = x.iloc[indices]
            y_group = y.iloc[indices]
            hovertext_group = [
                f"Date: {hover_date.iloc[i]}<br>ID: {hover_id.iloc[i]}<br>Reference: {x.iloc[i]:.2f}<br>Result: {y.iloc[i]:.2f}"
                for i in indices
            ]
            fig_parity.add_trace(go.Scatter(
                x=x_group,
                y=y_group,
                mode="markers",
                marker=dict(
                    color=group_config['color'],
                    size=group_config['size'],
                    symbol=group_config['symbol']
                ),
                hovertext=hovertext_group,
                hoverinfo="text",
                name="Sin set",
                showlegend=True
            ))
        
        # Líneas de referencia
        fig_parity.add_trace(go.Scatter(x=x, y=x, mode="lines", line=dict(dash="dash", color="gray"), name="y = x", showlegend=False))
        fig_parity.add_trace(go.Scatter(x=x, y=x + rmse, mode="lines", line=dict(dash="dash", color="red"), name="RMSE", showlegend=False))
        fig_parity.add_trace(go.Scatter(x=x, y=x - rmse, mode="lines", line=dict(dash="dash", color="red"), showlegend=False))
        fig_parity.update_layout(**create_layout("Parity Plot", reference_col, result_col))

        # Residuum vs N - ORDENADO POR FECHA CON COLORES DE GRUPOS
        if "Date" in df.columns:
            date_col = df.loc[valid_mask, "Date"].loc[aligned_mask]
            sort_indices = date_col.argsort()
            
            residuum = residuum.iloc[sort_indices]
            hover_id = hover_id.iloc[sort_indices]
            hover_date = hover_date.iloc[sort_indices]
            original_indices = [original_indices[i] for i in sort_indices]

        # En lugar de un solo Bar trace, crear traces por grupo
        fig_res = go.Figure()

        # Agrupar barras por grupo para la leyenda
        bars_by_group = {group: {'x': [], 'y': [], 'hovertext': []} for group in SAMPLE_GROUPS.keys()}

        for i, idx in enumerate(original_indices):
            group = sample_groups.get(idx, 'none')
            bars_by_group[group]['x'].append(i)
            bars_by_group[group]['y'].append(residuum.iloc[i])
            bars_by_group[group]['hovertext'].append(
                f"Date: {hover_date.iloc[i]}<br>ID: {hover_id.iloc[i]}<br>Residuum: {residuum.iloc[i]:.2f}"
            )

        # Agregar traces por grupo
        for group_name, group_config in SAMPLE_GROUPS.items():
            if bars_by_group[group_name]['x']:  # Solo si hay barras de este grupo
                if group_name == 'none':
                    label = "Sin set"
                    showlegend = True
                else:
                    custom_label = group_labels.get(group_name, group_name)
                    label = f"{group_config['emoji']} {custom_label}"
                    showlegend = True
                
                fig_res.add_trace(go.Bar(
                    x=bars_by_group[group_name]['x'],
                    y=bars_by_group[group_name]['y'],
                    hovertext=bars_by_group[group_name]['hovertext'],
                    hoverinfo="text",
                    name=label,
                    marker=dict(color=group_config['color']),
                    showlegend=showlegend
                ))

        fig_res.update_layout(**create_layout("Residuum vs N (ordenado por fecha)", "N", "Residuum"))

        # Histograma
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Histogram(x=residuum, nbinsx=20, marker=dict(color="blue")))
        layout_hist = create_layout("Residuum Histogram", "Residuum", "Count")
        layout_hist["showlegend"] = False  
        fig_hist.update_layout(**layout_hist)

        return fig_parity, fig_res, fig_hist, r2, rmse, bias, n

    except Exception:
        return None


def build_spectra_figure_for_report(
    df: pd.DataFrame,
    sample_groups: Dict[int, str] = None,
    group_labels: Dict[str, str] = None,
    SAMPLE_GROUPS: Dict = None,
    PIXEL_RE = None
) -> Optional[go.Figure]:
    """
    Genera espectros para reporte
    ACTUALIZADO: Muestra leyenda de grupos
    """
    if sample_groups is None:
        sample_groups = {}
    if group_labels is None:
        group_labels = {}
    
    pixel_cols = [c for c in df.columns if _is_pixel_col(c, PIXEL_RE)]
    if not pixel_cols:
        return None

    pixel_cols = sorted(pixel_cols, key=lambda s: int(str(s)[1:]))
    x = [int(str(c)[1:]) for c in pixel_cols]

    spec = (
        df[pixel_cols]
        .replace(",", ".", regex=True)
        .apply(pd.to_numeric, errors="coerce")
    )

    hover_id = df["ID"].astype(str) if "ID" in df.columns else pd.Series([str(i) for i in range(len(df))])
    hover_date = df["Date"].astype(str) if "Date" in df.columns else pd.Series([""] * len(df))
    hover_note = df["Note"].astype(str) if "Note" in df.columns else pd.Series([""] * len(df))

    fig = go.Figure()
    
    # Track which groups have been added to legend
    legend_added = set()

    for i in range(len(df)):
        y = spec.iloc[i].to_numpy()

        if np.all(np.isnan(y)):
            continue

        group = sample_groups.get(i, 'none')
        group_config = SAMPLE_GROUPS[group]
        color = group_config['color']
        opacity = 0.5 if group != 'none' else 0.35
        width = 2 if group != 'none' else 1
        legend_group = group

        if group != 'none':
            custom_label = group_labels.get(group, group)
            prefix = f"{group_config['emoji']} {custom_label} - "
            legend_name = f"{group_config['emoji']} {custom_label}"
        else:
            prefix = ""
            legend_name = "Sin set"
        
        # Show legend only for the first trace of each group
        show_legend = legend_group not in legend_added
        if show_legend:
            legend_added.add(legend_group)

        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode="lines",
                showlegend=show_legend,
                legendgroup=legend_group,
                name=legend_name,
                line={"width": width, "color": color},
                opacity=opacity,
                hovertemplate=(
                    f"{prefix}ID: {hover_id.iloc[i]}<br>"
                    f"Date: {hover_date.iloc[i]}<br>"
                    f"Note: {hover_note.iloc[i]}<br>"
                    "Pixel: %{x}<br>"
                    "Abs: %{y}<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title="Spectra",
        xaxis_title="Pixel",
        yaxis_title="Absorbance (AU)",
        autosize=True,
        height=700,
        hovermode="closest",
        template="plotly",
        plot_bgcolor="#E5ECF6",
        paper_bgcolor="white",
        xaxis={"gridcolor": "white"},
        yaxis={"gridcolor": "white"},
        showlegend=True
    )
    return fig


def generate_html_report(
    df: pd.DataFrame,
    file_name: str,
    sample_groups: Dict[int, str] = None,
    group_labels: Dict[str, str] = None,
    group_descriptions: Dict[str, str] = None,
    SAMPLE_GROUPS: Dict = None,
    PIXEL_RE = None
) -> str:
    """
    Genera HTML con Bootstrap tabs + sidebar BUCHI + CSS corporativo + GRUPOS + ESTADÍSTICAS POR GRUPO + FILTRO VISUAL (Año/Mes/ID/Note).
    """
    if sample_groups is None:
        sample_groups = {}
    if group_labels is None:
        group_labels = {}
    if group_descriptions is None:
        group_descriptions = {}
    
    columns_result = [c for c in df.columns if str(c).startswith("Result ")]
    columns_reference = [c.replace("Result ", "Reference ") for c in columns_result]
    columns_residuum = [c.replace("Result ", "Residuum ") for c in columns_result]

    summary_data: List[Dict] = []
    fig_spectra = build_spectra_figure_for_report(df, sample_groups, group_labels, SAMPLE_GROUPS, PIXEL_RE)
    plotly_already_included = False

    def _fig_html(fig: go.Figure) -> str:
        nonlocal plotly_already_included
        include_js = "inline" if not plotly_already_included else False
        html = fig.to_html(full_html=False, include_plotlyjs=include_js)
        plotly_already_included = True
        return html

    # Build valid params list
    valid_params: List[Tuple[str, str, Tuple]] = []
    for result_col, reference_col, residuum_col in zip(columns_result, columns_reference, columns_residuum):
        param_name = str(result_col).replace("Result ", "")
        param_id = _safe_html_id(param_name)
        plots = plot_comparison_for_report(df, result_col, reference_col, residuum_col, sample_groups, group_labels, SAMPLE_GROUPS)
        if plots:
            valid_params.append((param_name, param_id, plots))
            fig_parity, fig_res, fig_hist, r2, rmse, bias, n = plots
            summary_data.append({"Parameter": param_name, "R2": r2, "RMSE": rmse, "BIAS": bias, "N": n})

    # Verificar si hay grupos asignados
    has_groups = any(g != 'none' for g in sample_groups.values())
    
    # Extraer años y meses disponibles
    available_years = []
    available_months = list(range(1, 13))
    if 'Date' in df.columns:
        df_temp = df.copy()
        df_temp['Date'] = pd.to_datetime(df_temp['Date'], errors='coerce')
        available_years = sorted(df_temp['Date'].dt.year.dropna().unique().astype(int).tolist())

    # Embed full data as JSON for filtering
    df_export = df.copy()
    if 'Date' in df_export.columns:
        df_export['Date'] = pd.to_datetime(df_export['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
    full_data_json = df_export.to_json(orient='records')
    
    # Convert sample_groups keys to strings for JSON (numpy.int64 -> int -> str)
    sample_groups_json = {str(int(k)) if isinstance(k, (int, np.integer)) else str(k): v 
                          for k, v in sample_groups.items()}

    # Construcción del SIDEBAR
    sidebar_items = """
        <h2>📋 Índice</h2>
        <ul>
            <li><a href="#info-general">Información General</a></li>
            <li><a href="#summary-stats">Resumen Estadístico</a></li>
    """
    
    if fig_spectra:
        sidebar_items += '<li><a href="#spectra-section">Espectros</a></li>\n'
    
    if valid_params:
        sidebar_items += '''
            <li>
                <details class="sidebar-menu-details">
                    <summary>Análisis por Parámetro</summary>
                    <ul style="padding-left: 15px; margin-top: 5px;">
'''
        for param_name, param_id, _ in valid_params:
            onclick_code = f"$('#tab-{param_id}').tab('show'); document.getElementById('tabs-section').scrollIntoView({{behavior: 'smooth'}}); return false;"
            sidebar_items += f'                        <li><a href="#" onclick="{onclick_code}">{param_name}</a></li>\n'
        
        sidebar_items += '''
                    </ul>
                </details>
            </li>
'''
    
    # Agregar sección de grupos al sidebar si existen
    if has_groups:
        sidebar_items += '<li><a href="#grupos-section">Grupos</a></li>\n'
    
    sidebar_items += '''
        </ul>
'''
    
    # Agregar filtro visual al sidebar
    if available_years:
        sidebar_items += '''
        <div style="padding: 20px; border-top: 2px solid rgba(255,255,255,0.1); margin-top: 20px;">
            <details class="sidebar-menu-details">
                <summary style="cursor: pointer; font-weight: bold; color: white; padding: 8px 0; user-select: none; list-style: none;">
                    📅 Filtro Visual
                </summary>
                <div style="margin-top: 10px;">
                    <p style="color: rgba(255,255,255,0.7); font-size: 0.85rem; margin-bottom: 10px;">Solo afecta visualización</p>
                    
                    <div style="margin-bottom: 15px;">
                        <label style="color: white; font-size: 0.9rem; display: block; margin-bottom: 8px;">📅 Años</label>
                        <div id="yearFilters" style="display: flex; flex-direction: column; gap: 5px;"></div>
                    </div>
                    
                    <div style="margin-bottom: 15px;">
                        <label style="color: white; font-size: 0.9rem; display: block; margin-bottom: 8px;">📆 Meses (vacío = todos)</label>
                        <div id="monthFilters" style="display: flex; flex-direction: column; gap: 5px; max-height: 150px; overflow-y: auto;"></div>
                    </div>
                    
                    <div style="margin-bottom: 15px;">
                        <label style="color: white; font-size: 0.9rem; display: block; margin-bottom: 8px;">🔍 ID (contains)</label>
                        <input type="text" id="idFilter" placeholder="e.g., 'ABC123'" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px;">
                    </div>
                    
                    <div style="margin-bottom: 15px;">
                        <label style="color: white; font-size: 0.9rem; display: block; margin-bottom: 8px;">📝 Note (contains)</label>
                        <input type="text" id="noteFilter" placeholder="e.g., 'validation'" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px;">
                    </div>
                    
                    <button onclick="applyVisualFilter()" style="background: #28a745; color: white; padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; font-size: 14px; font-weight: bold; width: 100%; margin-bottom: 10px; transition: all 0.2s;">
                        🔄 Aplicar Filtros
                    </button>
                    
                    <button onclick="resetVisualFilter()" style="background: #666; color: white; padding: 8px 15px; border: none; border-radius: 5px; cursor: pointer; font-size: 13px; width: 100%;">
                        ↩️ Resetear
                    </button>
                    
                    <p id="filterIndicator" style="color: rgba(255,255,255,0.8); font-size: 0.85rem; margin-top: 10px; text-align: center;"></p>
                </div>
            </details>
        </div>
'''

    # Cargar CSS BUCHI
    buchi_css = load_buchi_css()
    sidebar_css = get_sidebar_styles()
    common_css = get_common_report_styles()

    # HTML COMPLETO
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    year = datetime.now().year
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Validation Report - {file_name}</title>

    <!-- Bootstrap CSS -->
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">

    <!-- jQuery -->
    <script src="https://code.jquery.com/jquery-3.5.1.js"></script>

    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/popper.js@1.16.1/dist/umd/popper.min.js"></script>
    <script src="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js"></script>

    <style>
{buchi_css}
{sidebar_css}
{common_css}

        /* Scrollbar sutil para filtros */
        #monthFilters::-webkit-scrollbar {{
            width: 6px;
        }}
        
        #monthFilters::-webkit-scrollbar-track {{
            background: transparent;
        }}
        
        #monthFilters::-webkit-scrollbar-thumb {{
            background-color: rgba(255, 255, 255, 0.3);
            border-radius: 3px;
        }}
        
        #monthFilters::-webkit-scrollbar-thumb:hover {{
            background-color: rgba(255, 255, 255, 0.5);
        }}
        
        /* Estilos para checkboxes de filtro */
        .filter-checkbox-label {{
            display: flex;
            align-items: center;
            color: white;
            font-size: 0.85rem;
            cursor: pointer;
            padding: 3px 5px;
            border-radius: 3px;
            transition: background-color 0.2s;
        }}
        
        .filter-checkbox-label:hover {{
            background-color: rgba(255, 255, 255, 0.1);
        }}
        
        .filter-checkbox-label input {{
            margin-right: 8px;
            cursor: pointer;
        }}
    </style>
</head>
<body>
    <!-- SIDEBAR -->
    <div class="sidebar">
{sidebar_items}
    </div>

    <!-- MAIN CONTENT -->
    <div class="main-content">
        <h1>Validation Report</h1>
        
        <!-- INFO GENERAL -->
        <div class="info-box" id="info-general">
            <h2>Información General</h2>
            <table>
                <tr>
                    <th>Archivo</th>
                    <td>{file_name}</td>
                </tr>
                <tr>
                    <th>Fecha de generación</th>
                    <td>{timestamp}</td>
                </tr>
                <tr>
                    <th>Número de muestras</th>
                    <td>{len(df)}</td>
                </tr>
                <tr>
                    <th>Parámetros analizados</th>
                    <td>{len(valid_params)}</td>
                </tr>
            </table>
            <p class="text-caption">
                <em>Este informe analiza valores predichos vs referencia usando métricas estadísticas (R², RMSE, BIAS).</em>
            </p>
        </div>

        <!-- SUMMARY STATS -->
        <div class="info-box" id="summary-stats">
            <h2>Resumen Estadístico</h2>
            <table class="summary-table">
                <thead>
                    <tr>
                        <th>Parámetro</th>
"""

    for row in summary_data:
        html_content += f"<th>{row['Parameter']}</th>"

    html_content += """
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>R²</strong></td>
"""
    for row in summary_data:
        html_content += f"<td>{row['R2']:.3f}</td>"

    html_content += """
                    </tr>
                    <tr>
                        <td><strong>RMSE</strong></td>
"""
    for row in summary_data:
        html_content += f"<td>{row['RMSE']:.3f}</td>"

    html_content += """
                    </tr>
                    <tr>
                        <td><strong>BIAS</strong></td>
"""
    for row in summary_data:
        html_content += f"<td>{row['BIAS']:.3f}</td>"

    html_content += """
                    </tr>
                    <tr>
                        <td><strong>N</strong></td>
"""
    for row in summary_data:
        html_content += f"<td>{row['N']}</td>"

    html_content += """
                    </tr>
                </tbody>
            </table>
        </div>
"""

    # SPECTRA
    if fig_spectra is not None:
        spectra_html = _fig_html(fig_spectra) if not plotly_already_included else fig_spectra.to_html(full_html=False, include_plotlyjs=False)
        html_content += f"""
        <div class="info-box" id="spectra-section">
            <h2>Espectros</h2>
            <p class="text-caption">
                <em>Overlay de todos los espectros NIR (columnas #1..#n). Los espectros coloreados pertenecen a grupos personalizados.</em>
            </p>
            <div class="plot-container">
                {spectra_html}
            </div>
        </div>
"""

    # TABS POR PARÁMETRO
    if valid_params:
        html_content += """
        <div class="info-box" id="tabs-section">
            <h2>Análisis por Parámetro</h2>
            <p class="text-caption">
                <em>Gráficos interactivos (Parity, Residuum vs N, Histograma) para cada parámetro. Los símbolos indican grupos de muestras.</em>
            </p>
            
            <ul class="nav nav-tabs" id="myTab" role="tablist">
"""

        first_tab = True
        for param_name, param_id, _ in valid_params:
            active_class = "active" if first_tab else ""
            first_tab = False
            html_content += f"""
                <li class="nav-item">
                    <a class="nav-link {active_class}" id="tab-{param_id}" data-toggle="tab"
                       href="#content-{param_id}" role="tab">{param_name}</a>
                </li>
"""

        html_content += """
            </ul>
            
            <div class="tab-content" id="myTabContent">
"""

        first_tab = True
        for param_name, param_id, plots in valid_params:
            fig_parity, fig_residuum, fig_histogram, r2, rmse, bias, n = plots
            active_class = "show active" if first_tab else ""
            first_tab = False

            fig_parity_html = _fig_html(fig_parity) if not plotly_already_included else fig_parity.to_html(full_html=False, include_plotlyjs=False)
            fig_residuum_html = fig_residuum.to_html(full_html=False, include_plotlyjs=False)
            fig_histogram_html = fig_histogram.to_html(full_html=False, include_plotlyjs=False)

            html_content += f"""
                <div class="tab-pane fade {active_class}" id="content-{param_id}" role="tabpanel">
                    <div class="stats-box">
                        <table>
                            <tr>
                                <td><strong>R²</strong></td>
                                <td><strong>RMSE</strong></td>
                                <td><strong>BIAS</strong></td>
                                <td><strong>N</strong></td>
                            </tr>
                            <tr>
                                <td>{r2:.3f}</td>
                                <td>{rmse:.3f}</td>
                                <td>{bias:.3f}</td>
                                <td>{n}</td>
                            </tr>
                        </table>
                    </div>

                    <div id="carousel-{param_id}" class="carousel slide" data-ride="carousel" data-interval="false">
                        <ol class="carousel-indicators">
                            <li data-target="#carousel-{param_id}" data-slide-to="0" class="active"></li>
                            <li data-target="#carousel-{param_id}" data-slide-to="1"></li>
                            <li data-target="#carousel-{param_id}" data-slide-to="2"></li>
                        </ol>

                        <div class="carousel-inner">
                            <div class="carousel-item active">
                                <div class="plot-container">{fig_parity_html}</div>
                            </div>
                            <div class="carousel-item">
                                <div class="plot-container">{fig_residuum_html}</div>
                            </div>
                            <div class="carousel-item">
                                <div class="plot-container">{fig_histogram_html}</div>
                            </div>
                        </div>

                        <a class="carousel-control-prev" href="#carousel-{param_id}" role="button" data-slide="prev">
                            <span class="carousel-control-prev-icon"></span>
                        </a>
                        <a class="carousel-control-next" href="#carousel-{param_id}" role="button" data-slide="next">
                            <span class="carousel-control-next-icon"></span>
                        </a>
                    </div>
                </div>
"""

        html_content += """
            </div>
        </div>
"""

    # ===== SECCIÓN DE GRUPOS (LEYENDA + ESTADÍSTICAS) =====
    if has_groups:
        # Contar muestras por grupo
        group_counts = {}
        for g in sample_groups.values():
            if g != 'none':
                group_counts[g] = group_counts.get(g, 0) + 1
        
        html_content += """
        <div class="info-box" id="grupos-section">
            <h2>Grupos</h2>
            <p class="text-caption">
                <em>Las muestras han sido clasificadas en grupos personalizados para su análisis.</em>
            </p>
            
            <!-- TABLA DE LEYENDA -->
            <h3 style="margin-top: 30px; margin-bottom: 15px;">Leyenda de Grupos</h3>
            <table style="width: 100%;">
                <thead>
                    <tr>
                        <th>Símbolo</th>
                        <th>Grupo</th>
                        <th>Descripción</th>
                        <th>Color</th>
                        <th>N° Muestras</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        for group_key in ['Set 1', 'Set 2', 'Set 3', 'Set 4']:
            if group_key in group_counts:
                group_config = SAMPLE_GROUPS[group_key]
                custom_label = group_labels.get(group_key, group_key)
                description = group_descriptions.get(group_key, '')
                description_text = description if description else '<em style="color: #999;">Sin descripción</em>'
                count = group_counts[group_key]
                
                html_content += f"""
                    <tr>
                        <td style="text-align: center; font-size: 24px;">{group_config['emoji']}</td>
                        <td><strong>{custom_label}</strong></td>
                        <td>{description_text}</td>
                        <td><span style="display: inline-block; width: 20px; height: 20px; background-color: {group_config['color']}; border: 1px solid #ccc; border-radius: 3px;"></span> {group_config['color']}</td>
                        <td>{count}</td>
                    </tr>
"""
        
        html_content += """
                </tbody>
            </table>
"""

        # ===== TABLA DE ESTADÍSTICAS POR GRUPO =====
        if valid_params:
            html_content += """
            <h3 style="margin-top: 40px; margin-bottom: 15px;">Estadísticas por Grupo</h3>
            <p class="text-caption">
                <em>Métricas de rendimiento (R², RMSE, BIAS, N) para cada grupo de validación por parámetro.</em>
            </p>
"""
            
            # Calcular índices de muestras eliminadas (removed_indices)
            # En el reporte HTML no tenemos muestras "eliminadas", todas las del df están presentes
            removed_indices = set()
            
            # Crear una tabla por cada parámetro
            for param_name, param_id, _ in valid_params:
                # Calcular estadísticas de todos los grupos para este parámetro
                all_stats = calculate_all_groups_statistics(
                    df,
                    param_name,
                    removed_indices,
                    sample_groups,
                    ['Set 1', 'Set 2', 'Set 3', 'Set 4']
                )
                
                # Filtrar solo grupos con datos
                groups_with_stats = {k: v for k, v in all_stats.items() if v is not None and k in group_counts}
                
                if groups_with_stats:
                    html_content += f"""
            <h4 style="margin-top: 25px; color: #0051a5;">{param_name}</h4>
            <table style="width: 100%; margin-top: 10px;">
                <thead>
                    <tr>
                        <th>Grupo</th>
                        <th>R²</th>
                        <th>RMSE</th>
                        <th>BIAS</th>
                        <th>N</th>
                    </tr>
                </thead>
                <tbody>
"""
                    
                    for group_key in ['Set 1', 'Set 2', 'Set 3', 'Set 4']:
                        if group_key in groups_with_stats:
                            stats = groups_with_stats[group_key]
                            group_config = SAMPLE_GROUPS[group_key]
                            custom_label = group_labels.get(group_key, group_key)
                            display_name = f"{group_config['emoji']} {custom_label}"
                            
                            html_content += f"""
                    <tr>
                        <td><strong>{display_name}</strong></td>
                        <td>{stats['r2']:.4f}</td>
                        <td>{stats['rmse']:.3f}</td>
                        <td>{stats['bias']:.3f}</td>
                        <td>{stats['n']}</td>
                    </tr>
"""
                    
                    html_content += """
                </tbody>
            </table>
"""
        
        html_content += """
        </div>
"""

    # FOOTER
    html_content += f"""
        <!-- FOOTER -->
        <div style="margin-top: 50px; padding-top: 20px; border-top: 2px solid #eee; text-align: center; color: #666; font-size: 12px;">
            <p>Informe generado automáticamente por COREF Suite</p>
            <p>Fecha: {timestamp}</p>
            <p>© {year} BÜCHI Labortechnik AG</p>
        </div>
    </div>

<script>
    // Embedded data
    const fullData = {full_data_json};
    const availableYears = {json.dumps(available_years)};
    const availableMonths = {json.dumps(available_months)};
    const monthNames = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
    const sampleGroups = {json.dumps(sample_groups_json)};
    const groupLabels = {json.dumps(group_labels)};
    const SAMPLE_GROUPS = {json.dumps(SAMPLE_GROUPS)};
    
    let filteredData = [...fullData];
    
    // Initialize filters
    function initializeFilters() {{
        const yearContainer = document.getElementById('yearFilters');
        availableYears.forEach(year => {{
            const label = document.createElement('label');
            label.className = 'filter-checkbox-label';
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.value = year;
            checkbox.checked = true;
            checkbox.className = 'year-filter';
            label.appendChild(checkbox);
            label.appendChild(document.createTextNode(' ' + year));
            yearContainer.appendChild(label);
        }});
        
        const monthContainer = document.getElementById('monthFilters');
        availableMonths.forEach(month => {{
            const label = document.createElement('label');
            label.className = 'filter-checkbox-label';
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.value = month;
            checkbox.checked = false;
            checkbox.className = 'month-filter';
            label.appendChild(checkbox);
            label.appendChild(document.createTextNode(' ' + monthNames[month - 1]));
            monthContainer.appendChild(label);
        }});
        
        updateFilterIndicator();
    }}
    
    function applyVisualFilter() {{
        const selectedYears = Array.from(document.querySelectorAll('.year-filter:checked')).map(cb => parseInt(cb.value));
        const selectedMonths = Array.from(document.querySelectorAll('.month-filter:checked')).map(cb => parseInt(cb.value));
        const idFilterText = document.getElementById('idFilter').value.toLowerCase();
        const noteFilterText = document.getElementById('noteFilter').value.toLowerCase();
        
        filteredData = fullData.filter(row => {{
            // Date filters
            if (row.Date) {{
                const date = new Date(row.Date);
                const year = date.getFullYear();
                const month = date.getMonth() + 1;
                
                if (selectedYears.length > 0 && !selectedYears.includes(year)) return false;
                if (selectedMonths.length > 0 && !selectedMonths.includes(month)) return false;
            }}
            
            // ID filter
            if (idFilterText && row.ID) {{
                if (!String(row.ID).toLowerCase().includes(idFilterText)) return false;
            }}
            
            // Note filter
            if (noteFilterText && row.Note) {{
                if (!String(row.Note).toLowerCase().includes(noteFilterText)) return false;
            }}
            
            return true;
        }});
        
        updateFilterIndicator();
        updateAllPlots();
        
        // Scroll to top to see changes
        window.scrollTo({{ top: 0, behavior: 'smooth' }});
    }}
    
    function resetVisualFilter() {{
        document.querySelectorAll('.year-filter').forEach(cb => cb.checked = true);
        document.querySelectorAll('.month-filter').forEach(cb => cb.checked = false);
        document.getElementById('idFilter').value = '';
        document.getElementById('noteFilter').value = '';
        filteredData = [...fullData];
        updateFilterIndicator();
        updateAllPlots();
    }}
    
    function updateFilterIndicator() {{
        const total = fullData.length;
        const filtered = filteredData.length;
        const indicator = document.getElementById('filterIndicator');
        
        if (total === filtered) {{
            indicator.textContent = `📊 ${{total}} muestras`;
        }} else {{
            indicator.textContent = `📊 ${{filtered}}/${{total}} muestras (filtro activo)`;
        }}
    }}
    
    function updateAllPlots() {{
        // Update spectra if exists
        updateSpectraPlot();
        
        // Update all parameter plots
        {json.dumps([param_id for _, param_id, _ in valid_params])}.forEach(paramId => {{
            updateParameterPlots(paramId);
        }});
    }}
    
    function updateSpectraPlot() {{
        // Find spectra plot div
        const spectraDiv = document.querySelector('#spectra-section .plotly-graph-div');
        if (!spectraDiv) return;
        
        // Get pixel columns (assuming #1, #2, etc.)
        const pixelCols = Object.keys(filteredData[0] || {{}}).filter(col => /^#\\d+$/.test(col)).sort((a, b) => {{
            return parseInt(a.slice(1)) - parseInt(b.slice(1));
        }});
        
        if (pixelCols.length === 0) return;
        
        const xValues = pixelCols.map(col => parseInt(col.slice(1)));
        const traces = [];
        const legendAdded = new Set();
        
        filteredData.forEach((row, idx) => {{
            const yValues = pixelCols.map(col => parseFloat(row[col]));
            if (yValues.every(v => isNaN(v))) return;
            
            const group = sampleGroups[idx.toString()] || 'none';
            const groupConfig = SAMPLE_GROUPS[group];
            const color = groupConfig.color;
            const opacity = group !== 'none' ? 0.5 : 0.35;
            const width = group !== 'none' ? 2 : 1;
            
            let legendName, prefix;
            if (group !== 'none') {{
                const customLabel = groupLabels[group] || group;
                legendName = `${{groupConfig.emoji}} ${{customLabel}}`;
                prefix = `${{legendName}} - `;
            }} else {{
                legendName = 'Sin set';
                prefix = '';
            }}
            
            const showLegend = !legendAdded.has(group);
            if (showLegend) legendAdded.add(group);
            
            traces.push({{
                x: xValues,
                y: yValues,
                mode: 'lines',
                showlegend: showLegend,
                legendgroup: group,
                name: legendName,
                line: {{ width: width, color: color }},
                opacity: opacity,
                hovertemplate: `${{prefix}}ID: ${{row.ID || idx}}<br>Date: ${{row.Date || ''}}<br>Note: ${{row.Note || ''}}<br>Pixel: %{{x}}<br>Abs: %{{y}}<extra></extra>`
            }});
        }});
        
        const layout = {{
            title: 'Spectra',
            xaxis: {{ title: 'Pixel', gridcolor: 'white' }},
            yaxis: {{ title: 'Absorbance (AU)', gridcolor: 'white' }},
            autosize: true,
            height: 700,
            hovermode: 'closest',
            template: 'plotly',
            plot_bgcolor: '#E5ECF6',
            paper_bgcolor: 'white',
            showlegend: true
        }};
        
        Plotly.react(spectraDiv, traces, layout);
    }}
    
    function updateParameterPlots(paramId) {{
        // Find the carousel for this parameter
        const carouselDiv = document.querySelector(`#carousel-${{paramId}}`);
        if (!carouselDiv) return;
        
        // Find the parity plot (first carousel item)
        const parityDiv = carouselDiv.querySelector('.carousel-item:first-child .plotly-graph-div');
        if (!parityDiv) return;
        
        // Get the parameter name from the tab
        const tabElement = document.querySelector(`#tab-${{paramId}}`);
        if (!tabElement) return;
        const paramName = tabElement.textContent.trim();
        
        // Column names
        const resultCol = `Result ${{paramName}}`;
        const referenceCol = `Reference ${{paramName}}`;
        const residuumCol = `Residuum ${{paramName}}`;
        
        // Filter data and extract valid points
        const validPoints = [];
        filteredData.forEach((row, idx) => {{
            const refVal = parseFloat(row[referenceCol]);
            const resVal = parseFloat(row[resultCol]);
            const residVal = parseFloat(row[residuumCol]);
            
            if (!isNaN(refVal) && !isNaN(resVal) && !isNaN(residVal) && 
                refVal !== 0 && resVal !== 0) {{
                validPoints.push({{
                    idx: idx,
                    ref: refVal,
                    res: resVal,
                    residuum: residVal,
                    id: row.ID || idx,
                    date: row.Date || '',
                    note: row.Note || '',
                    group: sampleGroups[idx.toString()] || 'none'
                }});
            }}
        }});
        
        if (validPoints.length < 2) return;
        
        // Group points by group
        const pointsByGroup = {{}};
        Object.keys(SAMPLE_GROUPS).forEach(g => pointsByGroup[g] = []);
        
        validPoints.forEach(point => {{
            pointsByGroup[point.group].push(point);
        }});
        
        // Calculate R², RMSE, BIAS
        const xVals = validPoints.map(p => p.ref);
        const yVals = validPoints.map(p => p.res);
        const n = xVals.length;
        
        const xMean = xVals.reduce((a, b) => a + b, 0) / n;
        const yMean = yVals.reduce((a, b) => a + b, 0) / n;
        
        const ssRes = validPoints.reduce((sum, p) => sum + Math.pow(p.res - p.ref, 2), 0);
        const ssTot = yVals.reduce((sum, y) => sum + Math.pow(y - yMean, 2), 0);
        const r2 = 1 - (ssRes / ssTot);
        
        const rmse = Math.sqrt(ssRes / n);
        const bias = (yVals.reduce((a, b) => a + b, 0) - xVals.reduce((a, b) => a + b, 0)) / n;
        
        // Create parity plot traces
        const traces = [];
        
        // Add group traces (excluding 'none')
        Object.keys(SAMPLE_GROUPS).forEach(groupName => {{
            if (groupName === 'none') return;
            
            const points = pointsByGroup[groupName];
            if (points.length === 0) return;
            
            const groupConfig = SAMPLE_GROUPS[groupName];
            const customLabel = groupLabels[groupName] || groupName;
            const displayLabel = `${{groupConfig.emoji}} ${{customLabel}}`;
            
            traces.push({{
                x: points.map(p => p.ref),
                y: points.map(p => p.res),
                mode: 'markers',
                marker: {{
                    color: groupConfig.color,
                    size: groupConfig.size,
                    symbol: groupConfig.symbol
                }},
                hovertemplate: points.map(p => 
                    `${{displayLabel}}<br>Date: ${{p.date}}<br>ID: ${{p.id}}<br>Reference: ${{p.ref.toFixed(2)}}<br>Result: ${{p.res.toFixed(2)}}<extra></extra>`
                ),
                name: displayLabel,
                showlegend: true
            }});
        }});
        
        // Add 'none' group
        const nonePoints = pointsByGroup['none'];
        if (nonePoints.length > 0) {{
            const groupConfig = SAMPLE_GROUPS['none'];
            traces.push({{
                x: nonePoints.map(p => p.ref),
                y: nonePoints.map(p => p.res),
                mode: 'markers',
                marker: {{
                    color: groupConfig.color,
                    size: groupConfig.size,
                    symbol: groupConfig.symbol
                }},
                hovertemplate: nonePoints.map(p => 
                    `Date: ${{p.date}}<br>ID: ${{p.id}}<br>Reference: ${{p.ref.toFixed(2)}}<br>Result: ${{p.res.toFixed(2)}}<extra></extra>`
                ),
                name: 'Sin set',
                showlegend: true
            }});
        }}
        
        // Add reference lines
        const minVal = Math.min(...xVals);
        const maxVal = Math.max(...xVals);
        
        // y = x line
        traces.push({{
            x: [minVal, maxVal],
            y: [minVal, maxVal],
            mode: 'lines',
            line: {{ dash: 'dash', color: 'gray' }},
            name: 'y = x',
            showlegend: false
        }});
        
        // RMSE lines
        traces.push({{
            x: [minVal, maxVal],
            y: [minVal + rmse, maxVal + rmse],
            mode: 'lines',
            line: {{ dash: 'dash', color: 'red' }},
            name: 'RMSE',
            showlegend: false
        }});
        
        traces.push({{
            x: [minVal, maxVal],
            y: [minVal - rmse, maxVal - rmse],
            mode: 'lines',
            line: {{ dash: 'dash', color: 'red' }},
            showlegend: false
        }});
        
        // Update layout
        const layout = {{
            title: 'Parity Plot',
            xaxis: {{ title: referenceCol, gridcolor: 'white' }},
            yaxis: {{ title: resultCol, gridcolor: 'white' }},
            showlegend: true,
            height: 550,
            dragmode: 'zoom',
            hovermode: 'closest',
            template: 'plotly',
            plot_bgcolor: '#E5ECF6',
            paper_bgcolor: 'white',
            autosize: true,
            legend: {{
                orientation: 'h',
                x: 0.5,
                y: -0.25,
                xanchor: 'center',
                yanchor: 'top'
            }},
            margin: {{ l: 60, r: 40, t: 80, b: 140 }}
        }};
        
        Plotly.react(parityDiv, traces, layout);
        
        // Update stats box
        const statsBox = carouselDiv.closest('.tab-pane').querySelector('.stats-box table');
        if (statsBox) {{
            statsBox.querySelector('tr:nth-child(2) td:nth-child(1)').textContent = r2.toFixed(3);
            statsBox.querySelector('tr:nth-child(2) td:nth-child(2)').textContent = rmse.toFixed(3);
            statsBox.querySelector('tr:nth-child(2) td:nth-child(3)').textContent = bias.toFixed(3);
            statsBox.querySelector('tr:nth-child(2) td:nth-child(4)').textContent = n;
        }}
    }}
    
    $(document).ready(function() {{
        initializeFilters();
        
        function forcePlotlyAutosize($root) {{
            $root = $root && $root.length ? $root : $(document);
            var $plots = $root.find('.carousel-item.active .plotly-graph-div, .tab-pane.active .plotly-graph-div');
            $plots.each(function() {{
                var gd = this;
                if (!gd) return;
                requestAnimationFrame(function() {{
                    requestAnimationFrame(function() {{
                        try {{ Plotly.Plots.resize(gd); }} catch(e) {{}}
                        try {{ Plotly.relayout(gd, {{ autosize: true }}); }} catch(e) {{}}
                    }});
                }});
            }});
        }}

        $('a[data-toggle="tab"]').on('shown.bs.tab', function(e) {{
            var target = $(e.target).attr('href');
            forcePlotlyAutosize($(target));
        }});

        $(document).on('slid.bs.carousel', '.carousel', function() {{
            forcePlotlyAutosize($(this));
        }});

        forcePlotlyAutosize($(document));
    }});
</script>

</body>
</html>
"""

    return html_content