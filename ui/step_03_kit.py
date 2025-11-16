"""
Paso 4: Medicion del Standard Kit
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
    Renderiza el paso de medicion del Standard Kit (Paso 3).
    Ahora con archivos separados para referencia y nueva lampara.
    """
    st.markdown("## PASO 4 DE 7: Medicion del Standard Kit")
    
    st.info("""
    **Nuevo proceso con archivos separados:**
    
    1. **TSV Referencia**: Archivo maestro con mediciones historicas (puede ser antiguo)
    2. **TSV Nueva Lampara**: Mediciones recientes que quieres ajustar
    
    Los archivos se compararan por ID de muestra.
    """)
    
    st.markdown("---")
    
    # Boton omitir
    col_skip1, col_skip2 = st.columns([3, 1])
    with col_skip2:
        if st.button("Omitir paso", key="skip_step3"):
            st.session_state.unsaved_changes = False
            go_to_next_step()
    
    # ==========================================
    # UPLOADER 1: TSV REFERENCIA
    # ==========================================
    st.markdown("### 1️ Archivo de Referencia")
    ref_file = st.file_uploader(
        "Sube el TSV de REFERENCIA (archivo maestro)",
        type=["tsv", "txt", "csv"],
        key="ref_kit_upload",
        help="Archivo historico con mediciones bien calibradas"
    )
    
    # ==========================================
    # UPLOADER 2: TSV NUEVA LAMPARA
    # ==========================================
    st.markdown("### 2️ Archivo de Nueva Lampara")
    new_file = st.file_uploader(
        "Sube el TSV de la NUEVA lampara",
        type=["tsv", "txt", "csv"],
        key="new_kit_upload",
        help="Mediciones recientes que quieres ajustar"
    )
    
    # ==========================================
    # PROCESAR SI AMBOS ARCHIVOS ESTAN SUBIDOS
    # ==========================================
    if ref_file and new_file:
        # Marcar cambios sin guardar
        st.session_state.unsaved_changes = True
        
        try:
            # Cargar ambos archivos
            df_ref = load_tsv_file(ref_file)
            df_new = load_tsv_file(new_file)
            
            # Obtener columnas espectrales (deben ser iguales en ambos)
            spectral_cols_ref = get_spectral_columns(df_ref)
            spectral_cols_new = get_spectral_columns(df_new)
            
            # Validar que tengan las mismas columnas espectrales
            if len(spectral_cols_ref) != len(spectral_cols_new):
                st.error(f"""
                Los archivos tienen diferente numero de canales espectrales:
                - Referencia: {len(spectral_cols_ref)} canales
                - Nueva: {len(spectral_cols_new)} canales
                
                Asegurate de usar archivos del mismo equipo.
                """)
                return
            
            spectral_cols = spectral_cols_ref  # Usar las del archivo de referencia
            
            # Convertir a numerico
            df_ref[spectral_cols] = df_ref[spectral_cols].apply(pd.to_numeric, errors="coerce")
            df_new[spectral_cols] = df_new[spectral_cols].apply(pd.to_numeric, errors="coerce")
            
            # Filtrar muestras (excluir WSTD)
            df_ref_kit = df_ref[df_ref["ID"].str.upper() != "WSTD"].copy()
            df_new_kit = df_new[df_new["ID"].str.upper() != "WSTD"].copy()
            
            if len(df_ref_kit) == 0:
                st.error("No se encontraron muestras en el archivo de REFERENCIA")
                return
            
            if len(df_new_kit) == 0:
                st.error("No se encontraron muestras en el archivo de NUEVA lampara")
                return
            
            # Mostrar informacion
            st.success("Archivos cargados correctamente")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("** Archivo de Referencia:**")
                st.write(f"- Mediciones: {len(df_ref_kit)}")
                st.write(f"- Muestras unicas: {len(df_ref_kit['ID'].unique())}")
            
            with col2:
                st.markdown("** Archivo Nueva Lampara:**")
                st.write(f"- Mediciones: {len(df_new_kit)}")
                st.write(f"- Muestras unicas: {len(df_new_kit['ID'].unique())}")
            
            st.write(f"**Canales espectrales:** {len(spectral_cols)}")
            
            # Agrupar por ID (promedio de mediciones repetidas)
            df_ref_grouped = df_ref_kit.groupby("ID")[spectral_cols].mean()
            df_new_grouped = df_new_kit.groupby("ID")[spectral_cols].mean()
            
            # Encontrar muestras comunes
            common_ids = find_common_samples(df_ref_grouped, df_new_grouped)
            
            if not validate_common_samples(common_ids):
                return
            
            # Filtrar solo muestras comunes
            df_ref_grouped = df_ref_grouped.loc[common_ids]
            df_new_grouped = df_new_grouped.loc[common_ids]
            
            st.success(f"Se encontraron {len(common_ids)} muestras comunes entre ambos archivos")
            
            # Seleccion de muestras para correccion
            render_sample_selection_simple(common_ids)
            
            # Visualizacion de espectros
            render_spectra_visualization_simple(
                df_ref_grouped, df_new_grouped,
                spectral_cols, common_ids
            )
            
            # Guardar datos (sin nombres de lamparas)
            save_kit_data(
                df=df_new_kit,  # Guardamos el df de la nueva lampara para el paso 6
                df_ref_grouped=df_ref_grouped,
                df_new_grouped=df_new_grouped,
                spectral_cols=spectral_cols,
                lamp_ref="Referencia",  # Nombre generico
                lamp_new="Nueva",       # Nombre generico
                common_ids=common_ids
            )
            
            # Botones de navegacion
            st.markdown("---")
            col_continue, col_skip = st.columns([3, 1])
            with col_continue:
                if st.button("Continuar al Paso 5", type="primary", use_container_width=True):
                    st.session_state.unsaved_changes = False
                    go_to_next_step()
            with col_skip:
                if st.button("Omitir", key="skip_after_step3", use_container_width=True):
                    st.session_state.unsaved_changes = False
                    go_to_next_step()
                    
        except Exception as e:
            st.error(f"Error al procesar los archivos: {str(e)}")
            import traceback
            st.error(traceback.format_exc())


def render_sample_selection_simple(common_ids):
    """
    Renderiza seleccion de muestras sin nombres de lamparas especificos.
    """
    st.markdown("### Seleccion de muestras para calcular la correccion")
    
    # Inicializar seleccion
    if 'selected_ids' not in st.session_state:
        st.session_state.selected_ids = list(common_ids)

    if 'pending_selection' not in st.session_state:
        st.session_state.pending_selection = list(common_ids)

    # Tabla de muestras
    df_samples = pd.DataFrame({
        'ID': list(common_ids),
        'Usar en correccion': [
            i in st.session_state.pending_selection 
            for i in common_ids
        ]
    })
    
    with st.expander("Ver y seleccionar muestras", expanded=True):
        with st.form("form_select_samples", clear_on_submit=False):
            edited = st.data_editor(
                df_samples,
                use_container_width=True,
                hide_index=True,
                disabled=['ID'],
                key="editor_select_samples"
            )
            
            col_a, col_b, col_c, col_d = st.columns([1, 1, 1, 2])
            btn_all = col_a.form_submit_button("Seleccionar todo")
            btn_none = col_b.form_submit_button("Deseleccionar todo")
            btn_invert = col_c.form_submit_button("Invertir seleccion")
            btn_confirm = col_d.form_submit_button("Confirmar seleccion", type="primary")
        
        if btn_all:
            st.session_state.pending_selection = list(common_ids)
            st.rerun()
        
        if btn_none:
            st.session_state.pending_selection = []
            st.rerun()
        
        if btn_invert:
            inverted = [i for i in common_ids if i not in st.session_state.pending_selection]
            st.session_state.pending_selection = inverted
            st.rerun()
        
        if btn_confirm:
            pending = edited.loc[edited['Usar en correccion'], 'ID'].tolist()
            st.session_state.pending_selection = pending
            st.session_state.selected_ids = pending
            st.success(f"Seleccion confirmada: {len(st.session_state.selected_ids)} muestras.")
        else:
            if isinstance(edited, pd.DataFrame):
                try:
                    pending = edited.loc[edited['Usar en correccion'], 'ID'].tolist()
                    st.session_state.pending_selection = pending
                except Exception:
                    pass
        
        st.caption(
            f"Seleccionadas (pendiente): {len(st.session_state.pending_selection)} - "
            f"Confirmadas: {len(st.session_state.get('selected_ids', []))}"
        )


def render_spectra_visualization_simple(df_ref_grouped, df_new_grouped, 
                                       spectral_cols, common_ids):
    """
    Visualizacion de espectros sin nombres de lamparas especificos.
    """
    with st.expander("Ver espectros promedio por muestra"):
        selected_ids = st.session_state.get('selected_ids', list(common_ids))
        ids_to_plot = selected_ids if len(selected_ids) > 0 else list(common_ids)
        
        if len(ids_to_plot) < len(common_ids):
            st.info(f"Mostrando {len(ids_to_plot)} de {len(common_ids)} muestras (solo seleccionadas)")
        
        fig = plot_kit_spectra(
            df_ref_grouped, df_new_grouped,
            spectral_cols, 
            "Referencia", "Nueva",  # Nombres genericos
            ids_to_plot
        )
        st.plotly_chart(fig, use_container_width=True)