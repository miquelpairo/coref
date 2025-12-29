"""
COREF - TSV Validation Reports
==============================
VERSIÓN OPTIMIZADA: Selección mediante botones + click events
"""

from __future__ import annotations

import base64
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from typing import Dict, List, Optional, Tuple, Set

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
st.markdown("## Generación de informes de validación NIR (TSV) con previsualización y selección de muestras.")

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
    
    **4. Previsualización y Selección (NUEVO):**
    - Visualiza espectros y gráficos de parámetros
    - Marca muestras en la tabla para eliminar (checkbox)
    - Revisa estadísticas y outliers visualmente
    - Elimina muestras problemáticas antes de generar el reporte
    
    **5. Generación de Reportes:**
    - Presiona **"Generar Informe Final"**
    - Genera informes HTML interactivos con:
        - Resumen estadístico (R², RMSE, BIAS, N)
        - Gráficos por parámetro (Parity, Residuum vs N, Histograma)
        - Plot de espectros NIR (columnas #1..#n)
        - Sidebar de navegación estilo BUCHI
    
    **6. Descargar Resultados:**
    - HTML: Reporte completo interactivo con Plotly
    - ZIP: Descarga todos los reportes si procesas múltiples archivos
    
    **Características:**
    - ✅ Gráficos interactivos con Plotly (zoom, pan, hover)
    - ✅ Selección mediante tabla interactiva
    - ✅ Previsualización antes de generar reporte
    - ✅ Diseño corporativo BUCHI con sidebar de navegación
    - ✅ Soporte para múltiples parámetros simultáneos
    - ✅ Vista de espectros completos NIR
    """)


# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = {}  # {filename: DataFrame}
if 'samples_to_remove' not in st.session_state:
    st.session_state.samples_to_remove = {}  # {filename: set(indices)}


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
# PLOTLY FIGURES - PARA VISUALIZACIÓN (SIN SELECCIÓN)
# =============================================================================

def create_layout(title: str, xaxis_title: str, yaxis_title: str) -> Dict:
    return {
        "title": title,
        "xaxis_title": xaxis_title,
        "yaxis_title": yaxis_title,
        "showlegend": False,
        "height": 600,  
        "dragmode": "zoom",
        "hovermode": "closest",
        "template": "plotly",
        "plot_bgcolor": "#E5ECF6",
        "paper_bgcolor": "white",
        "xaxis": {"gridcolor": "white"},
        "yaxis": {"gridcolor": "white"},
        "autosize": True,
    }


def plot_comparison_preview(df: pd.DataFrame, result_col: str, reference_col: str, residuum_col: str, 
                            removed_indices: Set[int] = None):
    """
    Genera gráficos de previsualización.
    Los puntos marcados para eliminar se muestran en rojo.
    """
    if removed_indices is None:
        removed_indices = set()
    
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

        # Obtener índices originales
        original_indices = df.loc[valid_mask].loc[aligned_mask].index.tolist()
        
        hover_id = df.loc[valid_mask, "ID"] if "ID" in df.columns else pd.Series(range(len(valid_mask)))
        hover_date = df.loc[valid_mask, "Date"] if "Date" in df.columns else pd.Series([""] * len(valid_mask))
        hover_id = hover_id.loc[aligned_mask]
        hover_date = hover_date.loc[aligned_mask]

        # Separar puntos normales vs marcados para eliminar
        keep_mask = [idx not in removed_indices for idx in original_indices]
        remove_mask = [idx in removed_indices for idx in original_indices]

        r2 = float(r2_score(x, y))
        rmse = float(np.sqrt(mean_squared_error(x, y)))
        bias = float(np.mean(y - x))
        n = int(len(x))

        # Parity plot
        fig_parity = go.Figure()
        
        # Puntos normales (azul)
        if any(keep_mask):
            hovertext_keep = [
                f"Index: {idx}<br>Date: {date_val}<br>ID: {id_val}<br>Reference: {x_val:.2f}<br>Result: {y_val:.2f}"
                for idx, id_val, date_val, x_val, y_val, keep in zip(original_indices, hover_id, hover_date, x, y, keep_mask)
                if keep
            ]
            fig_parity.add_trace(go.Scatter(
                x=x[[i for i, k in enumerate(keep_mask) if k]],
                y=y[[i for i, k in enumerate(keep_mask) if k]],
                mode="markers",
                marker=dict(color="blue", size=8),
                hovertext=hovertext_keep,
                hoverinfo="text",
                name="Data"
            ))
        
        # Puntos marcados para eliminar (rojo)
        if any(remove_mask):
            hovertext_remove = [
                f"⚠️ MARCADO PARA ELIMINAR<br>Index: {idx}<br>Date: {date_val}<br>ID: {id_val}<br>Reference: {x_val:.2f}<br>Result: {y_val:.2f}"
                for idx, id_val, date_val, x_val, y_val, remove in zip(original_indices, hover_id, hover_date, x, y, remove_mask)
                if remove
            ]
            fig_parity.add_trace(go.Scatter(
                x=x[[i for i, r in enumerate(remove_mask) if r]],
                y=y[[i for i, r in enumerate(remove_mask) if r]],
                mode="markers",
                marker=dict(color="red", size=10, symbol="x"),
                hovertext=hovertext_remove,
                hoverinfo="text",
                name="Marked for removal"
            ))
        
        # Líneas de referencia
        fig_parity.add_trace(go.Scatter(x=x, y=x, mode="lines", line=dict(dash="dash", color="gray"), name="y = x", showlegend=False))
        fig_parity.add_trace(go.Scatter(x=x, y=x + rmse, mode="lines", line=dict(dash="dash", color="orange"), name="RMSE", showlegend=False))
        fig_parity.add_trace(go.Scatter(x=x, y=x - rmse, mode="lines", line=dict(dash="dash", color="orange"), showlegend=False))
        
        fig_parity.update_layout(**create_layout("Parity Plot", reference_col, result_col))

        # Residuum vs N
        hovertext_res = [
            f"Index: {idx}<br>Date: {date_val}<br>ID: {id_val}<br>Residuum: {res_val:.2f}"
            for idx, id_val, date_val, res_val in zip(original_indices, hover_id, hover_date, residuum)
        ]
        
        colors = ["red" if idx in removed_indices else "blue" for idx in original_indices]
        
        fig_res = go.Figure(
            go.Bar(
                x=list(range(len(residuum))),
                y=residuum,
                hovertext=hovertext_res,
                hoverinfo="text",
                name="Residuum",
                marker=dict(color=colors)
            )
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


def build_spectra_figure_preview(df: pd.DataFrame, removed_indices: Set[int] = None) -> Optional[go.Figure]:
    if removed_indices is None:
        removed_indices = set()
    
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

        # Color según si está marcado para eliminar
        color = "red" if i in removed_indices else "blue"
        opacity = 0.7 if i in removed_indices else 0.35
        width = 2 if i in removed_indices else 1
        
        prefix = "⚠️ MARCADO - " if i in removed_indices else ""

        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode="lines",
                showlegend=False,
                line={"width": width, "color": color},
                opacity=opacity,
                hovertemplate=(
                    f"{prefix}Index: {i}<br>"
                    f"ID: {hover_id.iloc[i]}<br>"
                    f"Date: {hover_date.iloc[i]}<br>"
                    f"Note: {hover_note.iloc[i]}<br>"
                    "Pixel: %{x}<br>"
                    "Abs: %{y}<extra></extra>"
                )
            )
        )

    fig.update_layout(
        title="Spectra Preview",
        xaxis_title="Pixel",
        yaxis_title="Absorbance (AU)",
        autosize=True,
        height=700,
        hovermode="closest",
        template="plotly",
        plot_bgcolor="#E5ECF6",
        paper_bgcolor="white",
        xaxis={"gridcolor": "white"},
        yaxis={"gridcolor": "white"}
    )
    return fig


# =============================================================================
# HTML REPORT GENERATION (funciones para reporte final)
# =============================================================================

def plot_comparison_for_report(df: pd.DataFrame, result_col: str, reference_col: str, residuum_col: str):
    """Versión simple para reportes finales"""
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


def build_spectra_figure_for_report(df: pd.DataFrame) -> Optional[go.Figure]:
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
    fig_spectra = build_spectra_figure_for_report(df)
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
        plots = plot_comparison_for_report(df, result_col, reference_col, residuum_col)
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


# =============================================================================
# STREAMLIT UI - FILTROS DE FECHA PRIMERO
# =============================================================================

st.markdown("---")
st.markdown("### 📁 FASE 1: Carga y Filtrado de Archivos")

uploaded_files = st.file_uploader(
    "Cargar archivos TSV",
    type=["tsv", "txt"],
    accept_multiple_files=True,
    help="Selecciona uno o varios archivos TSV para procesar",
)

if uploaded_files:
    st.success(f"✅ {len(uploaded_files)} archivo(s) cargado(s)")
    
    # ========================================================================
    # FILTROS DE FECHA - PRIMERO, ANTES DE PROCESAR
    # ========================================================================
    st.markdown("---")
    st.subheader("📅 1. Filtrado por Fechas (Opcional)")
    st.info("Define el rango de fechas ANTES de procesar. Esto filtrará los datos desde el inicio.")
    
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
        if st.button("🗑️ Limpiar fechas"):
            st.rerun()
    
    # Mostrar info del filtro
    if start_date or end_date:
        filter_info = "🔍 **Filtro de fechas configurado:** "
        if start_date and end_date:
            filter_info += f"Desde {start_date.strftime('%d/%m/%Y')} hasta {end_date.strftime('%d/%m/%Y')}"
        elif start_date:
            filter_info += f"Desde {start_date.strftime('%d/%m/%Y')} en adelante"
        elif end_date:
            filter_info += f"Hasta {end_date.strftime('%d/%m/%Y')}"
        st.success(filter_info)
    
    st.markdown("---")
    st.subheader("2. Procesar Archivos")
    
    # Procesamiento con filtros aplicados
    if st.button("🔄 Procesar Archivos con Filtros", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        st.session_state.processed_data = {}
        st.session_state.samples_to_remove = {}  # IMPORTANTE: Resetear selecciones

        for idx, uploaded_file in enumerate(uploaded_files, start=1):
            file_name = uploaded_file.name.replace(".tsv", "").replace(".txt", "")
            status_text.text(f"Procesando {file_name}...")

            try:
                # Limpiar datos
                df_clean = clean_tsv_file(uploaded_file)
                
                # APLICAR FILTROS DE FECHA INMEDIATAMENTE
                df_filtered = df_clean.copy()
                rows_before = len(df_filtered)
                
                if "Date" in df_filtered.columns:
                    if start_date is not None:
                        start_datetime = pd.Timestamp(start_date)
                        df_filtered = df_filtered[df_filtered["Date"] >= start_datetime]
                    
                    if end_date is not None:
                        end_datetime = pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
                        df_filtered = df_filtered[df_filtered["Date"] <= end_datetime]
                    
                    rows_after = len(df_filtered)
                    
                    if start_date or end_date:
                        if rows_before != rows_after:
                            st.info(f"📊 {file_name}: {rows_before} → {rows_after} muestras después del filtro")
                        
                        if rows_after == 0:
                            st.warning(f"⚠️ {file_name}: No hay datos en el rango de fechas. Se omite.")
                            continue
                else:
                    if start_date or end_date:
                        st.warning(f"⚠️ {file_name}: No tiene columna 'Date', se ignora el filtro de fechas")
                
                # Resetear índices para evitar problemas - CRÍTICO
                df_filtered = df_filtered.reset_index(drop=True)
                
                # Guardar datos YA FILTRADOS
                st.session_state.processed_data[file_name] = df_filtered
                
                # CRÍTICO: Inicializar con set vacío para este archivo
                st.session_state.samples_to_remove[file_name] = set()
                
                st.success(f"✅ {file_name} procesado ({len(df_filtered)} muestras)")

            except Exception as e:
                st.error(f"❌ Error: {file_name}: {e}")
                import traceback
                st.code(traceback.format_exc())

            progress_bar.progress(idx / len(uploaded_files))

        status_text.text("✅ Procesamiento completado")


# FASE 2: Previsualización SOBRE DATOS YA FILTRADOS
if st.session_state.processed_data:
    st.markdown("---")
    st.markdown("### 🔍 FASE 2: Previsualización y Selección de Muestras")
    
    st.info("Los datos mostrados aquí ya incluyen el filtro de fechas aplicado en la Fase 1.")
    
    selected_file = st.selectbox(
        "Archivo:",
        options=list(st.session_state.processed_data.keys())
    )
    
    if selected_file:
        # Datos YA FILTRADOS por fecha
        df_current = st.session_state.processed_data[selected_file]
        
        # CRÍTICO: Limpiar índices inválidos
        removed_indices = st.session_state.samples_to_remove.get(selected_file, set())
        
        # Filtrar solo índices que existen en df_current
        valid_removed = {idx for idx in removed_indices if idx in df_current.index}
        
        # Si había índices inválidos, actualizar
        if len(valid_removed) != len(removed_indices):
            invalid_count = len(removed_indices - valid_removed)
            st.session_state.samples_to_remove[selected_file] = valid_removed
            if invalid_count > 0:
                st.warning(f"⚠️ Se limpiaron {invalid_count} selecciones inválidas de sesiones anteriores")
        
        removed_indices = valid_removed
        
        # Estadísticas
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Total", len(df_current))
        with col2:
            st.metric("🗑️ Marcadas", len(removed_indices))
        with col3:
            st.metric("✅ Finales", len(df_current) - len(removed_indices))
        
        st.markdown("---")
        
        # ESPECTROS
        with st.expander("📈 Vista de Espectros", expanded=False):
            try:
                fig_spectra = build_spectra_figure_preview(df_current, removed_indices)
                if fig_spectra:
                    st.plotly_chart(fig_spectra, use_container_width=True)
                else:
                    st.warning("No hay datos espectrales para mostrar")
            except Exception as e:
                st.error(f"Error generando espectros: {e}")
                import traceback
                st.code(traceback.format_exc())
        
        # GRÁFICOS POR PARÁMETRO
        with st.expander("📊 Gráficos por Parámetro", expanded=False):
            columns_result = [c for c in df_current.columns if str(c).startswith("Result ")]
            
            if columns_result:
                param_names = [str(c).replace("Result ", "") for c in columns_result]
                selected_param = st.selectbox("Parámetro:", param_names)
                
                result_col = f"Result {selected_param}"
                reference_col = f"Reference {selected_param}"
                residuum_col = f"Residuum {selected_param}"
                
                try:
                    plots = plot_comparison_preview(df_current, result_col, reference_col, residuum_col, removed_indices)
                    
                    if plots:
                        fig_parity, fig_res, fig_hist, r2, rmse, bias, n = plots
                        
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("R²", f"{r2:.3f}")
                        col2.metric("RMSE", f"{rmse:.3f}")
                        col3.metric("BIAS", f"{bias:.3f}")
                        col4.metric("N", n)
                        
                        tab1, tab2, tab3 = st.tabs(["Parity", "Residuum", "Histogram"])
                        
                        with tab1:
                            st.plotly_chart(fig_parity, use_container_width=True)
                        with tab2:
                            st.plotly_chart(fig_res, use_container_width=True)
                        with tab3:
                            st.plotly_chart(fig_hist, use_container_width=True)
                    else:
                        st.error(f"No se pudieron generar gráficos para {selected_param}. Verifica que haya datos válidos.")
                except Exception as e:
                    st.error(f"Error generando gráficos para {selected_param}: {e}")
                    import traceback
                    st.code(traceback.format_exc())
            else:
                st.warning("No hay parámetros Result en el archivo")
        
        st.markdown("---")
        
        # TABLA INTERACTIVA
        st.subheader("🎯 Selección de Muestras")
        st.info("✅ Marca las filas que quieras eliminar → Presiona **'Actualizar Selección'** → Revisa los gráficos → Confirma eliminación")
        
        # Preparar DataFrame para edición
        df_for_edit = df_current.copy()
        df_for_edit.insert(0, 'Eliminar', False)
        
        # Marcar las ya seleccionadas
        for idx in removed_indices:
            if idx in df_for_edit.index:
                df_for_edit.at[idx, 'Eliminar'] = True
        
        # Seleccionar columnas a mostrar
        display_cols = ['Eliminar']
        for col in ['ID', 'Date', 'Note']:
            if col in df_for_edit.columns:
                display_cols.append(col)
        
        # Añadir columnas Result
        result_cols = [c for c in df_for_edit.columns if str(c).startswith("Result ")]
        display_cols.extend(result_cols[:3])  # Primeros 3 parámetros
        
        edited_df = st.data_editor(
            df_for_edit[display_cols],
            column_config={
                "Eliminar": st.column_config.CheckboxColumn(
                    "Eliminar",
                    help="Marcar para eliminar esta muestra",
                    default=False,
                )
            },
            disabled=[c for c in display_cols if c != 'Eliminar'],
            hide_index=False,
            use_container_width=True,
            key=f"editor_{selected_file}"
        )
        
        st.markdown("---")
        
        # Botones de acción en 3 columnas
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Actualizar Selección", use_container_width=True, help="Actualiza los gráficos con las muestras marcadas"):
                # Actualizar selección sin eliminar
                new_removed = set(edited_df[edited_df['Eliminar']].index.tolist())
                st.session_state.samples_to_remove[selected_file] = new_removed
                st.success(f"✅ Selección actualizada: {len(new_removed)} muestras marcadas")
                st.rerun()
        
        with col2:
            if st.button("🗑️ Confirmar Eliminación", type="primary", use_container_width=True, 
                        disabled=(len(removed_indices) == 0),
                        help="Elimina definitivamente las muestras marcadas"):
                if removed_indices:
                    # Eliminar del DataFrame y resetear índices
                    df_updated = df_current.drop(index=list(removed_indices)).reset_index(drop=True)
                    st.session_state.processed_data[selected_file] = df_updated
                    # Limpiar selecciones
                    st.session_state.samples_to_remove[selected_file] = set()
                    st.success(f"✅ {len(removed_indices)} muestras eliminadas definitivamente")
                    st.rerun()
        
        with col3:
            if st.button("↩️ Desmarcar Todas", use_container_width=True,
                        disabled=(len(removed_indices) == 0),
                        help="Quita todas las marcas de selección"):
                st.session_state.samples_to_remove[selected_file] = set()
                st.rerun()
        
        # Mostrar resumen de selección
        if removed_indices:
            st.warning(f"⚠️ **{len(removed_indices)} muestras marcadas para eliminar**. Los gráficos arriba muestran estas muestras en rojo.")

# FASE 3: Generación (datos ya filtrados y depurados)
if st.session_state.processed_data:
    st.markdown("---")
    st.markdown("### 📥 FASE 3: Generar Reportes Finales")
    
    st.info("Los reportes se generarán con los datos actuales (después de filtros de fecha y eliminaciones manuales).")
    
    # Resumen
    st.subheader("📋 Resumen de Archivos")
    summary_data = []
    for fname, df in st.session_state.processed_data.items():
        summary_data.append({
            "Archivo": fname,
            "Muestras": len(df),
            "Parámetros": len([c for c in df.columns if str(c).startswith("Result ")])
        })
    
    st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    if st.button("📥 Generar Informes HTML", type="primary", use_container_width=True):
        results: List[ReportResult] = []
        progress_bar = st.progress(0)
        
        for idx, (file_name, df) in enumerate(st.session_state.processed_data.items(), start=1):
            try:
                if len(df) == 0:
                    st.warning(f"⚠️ {file_name}: No hay datos para generar reporte")
                    continue
                
                html = generate_html_report(df, file_name)
                results.append(ReportResult(name=file_name, html=html, csv=df))
                st.success(f"✅ {file_name} ({len(df)} muestras)")
            except Exception as e:
                st.error(f"❌ {file_name}: {e}")
                import traceback
                st.code(traceback.format_exc())
            
            progress_bar.progress(idx / len(st.session_state.processed_data))
        
        if results:
            st.markdown("---")
            
            if len(results) > 1:
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    for r in results:
                        zf.writestr(f"{r.name}.html", r.html)
                
                st.download_button(
                    "📦 Descargar todos los reportes (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name="tsv_validation_reports.zip",
                    mime="application/zip",
                    use_container_width=True
                )
                st.markdown("---")
            
            for r in results:
                st.markdown(f"**{r.name}**")
                st.download_button(
                    "💾 Descargar Informe HTML",
                    data=r.html,
                    file_name=f"{r.name}.html",
                    mime="text/html",
                    key=f"dl_{r.name}"
                )
                st.markdown("---")