"""
selection_utils.py
==================
Utilidades para extracción de eventos de selección desde gráficos Plotly.
Maneja clicks individuales y selecciones múltiples (lasso/box).
"""

from typing import List, Optional
import plotly.graph_objects as go


def create_event_id(events: List[dict]) -> str:
    """
    Crea un ID único para un conjunto de eventos.
    Útil para detectar si un evento ya fue procesado.
    
    Args:
        events: Lista de eventos de Plotly
        
    Returns:
        String hash único del conjunto de eventos
    """
    if not events:
        return ""
    
    event_str = str([
        (e.get("curveNumber"), e.get("pointNumber"), e.get("customdata"))
        for e in events
    ])
    
    return str(hash(event_str))


def extract_row_index_from_click(fig: go.Figure, event: dict) -> Optional[int]:
    """
    Extrae el índice de fila desde un evento de click en gráfico de espectros.
    
    En espectros, customdata puede ser:
    - Un int directo (pointNumber como ID)
    - Una lista/tuple donde el primer elemento es el row_index
    
    Args:
        fig: Figura de Plotly
        event: Evento individual de click
        
    Returns:
        Índice de fila o None si no se pudo extraer
    """
    if not event:
        return None
    
    curve_number = event.get("curveNumber", None)
    point_number = event.get("pointNumber", None)
    
    if curve_number is None:
        return None
    
    try:
        trace = fig.data[curve_number]
        customdata = getattr(trace, "customdata", None)
        
        if customdata is None or len(customdata) == 0:
            return None
        
        # Si viene pointNumber, usa el punto exacto
        if point_number is not None:
            cd = customdata[point_number]
        else:
            cd = customdata[0]
        
        # cd puede ser escalar (int) o lista/tuple
        if isinstance(cd, (list, tuple)) and len(cd) > 0:
            cd = cd[0]
        
        return int(cd)
    
    except Exception:
        return None


def extract_row_indices_from_spectra_events(fig: go.Figure, events: List[dict]) -> List[int]:
    """
    Extrae índices de fila desde eventos de espectros (lasso/box).
    
    En gráficos de espectros, customdata es típicamente un int directo
    por punto, representando el row_index único del espectro.
    
    Args:
        fig: Figura de Plotly
        events: Lista de eventos de selección múltiple
        
    Returns:
        Lista de índices únicos (sin duplicados, preservando orden)
    """
    if not events:
        return []
    
    def _coerce_to_int(cd):
        """Convierte customdata a int, manejando diferentes formatos."""
        if cd is None:
            return None
        
        # En espectros customdata es int directo
        try:
            return int(cd)
        except Exception:
            return None
    
    indices: List[int] = []
    
    for ev in events:
        # Intentar extraer directamente de customdata
        idx = _coerce_to_int(ev.get("customdata", None))
        
        if idx is not None:
            indices.append(idx)
            continue
        
        # Fallback: leer desde la traza usando curveNumber/pointNumber
        try:
            curve = ev.get("curveNumber", None)
            point = ev.get("pointNumber", None)
            
            if curve is None or point is None:
                continue
            
            trace_cd = getattr(fig.data[curve], "customdata", None)
            if trace_cd is None:
                continue
            
            idx = _coerce_to_int(trace_cd[point])
            if idx is not None:
                indices.append(idx)
        
        except Exception:
            pass
    
    # Eliminar duplicados preservando orden
    return _remove_duplicates_preserve_order(indices)


def extract_row_indices_from_parity_events(fig: go.Figure, events: List[dict]) -> List[int]:
    """
    Extrae índices de fila desde eventos de parity plots (lasso/box/click).
    
    En gráficos parity, customdata suele ser [row_id, date] o similar,
    donde row_id (primer elemento) es el índice de fila.
    
    Args:
        fig: Figura de Plotly
        events: Lista de eventos de selección
        
    Returns:
        Lista de índices únicos (sin duplicados, preservando orden)
    """
    if not events:
        return []
    
    def _coerce_to_int(cd):
        """Convierte customdata a int, manejando listas/tuples."""
        if cd is None:
            return None
        
        # En parity customdata suele ser [row_id, date] => tomar primer elemento
        if isinstance(cd, (list, tuple)) and len(cd) > 0:
            cd = cd[0]
        
        try:
            return int(cd)
        except Exception:
            return None
    
    indices: List[int] = []
    
    for ev in events:
        # Intentar extraer de customdata
        idx = _coerce_to_int(ev.get("customdata", None))
        
        if idx is not None:
            indices.append(idx)
            continue
        
        # Fallback: leer desde la traza
        try:
            curve = ev.get("curveNumber", None)
            point = ev.get("pointNumber", None)
            
            if curve is None or point is None:
                continue
            
            trace_cd = getattr(fig.data[curve], "customdata", None)
            if trace_cd is None:
                continue
            
            idx = _coerce_to_int(trace_cd[point])
            if idx is not None:
                indices.append(idx)
        
        except Exception:
            pass
    
    # Eliminar duplicados preservando orden
    return _remove_duplicates_preserve_order(indices)


def _remove_duplicates_preserve_order(items: List[int]) -> List[int]:
    """
    Elimina duplicados de una lista preservando el orden original.
    
    Args:
        items: Lista con posibles duplicados
        
    Returns:
        Lista sin duplicados
    """
    seen = set()
    result: List[int] = []
    
    for item in items:
        if item not in seen:
            result.append(item)
            seen.add(item)
    
    return result


def validate_indices_against_dataframe(indices: List[int], valid_indices: List[int]) -> List[int]:
    """
    Valida que los índices extraídos existan en el DataFrame actual.
    
    Args:
        indices: Índices extraídos de eventos
        valid_indices: Índices válidos del DataFrame actual
        
    Returns:
        Lista de índices válidos
    """
    valid_set = set(valid_indices)
    return [idx for idx in indices if idx in valid_set]