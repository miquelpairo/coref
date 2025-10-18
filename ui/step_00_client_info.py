"""
Paso 0: Información del Cliente
"""
import streamlit as st
from config import INSTRUCTIONS
from session_manager import (
    save_client_data, 
    save_default_client_data, 
    go_to_next_step
)


def render_client_info_step():
    """
    Renderiza el formulario de información del cliente (Paso -1).
    """
    st.markdown("## 📍 PASO 0: Información del Cliente")
    st.info(INSTRUCTIONS['client_info'])

    with st.form("client_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            client_name = st.text_input(
                "Nombre del Cliente *", 
                placeholder="Ej: Agropecuaria San José"
            )
            contact_person = st.text_input(
                "Persona de Contacto", 
                placeholder="Ej: Juan Pérez"
            )
            contact_email = st.text_input(
                "Email de Contacto", 
                placeholder="ejemplo@empresa.com"
            )
        
        with col2:
            sensor_sn = st.text_input(
                "Número de Serie del Sensor *", 
                placeholder="Ej: NIR-2024-001"
            )
            equipment_model = st.text_input(
                "Modelo del Equipo", 
                placeholder="Ej: SX-Suite 557"
            )
            location = st.text_input(
                "Ubicación", 
                placeholder="Ej: Planta Barcelona"
            )
        
        notes = st.text_area(
            "Notas adicionales", 
            placeholder="Información adicional relevante..."
        )

        submitted = st.form_submit_button(
            "✅ Guardar y Continuar", 
            type="primary", 
            use_container_width=True
        )
        
        if submitted:
            if not client_name or not sensor_sn:
                st.error("❌ Los campos marcados con * son obligatorios")
            else:
                save_client_data(
                    client_name=client_name,
                    sensor_sn=sensor_sn,
                    contact_person=contact_person,
                    contact_email=contact_email,
                    equipment_model=equipment_model,
                    location=location,
                    notes=notes
                )
                go_to_next_step()

    st.markdown("---")
    if st.button("⏭️ Omitir (no recomendado)", use_container_width=True):
        save_default_client_data()
        go_to_next_step()
