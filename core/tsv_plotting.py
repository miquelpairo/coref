"""
TSV Validation Reports - Plotting Functions (CLOUD + plotly_events SAFE)
========================================================================
Funciones para generar gráficos Plotly con soporte de grupos.

Cambios clave para que NO se queden vacíos con streamlit-plotly-events (Cloud):
- customdata 100% JSON-safe: SOLO listas/ints/str de Python (NO numpy arrays, NO np.int64)
- conversión robusta a numérico en parity (soporta coma decimal)
- PIXEL_RE robusto (#123 y 123 por defecto) + parseo de pixel seguro
- defensivo si SAMPLE_GROUPS llega None o falta 'none'
- clickmode "event+select" para facilitar eventos
"""

from __future__ import annotations

from typing import Dict, Set, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objs as go
from sklearn.metrics import mean_squared_error, r2_score


def create_layout(title: str, xaxis_title: str, yaxis_title: str) -> Dict:
    """Layout estándar para gráficos Plotly"""
    return {
        "title": title,
        "xaxis_title": xaxis_title,
        "yaxis_title": yaxis_title,
        "showlegend": True,
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


def _ensure_sample_groups(sample_groups_cfg: Optional[Dict]) -> Dict:
    """Garantiza que SAMPLE_GROUPS exista y contenga al menos 'none'."""
    if not sample_groups_cfg:
        sample_groups_cfg = {}
    if "none" not in sample_groups_cfg:
        sample_groups_cfg["none"] = {"color": "gray", "size": 8, "symbol": "circle", "emoji": "•"}
    return sample_groups_cfg


def plot_comparison_preview(
    df: pd.DataFrame,
    result_col: str,
    reference_col: str,
    residuum_col: str,
    removed_indices: Set[int] = None,
    sample_groups: Dict[int, str] = None,
    group_labels: Dict[str, str] = None,
    SAMPLE_GROUPS: Dict = None,
) -> Optional[Tuple]:
    """
    Genera gráficos de previsualización con grupos.

    Returns:
        Tuple(fig_parity, fig_residuum, fig_histogram, r2, rmse, bias, n) o None
    """
    if removed_indices is None:
        removed_indices = set()
    if sample_groups is None:
        sample_groups = {}
    if group_labels is None:
        group_labels = {}

    SAMPLE_GROUPS = _ensure_sample_groups(SAMPLE_GROUPS)

    try:
        # -------------------------
        # Convertir a numérico robusto (soporta coma decimal)
        # -------------------------
        ref = df[reference_col].astype(str).str.replace(",", ".", regex=False)
        res = df[result_col].astype(str).str.replace(",", ".", regex=False)
        resid = df[residuum_col].astype(str).str.replace(",", ".", regex=False)

        ref = pd.to_numeric(ref, errors="coerce")
        res = pd.to_numeric(res, errors="coerce")
        resid = pd.to_numeric(resid, errors="coerce")

        valid_mask = ref.notna() & res.notna() & resid.notna() & (ref != 0) & (res != 0)

        x = ref.loc[valid_mask]
        y = res.loc[valid_mask]
        residuum = resid.loc[valid_mask]

        if len(x) < 2:
            return None

        # índices reales del dataframe (lo que queremos recuperar al clicar)
        original_indices = df.loc[valid_mask].index.tolist()
        valid_removed_indices = removed_indices.intersection(set(original_indices))

        # hover data alineado a x/y
        if "ID" in df.columns:
            hover_id = df.loc[valid_mask, "ID"].astype(str)
        else:
            hover_id = pd.Series([str(i) for i in original_indices], index=x.index)

        if "Date" in df.columns:
            hover_date = df.loc[valid_mask, "Date"].astype(str)
        else:
            hover_date = pd.Series([""] * len(x), index=x.index)

        # métricas
        r2 = float(r2_score(x, y))
        rmse = float(np.sqrt(mean_squared_error(x, y)))
        bias = float(np.mean(y - x))
        n = int(len(x))

        # Clasificar puntos por grupo (posiciones i sobre x/y)
        points_by_group = {group: [] for group in SAMPLE_GROUPS.keys()}
        points_by_group["delete"] = []

        for i, idx in enumerate(original_indices):
            if idx in valid_removed_indices:
                points_by_group["delete"].append(i)
            else:
                group = sample_groups.get(idx, "none")
                if group not in points_by_group:
                    group = "none"
                points_by_group[group].append(i)

        # -------------------------
        # Parity plot
        # -------------------------
        fig_parity = go.Figure()

        def _make_cd(indices_list: list) -> list:
            """customdata JSON-safe: [[row_index(int), date(str)], ...]"""
            row_ids = [int(original_indices[i]) for i in indices_list]
            dates = [str(hover_date.iloc[i]) for i in indices_list]
            return [[rid, d] for rid, d in zip(row_ids, dates)]

        # Grupos (excluye none)
        for group_name, group_config in SAMPLE_GROUPS.items():
            if group_name == "none":
                continue

            indices = points_by_group.get(group_name, [])
            if not indices:
                continue

            custom_label = group_labels.get(group_name, group_name)
            display_label = f"{group_config.get('emoji','')} {custom_label}".strip()

            x_group = pd.to_numeric(x.iloc[indices], errors="coerce").astype(float)
            y_group = pd.to_numeric(y.iloc[indices], errors="coerce").astype(float)

            cd = _make_cd(indices)

            fig_parity.add_trace(
                go.Scatter(
                    x=x_group,
                    y=y_group,
                    mode="markers",
                    marker=dict(
                        color=group_config.get("color", "gray"),
                        size=group_config.get("size", 8),
                        symbol=group_config.get("symbol", "circle"),
                    ),
                    name=display_label,
                    customdata=cd,
                    hovertemplate=(
                        f"{display_label}<br>"
                        "RowIndex: %{customdata[0]}<br>"
                        "Date: %{customdata[1]}<br>"
                        "Reference: %{x:.2f}<br>"
                        "Result: %{y:.2f}<extra></extra>"
                    ),
                )
            )

        # Puntos 'none'
        indices_none = points_by_group.get("none", [])
        if indices_none:
            group_config = SAMPLE_GROUPS["none"]
            x_group = pd.to_numeric(x.iloc[indices_none], errors="coerce").astype(float)
            y_group = pd.to_numeric(y.iloc[indices_none], errors="coerce").astype(float)
            cd = _make_cd(indices_none)

            fig_parity.add_trace(
                go.Scatter(
                    x=x_group,
                    y=y_group,
                    mode="markers",
                    marker=dict(
                        color=group_config.get("color", "gray"),
                        size=group_config.get("size", 8),
                        symbol=group_config.get("symbol", "circle"),
                    ),
                    name="Sin grupo",
                    showlegend=True,
                    customdata=cd,
                    hovertemplate=(
                        "Sin grupo<br>"
                        "RowIndex: %{customdata[0]}<br>"
                        "Date: %{customdata[1]}<br>"
                        "Reference: %{x:.2f}<br>"
                        "Result: %{y:.2f}<extra></extra>"
                    ),
                )
            )

        # Puntos para eliminar
        indices_delete = points_by_group.get("delete", [])
        if indices_delete:
            x_remove = pd.to_numeric(x.iloc[indices_delete], errors="coerce").astype(float)
            y_remove = pd.to_numeric(y.iloc[indices_delete], errors="coerce").astype(float)
            cd = _make_cd(indices_delete)

            fig_parity.add_trace(
                go.Scatter(
                    x=x_remove,
                    y=y_remove,
                    mode="markers",
                    marker=dict(color="red", size=10, symbol="x"),
                    name="❌ Eliminar",
                    customdata=cd,
                    hovertemplate=(
                        "⚠️ MARCADO PARA ELIMINAR<br>"
                        "RowIndex: %{customdata[0]}<br>"
                        "Date: %{customdata[1]}<br>"
                        "Reference: %{x:.2f}<br>"
                        "Result: %{y:.2f}<extra></extra>"
                    ),
                )
            )

        # Líneas de referencia
        fig_parity.add_trace(
            go.Scatter(
                x=x,
                y=x,
                mode="lines",
                line=dict(dash="dash", color="gray"),
                name="y = x",
                showlegend=False,
            )
        )
        fig_parity.add_trace(
            go.Scatter(
                x=x,
                y=x + rmse,
                mode="lines",
                line=dict(dash="dash", color="orange"),
                name="RMSE+",
                showlegend=False,
            )
        )
        fig_parity.add_trace(
            go.Scatter(
                x=x,
                y=x - rmse,
                mode="lines",
                line=dict(dash="dash", color="orange"),
                name="RMSE-",
                showlegend=False,
            )
        )

        fig_parity.update_layout(**create_layout("Parity Plot", reference_col, result_col))
        fig_parity.update_layout(clickmode="event+select")

        # -------------------------
        # Residuum vs N - ORDENADO POR FECHA
        # -------------------------
        if "Date" in df.columns:
            date_col = df.loc[valid_mask, "Date"].astype(str)
            sort_indices = date_col.argsort()

            residuum = residuum.iloc[sort_indices]
            hover_id = hover_id.iloc[sort_indices]
            hover_date = hover_date.iloc[sort_indices]
            original_indices = [original_indices[i] for i in sort_indices]

        hovertext_res = [
            f"RowIndex: {idx}<br>Date: {date_val}<br>ID: {id_val}<br>Residuum: {res_val:.2f}"
            for idx, id_val, date_val, res_val in zip(original_indices, hover_id, hover_date, residuum)
        ]

        colors = []
        for idx in original_indices:
            if idx in valid_removed_indices:
                colors.append("red")
            else:
                group = sample_groups.get(idx, "none")
                group_cfg = SAMPLE_GROUPS.get(group, SAMPLE_GROUPS["none"])
                colors.append(group_cfg.get("color", "gray"))

        fig_res = go.Figure(
            go.Bar(
                x=list(range(len(residuum))),
                y=residuum,
                hovertext=hovertext_res,
                hoverinfo="text",
                name="Residuum",
                marker=dict(color=colors),
            )
        )
        fig_res.update_layout(**create_layout("Residuum vs N (ordenado por fecha)", "N", "Residuum"))

        # -------------------------
        # Histograma
        # -------------------------
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Histogram(x=residuum, nbinsx=20, marker=dict(color="blue")))
        layout_hist = create_layout("Residuum Histogram", "Residuum", "Count")
        layout_hist["showlegend"] = False
        fig_hist.update_layout(**layout_hist)

        return fig_parity, fig_res, fig_hist, r2, rmse, bias, n

    except Exception:
        return None


def build_spectra_figure_preview(
    df: pd.DataFrame,
    removed_indices: Set[int] = None,
    sample_groups: Dict[int, str] = None,
    group_labels: Dict[str, str] = None,
    SAMPLE_GROUPS: Dict = None,
    PIXEL_RE=None,
) -> Optional[go.Figure]:
    """
    Genera figura de espectros con grupos

    IMPORTANTE para plotly_events:
    - customdata debe ser LISTA python (no numpy) para que el componente no falle en Cloud.
    """
    import re

    if removed_indices is None:
        removed_indices = set()
    if sample_groups is None:
        sample_groups = {}
    if group_labels is None:
        group_labels = {}

    SAMPLE_GROUPS = _ensure_sample_groups(SAMPLE_GROUPS)

    # regex por defecto: '#123' o '123'
    if PIXEL_RE is None:
        PIXEL_RE = re.compile(r"^(#)?\d+$")

    def _is_pixel_col(col: str) -> bool:
        return bool(PIXEL_RE.fullmatch(str(col)))

    def _pixnum(col: str) -> int:
        s = str(col)
        return int(s[1:]) if s.startswith("#") else int(s)

    valid_removed = removed_indices.intersection(set(df.index))

    pixel_cols = [c for c in df.columns if _is_pixel_col(c)]
    if not pixel_cols:
        return None

    pixel_cols = sorted(pixel_cols, key=_pixnum)
    x = [_pixnum(c) for c in pixel_cols]  # python ints

    spec = (
        df[pixel_cols]
        .astype(str)
        .replace(",", ".", regex=True)
        .apply(pd.to_numeric, errors="coerce")
    )

    hover_id = df["ID"].astype(str) if "ID" in df.columns else pd.Series([str(i) for i in df.index], index=df.index)
    hover_date = df["Date"].astype(str) if "Date" in df.columns else pd.Series([""] * len(df), index=df.index)
    hover_note = df["Note"].astype(str) if "Note" in df.columns else pd.Series([""] * len(df), index=df.index)

    fig = go.Figure()
    legend_added = set()

    for i in df.index:
        y = spec.loc[i].to_numpy()

        if np.all(np.isnan(y)):
            continue

        if i in valid_removed:
            color = "red"
            opacity = 0.7
            width = 2
            prefix = "⚠️ MARCADO - "
            legend_name = "❌ Eliminar"
            legend_group = "delete"
        else:
            group = sample_groups.get(i, "none")
            group_config = SAMPLE_GROUPS.get(group, SAMPLE_GROUPS["none"])
            color = group_config.get("color", "gray")
            opacity = 0.5 if group != "none" else 0.35
            width = 2 if group != "none" else 1
            legend_group = group if group in SAMPLE_GROUPS else "none"

            if group != "none" and group in SAMPLE_GROUPS:
                custom_label = group_labels.get(group, group)
                prefix = f"{group_config.get('emoji','')} {custom_label} - ".strip() + " "
                legend_name = f"{group_config.get('emoji','')} {custom_label}".strip()
            else:
                prefix = ""
                legend_name = "Sin grupo"

        show_legend = legend_group not in legend_added
        if show_legend:
            legend_added.add(legend_group)

        # customdata LIST python por punto (JSON-safe)
        cd = [int(i)] * len(x)

        fig.add_trace(
            go.Scatter(
                x=x,
                y=[float(v) if np.isfinite(v) else None for v in y],  # lista python
                mode="lines",
                showlegend=show_legend,
                legendgroup=legend_group,
                name=legend_name,
                line={"width": width, "color": color},
                opacity=opacity,
                customdata=cd,
                hovertemplate=(
                    f"{prefix}RowIndex: %{{customdata}}<br>"
                    f"ID: {hover_id.loc[i]}<br>"
                    f"Date: {hover_date.loc[i]}<br>"
                    f"Note: {hover_note.loc[i]}<br>"
                    "Pixel: %{x}<br>"
                    "Abs: %{y}<extra></extra>"
                ),
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
        yaxis={"gridcolor": "white"},
        showlegend=True,
        clickmode="event+select",
    )
    return fig
