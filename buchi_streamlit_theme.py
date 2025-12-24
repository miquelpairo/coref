# buchi_streamlit_theme.py

import streamlit as st  # ← AÑADIR ESTA LÍNEA

def load_shared_report_css():
    """Carga CSS compartido de informes HTML"""
    try:
        with open('buchi_report_styles_simple.css', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return ""

def apply_buchi_styles():
    # Cargar CSS compartido
    shared_css = load_shared_report_css()
    
    st.markdown(f"""
        <style>
        /* ===== CSS COMPARTIDO DE INFORMES ===== */
        {shared_css}
        
        /* ===== SOLO OVERRIDES ESPECÍFICOS DE STREAMLIT ===== */
        [data-testid="stSidebar"] {{
            background-color: #093A34 !important;
        }}
        
        [data-testid="stSidebar"] * {{
            color: #FFFFFF !important;
        }}
        
        /* ... resto de estilos SOLO de Streamlit ... */
        </style>
    """, unsafe_allow_html=True)