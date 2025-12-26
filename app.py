"""
NIR ServiceKit - Launcher
Professional Service Toolkit for NIR Spectroscopy
"""
import streamlit as st

st.set_page_config(
    page_title="NIR ServiceKit",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Definir páginas agrupadas por categorías
pages = {
    "": [  # Grupo vacío para evitar título duplicado
        st.Page("pages/0_🏠_Home.py", title="Home", icon="🏠"),
    ],
    "🔧 Service": [
        st.Page("pages/1_📐_Baseline adjustment.py", title="Baseline Adjustment", icon="📐"),
        st.Page("pages/2_🎯_Validation_Standards.py", title="Validation Standards", icon="🎯"),
        st.Page("pages/3_🎚️_Offset_Adjustment.py", title="Offset Adjustment", icon="🎚️"),
    ],
    "📊 Application": [
        st.Page("pages/4_🔍_Comparacion_Espectros.py", title="Comparación Espectros", icon="🔍"),
        st.Page("pages/6_📊_Prediction_Reports.py", title="Prediction Reports", icon="📊"),
        st.Page("pages/07_📦_MetaReports.py", title="Report Consolidator", icon="📦"),
        st.Page("pages/08_✅_TSV_Validation_Reports.py", title="TSV Validation Reports", icon="✅"),
    ],
}

pg = st.navigation(pages)
pg.run()