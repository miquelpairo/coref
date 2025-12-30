"""
TSV Validation Reports - HTML Report Generator
===============================================
Funciones para generar reportes HTML con grupos personalizados
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import re

import pandas as pd
import plotly.graph_objs as go
import numpy as np
from sklearn.metrics import mean_squared_error, r2_score

from core.report_utils import load_buchi_css, get_sidebar_styles, get_common_report_styles


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

        # ✅ Leyenda debajo y centrada
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
    """Genera espectros para reporte"""
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

    for i in range(len(df)):
        y = spec.iloc[i].to_numpy()

        if np.all(np.isnan(y)):
            continue

        group = sample_groups.get(i, 'none')
        group_config = SAMPLE_GROUPS[group]
        color = group_config['color']
        opacity = 0.5 if group != 'none' else 0.35
        width = 2 if group != 'none' else 1

        if group != 'none':
            custom_label = group_labels.get(group, group)
            prefix = f"{group_config['emoji']} {custom_label} - "
        else:
            prefix = ""

        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode="lines",
                showlegend=False,
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
    )
    return fig


def generate_html_report(
    df: pd.DataFrame,
    file_name: str,
    sample_groups: Dict[int, str] = None,
    group_labels: Dict[str, str] = None,
    SAMPLE_GROUPS: Dict = None,
    PIXEL_RE = None
) -> str:
    """
    Genera HTML con Bootstrap tabs + sidebar BUCHI + CSS corporativo + GRUPOS.
    """
    if sample_groups is None:
        sample_groups = {}
    if group_labels is None:
        group_labels = {}
    
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

    # Construcción del SIDEBAR
    sidebar_items = """
        <h2>📋 Índice</h2>
        <ul>
            <li><a href="#info-general">Información General</a></li>
            <li><a href="#summary-stats">Resumen Estadístico</a></li>
    """
    
    if any(g != 'none' for g in sample_groups.values()):
        sidebar_items += '<li><a href="#grupos-legend">Leyenda de Grupos</a></li>\n'
    
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
    
    sidebar_items += '''
        </ul>
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

    # LEYENDA DE GRUPOS
    if any(g != 'none' for g in sample_groups.values()):
        group_counts = {}
        for g in sample_groups.values():
            if g != 'none':
                group_counts[g] = group_counts.get(g, 0) + 1
        
        html_content += """
        <div class="info-box" id="grupos-legend">
            <h2>🏷️ Leyenda de Grupos de Muestras</h2>
            <p class="text-caption">
                <em>Las muestras han sido clasificadas en grupos personalizados para su análisis.</em>
            </p>
            <table style="width: 100%; margin-top: 15px;">
                <thead>
                    <tr>
                        <th>Símbolo</th>
                        <th>Grupo</th>
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
                count = group_counts[group_key]
                
                html_content += f"""
                    <tr>
                        <td style="text-align: center; font-size: 24px;">{group_config['emoji']}</td>
                        <td><strong>{custom_label}</strong></td>
                        <td><span style="display: inline-block; width: 20px; height: 20px; background-color: {group_config['color']}; border: 1px solid #ccc; border-radius: 3px;"></span> {group_config['color']}</td>
                        <td>{count}</td>
                    </tr>
"""
        
        html_content += """
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
    $(document).ready(function() {{
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