"""
TSV Validation Reports - Plotting Functions
============================================
Funciones para generar gráficos Plotly con soporte de grupos
ACTUALIZADO: Leyendas en gráfico de espectros
MOD: Añadido customdata para selección desde gráfico (streamlit-plotly-events)
"""

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


def plot_comparison_preview(
    df: pd.DataFrame,
    result_col: str,
    reference_col: str,
    residuum_col: str,
    removed_indices: Set[int] = None,
    sample_groups: Dict[int, str] = None,
    group_labels: Dict[str, str] = None,
    SAMPLE_GROUPS: Dict = None
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

        # ✅ índices reales del dataframe (lo que queremos recuperar al clicar)
        original_indices = df.loc[valid_mask].loc[aligned_mask].index.tolist()
        valid_removed_indices = removed_indices.intersection(set(original_indices))

        # ✅ hover con índices alineados a x/y (evita desalineos)
        if "ID" in df.columns:
            hover_id = df.loc[valid_mask, "ID"].loc[aligned_mask].astype(str)
        else:
            hover_id = pd.Series([str(i) for i in original_indices], index=x.index)

        if "Date" in df.columns:
            hover_date = df.loc[valid_mask, "Date"].loc[aligned_mask].astype(str)
        else:
            hover_date = pd.Series([""] * len(x), index=x.index)

        r2 = float(r2_score(x, y))
        rmse = float(np.sqrt(mean_squared_error(x, y)))
        bias = float(np.mean(y - x))
        n = int(len(x))

        # Clasificar puntos por grupo (guardamos posiciones i sobre x/y)
        points_by_group = {group: [] for group in SAMPLE_GROUPS.keys()}
        points_by_group["delete"] = []

        for i, idx in enumerate(original_indices):
            if idx in valid_removed_indices:
                points_by_group["delete"].append(i)
            else:
                group = sample_groups.get(idx, "none")
                points_by_group[group].append(i)

        # -------------------------
        # Parity plot
        # -------------------------
        fig_parity = go.Figure()

        # Grupos Set 1..4 (excluye none)
        for group_name, group_config in SAMPLE_GROUPS.items():
            if group_name == "none":
                continue

            indices = points_by_group.get(group_name, [])
            if indices:
                custom_label = group_labels.get(group_name, group_name)
                display_label = f"{group_config['emoji']} {custom_label}"

                x_group = x.iloc[indices]
                y_group = y.iloc[indices]

                # ✅ customdata: [row_index, date_str]
                row_ids = [original_indices[i] for i in indices]
                dates = [str(hover_date.iloc[i]) for i in indices]
                cd = np.column_stack([row_ids, dates]).tolist()

                fig_parity.add_trace(go.Scatter(
                    x=x_group,
                    y=y_group,
                    mode="markers",
                    marker=dict(
                        color=group_config["color"],
                        size=group_config["size"],
                        symbol=group_config["symbol"]
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
                ))

        # Puntos 'none'
        indices = points_by_group.get("none", [])
        if indices:
            group_config = SAMPLE_GROUPS["none"]
            x_group = x.iloc[indices]
            y_group = y.iloc[indices]

            row_ids = [original_indices[i] for i in indices]
            dates = [str(hover_date.iloc[i]) for i in indices]
            cd = np.column_stack([row_ids, dates]).tolist()

            fig_parity.add_trace(go.Scatter(
                x=x_group,
                y=y_group,
                mode="markers",
                marker=dict(
                    color=group_config["color"],
                    size=group_config["size"],
                    symbol=group_config["symbol"]
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
            ))

        # Puntos para eliminar
        indices_delete = points_by_group.get("delete", [])
        if indices_delete:
            x_remove = x.iloc[indices_delete]
            y_remove = y.iloc[indices_delete]

            row_ids = [original_indices[i] for i in indices_delete]
            dates = [str(hover_date.iloc[i]) for i in indices_delete]
            cd = np.column_stack([row_ids, dates]).tolist()

            fig_parity.add_trace(go.Scatter(
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
            ))

        # Líneas de referencia
        fig_parity.add_trace(go.Scatter(
            x=x, y=x,
            mode="lines",
            line=dict(dash="dash", color="gray"),
            name="y = x",
            showlegend=False
        ))
        fig_parity.add_trace(go.Scatter(
            x=x, y=x + rmse,
            mode="lines",
            line=dict(dash="dash", color="orange"),
            name="RMSE",
            showlegend=False
        ))
        fig_parity.add_trace(go.Scatter(
            x=x, y=x - rmse,
            mode="lines",
            line=dict(dash="dash", color="orange"),
            name="RMSE",
            showlegend=False
        ))

        fig_parity.update_layout(**create_layout("Parity Plot", reference_col, result_col))

        # -------------------------
        # Residuum vs N - ORDENADO POR FECHA
        # -------------------------
        if "Date" in df.columns:
            date_col = df.loc[valid_mask, "Date"].loc[aligned_mask]
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
                colors.append(SAMPLE_GROUPS[group]["color"])

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
    PIXEL_RE=None
) -> Optional[go.Figure]:
    """
    Genera figura de espectros con grupos
    ACTUALIZADO: Muestra leyenda de grupos
    MOD: Añadido customdata para selección desde gráfico (streamlit-plotly-events)
    """
    import re

    if removed_indices is None:
        removed_indices = set()
    if sample_groups is None:
        sample_groups = {}
    if group_labels is None:
        group_labels = {}
    if PIXEL_RE is None:
        PIXEL_RE = re.compile(r"^#\d+$")

    def _is_pixel_col(col: str) -> bool:
        return bool(PIXEL_RE.fullmatch(str(col)))

    valid_removed = removed_indices.intersection(set(df.index))

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
            group_config = SAMPLE_GROUPS[group]
            color = group_config["color"]
            opacity = 0.5 if group != "none" else 0.35
            width = 2 if group != "none" else 1
            legend_group = group

            if group != "none":
                custom_label = group_labels.get(group, group)
                prefix = f"{group_config['emoji']} {custom_label} - "
                legend_name = f"{group_config['emoji']} {custom_label}"
            else:
                prefix = ""
                legend_name = "Sin grupo"

        show_legend = legend_group not in legend_added
        if show_legend:
            legend_added.add(legend_group)

        # ✅ customdata como escalar por punto (más compatible con plotly_events)
        cd = np.full(len(x), int(i))

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
                customdata=cd,
                hovertemplate=(
                    f"{prefix}RowIndex: %{{customdata}}<br>"
                    f"ID: {hover_id.loc[i]}<br>"
                    f"Date: {hover_date.loc[i]}<br>"
                    f"Note: {hover_note.loc[i]}<br>"
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
        yaxis={"gridcolor": "white"},
        showlegend=True
    )
    return fig
