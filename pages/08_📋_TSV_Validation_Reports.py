"""
COREF - TSV Validation Reports
==============================
VERSIÓN MODULAR: Código de generación separado en módulos
"""

from __future__ import annotations

import re
import zipfile
from io import BytesIO
from typing import Dict, List

import pandas as pd
import streamlit as st
from dateutil import parser as date_parser

from auth import check_password
from buchi_streamlit_theme import apply_buchi_styles
from core.tsv_plotting import plot_comparison_preview, build_spectra_figure_preview
from core.tsv_report_generator import generate_html_report, ReportResult


# =============================================================================
# STREAMLIT PAGE SETUP
# =============================================================================
apply_buchi_styles()

if not check_password():
    st.stop()

st.title("📋 TSV Validation Reports")
st.markdown("## Generación de informes de validación NIR (TSV) con previsualización y selección de muestras.")

# Información de uso
with st.expander("ℹ️ Instrucciones de Uso"):
    st.markdown("""
    ### Cómo usar TSV Validation Reports:
    
    **1. Cargar Archivos TSV:**
    - Sube uno o varios archivos TSV (export/journal de NIR-Online)
    - Los archivos pueden estar en formato estándar o journal
    - Soporta carga múltiple para procesamiento batch
    
    **2. Filtrar por Fechas (Opcional):**
    - Define rango de fechas para filtrar las mediciones
    - Útil para analizar períodos específicos de validación
    - Deja vacío para procesar todas las fechas
    
    **3. Procesamiento Automático:**
    - La herramienta limpia y reorganiza los datos (tipo Node-RED)
    - Elimina filas con todos los resultados en cero
    - Reorganiza columnas: Reference, Result, Residuum por parámetro
    - Convierte formatos de fecha automáticamente
    
    **4. Previsualización y Selección:**
    - Personaliza nombres de grupos para tu análisis
    - Marca muestras para eliminar (checkbox "Eliminar")
    - Asigna muestras a grupos (Grupo 1-4) para seguimiento visual
    - Los grupos aparecen con símbolos diferentes en los gráficos:
        - 🟩 Cuadrado verde
        - 🔺 Triángulo rojo
        - ⭐ Estrella dorada
        - ➕ Cruz gris
        - ❌ X roja (eliminar)
    - Revisa estadísticas y outliers visualmente
    - Elimina muestras problemáticas antes de generar el reporte
    
    **5. Generación de Reportes:**
    - Presiona **"Generar Informe Final"**
    - Los reportes incluyen los grupos marcados con sus etiquetas personalizadas
    - Genera informes HTML interactivos con:
        - Resumen estadístico (R², RMSE, BIAS, N)
        - Gráficos por parámetro (Parity, Residuum vs N, Histograma)
        - Plot de espectros NIR (columnas #1..#n)
        - Sidebar de navegación estilo BUCHI
        - Leyenda de grupos personalizados
    
    **6. Descargar Resultados:**
    - HTML: Reporte completo interactivo con Plotly
    - ZIP: Descarga todos los reportes si procesas múltiples archivos
    
    **Características:**
    - ✅ Gráficos interactivos con Plotly (zoom, pan, hover)
    - ✅ Selección mediante tabla interactiva
    - ✅ Agrupación de muestras con símbolos visuales
    - ✅ Etiquetas personalizables para grupos
    - ✅ Grupos incluidos en reportes HTML finales
    - ✅ Previsualización antes de generar reporte
    - ✅ Diseño corporativo BUCHI con sidebar de navegación
    - ✅ Soporte para múltiples parámetros simultáneos
    - ✅ Vista de espectros completos NIR
    """)


# =============================================================================
# SAMPLE GROUPS CONFIGURATION
# =============================================================================
SAMPLE_GROUPS = {
    'none': {'symbol': 'circle', 'color': 'blue', 'size': 8, 'emoji': '🔵'},
    'Set 1': {'symbol': 'square', 'color': 'green', 'size': 10, 'emoji': '🟩'},
    'Set 2': {'symbol': 'triangle-up', 'color': 'red', 'size': 10, 'emoji': '🔺'},
    'Set 3': {'symbol': 'star', 'color': 'gold', 'size': 12, 'emoji': '⭐'},
    'Set 4': {'symbol': 'cross', 'color': 'grey', 'size': 10, 'emoji': '➕'},
}


# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = {}
if 'samples_to_remove' not in st.session_state:
    st.session_state.samples_to_remove = {}
if 'sample_groups' not in st.session_state:
    st.session_state.sample_groups = {}
if 'group_labels' not in st.session_state:
    st.session_state.group_labels = {
        'Set 1': 'Set 1',
        'Set 2': 'Set 2',
        'Set 3': 'Set 3',
        'Set 4': 'Set 4'
    }


# =============================================================================
# DATA CLEANING / NODE-RED LOGIC
# =============================================================================

PIXEL_RE = re.compile(r"^#\d+$")


def _is_pixel_col(col: str) -> bool:
    return bool(PIXEL_RE.fullmatch(str(col)))


def filter_relevant_data(data: List[Dict]) -> List[Dict]:
    """Mantiene metadata hasta #X1 + columnas espectrales #1..#n"""
    if not data:
        return []

    all_columns = list(data[0].keys())
    stop_column = "#X1"

    base_cols: List[str] = []
    for col in all_columns:
        if col == stop_column:
            break
        base_cols.append(col)

    pixel_cols = [c for c in all_columns if _is_pixel_col(c)]
    pixel_cols = sorted(pixel_cols, key=lambda s: int(str(s)[1:]))

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
    """Elimina filas donde Result esté vacío o todos los valores sean 0"""
    out: List[Dict] = []
    for row in data:
        if "Result" not in row or row["Result"] is None:
            continue

        result_values = str(row["Result"]).split(";")
        all_zeroes = True
        for v in result_values:
            v = v.strip().replace(",", ".")
            if v in ("", "-", "NA", "NaN"):
                all_zeroes = False
                break
            try:
                if float(v) != 0.0:
                    all_zeroes = False
                    break
            except Exception:
                all_zeroes = False
                break

        if not all_zeroes:
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
        parameter_cols = all_cols[ref_i + 1 : begin_i]

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
            if ref_val is not None and ref_val != "":
                ref_val = str(ref_val).replace(",", ".")
                try:
                    ref_val_f = float(ref_val) if ref_val not in ("-", "NA") else None
                except Exception:
                    ref_val_f = None
            else:
                ref_val_f = None

            res_val_f = None
            if idx < len(result_values):
                rv = result_values[idx].replace(",", ".")
                try:
                    res_val_f = float(rv) if rv not in ("", "-", "NA") else None
                except Exception:
                    res_val_f = None

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
    fmts = ["%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m-%d-%Y"]

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
    """Pipeline completo de limpieza de TSV"""
    df_raw = pd.read_csv(uploaded_file, delimiter="\t", keep_default_na=False)
    data = df_raw.to_dict("records")

    data = filter_relevant_data(data)
    data = delete_zero_rows(data)
    data = reorganize_results_and_reference(data)

    df = pd.DataFrame(data)

    if not df.empty:
        pixel_cols = [c for c in df.columns if _is_pixel_col(c)]
        if pixel_cols:
            df[pixel_cols] = df[pixel_cols].replace(",", ".", regex=True)
            df[pixel_cols] = df[pixel_cols].apply(pd.to_numeric, errors="coerce")

    if "Date" in df.columns:
        df["Date"] = df["Date"].apply(try_parse_date)

    return df


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
    st.info("Define el rango de fechas ANTES de procesar. Esto filtrará los datos desde el inicio.")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        start_date = st.date_input(
            "Fecha de inicio",
            value=None,
            help="Dejar vacío para incluir desde el inicio"
        )
    
    with col2:
        end_date = st.date_input(
            "Fecha de fin",
            value=None,
            help="Dejar vacío para incluir hasta el final"
        )
    
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
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        st.session_state.processed_data = {}
        st.session_state.samples_to_remove = {}
        st.session_state.sample_groups = {}

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
                            st.info(f"📊 {file_name}: {rows_before} → {rows_after} muestras después del filtro")
                        
                        if rows_after == 0:
                            st.warning(f"⚠️ {file_name}: No hay datos en el rango de fechas. Se omite.")
                            continue
                else:
                    if start_date or end_date:
                        st.warning(f"⚠️ {file_name}: No tiene columna 'Date', se ignora el filtro de fechas")
                
                df_filtered = df_filtered.reset_index(drop=True)
                
                st.session_state.processed_data[file_name] = df_filtered
                st.session_state.samples_to_remove[file_name] = set()
                st.session_state.sample_groups[file_name] = {}
                
                st.success(f"✅ {file_name} procesado ({len(df_filtered)} muestras)")

            except Exception as e:
                st.error(f"❌ Error: {file_name}: {e}")
                import traceback
                st.code(traceback.format_exc())

            progress_bar.progress(idx / len(uploaded_files))

        status_text.text("✅ Procesamiento completado")


# =============================================================================
# FASE 2: PREVISUALIZACIÓN Y SELECCIÓN
# =============================================================================

if st.session_state.processed_data:
    st.markdown("---")
    st.markdown("### 🔍 FASE 2: Previsualización y Selección de Muestras")
    
    st.info("Los datos mostrados aquí ya incluyen el filtro de fechas aplicado en la Fase 1.")
    
    selected_file = st.selectbox(
        "Archivo:",
        options=list(st.session_state.processed_data.keys())
    )
    
    if selected_file:
        df_current = st.session_state.processed_data[selected_file]
        
        removed_indices = st.session_state.samples_to_remove.get(selected_file, set())
        sample_groups = st.session_state.sample_groups.get(selected_file, {})
        
        # Limpiar índices inválidos
        valid_removed = {idx for idx in removed_indices if idx in df_current.index}
        valid_groups = {idx: grp for idx, grp in sample_groups.items() if idx in df_current.index}
        
        if len(valid_removed) != len(removed_indices):
            st.session_state.samples_to_remove[selected_file] = valid_removed
        if len(valid_groups) != len(sample_groups):
            st.session_state.sample_groups[selected_file] = valid_groups
        
        removed_indices = valid_removed
        sample_groups = valid_groups
        
        # Estadísticas
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📊 Total", len(df_current))
        with col2:
            st.metric("🗑️ Eliminar", len(removed_indices))
        with col3:
            grouped_count = sum(1 for g in sample_groups.values() if g != 'none')
            st.metric("🏷️ Agrupadas", grouped_count)
        with col4:
            st.metric("✅ Finales", len(df_current) - len(removed_indices))
        
        st.markdown("---")
        
        # LEYENDA DE GRUPOS PERSONALIZABLE
        st.subheader("🏷️ Leyenda de Grupos")
        st.info("Personaliza los nombres de los grupos para tu análisis (ej: 'Outliers', 'Pre-ajuste', 'Validados', etc.)")

        legend_cols = st.columns(4)

        group_keys = ['Set 1', 'Set 2', 'Set 3', 'Set 4']
        for idx, group_key in enumerate(group_keys):
            with legend_cols[idx]:
                group_config = SAMPLE_GROUPS[group_key]
                
                st.markdown(f"**{group_config['emoji']} ({group_config['symbol']})**")
                
                new_label = st.text_input(
                    "Etiqueta:",
                    value=st.session_state.group_labels[group_key],
                    key=f"label_{group_key}",
                    max_chars=30,
                    help=f"Nombre personalizado para {group_key}"
                )
                
                if new_label != st.session_state.group_labels[group_key]:
                    st.session_state.group_labels[group_key] = new_label

        st.markdown("**Etiquetas actuales:**")
        labels_summary = " | ".join([
            f"{SAMPLE_GROUPS[k]['emoji']} **{st.session_state.group_labels[k]}**" 
            for k in group_keys
        ])
        st.markdown(labels_summary)
        
        st.markdown("---")
        
        # ESPECTROS
        with st.expander("📈 Vista de Espectros", expanded=True):
            try:
                fig_spectra = build_spectra_figure_preview(
                    df_current, removed_indices, sample_groups, 
                    st.session_state.group_labels, SAMPLE_GROUPS, PIXEL_RE
                )
                if fig_spectra:
                    st.plotly_chart(fig_spectra, use_container_width=True)
                else:
                    st.warning("No hay datos espectrales para mostrar")
            except Exception as e:
                st.error(f"Error generando espectros: {e}")
                import traceback
                st.code(traceback.format_exc())
        
        # GRÁFICOS POR PARÁMETRO
        with st.expander("📊 Gráficos por Parámetro", expanded=True):
            columns_result = [c for c in df_current.columns if str(c).startswith("Result ")]
            
            if columns_result:
                param_names = [str(c).replace("Result ", "") for c in columns_result]
                selected_param = st.selectbox("Parámetro:", param_names)
                
                result_col = f"Result {selected_param}"
                reference_col = f"Reference {selected_param}"
                residuum_col = f"Residuum {selected_param}"
                
                try:
                    plots = plot_comparison_preview(
                        df_current, result_col, reference_col, residuum_col,
                        removed_indices, sample_groups, st.session_state.group_labels, SAMPLE_GROUPS
                    )
                    
                    if plots:
                        fig_parity, fig_res, fig_hist, r2, rmse, bias, n = plots
                        
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("R²", f"{r2:.3f}")
                        col2.metric("RMSE", f"{rmse:.3f}")
                        col3.metric("BIAS", f"{bias:.3f}")
                        col4.metric("N", n)
                        
                        tab1, tab2, tab3 = st.tabs(["Parity", "Residuum", "Histogram"])
                        
                        with tab1:
                            st.plotly_chart(fig_parity, use_container_width=True)
                        with tab2:
                            st.plotly_chart(fig_res, use_container_width=True)
                        with tab3:
                            st.plotly_chart(fig_hist, use_container_width=True)
                    else:
                        st.error(f"No se pudieron generar gráficos para {selected_param}.")
                except Exception as e:
                    st.error(f"Error generando gráficos: {e}")
                    import traceback
                    st.code(traceback.format_exc())
            else:
                st.warning("No hay parámetros Result en el archivo")
        
        st.markdown("---")
        
        # TABLA INTERACTIVA
        st.subheader("🎯 Selección de Muestras")
        st.info("✅ Marca para **Eliminar** o asigna un **Grupo** → Presiona **'Actualizar Selección'** → Revisa los gráficos")
        
        df_for_edit = df_current.copy()
        df_for_edit.insert(0, 'Grupo', 'none')
        df_for_edit.insert(0, 'Eliminar', False)
        
        for idx in removed_indices:
            if idx in df_for_edit.index:
                df_for_edit.at[idx, 'Eliminar'] = True
        
        for idx, group in sample_groups.items():
            if idx in df_for_edit.index:
                df_for_edit.at[idx, 'Grupo'] = group
        
        display_cols = ['Eliminar', 'Grupo']
        for col in ['ID', 'Date', 'Note']:
            if col in df_for_edit.columns:
                display_cols.append(col)
        
        result_cols = [c for c in df_for_edit.columns if str(c).startswith("Result ")]
        display_cols.extend(result_cols[:3])
        
        edited_df = st.data_editor(
            df_for_edit[display_cols],
            column_config={
                "Eliminar": st.column_config.CheckboxColumn(
                    "Eliminar",
                    help="Marcar para eliminar esta muestra",
                    default=False,
                ),
                "Grupo": st.column_config.SelectboxColumn(
                    "Grupo",
                    help="Asignar muestra a un grupo de seguimiento",
                    options=['none', 'Set 1', 'Set 2', 'Set 3', 'Set 4'],
                    default='none',
                )
            },
            disabled=[c for c in display_cols if c not in ['Eliminar', 'Grupo']],
            hide_index=False,
            use_container_width=True,
            key=f"editor_{selected_file}"
        )
        
        st.markdown("---")
        
        # BOTONES DE ACCIÓN
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🔄 Actualizar Selección", use_container_width=True):
                new_removed = set(edited_df[edited_df['Eliminar']].index.tolist())
                new_groups = {}
                for idx in edited_df.index:
                    group_val = edited_df.at[idx, 'Grupo']
                    if group_val != 'none':
                        new_groups[idx] = group_val
                
                st.session_state.samples_to_remove[selected_file] = new_removed
                st.session_state.sample_groups[selected_file] = new_groups
                
                st.success(f"✅ Actualizado: {len(new_removed)} para eliminar, {len(new_groups)} agrupadas")
                st.rerun()
        
        with col2:
            if st.button("🗑️ Confirmar Eliminación", type="primary", use_container_width=True, 
                        disabled=(len(removed_indices) == 0)):
                if removed_indices:
                    df_updated = df_current.drop(index=list(removed_indices)).reset_index(drop=True)
                    st.session_state.processed_data[selected_file] = df_updated
                    st.session_state.samples_to_remove[selected_file] = set()
                    new_groups = {idx: grp for idx, grp in sample_groups.items() if idx not in removed_indices}
                    st.session_state.sample_groups[selected_file] = new_groups
                    st.success(f"✅ {len(removed_indices)} muestras eliminadas")
                    st.rerun()
        
        with col3:
            if st.button("↩️ Limpiar Todo", use_container_width=True,
                        disabled=(len(removed_indices) == 0 and len(sample_groups) == 0)):
                st.session_state.samples_to_remove[selected_file] = set()
                st.session_state.sample_groups[selected_file] = {}
                st.rerun()
        
        with col4:
            if st.button("🔄 Limpiar Grupos", use_container_width=True,
                        disabled=(len(sample_groups) == 0)):
                st.session_state.sample_groups[selected_file] = {}
                st.rerun()
        
        # RESUMEN
        if removed_indices or sample_groups:
            summary_parts = []
            if removed_indices:
                summary_parts.append(f"**{len(removed_indices)} marcadas para eliminar (X roja)**")
            if sample_groups:
                group_counts = {}
                for g in sample_groups.values():
                    group_counts[g] = group_counts.get(g, 0) + 1
                for group_key, count in group_counts.items():
                    label = st.session_state.group_labels.get(group_key, group_key)
                    emoji = SAMPLE_GROUPS[group_key]['emoji']
                    summary_parts.append(f"**{count} en {emoji} {label}**")
            
            st.info("📊 " + " | ".join(summary_parts))


# =============================================================================
# FASE 3: GENERACIÓN DE REPORTES
# =============================================================================

if st.session_state.processed_data:
    st.markdown("---")
    st.markdown("### 📥 FASE 3: Generar Reportes Finales")
    
    st.info("Los reportes incluirán los grupos personalizados que hayas configurado.")
    
    st.subheader("📋 Resumen de Archivos")
    summary_data = []
    for fname, df in st.session_state.processed_data.items():
        sample_groups_file = st.session_state.sample_groups.get(fname, {})
        grouped_count = sum(1 for g in sample_groups_file.values() if g != 'none')
        
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
        progress_bar = st.progress(0)
        
        for idx, (file_name, df) in enumerate(st.session_state.processed_data.items(), start=1):
            try:
                if len(df) == 0:
                    st.warning(f"⚠️ {file_name}: No hay datos para generar reporte")
                    continue
                
                sample_groups_file = st.session_state.sample_groups.get(file_name, {})
                html = generate_html_report(
                    df, file_name, sample_groups_file, 
                    st.session_state.group_labels, SAMPLE_GROUPS, PIXEL_RE
                )
                results.append(ReportResult(name=file_name, html=html, csv=df))
                st.success(f"✅ {file_name} ({len(df)} muestras)")
            except Exception as e:
                st.error(f"❌ {file_name}: {e}")
                import traceback
                st.code(traceback.format_exc())
            
            progress_bar.progress(idx / len(st.session_state.processed_data))
        
        if results:
            st.markdown("---")
            
            if len(results) > 1:
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    for r in results:
                        zf.writestr(f"{r.name}.html", r.html)
                
                st.download_button(
                    "📦 Descargar todos los reportes (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name="tsv_validation_reports.zip",
                    mime="application/zip",
                    use_container_width=True
                )
                st.markdown("---")
            
            for r in results:
                st.markdown(f"**{r.name}**")
                st.download_button(
                    "💾 Descargar Informe HTML",
                    data=r.html,
                    file_name=f"{r.name}.html",
                    mime="text/html",
                    key=f"dl_{r.name}"
                )
                st.markdown("---")