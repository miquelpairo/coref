"""
COREF - TSV Validation Reports
==============================
Generación de informes de validación NIR (TSV) con previsualización y selección de muestras.

Refactorizado para usar módulos especializados:
- tsv_session_manager: Gestión del estado de sesión
- tsv_processing: Limpieza y procesamiento de TSV
- selection_utils: Extracción de eventos de gráficos
- filehandlers: Carga de archivos

FIX UI (labels de grupo):
- En los selectbox de selección (Espectros/Parity) y en la tabla, se muestran los nombres
  personalizados definidos por el usuario (group_labels), pero se sigue guardando internamente
  "Set 1..Set 4" para no romper nada.
- En la leyenda de grupos, se muestra: "Etiqueta (Set X)".
"""

from __future__ import annotations

import zipfile
from io import BytesIO
from typing import List

import pandas as pd
import streamlit as st
import plotly.graph_objs as go

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
    update_groups_from_editor,
    clear_all_selections,
    clear_all_groups,
    clean_invalid_indices,
    get_file_statistics,
    get_editor_version,
    update_last_event_id,
    get_last_event_id,
    update_group_label,
    update_group_description,
    get_group_label,
    get_group_description,
)
from core.tsv_processing import (
    clean_tsv_file,
    get_spectral_columns,
    get_parameter_columns,
    extract_parameter_names,
    PIXEL_RE,
)
from core.selection_utils import (
    create_event_id,
    extract_row_index_from_click,
    extract_row_indices_from_spectra_events,
    extract_row_indices_from_parity_events,
)

try:
    from streamlit_plotly_events import plotly_events

    INTERACTIVE_SELECTION_AVAILABLE = True
except Exception:
    plotly_events = None
    INTERACTIVE_SELECTION_AVAILABLE = False


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
### Cómo usar TSV Validation Reports:

**1. Cargar Archivos TSV:**
- Sube archivos TSV (export/journal de NIR-Online)
- Soporte para múltiples encodings

**2. Filtrar por Fechas (Opcional)**

**3. Previsualización y Selección:**
- Selección desde gráficos (Espectros: click + lasso/box | Parity: click + lasso/box)
- Selección desde tabla interactiva
- Grupos personalizables con símbolos

**4. Generación de Reportes HTML**
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
# HELPERS (GROUP DISPLAY)
# =============================================================================
def group_display_name(group_key: str) -> str:
    """Texto visible al usuario (emoji + label). Mantiene clave interna Set 1..4."""
    emoji = SAMPLE_GROUPS.get(group_key, {}).get("emoji", "")
    label = get_group_label(group_key)
    return f"{emoji} {label}".strip()


def group_display_name_with_key(group_key: str) -> str:
    """Visible: etiqueta + (Set X)."""
    emoji = SAMPLE_GROUPS.get(group_key, {}).get("emoji", "")
    label = get_group_label(group_key)
    return f"{emoji} {label} ({group_key})".strip()


def group_options_display() -> List[str]:
    return [group_display_name(g) for g in GROUP_KEYS]


def display_to_group_key(display_value: str) -> str:
    """Mapeador display -> key interna."""
    mapping = {group_display_name(g): g for g in GROUP_KEYS}
    return mapping.get(display_value, "Set 1")


def group_key_to_display(group_key: str) -> str:
    """Key interna -> display (sin (Set X), para dropdowns de selección)."""
    if not group_key or group_key == "none":
        return "Sin grupo"
    return group_display_name(group_key)


def group_options_display_table() -> List[str]:
    """Opciones para tabla (incluye Sin grupo)."""
    return ["Sin grupo"] + [group_display_name(g) for g in GROUP_KEYS]

def _read_dates_fast(uploaded_file) -> pd.Series:
    encodings = ["utf-8", "ISO-8859-1", "latin-1", "cp1252"]
    for enc in encodings:
        try:
            uploaded_file.seek(0)
            df = pd.read_csv(
                uploaded_file,
                sep="\t",
                usecols=["Date"],
                dtype={"Date": "string"},
                encoding=enc,
                keep_default_na=False,
            )
            return df["Date"]
        except Exception:
            continue
    return pd.Series([], dtype="string")


def _parse_dates(s: pd.Series) -> pd.Series:
    if s is None or s.empty:
        return pd.to_datetime([], errors="coerce")
    s = s.astype("string").str.strip()
    s = s[s != ""]
    return pd.to_datetime(s, errors="coerce", dayfirst=True)

# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================
initialize_tsv_session_state()


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

# =============================================================================
# PREVIEW: Nº DE MUESTRAS POR MES Y ARCHIVO (ANTES DEL FILTRO)
# =============================================================================
with st.expander("📊 Preview: nº de muestras por mes y archivo (antes del filtro)", expanded=True):

    rows = []

    for uf in uploaded_files:
        file_name = uf.name.replace(".tsv", "").replace(".txt", "")
        dates_raw = _read_dates_fast(uf)
        dates = _parse_dates(dates_raw).dropna()

        if dates.empty:
            continue

        tmp = (
            dates
            .dt.to_period("M")
            .value_counts()
            .sort_index()
            .rename("count")
            .reset_index()
        )
        tmp.columns = ["Mes", "Muestras"]
        tmp["Archivo"] = file_name
        tmp["Mes"] = tmp["Mes"].dt.to_timestamp()

        rows.append(tmp)

    if rows:
        df_plot = pd.concat(rows, ignore_index=True)

        fig = go.Figure()

        for fname, g in df_plot.groupby("Archivo"):
            fig.add_bar(
                x=g["Mes"],
                y=g["Muestras"],
                name=fname,
            )

        fig.update_layout(
            barmode="group",   # columnas por archivo
            height=400,
            title="Nº de muestras por mes (por archivo)",
            xaxis_title="Mes",
            yaxis_title="Nº de muestras",
            template="plotly",
        )

        st.plotly_chart(fig, use_container_width=True)
        st.caption("Datos brutos, antes de aplicar filtros de fecha.")
    else:
        st.info("No se encontraron fechas válidas en los archivos cargados.")
    
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
                            st.info(f"📊 {file_name}: {rows_before} → {rows_after} muestras")
                        if rows_after == 0:
                            st.warning(f"⚠️ {file_name}: No hay datos en el rango. Se omite.")
                            continue
                else:
                    if start_date or end_date:
                        st.warning(f"⚠️ {file_name}: No tiene columna 'Date'")

                # Resetear índices para consistencia
                df_filtered = df_filtered.reset_index(drop=True)

                # Usar función del session manager
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

        # Limpiar índices inválidos
        clean_invalid_indices(selected_file)

        removed_indices = get_samples_to_remove(selected_file)
        sample_groups = get_sample_groups(selected_file)

        # Estadísticas
        stats = get_file_statistics(selected_file)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📊 Total", stats["total"])
        col2.metric("🗑️ Eliminar", stats["eliminar"])
        col3.metric("🏷️ Agrupadas", stats["agrupadas"])
        col4.metric("✅ Finales", stats["finales"])

        # Mostrar resumen de última aplicación
        summary = get_apply_summary(selected_file)
        if summary:
            parts = []
            if summary["eliminar"] > 0:
                parts.append(f"{summary['eliminar']} para eliminar")
            if summary["grupos"] > 0:
                parts.append(f"{summary['grupos']} a grupos")

            if parts:
                st.success(f"✅ Última actualización: {summary['count']} acciones aplicadas ({', '.join(parts)})")

        st.markdown("---")

        # LEYENDA DE GRUPOS
        st.subheader("🏷️ Leyenda de Grupos")
        for group_key in GROUP_KEYS:
            # ✅ aquí: etiqueta + (Set X)
            with st.expander(group_display_name_with_key(group_key), expanded=False):
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
                        action_txt = item["action"]
                        if item["action"] == "Asignar a Grupo":
                            action_txt += f" → {group_display_name(item.get('group', 'Set 1'))}"
                        st.write(f"{i+1}. Muestra **{item['idx']}**: {action_txt}")

            colA, colB, colC = st.columns([2, 2, 1])
            with colA:
                spectra_action = st.radio(
                    "Acción:",
                    ["Marcar para Eliminar", "Asignar a Grupo"],
                    key=f"spectra_action_{selected_file}",
                )
            with colB:
                if spectra_action == "Asignar a Grupo":
                    options_disp = group_options_display()
                    current_key = st.session_state.get(f"spectra_target_{selected_file}", "Set 1")
                    current_disp = group_display_name(current_key) if current_key in GROUP_KEYS else options_disp[0]

                    spectra_target_disp = st.selectbox(
                        "Grupo:",
                        options_disp,
                        index=options_disp.index(current_disp) if current_disp in options_disp else 0,
                        key=f"spectra_target_disp_{selected_file}",
                    )
                    spectra_target = display_to_group_key(spectra_target_disp)
                    st.session_state[f"spectra_target_{selected_file}"] = spectra_target

            with colC:
                spectra_multi = st.checkbox("Lasso/Box", value=False, key=f"spectra_multi_{selected_file}")

        try:
            fig_spectra = build_spectra_figure_preview(
                df_current,
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
                        key=f"spectra_{selected_file}_v{get_editor_version(selected_file)}",
                    )

                    if events:
                        event_id = create_event_id(events)
                        last_id = get_last_event_id(selected_file, "spectra")

                        if event_id != last_id:
                            update_last_event_id(selected_file, "spectra", event_id)

                            if spectra_multi:
                                clicked_indices = extract_row_indices_from_spectra_events(fig_spectra, events)
                            else:
                                single_idx = extract_row_index_from_click(fig_spectra, events[0])
                                clicked_indices = [single_idx] if single_idx is not None else []

                            if clicked_indices:
                                for clicked_idx in clicked_indices:
                                    add_pending_selection(
                                        selected_file,
                                        clicked_idx,
                                        spectra_action,
                                        spectra_target if spectra_action == "Asignar a Grupo" else None,
                                    )

                                pending_count = len(get_pending_selections(selected_file))

                                if spectra_action == "Asignar a Grupo" and spectra_target:
                                    st.toast(
                                        f"➕ {len(clicked_indices)} muestra(s) a pendientes → grupo: {group_display_name(spectra_target)} ({pending_count} pendientes)",
                                        icon="📍",
                                    )
                                else:
                                    st.toast(
                                        f"➕ {len(clicked_indices)} muestra(s) a pendientes → acción: Eliminar ({pending_count} pendientes)",
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

                    # Evita reenganche del último evento
                    update_last_event_id(selected_file, "spectra", "")
                    update_last_event_id(selected_file, "parity", "")

                    st.toast(
                        f"🧹 {n_cleared} acción(es) eliminada(s) de pendientes",
                        icon="🗑️",
                    )
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
            if not INTERACTIVE_SELECTION_AVAILABLE:
                st.warning("⚠️ Selección interactiva no disponible. Instala: `pip install streamlit-plotly-events`")

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
                            action_txt = item["action"]
                            if item["action"] == "Asignar a Grupo":
                                action_txt += f" → {group_display_name(item.get('group', 'Set 1'))}"
                            st.write(f"{i+1}. Muestra **{item['idx']}**: {action_txt}")

                colA, colB, colC = st.columns([2, 2, 1])
                with colA:
                    parity_action = st.radio(
                        "Acción:",
                        ["Marcar para Eliminar", "Asignar a Grupo"],
                        key=f"parity_action_{selected_file}",
                    )
                with colB:
                    if parity_action == "Asignar a Grupo":
                        options_disp = group_options_display()
                        current_key = st.session_state.get(f"parity_target_{selected_file}", "Set 1")
                        current_disp = group_display_name(current_key) if current_key in GROUP_KEYS else options_disp[0]

                        parity_target_disp = st.selectbox(
                            "Grupo:",
                            options_disp,
                            index=options_disp.index(current_disp) if current_disp in options_disp else 0,
                            key=f"parity_target_disp_{selected_file}",
                        )
                        parity_target = display_to_group_key(parity_target_disp)
                        st.session_state[f"parity_target_{selected_file}"] = parity_target

                with colC:
                    parity_multi = st.checkbox("Lasso/Box", value=True, key=f"parity_multi_{selected_file}")

            selected_param = st.selectbox("Parámetro:", param_names, key=f"param_{selected_file}")

            result_col = f"Result {selected_param}"
            reference_col = f"Reference {selected_param}"
            residuum_col = f"Residuum {selected_param}"

            try:
                plots = plot_comparison_preview(
                    df_current,
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
                                key=f"parity_{selected_file}_{selected_param}_v{get_editor_version(selected_file)}",
                            )

                            if events:
                                event_id = create_event_id(events)
                                last_id = get_last_event_id(selected_file, "parity")

                                if event_id != last_id:
                                    update_last_event_id(selected_file, "parity", event_id)

                                    clicked_indices = extract_row_indices_from_parity_events(fig_parity, events)
                                    if clicked_indices:
                                        for clicked_idx in clicked_indices:
                                            add_pending_selection(
                                                selected_file,
                                                clicked_idx,
                                                parity_action,
                                                parity_target if parity_action == "Asignar a Grupo" else None,
                                            )

                                        pending_count = len(get_pending_selections(selected_file))

                                        if parity_action == "Asignar a Grupo" and parity_target:
                                            st.toast(
                                                f"➕ {len(clicked_indices)} muestra(s) a pendientes → grupo: {group_display_name(parity_target)} ({pending_count} pendientes)",
                                                icon="📍",
                                            )
                                        else:
                                            st.toast(
                                                f"➕ {len(clicked_indices)} muestra(s) a pendientes → acción: Eliminar ({pending_count} pendientes)",
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

                        update_last_event_id(selected_file, "parity", "")
                        update_last_event_id(selected_file, "spectra", "")

                        st.toast(
                            f"🧹 {n_cleared} acción(es) eliminada(s) de pendientes",
                            icon="🗑️",
                        )
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
        # TABLA INTERACTIVA (PATCH SIN format_func)
        # =============================================================================
        st.subheader("🎯 Selección desde Tabla")
        st.info("✅ Marca para **Eliminar** o asigna un **Grupo** → Presiona **'Actualizar Selección'**")

        df_for_edit = df_current.copy()

        # Interno (lo que espera el session_manager)
        df_for_edit.insert(0, "Grupo", "none")
        df_for_edit.insert(0, "Eliminar", False)

        for idx_ in removed_indices:
            if idx_ in df_for_edit.index:
                df_for_edit.at[idx_, "Eliminar"] = True

        for idx_, grp_ in sample_groups.items():
            if idx_ in df_for_edit.index:
                df_for_edit.at[idx_, "Grupo"] = grp_

        # Visible y editable
        df_for_edit.insert(1, "Grupo (Etiqueta)", "Sin grupo")
        for idx_ in df_for_edit.index:
            g = df_for_edit.at[idx_, "Grupo"]
            df_for_edit.at[idx_, "Grupo (Etiqueta)"] = group_key_to_display(g)

        display_cols = ["Eliminar", "Grupo (Etiqueta)"]
        for col in ["ID", "Date", "Note"]:
            if col in df_for_edit.columns:
                display_cols.append(col)

        result_cols = get_parameter_columns(df_for_edit, "Result ")
        display_cols.extend(result_cols[:3])

        with st.expander("📋 Tabla de Muestras", expanded=False):
            edited_df = st.data_editor(
                df_for_edit[display_cols],
                column_config={
                    "Eliminar": st.column_config.CheckboxColumn("Eliminar", default=False),
                    "Grupo (Etiqueta)": st.column_config.SelectboxColumn(
                        "Grupo",
                        options=group_options_display_table(),
                        default="Sin grupo",
                    ),
                },
                disabled=[c for c in display_cols if c not in ["Eliminar", "Grupo (Etiqueta)"]],
                hide_index=False,
                use_container_width=True,
                key=f"editor_{selected_file}_v{get_editor_version(selected_file)}",
            )

            st.markdown("---")
            c1, c2, c3, c4 = st.columns(4)

            with c1:
                if st.button("🔄 Actualizar Selección", use_container_width=True, type="primary"):
                    # Convertimos display -> key interna y llamamos al session_manager
                    tmp = pd.DataFrame(index=edited_df.index)
                    tmp["Eliminar"] = edited_df["Eliminar"].astype(bool)

                    mapped = {}
                    for idx_ in edited_df.index:
                        disp = str(edited_df.at[idx_, "Grupo (Etiqueta)"])
                        if disp == "Sin grupo":
                            mapped[idx_] = "none"
                        else:
                            mapped[idx_] = display_to_group_key(disp)
                    tmp["Grupo"] = pd.Series(mapped)

                    update_groups_from_editor(selected_file, tmp)

                    stats = get_file_statistics(selected_file)
                    st.success(f"✅ Actualizado: {stats['eliminar']} eliminar, {stats['agrupadas']} agrupadas")
                    st.rerun()

            with c2:
                if st.button("🗑️ Confirmar Eliminación", use_container_width=True, disabled=(len(removed_indices) == 0)):
                    deleted_count = confirm_sample_deletion(selected_file)
                    st.success(f"✅ {deleted_count} muestras eliminadas")
                    st.rerun()

            with c3:
                if st.button(
                    "↩️ Limpiar Todo",
                    use_container_width=True,
                    disabled=(len(removed_indices) == 0 and len(sample_groups) == 0),
                ):
                    clear_all_selections(selected_file)
                    st.rerun()

            with c4:
                if st.button("🔄 Limpiar Grupos", use_container_width=True, disabled=(len(sample_groups) == 0)):
                    clear_all_groups(selected_file)
                    st.rerun()

        if removed_indices or sample_groups:
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
