"""
COREF Suite - Prediction Reports
Análisis comparativo de predicciones NIR entre diferentes lámparas
"""

import streamlit as st
import sys
from pathlib import Path


# Añadir el directorio raíz al path
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
    
from utils.nir_analyzer import NIRAnalyzer, get_params_in_original_order
from utils.prediction_charts import (
    create_comparison_plots,
    create_detailed_comparison,
    create_box_plots,
)
from utils.prediction_reports import generate_html_report
from datetime import datetime
from buchi_streamlit_theme import apply_buchi_styles
from auth import check_password

# Aplicar estilos corporativos Buchi
apply_buchi_styles()

st.title("📊 Prediction Reports")
st.markdown("## Análisis comparativo de predicciones NIR entre diferentes lámparas")

# VERIFICACIÓN DE AUTENTICACIÓN
if not check_password():
    st.stop()

# Información de uso
with st.expander("ℹ️ Instrucciones de Uso"):
    st.markdown("""
    ### Cómo usar Prediction Reports:
    
    **1. Cargar Archivo XML:**
    - Sube el archivo XML generado por NIR-Online
    - El sistema extraerá automáticamente productos y lámparas
    
    **2. Seleccionar Datos:**
    - Elige los productos a analizar
    - Filtra por IDs y lámparas específicas
    - Genera el análisis estadístico
    
    **3. Explorar Resultados:**
    - **Comparación Detallada**: Medias por producto y parámetro
    - **Diferencias**: Cambios porcentuales respecto a baseline
    - **Box Plots**: Distribución completa de mediciones
    - **Reporte**: Informe completo en texto
    
    **4. Generar Reportes:**
    - Descarga el informe en formato TXT
    - Genera un reporte HTML interactivo con todos los gráficos
    
    **Formato del archivo:**
    - **Tipo**: XML de NIR-Online
    - **Estructura**: Múltiples worksheets (uno por producto)
    - **Columnas requeridas**: No, ID, Note, Product, Method, parámetros numéricos
    """)

st.markdown("---")

# Inicializar session state específico
if 'pred_analyzer' not in st.session_state:
    st.session_state.pred_analyzer = None
if 'pred_filtered_data' not in st.session_state:
    st.session_state.pred_filtered_data = None
if 'pred_stats' not in st.session_state:
    st.session_state.pred_stats = None

# ==============================================================================
# SECCIÓN 1: CARGA DE ARCHIVO
# ==============================================================================

st.markdown("### 📁 Carga de archivos")
st.info("Carga un archivo XML y genera el análisis para ver los resultados")

col1, col2 = st.columns([3, 1])

with col1:
    uploaded_file = st.file_uploader(
        "Sube el archivo XML de reporte NIR",
        type=['xml'],
        help="Archivo XML generado por el software NIR-Online",
        key='pred_xml_file'
    )

with col2:
    if uploaded_file is not None:
        if st.button("📊 Cargar y Analizar", key='load_pred_btn', type="primary"):
            with st.spinner("Procesando archivo XML..."):
                analyzer = NIRAnalyzer()
                if analyzer.parse_xml(uploaded_file):
                    st.session_state.pred_analyzer = analyzer
                    st.success(f"✅ Archivo cargado correctamente!")

# Mostrar información del analyzer si está cargado
if st.session_state.pred_analyzer is not None:
    analyzer = st.session_state.pred_analyzer
    
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"📦 Productos encontrados: **{len(analyzer.products)}**")
    with col2:
        if analyzer.sensor_serial:
            st.info(f"🔬 Sensor NIR: **{analyzer.sensor_serial}**")

# ==============================================================================
# SECCIÓN 2: SELECCIÓN DE DATOS
# ==============================================================================

if st.session_state.pred_analyzer is not None:
    analyzer = st.session_state.pred_analyzer
    
    st.markdown("---")
    st.info("2. Selección de datos para análisis")
    
    # Selección de productos
    selected_products = st.multiselect(
        "Productos a analizar:",
        analyzer.products,
        default=analyzer.products,
        key='pred_products',
        help="Selecciona los productos que quieres incluir en el análisis"
    )
    
    if selected_products:
        # Obtener IDs y Notes únicos
        all_ids = set()
        all_notes = set()
        
        for product in selected_products:
            if product in analyzer.data:
                df = analyzer.data[product]
                all_ids.update(df['ID'].dropna().unique())
                all_notes.update(df['Note'].dropna().unique())
        
        all_ids = sorted(list(all_ids))
        all_notes = sorted(list(all_notes))
        
        st.markdown("#### Filtros de selección")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info(f"💡 **{len(all_ids)}** IDs disponibles")
            selected_ids = st.multiselect(
                "IDs:",
                all_ids,
                default=all_ids,
                key='pred_ids',
                help="Filtra por IDs específicos"
            )
        
        with col2:
            st.info(f"💡 **{len(all_notes)}** Lámparas disponibles")
            selected_notes = st.multiselect(
                "Lámparas (Notes):",
                all_notes,
                default=all_notes,
                key='pred_notes',
                help="Selecciona las lámparas a comparar"
            )
        
        # Crear combinaciones
        selected_combinations = [(id_val, note_val) 
                                for id_val in selected_ids 
                                for note_val in selected_notes]
        
        if selected_combinations:
            if st.button("🚀 Generar Análisis Completo", type="primary", key='generate_pred'):
                with st.spinner("Generando análisis estadístico..."):
                    filtered_data = analyzer.filter_data(selected_products, selected_combinations)
                    st.session_state.pred_filtered_data = filtered_data
                    
                    stats = analyzer.calculate_statistics(filtered_data)
                    st.session_state.pred_stats = stats
                    
                    st.success("✅ Análisis completado correctamente!")
                    
                    # Mostrar resumen
                    total_samples = sum(len(df) for df in filtered_data.values())
                    st.info(f"📊 **{total_samples}** muestras analizadas en **{len(filtered_data)}** productos")

# ==============================================================================
# SECCIÓN 3: VISUALIZACIÓN DE RESULTADOS
# ==============================================================================

if st.session_state.pred_stats is not None:
    stats = st.session_state.pred_stats
    analyzer = st.session_state.pred_analyzer
    
    # Obtener lámparas seleccionadas
    all_lamps = set()
    for product_stats in stats.values():
        all_lamps.update(product_stats.keys())
    all_lamps = sorted(list(all_lamps))
    
    if all_lamps:
        st.info(f"🔬 **Lámparas en análisis:** {', '.join(all_lamps)}")
    
    st.markdown("---")
    st.markdown("## 📊 Resultados del Análisis")
    
    # Tabs para diferentes visualizaciones
    tab1, tab2, tab3 = st.tabs([
        "📊 Comparación Detallada",
        "📈 Diferencias entre Lámparas",
        "📦 Box Plots",
    ])
    
    with tab1:
        st.subheader("Comparación Detallada por Producto y Parámetro")
        st.markdown("Visualización de medias y variabilidad para cada parámetro analítico")
        
        params = get_params_in_original_order(analyzer, list(stats.keys()))
        
        if params:
            selected_param = st.selectbox(
                "Selecciona el parámetro a visualizar:",
                params,
                key='detailed_param',
                help="Parámetro analítico a comparar entre lámparas"
            )
            
            fig_detailed = create_detailed_comparison(stats, selected_param)
            if fig_detailed:
                st.plotly_chart(fig_detailed, use_container_width=True)
        else:
            st.warning("No hay parámetros disponibles para visualizar")
    
    with tab2:
        st.subheader("Diferencias Relativas entre Lámparas")
        st.markdown("Análisis de diferencias porcentuales respecto a la lámpara baseline")
        
        fig_diff = create_comparison_plots(stats, analyzer)
        if fig_diff:
            st.plotly_chart(fig_diff, use_container_width=True)
    
    with tab3:
        st.subheader("Distribución de Valores por Lámpara")
        st.markdown("Box plots mostrando la distribución completa de mediciones")
        
        fig_box = create_box_plots(stats, analyzer)
        if fig_box:
            st.plotly_chart(fig_box, use_container_width=True)
    
  
    # ==============================================================================
    # SECCIÓN 4: GENERACIÓN DE INFORME HTML
    # ==============================================================================
    
    st.markdown("---")
    st.markdown("### 📥 Generar Informe HTML Completo")
    st.info("""
    Completa la información del servicio para generar un informe HTML profesional 
    con todos los gráficos y análisis estadísticos.
    """)
    
    st.markdown("#### 📋 Información del Servicio")
    
    col1, col2 = st.columns(2)
    
    with col1:
        sensor_serial_input = st.text_input(
            "Número de Serie del Sensor:",
            value=analyzer.sensor_serial if analyzer.sensor_serial else "",
            placeholder="Ej: NIR-2024-001",
            help="Número de serie único del equipo NIR",
            key="sensor_serial_input"
        )
        
        customer_name = st.text_input(
            "Cliente:",
            placeholder="Ej: Universidad de Barcelona",
            help="Nombre del cliente o institución",
            key="customer_name_input"
        )
    
    with col2:
        technician_name = st.text_input(
            "Técnico Responsable:",
            placeholder="Ej: Juan Pérez",
            help="Nombre del técnico que realizó el análisis",
            key="technician_name_input"
        )
        
        service_notes = st.text_area(
            "Notas del Análisis:",
            placeholder="Ej: Comparación de lámparas halógenas para validación de calibración...",
            help="Observaciones relevantes del análisis realizado",
            height=100,
            key="service_notes_input"
        )
    
    st.markdown("---")
    
    # Botón de generación centrado
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("📥 Generar Informe HTML", type="primary", use_container_width=True, key="generate_report_btn"):
            if not sensor_serial_input or not customer_name or not technician_name:
                st.error("❌ Por favor completa los campos obligatorios: Número de Serie, Cliente y Técnico")
            else:
                with st.spinner("⏳ Generando informe completo..."):
                    try:
                        # Generar nombre del archivo
                        lamps_str = "_".join(all_lamps[:3])
                        if len(all_lamps) > 3:
                            lamps_str += f"_and_{len(all_lamps)-3}_more"
                        
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"PREDICTIONS_REPORT_{sensor_serial_input.replace(' ', '_')}_{lamps_str}_{timestamp}.html"
                        
                        # Actualizar sensor_serial en analyzer si se proporcionó
                        if sensor_serial_input:
                            analyzer.sensor_serial = sensor_serial_input
                        
                        html_content = generate_html_report(stats, analyzer, filename)
                        
                        st.success("✅ Informe generado correctamente")
                        
                        st.download_button(
                            label="💾 Descargar Informe HTML",
                            data=html_content,
                            file_name=filename,
                            mime="text/html",
                            use_container_width=True,
                            key='download_html_final'
                        )
                        
                    except Exception as e:
                        st.error(f"❌ Error al generar informe: {str(e)}")
                        with st.expander("🔍 Ver detalles del error"):
                            import traceback
                            st.code(traceback.format_exc())

