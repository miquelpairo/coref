"""
COREF Suite - Launcher
"""
import streamlit as st

st.set_page_config(
    page_title="COREF Suite",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Definir páginas manualmente para control total del sidebar
pages = [
    st.Page("pages/0_🏠_Home.py", title="Home", icon="🏠"),
    st.Page("pages/1_📐_Baseline adjustment.py", title="Baseline Adjustment", icon="📐"),
    st.Page("pages/2_🎯_Validation_Standards.py", title="Validation Standards", icon="🎯"),
    st.Page("pages/3_🎚️_Offset_Adjustment.py", title="Offset Adjustment", icon="🎚️"),
    st.Page("pages/4_🔍_Comparacion_Espectros.py", title="Comparación Espectros", icon="🔍"),
    st.Page("pages/5_⚪_White_Reference_Comparison.py", title="White Reference", icon="⚪"),
]

pg = st.navigation(pages)
pg.run()