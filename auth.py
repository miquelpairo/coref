# -*- coding: utf-8 -*-
"""
Sistema de autenticacion con usuario y contrasena
"""
import streamlit as st


def check_password():
    """
    Verifica usuario y contrasena. Retorna True si es correcto.
    """
    # Verificar si ya esta autenticado
    if st.session_state.get("authenticated", False):
        return True
    
    # Mostrar formulario de login
    st.markdown("# 🔐 NIR ServiceKit")
    st.markdown("### Acceso Restringido")
    st.markdown("---")
    
    # Centrar el formulario
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            username = st.text_input(
                "Usuario",
                placeholder="Introduce tu usuario"
            )
            password = st.text_input(
                "Contrasena",
                type="password",
                placeholder="Introduce tu contrasena"
            )
            submit = st.form_submit_button(
                "Acceder", 
                use_container_width=True, 
                type="primary"
            )
            
            if submit:
                # Obtener credenciales desde secrets
                try:
                    correct_username = st.secrets["auth"]["username"]
                    correct_password = st.secrets["auth"]["password"]
                except:
                    # Credenciales por defecto (CAMBIAR ESTAS)
                    correct_username = "admin"
                    correct_password = "baseline2025"
                
                # Verificar credenciales
                if username == correct_username and password == correct_password:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.success("Acceso concedido")
                    st.rerun()
                else:
                    st.error("Usuario o contrasena incorrectos")
                    return False
        
        st.markdown("---")
        st.caption("Contacta al administrador si necesitas acceso")
    
    return False


def logout():
    """
    Cierra la sesion del usuario.
    """
    st.session_state.authenticated = False
    st.session_state.username = None
    st.rerun()
