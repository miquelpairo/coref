"""
Configuración de estilos corporativos Buchi para Streamlit
Aplicar al inicio de tu app con: apply_buchi_styles()
"""

import streamlit as st

# Colores corporativos Buchi
BUCHI_COLORS = {
    'verde_principal': '#64B445',
    'azul_oscuro': '#4F719A',
    'turquesa_claro': '#4DB9D2',
    'verde_turquesa': '#289A93',
    'verde_oscuro': '#093A34',
    'naranja': '#E08B55',
    'blanco': '#FFFFFF',
    'negro': '#000000',
    'gris_claro': '#F8F9FA'
}

def apply_buchi_styles():
    """
    Aplica los estilos base corporativos de Buchi:
    - Fuente: Helvetica
    - Fondo: Blanco
    - Texto: Negro
    - Sidebar: Fondo verde oscuro (#093A34) con texto blanco
    - Parche: corrige icono roto de los expanders de Streamlit
    """
    st.markdown(f"""
        <style>
        /* ===== CONFIGURACIÓN GENERAL ===== */
        * {{
            font-family: Helvetica, Arial, sans-serif !important;
        }}
        
        .stApp {{
            background-color: {BUCHI_COLORS['blanco']};
            color: {BUCHI_COLORS['negro']};
        }}
        
        /* ===== TÍTULOS ===== */
        h1, h2, h3, h4, h5, h6 {{
            color: {BUCHI_COLORS['negro']} !important;
        }}
        
        /* ===== TEXTO GENERAL ===== */
        p, span, div, label {{
            color: {BUCHI_COLORS['negro']} !important;
        }}
        
        /* ===== SIDEBAR - VERDE OSCURO CON TEXTO BLANCO ===== */
        [data-testid="stSidebar"] {{
            background-color: {BUCHI_COLORS['verde_oscuro']} !important;
        }}
        
        /* Todo el texto de la sidebar en blanco */
        [data-testid="stSidebar"] *,
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] h4,
        [data-testid="stSidebar"] h5,
        [data-testid="stSidebar"] h6,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] div {{
            color: {BUCHI_COLORS['blanco']} !important;
        }}
        
        /* Labels de inputs en sidebar */
        [data-testid="stSidebar"] .stTextInput label,
        [data-testid="stSidebar"] .stNumberInput label,
        [data-testid="stSidebar"] .stSelectbox label,
        [data-testid="stSidebar"] .stMultiSelect label,
        [data-testid="stSidebar"] .stTextArea label {{
            color: {BUCHI_COLORS['blanco']} !important;
        }}
        
        /* ===== BOTONES ===== */
        /* Botones NORMALES - Verde oscuro con texto blanco */
        .stButton > button {{
            background-color: {BUCHI_COLORS['verde_oscuro']};
            color: {BUCHI_COLORS['blanco']};
            border: none;
            border-radius: 10px;
            padding: 10px 20px;
            font-weight: bold;
            transition: all 0.3s ease;
        }}

        .stButton > button:hover {{
            background-color: {BUCHI_COLORS['verde_turquesa']};
        }}

        .stButton > button * {{
            color: {BUCHI_COLORS['blanco']} !important;
        }}

        /* Botones PRIMARY (Guardar y Continuar, etc) - VERDE */
        .stButton > button[data-testid="stBaseButton-primary"],
        button[data-testid="stBaseButton-primary"],
        .stFormSubmitButton > button {{
            background-color: {BUCHI_COLORS['verde_principal']} !important;
            color: {BUCHI_COLORS['blanco']} !important;
            border: none !important;
        }}

        .stButton > button[data-testid="stBaseButton-primary"]:hover,
        .stFormSubmitButton > button:hover {{
            background-color: {BUCHI_COLORS['verde_turquesa']} !important;
        }}

        .stFormSubmitButton > button *,
        .stButton > button[data-testid="stBaseButton-primary"] *,
        button[data-testid="stBaseButton-primary"] * {{
            color: {BUCHI_COLORS['blanco']} !important;
        }}

        /* Botones SECONDARY en SIDEBAR (navegación pasos) - VERDE */
        [data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"] {{
            background-color: {BUCHI_COLORS['verde_principal']} !important;
            color: {BUCHI_COLORS['blanco']} !important;
            border: none !important;
            text-align: left !important;
        }}

        [data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"]:hover {{
            background-color: {BUCHI_COLORS['verde_turquesa']} !important;
        }}

        [data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"] * {{
            color: {BUCHI_COLORS['blanco']} !important;
        }}

        /* Botones SECONDARY en MAIN - Blanco con borde (GENÉRICO) */
        section[data-testid="stMain"] button[data-testid="stBaseButton-secondary"] {{
            background-color: {BUCHI_COLORS['blanco']} !important;
            color: {BUCHI_COLORS['negro']} !important;
            border: 2px solid {BUCHI_COLORS['verde_principal']} !important;
        }}

        section[data-testid="stMain"] button[data-testid="stBaseButton-secondary"]:hover {{
            background-color: {BUCHI_COLORS['gris_claro']} !important;
            border-color: {BUCHI_COLORS['verde_turquesa']} !important;
        }}

        section[data-testid="stMain"] button[data-testid="stBaseButton-secondary"] * {{
            color: {BUCHI_COLORS['negro']} !important;
        }}

        /* Botón Cerrar Sesión específico - sobrescribe secondary en main */
        section[data-testid="stMain"] .st-key-logout_btn button[data-testid="stBaseButton-secondary"] {{
            background-color: {BUCHI_COLORS['verde_oscuro']} !important;
            color: {BUCHI_COLORS['blanco']} !important;
            border: none !important;
        }}

        section[data-testid="stMain"] .st-key-logout_btn button[data-testid="stBaseButton-secondary"]:hover {{
            background-color: {BUCHI_COLORS['verde_turquesa']} !important;
        }}

        section[data-testid="stMain"] .st-key-logout_btn button[data-testid="stBaseButton-secondary"] * {{
            color: {BUCHI_COLORS['blanco']} !important;
        }}
        
        /* ===== INPUTS ===== */
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input,
        .stTextArea > div > div > textarea {{
            border-radius: 5px;
            border: 1px solid #ddd;
        }}
        
        /* ===== DATAFRAME ===== */
        .stDataFrame {{
            background-color: {BUCHI_COLORS['blanco']};
        }}
        
        /* ===== TABS ===== */
        .stTabs [data-baseweb="tab"] {{
            color: {BUCHI_COLORS['negro']};
        }}
        
        .stTabs [aria-selected="true"] {{
            background-color: {BUCHI_COLORS['verde_principal']};
            color: {BUCHI_COLORS['blanco']} !important;
        }}

        /* ===== EXPANDERS =====
           Parche global para ocultar 'keyboard_arrow_*'
           y dibujar una flecha consistente en local y en streamlit.io
        */

        /* --- CASO STREAMLIT CLOUD (usa <details><summary>...) --- */

        /* 1. Oculta el span con data-testid="stIconMaterial" dentro del summary */
        details > summary [data-testid="stIconMaterial"] {{
            display: none !important;
            visibility: hidden !important;
        }}

        /* 2. Ajusta el summary para posicionar nuestra flecha propia */
        details > summary {{
            position: relative !important;
            list-style: none !important; /* quita el triángulo por defecto de <summary> en algunos navegadores */
            padding-right: 2rem !important;
            cursor: pointer;
            display: flex !important;
            align-items: center !important;
            gap: 0.5rem !important;
            color: inherit !important;
        }}

        /* 3. Flecha cuando el expander está cerrado (details SIN open) */
        details:not([open]) > summary::after {{
            content: "▾";
            position: absolute;
            right: 0.75rem;
            top: 50%;
            transform: translateY(-50%);
            font-size: 1rem;
            font-weight: 400;
            color: {BUCHI_COLORS['negro']};
        }}

        /* 4. Flecha cuando está abierto (details[open]) */
        details[open] > summary::after {{
            content: "▴";
            position: absolute;
            right: 0.75rem;
            top: 50%;
            transform: translateY(-50%);
            font-size: 1rem;
            font-weight: 400;
            color: {BUCHI_COLORS['negro']};
        }}

        /* 5. Asegura que el texto del título siga visible
              (Streamlit mete el título dentro de <div data-testid="stMarkdownContainer"><p>...</p></div>)
              No lo tocamos de color para no pelear con tus overrides globales,
              pero garantizamos que no colapse por herencia de font-size:0 de reglas anteriores.
        */
        details > summary [data-testid="stMarkdownContainer"],
        details > summary [data-testid="stMarkdownContainer"] * {{
            font-size: inherit !important;
            line-height: inherit !important;
            color: inherit !important;
            visibility: visible !important;
            display: block !important;
        }}

        /* --- CASO LOCAL (usa div[data-testid="stExpander"] ... role="button") --- */

        /* Asegura layout tipo flex en local */
        div[data-testid="stExpander"] > div[role="button"] {{
            display: flex !important;
            align-items: center !important;
            position: relative !important;
            padding-right: 2rem !important;
            min-height: 2rem;
            line-height: 1.4;
            gap: 0.5rem !important;
            color: inherit !important;
        }}

        /* Oculta el span con el icono roto en local */
        div[data-testid="stExpander"] > div[role="button"] span[data-testid="stIconMaterial"] {{
            display: none !important;
            visibility: hidden !important;
        }}

        /* Evita que se vea texto como 'keyboard_arrow_down' en spans sueltos */
        div[data-testid="stExpander"] > div[role="button"] span {{
            font-size: 0 !important;
            line-height: 0 !important;
            color: transparent !important;
            width: 0 !important;
            height: 0 !important;
            overflow: hidden !important;
            display: inline-block !important;
        }}

        /* Rehabilita el texto bueno (el título) donde Streamlit lo pone normalmente */
        div[data-testid="stExpander"] > div[role="button"] p,
        div[data-testid="stExpander"] > div[role="button"] div[data-testid="stMarkdownContainer"],
        div[data-testid="stExpander"] > div[role="button"] div[data-testid="stMarkdownContainer"] * {{
            font-size: inherit !important;
            line-height: inherit !important;
            color: inherit !important;
            width: auto !important;
            height: auto !important;
            overflow: visible !important;
            display: inline-block !important;
            visibility: visible !important;
        }}

        /* Flecha custom en local (aria-expanded false/true) */
        div[data-testid="stExpander"] > div[role="button"][aria-expanded="false"]::after {{
            content: "▾";
            position: absolute;
            right: 0.75rem;
            top: 50%;
            transform: translateY(-50%);
            font-size: 1rem;
            font-weight: 400;
            color: {BUCHI_COLORS['negro']};
        }}

        div[data-testid="stExpander"] > div[role="button"][aria-expanded="true"]::after {{
            content: "▴";
            position: absolute;
            right: 0.75rem;
            top: 50%;
            transform: translateY(-50%);
            font-size: 1rem;
            font-weight: 400;
            color: {BUCHI_COLORS['negro']};
        }}




        </style>
    """, unsafe_allow_html=True)


def add_custom_css(custom_css):
    """
    Añade CSS personalizado adicional
    
    Args:
        custom_css: String con CSS adicional
    
    Ejemplo:
        add_custom_css('''
            h1 {
                color: red !important;
            }
        ''')
    """
    st.markdown(f"""
        <style>
        {custom_css}
        </style>
    """, unsafe_allow_html=True)


# ========================================
# EJEMPLO DE USO
# ========================================

if __name__ == "__main__":
    st.set_page_config(
        page_title="App Buchi",
        page_icon="🧪",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Aplicar estilos corporativos base
    apply_buchi_styles()
    
    # Sidebar
    with st.sidebar:
        st.title("🧪 COREF System")
        st.markdown("---")
        st.subheader("Configuración")
        
        sample_name = st.text_input("Nombre de muestra")
        analysis_type = st.selectbox(
            "Tipo de análisis",
            ["Kjeldahl", "Soxhlet", "Fibra"]
        )
        
        if st.button("Iniciar Análisis"):
            st.success("Análisis iniciado")
    
    # Main content
    st.title("Sistema de Análisis COREF")
    st.write("Bienvenido al sistema de análisis Buchi")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Muestras", "42")
    
    with col2:
        st.metric("Completados", "95%")
    
    with col3:
        st.metric("En proceso", "3")
    
    st.markdown("---")
    
    # Ejemplo de tabs
    tab1, tab2 = st.tabs(["📊 Datos", "📈 Gráficos"])
    
    with tab1:
        st.subheader("Datos de análisis")
        st.write("Aquí van tus datos...")
    
    with tab2:
        st.subheader("Gráficos")
        st.write("Aquí van tus gráficos...")
    
    # Ejemplo de personalización adicional
    st.markdown("---")
    st.subheader("💡 Para personalizar más estilos:")
    st.code("""
# Añadir estilos personalizados
add_custom_css('''
    h1 {
        border-left: 5px solid #64B445 !important;
        padding-left: 15px !important;
    }
''')
    """)
