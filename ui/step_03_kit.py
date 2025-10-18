"""
Paso 3: Medición del Standard Kit
"""
import streamlit as st
import pandas as pd
from config import INSTRUCTIONS, MESSAGES
from session_manager import (
    save_kit_data, 
    go_to_next_step,
    update_selected_samples,
    update_pending_selection
)
from core.file_handlers import load_tsv_file, get_spectral_columns
from core.spectral_processing import group_measurements_by_lamp, find_common_samples
from utils.plotting import plot_kit_spectra
from utils.validators import validate_common_samples


def render_kit_step():
    """
    Renderiza el paso de medición del Standard Kit (Paso 2).
    """
    st.markdown("## 📍 PASO 2 DE 5: Medición del Standard Kit")
    st.markdown(INSTRUCTIONS['kit'])

    st.markdown("---")
    kit_file = st.file_uploader(
        "📁 Sube el archivo TSV con las mediciones del Standard Kit", 
        type="tsv", 
        key="kit_upload"
    )

    col_skip1, col_skip2 = st.columns([3, 1])
    with col_skip2:
        if st.button("⏭️ Omitir paso", key="skip_step2"):
            go_to_next_step()

    if kit_file:
        try:
            # Cargar archivo
            df = load_tsv_file(kit_file)
            
            # Obtener columnas espectrales
            spectral_cols = get_spectral_columns(df)
            
            # Convertir columnas espectrales a numérico
            df[spectral_cols] = df[spectral_cols].apply(pd.to_numeric, errors="coerce")
            
            # Filtrar muestras (excluir WSTD)
            df_kit = df[df["ID"].str.upper() != "WSTD"].copy()
            
            if len(df_kit) == 0:
                st.error(MESSAGES['error_no_samples'])
                return
            
            # Obtener información básica
            lamp_options = [lamp for lamp in df_kit["Note"].unique() if pd.notna(lamp)]
            sample_ids = df_kit["ID"].unique()
            
            # Mostrar información
            st.success(MESSAGES['success_file_loaded'])
            st.write(f"**Total de mediciones:** {len(df_kit)}")
            st.write(f"**Muestras únicas:** {len(sample_ids)}")
            st.write(f"**Lámparas detectadas:** {', '.join(lamp_options)}")
            st.write(f"**Canales espectrales:** {len(spectral_cols)}")
            
            # Selección de lámparas
            st.markdown("### 🔦 Identificación de Lámparas")
            lamp_ref, lamp_new = render_lamp_selection(lamp_options)
            
            # Agrupar mediciones por lámpara
            df_ref_grouped, df_new_grouped = group_measurements_by_lamp(
                df_kit, spectral_cols, lamp_ref, lamp_new
            )
            
            # Encontrar muestras comunes
            common_ids = find_common_samples(df_ref_grouped, df_new_grouped)
            
            if not validate_common_samples(common_ids):
                return
            
            # Filtrar solo muestras comunes
            df_ref_grouped = df_ref_grouped.loc[common_ids]
            df_new_grouped = df_new_grouped.loc[common_ids]
            
            st.success(f"✅ Se encontraron {len(common_ids)} muestras comunes entre ambas lámparas")
            
            # Selección de muestras para corrección
            render_sample_selection(df_kit, common_ids, lamp_ref, lamp_new)
            
            # Visualización de espectros
            render_spectra_visualization(
                df_ref_grouped, df_new_grouped, 
                spectral_cols, lamp_ref, lamp_new, common_ids
            )
            
            # Guardar datos
            save_kit_data(
                df=df_kit,
                df_ref_grouped=df_ref_grouped,
                df_new_grouped=df_new_grouped,
                spectral_cols=spectral_cols,
                lamp_ref=lamp_ref,
                lamp_new=lamp_new,
                common_ids=common_ids
            )
            
            # Botones de navegación
            st.markdown("---")
            col_continue, col_skip = st.columns([3, 1])
            with col_continue:
                if st.button("➡️ Continuar al Paso 3", type="primary", use_container_width=True):
                    go_to_next_step()
            with col_skip:
                if st.button("⏭️ Omitir", key="skip_after_step2", use_container_width=True):
                    go_to_next_step()
                    
        except Exception as e:
            st.error(f"❌ Error al procesar el archivo: {str(e)}")


def render_lamp_selection(lamp_options):
    """
    Renderiza los selectores para identificar lámparas.
    
    Args:
        lamp_options (list): Lista de lámparas disponibles
        
    Returns:
        tuple: (lamp_ref, lamp_new) nombres de las lámparas seleccionadas
    """
    col1, col2 = st.columns(2)
    
    with col1:
        lamp_ref = st.selectbox(
            "Selecciona la lámpara de REFERENCIA", 
            lamp_options, 
            index=0, 
            key="lamp_ref_select"
        )
    
    with col2:
        lamp_new = st.selectbox(
            "Selecciona la lámpara NUEVA", 
            lamp_options, 
            index=min(1, len(lamp_options)-1), 
            key="lamp_new_select"
        )
    
    return lamp_ref, lamp_new


def render_sample_selection(df, common_ids, lamp_ref, lamp_new):
    """
    Renderiza la interfaz de selección de muestras para la corrección.
    
    Args:
        df (pd.DataFrame): DataFrame completo con mediciones
        common_ids (list): Lista de IDs comunes
        lamp_ref (str): Nombre de la lámpara de referencia
        lamp_new (str): Nombre de la lámpara nueva
    """
    st.markdown("### ✅ Selección de muestras para calcular la corrección")
    
    # Inicializar selección si no existe
    if 'selected_ids' not in st.session_state:
        st.session_state.selected_ids = list(common_ids)
    
    if 'pending_selection' not in st.session_state:
        st.session_state.pending_selection = list(st.session_state.selected_ids)
    
    # Construir tabla de muestras
    df_samples = pd.DataFrame({
        'ID': list(common_ids),
        f'Mediciones {lamp_ref}': [
            len(df[(df['ID'] == i) & (df['Note'] == lamp_ref)]) 
            for i in common_ids
        ],
        f'Mediciones {lamp_new}': [
            len(df[(df['ID'] == i) & (df['Note'] == lamp_new)]) 
            for i in common_ids
        ],
        'Usar en corrección': [
            i in st.session_state.pending_selection 
            for i in common_ids
        ]
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
        
        # Gestionar botones
        if btn_all:
            update_pending_selection(list(common_ids))
            st.rerun()
        
        if btn_none:
            update_pending_selection([])
            st.rerun()
        
        if btn_invert:
            inverted = [i for i in common_ids if i not in st.session_state.pending_selection]
            update_pending_selection(inverted)
            st.rerun()
        
        if btn_confirm:
            # Confirmar lo que está marcado en la tabla
            pending = edited.loc[edited['Usar en corrección'], 'ID'].tolist()
            update_pending_selection(pending)
            update_selected_samples(pending)
            st.success(f"Selección confirmada: {len(st.session_state.selected_ids)} muestras.")
        else:
            # Sincronizar previsualización con la tabla
            if isinstance(edited, pd.DataFrame):
                try:
                    pending = edited.loc[edited['Usar en corrección'], 'ID'].tolist()
                    update_pending_selection(pending)
                except Exception:
                    pass
        
        st.caption(
            f"Seleccionadas (pendiente/previa a confirmar): {len(st.session_state.pending_selection)} — "
            f"Confirmadas: {len(st.session_state.get('selected_ids', []))}"
        )


def render_spectra_visualization(df_ref_grouped, df_new_grouped, spectral_cols, 
                                lamp_ref, lamp_new, common_ids):
    """
    Renderiza la visualización de espectros por muestra.
    
    Args:
        df_ref_grouped (pd.DataFrame): Mediciones de referencia agrupadas
        df_new_grouped (pd.DataFrame): Mediciones nuevas agrupadas
        spectral_cols (list): Lista de columnas espectrales
        lamp_ref (str): Nombre de lámpara de referencia
        lamp_new (str): Nombre de lámpara nueva
        common_ids (list): IDs comunes
    """
    with st.expander("📊 Ver espectros promedio por muestra"):
        fig = plot_kit_spectra(
            df_ref_grouped, df_new_grouped, 
            spectral_cols, lamp_ref, lamp_new, common_ids
        )
        st.pyplot(fig)
