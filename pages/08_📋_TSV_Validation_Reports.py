"""
COREF - TSV Validation Reports
==============================
Genera informes HTML interactivos (Bootstrap + DataTables + Plotly) a partir de TSV
(export/journal), incluyendo:
- Limpieza y reorganización tipo Node-RED
- Parity / Residuum vs N / Histograma por parámetro
- Summary of statistics
- NUEVO: Plot de espectros (columnas #1..#n) + Filtro por fechas

Autor: Miquel
"""

from __future__ import annotations

import base64
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objs as go
import streamlit as st
from dateutil import parser as date_parser
from sklearn.metrics import mean_squared_error, r2_score

from auth import check_password
from buchi_streamlit_theme import apply_buchi_styles


# =============================================================================
# STREAMLIT PAGE SETUP
# =============================================================================
apply_buchi_styles()

if not check_password():
    st.stop()

st.title("📋 TSV Validation Reports")
st.markdown("## Generación de informes de validación NIR (TSV) con gráficos interactivos y espectros.")

# Información de uso
with st.expander("ℹ️ Instrucciones de Uso"):
    st.markdown("""
    ### Cómo usar TSV Validation Reports:
    
    **1. Cargar Archivos TSV:**
    - Sube uno o varios archivos TSV (export/journal de NIR-Online)
    - Los archivos pueden estar en formato estándar o journal
    - Soporta carga múltiple para procesamiento batch
    
    **2. Filtrar por Fechas (Opcional):**
    - Define rango de fechas para filtrar las mediciones
    - Útil para analizar períodos específicos de validación
    - Deja vacío para procesar todas las fechas
    
    **3. Procesamiento Automático:**
    - La herramienta limpia y reorganiza los datos (tipo Node-RED)
    - Elimina filas con todos los resultados en cero
    - Reorganiza columnas: Reference, Result, Residuum por parámetro
    - Convierte formatos de fecha automáticamente
    
    **4. Generación de Reportes:**
    - Presiona **"Procesar y Generar Reportes"**
    - Genera informes HTML interactivos con:
        - Resumen estadístico (R², RMSE, BIAS, N)
        - Gráficos por parámetro (Parity, Residuum vs N, Histograma)
        - Plot de espectros NIR (columnas #1..#n)
        - Tabla de datos con filtrado por columnas
        - Sidebar de navegación estilo BUCHI
    
    **5. Descargar Resultados:**
    - HTML: Reporte completo interactivo con Plotly + DataTables
    - CSV: Datos limpios y reorganizados
    - ZIP: Descarga todos los reportes si procesas múltiples archivos
    
    **Características:**
    - ✅ Gráficos interactivos con Plotly (zoom, pan, hover)
    - ✅ Tabla de datos con búsqueda y filtrado
    - ✅ Diseño corporativo BUCHI con sidebar de navegación
    - ✅ Soporte para múltiples parámetros simultáneos
    - ✅ Vista de espectros completos NIR
    """)


# =============================================================================
# DATA CLEANING / NODE-RED LOGIC
# =============================================================================

PIXEL_RE = re.compile(r"^#\d+$")


def _is_pixel_col(col: str) -> bool:
    return bool(PIXEL_RE.fullmatch(str(col)))


def filter_relevant_data(data: List[Dict]) -> List[Dict]:
    """
    Mantiene:
    - Todas las columnas de metadata hasta '#X1' (sin incluir)
    - + columnas espectrales '#1'..'#n' (pixeles), estén donde estén
    """
    if not data:
        return []

    all_columns = list(data[0].keys())
    stop_column = "#X1"

    # 1) Metadata columns: up to #X1 (excluded)
    base_cols: List[str] = []
    for col in all_columns:
        if col == stop_column:
            break
        base_cols.append(col)

    # 2) Pixel columns: #1..#n
    pixel_cols = [c for c in all_columns if _is_pixel_col(c)]
    pixel_cols = sorted(pixel_cols, key=lambda s: int(str(s)[1:]))

    columns_to_keep = base_cols + pixel_cols

    filtered: List[Dict] = []
    for row in data:
        new_row = {}
        for col in columns_to_keep:
            v = row.get(col, None)
            new_row[col] = v if v not in ("", None) else None
        filtered.append(new_row)

    return filtered


def delete_zero_rows(data: List[Dict]) -> List[Dict]:
    """
    Elimina filas donde 'Result' esté vacío o donde TODOS los valores result sean 0.
    """
    out: List[Dict] = []
    for row in data:
        if "Result" not in row or row["Result"] is None:
            continue

        result_values = str(row["Result"]).split(";")
        all_zeroes = True
        for v in result_values:
            v = v.strip().replace(",", ".")
            if v in ("", "-", "NA", "NaN"):
                all_zeroes = False
                break
            try:
                if float(v) != 0.0:
                    all_zeroes = False
                    break
            except Exception:
                all_zeroes = False
                break

        if not all_zeroes:
            out.append(row)

    return out


def reorganize_results_and_reference(data: List[Dict]) -> List[Dict]:
    """
    Reorganiza a:
    - columnas no-parámetro (ID, Date, Recipe, Note, etc.)
    - Reference <param>, Result <param>, Residuum <param>
    """
    if not data:
        return []

    reorganized: List[Dict] = []

    for row in data:
        all_cols = list(row.keys())
        if "Reference" not in all_cols or "Begin" not in all_cols:
            reorganized.append(row)
            continue

        ref_i = all_cols.index("Reference")
        begin_i = all_cols.index("Begin")
        parameter_cols = all_cols[ref_i + 1 : begin_i]

        new_row: Dict = {}
        for key in all_cols:
            if key in parameter_cols:
                continue
            if key in ("Result", "Reference"):
                continue
            new_row[key] = row.get(key)

        result_values: List[str] = []
        if row.get("Result") is not None:
            result_values = [v.strip() for v in str(row["Result"]).split(";")]

        for idx, p in enumerate(parameter_cols):
            ref_val = row.get(p)
            if ref_val is not None and ref_val != "":
                ref_val = str(ref_val).replace(",", ".")
                try:
                    ref_val_f = float(ref_val) if ref_val not in ("-", "NA") else None
                except Exception:
                    ref_val_f = None
            else:
                ref_val_f = None

            res_val_f = None
            if idx < len(result_values):
                rv = result_values[idx].replace(",", ".")
                try:
                    res_val_f = float(rv) if rv not in ("", "-", "NA") else None
                except Exception:
                    res_val_f = None

            new_row[f"Reference {p}"] = ref_val_f
            new_row[f"Result {p}"] = res_val_f
            new_row[f"Residuum {p}"] = (res_val_f - ref_val_f) if (ref_val_f is not None and res_val_f is not None) else None

        reorganized.append(new_row)

    return reorganized


def try_parse_date(date_str) -> pd.Timestamp:
    """Intenta convertir fecha con formatos comunes y fallback a dateutil."""
    if pd.isna(date_str) or date_str is None or str(date_str).strip() == "":
        return pd.NaT

    s = str(date_str).strip()
    fmts = ["%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m-%d-%Y"]

    for fmt in fmts:
        try:
            return pd.to_datetime(s, format=fmt)
        except Exception:
            pass

    try:
        return pd.to_datetime(date_parser.parse(s, dayfirst=True))
    except Exception:
        return pd.NaT


def clean_tsv_file(uploaded_file) -> pd.DataFrame:
    df_raw = pd.read_csv(uploaded_file, delimiter="\t", keep_default_na=False)
    data = df_raw.to_dict("records")

    data = filter_relevant_data(data)
    data = delete_zero_rows(data)
    data = reorganize_results_and_reference(data)

    df = pd.DataFrame(data)

    if not df.empty:
        pixel_cols = [c for c in df.columns if _is_pixel_col(c)]
        if pixel_cols:
            df[pixel_cols] = df[pixel_cols].replace(",", ".", regex=True)
            df[pixel_cols] = df[pixel_cols].apply(pd.to_numeric, errors="coerce")

    if "Date" in df.columns:
        df["Date"] = df["Date"].apply(try_parse_date)

    return df


# =============================================================================
# PLOTLY FIGURES
# =============================================================================

def create_layout(title: str, xaxis_title: str, yaxis_title: str) -> Dict:
    return {
        "title": title,
        "xaxis_title": xaxis_title,
        "yaxis_title": yaxis_title,
        "showlegend": False,
        "width": 900,
        "height": 600,
        "dragmode": "zoom",
        "hovermode": "closest",
        "template": "plotly",
        "plot_bgcolor": "#E5ECF6",
        "paper_bgcolor": "white",
        "xaxis": {"gridcolor": "white"},
        "yaxis": {"gridcolor": "white"},
    }


def plot_comparison(df: pd.DataFrame, result_col: str, reference_col: str, residuum_col: str):
    """
    Genera:
    - Parity plot
    - Residuum vs N
    - Histograma residuum
    """
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

        hover_id = df.loc[valid_mask, "ID"] if "ID" in df.columns else pd.Series(range(len(valid_mask)))
        hover_date = df.loc[valid_mask, "Date"] if "Date" in df.columns else pd.Series([""] * len(valid_mask))
        hover_id = hover_id.loc[aligned_mask]
        hover_date = hover_date.loc[aligned_mask]

        r2 = float(r2_score(x, y))
        rmse = float(np.sqrt(mean_squared_error(x, y)))
        bias = float(np.mean(y - x))
        n = int(len(x))

        hovertext = [
            f"Date: {date_val}<br>ID: {id_val}<br>Reference: {x_val:.2f}<br>Result: {y_val:.2f}"
            for id_val, date_val, x_val, y_val in zip(hover_id, hover_date, x, y)
        ]

        # Parity plot
        fig_parity = go.Figure()
        fig_parity.add_trace(go.Scatter(x=x, y=y, mode="markers", hovertext=hovertext, hoverinfo="text", name="Data"))
        fig_parity.add_trace(go.Scatter(x=x, y=x, mode="lines", line=dict(dash="dash", color="gray"), name="y = x"))
        fig_parity.add_trace(go.Scatter(x=x, y=x + rmse, mode="lines", line=dict(dash="dash", color="red"), name="y = x + RMSE"))
        fig_parity.add_trace(go.Scatter(x=x, y=x - rmse, mode="lines", line=dict(dash="dash", color="red"), name="y = x - RMSE"))
        fig_parity.update_layout(**create_layout("Parity Plot", reference_col, result_col))

        # Residuum vs N
        hovertext_res = [
            f"Date: {date_val}<br>ID: {id_val}<br>Residuum: {res_val:.2f}"
            for id_val, date_val, res_val in zip(hover_id, hover_date, residuum)
        ]
        fig_res = go.Figure(
            go.Bar(x=list(range(len(residuum))), y=residuum, hovertext=hovertext_res, hoverinfo="text", name="Residuum")
        )
        fig_res.update_layout(**create_layout("Residuum vs N", "N", "Residuum"))

        # Histograma
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Histogram(x=residuum, nbinsx=20, marker=dict(color="blue")))
        fig_hist.update_layout(**create_layout("Residuum Histogram", "Residuum", "Count"))

        return fig_parity, fig_res, fig_hist, r2, rmse, bias, n

    except Exception as e:
        st.error(f"Error generando plots para {result_col}: {e}")
        return None


def build_spectra_figure(df: pd.DataFrame) -> Optional[go.Figure]:
    pixel_cols = [c for c in df.columns if _is_pixel_col(c)]
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

        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode="lines",
                showlegend=False,
                line={"width": 1},
                opacity=0.35,
                hovertemplate=(
                    f"ID: {hover_id.iloc[i]}<br>"
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
        width=1250,
        height=700,
        hovermode="closest",
        template="plotly",
        plot_bgcolor="#E5ECF6",
        paper_bgcolor="white",
        xaxis={"gridcolor": "white"},
        yaxis={"gridcolor": "white"},
    )
    return fig


# =============================================================================
# HTML REPORT GENERATION
# =============================================================================

def _safe_html_id(s: str) -> str:
    s = s.strip()
    s = s.replace(" ", "-").replace("/", "-").replace("\\", "-")
    s = re.sub(r"[^a-zA-Z0-9\-_]", "", s)
    return s or "param"


@dataclass
class ReportResult:
    name: str
    html: str
    csv: pd.DataFrame


def generate_html_report(df: pd.DataFrame, file_name: str) -> str:
    """
    Genera HTML con Bootstrap tabs + sidebar BUCHI + CSS corporativo.
    """
    from core.report_utils import load_buchi_css, get_sidebar_styles, get_common_report_styles
    
    columns_result = [c for c in df.columns if str(c).startswith("Result ")]
    columns_reference = [c.replace("Result ", "Reference ") for c in columns_result]
    columns_residuum = [c.replace("Result ", "Residuum ") for c in columns_result]

    summary_data: List[Dict] = []
    fig_spectra = build_spectra_figure(df)
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
        plots = plot_comparison(df, result_col, reference_col, residuum_col)
        if plots:
            valid_params.append((param_name, param_id, plots))
            fig_parity, fig_res, fig_hist, r2, rmse, bias, n = plots
            summary_data.append({"Parameter": param_name, "R2": r2, "RMSE": rmse, "BIAS": bias, "N": n})

    # ========================================================================
    # CONSTRUCCIÓN DEL SIDEBAR
    # ========================================================================
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
    
    sidebar_items += '''
            <li><a href="#data-table-section">Tabla de Datos</a></li>
        </ul>
'''

    # ========================================================================
    # CARGAR CSS BUCHI
    # ========================================================================
    buchi_css = load_buchi_css()
    sidebar_css = get_sidebar_styles()
    common_css = get_common_report_styles()

    # ========================================================================
    # HTML COMPLETO
    # ========================================================================
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

    <!-- DataTables CSS -->
    <link rel="stylesheet" href="https://cdn.datatables.net/1.10.21/css/jquery.dataTables.min.css">
    <link rel="stylesheet" href="https://cdn.datatables.net/fixedheader/3.1.8/css/fixedHeader.dataTables.min.css">

    <!-- jQuery (ONLY FULL VERSION) -->
    <script src="https://code.jquery.com/jquery-3.5.1.js"></script>

    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/popper.js@1.16.1/dist/umd/popper.min.js"></script>
    <script src="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js"></script>

    <!-- DataTables JS -->
    <script src="https://cdn.datatables.net/1.10.21/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/fixedheader/3.1.8/js/dataTables.fixedHeader.min.js"></script>

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

    # SPECTRA
    if fig_spectra is not None:
        spectra_html = _fig_html(fig_spectra) if not plotly_already_included else fig_spectra.to_html(full_html=False, include_plotlyjs=False)
        html_content += f"""
        <div class="info-box" id="spectra-section">
            <h2>Espectros</h2>
            <p class="text-caption">
                <em>Overlay de todos los espectros NIR (columnas #1..#n).</em>
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
                <em>Gráficos interactivos (Parity, Residuum vs N, Histograma) para cada parámetro.</em>
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

    # DATA TABLE
    html_content += """
        <div class="info-box" id="data-table-section">
            <h2>Tabla de Datos Original</h2>
            <p class="text-caption">
                <em>Datos limpios y reorganizados con filtrado por columnas.</em>
            </p>
            <table id="data-table" class="display nowrap" style="width:100%">
                <thead>
                    <tr>
"""
    for col in df.columns:
        html_content += f"<th>{col}</th>"

    html_content += """
                    </tr>
                </thead>
                <tbody>
"""

    for _, r in df.iterrows():
        html_content += "<tr>"
        for col in df.columns:
            v = r[col]
            if pd.isna(v):
                html_content += "<td></td>"
            else:
                html_content += f"<td>{v}</td>"
        html_content += "</tr>"

    html_content += f"""
                </tbody>
            </table>
        </div>

        <!-- FOOTER -->
        <div style="margin-top: 50px; padding-top: 20px; border-top: 2px solid #eee; text-align: center; color: #666; font-size: 12px;">
            <p>Informe generado automáticamente por COREF Suite</p>
            <p>Fecha: {timestamp}</p>
            <p>© {year} BÜCHI Labortechnik AG</p>
        </div>
    </div>

    <script>
        $(document).ready(function() {{
            // Clonar el header ANTES de inicializar DataTable
            $('#data-table thead tr').clone(true).appendTo('#data-table thead');
            $('#data-table thead tr:eq(1) th').each(function(i) {{
                var title = $(this).text();
                $(this).html('<input type="text" placeholder="Filtrar ' + title + '" style="width:100%; padding: 5px; font-size: 12px; box-sizing: border-box;"/>');
            }});

            // Ahora inicializar DataTable
            var table = $('#data-table').DataTable({{
                scrollX: true,
                pageLength: 25,
                fixedHeader: true,
                orderCellsTop: true,
                searching: true
            }});

            // Conectar los inputs de filtro
            $('#data-table thead tr:eq(1) th').each(function(i) {{
                $('input', this).on('keyup change', function() {{
                    if (table.column(i).search() !== this.value) {{
                        table.column(i).search(this.value).draw();
                    }}
                }});
            }});

            // Plotly resize on tab show
            $('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {{
                var target = $(e.target).attr('href');
                $(target).find('.plotly-graph-div').each(function() {{
                    Plotly.relayout(this, {{ autosize: true }});
                }});
            }});
        }});
    </script>

</body>
</html>
"""

    return html_content


# =============================================================================
# STREAMLIT UI
# =============================================================================


st.markdown("---")
st.markdown("### 📁 Carga de archivos")
st.info(
    """
1. **Carga** uno o varios archivos TSV
2. **Opcionalmente filtra** por rango de fechas

"""
)

uploaded_files = st.file_uploader(
    "Cargar archivos TSV",
    type=["tsv", "txt"],
    accept_multiple_files=True,
    help="Selecciona uno o varios archivos TSV para procesar",
)

if uploaded_files:
    st.success(f"✅ {len(uploaded_files)} archivo(s) cargado(s)")
    
    # ========================================================================
    # FILTRO POR FECHAS
    # ========================================================================
    st.markdown("---")
    st.subheader("📅 Filtrado por Fechas (Opcional)")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        start_date = st.date_input(
            "Fecha de inicio",
            value=None,
            help="Dejar vacío para incluir desde el inicio"
        )
    
    with col2:
        end_date = st.date_input(
            "Fecha de fin",
            value=None,
            help="Dejar vacío para incluir hasta el final"
        )
    
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        clear_dates = st.button("🗑️ Limpiar fechas")
    
    if clear_dates:
        st.rerun()
    
    # Mostrar info del filtro
    if start_date or end_date:
        filter_info = "🔍 **Filtro activo:** "
        if start_date and end_date:
            filter_info += f"Desde {start_date.strftime('%d/%m/%Y')} hasta {end_date.strftime('%d/%m/%Y')}"
        elif start_date:
            filter_info += f"Desde {start_date.strftime('%d/%m/%Y')} en adelante"
        elif end_date:
            filter_info += f"Hasta {end_date.strftime('%d/%m/%Y')}"
        st.info(filter_info)
    
    st.markdown("---")
    
    # ========================================================================
    # PROCESAMIENTO
    # ========================================================================
    if st.button("🚀 Procesar y Generar Reportes", type="primary"):
        results: List[ReportResult] = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        for idx, uploaded_file in enumerate(uploaded_files, start=1):
            file_name = uploaded_file.name.replace(".tsv", "").replace(".txt", "")
            status_text.text(f"Procesando {file_name}...")

            try:
                # Limpiar datos
                df_clean = clean_tsv_file(uploaded_file)
                
                # Aplicar filtro de fechas si existe
                df_filtered = df_clean.copy()
                rows_before = len(df_filtered)
                
                if "Date" in df_filtered.columns:
                    if start_date is not None:
                        start_datetime = pd.Timestamp(start_date)
                        df_filtered = df_filtered[df_filtered["Date"] >= start_datetime]
                    
                    if end_date is not None:
                        # Incluir todo el día final (hasta las 23:59:59)
                        end_datetime = pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
                        df_filtered = df_filtered[df_filtered["Date"] <= end_datetime]
                    
                    rows_after = len(df_filtered)
                    
                    if rows_before != rows_after:
                        st.info(f"📊 {file_name}: {rows_before} → {rows_after} filas después del filtro de fechas")
                    
                    if rows_after == 0:
                        st.warning(f"⚠️ {file_name}: No hay datos en el rango de fechas seleccionado. Se omite este archivo.")
                        continue
                else:
                    if start_date or end_date:
                        st.warning(f"⚠️ {file_name}: No tiene columna 'Date', se ignora el filtro de fechas.")

                # Generar reporte
                html = generate_html_report(df_filtered, file_name)

                results.append(ReportResult(name=file_name, html=html, csv=df_filtered))
                st.success(f"✅ {file_name} procesado correctamente")

            except Exception as e:
                st.error(f"❌ Error procesando {file_name}: {e}")
                import traceback
                st.code(traceback.format_exc())

            progress_bar.progress(idx / len(uploaded_files))

        status_text.text("✅ Todos los archivos procesados")

        if results:
            st.markdown("---")
            st.subheader("📥 Descargar reportes")

            # ZIP download if multiple
            if len(results) > 1:
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    for r in results:
                        zf.writestr(f"{r.name}.html", r.html)
                        zf.writestr(f"{r.name}_cleaned.csv", r.csv.to_csv(sep=";", index=False))

                st.download_button(
                    label="📦 Descargar todos los reportes (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name="tsv_validation_reports.zip",
                    mime="application/zip",
                    use_container_width=True,
                )

                st.markdown("---")

            # Individual downloads
            for r in results:
                c1, c2, c3 = st.columns([3, 1, 1])
                with c1:
                    st.write(f"**{r.name}**")
                with c2:
                    st.download_button(
                        label="⬇️ HTML",
                        data=r.html,
                        file_name=f"{r.name}.html",
                        mime="text/html",
                        key=f"html_{r.name}",
                        use_container_width=True,
                    )
                with c3:
                    st.download_button(
                        label="⬇️ CSV",
                        data=r.csv.to_csv(sep=";", index=False),
                        file_name=f"{r.name}_cleaned.csv",
                        mime="text/csv",
                        key=f"csv_{r.name}",
                        use_container_width=True,
                    )

            # Preview
            st.markdown("---")
            if st.checkbox("👀 Vista previa del primer reporte"):
                st.components.v1.html(results[0].html, height=850, scrolling=True)
        elif start_date or end_date:
            st.warning("⚠️ No se generaron reportes. Verifica que haya datos en el rango de fechas seleccionado.")