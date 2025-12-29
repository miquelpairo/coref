"""
COREF - TSV Validation Reports
==============================
Genera informes HTML interactivos (Bootstrap + Plotly) a partir de TSV (export/journal), incluyendo:
- Limpieza y reorganización tipo Node-RED
- Parity / Residuum vs N / Histograma por parámetro
- Summary of statistics
- Plot de espectros (columnas #1..#n) + Filtro por fechas
- NUEVO: Previsualización interactiva y selección de muestras para eliminar (click + lasso/box)

Autor: Miquel
"""

from __future__ import annotations

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

from streamlit_plotly_events import plotly_events  # ✅ NUEVO (requirements.txt)

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

with st.expander("ℹ️ Instrucciones de Uso"):
    st.markdown(
        """
### Cómo usar TSV Validation Reports:

**1. Cargar Archivos TSV:**
- Sube uno o varios archivos TSV (export/journal de NIR-Online)
- Soporta carga múltiple

**2. Filtrar por Fechas (Opcional):**
- Define rango de fechas para filtrar las mediciones

**3. Procesar:**
- Limpia y reorganiza los datos
- Elimina filas con Result vacío / todos 0
- Reorganiza: Reference/Result/Residuum por parámetro
- Convierte fechas automáticamente

**4. Previsualización y Selección (NUEVO):**
- Click o Lasso/Box select para marcar/desmarcar muestras
- Se muestran en rojo en los gráficos
- Confirma eliminación cuando quieras

**5. Generación de Reportes Finales:**
- Genera HTML con carrusel de gráficos + espectros (Plotly)

**Nota técnica:**
- La captura de selección se hace con `streamlit-plotly-events`.
"""
    )


# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================
if "processed_data" not in st.session_state:
    st.session_state.processed_data = {}  # {filename: DataFrame}
if "samples_to_remove" not in st.session_state:
    st.session_state.samples_to_remove = {}  # {filename: set(df_index)}
if "last_events" not in st.session_state:
    st.session_state.last_events = {}  # {key: set(signature)} para evitar doble toggle


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

    base_cols: List[str] = []
    for col in all_columns:
        if col == stop_column:
            break
        base_cols.append(col)

    pixel_cols = [c for c in all_columns if _is_pixel_col(c)]
    pixel_cols = sorted(pixel_cols, key=lambda s: int(str(s)[1:]))

    columns_to_keep = base_cols + pixel_cols

    filtered: List[Dict] = []
    for row in data:
        new_row: Dict = {}
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
            new_row[f"Residuum {p}"] = (
                (res_val_f - ref_val_f) if (ref_val_f is not None and res_val_f is not None) else None
            )

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
# HELPERS PARA EVENTOS (evitar doble-toggle en reruns)
# =============================================================================
def _event_signature(ev: dict) -> str:
    # firma suficientemente estable para deduplicar el mismo evento en reruns
    return f"{ev.get('curveNumber','')}/{ev.get('pointNumber','')}/{ev.get('x','')}/{ev.get('y','')}/{ev.get('customdata','')}"


def toggle_from_events(events: List[dict], removed_indices: Set[int], dedupe_key: str) -> bool:
    """
    Toggle indices leyendo `customdata` de plotly_events.
    Devuelve True si cambió algo.
    """
    if not events:
        return False

    prev = st.session_state.last_events.get(dedupe_key, set())
    current = set(_event_signature(e) for e in events)

    # Solo procesa lo nuevo
    new_events = [e for e in events if _event_signature(e) not in prev]
    st.session_state.last_events[dedupe_key] = current

    changed = False
    for ev in new_events:
        cd = ev.get("customdata")
        if cd is None:
            continue
        idx = cd[0] if isinstance(cd, (list, tuple)) else cd
        try:
            idx = int(idx)
        except Exception:
            continue

        if idx in removed_indices:
            removed_indices.remove(idx)
        else:
            removed_indices.add(idx)
        changed = True

    return changed


# =============================================================================
# PLOTLY FIGURES - INTERACTIVE (PREVIEW)
# =============================================================================
def create_layout(title: str, xaxis_title: str, yaxis_title: str, with_selection: bool = True) -> Dict:
    layout = {
        "title": title,
        "xaxis_title": xaxis_title,
        "yaxis_title": yaxis_title,
        "showlegend": False,
        "height": 600,
        "dragmode": "lasso" if with_selection else "zoom",
        "hovermode": "closest",
        "template": "plotly",
        "plot_bgcolor": "#E5ECF6",
        "paper_bgcolor": "white",
        "xaxis": {"gridcolor": "white"},
        "yaxis": {"gridcolor": "white"},
        "autosize": True,
    }
    if with_selection:
        layout["clickmode"] = "event+select"
    return layout


def plot_comparison_interactive(
    df: pd.DataFrame,
    result_col: str,
    reference_col: str,
    residuum_col: str,
    removed_indices: Set[int] | None = None,
):
    """
    Genera gráficos interactivos con capacidad de selección.
    Los puntos marcados para eliminar se muestran en rojo.
    `customdata` SIEMPRE lleva el df.index real.
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

        # Índices reales del DF (IMPORTANTÍSIMO)
        original_indices = df.loc[valid_mask].loc[aligned_mask].index.tolist()

        hover_id = df.loc[valid_mask, "ID"] if "ID" in df.columns else pd.Series(range(len(df)))
        hover_date = df.loc[valid_mask, "Date"] if "Date" in df.columns else pd.Series([""] * len(df))
        hover_id = hover_id.loc[aligned_mask]
        hover_date = hover_date.loc[aligned_mask]

        r2 = float(r2_score(x, y))
        rmse = float(np.sqrt(mean_squared_error(x, y)))
        bias = float(np.mean(y - x))
        n = int(len(x))

        keep_mask = [idx not in removed_indices for idx in original_indices]
        remove_mask = [idx in removed_indices for idx in original_indices]

        # Parity
        fig_parity = go.Figure()

        keep_idx_positions = [i for i, k in enumerate(keep_mask) if k]
        rem_idx_positions = [i for i, r in enumerate(remove_mask) if r]

        if keep_idx_positions:
            hovertext_keep = []
            keep_custom = []
            keep_x = []
            keep_y = []
            for pos in keep_idx_positions:
                idx = original_indices[pos]
                keep_custom.append([idx])
                keep_x.append(x.iloc[pos])
                keep_y.append(y.iloc[pos])
                hovertext_keep.append(
                    f"Index: {idx}<br>Date: {hover_date.iloc[pos]}<br>ID: {hover_id.iloc[pos]}<br>"
                    f"Reference: {x.iloc[pos]:.2f}<br>Result: {y.iloc[pos]:.2f}"
                )

            fig_parity.add_trace(
                go.Scatter(
                    x=keep_x,
                    y=keep_y,
                    mode="markers",
                    marker=dict(color="blue", size=8),
                    hovertext=hovertext_keep,
                    hoverinfo="text",
                    name="Data",
                    customdata=keep_custom,
                )
            )

        if rem_idx_positions:
            hovertext_remove = []
            rem_custom = []
            rem_x = []
            rem_y = []
            for pos in rem_idx_positions:
                idx = original_indices[pos]
                rem_custom.append([idx])
                rem_x.append(x.iloc[pos])
                rem_y.append(y.iloc[pos])
                hovertext_remove.append(
                    f"⚠️ MARCADO PARA ELIMINAR<br>Index: {idx}<br>Date: {hover_date.iloc[pos]}<br>ID: {hover_id.iloc[pos]}<br>"
                    f"Reference: {x.iloc[pos]:.2f}<br>Result: {y.iloc[pos]:.2f}"
                )

            fig_parity.add_trace(
                go.Scatter(
                    x=rem_x,
                    y=rem_y,
                    mode="markers",
                    marker=dict(color="red", size=10, symbol="x"),
                    hovertext=hovertext_remove,
                    hoverinfo="text",
                    name="Marked for removal",
                    customdata=rem_custom,
                )
            )

        # líneas guía
        fig_parity.add_trace(go.Scatter(x=x, y=x, mode="lines", line=dict(dash="dash", color="gray"), name="y = x"))
        fig_parity.add_trace(
            go.Scatter(x=x, y=x + rmse, mode="lines", line=dict(dash="dash", color="orange"), name="y = x + RMSE")
        )
        fig_parity.add_trace(
            go.Scatter(x=x, y=x - rmse, mode="lines", line=dict(dash="dash", color="orange"), name="y = x - RMSE")
        )

        fig_parity.update_layout(**create_layout("Parity Plot (click/lasso para marcar)", reference_col, result_col, True))

        # Residuum vs N (barra con customdata = df.index)
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
                marker=dict(color=colors),
                customdata=[[idx] for idx in original_indices],
            )
        )
        fig_res.update_layout(**create_layout("Residuum vs N (click/lasso para marcar)", "N", "Residuum", True))

        # Histograma (sin selección)
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Histogram(x=residuum, nbinsx=20, marker=dict(color="blue")))
        fig_hist.update_layout(**create_layout("Residuum Histogram", "Residuum", "Count", False))

        return fig_parity, fig_res, fig_hist, r2, rmse, bias, n

    except Exception as e:
        st.error(f"Error generando plots para {result_col}: {e}")
        return None


def build_spectra_figure_interactive(df: pd.DataFrame, removed_indices: Set[int] | None = None) -> Optional[go.Figure]:
    """
    Espectros con customdata = df.index real.
    """
    if removed_indices is None:
        removed_indices = set()

    pixel_cols = [c for c in df.columns if _is_pixel_col(c)]
    if not pixel_cols:
        return None

    pixel_cols = sorted(pixel_cols, key=lambda s: int(str(s)[1:]))
    x = [int(str(c)[1:]) for c in pixel_cols]

    spec = df[pixel_cols].replace(",", ".", regex=True).apply(pd.to_numeric, errors="coerce")

    hover_id = df["ID"].astype(str) if "ID" in df.columns else pd.Series([str(i) for i in df.index], index=df.index)
    hover_date = df["Date"].astype(str) if "Date" in df.columns else pd.Series([""] * len(df), index=df.index)
    hover_note = df["Note"].astype(str) if "Note" in df.columns else pd.Series([""] * len(df), index=df.index)

    fig = go.Figure()

    for idx in df.index:
        y = spec.loc[idx].to_numpy()
        if np.all(np.isnan(y)):
            continue

        marked = idx in removed_indices
        color = "red" if marked else "blue"
        opacity = 0.7 if marked else 0.35
        width = 2 if marked else 1
        prefix = "⚠️ MARCADO - " if marked else ""

        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode="lines",
                showlegend=False,
                line={"width": width, "color": color},
                opacity=opacity,
                hovertemplate=(
                    f"{prefix}Index: {idx}<br>"
                    f"ID: {hover_id.loc[idx]}<br>"
                    f"Date: {hover_date.loc[idx]}<br>"
                    f"Note: {hover_note.loc[idx]}<br>"
                    "Pixel: %{x}<br>"
                    "Abs: %{y}<extra></extra>"
                ),
                customdata=[[idx]],
            )
        )

    fig.update_layout(
        title="Spectra (click/lasso para marcar)",
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
        dragmode="lasso",
        clickmode="event+select",
    )
    return fig


# =============================================================================
# HTML REPORT GENERATION (FINAL) - sin selección
# =============================================================================
def create_layout_for_report(title: str, xaxis_title: str, yaxis_title: str) -> Dict:
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


def plot_comparison_for_report(df: pd.DataFrame, result_col: str, reference_col: str, residuum_col: str):
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

        hover_id = df.loc[valid_mask, "ID"] if "ID" in df.columns else pd.Series(range(len(df)))
        hover_date = df.loc[valid_mask, "Date"] if "Date" in df.columns else pd.Series([""] * len(df))
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

        fig_parity = go.Figure()
        fig_parity.add_trace(go.Scatter(x=x, y=y, mode="markers", hovertext=hovertext, hoverinfo="text", name="Data"))
        fig_parity.add_trace(go.Scatter(x=x, y=x, mode="lines", line=dict(dash="dash", color="gray"), name="y = x"))
        fig_parity.add_trace(go.Scatter(x=x, y=x + rmse, mode="lines", line=dict(dash="dash", color="red"), name="y = x + RMSE"))
        fig_parity.add_trace(go.Scatter(x=x, y=x - rmse, mode="lines", line=dict(dash="dash", color="red"), name="y = x - RMSE"))
        fig_parity.update_layout(**create_layout_for_report("Parity Plot", reference_col, result_col))

        hovertext_res = [
            f"Date: {date_val}<br>ID: {id_val}<br>Residuum: {res_val:.2f}"
            for id_val, date_val, res_val in zip(hover_id, hover_date, residuum)
        ]
        fig_res = go.Figure(go.Bar(x=list(range(len(residuum))), y=residuum, hovertext=hovertext_res, hoverinfo="text", name="Residuum"))
        fig_res.update_layout(**create_layout_for_report("Residuum vs N", "N", "Residuum"))

        fig_hist = go.Figure()
        fig_hist.add_trace(go.Histogram(x=residuum, nbinsx=20, marker=dict(color="blue")))
        fig_hist.update_layout(**create_layout_for_report("Residuum Histogram", "Residuum", "Count"))

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

    spec = df[pixel_cols].replace(",", ".", regex=True).apply(pd.to_numeric, errors="coerce")

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
    s = s.strip().replace(" ", "-").replace("/", "-").replace("\\", "-")
    s = re.sub(r"[^a-zA-Z0-9\-_]", "", s)
    return s or "param"


@dataclass
class ReportResult:
    name: str
    html: str
    csv: pd.DataFrame


def generate_html_report(df: pd.DataFrame, file_name: str) -> str:
    """
    HTML final: Bootstrap + carrusel + autosize fix para Plotly (carousel/tabs).
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
        html = fig.to_html(full_html=False, include_plotlyjs=include_js, config={"responsive": True})
        plotly_already_included = True
        return html

    valid_params: List[Tuple[str, str, Tuple]] = []
    for result_col, reference_col, residuum_col in zip(columns_result, columns_reference, columns_residuum):
        param_name = str(result_col).replace("Result ", "")
        param_id = _safe_html_id(param_name)
        plots = plot_comparison_for_report(df, result_col, reference_col, residuum_col)
        if plots:
            valid_params.append((param_name, param_id, plots))
            fig_parity, fig_res, fig_hist, r2, rmse, bias, n = plots
            summary_data.append({"Parameter": param_name, "R2": r2, "RMSE": rmse, "BIAS": bias, "N": n})

    sidebar_items = """
        <h2>📋 Índice</h2>
        <ul>
            <li><a href="#info-general">Información General</a></li>
            <li><a href="#summary-stats">Resumen Estadístico</a></li>
    """
    if fig_spectra:
        sidebar_items += '<li><a href="#spectra-section">Espectros</a></li>\n'
    if valid_params:
        sidebar_items += """
            <li>
                <details class="sidebar-menu-details">
                    <summary>Análisis por Parámetro</summary>
                    <ul style="padding-left: 15px; margin-top: 5px;">
"""
        for param_name, param_id, _ in valid_params:
            onclick_code = f"$('#tab-{param_id}').tab('show'); document.getElementById('tabs-section').scrollIntoView({{behavior: 'smooth'}}); return false;"
            sidebar_items += f'                        <li><a href="#" onclick="{onclick_code}">{param_name}</a></li>\n'
        sidebar_items += """
                    </ul>
                </details>
            </li>
"""
    sidebar_items += """
            <li><a href="#data-table-section">Tabla de Datos</a></li>
        </ul>
"""

    buchi_css = load_buchi_css()
    sidebar_css = get_sidebar_styles()
    common_css = get_common_report_styles()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    year = datetime.now().year

    # IMPORTANTE: este bloque es f-string => JS con llaves debe ir como {{ }}
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

    <!-- jQuery -->
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
    <div class="sidebar">
{sidebar_items}
    </div>

    <div class="main-content">
        <h1>Validation Report</h1>

        <div class="info-box" id="info-general">
            <h2>Información General</h2>
            <table>
                <tr><th>Archivo</th><td>{file_name}</td></tr>
                <tr><th>Fecha de generación</th><td>{timestamp}</td></tr>
                <tr><th>Número de muestras</th><td>{len(df)}</td></tr>
                <tr><th>Parámetros analizados</th><td>{len(valid_params)}</td></tr>
            </table>
            <p class="text-caption">
                <em>Este informe analiza valores predichos vs referencia usando métricas estadísticas (R², RMSE, BIAS).</em>
            </p>
        </div>

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
                    <tr><td><strong>R²</strong></td>
"""
    for row in summary_data:
        html_content += f"<td>{row['R2']:.3f}</td>"

    html_content += """
                    </tr>
                    <tr><td><strong>RMSE</strong></td>
"""
    for row in summary_data:
        html_content += f"<td>{row['RMSE']:.3f}</td>"

    html_content += """
                    </tr>
                    <tr><td><strong>BIAS</strong></td>
"""
    for row in summary_data:
        html_content += f"<td>{row['BIAS']:.3f}</td>"

    html_content += """
                    </tr>
                    <tr><td><strong>N</strong></td>
"""
    for row in summary_data:
        html_content += f"<td>{row['N']}</td>"

    html_content += """
                    </tr>
                </tbody>
            </table>
        </div>
"""

    if fig_spectra is not None:
        spectra_html = _fig_html(fig_spectra) if not plotly_already_included else fig_spectra.to_html(full_html=False, include_plotlyjs=False, config={"responsive": True})
        html_content += f"""
        <div class="info-box" id="spectra-section">
            <h2>Espectros</h2>
            <p class="text-caption"><em>Overlay de todos los espectros NIR (columnas #1..#n).</em></p>
            <div class="plot-container">{spectra_html}</div>
        </div>
"""

    if valid_params:
        html_content += """
        <div class="info-box" id="tabs-section">
            <h2>Análisis por Parámetro</h2>
            <p class="text-caption"><em>Gráficos interactivos para cada parámetro.</em></p>

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

            fig_parity_html = _fig_html(fig_parity) if not plotly_already_included else fig_parity.to_html(full_html=False, include_plotlyjs=False, config={"responsive": True})
            fig_residuum_html = fig_residuum.to_html(full_html=False, include_plotlyjs=False, config={"responsive": True})
            fig_histogram_html = fig_histogram.to_html(full_html=False, include_plotlyjs=False, config={"responsive": True})

            html_content += f"""
                <div class="tab-pane fade {active_class}" id="content-{param_id}" role="tabpanel">
                    <div class="stats-box">
                        <table>
                            <tr><td><strong>R²</strong></td><td><strong>RMSE</strong></td><td><strong>BIAS</strong></td><td><strong>N</strong></td></tr>
                            <tr><td>{r2:.3f}</td><td>{rmse:.3f}</td><td>{bias:.3f}</td><td>{n}</td></tr>
                        </table>
                    </div>

                    <div id="carousel-{param_id}" class="carousel slide" data-ride="carousel" data-interval="false">
                        <ol class="carousel-indicators">
                            <li data-target="#carousel-{param_id}" data-slide-to="0" class="active"></li>
                            <li data-target="#carousel-{param_id}" data-slide-to="1"></li>
                            <li data-target="#carousel-{param_id}" data-slide-to="2"></li>
                        </ol>

                        <div class="carousel-inner">
                            <div class="carousel-item active"><div class="plot-container">{fig_parity_html}</div></div>
                            <div class="carousel-item"><div class="plot-container">{fig_residuum_html}</div></div>
                            <div class="carousel-item"><div class="plot-container">{fig_histogram_html}</div></div>
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

    # Data table (simple)
    html_content += """
        <div class="info-box" id="data-table-section">
            <h2>Tabla de Datos</h2>
            <table id="data-table" class="display nowrap" style="width:100%">
                <thead><tr>
"""
    for col in df.columns:
        html_content += f"<th>{col}</th>"
    html_content += """
                </tr></thead>
                <tbody>
"""
    for _, r in df.iterrows():
        html_content += "<tr>"
        for col in df.columns:
            v = r[col]
            html_content += "<td></td>" if pd.isna(v) else f"<td>{v}</td>"
        html_content += "</tr>"

    html_content += f"""
                </tbody>
            </table>
        </div>

        <div style="margin-top: 50px; padding-top: 20px; border-top: 2px solid #eee; text-align: center; color: #666; font-size: 12px;">
            <p>Informe generado automáticamente por COREF Suite</p>
            <p>Fecha: {timestamp}</p>
            <p>© {year} BÜCHI Labortechnik AG</p>
        </div>
    </div>

    <script>
    $(document).ready(function() {{
        // DataTable con filtros por columna
        $('#data-table thead tr').clone(true).appendTo('#data-table thead');
        $('#data-table thead tr:eq(1) th').each(function(i) {{
            var title = $(this).text();
            $(this).html('<input type="text" placeholder="Filtrar ' + title + '" style="width:100%; padding: 5px; font-size: 12px; box-sizing: border-box;"/>');
        }});

        var table = $('#data-table').DataTable({{
            scrollX: true,
            pageLength: 25,
            fixedHeader: true,
            orderCellsTop: true,
            searching: true
        }});

        $('#data-table thead tr:eq(1) th').each(function(i) {{
            $('input', this).on('keyup change', function() {{
                if (table.column(i).search() !== this.value) {{
                    table.column(i).search(this.value).draw();
                }}
            }});
        }});

        // FIX: autosize Plotly en tabs + carousel
        function forcePlotlyAutosize($root) {{
            $root = $root && $root.length ? $root : $(document);

            var $plots = $root.find(
                '.carousel-item.active .plotly-graph-div, ' +
                '.tab-pane.active .plotly-graph-div'
            );

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
# STREAMLIT UI - FASE 1
# =============================================================================
st.markdown("---")
st.markdown("### 📁 FASE 1: Carga de archivos")
st.info(
    """
1. **Carga** uno o varios archivos TSV
2. **Opcionalmente filtra** por rango de fechas
3. **Procesa** para limpiar y reorganizar los datos
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

    st.markdown("---")
    st.subheader("📅 Filtrado por Fechas (Opcional)")

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        start_date = st.date_input("Fecha de inicio", value=None, help="Dejar vacío para incluir desde el inicio")
    with col2:
        end_date = st.date_input("Fecha de fin", value=None, help="Dejar vacío para incluir hasta el final")
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        clear_dates = st.button("🗑️ Limpiar fechas")

    if clear_dates:
        st.rerun()

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

    if st.button("🔄 Procesar Archivos", type="primary", use_container_width=True, key="process_files_btn"):
        progress_bar = st.progress(0)
        status_text = st.empty()

        st.session_state.processed_data = {}
        st.session_state.samples_to_remove = {}
        st.session_state.last_events = {}

        for idx, uploaded_file in enumerate(uploaded_files, start=1):
            file_name = uploaded_file.name.replace(".tsv", "").replace(".txt", "")
            status_text.text(f"Procesando {file_name}...")

            try:
                df_clean = clean_tsv_file(uploaded_file)
                df_filtered = df_clean.copy()

                if "Date" in df_filtered.columns:
                    rows_before = len(df_filtered)

                    if start_date is not None:
                        df_filtered = df_filtered[df_filtered["Date"] >= pd.Timestamp(start_date)]
                    if end_date is not None:
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

                # ✅ NO reseteamos índice aquí: mantenemos df.index real para selección consistente
                st.session_state.processed_data[file_name] = df_filtered
                st.session_state.samples_to_remove[file_name] = set()

                st.success(f"✅ {file_name} procesado correctamente ({len(df_filtered)} muestras)")

            except Exception as e:
                st.error(f"❌ Error procesando {file_name}: {e}")
                import traceback

                st.code(traceback.format_exc())

            progress_bar.progress(idx / len(uploaded_files))

        status_text.text("✅ Todos los archivos procesados")


# =============================================================================
# FASE 2: PREVISUALIZACIÓN Y SELECCIÓN
# =============================================================================
if st.session_state.processed_data:
    st.markdown("---")
    st.markdown("### 🔍 FASE 2: Previsualización y Selección de Muestras")

    st.info(
        """
**Instrucciones:**
- Haz **click** o usa **Lasso/Box select** para marcar/desmarcar.
- Lo marcado aparece en **rojo**.
- Puedes confirmar eliminación cuando quieras.
"""
    )

    selected_file = st.selectbox(
        "Selecciona archivo para previsualizar:",
        options=list(st.session_state.processed_data.keys()),
        key="file_selector",
    )

    if selected_file:
        df_current = st.session_state.processed_data[selected_file]
        removed_indices = st.session_state.samples_to_remove.get(selected_file, set())

        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric("📊 Total muestras", len(df_current))
        with col_stat2:
            st.metric("🗑️ Marcadas para eliminar", len(removed_indices))
        with col_stat3:
            st.metric("✅ Muestras finales", len(df_current) - len(removed_indices))

        st.markdown("---")

        # -------- Espectros ----------
        st.subheader("📈 Vista de Espectros")
        fig_spectra = build_spectra_figure_interactive(df_current, removed_indices)
        if fig_spectra:
            events = plotly_events(
                fig_spectra,
                click_event=True,
                select_event=True,
                hover_event=False,
                key=f"spectra_{selected_file}",
            )

            if toggle_from_events(events, removed_indices, dedupe_key=f"spectra_{selected_file}"):
                st.session_state.samples_to_remove[selected_file] = removed_indices
                st.rerun()

        st.markdown("---")

        # -------- Parámetros ----------
        st.subheader("📊 Gráficos por Parámetro")

        columns_result = [c for c in df_current.columns if str(c).startswith("Result ")]
        if not columns_result:
            st.warning("No se encontraron columnas 'Result <param>' en este archivo.")
        else:
            param_names = [str(c).replace("Result ", "") for c in columns_result]
            tabs = st.tabs(param_names)

            for tab, result_col in zip(tabs, columns_result):
                param_name = str(result_col).replace("Result ", "")
                reference_col = f"Reference {param_name}"
                residuum_col = f"Residuum {param_name}"

                with tab:
                    plots = plot_comparison_interactive(df_current, result_col, reference_col, residuum_col, removed_indices)
                    if not plots:
                        st.warning(f"No hay datos suficientes para {param_name}.")
                        continue

                    fig_parity, fig_res, fig_hist, r2, rmse, bias, n = plots

                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("R²", f"{r2:.3f}")
                    c2.metric("RMSE", f"{rmse:.3f}")
                    c3.metric("BIAS", f"{bias:.3f}")
                    c4.metric("N", n)

                    subtabs = st.tabs(["Parity Plot", "Residuum vs N", "Histogram"])

                    with subtabs[0]:
                        events = plotly_events(
                            fig_parity,
                            click_event=True,
                            select_event=True,
                            hover_event=False,
                            key=f"parity_{selected_file}_{param_name}",
                        )
                        if toggle_from_events(events, removed_indices, dedupe_key=f"parity_{selected_file}_{param_name}"):
                            st.session_state.samples_to_remove[selected_file] = removed_indices
                            st.rerun()

                    with subtabs[1]:
                        events = plotly_events(
                            fig_res,
                            click_event=True,
                            select_event=True,
                            hover_event=False,
                            key=f"residuum_{selected_file}_{param_name}",
                        )
                        if toggle_from_events(events, removed_indices, dedupe_key=f"residuum_{selected_file}_{param_name}"):
                            st.session_state.samples_to_remove[selected_file] = removed_indices
                            st.rerun()

                    with subtabs[2]:
                        st.plotly_chart(fig_hist, use_container_width=True)

        st.markdown("---")

        # -------- Tabla de marcados ----------
        if removed_indices:
            st.subheader(f"🎯 Muestras Marcadas para Eliminar ({len(removed_indices)})")

            # OJO: removed_indices son df.index
            selected_rows = df_current.loc[sorted(list(removed_indices))].copy()

            display_cols = ["ID", "Date", "Note"]
            if not all(c in selected_rows.columns for c in display_cols):
                display_cols = list(selected_rows.columns[:6])

            st.dataframe(selected_rows[display_cols], use_container_width=True, hide_index=False)

            colA, colB, colC = st.columns([1, 1, 1])

            with colA:
                if st.button("🗑️ Confirmar Eliminación", type="primary", use_container_width=True):
                    df_updated = df_current.drop(index=list(removed_indices))
                    # ✅ aquí sí reseteamos índice para “dataset final limpio”
                    df_updated = df_updated.reset_index(drop=True)

                    st.session_state.processed_data[selected_file] = df_updated
                    st.session_state.samples_to_remove[selected_file] = set()
                    st.session_state.last_events = {}  # reset dedupe
                    st.success("✅ Muestras eliminadas y dataset actualizado.")
                    st.rerun()

            with colB:
                if st.button("↩️ Desmarcar Todas", use_container_width=True):
                    st.session_state.samples_to_remove[selected_file] = set()
                    st.session_state.last_events = {}
                    st.rerun()

            with colC:
                if st.button("💾 Aplicar marcado a todos los parámetros", use_container_width=True):
                    # no hace nada extra: el marcado ya es global al archivo
                    st.info("✅ El marcado ya es global para el archivo (afecta a todos los gráficos).")

        else:
            st.info("👆 Selecciona puntos/líneas en los gráficos para marcarlos para eliminación")


# =============================================================================
# FASE 3: GENERACIÓN FINAL
# =============================================================================
if st.session_state.processed_data:
    st.markdown("---")
    st.markdown("### 📥 FASE 3: Generar Reportes Finales")

    summary_rows = []
    for fname, df in st.session_state.processed_data.items():
        summary_rows.append(
            {"Archivo": fname, "Muestras": len(df), "Parámetros": len([c for c in df.columns if str(c).startswith("Result ")])}
        )
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

    st.markdown("---")

    if st.button("📥 Generar Informes HTML Finales", type="primary", use_container_width=True, key="generate_reports_btn"):
        results: List[ReportResult] = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        items = list(st.session_state.processed_data.items())
        for idx, (file_name, df) in enumerate(items, start=1):
            status_text.text(f"Generando reporte para {file_name}...")
            try:
                html = generate_html_report(df, file_name)
                results.append(ReportResult(name=file_name, html=html, csv=df))
                st.success(f"✅ Reporte generado: {file_name}")
            except Exception as e:
                st.error(f"❌ Error generando reporte para {file_name}: {e}")
                import traceback

                st.code(traceback.format_exc())

            progress_bar.progress(idx / len(items))

        status_text.text("✅ Todos los reportes generados")

        if results:
            st.markdown("---")
            st.subheader("📥 Descargar Reportes")

            if len(results) > 1:
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    for r in results:
                        zf.writestr(f"{r.name}.html", r.html)

                st.download_button(
                    label="📦 Descargar todos los reportes (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name="tsv_validation_reports.zip",
                    mime="application/zip",
                    use_container_width=True,
                )
                st.markdown("---")

            for r in results:
                st.markdown(f"**{r.name}**")
                st.download_button(
                    label="💾 Descargar Informe HTML",
                    data=r.html,
                    file_name=f"{r.name}.html",
                    mime="text/html",
                    key=f"html_final_{r.name}",
                )
                st.markdown("---")
