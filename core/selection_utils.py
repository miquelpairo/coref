"""
selection_utils.py
==================
Utilidades para extracción de eventos de selección desde gráficos Plotly.
Maneja clicks individuales y selecciones múltiples (lasso/box).

FIXES (filtros + cloud + plotly_events):
- create_event_id: soporta pointIndex (además de pointNumber) y añade x/y para evitar colisiones
- extract_row_index_from_click: prioriza event["customdata"] y soporta pointIndex
- extract_row_indices_*: fallback usa pointIndex si pointNumber no está
- Todo defensivo y JSON-safe
"""

from __future__ import annotations

from typing import List, Optional, Any, Tuple
import json
import hashlib

import plotly.graph_objects as go


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _safe_int(x: Any) -> Optional[int]:
    """Int robusto (acepta int/str/np types)."""
    if x is None:
        return None
    try:
        return int(x)
    except Exception:
        return None


def _first_if_seq(x: Any) -> Any:
    """Si x es (list/tuple) devuelve primer elemento; si no, devuelve x."""
    if isinstance(x, (list, tuple)) and len(x) > 0:
        return x[0]
    return x


def _normalize_customdata_for_id(cd: Any) -> Any:
    """
    Normaliza customdata para que sea estable en create_event_id.
    - Parity: [row_id, date, ...] -> row_id
    - Spectra markers: escalar row_id (pero por si llega lista)
    """
    return _first_if_seq(cd)


def _event_point_number(e: dict) -> Any:
    """Devuelve pointNumber o (fallback) pointIndex."""
    return e.get("pointNumber", e.get("pointIndex"))


def _remove_duplicates_preserve_order(items: List[int]) -> List[int]:
    """Elimina duplicados preservando orden."""
    seen = set()
    out: List[int] = []
    for it in items:
        if it not in seen:
            seen.add(it)
            out.append(it)
    return out


# -----------------------------------------------------------------------------
# Event ID / dedupe
# -----------------------------------------------------------------------------
def create_event_id(events: List[dict]) -> str:
    """
    Crea un ID único para un conjunto de eventos.
    Útil para detectar si un evento ya fue procesado.

    Nota: plotly_events a veces usa pointIndex en lugar de pointNumber
    (especialmente en lasso/box). Incluimos x/y para evitar colisiones.

    IMPORTANTE: usamos md5 (estable) en lugar de hash() de Python (no estable entre procesos).
    """
    if not events:
        return ""

    payload: List[Tuple[Any, Any, Any, Any, Any]] = []
    for e in events:
        payload.append(
            (
                e.get("curveNumber"),
                _event_point_number(e),
                _normalize_customdata_for_id(e.get("customdata")),
                e.get("x"),
                e.get("y"),
            )
        )

    # Orden-independiente (por si Plotly devuelve eventos en distinto orden)
    payload_sorted = sorted(payload, key=lambda t: (t[0], t[1], str(t[2]), str(t[3]), str(t[4])))

    s = json.dumps(payload_sorted, ensure_ascii=True, sort_keys=False)
    return hashlib.md5(s.encode("utf-8")).hexdigest()[:16]


# -----------------------------------------------------------------------------
# Click (spectra)
# -----------------------------------------------------------------------------
def extract_row_index_from_click(fig: go.Figure, event: dict) -> Optional[int]:
    """
    Extrae el índice de fila desde un evento de click.

    Regla:
    - Preferir event["customdata"] (más fiable, especialmente con trazas múltiples)
    - Fallback: leer desde fig.data[curveNumber].customdata[pointNumber/pointIndex]
    """
    if not event:
        return None

    # 1) Preferir customdata del evento (típico en markers)
    cd_ev = event.get("customdata", None)
    if cd_ev is not None:
        cd_ev = _first_if_seq(cd_ev)
        rid = _safe_int(cd_ev)
        if rid is not None:
            return rid

    curve_number = event.get("curveNumber", None)
    if curve_number is None:
        return None

    point_number = _event_point_number(event)

    try:
        trace = fig.data[curve_number]
        customdata = getattr(trace, "customdata", None)
        if not customdata:
            return None

        if point_number is None:
            cd = customdata[0]
        else:
            cd = customdata[int(point_number)]

        cd = _first_if_seq(cd)
        return _safe_int(cd)
    except Exception:
        return None


# -----------------------------------------------------------------------------
# Multi-select (spectra)
# -----------------------------------------------------------------------------
def extract_row_indices_from_spectra_events(fig: go.Figure, events: List[dict]) -> List[int]:
    """
    Extrae índices de fila desde eventos de espectros (lasso/box).

    En tu plotting actual:
    - En markers downsampled: event["customdata"] == row_index (int)
    - Puede haber eventos sin customdata (p.ej. trazas de líneas) => ignorar
    """
    if not events:
        return []

    indices: List[int] = []

    for ev in events:
        # 1) Preferir customdata del evento
        cd_ev = ev.get("customdata", None)
        cd_ev = _first_if_seq(cd_ev)
        rid = _safe_int(cd_ev)
        if rid is not None:
            indices.append(rid)
            continue

        # 2) Fallback: leer customdata desde la traza
        try:
            curve = ev.get("curveNumber", None)
            point = _event_point_number(ev)

            if curve is None or point is None:
                continue

            trace_cd = getattr(fig.data[curve], "customdata", None)
            if not trace_cd:
                continue

            cd = trace_cd[int(point)]
            cd = _first_if_seq(cd)
            rid = _safe_int(cd)
            if rid is not None:
                indices.append(rid)
        except Exception:
            pass

    return _remove_duplicates_preserve_order(indices)


# -----------------------------------------------------------------------------
# Multi-select / click (parity)
# -----------------------------------------------------------------------------
def extract_row_indices_from_parity_events(fig: go.Figure, events: List[dict]) -> List[int]:
    """
    Extrae índices de fila desde eventos de parity (lasso/box/click).

    En tu plotting:
    - customdata suele ser [row_id, date] => row_id = customdata[0]
    - Puede haber trazas sin customdata (y=x, RMSE±) => ignorar / fallback
    """
    if not events:
        return []

    indices: List[int] = []

    def _coerce_parity_cd(cd: Any) -> Optional[int]:
        cd = _first_if_seq(cd)
        return _safe_int(cd)

    for ev in events:
        # 1) Preferir customdata del evento
        rid = _coerce_parity_cd(ev.get("customdata", None))
        if rid is not None:
            indices.append(rid)
            continue

        # 2) Fallback: leer desde la traza usando curve/point
        try:
            curve = ev.get("curveNumber", None)
            point = _event_point_number(ev)

            if curve is None or point is None:
                continue

            trace_cd = getattr(fig.data[curve], "customdata", None)
            if not trace_cd:
                continue

            rid = _coerce_parity_cd(trace_cd[int(point)])
            if rid is not None:
                indices.append(rid)
        except Exception:
            pass

    return _remove_duplicates_preserve_order(indices)


# -----------------------------------------------------------------------------
# Validation
# -----------------------------------------------------------------------------
def validate_indices_against_dataframe(indices: List[int], valid_indices: List[int]) -> List[int]:
    """
    Valida que los índices extraídos existan en el DataFrame actual.
    """
    valid_set = set(valid_indices)
    return [idx for idx in indices if idx in valid_set]
