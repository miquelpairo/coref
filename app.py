import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import json
from datetime import datetime
from pathlib import Path

st.set_page_config(page_title="Baseline Adjustment Tool", layout="wide")

# Inicializar session_state
if 'step' not in st.session_state:
    st.session_state.step = -1
if 'wstd_data' not in st.session_state:
    st.session_state.wstd_data = None
if 'kit_data' not in st.session_state:
    st.session_state.kit_data = None
if 'baseline_data' not in st.session_state:
    st.session_state.baseline_data = None
if 'backup_done' not in st.session_state:
    st.session_state.backup_done = False
if 'client_data' not in st.session_state:
    st.session_state.client_data = None
if 'selected_ids' not in st.session_state:
    st.session_state.selected_ids = []

# Header
st.title("🔧 Baseline Adjustment Tool")
st.markdown("### Asistente para ajuste de línea base en espectrómetros NIR")

# Sidebar con progreso
with st.sidebar:
    st.markdown("## 📊 Progreso")
    steps = [
        "Datos del cliente",
        "Backup de archivos",
        "Diagnóstico WSTD",
        "Medir Standard Kit",
        "Calcular corrección",
        "Cargar baseline",
        "Exportar e Informe"
    ]
    for i, step_name in enumerate(steps):
        step_idx = i - 1  # Ajustar porque comenzamos en -1
        if step_idx < st.session_state.step:
            st.markdown(f"✅ **{i}. {step_name}**")
        elif step_idx == st.session_state.step:
            st.markdown(f"⏳ **{i}. {step_name}**")
        else:
            st.markdown(f"○ {i}. {step_name}")

    st.markdown("---")
    if st.session_state.step > -1:
        if st.button("⬅️ Volver al paso anterior"):
            st.session_state.step = max(-1, st.session_state.step - 1)
            st.rerun()

# ============================================================================
# PASO -1: DATOS DEL CLIENTE
# ============================================================================
if st.session_state.step == -1:
    st.markdown("## 📍 PASO 0: Información del Cliente")
    st.info("""
    Por favor, completa los siguientes datos antes de comenzar el proceso de ajuste.
    Esta información se incluirá en el informe final.
    """)

    with st.form("client_form"):
        col1, col2 = st.columns(2)
        with col1:
            client_name = st.text_input("Nombre del Cliente *", placeholder="Ej: Agropecuaria San José")
            contact_person = st.text_input("Persona de Contacto", placeholder="Ej: Juan Pérez")
            contact_email = st.text_input("Email de Contacto", placeholder="ejemplo@empresa.com")
        with col2:
            sensor_sn = st.text_input("Número de Serie del Sensor *", placeholder="Ej: NIR-2024-001")
            equipment_model = st.text_input("Modelo del Equipo", placeholder="Ej: SX-Suite 557")
            location = st.text_input("Ubicación", placeholder="Ej: Planta Barcelona")
        notes = st.text_area("Notas adicionales", placeholder="Información adicional relevante...")

        submitted = st.form_submit_button("✅ Guardar y Continuar", type="primary", use_container_width=True)
        if submitted:
            if not client_name or not sensor_sn:
                st.error("❌ Los campos marcados con * son obligatorios")
            else:
                st.session_state.client_data = {
                    'client_name': client_name,
                    'contact_person': contact_person,
                    'contact_email': contact_email,
                    'sensor_sn': sensor_sn,
                    'equipment_model': equipment_model,
                    'location': location,
                    'notes': notes,
                    'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                st.session_state.step = 0
                st.rerun()

    st.markdown("---")
    if st.button("⏭️ Omitir (no recomendado)", use_container_width=True):
        st.session_state.client_data = {
            'client_name': 'No especificado',
            'contact_person': '',
            'contact_email': '',
            'sensor_sn': 'No especificado',
            'equipment_model': '',
            'location': '',
            'notes': '',
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        st.session_state.step = 0
        st.rerun()

# ============================================================================
# PASO 0: ADVERTENCIA DE BACKUP
# ============================================================================
if st.session_state.step == 0:
    st.markdown("## 📍 PASO 0: Advertencia Importante")
    st.warning("""
    ### ⚠️ ATENCIÓN: Backup de Archivos Baseline

    **Antes de continuar con este proceso, es CRÍTICO que realices una copia de seguridad manual 
    de los archivos baseline actuales.**

    Este procedimiento modificará los archivos de línea base del equipo NIR. Si algo sale mal, 
    necesitarás los archivos originales para restaurar la configuración.
    """)

    st.markdown("### 📁 Ubicaciones de los archivos baseline:")
    col1, col2 = st.columns(2)
    with col1:
        st.code("C:\\\\ProgramData\\\\NIR-Online\\\\SX-Suite", language="text")
        st.caption("📄 Archivos .ref (SX Suite ≤ 531)")
    with col2:
        st.code("C:\\\\ProgramData\\\\NIR-Online\\\\SX-Suite\\\\Data\\\\Reference", language="text")
        st.caption("📄 Archivos .csv (SX Suite ≥ 557)")

    st.markdown("---")
    st.info("""
    ### 📋 Procedimiento recomendado para el backup:
    1. Copia toda la carpeta correspondiente a tu versión de software
    2. Pégala en una ubicación segura (Desktop, carpeta de backups, etc.)
    3. Renombra la carpeta con la fecha actual (ej: `SX-Suite_Backup_2025-01-15`)
    4. Verifica que la copia se realizó correctamente
    """)

    st.markdown("---")
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("✅ Ya realicé el backup, continuar", type="primary", use_container_width=True):
            st.session_state.backup_done = True
            st.session_state.step = 1
            st.rerun()
    with col_btn2:
        if st.button("⏭️ Omitir este paso (no recomendado)", use_container_width=True):
            st.session_state.backup_done = False
            st.session_state.step = 1
            st.rerun()

# ============================================================================
# PASO 1: DIAGNÓSTICO INICIAL CON WSTD
# ============================================================================
elif st.session_state.step == 1:
    st.markdown("## 📍 PASO 1 DE 5: Diagnóstico Inicial")
    st.markdown("""
    ### 📋 Instrucciones para el técnico:

    1. **Prepara el White Standard** (referencia blanca del kit)
    2. En el equipo NIR, **NO tomes línea base** (medir como muestra normal)
    3. **Mide el White Standard con la lámpara de referencia** (la que está en uso actualmente)
       - 📝 ID: `WSTD`
       - 📝 Note: nombre de tu lámpara de referencia (ej: "L1", "LampOld", etc.)
    4. **Cambia a la lámpara nueva** en el equipo
    5. **Mide el White Standard con la lámpara nueva**
       - 📝 ID: `WSTD`
       - 📝 Note: nombre de tu lámpara nueva (ej: "L2", "LampNew", etc.)
    6. **Exporta el archivo TSV** con ambas mediciones

    ℹ️ **¿Por qué este paso?** Si el sistema está bien calibrado, las mediciones del White Standard 
    sin línea base deberían estar muy cercanas a 0 en todo el espectro. Este diagnóstico nos muestra 
    el estado actual del sistema antes del ajuste.
    """)

    st.markdown("---")
    wstd_file = st.file_uploader("📁 Sube el archivo TSV con las mediciones de WSTD", type="tsv", key="wstd_upload")

    col_skip1, col_skip2 = st.columns([3, 1])
    with col_skip2:
        if st.button("⏭️ Omitir paso", key="skip_step1"):
            st.session_state.step = 2
            st.rerun()

    if wstd_file:
        try:
            content = wstd_file.read().decode("utf-8").replace(",", ".")
            df = pd.read_csv(io.StringIO(content), sep="\t")

            df_wstd = df[df["ID"].str.upper() == "WSTD"]
            if len(df_wstd) == 0:
                st.error("❌ No se encontraron mediciones con ID = 'WSTD' en el archivo.")
                st.info("Verifica que hayas etiquetado correctamente las mediciones del White Standard.")
            else:
                spectral_cols = [col for col in df.columns if col.startswith("#") and col[1:].isdigit()]
                df_wstd[spectral_cols] = df_wstd[spectral_cols].apply(pd.to_numeric, errors="coerce")

                lamps = [lamp for lamp in df_wstd["Note"].unique() if pd.notna(lamp)]
                st.success("✅ Archivo cargado correctamente")
                st.write(f"**Mediciones WSTD encontradas:** {len(df_wstd)}")
                st.write(f"**Lámparas detectadas:** {', '.join(lamps)}")
                st.write(f"**Canales espectrales:** {len(spectral_cols)}")

                df_wstd_grouped = df_wstd.groupby("Note")[spectral_cols].mean()

                st.markdown("### 📊 Diagnóstico Visual")
                fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
                for lamp in df_wstd_grouped.index:
                    spectrum = df_wstd_grouped.loc[lamp].values
                    ax1.plot(range(1, len(spectral_cols) + 1), spectrum, label=lamp, linewidth=2)
                ax1.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
                ax1.set_title("Espectros del White Standard (sin línea base)", fontsize=12, fontweight='bold')
                ax1.set_xlabel("Canal espectral")
                ax1.set_ylabel("Intensidad")
                ax1.legend()
                ax1.grid(True, alpha=0.3)

                if len(df_wstd_grouped) == 2:
                    lamp1, lamp2 = df_wstd_grouped.index[0], df_wstd_grouped.index[1]
                    diff = df_wstd_grouped.loc[lamp1].values - df_wstd_grouped.loc[lamp2].values
                    ax2.plot(range(1, len(spectral_cols) + 1), diff, linewidth=2)
                    ax2.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
                    ax2.set_title(f"Diferencia espectral: {lamp1} - {lamp2}", fontsize=12, fontweight='bold')
                    ax2.set_xlabel("Canal espectral")
                    ax2.set_ylabel("Diferencia")
                    ax2.grid(True, alpha=0.3)
                else:
                    ax2.text(0.5, 0.5, 'Se necesitan 2 lámparas para mostrar diferencias',
                             ha='center', va='center', transform=ax2.transAxes)
                    ax2.set_xlim(0, 1)
                    ax2.set_ylim(0, 1)

                plt.tight_layout()
                st.pyplot(fig)

                st.markdown("### 📈 Métricas de Diagnóstico")
                cols = st.columns(len(df_wstd_grouped))
                for i, lamp in enumerate(df_wstd_grouped.index):
                    spectrum = df_wstd_grouped.loc[lamp].values
                    with cols[i]:
                        st.markdown(f"**{lamp}**")
                        max_val = np.max(np.abs(spectrum))
                        mean_val = np.mean(np.abs(spectrum))
                        std_val = np.std(spectrum)
                        st.metric("Desv. máxima", f"{max_val:.4f}")
                        st.metric("Desv. media", f"{mean_val:.4f}")
                        st.metric("Desv. estándar", f"{std_val:.4f}")
                        if max_val < 0.01:
                            st.success("🟢 Bien ajustado")
                        elif max_val < 0.05:
                            st.warning("🟡 Desviación moderada")
                        else:
                            st.error("🔴 Requiere ajuste")

                st.session_state.wstd_data = {
                    'df': df_wstd,
                    'grouped': df_wstd_grouped,
                    'spectral_cols': spectral_cols,
                    'lamps': lamps
                }

                st.markdown("---")
                if st.button("➡️ Continuar al Paso 2", type="primary", use_container_width=True):
                    st.session_state.step = 2
                    st.rerun()

        except Exception as e:
            st.error(f"❌ Error al procesar el archivo: {str(e)}")

# ============================================================================
# PASO 2: MEDIR STANDARD KIT
# ============================================================================
elif st.session_state.step == 2:
    st.markdown("## 📍 PASO 2 DE 5: Medición del Standard Kit")
    st.markdown("""
    ### 📋 Instrucciones para el técnico:

    1. **Toma línea base con la lámpara NUEVA** usando el White Reference
    2. **Mide todas las muestras del Standard Kit con la lámpara de REFERENCIA**
       - 📝 Usa IDs consistentes para cada muestra (ej: "Sample01", "Sample02", "Soja_A", etc.)
       - 📝 Note: nombre de tu lámpara de referencia (el mismo del Paso 1)
    3. **Mide las MISMAS muestras con la lámpara NUEVA**
       - 📝 **Usa exactamente las mismas IDs** que en el paso anterior
       - 📝 Note: nombre de tu lámpara nueva (el mismo del Paso 1)
    4. **Exporta el archivo TSV** con todas las mediciones

    ⚠️ **Importante:** Es crítico que uses las mismas IDs para las mismas muestras en ambas lámparas. 
    El script emparejará las mediciones por ID.

    💡 **Tip:** Se recomienda medir entre 10-20 muestras representativas de tu rango analítico habitual.
    """)

    st.markdown("---")
    kit_file = st.file_uploader("📁 Sube el archivo TSV con las mediciones del Standard Kit", type="tsv", key="kit_upload")

    col_skip1, col_skip2 = st.columns([3, 1])
    with col_skip2:
        if st.button("⏭️ Omitir paso", key="skip_step2"):
            st.session_state.step = 3
            st.rerun()

    if kit_file:
        try:
            content = kit_file.read().decode("utf-8").replace(",", ".")
            df = pd.read_csv(io.StringIO(content), sep="\t")

            spectral_cols = [col for col in df.columns if col.startswith("#") and col[1:].isdigit()]
            df[spectral_cols] = df[spectral_cols].apply(pd.to_numeric, errors="coerce")

            df_kit = df[df["ID"].str.upper() != "WSTD"].copy()
            if len(df_kit) == 0:
                st.error("❌ No se encontraron mediciones de muestras (todas son WSTD).")
            else:
                lamp_options = [lamp for lamp in df_kit["Note"].unique() if pd.notna(lamp)]
                sample_ids = df_kit["ID"].unique()

                st.success("✅ Archivo cargado correctamente")
                st.write(f"**Total de mediciones:** {len(df_kit)}")
                st.write(f"**Muestras únicas:** {len(sample_ids)}")
                st.write(f"**Lámparas detectadas:** {', '.join(lamp_options)}")
                st.write(f"**Canales espectrales:** {len(spectral_cols)}")

                st.markdown("### 🔦 Identificación de Lámparas")
                col1, col2 = st.columns(2)
                with col1:
                    lamp_ref = st.selectbox("Selecciona la lámpara de REFERENCIA", lamp_options, index=0, key="lamp_ref_select")
                with col2:
                    lamp_new = st.selectbox("Selecciona la lámpara NUEVA", lamp_options, index=min(1, len(lamp_options)-1), key="lamp_new_select")

                df_ref = df_kit[df_kit["Note"] == lamp_ref].copy()
                df_new = df_kit[df_kit["Note"] == lamp_new].copy()

                df_ref_grouped = df_ref.groupby("ID")[spectral_cols].mean()
                df_new_grouped = df_new.groupby("ID")[spectral_cols].mean()

                common_ids = df_ref_grouped.index.intersection(df_new_grouped.index)
                if len(common_ids) == 0:
                    st.error("❌ No hay muestras comunes entre las dos lámparas. Verifica que uses las mismas IDs.")
                else:
                    df_ref_grouped = df_ref_grouped.loc[common_ids]
                    df_new_grouped = df_new_grouped.loc[common_ids]

                    st.success(f"✅ Se encontraron {len(common_ids)} muestras comunes entre ambas lámparas")

                    # === SELECCIÓN DE MUESTRAS (con confirmación) ===
                    st.markdown("### ✅ Selección de muestras para calcular la corrección")

                    # Valores por defecto: lo último confirmado o, si no existe, todas
                    if 'selected_ids' not in st.session_state:
                        st.session_state.selected_ids = list(common_ids)

                    # Estado intermedio mientras marcas/desmarcas (no confirmado aún)
                    if 'pending_selection' not in st.session_state:
                        st.session_state.pending_selection = list(st.session_state.selected_ids)

                    # Construimos tabla
                    df_samples = pd.DataFrame({
                        'ID': list(common_ids),
                        f'Mediciones {lamp_ref}': [len(df_ref[df_ref['ID'] == i]) for i in common_ids],
                        f'Mediciones {lamp_new}': [len(df_new[df_new['ID'] == i]) for i in common_ids],
                        'Usar en corrección': [i in st.session_state.pending_selection for i in common_ids]
                    })

                    with st.expander("📋 Ver muestras emparejadas"):
                        with st.form("form_select_samples", clear_on_submit=False):
                            edited = st.data_editor(
                                df_samples,
                                use_container_width=True,
                                hide_index=True,
                                disabled=[f'Mediciones {lamp_ref}', f'Mediciones {lamp_new}'],
                                key="editor_select_samples"
                            )

                            col_a, col_b, col_c, col_d = st.columns([1, 1, 1, 2])
                            btn_all = col_a.form_submit_button("Seleccionar todo")
                            btn_none = col_b.form_submit_button("Deseleccionar todo")
                            btn_invert = col_c.form_submit_button("Invertir selección")
                            btn_confirm = col_d.form_submit_button("✅ Confirmar selección", type="primary")

                    # Gestionar botones (se ejecuta tras enviar el form)
                    if btn_all:
                        st.session_state.pending_selection = list(common_ids)
                        st.rerun()

                    if btn_none:
                        st.session_state.pending_selection = []
                        st.rerun()

                    if btn_invert:
                        st.session_state.pending_selection = [i for i in common_ids if i not in st.session_state.pending_selection]
                        st.rerun()

                    if btn_confirm:
                        # Confirmar lo que está marcado en la tabla ahora mismo
                        st.session_state.pending_selection = edited.loc[edited['Usar en corrección'], 'ID'].tolist()
                        st.session_state.selected_ids = list(st.session_state.pending_selection)  # <- esto es lo que usa el Paso 3
                        st.success(f"Selección confirmada: {len(st.session_state.selected_ids)} muestras.")
                    else:
                        # Sin confirmar: sincronizar previsualización con lo que se ve en la tabla
                        if isinstance(edited, pd.DataFrame):
                            try:
                                st.session_state.pending_selection = edited.loc[edited['Usar en corrección'], 'ID'].tolist()
                            except Exception:
                                pass

                    st.caption(
                        f"Seleccionadas (pendiente/previa a confirmar): {len(st.session_state.pending_selection)} — "
                        f"Confirmadas: {len(st.session_state.get('selected_ids', []))}"
                    )


                    # Visualización de espectros
                    with st.expander("📊 Ver espectros promedio por muestra"):
                        fig_samples, ax_samples = plt.subplots(figsize=(12, 6))
                        for id_ in common_ids:
                            ax_samples.plot(range(1, len(spectral_cols) + 1), df_ref_grouped.loc[id_],
                                            label=f"{lamp_ref} - {id_}", alpha=0.7, linewidth=1)
                            ax_samples.plot(range(1, len(spectral_cols) + 1), df_new_grouped.loc[id_],
                                            linestyle="--", label=f"{lamp_new} - {id_}", alpha=0.7, linewidth=1)
                        ax_samples.set_title("Espectros promedio por muestra")
                        ax_samples.set_xlabel("Canal espectral")
                        ax_samples.set_ylabel("Absorbancia")
                        ax_samples.grid(True, alpha=0.3)
                        ax_samples.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
                        plt.tight_layout()
                        st.pyplot(fig_samples)

                    # Guardar datos
                    st.session_state.kit_data = {
                        'df': df_kit,
                        'df_ref_grouped': df_ref_grouped,
                        'df_new_grouped': df_new_grouped,
                        'spectral_cols': spectral_cols,
                        'lamp_ref': lamp_ref,
                        'lamp_new': lamp_new,
                        'common_ids': common_ids
                    }

                    st.markdown("---")
                    col_continue, col_skip = st.columns([3, 1])
                    with col_continue:
                        if st.button("➡️ Continuar al Paso 3", type="primary", use_container_width=True):
                            st.session_state.step = 3
                            st.rerun()
                    with col_skip:
                        if st.button("⏭️ Omitir", key="skip_after_step2", use_container_width=True):
                            st.session_state.step = 3
                            st.rerun()

        except Exception as e:
            st.error(f"❌ Error al procesar el archivo: {str(e)}")

# ============================================================================
# PASO 3: CALCULAR CORRECCIÓN
# ============================================================================
elif st.session_state.step == 3:
    st.markdown("## 📍 PASO 3 DE 5: Cálculo de Corrección Espectral")

    if st.session_state.kit_data is None:
        st.error("❌ No hay datos del Standard Kit. Vuelve al Paso 2.")
    else:
        kit_data = st.session_state.kit_data
        df_ref_grouped = kit_data['df_ref_grouped']
        df_new_grouped = kit_data['df_new_grouped']
        spectral_cols = kit_data['spectral_cols']
        lamp_ref = kit_data['lamp_ref']
        lamp_new = kit_data['lamp_new']
        common_ids = kit_data['common_ids']

        st.info(f"""
        **Calculando la diferencia espectral promedio entre:**
        - 🔵 Lámpara de referencia: **{lamp_ref}**
        - 🔴 Lámpara nueva: **{lamp_new}**
        - 📊 Basado en **{len(common_ids)} muestras** comunes
        """)

        # Calcular diferencias (solo con las muestras seleccionadas)
        ids_for_corr = st.session_state.get('selected_ids', list(common_ids))
        if len(ids_for_corr) == 0:
            st.warning("No has seleccionado ninguna muestra. Se usarán todas por defecto.")
            ids_for_corr = list(common_ids)
        try:
            df_ref_sel = df_ref_grouped.loc[ids_for_corr]
            df_new_sel = df_new_grouped.loc[ids_for_corr]
        except Exception:
            idx = [i for i in ids_for_corr if i in df_ref_grouped.index and i in df_new_grouped.index]
            df_ref_sel = df_ref_grouped.loc[idx]
            df_new_sel = df_new_grouped.loc[idx]

        diff_matrix = df_ref_sel.values - df_new_sel.values
        mean_diff = diff_matrix.mean(axis=0)

        # Crear DataFrame con resultados
        df_diff = pd.DataFrame({"Canal": range(1, len(mean_diff) + 1)})
        for id_ in common_ids:
            df_diff[f"{lamp_ref}_{id_}"] = df_ref_grouped.loc[id_].values
            df_diff[f"{lamp_new}_{id_}"] = df_new_grouped.loc[id_].values
            df_diff[f"DIF_{id_}"] = df_ref_grouped.loc[id_].values - df_new_grouped.loc[id_].values
        df_diff["CORRECCION_PROMEDIO"] = mean_diff

        # Visualización
        st.markdown("### 📊 Diferencias Espectrales por Muestra")
        fig_diff, ax_diff = plt.subplots(figsize=(12, 6))
        for id_ in common_ids:
            ax_diff.plot(df_diff["Canal"], df_diff[f"DIF_{id_}"], label=f"{id_}", alpha=0.4, linewidth=1)
        ax_diff.plot(df_diff["Canal"], df_diff["CORRECCION_PROMEDIO"], linewidth=3, label="Corrección Promedio", zorder=10)
        ax_diff.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        ax_diff.set_title(f"Diferencias espectrales: {lamp_ref} - {lamp_new}", fontsize=12, fontweight='bold')
        ax_diff.set_xlabel("Canal espectral")
        ax_diff.set_ylabel("Diferencia")
        ax_diff.legend()
        ax_diff.grid(True, alpha=0.3)
        plt.tight_layout()
        st.pyplot(fig_diff)

        # Estadísticas
        st.markdown("### 📈 Estadísticas de la Corrección")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Corrección máxima", f"{np.max(np.abs(mean_diff)):.4f}")
        with col2:
            st.metric("Corrección media", f"{np.mean(np.abs(mean_diff)):.4f}")
        with col3:
            st.metric("Desviación estándar", f"{np.std(mean_diff):.4f}")

        # Descargar tabla de corrección
        csv_diff = io.StringIO()
        df_diff.to_csv(csv_diff, index=False)
        st.download_button("📄 Descargar tabla de corrección (CSV)",
                           data=csv_diff.getvalue(),
                           file_name=f"correccion_{lamp_ref}_vs_{lamp_new}.csv",
                           mime="text/csv")

        # Guardar mean_diff
        st.session_state.kit_data['mean_diff'] = mean_diff

        st.markdown("---")
        col_continue, col_skip = st.columns([3, 1])
        with col_continue:
            if st.button("➡️ Continuar al Paso 4", type="primary", use_container_width=True):
                st.session_state.step = 4
                st.rerun()
        with col_skip:
            if st.button("⏭️ Omitir", key="skip_step3", use_container_width=True):
                st.session_state.step = 4
                st.rerun()

# ============================================================================
# PASO 4: CARGAR BASELINE
# ============================================================================
elif st.session_state.step == 4:
    st.markdown("## 📍 PASO 4 DE 5: Cargar Baseline de la Lámpara Nueva")

    if st.session_state.kit_data is None:
        st.error("❌ No hay datos del Standard Kit. Vuelve al Paso 2.")
    else:
        kit_data = st.session_state.kit_data
        lamp_new = kit_data['lamp_new']
        spectral_cols = kit_data['spectral_cols']
        mean_diff = kit_data.get('mean_diff', None)

        st.markdown(f"""
        ### 📋 Instrucciones:

        Necesitas cargar el archivo baseline actual de la lámpara **{lamp_new}** que tomaste en el Paso 2.

        Este archivo puede ser:
        - 📄 **Archivo .ref** (SX Suite 531 o anterior) - Formato binario
        - 📄 **Archivo .csv** (SX Suite 557 o posterior) - Formato de texto

        El archivo debe tener **exactamente {len(spectral_cols)} canales espectrales** para coincidir con tus mediciones.
        """)

        st.markdown("---")

        baseline_file = st.file_uploader("📁 Sube el archivo baseline (.ref o .csv)",
                                         type=["ref", "csv"], key="baseline_upload")

        col_skip1, col_skip2 = st.columns([3, 1])
        with col_skip2:
            if st.button("⏭️ Omitir paso", key="skip_step4"):
                st.session_state.step = 5
                st.rerun()

        if baseline_file:
            file_extension = baseline_file.name.split('.')[-1].lower()
            try:
                ref_spectrum = None
                header = None
                df_baseline = None
                origin = file_extension

                if file_extension == 'ref':
                    # Leer .REF
                    ref_data = np.frombuffer(baseline_file.read(), dtype=np.float32)
                    header = ref_data[:3]
                    ref_spectrum = ref_data[3:]

                    st.success("✅ Archivo .ref cargado correctamente")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**Valores de cabecera:**")
                        st.write(f"X1 = {header[0]:.6e}")
                        st.write(f"X2 = {header[1]:.6e}")
                        st.write(f"X3 = {header[2]:.6e}")
                    with col2:
                        st.metric("Puntos espectrales", len(ref_spectrum))
                        st.write("**Primeros 5 valores:**")
                        st.write(ref_spectrum[:5])

                elif file_extension == 'csv':
                    # Leer .CSV
                    df_baseline = pd.read_csv(baseline_file)
                    if 'data' not in df_baseline.columns or 'nir_pixels' not in df_baseline.columns:
                        st.error("❌ El archivo CSV no tiene la estructura esperada (faltan columnas 'data' o 'nir_pixels').")
                    else:
                        data_string = df_baseline['data'].iloc[0]
                        ref_spectrum = np.array(json.loads(data_string))
                        nir_pixels = int(df_baseline['nir_pixels'].iloc[0])

                        st.success("✅ Archivo .csv cargado correctamente")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("NIR Pixels", nir_pixels)
                            st.metric("Timestamp", df_baseline['time_stamp'].iloc[0])
                        with col2:
                            st.metric("Sys Temp (°C)", f"{df_baseline['sys_temp'].iloc[0]:.2f}")
                            st.metric("TEC Temp (°C)", f"{df_baseline['tec_temp'].iloc[0]:.2f}")
                        with col3:
                            st.metric("Lamp Time", df_baseline['lamp_time'].iloc[0])
                            st.metric("Puntos data", len(ref_spectrum))

                        if nir_pixels != len(ref_spectrum):
                            st.warning(f"⚠️ Inconsistencia: nir_pixels ({nir_pixels}) ≠ longitud data ({len(ref_spectrum)})")

                # Validación de dimensiones
                if ref_spectrum is not None:
                    if len(ref_spectrum) != len(spectral_cols):
                        st.error(f"❌ **Error de validación:** El baseline tiene {len(ref_spectrum)} puntos, pero el TSV tiene {len(spectral_cols)} canales. No coinciden.")
                    else:
                        st.success(f"✅ Validación correcta: {len(ref_spectrum)} puntos en ambos archivos")

                        # Visualizar baseline original
                        fig_base, ax_base = plt.subplots(figsize=(12, 4))
                        ax_base.plot(range(1, len(ref_spectrum) + 1), ref_spectrum, linewidth=2)
                        ax_base.set_title(f"Baseline original de {lamp_new}", fontsize=12, fontweight='bold')
                        ax_base.set_xlabel("Canal espectral")
                        ax_base.set_ylabel("Intensidad")
                        ax_base.grid(True, alpha=0.3)
                        plt.tight_layout()
                        st.pyplot(fig_base)

                        # Guardar datos
                        st.session_state.baseline_data = {
                            'ref_spectrum': ref_spectrum,
                            'header': header,
                            'df_baseline': df_baseline,
                            'origin': origin
                        }

                        st.markdown("---")
                        col_continue, col_skip = st.columns([3, 1])
                        with col_continue:
                            if st.button("➡️ Continuar al Paso 5", type="primary", use_container_width=True):
                                st.session_state.step = 5
                                st.rerun()
                        with col_skip:
                            if st.button("⏭️ Omitir", key="skip_after_step4", use_container_width=True):
                                st.session_state.step = 5
                                st.rerun()

            except Exception as e:
                st.error(f"❌ Error al procesar el archivo: {str(e)}")

# ============================================================================
# PASO 5: APLICAR CORRECCIÓN Y EXPORTAR
# ============================================================================
elif st.session_state.step == 5:
    st.markdown("## 📍 PASO 5 DE 5: Aplicar Corrección y Exportar")

    if st.session_state.kit_data is None or st.session_state.baseline_data is None:
        st.error("❌ Faltan datos. Vuelve a los pasos anteriores.")
    else:
        kit_data = st.session_state.kit_data
        baseline_data = st.session_state.baseline_data

        df_ref_grouped = kit_data['df_ref_grouped']
        df_new_grouped = kit_data['df_new_grouped']
        spectral_cols = kit_data['spectral_cols']
        lamp_ref = kit_data['lamp_ref']
        lamp_new = kit_data['lamp_new']
        common_ids = kit_data['common_ids']
        mean_diff = kit_data['mean_diff']
        df = kit_data['df']

        ref_spectrum = baseline_data['ref_spectrum']
        header = baseline_data['header']
        df_baseline = baseline_data['df_baseline']
        origin = baseline_data['origin']

        # Aplicar corrección
        ref_corrected = ref_spectrum - mean_diff
        st.success("✅ Corrección aplicada al baseline")

        st.markdown("### 📊 Comparación: Baseline Original vs Corregido")
        col_val1, col_val2 = st.columns(2)
        with col_val1:
            st.write("**Primeros 5 valores:**")
            st.write(f"Original: {ref_spectrum[:5]}")
            st.write(f"Corregido: {ref_corrected[:5]}")
        with col_val2:
            st.write("**Últimos 5 valores:**")
            st.write(f"Original: {ref_spectrum[-5:]}")
            st.write(f"Corregido: {ref_corrected[-5:]}")

        fig_comp, ax_comp = plt.subplots(figsize=(12, 5))
        ax_comp.plot(range(1, len(ref_spectrum) + 1), ref_spectrum, label="Baseline original", linewidth=2)
        ax_comp.plot(range(1, len(ref_corrected) + 1), ref_corrected, label="Baseline corregido", linewidth=2, linestyle="--")
        ax_comp.set_title("Comparación: baseline original vs corregido", fontsize=12, fontweight='bold')
        ax_comp.set_xlabel("Canal espectral")
        ax_comp.set_ylabel("Intensidad")
        ax_comp.legend()
        ax_comp.grid(True, alpha=0.3)
        plt.tight_layout()
        st.pyplot(fig_comp)

        # CSV de comparación
        df_comparison = pd.DataFrame({
            "Canal": range(1, len(ref_spectrum) + 1),
            "baseline_original": ref_spectrum,
            "baseline_corregido": ref_corrected,
            "correccion_aplicada": mean_diff
        })
        csv_comp = io.StringIO()
        df_comparison.to_csv(csv_comp, index=False)

        st.markdown("---")
        st.markdown("### 💾 Exportar Archivos Corregidos")

        col_exp1, col_exp2 = st.columns(2)

        # EXPORTAR .REF
        with col_exp1:
            st.markdown("#### 📄 Formato .ref (binario)")
            if origin == 'ref' and header is not None:
                final_ref = np.concatenate([header, ref_corrected.astype(np.float32)])
                st.info("✓ Cabecera original del sensor preservada")
                ref_bytes = io.BytesIO()
                ref_bytes.write(final_ref.astype(np.float32).tobytes())
                ref_bytes.seek(0)
                st.download_button("📥 Descargar .ref corregido",
                                   data=ref_bytes,
                                   file_name=f"baseline_{lamp_new}_corregido.ref",
                                   mime="application/octet-stream",
                                   key="download_ref",
                                   use_container_width=True)
            else:
                st.error("⚠️ No se puede generar .ref desde CSV: faltan valores de cabecera del sensor")

        # EXPORTAR .CSV
        with col_exp2:
            st.markdown("#### 📄 Formato .csv (nuevo software)")
            if origin == 'csv' and df_baseline is not None:
                df_export_csv = df_baseline.copy()
                df_export_csv['data'] = json.dumps(ref_corrected.tolist())
                st.success("✓ Metadatos originales preservados")
            else:
                st.warning("⚠️ Metadatos generados por defecto")
                df_export_csv = pd.DataFrame([{
                    'time_stamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'expires': '',
                    'sys_temp': 35.0,
                    'tec_temp': 25.0,
                    'lamp_time': '0:00:00',
                    'count': 1,
                    'vis_avg': 32000,
                    'vis_max': 65535,
                    'vis_int_time': 100,
                    'vis_gain': 1,
                    'vis_offset': 0,
                    'vis_scans': 10,
                    'vis_first': 0,
                    'vis_pixels': 256,
                    'nir_avg': 1000.0,
                    'nir_max': 4095,
                    'nir_int_time': 10.0,
                    'nir_gain': 1.0,
                    'nir_offset': 0,
                    'nir_scans': 10,
                    'nir_first': 0,
                    'nir_pixels': len(ref_corrected),
                    'bounds': '400.0,1000.0',
                    'data': json.dumps(ref_corrected.tolist())
                }])

            csv_bytes = io.StringIO()
            df_export_csv.to_csv(csv_bytes, index=False)
            st.download_button("📥 Descargar .csv corregido",
                               data=csv_bytes.getvalue(),
                               file_name=f"baseline_{lamp_new}_corregido.csv",
                               mime="text/csv",
                               key="download_csv",
                               use_container_width=True)

        # Descargar comparación
        st.download_button("📄 Descargar comparación detallada (CSV)",
                           data=csv_comp.getvalue(),
                           file_name=f"comparacion_baseline_{lamp_new}.csv",
                           mime="text/csv",
                           use_container_width=True)

        st.markdown("---")
        st.markdown("### 🔬 Simulación: Efecto de la Corrección")
        st.info("""
        A continuación se muestra cómo quedarían los espectros de la lámpara nueva después de 
        aplicar el baseline corregido, comparados con los espectros de la lámpara de referencia.
        """)

        # Simular corrección aplicada (sección desdoblada: usadas / no usadas)
        df_new_corr = df[df["Note"] == lamp_new].copy()
        df_new_corr[spectral_cols] = df_new_corr[spectral_cols].astype(float).values + ref_spectrum - ref_corrected

        used_ids = st.session_state.get('selected_ids', list(common_ids))
        other_ids = [i for i in common_ids if i not in used_ids]

        st.markdown("#### ✅ Muestras usadas en la corrección")
        fig_used, ax_used = plt.subplots(figsize=(12, 6))
        for id_ in used_ids:
            spec_ref = df_ref_grouped.loc[id_].values
            spec_corr = df_new_corr[df_new_corr['ID'] == id_][spectral_cols].astype(float).mean().values
            ax_used.plot(range(1, len(spec_ref) + 1), spec_ref, label=f"{lamp_ref} - {id_}", linewidth=1.5, alpha=0.85)
            ax_used.plot(range(1, len(spec_corr) + 1), spec_corr, linestyle="--", label=f"{lamp_new} corregido - {id_}", linewidth=1.5, alpha=0.85)
        ax_used.set_title(f"{lamp_ref} (referencia) vs {lamp_new} (corregido) — usadas en la corrección", fontsize=12, fontweight='bold')
        ax_used.set_xlabel("Canal espectral")
        ax_used.set_ylabel("Absorbancia")
        ax_used.grid(True, alpha=0.3)
        ax_used.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        st.pyplot(fig_used)

        if len(other_ids) > 0:
            st.markdown("#### 🔎 Muestras no usadas (validación)")
            fig_other, ax_other = plt.subplots(figsize=(12, 6))
            for id_ in other_ids:
                spec_ref = df_ref_grouped.loc[id_].values
                spec_corr = df_new_corr[df_new_corr['ID'] == id_][spectral_cols].astype(float).mean().values
                ax_other.plot(range(1, len(spec_ref) + 1), spec_ref, label=f"{lamp_ref} - {id_}", linewidth=1.5, alpha=0.85)
                ax_other.plot(range(1, len(spec_corr) + 1), spec_corr, linestyle="--", label=f"{lamp_new} corregido - {id_}", linewidth=1.5, alpha=0.85)
            ax_other.set_title(f"{lamp_ref} (referencia) vs {lamp_new} (corregido) — NO usadas", fontsize=12, fontweight='bold')
            ax_other.set_xlabel("Canal espectral")
            ax_other.set_ylabel("Absorbancia")
            ax_other.grid(True, alpha=0.3)
            ax_other.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            plt.tight_layout()
            st.pyplot(fig_other)
        else:
            st.info("Todas las muestras comunes están siendo usadas para calcular la corrección.")

        # Exportar TSV corregido
        df_export_tsv = df.copy()
        df_export_tsv.loc[df_export_tsv["Note"] == lamp_new, spectral_cols] = df_new_corr[spectral_cols]
        tsv_bytes = io.StringIO()
        df_export_tsv.to_csv(tsv_bytes, sep="\t", index=False)
        st.download_button("📥 Descargar TSV completo con espectros corregidos (verificación)",
                           data=tsv_bytes.getvalue(),
                           file_name=f"espectros_{lamp_new}_corregidos.tsv",
                           mime="text/tab-separated-values",
                           use_container_width=True)

        st.markdown("---")
        st.success("""
        ### ✅ Proceso Completado

        **Próximos pasos:**
        1. Descarga el baseline corregido en el formato adecuado (.ref o .csv)
        2. Copia el archivo a la ubicación correspondiente en tu sistema
        3. Verifica el ajuste midiendo nuevamente el White Standard sin línea base
        4. Los espectros de ambas lámparas deberían estar ahora alineados

        💾 **Recordatorio:** Asegúrate de haber realizado el backup de los archivos originales.
        """)

        # Generar informe
        st.markdown("---")
        st.markdown("### 📋 Generar Informe del Proceso")

        if st.button("📄 Generar Informe Completo", use_container_width=True, type="primary"):
            # Crear informe HTML
            client_data = st.session_state.client_data or {}
            wstd_data = st.session_state.wstd_data or {}

            # Asegurar listas de usadas / no usadas para el informe
            used_ids = st.session_state.get('selected_ids', list(common_ids))
            other_ids = [i for i in common_ids if i not in used_ids]

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
                    h2 {{ color: #34495e; margin-top: 30px; }}
                    .info-box {{ background-color: #ecf0f1; padding: 15px; border-radius: 5px; margin: 10px 0; }}
                    .warning-box {{ background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #ffc107; }}
                    .success-box {{ background-color: #d4edda; padding: 15px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #28a745; }}
                    .metric {{ display: inline-block; margin: 10px 20px 10px 0; }}
                    .metric-label {{ font-weight: bold; color: #7f8c8d; }}
                    .metric-value {{ color: #2c3e50; font-size: 1.1em; }}
                    table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                    th, td {{ border: 1px solid #bdc3c7; padding: 10px; text-align: left; }}
                    th {{ background-color: #3498db; color: white; }}
                    .status-good {{ color: #28a745; font-weight: bold; }}
                    .status-warning {{ color: #ffc107; font-weight: bold; }}
                    .status-bad {{ color: #dc3545; font-weight: bold; }}
                    .footer {{ margin-top: 50px; padding-top: 20px; border-top: 1px solid #bdc3c7; text-align: center; color: #7f8c8d; }}
                    .tag {{ display:inline-block; padding:2px 8px; border-radius:12px; font-size:0.85em; }}
                    .tag-ok {{ background:#e8f5e9; color:#2e7d32; border:1px solid #c8e6c9; }}
                    .tag-no {{ background:#fff3e0; color:#e65100; border:1px solid #ffe0b2; }}
                </style>
            </head>
            <body>
                <h1>📊 Informe de Ajuste de Baseline NIR</h1>

                <div class="info-box">
                    <h2>👤 Información del Cliente</h2>
                    <div class="metric">
                        <span class="metric-label">Cliente:</span>
                        <span class="metric-value">{client_data.get('client_name', 'N/A')}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Contacto:</span>
                        <span class="metric-value">{client_data.get('contact_person', 'N/A')}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Email:</span>
                        <span class="metric-value">{client_data.get('contact_email', 'N/A')}</span>
                    </div>
                    <br>
                    <div class="metric">
                        <span class="metric-label">N/S Sensor:</span>
                        <span class="metric-value">{client_data.get('sensor_sn', 'N/A')}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Modelo:</span>
                        <span class="metric-value">{client_data.get('equipment_model', 'N/A')}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Ubicación:</span>
                        <span class="metric-value">{client_data.get('location', 'N/A')}</span>
                    </div>
                    <br>
                    <div class="metric">
                        <span class="metric-label">Fecha del Proceso:</span>
                        <span class="metric-value">{client_data.get('date', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}</span>
                    </div>
                </div>
            """

            # Añadir diagnóstico WSTD si existe
            if wstd_data and 'grouped' in wstd_data:
                df_wstd_grouped = wstd_data['grouped']
                html_content += """
                <div class="warning-box">
                    <h2>🔍 Diagnóstico Inicial - White Standard (sin línea base)</h2>
                    <p><strong>Estado del sistema ANTES del ajuste:</strong></p>
                    <table>
                        <tr>
                            <th>Lámpara</th>
                            <th>Desv. Máxima</th>
                            <th>Desv. Media</th>
                            <th>Desv. Estándar</th>
                            <th>Estado</th>
                        </tr>
                """
                for lamp in df_wstd_grouped.index:
                    spectrum = df_wstd_grouped.loc[lamp].values
                    max_val = np.max(np.abs(spectrum))
                    mean_val = np.mean(np.abs(spectrum))
                    std_val = np.std(spectrum)
                    if max_val < 0.01:
                        status = '<span class="status-good">🟢 Bien ajustado</span>'
                    elif max_val < 0.05:
                        status = '<span class="status-warning">🟡 Desviación moderada</span>'
                    else:
                        status = '<span class="status-bad">🔴 Requiere ajuste</span>'

                    html_content += f"""
                        <tr>
                            <td><strong>{lamp}</strong></td>
                            <td>{max_val:.6f}</td>
                            <td>{mean_val:.6f}</td>
                            <td>{std_val:.6f}</td>
                            <td>{status}</td>
                        </tr>
                    """
                html_content += """
                    </table>
                    <p style="margin-top: 10px; font-size: 0.9em; color: #6c757d;">
                    <em>Nota: Las mediciones del White Standard sin línea base deben estar cercanas a 0 
                    en todo el espectro si el sistema está bien calibrado. Estas métricas muestran 
                    la desviación respecto al valor ideal (0).</em>
                    </p>
                </div>
                """

            html_content += f"""
                <div class="info-box">
                    <h2>🔬 Detalles del Proceso</h2>
                    <div class="metric">
                        <span class="metric-label">Lámpara de Referencia:</span>
                        <span class="metric-value">{lamp_ref}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Lámpara Nueva:</span>
                        <span class="metric-value">{lamp_new}</span>
                    </div>
                    <br>
                    <div class="metric">
                        <span class="metric-label">Canales Espectrales:</span>
                        <span class="metric-value">{len(spectral_cols)}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Muestras Comunes:</span>
                        <span class="metric-value">{len(common_ids)}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Muestras usadas en corrección:</span>
                        <span class="metric-value">{len(used_ids)}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Formato Baseline:</span>
                        <span class="metric-value">.{origin}</span>
                    </div>
                </div>

                <h2>📦 Muestras del Standard Kit</h2>
                <table>
                    <tr>
                        <th>ID Muestra</th>
                        <th>Mediciones {lamp_ref}</th>
                        <th>Mediciones {lamp_new}</th>
                        <th>Usada para corrección</th>
                    </tr>
            """

            # Tabla de muestras con marcado de usadas (✓/✗)
            for id_ in common_ids:
                count_ref = len(df[(df['ID'] == id_) & (df['Note'] == lamp_ref)])
                count_new = len(df[(df['ID'] == id_) & (df['Note'] == lamp_new)])
                used_tag = '<span class="tag tag-ok">✓ Sí</span>' if id_ in used_ids else '<span class="tag tag-no">✗ No</span>'
                html_content += f"""
                    <tr>
                        <td>{id_}</td>
                        <td>{count_ref}</td>
                        <td>{count_new}</td>
                        <td>{used_tag}</td>
                    </tr>
                """

            html_content += """
                </table>

                <div class="info-box">
                    <h2>📈 Estadísticas de la Corrección</h2>
            """

            html_content += f"""
                    <div class="metric">
                        <span class="metric-label">Corrección Máxima:</span>
                        <span class="metric-value">{np.max(np.abs(mean_diff)):.6f}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Corrección Media:</span>
                        <span class="metric-value">{np.mean(np.abs(mean_diff)):.6f}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Desviación Estándar:</span>
                        <span class="metric-value">{np.std(mean_diff):.6f}</span>
                    </div>
                </div>

                <div class="info-box">
                    <h2>📊 Baseline Generado</h2>
                    <div class="metric">
                        <span class="metric-label">Puntos Espectrales:</span>
                        <span class="metric-value">{len(ref_corrected)}</span>
                    </div>
            """

            if origin == 'ref' and header is not None:
                html_content += f"""
                    <div class="metric">
                        <span class="metric-label">Cabecera X1:</span>
                        <span class="metric-value">{header[0]:.6e}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Cabecera X2:</span>
                        <span class="metric-value">{header[1]:.6e}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Cabecera X3:</span>
                        <span class="metric-value">{header[2]:.6e}</span>
                    </div>
                """

            html_content += f"""
                    <br>
                    <div class="metric">
                        <span class="metric-label">Valor Mínimo:</span>
                        <span class="metric-value">{np.min(ref_corrected):.6f}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Valor Máximo:</span>
                        <span class="metric-value">{np.max(ref_corrected):.6f}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Valor Medio:</span>
                        <span class="metric-value">{np.mean(ref_corrected):.6f}</span>
                    </div>
                </div>
            """

            if client_data.get('notes'):
                html_content += f"""
                <div class="info-box">
                    <h2>📝 Notas Adicionales</h2>
                    <p>{client_data.get('notes')}</p>
                </div>
                """

            # ===== Gráficas para el informe =====
            import base64
            from io import BytesIO

            # 1) Gráfico: Muestras USADAS en la corrección (leyenda fuera)
            fig_used_rep, ax_used_rep = plt.subplots(figsize=(14, 7))
            for id_ in used_ids:
                spec_ref = df_ref_grouped.loc[id_].values
                spec_corr = df_new_corr[df_new_corr['ID'] == id_][spectral_cols].astype(float).mean().values
                ax_used_rep.plot(range(1, len(spec_ref) + 1), spec_ref, label=f"{lamp_ref} - {id_}", linewidth=2, alpha=0.85)
                ax_used_rep.plot(range(1, len(spec_corr) + 1), spec_corr, linestyle="--", label=f"{lamp_new} corregido - {id_}", linewidth=2, alpha=0.85)
            ax_used_rep.set_title("Resultado (usadas para corrección): Referencia vs Nueva corregida", fontsize=14, fontweight='bold')
            ax_used_rep.set_xlabel("Canal espectral")
            ax_used_rep.set_ylabel("Absorbancia")
            ax_used_rep.grid(True, alpha=0.3)
            ax_used_rep.legend(bbox_to_anchor=(1.02, 0.5), loc='center left', fontsize=9, frameon=False)
            plt.tight_layout(rect=[0, 0, 0.8, 1])  # espacio para la leyenda a la derecha

            buf_used = BytesIO()
            fig_used_rep.savefig(buf_used, format='png', dpi=150, bbox_inches='tight')
            buf_used.seek(0)
            img_used_base64 = base64.b64encode(buf_used.read()).decode()
            plt.close(fig_used_rep)

            # 2) Gráfico: Muestras NO usadas (validación) (leyenda fuera)
            img_val_base64 = ""
            if len(other_ids) > 0:
                fig_val_rep, ax_val_rep = plt.subplots(figsize=(14, 7))
                for id_ in other_ids:
                    spec_ref = df_ref_grouped.loc[id_].values
                    spec_corr = df_new_corr[df_new_corr['ID'] == id_][spectral_cols].astype(float).mean().values
                    ax_val_rep.plot(range(1, len(spec_ref) + 1), spec_ref, label=f"{lamp_ref} - {id_}", linewidth=2, alpha=0.85)
                    ax_val_rep.plot(range(1, len(spec_corr) + 1), spec_corr, linestyle="--", label=f"{lamp_new} corregido - {id_}", linewidth=2, alpha=0.85)
                ax_val_rep.set_title("Resultado (validación): Referencia vs Nueva corregida", fontsize=14, fontweight='bold')
                ax_val_rep.set_xlabel("Canal espectral")
                ax_val_rep.set_ylabel("Absorbancia")
                ax_val_rep.grid(True, alpha=0.3)
                ax_val_rep.legend(bbox_to_anchor=(1.02, 0.5), loc='center left', fontsize=9, frameon=False)
                plt.tight_layout(rect=[0, 0, 0.8, 1])

                buf_val = BytesIO()
                fig_val_rep.savefig(buf_val, format='png', dpi=150, bbox_inches='tight')
                buf_val.seek(0)
                img_val_base64 = base64.b64encode(buf_val.read()).decode()
                plt.close(fig_val_rep)

            # Insertar imágenes en el HTML
            html_content += f"""
                <h2>📊 Resultados gráficos</h2>
                <h3>✅ Muestras usadas en la corrección</h3>
                <img src="data:image/png;base64,{img_used_base64}" style="width:100%; max-width:1000px;">
            """
            if img_val_base64:
                html_content += f"""
                <h3>🔎 Muestras de validación (no usadas)</h3>
                <img src="data:image/png;base64,{img_val_base64}" style="width:100%; max-width:1000px;">
                """

            # Cierre del HTML
            html_content += f"""
                <div class="footer">
                    <p>Informe generado automáticamente por Baseline Adjustment Tool</p>
                    <p>Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
            </body>
            </html>
            """

            # Entregar informe
            st.download_button(
                label="📥 Descargar Informe HTML",
                data=html_content,
                file_name=f"Informe_Baseline_{client_data.get('sensor_sn', 'sensor')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                mime="text/html",
                use_container_width=True
            )
            st.success("✅ Informe generado correctamente")

        st.markdown("---")
        if st.button("🔄 Reiniciar proceso", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()



# ============================================================================
# SECCIÓN DE UTILIDADES (accesible desde cualquier paso)
# ============================================================================
st.markdown("---")
with st.expander("🔧 Utilidades: Conversión de archivos"):
    st.markdown("### Convertir archivo .ref a .csv")
    st.info("Convierte un archivo .ref (formato antiguo) a .csv (formato nuevo) con metadatos por defecto.")

    util_ref_file = st.file_uploader("Selecciona archivo .ref", type="ref", key="util_ref")
    if util_ref_file:
        try:
            ref_data = np.frombuffer(util_ref_file.read(), dtype=np.float32)
            header = ref_data[:3]
            ref_spectrum = ref_data[3:]

            st.write(f"✅ Archivo cargado: {len(ref_spectrum)} puntos espectrales")

            if st.button("Generar CSV desde .ref", key="util_convert"):
                df_export_csv = pd.DataFrame([{
                    'time_stamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'expires': '',
                    'sys_temp': 35.0,
                    'tec_temp': 25.0,
                    'lamp_time': '0:00:00',
                    'count': 1,
                    'vis_avg': 32000,
                    'vis_max': 65535,
                    'vis_int_time': 100,
                    'vis_gain': 1,
                    'vis_offset': 0,
                    'vis_scans': 10,
                    'vis_first': 0,
                    'vis_pixels': 256,
                    'nir_avg': 1000.0,
                    'nir_max': 4095,
                    'nir_int_time': 10.0,
                    'nir_gain': 1.0,
                    'nir_offset': 0,
                    'nir_scans': 10,
                    'nir_first': 0,
                    'nir_pixels': len(ref_spectrum),
                    'bounds': '400.0,1000.0',
                    'data': json.dumps(ref_spectrum.tolist())
                }])

                csv_bytes = io.StringIO()
                df_export_csv.to_csv(csv_bytes, index=False)

                st.warning("⚠️ CSV generado con metadatos por defecto. Solo 'nir_pixels' y 'data' son valores reales.")
                st.download_button("📥 Descargar CSV convertido",
                                   data=csv_bytes.getvalue(),
                                   file_name=util_ref_file.name.replace('.ref', '.csv'),
                                   mime="text/csv",
                                   key="util_download_csv")
        except Exception as e:
            st.error(f"Error: {str(e)}")
