"""
NIR ServiceKit - Home
============
NIR Service & Application Tools Suite
Página principal con navegación a herramientas.

Author: Miquel
Date: 2025
"""

import streamlit as st
from auth import check_password
from buchi_streamlit_theme import apply_buchi_styles
from app_config.messages import HOME_PAGE

# Aplicar estilos corporativos
apply_buchi_styles()

# Verificación de autenticación
if not check_password():
    st.stop()

# ============================================================================
# PÁGINA HOME
# ============================================================================

st.title(HOME_PAGE['title'])
st.markdown(f"### {HOME_PAGE['subtitle']}")

st.divider()

# Descripción general
st.markdown(HOME_PAGE['description'])

st.divider()

# ============================================================================
# SECCIÓN 1: SERVICE TOOLS
# ============================================================================
service = HOME_PAGE['service_tools']
st.markdown(f"## {service['section_title']}")
st.markdown(f"*{service['section_subtitle']}*")

st.write("")

# ---------------------------------------------------------------------------
# FILA 1 (3 columnas): Baseline | Validation | Offset
# ---------------------------------------------------------------------------
col1, col2, col3 = st.columns(3)

# BASELINE
with col1:
    tool = service['baseline']
    features_html = ''.join([f'<li>{f}</li>' for f in tool['features']])
    st.markdown(
        f"""
    <div class="card-container {tool['card_class']}">
        <h3>{tool['title']}</h3>
        <p>{tool['description']}</p>
        <ul>
            {features_html}
        </ul>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.write("")
    if st.button(
        tool['button'],
        key="btn_baseline",
        use_container_width=True,
        type="primary",
    ):
        st.switch_page(tool['page'])

# VALIDATION
with col2:
    tool = service['validation']
    features_html = ''.join([f'<li>{f}</li>' for f in tool['features']])
    st.markdown(
        f"""
    <div class="card-container {tool['card_class']}">
        <h3>{tool['title']}</h3>
        <p>{tool['description']}</p>
        <ul>
            {features_html}
        </ul>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.write("")
    if st.button(
        tool['button'],
        key="btn_validation",
        use_container_width=True,
        type="primary",
    ):
        st.switch_page(tool['page'])

# OFFSET
with col3:
    tool = service['offset']
    features_html = ''.join([f'<li>{f}</li>' for f in tool['features']])
    st.markdown(
        f"""
    <div class="card-container {tool['card_class']}">
        <h3>{tool['title']}</h3>
        <p>{tool['description']}</p>
        <ul>
            {features_html}
        </ul>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.write("")
    if st.button(
        tool['button'],
        key="btn_offset",
        use_container_width=True,
        type="primary",
    ):
        st.switch_page(tool['page'])

st.divider()

# ============================================================================
# SECCIÓN 2: APPLICATION TOOLS
# ============================================================================
apps = HOME_PAGE['application_tools']
st.markdown(f"## {apps['section_title']}")
st.markdown(f"*{apps['section_subtitle']}*")

st.write("")

# ---------------------------------------------------------------------------
# FILA 2 (2 columnas centradas): Spectrum | Predictions
# ---------------------------------------------------------------------------
sp3, col4, col5, sp4 = st.columns([0.5, 1, 1, 0.5])

# SPECTRUM COMPARISON
with col4:
    tool = apps['spectrum']
    features_html = ''.join([f'<li>{f}</li>' for f in tool['features']])
    st.markdown(
        f"""
    <div class="card-container {tool['card_class']}">
        <h3>{tool['title']}</h3>
        <p>{tool['description']}</p>
        <ul>
            {features_html}
        </ul>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.write("")
    if st.button(
        tool['button'],
        key="btn_comparison",
        use_container_width=True,
        type="primary",
    ):
        st.switch_page(tool['page'])

# PREDICTION REPORTS
with col5:
    tool = apps['predictions']
    features_html = ''.join([f'<li>{f}</li>' for f in tool['features']])
    st.markdown(
        f"""
    <div class="card-container {tool['card_class']}">
        <h3>{tool['title']}</h3>
        <p>{tool['description']}</p>
        <ul>
            {features_html}
        </ul>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.write("")
    if st.button(
        tool['button'],
        key="btn_predictions",
        use_container_width=True,
        type="primary",
    ):
        st.switch_page(tool['page'])

# ---------------------------------------------------------------------------
# FILA 3 (2 tarjetas centradas): MetaReports | TSV Validation Reports
# ---------------------------------------------------------------------------
st.write("")

sp1, c1, c2, sp2 = st.columns([0.5, 1, 1, 0.5])

# METAREPORTS
with c1:
    tool = apps['metareports']
    features_html = ''.join([f'<li>{f}</li>' for f in tool['features']])
    st.markdown(
        f"""
    <div class="card-container {tool['card_class']}">
        <h3>{tool['title']}</h3>
        <p>{tool['description']}</p>
        <ul>
            {features_html}
        </ul>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.write("")
    if st.button(
        tool['button'],
        key="btn_metareports",
        use_container_width=True,
        type="primary",
    ):
        st.switch_page(tool['page'])

# TSV VALIDATION REPORTS
with c2:
    tool = apps['tsv_validation']
    features_html = ''.join([f'<li>{f}</li>' for f in tool['features']])
    st.markdown(
        f"""
    <div class="card-container {tool['card_class']}">
        <h3>{tool['title']}</h3>
        <p>{tool['description']}</p>
        <ul>
            {features_html}
        </ul>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.write("")
    if st.button(
        tool['button'],
        key="btn_tsv_validation_reports",
        use_container_width=True,
        type="primary",
    ):
        st.switch_page(tool['page'])

st.divider()

# Información adicional - Workflow
st.markdown(f"### {HOME_PAGE['workflow']['title']}")
st.markdown(HOME_PAGE['workflow']['content'])

st.divider()

# Footer
footer = HOME_PAGE['footer']
st.markdown(
    f"""
<div style="text-align: center; color: #666; padding: 20px;">
    <p><strong>{footer['app_name']}</strong> | Versión {HOME_PAGE['version']} </p>
    <p>{footer['support_text']}</p>
</div>
""",
    unsafe_allow_html=True,
)