# buchi_streamlit_theme.py

import streamlit as st


def load_shared_report_css() -> str:
    """
    Carga CSS compartido de informes HTML (para reports descargables).
    Si no existe el archivo, devuelve string vacío.
    """
    try:
        with open("buchi_report_styles_simple.css", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def apply_buchi_styles() -> None:
    """
    Estilos BUCHI en Streamlit (sin romper nada):
    - Sidebar corporativo (fondo + tipografía)
    - Botones PRIMARY verdes (global) → también en form_submit_button
    - Botones SECONDARY: default en main, pero en SIDEBAR gris oscuro para contraste con texto blanco
    - Header Streamlit intacto (Deploy/Settings/Rerun)
    - (Opcional) inyecta el CSS de reports si existe, pero NO dependemos de él
    """
    shared_css = load_shared_report_css()

    st.markdown(
        f"""
        <style>
        /* ================================
           (Opcional) CSS compartido de reports
           ================================ */
        {shared_css}

        /* =========================================================
           SIDEBAR – FONDO CORPORATIVO
           ========================================================= */
        [data-testid="stSidebar"] {{
            background-color: #093A34 !important;
        }}

        /* Textos del sidebar */
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] h4,
        [data-testid="stSidebar"] small {{
            color: #ffffff !important;
        }}

        /* Inputs del sidebar */
        [data-testid="stSidebar"] input,
        [data-testid="stSidebar"] textarea {{
            background-color: #ffffff !important;
            color: #111111 !important;
        }}

        /* =========================================================
           BOTONES PRIMARY – VERDE BUCHI (GLOBAL)
           ========================================================= */
        button[kind="primary"],
        button[kind="primaryFormSubmit"] {{
            background-color: #64B445 !important;
            color: #ffffff !important;
            border: 1px solid #64B445 !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
        }}

        button[kind="primary"]:hover,
        button[kind="primaryFormSubmit"]:hover {{
            background-color: #289A93 !important;
            border-color: #289A93 !important;
        }}

        /* =========================================================
           BOTONES SECONDARY – MAIN CONTENT
           → dejamos el estilo DEFAULT de Streamlit (NO TOCAR)
           ========================================================= */


        /* =========================================================
           BOTONES SECONDARY – SIDEBAR
           Gris medio oscuro para contraste con texto blanco
           ========================================================= */
        [data-testid="stSidebar"] button[kind="secondary"],
        [data-testid="stSidebar"] button[kind="secondaryFormSubmit"] {{
            background-color: #5f6b68 !important;
            color: #ffffff !important;
            border: 1px solid #5f6b68 !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
        }}

        [data-testid="stSidebar"] button[kind="secondary"]:hover,
        [data-testid="stSidebar"] button[kind="secondaryFormSubmit"]:hover {{
            background-color: #4e5956 !important;
            border-color: #4e5956 !important;
        }}

        /* =========================================================
           HEADER STREAMLIT (Deploy / Settings / Rerun)
           → NO tocar estilos
           ========================================================= */
        header button,
        header [role="button"] {{
            background-color: transparent !important;
            color: inherit !important;
            border: none !important;
            box-shadow: none !important;
            padding: initial !important;
        }}

        /* =========================================================
        EXPANDER ICON (flecha) – SIDEBAR
        ========================================================= */
        [data-testid="stSidebar"] svg[data-testid="stExpanderToggleIcon"] {{
            color: #ffffff !important;
            fill: currentColor !important;
        }}

        /* =========================================================
        LISTAS / ITEMS DENTRO DEL SIDEBAR (ul / li)
        ========================================================= */
        [data-testid="stSidebar"] ul,
        [data-testid="stSidebar"] li {{
            color: #ffffff !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
