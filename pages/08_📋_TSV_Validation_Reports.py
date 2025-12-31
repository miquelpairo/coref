"""
COREF - TSV Validation Reports
==============================
Selección desde gráficos con fallback para cloud

FIXES IMPORTANTES (plotly_events):
- customdata debe ser JSON-safe (listas/ints Python, no numpy) -> esto va en core.tsv_plotting
- extractor de espectros: usa pointNumber (antes cogías customdata[0] y fallaba)
- last_event_id separado por gráfico (spectra/parity) para evitar colisiones
- PIXEL_RE más robusto: acepta #123 y 123 (por si algún TSV viene sin #)
- limpia el "typo" del final (había texto suelto tras st.markdown("---"))

MEJORAS UI:
- st.toast() para feedback inmediato al hacer click (sin re-render molesto)
- st.success() con resumen después de aplicar selecciones
- Lasso/Box habilitado para espectros (agrupa por row_index único)
- FIX: Extractor específico para espectros con lasso/box (customdata es int, no lista)
"""

from __future__ import annotations

import re
import zipfile
from io import BytesIO
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st
from dateutil import parser as date_parser

from auth import check_password
from buchi_streamlit_theme import apply_buchi_styles
from core.tsv_plotting import plot_comparison_preview, build_spectra_figure_preview
from core.tsv_report_generator import generate_html_report, ReportResult

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
    st.markdown("""
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
""")


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


# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================
st.session_state.setdefault("processed_data", {})
st.session_state.setdefault("samples_to_remove", {})
st.session_state.setdefault("sample_groups", {})
st.session_state.setdefault("group_labels", {"Set 1": "Set 1", "Set 2": "Set 2", "Set 3": "Set 3", "Set 4": "Set 4"})
st.session_state.setdefault("group_descriptions", {"Set 1": "", "Set 2": "", "Set 3": "", "Set 4": ""})
st.session_state.setdefault("editor_version", {})
st.session_state.setdefault("pending_selections", {})

# FIX: last_event_id separado por gráfico para evitar colisiones spectra/parity
# estructura: last_event_id[file] = {"spectra": "...", "parity": "..."}
st.session_state.setdefault("last_event_id", {})

# NUEVO: Guardar resumen de última aplicación para mostrar después del rerun
st.session_state.setdefault("last_apply_summary", {})


# =============================================================================
# DATA CLEANING / NODE-RED LOGIC
# =============================================================================
# FIX: acepta #123 y 123 (más robusto en cloud si el TSV cambia)
PIXEL_RE = re.compile(r"^(#)?\d+$")


def _is_pixel_col(col: str) -> bool:
    return bool(PIXEL_RE.fullmatch(str(col)))


def _pixnum(col: str) -> int:
    s = str(col)
    return int(s[1:]) if s.startswith("#") else int(s)


def clean_value(v: str) -> Optional[float]:
    """Limpia un valor removiendo unidades comunes y convirtiendo a float."""
    if v is None:
        return None
    s = str(v).strip()
    if s in ("", "-", "NA", "NaN", "nan"):
        return None
    if s.startswith("-.") or s.startswith("-.-"):
        return None
    s = s.replace("%", "").replace("ppm", "").replace(",", ".").strip()
    if s in ("", "-", "NA", "NaN", "nan"):
        return None
    try:
        return float(s)
    except Exception:
        return None


def filter_relevant_data(data: List[Dict]) -> List[Dict]:
    """Mantiene metadata hasta #X1 + columnas espectrales (#1..#n o 1..n)."""
    if not data:
        return []
    all_columns = list(data[0].keys())
    stop_column = "#X1"
    base_cols: List[str] = []
    for col in all_columns:
        if col == stop_column:
            break
        base_cols.append(col)

    pixel_cols = sorted([c for c in all_columns if _is_pixel_col(c)], key=_pixnum)
    columns_to_keep = base_cols + pixel_cols

    filtered: List[Dict] = []
    for row in data:
        new_row = {}
        for col in columns_to_keep:
            v = row.get(col, None)
            new_row[col] = v if v not in ("", None) else None
        filtered.append(new_row)
    return filtered


def delete_zero_rows(data: List[Dict]) -> List[Dict]:
    """Elimina filas donde Result esté vacío o todos los valores sean 0."""
    out: List[Dict] = []
    for row in data:
        if "Result" not in row:
            continue
        result_val = row.get("Result")
        if result_val is None or str(result_val).strip() == "":
            continue
        result_values = str(result_val).split(";")
        cleaned = [clean_value(v) for v in result_values]
        cleaned = [v for v in cleaned if v is not None]
        if not cleaned:
            continue
        if all(v == 0.0 for v in cleaned):
            continue
        out.append(row)
    return out


def reorganize_results_and_reference(data: List[Dict]) -> List[Dict]:
    """Reorganiza a: Reference <param>, Result <param>, Residuum <param>"""
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
        parameter_cols = all_cols[ref_i + 1: begin_i]
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
            ref_val_f = clean_value(ref_val) if (ref_val not in (None, "")) else None
            res_val_f = None
            if idx < len(result_values):
                res_val_f = clean_value(result_values[idx])

            if res_val_f is None:
                param_col_val = row.get(p)
                if param_col_val is not None and param_col_val != "":
                    res_val_f = clean_value(param_col_val)

            new_row[f"Reference {p}"] = ref_val_f
            new_row[f"Result {p}"] = res_val_f
            new_row[f"Residuum {p}"] = (res_val_f - ref_val_f) if (ref_val_f is not None and res_val_f is not None) else None

        reorganized.append(new_row)
    return reorganized


def try_parse_date(date_str) -> pd.Timestamp:
    """Intenta convertir fecha con formatos comunes y fallback a dateutil"""
    if pd.isna(date_str) or date_str is None or str(date_str).strip() == "":
        return pd.NaT
    s = str(date_str).strip()
    fmts = ["%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m-%d-%Y", "%Y-%m-%d %H:%M:%S"]
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
    """Pipeline completo de limpieza de TSV."""
    uploaded_file.seek(0)
    encodings_to_try = ["utf-8", "ISO-8859-1", "latin-1", "cp1252"]
    df_raw = None

    for encoding in encodings_to_try:
        try:
            uploaded_file.seek(0)
            df_raw = pd.read_csv(uploaded_file, delimiter="\t", keep_default_na=False, encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
        except Exception:
            try:
                uploaded_file.seek(0)
                df_raw = pd.read_csv(
                    uploaded_file,
                    delimiter="\t",
                    keep_default_na=False,
                    encoding=encoding,
                    doublequote=False,
                    escapechar="\\",
                )
                break
            except Exception:
                continue

    if df_raw is None:
        raise ValueError("❌ No se pudo leer el archivo")

    data = df_raw.to_dict("records")
    data = filter_relevant_data(data)
    data = delete_zero_rows(data)
    data = reorganize_results_and_reference(data)

    df = pd.DataFrame(data)

    if not df.empty:
        pixel_cols = [c for c in df.columns if _is_pixel_col(c)]
        if pixel_cols:
            df[pixel_cols] = df[pixel_cols].astype(str).replace(",", ".", regex=True)
            df[pixel_cols] = df[pixel_cols].apply(pd.to_numeric, errors="coerce")

    if "Date" in df.columns:
        df["Date"] = df["Date"].apply(try_parse_date)

    return df


# =============================================================================
# HELPER: EXTRACT ROW INDEX FROM CLICK EVENT (ESPECTROS)
# =============================================================================
def _extract_row_index_from_click(fig, event) -> Optional[int]:
    """
    Extrae el índice de fila desde click event.
    FIX: usa pointNumber cuando customdata es lista por punto (espectros).
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

        # Si viene pointNumber, usa el punto exacto (lo correcto en espectros)
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


# =============================================================================
# HELPER: EXTRACT ROW INDICES FROM SPECTRA EVENTS (LASSO/BOX)
# =============================================================================
def _extract_row_indices_from_spectra_events(fig, events) -> List[int]:
    """
    Extrae índices de fila desde eventos de espectros (lasso/box).
    En espectros, customdata es un int directo (no lista como en parity).
    """
    if not events:
        return []

    def _coerce(cd):
        if cd is None:
            return None
        # En espectros customdata es int directo
        try:
            return int(cd)
        except Exception:
            return None

    out: List[int] = []
    for ev in events:
        # Intentar extraer directamente de customdata
        idx = _coerce(ev.get("customdata", None))
        if idx is not None:
            out.append(idx)
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

            idx = _coerce(trace_cd[point])
            if idx is not None:
                out.append(idx)
        except Exception:
            pass

    # Eliminar duplicados preservando orden
    seen = set()
    uniq: List[int] = []
    for x in out:
        if x not in seen:
            uniq.append(x)
            seen.add(x)
    
    return uniq


# =============================================================================
# HELPER: EXTRACT ROW INDICES FROM EVENTS (PARITY - LASSO/BOX)
# =============================================================================
def _extract_row_indices_from_events(fig, events) -> List[int]:
    """Extrae índices de fila desde eventos (click o lasso/box select)."""
    if not events:
        return []

    def _coerce(cd):
        if cd is None:
            return None
        # En parity tu customdata suele ser [row_id, date] => nos quedamos con row_id
        if isinstance(cd, (list, tuple)) and len(cd) > 0:
            cd = cd[0]
        try:
            return int(cd)
        except Exception:
            return None

    out: List[int] = []
    for ev in events:
        idx = _coerce(ev.get("customdata", None))
        if idx is not None:
            out.append(idx)
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

            idx = _coerce(trace_cd[point])
            if idx is not None:
                out.append(idx)
        except Exception:
            pass

    # uniq preservando orden
    seen = set()
    uniq: List[int] = []
    for x in out:
        if x not in seen:
            uniq.append(x)
            seen.add(x)
    return uniq


def _create_event_id(events) -> str:
    """Crea un ID único para un conjunto de eventos."""
    if not events:
        return ""
    event_str = str([(e.get("curveNumber"), e.get("pointNumber"), e.get("customdata")) for e in events])
    return str(hash(event_str))


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

        st.session_state.processed_data = {}
        st.session_state.samples_to_remove = {}
        st.session_state.sample_groups = {}
        st.session_state.editor_version = {}
        st.session_state.pending_selections = {}
        st.session_state.last_event_id = {}
        st.session_state.last_apply_summary = {}

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

                # IMPORTANT: índice 0..n para que todo sea consistente (selección y borrado)
                df_filtered = df_filtered.reset_index(drop=True)

                st.session_state.processed_data[file_name] = df_filtered
                st.session_state.samples_to_remove[file_name] = set()
                st.session_state.sample_groups[file_name] = {}
                st.session_state.editor_version[file_name] = 0
                st.session_state.pending_selections[file_name] = []

                # FIX: last_event_id por gráfico
                st.session_state.last_event_id[file_name] = {"spectra": "", "parity": ""}

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
if st.session_state.processed_data:
    st.markdown("---")
    st.markdown("### 🔍 FASE 2: Previsualización y Selección de Muestras")

    selected_file = st.selectbox("Archivo:", options=list(st.session_state.processed_data.keys()))

    if selected_file:
        st.session_state.editor_version.setdefault(selected_file, 0)
        st.session_state.pending_selections.setdefault(selected_file, [])
        st.session_state.last_event_id.setdefault(selected_file, {"spectra": "", "parity": ""})

        df_current = st.session_state.processed_data[selected_file]
        removed_indices = st.session_state.samples_to_remove.get(selected_file, set())
        sample_groups = st.session_state.sample_groups.get(selected_file, {})

        # Limpiar índices inválidos
        valid_removed = {i for i in removed_indices if i in df_current.index}
        valid_groups = {i: g for i, g in sample_groups.items() if i in df_current.index}
        if len(valid_removed) != len(removed_indices):
            st.session_state.samples_to_remove[selected_file] = valid_removed
        if len(valid_groups) != len(sample_groups):
            st.session_state.sample_groups[selected_file] = valid_groups
        removed_indices = valid_removed
        sample_groups = valid_groups

        # Estadísticas
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📊 Total", len(df_current))
        col2.metric("🗑️ Eliminar", len(removed_indices))
        grouped_count = sum(1 for g in sample_groups.values() if g != "none")
        col3.metric("🏷️ Agrupadas", grouped_count)
        col4.metric("✅ Finales", len(df_current) - len(removed_indices))

        # NUEVO: Mostrar resumen de última aplicación (después de las métricas)
        if selected_file in st.session_state.last_apply_summary:
            summary = st.session_state.last_apply_summary[selected_file]
            parts = []
            if summary['eliminar'] > 0:
                parts.append(f"{summary['eliminar']} para eliminar")
            if summary['grupos'] > 0:
                parts.append(f"{summary['grupos']} a grupos")
            
            if parts:
                st.success(f"✅ Última actualización: {summary['count']} acciones aplicadas ({', '.join(parts)})")
            
            # Limpiar para que no se muestre en el siguiente rerun por otro motivo
            del st.session_state.last_apply_summary[selected_file]

        st.markdown("---")

        # LEYENDA DE GRUPOS
        st.subheader("🏷️ Leyenda de Grupos")
        group_keys = ["Set 1", "Set 2", "Set 3", "Set 4"]
        for group_key in group_keys:
            with st.expander(f"{SAMPLE_GROUPS[group_key]['emoji']} {group_key}", expanded=False):
                c1, c2 = st.columns([1, 2])
                with c1:
                    new_label = st.text_input(
                        "Etiqueta:",
                        value=st.session_state.group_labels[group_key],
                        key=f"label_{selected_file}_{group_key}",
                        max_chars=30
                    )
                    if new_label != st.session_state.group_labels[group_key]:
                        st.session_state.group_labels[group_key] = new_label
                with c2:
                    new_desc = st.text_area(
                        "Descripción:",
                        value=st.session_state.group_descriptions[group_key],
                        key=f"desc_{selected_file}_{group_key}",
                        max_chars=200,
                        height=100
                    )
                    if new_desc != st.session_state.group_descriptions[group_key]:
                        st.session_state.group_descriptions[group_key] = new_desc

        st.markdown("---")

        # =============================================================================
        # ESPECTROS
        # =============================================================================
        st.markdown("### 📈 Selección desde Espectros")

        if not INTERACTIVE_SELECTION_AVAILABLE:
            st.warning("⚠️ Selección interactiva no disponible. Instala: `pip install streamlit-plotly-events`")

        # Defaults para evitar NameError si no hay plotly_events
        spectra_action = "Marcar para Eliminar"
        spectra_target = None
        spectra_multi = False

        if INTERACTIVE_SELECTION_AVAILABLE:
            st.info("💡 Haz **click** para seleccionar espectros individuales o activa **Lasso/Box** para selección múltiple")

            pending = st.session_state.pending_selections[selected_file]
            if pending:
                st.warning(f"⏳ **{len(pending)} acción(es) pendiente(s)**")
                with st.expander("Ver selecciones pendientes", expanded=False):
                    for i, item in enumerate(pending):
                        action_txt = item["action"]
                        if item["action"] == "Asignar a Grupo":
                            action_txt += f" → {item.get('group', 'none')}"
                        st.write(f"{i+1}. Muestra **{item['idx']}**: {action_txt}")

            # NUEVO: 3 columnas para incluir checkbox Lasso/Box
            colA, colB, colC = st.columns([2, 2, 1])
            with colA:
                spectra_action = st.radio(
                    "Acción:",
                    ["Marcar para Eliminar", "Asignar a Grupo"],
                    key=f"spectra_action_{selected_file}"
                )
            with colB:
                if spectra_action == "Asignar a Grupo":
                    spectra_target = st.selectbox(
                        "Grupo:",
                        ["Set 1", "Set 2", "Set 3", "Set 4"],
                        key=f"spectra_target_{selected_file}"
                    )
            with colC:
                spectra_multi = st.checkbox("Lasso/Box", value=False, key=f"spectra_multi_{selected_file}")

        try:
            fig_spectra = build_spectra_figure_preview(
                df_current,
                removed_indices,
                sample_groups,
                st.session_state.group_labels,
                SAMPLE_GROUPS,
                PIXEL_RE
            )

            if fig_spectra:
                if not INTERACTIVE_SELECTION_AVAILABLE:
                    st.plotly_chart(fig_spectra, use_container_width=True)
                else:
                    # NUEVO: Activar dragmode lasso si está habilitado
                    if spectra_multi:
                        fig_spectra.update_layout(dragmode="lasso")

                    events = plotly_events(
                        fig_spectra,
                        click_event=True,
                        select_event=spectra_multi,  # NUEVO: Condicional según checkbox
                        hover_event=False,
                        override_height=700,
                        key=f"spectra_{selected_file}_v{st.session_state.editor_version[selected_file]}"
                    )

                    if events:
                        event_id = _create_event_id(events)
                        last_id = st.session_state.last_event_id[selected_file].get("spectra", "")

                        if event_id != last_id:
                            st.session_state.last_event_id[selected_file]["spectra"] = event_id

                            # NUEVO: Si es lasso/box, extraer múltiples índices únicos con función específica
                            if spectra_multi:
                                clicked_indices = _extract_row_indices_from_spectra_events(fig_spectra, events)
                            else:
                                # Si es click simple, extraer un solo índice
                                single_idx = _extract_row_index_from_click(fig_spectra, events[0])
                                clicked_indices = [single_idx] if single_idx is not None else []

                            if clicked_indices:
                                pending = st.session_state.pending_selections[selected_file]
                                
                                for clicked_idx in clicked_indices:
                                    new_item = {
                                        "idx": clicked_idx,
                                        "action": spectra_action,
                                        "group": spectra_target if spectra_action == "Asignar a Grupo" else None
                                    }

                                    already = any(
                                        it.get("idx") == new_item["idx"]
                                        and it.get("action") == new_item["action"]
                                        and it.get("group") == new_item["group"]
                                        for it in pending
                                    )

                                    if not already:
                                        pending.append(new_item)

                                # NUEVO: Toast con múltiples muestras
                                st.toast(f"✅ {len(clicked_indices)} muestra(s) agregadas ({len(pending)} pendientes)", icon="📍")
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
            pending = st.session_state.pending_selections[selected_file]

            with b1:
                if st.button(
                    "✅ Aplicar Selecciones",
                    use_container_width=True,
                    type="primary",
                    disabled=(len(pending) == 0),
                    key=f"apply_spectra_{selected_file}"
                ):
                    for item in pending:
                        idx = item["idx"]
                        action = item["action"]

                        if action == "Marcar para Eliminar":
                            if idx in st.session_state.samples_to_remove[selected_file]:
                                st.session_state.samples_to_remove[selected_file].remove(idx)
                            else:
                                st.session_state.samples_to_remove[selected_file].add(idx)
                            st.session_state.sample_groups[selected_file].pop(idx, None)

                        elif action == "Asignar a Grupo":
                            grp = item.get("group")
                            if grp and grp != "none":
                                st.session_state.sample_groups[selected_file][idx] = grp
                                st.session_state.samples_to_remove[selected_file].discard(idx)

                    # NUEVO: Guardar resumen para mostrar después del rerun
                    st.session_state.last_apply_summary[selected_file] = {
                        'count': len(pending),
                        'eliminar': sum(1 for p in pending if p['action'] == 'Marcar para Eliminar'),
                        'grupos': sum(1 for p in pending if p['action'] == 'Asignar a Grupo')
                    }

                    st.session_state.pending_selections[selected_file] = []
                    st.session_state.last_event_id[selected_file]["spectra"] = ""
                    st.session_state.editor_version[selected_file] += 1
                    st.rerun()

            with b2:
                if st.button(
                    "🗑️ Limpiar Pendientes",
                    use_container_width=True,
                    disabled=(len(pending) == 0),
                    key=f"clear_spectra_{selected_file}"
                ):
                    st.session_state.pending_selections[selected_file] = []
                    st.session_state.last_event_id[selected_file]["spectra"] = ""
                    st.rerun()

            with b3:
                if st.button(
                    "🔄 Confirmar Eliminación",
                    use_container_width=True,
                    disabled=(len(removed_indices) == 0),
                    key=f"delete_spectra_{selected_file}"
                ):
                    if removed_indices:
                        old_to_new = {}
                        sorted_indices = sorted(df_current.index)
                        removed_sorted = sorted(removed_indices)
                        new_idx = 0
                        for old_idx in sorted_indices:
                            if old_idx not in removed_sorted:
                                old_to_new[old_idx] = new_idx
                                new_idx += 1

                        df_updated = df_current.drop(index=list(removed_indices)).reset_index(drop=True)

                        new_groups = {}
                        for old_idx, grp in sample_groups.items():
                            if old_idx not in removed_indices:
                                mapped = old_to_new.get(old_idx)
                                if mapped is not None:
                                    new_groups[mapped] = grp

                        st.session_state.processed_data[selected_file] = df_updated
                        st.session_state.samples_to_remove[selected_file] = set()
                        st.session_state.sample_groups[selected_file] = new_groups
                        st.session_state.pending_selections[selected_file] = []
                        st.session_state.last_event_id[selected_file]["spectra"] = ""
                        st.session_state.editor_version[selected_file] += 1
                        st.success(f"✅ {len(removed_indices)} muestras eliminadas")
                        st.rerun()

        st.markdown("---")

        # =============================================================================
        # PARITY
        # =============================================================================
        st.markdown("### 📊 Selección desde Parity")

        columns_result = [c for c in df_current.columns if str(c).startswith("Result ")]
        if not columns_result:
            st.warning("No hay parámetros Result")
        else:
            if not INTERACTIVE_SELECTION_AVAILABLE:
                st.warning("⚠️ Selección interactiva no disponible. Instala: `pip install streamlit-plotly-events`")

            parity_action = "Marcar para Eliminar"
            parity_target = None
            parity_multi = False

            if INTERACTIVE_SELECTION_AVAILABLE:
                st.info("💡 Usa **click** para seleccionar puntos individuales o activa **Lasso/Box** para selección múltiple")

                pending = st.session_state.pending_selections[selected_file]
                if pending:
                    st.warning(f"⏳ **{len(pending)} acción(es) pendiente(s)**")
                    with st.expander("Ver selecciones pendientes", expanded=False):
                        for i, item in enumerate(pending):
                            action_txt = item["action"]
                            if item["action"] == "Asignar a Grupo":
                                action_txt += f" → {item.get('group', 'none')}"
                            st.write(f"{i+1}. Muestra **{item['idx']}**: {action_txt}")

                colA, colB, colC = st.columns([2, 2, 1])
                with colA:
                    parity_action = st.radio(
                        "Acción:",
                        ["Marcar para Eliminar", "Asignar a Grupo"],
                        key=f"parity_action_{selected_file}"
                    )
                with colB:
                    if parity_action == "Asignar a Grupo":
                        parity_target = st.selectbox(
                            "Grupo:",
                            ["Set 1", "Set 2", "Set 3", "Set 4"],
                            key=f"parity_target_{selected_file}"
                        )
                with colC:
                    # MODIFICADO: value=True para activar lasso por defecto
                    parity_multi = st.checkbox("Lasso/Box", value=True, key=f"parity_multi_{selected_file}")

            param_names = [str(c).replace("Result ", "") for c in columns_result]
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
                    SAMPLE_GROUPS
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
                                key=f"parity_{selected_file}_{selected_param}_v{st.session_state.editor_version[selected_file]}"
                            )

                            if events:
                                event_id = _create_event_id(events)
                                last_id = st.session_state.last_event_id[selected_file].get("parity", "")

                                if event_id != last_id:
                                    st.session_state.last_event_id[selected_file]["parity"] = event_id

                                    clicked_indices = _extract_row_indices_from_events(fig_parity, events)
                                    if clicked_indices:
                                        pending = st.session_state.pending_selections[selected_file]
                                        for clicked_idx in clicked_indices:
                                            new_item = {
                                                "idx": clicked_idx,
                                                "action": parity_action,
                                                "group": parity_target if parity_action == "Asignar a Grupo" else None
                                            }

                                            already = any(
                                                it.get("idx") == new_item["idx"]
                                                and it.get("action") == new_item["action"]
                                                and it.get("group") == new_item["group"]
                                                for it in pending
                                            )

                                            if not already:
                                                pending.append(new_item)

                                        # NUEVO: Toast en vez de st.info (sin re-render molesto)
                                        st.toast(f"✅ {len(clicked_indices)} muestra(s) agregadas ({len(pending)} pendientes)", icon="📍")

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
                pending = st.session_state.pending_selections[selected_file]

                with b1:
                    if st.button(
                        "✅ Aplicar Selecciones",
                        use_container_width=True,
                        type="primary",
                        disabled=(len(pending) == 0),
                        key=f"apply_parity_{selected_file}"
                    ):
                        for item in pending:
                            idx = item["idx"]
                            action = item["action"]

                            if action == "Marcar para Eliminar":
                                if idx in st.session_state.samples_to_remove[selected_file]:
                                    st.session_state.samples_to_remove[selected_file].remove(idx)
                                else:
                                    st.session_state.samples_to_remove[selected_file].add(idx)
                                st.session_state.sample_groups[selected_file].pop(idx, None)

                            elif action == "Asignar a Grupo":
                                grp = item.get("group")
                                if grp and grp != "none":
                                    st.session_state.sample_groups[selected_file][idx] = grp
                                    st.session_state.samples_to_remove[selected_file].discard(idx)

                        # NUEVO: Guardar resumen para mostrar después del rerun
                        st.session_state.last_apply_summary[selected_file] = {
                            'count': len(pending),
                            'eliminar': sum(1 for p in pending if p['action'] == 'Marcar para Eliminar'),
                            'grupos': sum(1 for p in pending if p['action'] == 'Asignar a Grupo')
                        }

                        st.session_state.pending_selections[selected_file] = []
                        st.session_state.last_event_id[selected_file]["parity"] = ""
                        st.session_state.editor_version[selected_file] += 1
                        st.rerun()

                with b2:
                    if st.button(
                        "🗑️ Limpiar Pendientes",
                        use_container_width=True,
                        disabled=(len(pending) == 0),
                        key=f"clear_parity_{selected_file}"
                    ):
                        st.session_state.pending_selections[selected_file] = []
                        st.session_state.last_event_id[selected_file]["parity"] = ""
                        st.rerun()

                with b3:
                    if st.button(
                        "🔄 Confirmar Eliminación",
                        use_container_width=True,
                        disabled=(len(removed_indices) == 0),
                        key=f"delete_parity_{selected_file}"
                    ):
                        if removed_indices:
                            old_to_new = {}
                            sorted_indices = sorted(df_current.index)
                            removed_sorted = sorted(removed_indices)
                            new_idx = 0
                            for old_idx in sorted_indices:
                                if old_idx not in removed_sorted:
                                    old_to_new[old_idx] = new_idx
                                    new_idx += 1

                            df_updated = df_current.drop(index=list(removed_indices)).reset_index(drop=True)

                            new_groups = {}
                            for old_idx, grp in sample_groups.items():
                                if old_idx not in removed_indices:
                                    mapped = old_to_new.get(old_idx)
                                    if mapped is not None:
                                        new_groups[mapped] = grp

                            st.session_state.processed_data[selected_file] = df_updated
                            st.session_state.samples_to_remove[selected_file] = set()
                            st.session_state.sample_groups[selected_file] = new_groups
                            st.session_state.pending_selections[selected_file] = []
                            st.session_state.last_event_id[selected_file]["parity"] = ""
                            st.session_state.editor_version[selected_file] += 1
                            st.success(f"✅ {len(removed_indices)} muestras eliminadas")
                            st.rerun()

        st.markdown("---")

        # =============================================================================
        # TABLA INTERACTIVA
        # =============================================================================
        st.subheader("🎯 Selección desde Tabla")
        st.info("✅ Marca para **Eliminar** o asigna un **Grupo** → Presiona **'Actualizar Selección'**")

        df_for_edit = df_current.copy()
        df_for_edit.insert(0, "Grupo", "none")
        df_for_edit.insert(0, "Eliminar", False)

        for idx_ in removed_indices:
            if idx_ in df_for_edit.index:
                df_for_edit.at[idx_, "Eliminar"] = True

        for idx_, grp_ in sample_groups.items():
            if idx_ in df_for_edit.index:
                df_for_edit.at[idx_, "Grupo"] = grp_

        display_cols = ["Eliminar", "Grupo"]
        for col in ["ID", "Date", "Note"]:
            if col in df_for_edit.columns:
                display_cols.append(col)

        result_cols = [c for c in df_for_edit.columns if str(c).startswith("Result ")]
        display_cols.extend(result_cols[:3])

        with st.expander("📋 Tabla de Muestras", expanded=False):
            edited_df = st.data_editor(
                df_for_edit[display_cols],
                column_config={
                    "Eliminar": st.column_config.CheckboxColumn("Eliminar", default=False),
                    "Grupo": st.column_config.SelectboxColumn(
                        "Grupo",
                        options=["none", "Set 1", "Set 2", "Set 3", "Set 4"],
                        default="none"
                    ),
                },
                disabled=[c for c in display_cols if c not in ["Eliminar", "Grupo"]],
                hide_index=False,
                use_container_width=True,
                key=f"editor_{selected_file}_v{st.session_state.editor_version[selected_file]}"
            )

            # BOTONES DEBAJO DE TABLA
            st.markdown("---")
            c1, c2, c3, c4 = st.columns(4)

            with c1:
                if st.button("🔄 Actualizar Selección", use_container_width=True, type="primary"):
                    new_removed = set()
                    new_groups = {}
                    for idx_ in edited_df.index:
                        if bool(edited_df.at[idx_, "Eliminar"]):
                            new_removed.add(idx_)
                        grp_val = edited_df.at[idx_, "Grupo"]
                        if grp_val != "none":
                            new_groups[idx_] = grp_val
                    st.session_state.samples_to_remove[selected_file] = new_removed
                    st.session_state.sample_groups[selected_file] = new_groups
                    st.session_state.editor_version[selected_file] += 1
                    st.success(f"✅ Actualizado: {len(new_removed)} eliminar, {len(new_groups)} agrupadas")
                    st.rerun()

            with c2:
                if st.button("🗑️ Confirmar Eliminación", use_container_width=True, disabled=(len(removed_indices) == 0)):
                    if removed_indices:
                        old_to_new = {}
                        sorted_indices = sorted(df_current.index)
                        removed_sorted = sorted(removed_indices)
                        new_idx = 0
                        for old_idx in sorted_indices:
                            if old_idx not in removed_sorted:
                                old_to_new[old_idx] = new_idx
                                new_idx += 1
                        df_updated = df_current.drop(index=list(removed_indices)).reset_index(drop=True)
                        new_groups = {}
                        for old_idx, grp in sample_groups.items():
                            if old_idx not in removed_indices:
                                mapped = old_to_new.get(old_idx)
                                if mapped is not None:
                                    new_groups[mapped] = grp
                        st.session_state.processed_data[selected_file] = df_updated
                        st.session_state.samples_to_remove[selected_file] = set()
                        st.session_state.sample_groups[selected_file] = new_groups
                        st.session_state.pending_selections[selected_file] = []
                        st.session_state.last_event_id[selected_file]["spectra"] = ""
                        st.session_state.last_event_id[selected_file]["parity"] = ""
                        st.session_state.editor_version[selected_file] += 1
                        st.success(f"✅ {len(removed_indices)} muestras eliminadas")
                        st.rerun()

            with c3:
                if st.button(
                    "↩️ Limpiar Todo",
                    use_container_width=True,
                    disabled=(len(removed_indices) == 0 and len(sample_groups) == 0)
                ):
                    st.session_state.samples_to_remove[selected_file] = set()
                    st.session_state.sample_groups[selected_file] = {}
                    st.session_state.pending_selections[selected_file] = []
                    st.session_state.last_event_id[selected_file]["spectra"] = ""
                    st.session_state.last_event_id[selected_file]["parity"] = ""
                    st.session_state.editor_version[selected_file] += 1
                    st.rerun()

            with c4:
                if st.button("🔄 Limpiar Grupos", use_container_width=True, disabled=(len(sample_groups) == 0)):
                    st.session_state.sample_groups[selected_file] = {}
                    st.session_state.editor_version[selected_file] += 1
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
                    label = st.session_state.group_labels.get(group_key, group_key)
                    emoji = SAMPLE_GROUPS[group_key]["emoji"]
                    summary_parts.append(f"**{count} en {emoji} {label}**")
            st.info("📊 " + " | ".join(summary_parts))


# =============================================================================
# FASE 3: GENERACIÓN DE REPORTES
# =============================================================================
if st.session_state.processed_data:
    st.markdown("---")
    st.markdown("### 📥 FASE 3: Generar Reportes Finales")

    st.subheader("📋 Resumen de Archivos")
    summary_data = []
    for fname, df in st.session_state.processed_data.items():
        sample_groups_file = st.session_state.sample_groups.get(fname, {})
        grouped_count = sum(1 for g in sample_groups_file.values() if g != "none")
        summary_data.append({
            "Archivo": fname,
            "Muestras": len(df),
            "Agrupadas": grouped_count,
            "Parámetros": len([c for c in df.columns if str(c).startswith("Result ")])
        })
    st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)

    st.markdown("---")
    if st.button("📥 Generar Informes HTML", type="primary", use_container_width=True):
        results: List[ReportResult] = []
        progress_bar = st.progress(0.0)

        for idx, (file_name, df) in enumerate(st.session_state.processed_data.items(), start=1):
            try:
                if len(df) == 0:
                    st.warning(f"⚠️ {file_name}: No hay datos")
                    continue

                sample_groups_file = st.session_state.sample_groups.get(file_name, {})

                html = generate_html_report(
                    df,
                    file_name,
                    sample_groups_file,
                    st.session_state.group_labels,
                    st.session_state.group_descriptions,
                    SAMPLE_GROUPS,
                    PIXEL_RE
                )

                results.append(ReportResult(name=file_name, html=html, csv=df))
                st.success(f"✅ {file_name}")

            except Exception as e:
                st.error(f"❌ {file_name}: {e}")

            progress_bar.progress(idx / float(len(st.session_state.processed_data)))

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
                    use_container_width=True
                )
                st.markdown("---")

            for r in results:
                st.markdown(f"**{r.name}**")
                st.download_button(
                    "💾 Descargar HTML",
                    data=r.html,
                    file_name=f"{r.name}.html",
                    mime="text/html",
                    key=f"dl_{r.name}"
                )
                st.markdown("---")