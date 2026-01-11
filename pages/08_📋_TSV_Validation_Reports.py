"""
COREF - TSV Validation Reports
==============================
Generación de informes de validación NIR (TSV) con previsualización y selección de muestras.

Refactorizado para usar módulos especializados:
- tsv_session_manager: Gestión del estado de sesión
- tsv_processing: Limpieza y procesamiento de TSV
- selection_utils: Extracción de eventos de gráficos
- plotly_utils: Gráficos y visualizaciones
- tsv_statistics: Cálculo de estadísticas por grupo
"""

from __future__ import annotations

import zipfile
from io import BytesIO
from typing import List
import json
import hashlib


import pandas as pd
import streamlit as st

from auth import check_password
from buchi_streamlit_theme import apply_buchi_styles
from core.tsv_plotting import plot_comparison_preview, build_spectra_figure_preview
from core.tsv_report_generator import generate_html_report, ReportResult
from core.tsv_session_manager import (
    initialize_tsv_session_state,
    add_processed_file,
    has_processed_data,
    get_processed_files,
    apply_pending_selections,
    get_apply_summary,
    add_pending_selection,
    clear_pending_selections,
    get_pending_selections,
    has_pending_selections,
    confirm_sample_deletion,
    get_samples_to_remove,
    get_sample_groups,
    clear_all_selections,
    clear_all_groups,
    clean_invalid_indices,
    get_file_statistics,
    get_editor_version,
    increment_editor_version,
    update_last_event_id,
    get_last_event_id,
    clear_last_event_ids,
    update_group_label,
    update_group_description,
    get_group_label,
    get_group_description,
    # Display helpers
    get_group_display_name,
    get_group_display_name_with_key,
    display_to_group_key,
    get_group_options_display,
)
from core.tsv_processing import (
    clean_tsv_file,
    get_parameter_columns,
    extract_parameter_names,
    PIXEL_RE,
    build_samples_by_month_dataframe,
)
from core.plotly_utils import create_samples_by_month_chart
from core.selection_utils import (
    create_event_id,
    extract_row_index_from_click,
    extract_row_indices_from_spectra_events,
    extract_row_indices_from_parity_events,
)
from core.tsv_statistics import (
    calculate_group_statistics,
    calculate_all_groups_statistics,
    get_statistics_summary,
    get_active_groups,
    count_samples_per_group,
)

try:
    from streamlit_plotly_events import plotly_events

    INTERACTIVE_SELECTION_AVAILABLE = True
except Exception:
    plotly_events = None
    INTERACTIVE_SELECTION_AVAILABLE = False


# =============================================================================
# HELPER: Apply Visual Filter
# =============================================================================
def apply_visual_filter(df: pd.DataFrame, selected_file: str) -> pd.DataFrame:
    """
    Aplica filtro visual (solo para visualización, no modifica df original)
    Retorna df filtrado manteniendo índices originales
    """
    # Get filter settings for current file
    filter_years = st.session_state.visual_filter_years.get(selected_file, [])
    filter_months = st.session_state.visual_filter_months.get(selected_file, [])
    filter_id = st.session_state.get('visual_filter_id', {}).get(selected_file, "")
    filter_note = st.session_state.get('visual_filter_note', {}).get(selected_file, "")
    
    # If no filters active, return original
    if not filter_years and not filter_months and not filter_id and not filter_note:
        return df
    
    df_temp = df.copy()
    mask = pd.Series(True, index=df_temp.index)
    
    # Date filters
    if 'Date' in df_temp.columns and (filter_years or filter_months):
        df_temp['Date'] = pd.to_datetime(df_temp['Date'], errors='coerce')
        
        if filter_years:
            mask &= df_temp['Date'].dt.year.isin(filter_years)
        
        if filter_months:
            mask &= df_temp['Date'].dt.month.isin(filter_months)
    
    # ID filter
    if filter_id and "ID" in df_temp.columns:
        mask &= df_temp["ID"].astype(str).str.contains(filter_id, case=False, na=False)

    # Note filter
    if filter_note and "Note" in df_temp.columns:
        mask &= df_temp["Note"].astype(str).str.contains(filter_note, case=False, na=False)

    
    return df_temp.loc[mask].copy()


def get_filter_indicator(df_original: pd.DataFrame, df_filtered: pd.DataFrame) -> str:
    """
    Retorna string indicador del estado del filtro visual
    """
    total = len(df_original)
    filtered = len(df_filtered)
    
    if total == filtered:
        return f"📊 Mostrando {total} muestras"
    else:
        return f"📊 Mostrando {filtered}/{total} muestras (filtro activo)"


def get_visual_filter_hash(selected_file: str) -> str:
    payload = {
        "years": st.session_state.visual_filter_years.get(selected_file, []),
        "months": st.session_state.visual_filter_months.get(selected_file, []),
        "id": st.session_state.visual_filter_id.get(selected_file, ""),
        "note": st.session_state.visual_filter_note.get(selected_file, ""),
    }
    s = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return hashlib.md5(s.encode("utf-8")).hexdigest()[:8]



# =============================================================================
# STREAMLIT PAGE SETUP
# =============================================================================
apply_buchi_styles()

if not check_password():
    st.stop()

st.title("📋 TSV Validation Reports")
st.markdown("## Generación de informes de validación NIR (TSV) con previsualización y selección de muestras.")


# =============================================================================
# INFO / HELP
# =============================================================================
with st.expander("ℹ️ Instrucciones de Uso"):
    st.markdown(
        """
### Cómo usar TSV Validation Reports

**1. Cargar Archivos TSV**
- Sube archivos TSV (export/journal de NIR-Online)
- Soporte para múltiples encodings

**2. Filtrar por Fechas (Opcional)**

**3. Previsualización y Selección**
- Filtro visual por año/mes/ID/Note en sidebar (solo afecta visualización)
- Selección desde gráficos (Espectros: click + lasso/box | Parity: click + lasso/box)
- Selección desde tabla (checkboxes → añadir a pendientes → aplicar)
- Grupos personalizables (se guarda Set 1..4 internamente, pero se muestra la etiqueta del usuario)

**4. Estadísticas por Grupo**
- Visualiza R², RMSE, BIAS y N para cada grupo de validación

**5. Generación de Reportes HTML**
"""
    )


# =============================================================================
# SAMPLE GROUPS CONFIGURATION
# =============================================================================
SAMPLE_GROUPS = {
    "none": {"symbol": "circle", "color": "blue", "size": 8, "emoji": "🔵"},
    "Set 1": {"symbol": "square", "color": "green", "size": 10, "emoji": "🟩"},
    "Set 2": {"symbol": "triangle-up", "color": "red", "size": 10, "emoji": "🔺"},
    "Set 3": {"symbol": "star", "color": "gold", "size": 12, "emoji": "⭐"},
    "Set 4": {"symbol": "cross", "color": "grey", "size": 10, "emoji": "➕"},
}
GROUP_KEYS = ["Set 1", "Set 2", "Set 3", "Set 4"]


# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================
initialize_tsv_session_state()

# Initialize visual filter state
if 'visual_filter_years' not in st.session_state:
    st.session_state.visual_filter_years = {}
if 'visual_filter_months' not in st.session_state:
    st.session_state.visual_filter_months = {}
if 'visual_filter_id' not in st.session_state:
    st.session_state.visual_filter_id = {}
if 'visual_filter_note' not in st.session_state:
    st.session_state.visual_filter_note = {}


# =============================================================================
# STREAMLIT UI - FASE 1: CARGA Y FILTRADO
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
    st.markdown("---")

    # -------------------------------------------------------------------------
    # PREVIEW (solo esto dentro del expander)
    # -------------------------------------------------------------------------
    with st.expander("📊 Preview: nº de muestras por mes y archivo (antes del filtro)", expanded=True):
        df_preview = build_samples_by_month_dataframe(uploaded_files)
        if df_preview is not None and len(df_preview) > 0:
            fig_prev = create_samples_by_month_chart(df_preview)
            st.plotly_chart(fig_prev, use_container_width=True)
            st.caption("Datos brutos, antes de aplicar filtros de fecha.")
        else:
            st.info("No se encontraron fechas válidas en los archivos cargados (preview).")

    # -------------------------------------------------------------------------
    # FILTRO (FUERA del expander)
    # -------------------------------------------------------------------------
    st.subheader("📅 1. Filtrado por Fechas (Opcional)")
    st.info("Define el rango de fechas ANTES de procesar.")

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        start_date = st.date_input("Fecha de inicio", value=None)
    with col2:
        end_date = st.date_input("Fecha de fin", value=None)
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ Limpiar fechas"):
            st.rerun()

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

    if st.button("🔄 Procesar Archivos con Filtros", type="primary", use_container_width=True):
        progress_bar = st.progress(0.0)
        status_text = st.empty()

        for idx, uploaded_file in enumerate(uploaded_files, start=1):
            file_name = uploaded_file.name.replace(".tsv", "").replace(".txt", "")
            status_text.text(f"Procesando {file_name}...")

            try:
                df_clean = clean_tsv_file(uploaded_file)
                df_filtered = df_clean.copy()
                rows_before = len(df_filtered)

                # -----------------------------
                # APLICAR FILTRADO DE FECHAS
                # -----------------------------
                if start_date is not None or end_date is not None:
                    if "Date" not in df_filtered.columns:
                        st.warning(f"⚠️ {file_name}: No tiene columna 'Date', no se puede filtrar por fechas")
                    else:
                        df_filtered["Date"] = pd.to_datetime(df_filtered["Date"], errors="coerce")
                        valid_dates_before = int(df_filtered["Date"].notna().sum())

                        if valid_dates_before == 0:
                            st.warning(f"⚠️ {file_name}: No tiene fechas válidas para filtrar (Date = NaT). Se procesa sin filtro.")
                        else:
                            mask = pd.Series(True, index=df_filtered.index)

                            if start_date is not None:
                                start_dt = pd.Timestamp(start_date).normalize()
                                mask &= df_filtered["Date"] >= start_dt

                            if end_date is not None:
                                end_dt = (
                                    pd.Timestamp(end_date).normalize()
                                    + pd.Timedelta(days=1)
                                    - pd.Timedelta(seconds=1)
                                )
                                mask &= df_filtered["Date"] <= end_dt

                            df_filtered = df_filtered.loc[mask].copy()
                            rows_after = len(df_filtered)

                            if rows_before != rows_after:
                                st.info(f"📊 {file_name}: {rows_before} → {rows_after} muestras (filtro aplicado)")

                            if rows_after == 0:
                                st.warning(f"⚠️ {file_name}: No hay datos en el rango. Se omite.")
                                continue

                # Resetear índices para consistencia
                df_filtered = df_filtered.reset_index(drop=True)

                add_processed_file(file_name, df_filtered)
                st.success(f"✅ {file_name} procesado ({len(df_filtered)} muestras)")

            except Exception as e:
                st.error(f"❌ Error: {file_name}: {e}")
                import traceback

                st.code(traceback.format_exc())

            progress_bar.progress(idx / float(len(uploaded_files)))

        status_text.text("✅ Procesamiento completado")


# =============================================================================
# FASE 2: PREVISUALIZACIÓN Y SELECCIÓN
# =============================================================================
if has_processed_data():
    st.markdown("---")
    st.markdown("### 🔍 FASE 2: Previsualización y Selección de Muestras")

    selected_file = st.selectbox("Archivo:", options=get_processed_files())

    if selected_file:
        df_current = st.session_state.processed_data[selected_file]

        # Limpieza defensiva
        clean_invalid_indices(selected_file)

        removed_indices = get_samples_to_remove(selected_file)
        sample_groups = get_sample_groups(selected_file)

        # =============================================================================
        # SIDEBAR: FILTRO VISUAL
        # =============================================================================
        with st.sidebar:
            st.markdown("### 📅 Filtro Visual")
            st.caption("Solo afecta visualización, no modifica datos")
            
            # Extract available years and months from data
            if 'Date' in df_current.columns:
                df_temp = df_current.copy()
                df_temp['Date'] = pd.to_datetime(df_temp['Date'], errors='coerce')
                available_years = sorted(df_temp['Date'].dt.year.dropna().unique().astype(int).tolist())
                available_months = list(range(1, 13))
                month_names = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                              'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
                
                # Initialize filter for this file if not exists
                if selected_file not in st.session_state.visual_filter_years:
                    st.session_state.visual_filter_years[selected_file] = []
                if selected_file not in st.session_state.visual_filter_months:
                    st.session_state.visual_filter_months[selected_file] = []
                if selected_file not in st.session_state.visual_filter_id:
                    st.session_state.visual_filter_id[selected_file] = ""
                if selected_file not in st.session_state.visual_filter_note:
                    st.session_state.visual_filter_note[selected_file] = ""
                
                # Year selector
                filter_years = st.multiselect(
                    "📅 Años",
                    available_years,
                    default=st.session_state.visual_filter_years[selected_file],
                    key=f"visual_years_{selected_file}"
                )
                st.session_state.visual_filter_years[selected_file] = filter_years
                
                # Month selector
                filter_months = st.multiselect(
                    "📆 Meses (vacío = todos)",
                    available_months,
                    default=st.session_state.visual_filter_months[selected_file],
                    format_func=lambda x: month_names[x-1],
                    key=f"visual_months_{selected_file}"
                )
                st.session_state.visual_filter_months[selected_file] = filter_months
                
                # ID filter
                filter_id = st.text_input(
                    "🔍 ID (contains)",
                    value=st.session_state.visual_filter_id[selected_file],
                    placeholder="e.g., 'ABC123'",
                    key=f"visual_id_{selected_file}"
                )
                st.session_state.visual_filter_id[selected_file] = filter_id
                
                # Note filter
                filter_note = st.text_input(
                    "📝 Note (contains)",
                    value=st.session_state.visual_filter_note[selected_file],
                    placeholder="e.g., 'validation'",
                    key=f"visual_note_{selected_file}"
                )
                st.session_state.visual_filter_note[selected_file] = filter_note
                
                # Reset button
                if st.button("🔄 Resetear Filtro", use_container_width=True):
                    st.session_state.visual_filter_years[selected_file] = []
                    st.session_state.visual_filter_months[selected_file] = []
                    st.session_state.visual_filter_id[selected_file] = ""
                    st.session_state.visual_filter_note[selected_file] = ""
                    clear_last_event_ids(selected_file)
                    st.rerun()
            else:
                st.info("No hay columna Date disponible")

        # Apply visual filter
        df_filtered = apply_visual_filter(df_current, selected_file)
        filter_indicator = get_filter_indicator(df_current, df_filtered)

        vf = get_visual_filter_hash(selected_file)

        # Si cambia el filtro, resetea dedupe de eventos para que el siguiente click no se ignore
        prev_vf = st.session_state.get(f"_vf_prev_{selected_file}")
        if prev_vf != vf:
            st.session_state[f"_vf_prev_{selected_file}"] = vf
            clear_last_event_ids(selected_file)



        # Estadísticas (sobre datos ORIGINALES, no filtrados)
        stats = get_file_statistics(selected_file)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📊 Total", stats["total"])
        col2.metric("🗑️ Eliminar", stats["eliminar"])
        col3.metric("🏷️ Agrupadas", stats["agrupadas"])
        col4.metric("✅ Finales", stats["finales"])
        
        # Filter indicator
        st.info(filter_indicator)

        # Resumen de última aplicación
        summary = get_apply_summary(selected_file)
        if summary:
            parts = []
            if summary.get("eliminar", 0) > 0:
                parts.append(f"{summary['eliminar']} para eliminar")
            if summary.get("grupos", 0) > 0:
                parts.append(f"{summary['grupos']} a grupos")
            if parts:
                st.success(f"✅ Última actualización: {summary['count']} acciones aplicadas ({', '.join(parts)})")

        st.markdown("---")

        # =============================================================================
        # LEYENDA DE GRUPOS
        # =============================================================================
        st.subheader("🏷️ Leyenda de Grupos")
        for group_key in GROUP_KEYS:
            with st.expander(get_group_display_name_with_key(group_key, SAMPLE_GROUPS), expanded=False):
                c1, c2 = st.columns([1, 2])
                with c1:
                    new_label = st.text_input(
                        "Etiqueta:",
                        value=get_group_label(group_key),
                        key=f"label_{selected_file}_{group_key}",
                        max_chars=30,
                    )
                    if new_label != get_group_label(group_key):
                        update_group_label(group_key, new_label)
                with c2:
                    new_desc = st.text_area(
                        "Descripción:",
                        value=get_group_description(group_key),
                        key=f"desc_{selected_file}_{group_key}",
                        max_chars=200,
                        height=100,
                    )
                    if new_desc != get_group_description(group_key):
                        update_group_description(group_key, new_desc)

        st.markdown("---")

        # =============================================================================
        # ESPECTROS
        # =============================================================================
        st.markdown("### 📈 Selección desde Espectros")

        if not INTERACTIVE_SELECTION_AVAILABLE:
            st.warning("⚠️ Selección interactiva no disponible. Instala: `pip install streamlit-plotly-events`")

        spectra_action = "Marcar para Eliminar"
        spectra_target = None
        spectra_multi = False

        if INTERACTIVE_SELECTION_AVAILABLE:
            st.info("💡 Haz **click** para seleccionar espectros individuales o activa **Lasso/Box** para selección múltiple")

            if has_pending_selections(selected_file):
                pending = get_pending_selections(selected_file)
                st.warning(f"⏳ **{len(pending)} acción(es) pendiente(s)**")
                with st.expander("Ver selecciones pendientes", expanded=False):
                    for i, item in enumerate(pending):
                        action_txt = item.get("action", "")
                        if item.get("action") == "Asignar a Grupo":
                            group_key = item.get("group", "Set 1")
                            action_txt += f" → {get_group_display_name(group_key, SAMPLE_GROUPS)}"
                        st.write(f"{i+1}. Muestra **{item.get('idx')}**: {action_txt}")

            colA, colB, colC = st.columns([2, 2, 1])
            with colA:
                spectra_action = st.radio(
                    "Acción:",
                    ["Marcar para Eliminar", "Asignar a Grupo"],
                    key=f"spectra_action_{selected_file}",
                )
            with colB:
                if spectra_action == "Asignar a Grupo":
                    options_disp = get_group_options_display(GROUP_KEYS, SAMPLE_GROUPS)
                    current_key = st.session_state.get(f"spectra_target_{selected_file}", "Set 1")
                    current_disp = (
                        get_group_display_name(current_key, SAMPLE_GROUPS)
                        if current_key in GROUP_KEYS
                        else (options_disp[0] if options_disp else "Set 1")
                    )

                    spectra_target_disp = st.selectbox(
                        "Grupo:",
                        options_disp,
                        index=options_disp.index(current_disp) if current_disp in options_disp else 0,
                        key=f"spectra_target_disp_{selected_file}",
                    )
                    spectra_target = display_to_group_key(spectra_target_disp, GROUP_KEYS, SAMPLE_GROUPS)
                    st.session_state[f"spectra_target_{selected_file}"] = spectra_target

            with colC:
                spectra_multi = st.checkbox("Lasso/Box", value=False, key=f"spectra_multi_{selected_file}")

        try:
            # Build spectra figure with FILTERED data for visualization
            fig_spectra = build_spectra_figure_preview(
                df_filtered,  # Use filtered data for visualization
                removed_indices,
                sample_groups,
                st.session_state.group_labels,
                SAMPLE_GROUPS,
                PIXEL_RE,
            )

            if fig_spectra:
                if not INTERACTIVE_SELECTION_AVAILABLE:
                    st.plotly_chart(fig_spectra, use_container_width=True)
                else:
                    if spectra_multi:
                        fig_spectra.update_layout(dragmode="lasso")

                    events = plotly_events(
                        fig_spectra,
                        click_event=True,
                        select_event=spectra_multi,
                        hover_event=False,
                        override_height=700,
                        key=f"spectra_{selected_file}_v{get_editor_version(selected_file)}_f{vf}",
                    )

                    if events:
                        context = f"{spectra_action}|{spectra_target if spectra_action=='Asignar a Grupo' else ''}"
                        event_id = f"{create_event_id(events)}|{context}"
                        last_id = get_last_event_id(selected_file, "spectra")

                        if event_id != last_id:
                            update_last_event_id(selected_file, "spectra", event_id)

                            # Con tu plotting, tanto click como lasso devuelven customdata en markers
                            clicked_indices = extract_row_indices_from_spectra_events(fig_spectra, events)


                            # Map filtered indices back to original df_current indices
                            original_clicked_indices = clicked_indices


                            if original_clicked_indices:
                                for clicked_idx in original_clicked_indices:
                                    add_pending_selection(
                                        selected_file,
                                        clicked_idx,
                                        spectra_action,
                                        spectra_target if spectra_action == "Asignar a Grupo" else None,
                                    )

                                pending_count = len(get_pending_selections(selected_file))
                                if spectra_action == "Asignar a Grupo" and spectra_target:
                                    st.toast(
                                        f"➕ {len(original_clicked_indices)} muestra(s) a pendientes → grupo: {get_group_display_name(spectra_target, SAMPLE_GROUPS)} ({pending_count} pendientes)",
                                        icon="📍",
                                    )
                                else:
                                    st.toast(
                                        f"➕ {len(original_clicked_indices)} muestra(s) a pendientes → acción: Eliminar ({pending_count} pendientes)",
                                        icon="📍",
                                    )
            else:
                st.warning("No hay datos espectrales")

        except Exception as e:
            st.error(f"Error: {e}")
            import traceback

            st.code(traceback.format_exc())

        # BOTONES DEBAJO DE ESPECTROS
        if INTERACTIVE_SELECTION_AVAILABLE:
            st.markdown("---")
            b1, b2, b3 = st.columns(3)

            with b1:
                if st.button(
                    "✅ Aplicar Selecciones",
                    use_container_width=True,
                    type="primary",
                    disabled=not has_pending_selections(selected_file),
                    key=f"apply_spectra_{selected_file}",
                ):
                    apply_pending_selections(selected_file)
                    st.rerun()

            with b2:
                if st.button(
                    "🗑️ Limpiar Pendientes",
                    use_container_width=True,
                    disabled=not has_pending_selections(selected_file),
                    key=f"clear_spectra_{selected_file}",
                ):
                    n_cleared = clear_pending_selections(selected_file)
                    clear_last_event_ids(selected_file)
                    increment_editor_version(selected_file)
                    st.toast(f"🧹 {n_cleared} acción(es) eliminada(s) de pendientes", icon="🗑️")
                    st.rerun()

            with b3:
                if st.button(
                    "🔄 Confirmar Eliminación",
                    use_container_width=True,
                    disabled=(len(removed_indices) == 0),
                    key=f"delete_spectra_{selected_file}",
                ):
                    deleted_count = confirm_sample_deletion(selected_file)
                    st.success(f"✅ {deleted_count} muestras eliminadas")
                    st.rerun()

        st.markdown("---")

        # =============================================================================
        # PARITY
        # =============================================================================
        st.markdown("### 📊 Selección desde Parity")

        param_names = extract_parameter_names(df_current)
        if not param_names:
            st.warning("No hay parámetros Result")
        else:
            parity_action = "Marcar para Eliminar"
            parity_target = None
            parity_multi = False

            if INTERACTIVE_SELECTION_AVAILABLE:
                st.info("💡 Usa **click** para seleccionar puntos individuales o activa **Lasso/Box** para selección múltiple")

                if has_pending_selections(selected_file):
                    pending = get_pending_selections(selected_file)
                    st.warning(f"⏳ **{len(pending)} acción(es) pendiente(s)**")
                    with st.expander("Ver selecciones pendientes", expanded=False):
                        for i, item in enumerate(pending):
                            action_txt = item.get("action", "")
                            if item.get("action") == "Asignar a Grupo":
                                group_key = item.get("group", "Set 1")
                                action_txt += f" → {get_group_display_name(group_key, SAMPLE_GROUPS)}"
                            st.write(f"{i+1}. Muestra **{item.get('idx')}**: {action_txt}")

                colA, colB, colC = st.columns([2, 2, 1])
                with colA:
                    parity_action = st.radio(
                        "Acción:",
                        ["Marcar para Eliminar", "Asignar a Grupo"],
                        key=f"parity_action_{selected_file}",
                    )
                with colB:
                    if parity_action == "Asignar a Grupo":
                        options_disp = get_group_options_display(GROUP_KEYS, SAMPLE_GROUPS)
                        current_key = st.session_state.get(f"parity_target_{selected_file}", "Set 1")
                        current_disp = (
                            get_group_display_name(current_key, SAMPLE_GROUPS)
                            if current_key in GROUP_KEYS
                            else (options_disp[0] if options_disp else "Set 1")
                        )

                        parity_target_disp = st.selectbox(
                            "Grupo:",
                            options_disp,
                            index=options_disp.index(current_disp) if current_disp in options_disp else 0,
                            key=f"parity_target_disp_{selected_file}",
                        )
                        parity_target = display_to_group_key(parity_target_disp, GROUP_KEYS, SAMPLE_GROUPS)
                        st.session_state[f"parity_target_{selected_file}"] = parity_target

                with colC:
                    parity_multi = st.checkbox("Lasso/Box", value=True, key=f"parity_multi_{selected_file}")

            selected_param = st.selectbox("Parámetro:", param_names, key=f"param_{selected_file}")

            result_col = f"Result {selected_param}"
            reference_col = f"Reference {selected_param}"
            residuum_col = f"Residuum {selected_param}"

            try:
                # Plot comparison with FILTERED data for visualization
                plots = plot_comparison_preview(
                    df_filtered,  # Use filtered data for visualization
                    result_col,
                    reference_col,
                    residuum_col,
                    removed_indices,
                    sample_groups,
                    st.session_state.group_labels,
                    SAMPLE_GROUPS,
                )

                if not plots:
                    st.error(f"No se pudieron generar gráficos para {selected_param}")
                else:
                    fig_parity, fig_res, fig_hist, r2, rmse, bias, n = plots

                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("R²", f"{r2:.3f}")
                    m2.metric("RMSE", f"{rmse:.3f}")
                    m3.metric("BIAS", f"{bias:.3f}")
                    m4.metric("N", n)

                    tab1, tab2, tab3 = st.tabs(["Parity", "Residuum", "Histogram"])

                    with tab1:
                        if not INTERACTIVE_SELECTION_AVAILABLE:
                            st.plotly_chart(fig_parity, use_container_width=True)
                        else:
                            if parity_multi:
                                fig_parity.update_layout(dragmode="lasso")

                            events = plotly_events(
                                fig_parity,
                                click_event=True,
                                select_event=parity_multi,
                                hover_event=False,
                                override_height=600,
                                key=f"parity_{selected_file}_{selected_param}_v{get_editor_version(selected_file)}_f{vf}",
                            )

                            if events:
                                context = f"{parity_action}|{parity_target if parity_action=='Asignar a Grupo' else ''}|{selected_param}"
                                event_id = f"{create_event_id(events)}|{context}"

                                if event_id != last_id:
                                    update_last_event_id(selected_file, "parity", event_id)

                                    clicked_indices = extract_row_indices_from_parity_events(fig_parity, events)
                                    
                                    # Map filtered indices back to original df_current indices
                                    original_clicked_indices = clicked_indices
                                    
                                    if original_clicked_indices:
                                        for clicked_idx in original_clicked_indices:
                                            add_pending_selection(
                                                selected_file,
                                                clicked_idx,
                                                parity_action,
                                                parity_target if parity_action == "Asignar a Grupo" else None,
                                            )

                                        pending_count = len(get_pending_selections(selected_file))
                                        if parity_action == "Asignar a Grupo" and parity_target:
                                            st.toast(
                                                f"➕ {len(original_clicked_indices)} muestra(s) a pendientes → grupo: {get_group_display_name(parity_target, SAMPLE_GROUPS)} ({pending_count} pendientes)",
                                                icon="📍",
                                            )
                                        else:
                                            st.toast(
                                                f"➕ {len(original_clicked_indices)} muestra(s) a pendientes → acción: Eliminar ({pending_count} pendientes)",
                                                icon="📍",
                                            )

                    with tab2:
                        st.plotly_chart(fig_res, use_container_width=True)
                    with tab3:
                        st.plotly_chart(fig_hist, use_container_width=True)

            except Exception as e:
                st.error(f"Error: {e}")
                import traceback

                st.code(traceback.format_exc())

            # BOTONES DEBAJO DE PARITY
            if INTERACTIVE_SELECTION_AVAILABLE:
                st.markdown("---")
                b1, b2, b3 = st.columns(3)

                with b1:
                    if st.button(
                        "✅ Aplicar Selecciones",
                        use_container_width=True,
                        type="primary",
                        disabled=not has_pending_selections(selected_file),
                        key=f"apply_parity_{selected_file}",
                    ):
                        apply_pending_selections(selected_file)
                        st.rerun()

                with b2:
                    if st.button(
                        "🗑️ Limpiar Pendientes",
                        use_container_width=True,
                        disabled=not has_pending_selections(selected_file),
                        key=f"clear_parity_{selected_file}",
                    ):
                        n_cleared = clear_pending_selections(selected_file)
                        clear_last_event_ids(selected_file)
                        increment_editor_version(selected_file)
                        st.toast(f"🧹 {n_cleared} acción(es) eliminada(s) de pendientes", icon="🗑️")
                        st.rerun()

                with b3:
                    if st.button(
                        "🔄 Confirmar Eliminación",
                        use_container_width=True,
                        disabled=(len(removed_indices) == 0),
                        key=f"delete_parity_{selected_file}",
                    ):
                        deleted_count = confirm_sample_deletion(selected_file)
                        st.success(f"✅ {deleted_count} muestras eliminadas")
                        st.rerun()

        st.markdown("---")

        # =============================================================================
        # TABLA INTERACTIVA
        # =============================================================================
        st.subheader("🎯 Selección desde Tabla")
        st.info("💡 **Nuevo flujo:** Marca checkboxes → Elige acción → Añade a pendientes → Aplica")

        if has_pending_selections(selected_file):
            pending = get_pending_selections(selected_file)
            st.warning(f"⏳ **{len(pending)} acción(es) pendiente(s)**")
            with st.expander("Ver selecciones pendientes", expanded=False):
                for i, item in enumerate(pending):
                    action_txt = item.get("action", "")
                    if item.get("action") == "Asignar a Grupo":
                        group_key = item.get("group", "Set 1")
                        action_txt += f" → {get_group_display_name(group_key, SAMPLE_GROUPS)}"
                    st.write(f"{i+1}. Muestra **{item.get('idx')}**: {action_txt}")

        colA, colB = st.columns([2, 2])
        with colA:
            table_action = st.radio(
                "Acción para muestras seleccionadas:",
                ["Marcar para Eliminar", "Asignar a Grupo"],
                key=f"table_action_{selected_file}",
            )
        with colB:
            if table_action == "Asignar a Grupo":
                options_disp = get_group_options_display(GROUP_KEYS, SAMPLE_GROUPS)
                current_key = st.session_state.get(f"table_target_{selected_file}", "Set 1")
                current_disp = (
                    get_group_display_name(current_key, SAMPLE_GROUPS)
                    if current_key in GROUP_KEYS
                    else (options_disp[0] if options_disp else "Set 1")
                )
                table_target_disp = st.selectbox(
                    "Grupo destino:",
                    options_disp,
                    index=options_disp.index(current_disp) if current_disp in options_disp else 0,
                    key=f"table_target_disp_{selected_file}",
                )
                table_target = display_to_group_key(table_target_disp, GROUP_KEYS, SAMPLE_GROUPS)
                st.session_state[f"table_target_{selected_file}"] = table_target
            else:
                table_target = None

        st.markdown("---")

        # Use FILTERED data for table display, pero con RowIndex real como índice
        df_for_edit = df_filtered.copy()

        # RowIndex real: como df_filtered viene de df_current[mask], conserva el índice original
        # Si por lo que sea tu apply_visual_filter devolviera vista, esto lo fuerza
        df_for_edit = df_for_edit.copy()
        df_for_edit.index = df_filtered.index  # explícito: RowIndex real

        df_for_edit.insert(0, "☑️ Seleccionar", False)
        df_for_edit.insert(1, "Estado Actual", "Normal")

        for rid in df_for_edit.index:
            if rid in removed_indices:
                df_for_edit.at[rid, "Estado Actual"] = "❌ Eliminar"
            else:
                gk = sample_groups.get(rid, "none")
                if gk and gk != "none":
                    df_for_edit.at[rid, "Estado Actual"] = get_group_display_name(gk, SAMPLE_GROUPS)


        display_cols = ["☑️ Seleccionar", "Estado Actual"]
        for col in ["ID", "Date", "Note"]:
            if col in df_for_edit.columns:
                display_cols.append(col)

        result_cols = get_parameter_columns(df_for_edit, "Result ")
        display_cols.extend(result_cols[:3])

        with st.expander("📋 Tabla de Muestras", expanded=True):
            edited_df = st.data_editor(
                df_for_edit[display_cols],
                column_config={
                    "☑️ Seleccionar": st.column_config.CheckboxColumn(
                        "☑️ Seleccionar",
                        help="Marca las muestras sobre las que aplicar la acción",
                        default=False,
                    ),
                    "Estado Actual": st.column_config.TextColumn(
                        "Estado Actual",
                        help="Estado actual de la muestra",
                        disabled=True,
                    ),
                },
                disabled=[c for c in display_cols if c != "☑️ Seleccionar"],
                hide_index=False,
                use_container_width=True,
                key=f"editor_{selected_file}_v{get_editor_version(selected_file)}_f{vf}",
            )

            st.markdown("---")

            n_selected = int(edited_df["☑️ Seleccionar"].sum()) if "☑️ Seleccionar" in edited_df.columns else 0
            if n_selected > 0:
                st.info(f"📌 **{n_selected} muestra(s) seleccionada(s)**")

            c1, c2, c3, c4, c5 = st.columns(5)

            with c1:
                if st.button(
                    "➕ Añadir a Pendientes",
                    use_container_width=True,
                    type="primary",
                    disabled=(n_selected == 0),
                    help="Añade las muestras seleccionadas a la lista de acciones pendientes",
                ):
                    selected_indices = edited_df.index[edited_df["☑️ Seleccionar"] == True].tolist()


                    for idx_ in selected_indices:
                        add_pending_selection(
                            selected_file,
                            idx_,
                            table_action,
                            table_target if table_action == "Asignar a Grupo" else None,
                        )

                    pending_count = len(get_pending_selections(selected_file))

                    if table_action == "Asignar a Grupo" and table_target:
                        st.toast(
                            f"➕ {len(selected_indices)} muestra(s) añadidas a pendientes → grupo: {get_group_display_name(table_target, SAMPLE_GROUPS)} ({pending_count} pendientes total)",
                            icon="📍",
                        )
                    else:
                        st.toast(
                            f"➕ {len(selected_indices)} muestra(s) añadidas a pendientes → acción: Eliminar ({pending_count} pendientes total)",
                            icon="📍",
                        )

                    increment_editor_version(selected_file)
                    st.rerun()

            with c2:
                if st.button(
                    "✅ Aplicar Pendientes",
                    use_container_width=True,
                    disabled=not has_pending_selections(selected_file),
                    help="Aplica todas las acciones pendientes",
                ):
                    apply_pending_selections(selected_file)
                    st.rerun()

            with c3:
                if st.button(
                    "🗑️ Limpiar Pendientes",
                    use_container_width=True,
                    disabled=not has_pending_selections(selected_file),
                    help="Limpia la lista de acciones pendientes",
                ):
                    n_cleared = clear_pending_selections(selected_file)
                    clear_last_event_ids(selected_file)
                    increment_editor_version(selected_file)
                    st.toast(f"🧹 {n_cleared} acción(es) eliminada(s) de pendientes", icon="🗑️")
                    st.rerun()

            with c4:
                if st.button(
                    "🔄 Confirmar Eliminación",
                    use_container_width=True,
                    disabled=(len(removed_indices) == 0),
                    help="Elimina definitivamente las muestras marcadas",
                ):
                    deleted_count = confirm_sample_deletion(selected_file)
                    st.success(f"✅ {deleted_count} muestras eliminadas definitivamente")
                    st.rerun()

            with c5:
                if st.button(
                    "↩️ Limpiar Todo",
                    use_container_width=True,
                    disabled=(len(removed_indices) == 0 and len(sample_groups) == 0),
                    help="Limpia todas las marcas y grupos",
                ):
                    clear_all_selections(selected_file)
                    clear_last_event_ids(selected_file)
                    st.rerun()

        # Resumen visual
        if removed_indices or sample_groups:
            st.markdown("---")
            summary_parts = []
            if removed_indices:
                summary_parts.append(f"**{len(removed_indices)} marcadas para eliminar**")
            if sample_groups:
                group_counts = {}
                for g in sample_groups.values():
                    group_counts[g] = group_counts.get(g, 0) + 1
                for group_key, count in group_counts.items():
                    label = get_group_label(group_key)
                    emoji = SAMPLE_GROUPS[group_key]["emoji"]
                    summary_parts.append(f"**{count} en {emoji} {label}**")
            st.info("📊 " + " | ".join(summary_parts))

        # =============================================================================
        # ✨ NUEVA SECCIÓN: ESTADÍSTICAS POR GRUPO
        # =============================================================================
        st.markdown("---")
        st.markdown("### 📊 Estadísticas por Grupo")

        # Verificar si hay grupos asignados
        active_groups = get_active_groups(sample_groups, removed_indices)

        if not active_groups:
            st.info("ℹ️ No hay muestras asignadas a grupos todavía. Asigna muestras a grupos para ver sus estadísticas.")
        else:
            param_names = extract_parameter_names(df_current)

            if not param_names:
                st.warning("⚠️ No hay parámetros disponibles para mostrar estadísticas")
            else:
                # Selector de parámetro para estadísticas
                stats_param = st.selectbox(
                    "Selecciona parámetro para estadísticas:",
                    param_names,
                    key=f"stats_param_{selected_file}",
                    help="Elige el parámetro para el cual mostrar estadísticas por grupo"
                )

                st.markdown("---")

                # Calcular estadísticas para todos los grupos (ALWAYS on FULL df_current)
                all_group_stats = calculate_all_groups_statistics(
                    df_current,  # Use full data for statistics
                    stats_param,
                    removed_indices,
                    sample_groups,
                    GROUP_KEYS
                )

                # Contar muestras por grupo
                group_sample_counts = count_samples_per_group(sample_groups, removed_indices, GROUP_KEYS)

                # Mostrar estadísticas de cada grupo activo en expandibles
                for group_key in GROUP_KEYS:
                    if group_key not in active_groups:
                        continue

                    n_samples = group_sample_counts.get(group_key, 0)

                    if n_samples == 0:
                        continue

                    display_name = get_group_display_name_with_key(group_key, SAMPLE_GROUPS)
                    stats = all_group_stats.get(group_key)

                    with st.expander(f"{display_name} ({n_samples} muestras)", expanded=True):
                        if stats is None:
                            st.warning(f"⚠️ No hay suficientes datos válidos para calcular estadísticas (mínimo 2 muestras con valores válidos)")
                        else:
                            # Mostrar métricas en columnas
                            col1, col2, col3, col4 = st.columns(4)
                            col1.metric("R²", f"{stats['r2']:.4f}")
                            col2.metric("RMSE", f"{stats['rmse']:.3f}")
                            col3.metric("BIAS", f"{stats['bias']:.3f}")
                            col4.metric("N", stats['n'])

                            # Mostrar descripción del grupo si existe
                            desc = get_group_description(group_key)
                            if desc:
                                st.caption(f"📝 {desc}")

                # Tabla resumen comparativa (opcional)
                st.markdown("---")
                st.subheader("📋 Resumen Comparativo")

                summary_df = get_statistics_summary(
                    all_group_stats,
                    st.session_state.group_labels,
                    SAMPLE_GROUPS
                )

                if not summary_df.empty:
                    st.dataframe(
                        summary_df,
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("No hay estadísticas disponibles para mostrar")


# =============================================================================
# FASE 3: GENERACIÓN DE REPORTES
# =============================================================================
if has_processed_data():
    st.markdown("---")
    st.markdown("### 📥 FASE 3: Generar Reportes Finales")

    st.subheader("📋 Resumen de Archivos")
    summary_data = []
    for fname in get_processed_files():
        stats = get_file_statistics(fname)
        df = st.session_state.processed_data[fname]
        summary_data.append(
            {
                "Archivo": fname,
                "Muestras": stats["total"],
                "Agrupadas": stats["agrupadas"],
                "Parámetros": len(get_parameter_columns(df, "Result ")),
            }
        )
    st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)

    st.markdown("---")
    if st.button("📥 Generar Informes HTML", type="primary", use_container_width=True):
        results: List[ReportResult] = []
        progress_bar = st.progress(0.0)

        for idx, file_name in enumerate(get_processed_files(), start=1):
            try:
                df = st.session_state.processed_data[file_name]

                if len(df) == 0:
                    st.warning(f"⚠️ {file_name}: No hay datos")
                    continue

                sample_groups_file = get_sample_groups(file_name)

                html = generate_html_report(
                    df,
                    file_name,
                    sample_groups_file,
                    st.session_state.group_labels,
                    st.session_state.group_descriptions,
                    SAMPLE_GROUPS,
                    PIXEL_RE,
                )

                results.append(ReportResult(name=file_name, html=html, csv=df))
                st.success(f"✅ {file_name}")

            except Exception as e:
                st.error(f"❌ {file_name}: {e}")

            progress_bar.progress(idx / float(len(get_processed_files())))

        if results:
            st.markdown("---")
            if len(results) > 1:
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    for r in results:
                        zf.writestr(f"{r.name}.html", r.html)

                st.download_button(
                    "📦 Descargar ZIP",
                    data=zip_buffer.getvalue(),
                    file_name="reports.zip",
                    mime="application/zip",
                    use_container_width=True,
                )
                st.markdown("---")

            for r in results:
                st.markdown(f"**{r.name}**")
                st.download_button(
                    "💾 Descargar HTML",
                    data=r.html,
                    file_name=f"{r.name}.html",
                    mime="text/html",
                    key=f"dl_{r.name}",
                )
                st.markdown("---")