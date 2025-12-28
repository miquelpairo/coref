"""
COREF Suite - NIR Maintenance Consolidator
Consolida informes de Baseline Adjustment, Validación Óptica y Predicciones
"""
import streamlit as st
from datetime import datetime
import sys
from pathlib import Path

# Añadir path de módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

from buchi_streamlit_theme import apply_buchi_styles
from modules.consolidator.parsers import BaselineParser, ValidationParser, PredictionsParser
from modules.consolidator import ReportConsolidatorV2
from auth import check_password
from ui.ui_helpers import show_success, show_info, show_error

# Aplicar estilos corporativos Buchi
apply_buchi_styles()

# VERIFICACIÓN DE AUTENTICACIÓN
if not check_password():
    st.stop()


def extract_service_info(baseline_html=None, validation_html=None, predictions_html=None):
    """Extrae información básica del servicio de los HTMLs"""
    info = {
        'sensor_id': '',
        'fecha': '',
        'tecnico': '',
        'cliente': '',
        'ubicacion': '',
        'modelo': '',
        'mantenimiento': False,
        'ajuste_baseline': False,
        'lampara_referencia': '',
        'lampara_nueva': '',
        'validacion_optica': False,
        'predicciones_muestras': False,
        'notas': ''
    }
    
    # Intentar extraer de baseline primero
    if baseline_html:
        try:
            parser = BaselineParser(baseline_html)
            parser.parse()
            baseline_info = parser.data.get('info_cliente', {})
            info['sensor_id'] = baseline_info.get('ID del Sensor', '')
            info['fecha'] = baseline_info.get('Fecha del Informe', '')
            info['tecnico'] = baseline_info.get('Técnico', '')
            info['cliente'] = baseline_info.get('Cliente', baseline_info.get('Empresa', ''))
            info['ubicacion'] = baseline_info.get('Ubicación', '')
            info['modelo'] = baseline_info.get('Modelo', '')
        except Exception:
            pass
    
    # Si falta info, intentar con validación
    if validation_html and not info['sensor_id']:
        try:
            parser = ValidationParser(validation_html)
            parser.parse()
            val_info = parser.data.get('info_servicio', {})
            if not info['sensor_id']:
                info['sensor_id'] = val_info.get('ID del Sensor', '')
            if not info['fecha']:
                info['fecha'] = val_info.get('Fecha del Informe', '')
            if not info['cliente']:
                info['cliente'] = val_info.get('Cliente', '')
            if not info['modelo']:
                info['modelo'] = val_info.get('Modelo del Equipo', '')
        except Exception:
            pass
    
    # Si aún falta info, intentar con predicciones
    if predictions_html and not info['sensor_id']:
        try:
            parser = PredictionsParser(predictions_html)
            parser.parse()
            pred_info = parser.data.get('info_general', {})
            if not info['sensor_id']:
                info['sensor_id'] = pred_info.get('Sensor NIR', '')
            if not info['fecha']:
                info['fecha'] = pred_info.get('Fecha del Reporte', '')
        except Exception:
            pass
    
    # Si no hay fecha, usar fecha actual
    if not info['fecha']:
        info['fecha'] = datetime.now().strftime('%Y-%m-%d')
    
    return info


def main():
    # Header
    st.title("📦 Report Consolidator")
    st.markdown("## Consolidación de Informes de Mantenimiento Preventivo")
    
    # Información de uso
    with st.expander("ℹ️ Instrucciones de Uso"):
        st.markdown("""
        ### Consolidador de Informes NIR
        
        Esta herramienta consolida hasta 3 tipos de informes en un único documento HTML:
        
        **Tipos de Informes:**
        1. 📊 **Baseline Adjustment** - Corrección de baseline
        2. ✅ **Validación Óptica** - Validación con kit óptico
        3. 🔬 **Predicciones** - Análisis comparativo de predicciones
        
        **Proceso:**
        1. Sube al menos 1 archivo HTML (puedes subir 2 o 3)
        2. Revisa y edita la información del servicio extraída automáticamente
        3. Haz clic en "Generar Informe Consolidado"
        4. Descarga el informe final en formato HTML
        
        **El informe consolidado incluye:**
        - ✅ Resumen ejecutivo con estado global
        - 📋 Información de servicio completa
        - 📄 HTMLs originales embebidos con todos los gráficos
        - 🗂️ Navegación lateral indexada
        - 🎨 Estilo corporativo BUCHI
        """)
    
    st.markdown("---")
    
    # Sección de carga de archivos
    st.markdown("### 📁 Carga de archivos")
    st.info(" Carga los informes de baseline adjustement, standards validation y predictions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="upload-section">', unsafe_allow_html=True)
        st.markdown("#### 📊 Baseline Adjustment")
        baseline_file = st.file_uploader(
            "Subir informe de Baseline",
            type=['html'],
            key='baseline',
            help="Informe generado por COREF Suite con la corrección de baseline"
        )
        if baseline_file:
            show_success("✅ Archivo cargado")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="upload-section">', unsafe_allow_html=True)
        st.markdown("#### ✅ Validación Óptica")
        validation_file = st.file_uploader(
            "Subir informe de Validación",
            type=['html'],
            key='validation',
            help="Informe de validación con standards ópticos"
        )
        if validation_file:
            show_success("✅ Archivo cargado")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="upload-section">', unsafe_allow_html=True)
        st.markdown("#### 🔬 Predicciones")
        predictions_file = st.file_uploader(
            "Subir informe de Predicciones",
            type=['html'],
            key='predictions',
            help="Informe comparativo de predicciones con muestras reales"
        )
        if predictions_file:
            show_success("✅ Archivo cargado")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Verificar que al menos un archivo está cargado
    files_loaded = sum([
        baseline_file is not None, 
        validation_file is not None, 
        predictions_file is not None
    ])
    
    if files_loaded == 0:
        show_info("📌 Por favor, sube al menos un informe para comenzar")
        return
    
    st.markdown("---")
    
    # Leer HTMLs
    baseline_html = baseline_file.read().decode('utf-8') if baseline_file else None
    validation_html = validation_file.read().decode('utf-8') if validation_file else None
    predictions_html = predictions_file.read().decode('utf-8') if predictions_file else None
    
    # Extraer información de servicio automáticamente
    if 'consolidator_service_info' not in st.session_state:
        st.session_state.consolidator_service_info = extract_service_info(
            baseline_html, validation_html, predictions_html
        )
    
    # Formulario editable de información de servicio
    st.markdown("### 📋 Información del Servicio")
    st.markdown("*Los datos se extraen automáticamente de los informes. Puedes editarlos antes de generar el consolidado.*")
    
    with st.form("service_info_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            sensor_id = st.text_input(
                "ID del Sensor",
                value=st.session_state.consolidator_service_info.get('sensor_id', ''),
                help="Identificador único del sensor NIR"
            )
            fecha = st.text_input(
                "Fecha del Servicio",
                value=st.session_state.consolidator_service_info.get('fecha', ''),
                help="Fecha en formato YYYY-MM-DD"
            )
            tecnico = st.text_input(
                "Técnico Responsable",
                value=st.session_state.consolidator_service_info.get('tecnico', ''),
                help="Nombre del técnico que realizó el servicio"
            )
        
        with col2:
            cliente = st.text_input(
                "Cliente",
                value=st.session_state.consolidator_service_info.get('cliente', ''),
                help="Nombre del cliente o empresa"
            )
            ubicacion = st.text_input(
                "Ubicación",
                value=st.session_state.consolidator_service_info.get('ubicacion', ''),
                help="Ubicación del equipo"
            )
            modelo = st.text_input(
                "Modelo del Equipo",
                value=st.session_state.consolidator_service_info.get('modelo', ''),
                help="Modelo del espectrómetro NIR"
            )
        
        # Contexto del Mantenimiento
        st.markdown("---")
        st.markdown("#### 🔧 Contexto del Mantenimiento")
        
        col_ctx1, col_ctx2 = st.columns(2)
        
        with col_ctx1:
            mantenimiento = st.checkbox(
                "Mantenimiento",
                value=st.session_state.consolidator_service_info.get('mantenimiento', False),
                help="¿Se realizó mantenimiento preventivo/correctivo?"
            )
            
            ajuste_baseline = st.checkbox(
                "Ajuste Baseline a 0",
                value=st.session_state.consolidator_service_info.get('ajuste_baseline', False),
                help="¿Se realizó ajuste de baseline a cero?"
            )
            
            validacion_optica = st.checkbox(
                "Validación Estándares Ópticos",
                value=st.session_state.consolidator_service_info.get('validacion_optica', False),
                help="¿Se validó con estándares ópticos?"
            )
        
        with col_ctx2:
            predicciones_muestras = st.checkbox(
                "Predicciones de Muestras",
                value=st.session_state.consolidator_service_info.get('predicciones_muestras', False),
                help="¿Se realizaron predicciones con muestras reales?"
            )
            
            lampara_referencia = st.text_input(
                "Lámpara de Referencia",
                value=st.session_state.consolidator_service_info.get('lampara_referencia', ''),
                help="Identificación de la lámpara de referencia"
            )
            
            lampara_nueva = st.text_input(
                "Lámpara Nueva",
                value=st.session_state.consolidator_service_info.get('lampara_nueva', ''),
                help="Identificación de la lámpara nueva instalada"
            )
        
        st.markdown("---")
        
        notas = st.text_area(
            "Notas Adicionales",
            value=st.session_state.consolidator_service_info.get('notas', ''),
            height=80,
            help="Observaciones, comentarios o información adicional"
        )
        
        # Botón para actualizar info
        update_info = st.form_submit_button("💾 Actualizar Información", use_container_width=True)
        
        if update_info:
            st.session_state.consolidator_service_info = {
                'sensor_id': sensor_id,
                'fecha': fecha,
                'tecnico': tecnico,
                'cliente': cliente,
                'ubicacion': ubicacion,
                'modelo': modelo,
                'mantenimiento': mantenimiento,
                'ajuste_baseline': ajuste_baseline,
                'lampara_referencia': lampara_referencia,
                'lampara_nueva': lampara_nueva,
                'validacion_optica': validacion_optica,
                'predicciones_muestras': predicciones_muestras,
                'notas': notas
            }
            st.success("✅ Información actualizada")
    
    st.markdown("---")
    
    # Mostrar resumen de archivos cargados
    st.markdown("### 📋 Archivos Cargados")
    summary_cols = st.columns(3)
    
    with summary_cols[0]:
        if baseline_file:
            st.metric("Baseline Adjustment", "✅ Cargado")
        else:
            st.metric("Baseline Adjustment", "⚪ No cargado")
    
    with summary_cols[1]:
        if validation_file:
            st.metric("Validación Óptica", "✅ Cargado")
        else:
            st.metric("Validación Óptica", "⚪ No cargado")
    
    with summary_cols[2]:
        if predictions_file:
            st.metric("Predicciones", "✅ Cargado")
        else:
            st.metric("Predicciones", "⚪ No cargado")
    
    st.markdown("---")
    
    # Botón de generación centrado
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
        if st.button("📥 Generar Informe Consolidado", type="primary", use_container_width=True, key="generate_consolidated_btn"):
            generate_consolidated_report(
                baseline_html, 
                validation_html, 
                predictions_html,
                st.session_state.consolidator_service_info
            )


def generate_consolidated_report(baseline_html, validation_html, predictions_html, service_info):
    """Genera el informe consolidado usando ReportConsolidatorV2"""
    
    with st.spinner("🔄 Procesando informes..."):
        try:
            # Crear consolidador
            consolidator = ReportConsolidatorV2()
            consolidator.set_service_info(service_info)
            
            # Parsear y añadir baseline
            if baseline_html:
                with st.spinner("📊 Procesando Baseline Adjustment..."):
                    parser = BaselineParser(baseline_html)
                    baseline_data = parser.parse()
                    consolidator.add_baseline(baseline_data, baseline_html)
                    st.success("✅ Baseline procesado")
            
            # Parsear y añadir validación
            if validation_html:
                with st.spinner("✅ Procesando Validación Óptica..."):
                    parser = ValidationParser(validation_html)
                    validation_data = parser.parse()
                    consolidator.add_validation(validation_data, validation_html)
                    st.success("✅ Validación procesada")
            
            # Parsear y añadir predicciones
            if predictions_html:
                with st.spinner("🔬 Procesando Predicciones..."):
                    parser = PredictionsParser(predictions_html)
                    predictions_data = parser.parse()
                    consolidator.add_predictions(predictions_data, predictions_html)
                    st.success("✅ Predicciones procesadas")
            
            # Generar HTML consolidado
            with st.spinner("📝 Generando informe consolidado..."):
                consolidated_html = consolidator.generate_html()
            
            st.success("🎉 ¡Informe consolidado generado exitosamente!")
            
            # Determinar estado global
            status = consolidator._determine_global_status()
            
            # Mostrar preview del estado
            st.markdown("---")
            st.markdown("### 📊 Resumen del Informe")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Sensor ID", service_info['sensor_id'] or "N/A")
            with col2:
                status_emoji = {
                    'OK': '✅',
                    'WARNING': '⚠️',
                    'FAIL': '❌',
                    'UNKNOWN': 'ℹ️'
                }
                st.metric("Estado Global", f"{status_emoji.get(status, 'ℹ️')} {status}")
            
            # Botón de descarga
            st.markdown("---")
            st.markdown("### 💾 Descargar Informe")
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            sensor_id = service_info['sensor_id'] or "NIR"
            filename = f"METAREPORT_{sensor_id}_{timestamp}.html"
            
            st.download_button(
                label="📥 Descargar Informe Consolidado (HTML)",
                data=consolidated_html,
                file_name=filename,
                mime="text/html",
                use_container_width=True
            )
            
            show_info("✨ El informe HTML está listo para descargar. Incluye todos los informes originales completos con gráficos, navegación lateral y formato corporativo BUCHI.")
            
        except Exception as e:
            show_error(f"Error al generar el informe: {str(e)}")
            st.exception(e)


if __name__ == "__main__":
    # Inicializar session state
    if 'consolidator_service_info' not in st.session_state:
        st.session_state.consolidator_service_info = {
            'sensor_id': '',
            'fecha': '',
            'tecnico': '',
            'cliente': '',
            'ubicacion': '',
            'modelo': '',
            'mantenimiento': False,
            'ajuste_baseline': False,
            'lampara_referencia': '',
            'lampara_nueva': '',
            'validacion_optica': False,
            'predicciones_muestras': False,
            'notas': ''
        }
    
    main()