# -*- coding: utf-8 -*-
"""
Paso 1: Informacion del Cliente
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
    Renderiza el formulario de informacion del cliente (Paso 0).
    """
    st.markdown("## PASO 1 DE 7: Informacion del Cliente")
    st.info(INSTRUCTIONS['client_info'])
    
    with st.form("client_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            client_name = st.text_input(
                "Nombre del Cliente *", 
                placeholder="Ej: Empresa"
            )
            contact_person = st.text_input(
                "Persona de Contacto", 
                placeholder="Ej: Nombre y apellido"
            )
            contact_email = st.text_input(
                "Email de Contacto", 
                placeholder="ejemplo@empresa.com"
            )
        
        with col2:
            sensor_sn = st.text_input(
                "Numero de Serie del Sensor *", 
                placeholder="Ej: NIR-2024-001"
            )
            equipment_model = st.text_input(
                "Modelo del Equipo", 
                placeholder="Ej: SX-Suite 557"
            )
            location = st.text_input(
                "Ubicacion", 
                placeholder="Ej: Planta Barcelona"
            )
            technician = st.text_input(
                "Tecnico que realiza la tarea",
                placeholder="Ej: Nombre y Apellido"
            )
        
        notes = st.text_area(
            "Notas adicionales", 
            placeholder="Informacion adicional relevante..."
        )
        
        submitted = st.form_submit_button(
            "Guardar y Continuar", 
            type="primary", 
            use_container_width=True
        )
        
        if submitted:
            if not client_name or not sensor_sn:
                st.error("Los campos marcados con * son obligatorios")
            else:
                save_client_data(
                    client_name=client_name,
                    sensor_sn=sensor_sn,
                    contact_person=contact_person,
                    contact_email=contact_email,
                    equipment_model=equipment_model,
                    location=location,
                    notes=notes,
                    technician=technician
                )
                go_to_next_step()
    
    st.markdown("---")
    if st.button("Omitir (no recomendado)", use_container_width=True):
        save_default_client_data()
        go_to_next_step()