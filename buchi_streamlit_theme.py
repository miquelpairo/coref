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
           Fix global del icono roto 'keyboard_arrow_down'
           y sustitución por una flecha Unicode estable
        */

        /* Oculta el span interno donde Streamlit intenta renderizar Material Icons */
        div[data-testid="stExpander"] div[role="button"] span[data-testid="stIconMaterial"] {{
            display: none !important;
        }}

        /* Asegura layout razonable para el header del expander */
        div[data-testid="stExpander"] div[role="button"] {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        /* Inserta nuestra propia flecha al final del título del expander */
        div[data-testid="stExpander"] div[role="button"]::after {{
            content: "▾";
            font-size: 1rem;
            color: {BUCHI_COLORS['negro']};
            margin-left: auto;
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
