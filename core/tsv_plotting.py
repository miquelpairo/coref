"""
TSV Validation Reports - Plotting Functions (CLOUD + plotly_events SAFE)
========================================================================
- customdata 100% JSON-safe (Python ints/str, no numpy)
- parity: x/y también 100% Python lists (evita Series/np types que rompen plotly_events)
- spectra: idem
- FIX CRÍTICO: Lasso/Box en espectros -> Plotly selecciona PUNTOS; con mode="lines" no suele haber selección.
  => usamos "lines+markers" con markers casi invisibles (size pequeño + opacity muy baja)
"""

from __future__ import annotations

from typing import Dict, Set, Optional, Tuple, List

import numpy as np
import pandas as pd
import plotly.graph_objs as go
from sklearn.metrics import mean_squared_error, r2_score


def create_layout(title: str, xaxis_title: str, yaxis_title: str) -> Dict:
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
    if removed_indices is None:
        removed_indices = set()
    if sample_groups is None:
        sample_groups = {}
    if group_labels is None:
        group_labels = {}

    SAMPLE_GROUPS = _ensure_sample_groups(SAMPLE_GROUPS)

    try:
        # --- numérico robusto (coma decimal) ---
        ref = pd.to_numeric(df[reference_col].astype(str).str.replace(",", ".", regex=False), errors="coerce")
        res = pd.to_numeric(df[result_col].astype(str).str.replace(",", ".", regex=False), errors="coerce")
        resid = pd.to_numeric(df[residuum_col].astype(str).str.replace(",", ".", regex=False), errors="coerce")

        valid_mask = ref.notna() & res.notna() & resid.notna() & (ref != 0) & (res != 0)

        x_s = ref.loc[valid_mask]
        y_s = res.loc[valid_mask]
        residuum_s = resid.loc[valid_mask]

        if len(x_s) < 2:
            return None

        original_indices: List[int] = [int(i) for i in df.loc[valid_mask].index.tolist()]
        valid_removed_indices = removed_indices.intersection(set(original_indices))

        # hover aligned
        if "ID" in df.columns:
            hover_id = df.loc[valid_mask, "ID"].astype(str).reset_index(drop=True)
        else:
            hover_id = pd.Series([str(i) for i in original_indices])

        if "Date" in df.columns:
            hover_date = df.loc[valid_mask, "Date"].astype(str).reset_index(drop=True)
        else:
            hover_date = pd.Series([""] * len(x_s))

        # métricas (forzamos float Python)
        r2 = float(r2_score(x_s, y_s))
        rmse = float(np.sqrt(mean_squared_error(x_s, y_s)))
        bias = float(np.mean(y_s - x_s))
        n = int(len(x_s))

        # IMPORTANT: arrays base como LISTAS Python (plotly_events-safe)
        x_all = [float(v) for v in x_s.to_numpy()]
        y_all = [float(v) for v in y_s.to_numpy()]
        residuum_all = [float(v) for v in residuum_s.to_numpy()]

        # Clasificar puntos por grupo (posiciones sobre x_all/y_all)
        points_by_group = {g: [] for g in SAMPLE_GROUPS.keys()}
        points_by_group["delete"] = []

        for pos, idx in enumerate(original_indices):
            if idx in valid_removed_indices:
                points_by_group["delete"].append(pos)
            else:
                g = sample_groups.get(idx, "none")
                if g not in points_by_group:
                    g = "none"
                points_by_group[g].append(pos)

        def _make_cd(positions: list) -> list:
            # [[row_index(int), date(str)], ...]
            row_ids = [int(original_indices[p]) for p in positions]
            dates = [str(hover_date.iloc[p]) for p in positions]
            return [[rid, d] for rid, d in zip(row_ids, dates)]

        def _xy_from_positions(positions: list) -> tuple[list, list]:
            return ([x_all[p] for p in positions], [y_all[p] for p in positions])

        # -------------------------
        # Parity plot
        # -------------------------
        fig_parity = go.Figure()

        # grupos (excluye none)
        for group_name, group_config in SAMPLE_GROUPS.items():
            if group_name == "none":
                continue
            pos = points_by_group.get(group_name, [])
            if not pos:
                continue

            custom_label = group_labels.get(group_name, group_name)
            display_label = f"{group_config.get('emoji','')} {custom_label}".strip()

            xg, yg = _xy_from_positions(pos)
            cd = _make_cd(pos)

            fig_parity.add_trace(
                go.Scatter(
                    x=xg,
                    y=yg,
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

        # none
        pos_none = points_by_group.get("none", [])
        if pos_none:
            cfg = SAMPLE_GROUPS["none"]
            xg, yg = _xy_from_positions(pos_none)
            cd = _make_cd(pos_none)

            fig_parity.add_trace(
                go.Scatter(
                    x=xg,
                    y=yg,
                    mode="markers",
                    marker=dict(
                        color=cfg.get("color", "gray"),
                        size=cfg.get("size", 8),
                        symbol=cfg.get("symbol", "circle"),
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

        # delete
        pos_del = points_by_group.get("delete", [])
        if pos_del:
            xd, yd = _xy_from_positions(pos_del)
            cd = _make_cd(pos_del)

            fig_parity.add_trace(
                go.Scatter(
                    x=xd,
                    y=yd,
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

        # líneas de referencia (listas Python)
        fig_parity.add_trace(
            go.Scatter(
                x=x_all,
                y=x_all,
                mode="lines",
                line=dict(dash="dash", color="gray"),
                name="y = x",
                showlegend=False,
            )
        )
        fig_parity.add_trace(
            go.Scatter(
                x=x_all,
                y=[v + rmse for v in x_all],
                mode="lines",
                line=dict(dash="dash", color="orange"),
                name="RMSE+",
                showlegend=False,
            )
        )
        fig_parity.add_trace(
            go.Scatter(
                x=x_all,
                y=[v - rmse for v in x_all],
                mode="lines",
                line=dict(dash="dash", color="orange"),
                name="RMSE-",
                showlegend=False,
            )
        )

        fig_parity.update_layout(**create_layout("Parity Plot", reference_col, result_col))
        fig_parity.update_layout(clickmode="event+select")

        # -------------------------
        # Residuum vs N (ordenado por fecha)
        # -------------------------
        if "Date" in df.columns:
            # argsort devuelve numpy => convertir a lista de ints python
            date_col = df.loc[valid_mask, "Date"].astype(str).reset_index(drop=True)
            sort_idx = [int(i) for i in np.argsort(date_col.to_numpy())]

            residuum_sorted = [residuum_all[i] for i in sort_idx]
            hover_id_sorted = [str(hover_id.iloc[i]) for i in sort_idx]
            hover_date_sorted = [str(hover_date.iloc[i]) for i in sort_idx]
            original_indices_sorted = [int(original_indices[i]) for i in sort_idx]
        else:
            residuum_sorted = residuum_all
            hover_id_sorted = [str(v) for v in hover_id.to_list()]
            hover_date_sorted = [str(v) for v in hover_date.to_list()]
            original_indices_sorted = [int(v) for v in original_indices]

        hovertext_res = [
            f"RowIndex: {idx}<br>Date: {d}<br>ID: {idv}<br>Residuum: {rv:.2f}"
            for idx, idv, d, rv in zip(original_indices_sorted, hover_id_sorted, hover_date_sorted, residuum_sorted)
        ]

        colors = []
        for idx in original_indices_sorted:
            if idx in valid_removed_indices:
                colors.append("red")
            else:
                g = sample_groups.get(idx, "none")
                cfg = SAMPLE_GROUPS.get(g, SAMPLE_GROUPS["none"])
                colors.append(cfg.get("color", "gray"))

        fig_res = go.Figure(
            go.Bar(
                x=list(range(len(residuum_sorted))),
                y=residuum_sorted,
                hovertext=hovertext_res,
                hoverinfo="text",
                name="Residuum",
                marker=dict(color=colors),
            )
        )
        fig_res.update_layout(**create_layout("Residuum vs N (ordenado por fecha)", "N", "Residuum"))

        # histograma
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Histogram(x=residuum_sorted, nbinsx=20, marker=dict(color="blue")))
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
    import re

    if removed_indices is None:
        removed_indices = set()
    if sample_groups is None:
        sample_groups = {}
    if group_labels is None:
        group_labels = {}

    SAMPLE_GROUPS = _ensure_sample_groups(SAMPLE_GROUPS)

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
    x_full = [_pixnum(c) for c in pixel_cols]  # python ints

    # Matriz espectral (igual que ya tenías)
    spec = (
        df[pixel_cols]
        .astype(str)
        .replace(",", ".", regex=True)
        .apply(pd.to_numeric, errors="coerce")
    )

    hover_id = df["ID"].astype(str) if "ID" in df.columns else pd.Series([str(i) for i in df.index], index=df.index)
    hover_date = df["Date"].astype(str) if "Date" in df.columns else pd.Series([""] * len(df), index=df.index)
    hover_note = df["Note"].astype(str) if "Note" in df.columns else pd.Series([""] * len(df), index=df.index)

    # ✅ STRIDE AUTO: optimiza rendimiento
    n_spec = int(len(df))
    if n_spec <= 250:
        stride = 6   # 300-600 px -> 50-100 puntos seleccionables por espectro
    elif n_spec <= 600:
        stride = 10
    else:
        stride = 15  # casos de 1000 espectros

    x_sel = x_full[::stride]  # puntos para selección

    fig = go.Figure()
    legend_added = set()

    for i in df.index:
        y_np = spec.loc[i].to_numpy()
        if np.all(np.isnan(y_np)):
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

        # y como lista Python
        y_full = [float(v) if np.isfinite(v) else None for v in y_np]
        y_sel = y_full[::stride]

        # 1) ✅ LÍNEA COMPLETA (barata, sin markers)
        fig.add_trace(
            go.Scatter(
                x=x_full,
                y=y_full,
                mode="lines",
                showlegend=show_legend,
                legendgroup=legend_group,
                name=legend_name,
                line={"width": width, "color": color},
                opacity=opacity,
                hoverinfo="skip",   # reduce peso
            )
        )

        # 2) ✅ MARKERS DOWN-SAMPLED (solo para selección)
        # customdata SOLO aquí, y 1 por punto
        cd_sel = [int(i)] * len(x_sel)

        fig.add_trace(
            go.Scatter(
                x=x_sel,
                y=y_sel,
                mode="markers",
                showlegend=False,
                legendgroup=legend_group,
                marker={"size": 6, "opacity": 0.01},  # seleccionable pero invisible
                opacity=1.0,
                customdata=cd_sel,
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
