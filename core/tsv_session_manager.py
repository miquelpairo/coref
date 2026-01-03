"""
Gestión del estado de sesión para TSV Validation Reports
"""
from typing import Dict, List, Set, Optional
import streamlit as st
import pandas as pd


# =============================================================================
# INICIALIZACIÓN
# =============================================================================

def initialize_tsv_session_state():
    """
    Inicializa todas las variables del session_state para TSV Validation.
    Esta función se llama al inicio de cada ejecución de la app.
    """
    st.session_state.setdefault("processed_data", {})
    st.session_state.setdefault("samples_to_remove", {})
    st.session_state.setdefault("sample_groups", {})
    st.session_state.setdefault("group_labels", {
        "Set 1": "Set 1",
        "Set 2": "Set 2",
        "Set 3": "Set 3",
        "Set 4": "Set 4"
    })
    st.session_state.setdefault("group_descriptions", {
        "Set 1": "",
        "Set 2": "",
        "Set 3": "",
        "Set 4": ""
    })
    st.session_state.setdefault("editor_version", {})
    st.session_state.setdefault("pending_selections", {})
    st.session_state.setdefault("last_event_id", {})
    st.session_state.setdefault("last_apply_summary", {})


# =============================================================================
# GESTIÓN DE ARCHIVOS PROCESADOS
# =============================================================================

def add_processed_file(file_name: str, df: pd.DataFrame):
    """
    Añade un archivo procesado al estado de sesión.
    
    Args:
        file_name: Nombre del archivo
        df: DataFrame con los datos procesados
    """
    st.session_state.processed_data[file_name] = df
    st.session_state.samples_to_remove[file_name] = set()
    st.session_state.sample_groups[file_name] = {}
    st.session_state.editor_version[file_name] = 0
    st.session_state.pending_selections[file_name] = []
    st.session_state.last_event_id[file_name] = {"spectra": "", "parity": ""}


def remove_processed_file(file_name: str):
    """
    Elimina un archivo del estado de sesión.
    
    Args:
        file_name: Nombre del archivo a eliminar
    """
    st.session_state.processed_data.pop(file_name, None)
    st.session_state.samples_to_remove.pop(file_name, None)
    st.session_state.sample_groups.pop(file_name, None)
    st.session_state.editor_version.pop(file_name, None)
    st.session_state.pending_selections.pop(file_name, None)
    st.session_state.last_event_id.pop(file_name, None)
    st.session_state.last_apply_summary.pop(file_name, None)


def clear_all_processed_data():
    """Limpia todos los datos procesados del estado de sesión."""
    st.session_state.processed_data = {}
    st.session_state.samples_to_remove = {}
    st.session_state.sample_groups = {}
    st.session_state.editor_version = {}
    st.session_state.pending_selections = {}
    st.session_state.last_event_id = {}
    st.session_state.last_apply_summary = {}


def get_processed_files() -> List[str]:
    """
    Obtiene la lista de archivos procesados.
    
    Returns:
        Lista de nombres de archivos
    """
    return list(st.session_state.processed_data.keys())


def has_processed_data() -> bool:
    """
    Verifica si hay datos procesados.
    
    Returns:
        True si hay al menos un archivo procesado
    """
    return bool(st.session_state.processed_data)


# =============================================================================
# GESTIÓN DE SELECCIONES PENDIENTES
# =============================================================================

def add_pending_selection(file_name: str, idx: int, action: str, group: Optional[str] = None):
    """
    Añade una selección pendiente para un archivo.
    
    Args:
        file_name: Nombre del archivo
        idx: Índice de la muestra
        action: Acción a realizar ("Marcar para Eliminar" o "Asignar a Grupo")
        group: Grupo destino (si action == "Asignar a Grupo")
    """
    pending = st.session_state.pending_selections.get(file_name, [])
    
    new_item = {
        "idx": idx,
        "action": action,
        "group": group
    }
    
    # Verificar si ya existe
    already_exists = any(
        item.get("idx") == new_item["idx"]
        and item.get("action") == new_item["action"]
        and item.get("group") == new_item["group"]
        for item in pending
    )
    
    if not already_exists:
        pending.append(new_item)
        st.session_state.pending_selections[file_name] = pending


def clear_pending_selections(file_name: str) -> int:
    """
    Limpia todas las selecciones pendientes de un archivo y devuelve cuántas se borraron.
    """
    pending = st.session_state.pending_selections.get(file_name, [])
    n = len(pending) if pending else 0
    st.session_state.pending_selections[file_name] = []
    return n


def get_pending_selections(file_name: str) -> List[Dict]:
    """
    Obtiene las selecciones pendientes de un archivo.
    
    Args:
        file_name: Nombre del archivo
        
    Returns:
        Lista de diccionarios con las selecciones pendientes
    """
    return st.session_state.pending_selections.get(file_name, [])


def has_pending_selections(file_name: str) -> bool:
    """
    Verifica si hay selecciones pendientes para un archivo.
    
    Args:
        file_name: Nombre del archivo
        
    Returns:
        True si hay selecciones pendientes
    """
    return bool(st.session_state.pending_selections.get(file_name, []))


# =============================================================================
# APLICACIÓN DE SELECCIONES
# =============================================================================

def apply_pending_selections(file_name: str):
    """
    Aplica todas las selecciones pendientes de un archivo.
    Actualiza samples_to_remove y sample_groups según las acciones pendientes.
    
    Args:
        file_name: Nombre del archivo
    """
    pending = st.session_state.pending_selections.get(file_name, [])
    
    if not pending:
        return
    
    eliminar_count = 0
    grupos_count = 0
    
    for item in pending:
        idx = item["idx"]
        action = item["action"]
        
        if action == "Marcar para Eliminar":
            # Toggle: si ya está marcado, lo desmarca
            if idx in st.session_state.samples_to_remove[file_name]:
                st.session_state.samples_to_remove[file_name].remove(idx)
            else:
                st.session_state.samples_to_remove[file_name].add(idx)
                eliminar_count += 1
            
            # Limpiar grupo si existe
            st.session_state.sample_groups[file_name].pop(idx, None)
            
        elif action == "Asignar a Grupo":
            grp = item.get("group")
            if grp and grp != "none":
                st.session_state.sample_groups[file_name][idx] = grp
                # Quitar de eliminados si estaba
                st.session_state.samples_to_remove[file_name].discard(idx)
                grupos_count += 1
    
    # Guardar resumen para mostrar después del rerun
    st.session_state.last_apply_summary[file_name] = {
        'count': len(pending),
        'eliminar': eliminar_count,
        'grupos': grupos_count
    }
    
    # Limpiar pendientes y eventos
    st.session_state.pending_selections[file_name] = []
    st.session_state.last_event_id[file_name] = {"spectra": "", "parity": ""}
    st.session_state.editor_version[file_name] += 1


def get_apply_summary(file_name: str) -> Optional[Dict]:
    """
    Recupera el resumen de la última aplicación y lo limpia.
    
    Args:
        file_name: Nombre del archivo
        
    Returns:
        Diccionario con el resumen o None si no existe
    """
    summary = st.session_state.last_apply_summary.get(file_name)
    
    if summary:
        # Limpiar para que no se muestre en el siguiente rerun
        del st.session_state.last_apply_summary[file_name]
    
    return summary


# =============================================================================
# GESTIÓN DE MUESTRAS PARA ELIMINAR
# =============================================================================

def get_samples_to_remove(file_name: str) -> Set[int]:
    """
    Obtiene el conjunto de índices marcados para eliminar.
    
    Args:
        file_name: Nombre del archivo
        
    Returns:
        Set de índices a eliminar
    """
    return st.session_state.samples_to_remove.get(file_name, set())


def mark_sample_for_removal(file_name: str, idx: int):
    """
    Marca una muestra para eliminar.
    
    Args:
        file_name: Nombre del archivo
        idx: Índice de la muestra
    """
    st.session_state.samples_to_remove[file_name].add(idx)


def unmark_sample_for_removal(file_name: str, idx: int):
    """
    Desmarca una muestra para eliminar.
    
    Args:
        file_name: Nombre del archivo
        idx: Índice de la muestra
    """
    st.session_state.samples_to_remove[file_name].discard(idx)


def clear_samples_to_remove(file_name: str):
    """
    Limpia todas las muestras marcadas para eliminar.
    
    Args:
        file_name: Nombre del archivo
    """
    st.session_state.samples_to_remove[file_name] = set()


# =============================================================================
# GESTIÓN DE GRUPOS DE MUESTRAS
# =============================================================================

def get_sample_groups(file_name: str) -> Dict[int, str]:
    """
    Obtiene el diccionario de grupos de muestras.
    
    Args:
        file_name: Nombre del archivo
        
    Returns:
        Dict {idx: group_name}
    """
    return st.session_state.sample_groups.get(file_name, {})


def assign_sample_to_group(file_name: str, idx: int, group: str):
    """
    Asigna una muestra a un grupo.
    
    Args:
        file_name: Nombre del archivo
        idx: Índice de la muestra
        group: Nombre del grupo
    """
    st.session_state.sample_groups[file_name][idx] = group
    # Quitar de eliminados si estaba
    st.session_state.samples_to_remove[file_name].discard(idx)


def remove_sample_from_groups(file_name: str, idx: int):
    """
    Elimina una muestra de todos los grupos.
    
    Args:
        file_name: Nombre del archivo
        idx: Índice de la muestra
    """
    st.session_state.sample_groups[file_name].pop(idx, None)


def clear_all_groups(file_name: str):
    """
    Limpia todos los grupos de un archivo.
    
    Args:
        file_name: Nombre del archivo
    """
    st.session_state.sample_groups[file_name] = {}


def update_groups_from_editor(file_name: str, edited_df: pd.DataFrame):
    """
    Actualiza los grupos y muestras a eliminar desde el data_editor.
    
    Args:
        file_name: Nombre del archivo
        edited_df: DataFrame editado con columnas "Eliminar" y "Grupo"
    """
    new_removed = set()
    new_groups = {}
    
    for idx in edited_df.index:
        # Muestras marcadas para eliminar
        if bool(edited_df.at[idx, "Eliminar"]):
            new_removed.add(idx)
        
        # Muestras asignadas a grupos
        grp_val = edited_df.at[idx, "Grupo"]
        if grp_val != "none":
            new_groups[idx] = grp_val
    
    st.session_state.samples_to_remove[file_name] = new_removed
    st.session_state.sample_groups[file_name] = new_groups
    st.session_state.editor_version[file_name] += 1


# =============================================================================
# CONFIRMACIÓN DE ELIMINACIÓN
# =============================================================================

def confirm_sample_deletion(file_name: str) -> int:
    """
    Confirma y ejecuta la eliminación de muestras marcadas.
    Actualiza el DataFrame y remapia los índices de grupos.
    
    Args:
        file_name: Nombre del archivo
        
    Returns:
        Número de muestras eliminadas
    """
    df_current = st.session_state.processed_data[file_name]
    removed_indices = st.session_state.samples_to_remove[file_name]
    sample_groups = st.session_state.sample_groups[file_name]
    
    if not removed_indices:
        return 0
    
    # Crear mapeo de índices antiguos a nuevos
    old_to_new = {}
    sorted_indices = sorted(df_current.index)
    removed_sorted = sorted(removed_indices)
    new_idx = 0
    
    for old_idx in sorted_indices:
        if old_idx not in removed_sorted:
            old_to_new[old_idx] = new_idx
            new_idx += 1
    
    # Eliminar filas y resetear índices
    df_updated = df_current.drop(index=list(removed_indices)).reset_index(drop=True)
    
    # Remapar grupos
    new_groups = {}
    for old_idx, grp in sample_groups.items():
        if old_idx not in removed_indices:
            mapped = old_to_new.get(old_idx)
            if mapped is not None:
                new_groups[mapped] = grp
    
    # Actualizar estado
    st.session_state.processed_data[file_name] = df_updated
    st.session_state.samples_to_remove[file_name] = set()
    st.session_state.sample_groups[file_name] = new_groups
    st.session_state.pending_selections[file_name] = []
    st.session_state.last_event_id[file_name] = {"spectra": "", "parity": ""}
    st.session_state.editor_version[file_name] += 1
    
    return len(removed_indices)


# =============================================================================
# LIMPIEZA DE DATOS
# =============================================================================

def clear_all_selections(file_name: str):
    """
    Limpia todas las selecciones (grupos y eliminados) de un archivo.
    
    Args:
        file_name: Nombre del archivo
    """
    st.session_state.samples_to_remove[file_name] = set()
    st.session_state.sample_groups[file_name] = {}
    st.session_state.pending_selections[file_name] = []
    st.session_state.last_event_id[file_name] = {"spectra": "", "parity": ""}
    st.session_state.editor_version[file_name] += 1


def clean_invalid_indices(file_name: str):
    """
    Limpia índices inválidos de samples_to_remove y sample_groups.
    Útil después de filtrar o modificar el DataFrame.
    
    Args:
        file_name: Nombre del archivo
    """
    df_current = st.session_state.processed_data[file_name]
    
    # Limpiar índices inválidos de removed
    removed_indices = st.session_state.samples_to_remove[file_name]
    valid_removed = {i for i in removed_indices if i in df_current.index}
    
    # Limpiar índices inválidos de grupos
    sample_groups = st.session_state.sample_groups[file_name]
    valid_groups = {i: g for i, g in sample_groups.items() if i in df_current.index}
    
    # Actualizar solo si hubo cambios
    if len(valid_removed) != len(removed_indices):
        st.session_state.samples_to_remove[file_name] = valid_removed
    
    if len(valid_groups) != len(sample_groups):
        st.session_state.sample_groups[file_name] = valid_groups


# =============================================================================
# GESTIÓN DE ETIQUETAS Y DESCRIPCIONES DE GRUPOS
# =============================================================================

def update_group_label(group_key: str, new_label: str):
    """
    Actualiza la etiqueta de un grupo.
    
    Args:
        group_key: Clave del grupo ("Set 1", "Set 2", etc.)
        new_label: Nueva etiqueta
    """
    st.session_state.group_labels[group_key] = new_label


def update_group_description(group_key: str, new_description: str):
    """
    Actualiza la descripción de un grupo.
    
    Args:
        group_key: Clave del grupo
        new_description: Nueva descripción
    """
    st.session_state.group_descriptions[group_key] = new_description


def get_group_label(group_key: str) -> str:
    """
    Obtiene la etiqueta de un grupo.
    
    Args:
        group_key: Clave del grupo
        
    Returns:
        Etiqueta del grupo
    """
    return st.session_state.group_labels.get(group_key, group_key)


def get_group_description(group_key: str) -> str:
    """
    Obtiene la descripción de un grupo.
    
    Args:
        group_key: Clave del grupo
        
    Returns:
        Descripción del grupo
    """
    return st.session_state.group_descriptions.get(group_key, "")


# =============================================================================
# GESTIÓN DE VERSIONES Y EVENTOS
# =============================================================================

def increment_editor_version(file_name: str):
    """
    Incrementa la versión del editor para forzar re-render.
    
    Args:
        file_name: Nombre del archivo
    """
    st.session_state.editor_version[file_name] = st.session_state.editor_version.get(file_name, 0) + 1


def get_editor_version(file_name: str) -> int:
    """
    Obtiene la versión actual del editor.
    
    Args:
        file_name: Nombre del archivo
        
    Returns:
        Versión del editor
    """
    return st.session_state.editor_version.get(file_name, 0)


def update_last_event_id(file_name: str, graph_type: str, event_id: str):
    """
    Actualiza el último event_id procesado para un gráfico.
    
    Args:
        file_name: Nombre del archivo
        graph_type: Tipo de gráfico ("spectra" o "parity")
        event_id: ID del evento
    """
    if file_name not in st.session_state.last_event_id:
        st.session_state.last_event_id[file_name] = {"spectra": "", "parity": ""}
    
    st.session_state.last_event_id[file_name][graph_type] = event_id


def get_last_event_id(file_name: str, graph_type: str) -> str:
    """
    Obtiene el último event_id procesado para un gráfico.
    
    Args:
        file_name: Nombre del archivo
        graph_type: Tipo de gráfico ("spectra" o "parity")
        
    Returns:
        ID del último evento
    """
    return st.session_state.last_event_id.get(file_name, {}).get(graph_type, "")


# =============================================================================
# ESTADÍSTICAS Y MÉTRICAS
# =============================================================================

def get_file_statistics(file_name: str) -> Dict[str, int]:
    """
    Obtiene estadísticas de un archivo procesado.
    
    Args:
        file_name: Nombre del archivo
        
    Returns:
        Dict con total, eliminar, agrupadas, finales
    """
    df = st.session_state.processed_data.get(file_name)
    if df is None:
        return {"total": 0, "eliminar": 0, "agrupadas": 0, "finales": 0}
    
    removed = st.session_state.samples_to_remove.get(file_name, set())
    groups = st.session_state.sample_groups.get(file_name, {})
    
    grouped_count = sum(1 for g in groups.values() if g != "none")
    
    return {
        "total": len(df),
        "eliminar": len(removed),
        "agrupadas": grouped_count,
        "finales": len(df) - len(removed)
    }