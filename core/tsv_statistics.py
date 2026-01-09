"""
COREF - TSV Statistics Module
==============================
Cálculo de estadísticas por grupo para validación NIR.

Funciones principales:
- calculate_group_statistics: Estadísticas (R², RMSE, BIAS, N) por grupo
- calculate_all_groups_statistics: Estadísticas de todos los grupos activos
- get_statistics_summary: Resumen comparativo de grupos
"""

from typing import Dict, List, Optional, Set
import pandas as pd
import numpy as np
from sklearn.metrics import r2_score, mean_squared_error


def calculate_group_statistics(
    df: pd.DataFrame,
    param_name: str,
    removed_indices: Set[int],
    sample_groups: Dict[int, str],
    group_key: str,
) -> Optional[Dict[str, float]]:
    """
    Calcula estadísticas (R², RMSE, BIAS, N) para un grupo específico.
    
    Args:
        df: DataFrame con los datos
        param_name: Nombre del parámetro (ej: "Protein")
        removed_indices: Índices marcados para eliminar
        sample_groups: Dict con asignaciones de grupos {idx: group_key}
        group_key: Clave del grupo ("Set 1", "Set 2", "Set 3", "Set 4")
    
    Returns:
        dict con keys: r2, rmse, bias, n
        None si no hay suficientes datos válidos (< 2 muestras)
    
    Example:
        >>> stats = calculate_group_statistics(df, "Protein", removed, groups, "Set 1")
        >>> if stats:
        >>>     print(f"R²: {stats['r2']:.3f}")
    """
    result_col = f"Result {param_name}"
    reference_col = f"Reference {param_name}"
    
    # Verificar que las columnas existen
    if result_col not in df.columns or reference_col not in df.columns:
        return None
    
    # Filtrar: solo muestras del grupo, no eliminadas
    mask = pd.Series(False, index=df.index)
    for idx, grp in sample_groups.items():
        if grp == group_key and idx not in removed_indices and idx in df.index:
            mask.loc[idx] = True
    
    df_group = df.loc[mask]
    
    if len(df_group) == 0:
        return None
    
    # Filtrar valores válidos (no NaN)
    valid = df_group[[result_col, reference_col]].dropna()
    
    if len(valid) < 2:
        return None
    
    result = valid[result_col].values
    reference = valid[reference_col].values
    
    # Calcular métricas
    try:
        r2 = r2_score(reference, result)
        rmse = np.sqrt(mean_squared_error(reference, result))
        bias = np.mean(result - reference)
        n = len(valid)
        
        return {
            "r2": float(r2),
            "rmse": float(rmse),
            "bias": float(bias),
            "n": int(n),
        }
    except Exception:
        return None


def calculate_all_groups_statistics(
    df: pd.DataFrame,
    param_name: str,
    removed_indices: Set[int],
    sample_groups: Dict[int, str],
    group_keys: List[str],
) -> Dict[str, Optional[Dict[str, float]]]:
    """
    Calcula estadísticas para todos los grupos especificados.
    
    Args:
        df: DataFrame con los datos
        param_name: Nombre del parámetro
        removed_indices: Índices marcados para eliminar
        sample_groups: Dict con asignaciones de grupos
        group_keys: Lista de claves de grupos a calcular (ej: ["Set 1", "Set 2"])
    
    Returns:
        Dict con {group_key: stats_dict} para cada grupo
        stats_dict puede ser None si no hay datos suficientes
    
    Example:
        >>> all_stats = calculate_all_groups_statistics(
        >>>     df, "Protein", removed, groups, ["Set 1", "Set 2"]
        >>> )
        >>> for group, stats in all_stats.items():
        >>>     if stats:
        >>>         print(f"{group}: R²={stats['r2']:.3f}")
    """
    results = {}
    
    for group_key in group_keys:
        stats = calculate_group_statistics(
            df, param_name, removed_indices, sample_groups, group_key
        )
        results[group_key] = stats
    
    return results


def get_statistics_summary(
    all_stats: Dict[str, Optional[Dict[str, float]]],
    group_labels: Dict[str, str],
    sample_groups_config: Dict[str, Dict],
) -> pd.DataFrame:
    """
    Crea un DataFrame resumen con las estadísticas de todos los grupos.
    
    Args:
        all_stats: Dict con estadísticas por grupo (output de calculate_all_groups_statistics)
        group_labels: Dict con etiquetas personalizadas {group_key: label}
        sample_groups_config: Config de grupos con emoji, color, etc.
    
    Returns:
        DataFrame con columnas: Grupo, Emoji, R², RMSE, BIAS, N
        Solo incluye grupos con datos válidos
    
    Example:
        >>> summary_df = get_statistics_summary(all_stats, labels, SAMPLE_GROUPS)
        >>> st.dataframe(summary_df)
    """
    rows = []
    
    for group_key, stats in all_stats.items():
        if stats is None:
            continue
        
        # Obtener label personalizado o usar el por defecto
        label = group_labels.get(group_key, group_key)
        emoji = sample_groups_config.get(group_key, {}).get("emoji", "")
        
        rows.append({
            "Grupo": f"{emoji} {label}",
            "R²": f"{stats['r2']:.4f}",
            "RMSE": f"{stats['rmse']:.3f}",
            "BIAS": f"{stats['bias']:.3f}",
            "N": stats['n'],
        })
    
    if not rows:
        return pd.DataFrame()
    
    return pd.DataFrame(rows)


def get_best_worst_groups(
    all_stats: Dict[str, Optional[Dict[str, float]]],
    metric: str = "r2",
) -> Dict[str, Optional[str]]:
    """
    Identifica el mejor y peor grupo según una métrica.
    
    Args:
        all_stats: Dict con estadísticas por grupo
        metric: Métrica a comparar ("r2", "rmse", "bias")
    
    Returns:
        Dict con keys "best" y "worst", valores son group_keys o None
    
    Example:
        >>> best_worst = get_best_worst_groups(all_stats, "r2")
        >>> st.info(f"Mejor grupo (R²): {best_worst['best']}")
    """
    valid_stats = {k: v for k, v in all_stats.items() if v is not None}
    
    if not valid_stats:
        return {"best": None, "worst": None}
    
    if metric not in ["r2", "rmse", "bias"]:
        return {"best": None, "worst": None}
    
    # Para R²: mayor es mejor
    # Para RMSE y BIAS (absoluto): menor es mejor
    if metric == "r2":
        best = max(valid_stats.items(), key=lambda x: x[1][metric])[0]
        worst = min(valid_stats.items(), key=lambda x: x[1][metric])[0]
    else:
        # Para RMSE y BIAS usamos valor absoluto
        if metric == "bias":
            best = min(valid_stats.items(), key=lambda x: abs(x[1][metric]))[0]
            worst = max(valid_stats.items(), key=lambda x: abs(x[1][metric]))[0]
        else:  # rmse
            best = min(valid_stats.items(), key=lambda x: x[1][metric])[0]
            worst = max(valid_stats.items(), key=lambda x: x[1][metric])[0]
    
    return {"best": best, "worst": worst}


def count_samples_per_group(
    sample_groups: Dict[int, str],
    removed_indices: Set[int],
    group_keys: List[str],
) -> Dict[str, int]:
    """
    Cuenta el número de muestras válidas (no eliminadas) por grupo.
    
    Args:
        sample_groups: Dict con asignaciones de grupos
        removed_indices: Índices marcados para eliminar
        group_keys: Lista de claves de grupos
    
    Returns:
        Dict con {group_key: count}
    
    Example:
        >>> counts = count_samples_per_group(groups, removed, ["Set 1", "Set 2"])
        >>> st.write(f"Set 1: {counts['Set 1']} muestras")
    """
    counts = {group_key: 0 for group_key in group_keys}
    
    for idx, grp in sample_groups.items():
        if grp in counts and idx not in removed_indices:
            counts[grp] += 1
    
    return counts


def get_active_groups(
    sample_groups: Dict[int, str],
    removed_indices: Set[int],
) -> Set[str]:
    """
    Obtiene el conjunto de grupos que tienen al menos una muestra válida.
    
    Args:
        sample_groups: Dict con asignaciones de grupos
        removed_indices: Índices marcados para eliminar
    
    Returns:
        Set con claves de grupos activos (excluye "none")
    
    Example:
        >>> active = get_active_groups(groups, removed)
        >>> if "Set 1" in active:
        >>>     st.write("Set 1 tiene muestras asignadas")
    """
    active = set()
    
    for idx, grp in sample_groups.items():
        if grp != "none" and idx not in removed_indices:
            active.add(grp)
    
    return active


def format_statistics_for_display(
    stats: Optional[Dict[str, float]],
    decimal_places: Dict[str, int] = None,
) -> Dict[str, str]:
    """
    Formatea estadísticas para mostrar en UI con número de decimales personalizado.
    
    Args:
        stats: Dict con estadísticas brutas
        decimal_places: Dict opcional con {metric: decimals}, por defecto {"r2": 4, "rmse": 3, "bias": 3}
    
    Returns:
        Dict con valores formateados como strings
    
    Example:
        >>> formatted = format_statistics_for_display(stats)
        >>> st.metric("R²", formatted["r2"])
    """
    if stats is None:
        return {
            "r2": "N/A",
            "rmse": "N/A",
            "bias": "N/A",
            "n": "N/A",
        }
    
    if decimal_places is None:
        decimal_places = {"r2": 4, "rmse": 3, "bias": 3}
    
    return {
        "r2": f"{stats['r2']:.{decimal_places.get('r2', 4)}f}",
        "rmse": f"{stats['rmse']:.{decimal_places.get('rmse', 3)}f}",
        "bias": f"{stats['bias']:.{decimal_places.get('bias', 3)}f}",
        "n": str(stats['n']),
    }