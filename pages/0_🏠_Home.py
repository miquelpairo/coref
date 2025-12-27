"""
NIR ServiceKit - Home
============
NIR Service & Application Tools Suite
Página principal con navegación a herramientas.

Author: Miquel
Date: 2025
"""

import streamlit as st
import streamlit.components.v1 as components
from auth import check_password
from buchi_streamlit_theme import apply_buchi_styles
from app_config.messages import HOME_PAGE
from css.carousel_styles import CAROUSEL_CSS

# Aplicar estilos corporativos
apply_buchi_styles()

# Verificación de autenticación
if not check_password():
    st.stop()

# ============================================================================
# FUNCIÓN PARA RENDERIZAR CARRUSEL BOOTSTRAP
# ============================================================================
def render_carousel(title, subtitle, items, carousel_id):
    """
    Renderiza un carrusel Bootstrap completamente funcional
    
    Args:
        title: Título de la sección
        subtitle: Subtítulo de la sección
        items: Lista de diccionarios con tool configs
        carousel_id: ID único para el carrusel
    """
    
    # Construir slides del carrusel
    slides_html = ""
    for idx, tool in enumerate(items):
        features_html = ''.join([f'<li>{f}</li>' for f in tool['features']])
        active_class = "active" if idx == 0 else ""
        
        slides_html += f"""
        <div class="carousel-item {active_class}">
            <div class="d-flex justify-content-center">
                <div class="card tool-card {tool['card_class']}">
                    <div class="card-body">
                        <h5 class="card-title">{tool['title']}</h5>
                        <p class="card-text">{tool['description']}</p>
                        <ul class="card-features">
                            {features_html}
                        </ul>
                    </div>
                </div>
            </div>
        </div>
        """
    
    # HTML completo autocontenido
    html_content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            {CAROUSEL_CSS}
        </style>
    </head>
    <body>
        <h3 class="section-header">{title}</h3>
        
        <div id="{carousel_id}" class="carousel slide" data-bs-ride="false">
            <div class="carousel-indicators">
                {' '.join([f'<button type="button" data-bs-target="#{carousel_id}" data-bs-slide-to="{i}" {"class=active" if i==0 else ""}></button>' for i in range(len(items))])}
            </div>
            
            <div class="carousel-inner">
                {slides_html}
            </div>
            
            <button class="carousel-control-prev" type="button" data-bs-target="#{carousel_id}" data-bs-slide="prev">
                <span class="carousel-control-prev-icon"></span>
            </button>
            <button class="carousel-control-next" type="button" data-bs-target="#{carousel_id}" data-bs-slide="next">
                <span class="carousel-control-next-icon"></span>
            </button>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """
    
    components.html(html_content, height=480, scrolling=False)

# ============================================================================
# PÁGINA HOME
# ============================================================================

st.title(HOME_PAGE['title'])
st.markdown(f"### {HOME_PAGE['subtitle']}")

st.divider()

st.markdown(HOME_PAGE['description'])

st.divider()

# ============================================================================
# CARRUSELES LADO A LADO
# ============================================================================

# Crear dos columnas para los carruseles
carousel_col1, carousel_col2 = st.columns(2)

# COLUMNA 1: SERVICE TOOLS
with carousel_col1:
    service = HOME_PAGE['service_tools']
    
    service_items = [
        service['baseline'],
        service['validation'],
        service['offset']
    ]
    
    render_carousel(
        title=service['section_title'],
        subtitle=service['section_subtitle'],
        items=service_items,
        carousel_id="carouselService"
    )

# COLUMNA 2: APPLICATION TOOLS
with carousel_col2:
    apps = HOME_PAGE['application_tools']
    
    app_items = [
        apps['spectrum'],
        apps['predictions'],
        apps['metareports'],
        apps['tsv_validation']
    ]
    
    render_carousel(
        title=apps['section_title'],
        subtitle=apps['section_subtitle'],
        items=app_items,
        carousel_id="carouselApps"
    )

st.divider()

# ============================================================================
# WORKFLOW & FOOTER
# ============================================================================

st.markdown(f"### {HOME_PAGE['workflow']['title']}")
st.markdown(HOME_PAGE['workflow']['content'])

st.divider()

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