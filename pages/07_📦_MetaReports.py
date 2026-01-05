"""
COREF Suite - NIR Maintenance Consolidator
Consolida informes de Baseline Adjustment, Validación Óptica y Predicciones
"""
import streamlit as st
from datetime import datetime
import sys
from pathlib import Path
import pandas as pd

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
            
            info['sensor_id'] = (baseline_info.get('N/S Sensor', '') or 
                                baseline_info.get('N/S sensor', '') or
                                baseline_info.get('N/S del Sensor', '') or
                                baseline_info.get('ID del Sensor', '') or
                                baseline_info.get('Sensor ID', '') or
                                baseline_info.get('Número de Serie', ''))
            
            info['fecha'] = (baseline_info.get('Fecha del Proceso', '') or
                           baseline_info.get('Fecha del Informe', '') or 
                           baseline_info.get('Fecha', '') or
                           baseline_info.get('Fecha del Servicio', ''))
            
            if info['fecha'] and ' ' in info['fecha']:
                info['fecha'] = info['fecha'].split(' ')[0]
            
            info['tecnico'] = (baseline_info.get('Técnico', '') or 
                             baseline_info.get('Técnico Responsable', ''))
            
            info['cliente'] = (baseline_info.get('Cliente', '') or 
                             baseline_info.get('Empresa', ''))
            
            info['ubicacion'] = baseline_info.get('Ubicación', '')
            
            info['modelo'] = (baseline_info.get('Modelo', '') or 
                            baseline_info.get('Modelo del Equipo', ''))
            
        except Exception as e:
            print(f"Error parsing baseline: {e}")
    
    # Si falta info, intentar con validación
    if validation_html:
        try:
            parser = ValidationParser(validation_html)
            parser.parse()
            val_info = parser.data.get('info_servicio', {})
            
            if not info['sensor_id']:
                info['sensor_id'] = (val_info.get('N/S Sensor', '') or
                                   val_info.get('N/S sensor', '') or
                                   val_info.get('ID del Sensor', '') or 
                                   val_info.get('Sensor ID', ''))
            if not info['fecha']:
                info['fecha'] = (val_info.get('Fecha del Proceso', '') or
                               val_info.get('Fecha del Informe', '') or 
                               val_info.get('Fecha', ''))
                if info['fecha'] and ' ' in info['fecha']:
                    info['fecha'] = info['fecha'].split(' ')[0]
                    
            if not info['cliente']:
                info['cliente'] = val_info.get('Cliente', '')
            if not info['modelo']:
                info['modelo'] = (val_info.get('Modelo del Equipo', '') or 
                                val_info.get('Modelo', ''))
            if not info['tecnico']:
                info['tecnico'] = val_info.get('Técnico', '')
            if not info['ubicacion']:
                info['ubicacion'] = val_info.get('Ubicación', '')
                
        except Exception as e:
            print(f"Error parsing validation: {e}")
    
    # Si aún falta info, intentar con predicciones
    if predictions_html:
        try:
            parser = PredictionsParser(predictions_html)
            parser.parse()
            pred_info = parser.data.get('info_general', {})
            
            if not info['sensor_id']:
                info['sensor_id'] = (pred_info.get('N/S Sensor', '') or
                                   pred_info.get('N/S sensor', '') or
                                   pred_info.get('Sensor NIR', '') or 
                                   pred_info.get('ID del Sensor', ''))
            if not info['fecha']:
                info['fecha'] = (pred_info.get('Fecha del Proceso', '') or
                               pred_info.get('Fecha del Reporte', '') or 
                               pred_info.get('Fecha', ''))
                if info['fecha'] and ' ' in info['fecha']:
                    info['fecha'] = info['fecha'].split(' ')[0]
                    
            if not info['cliente']:
                info['cliente'] = pred_info.get('Cliente', '')
            
            # ⭐ EXTRAER LÁMPARAS DE PREDICTIONS
            lamparas = pred_info.get('Lámparas', [])
            if lamparas:
                if len(lamparas) >= 1 and not info['lampara_referencia']:
                    info['lampara_referencia'] = lamparas[0]
                if len(lamparas) >= 2 and not info['lampara_nueva']:
                    info['lampara_nueva'] = lamparas[1]
                
        except Exception as e:
            print(f"Error parsing predictions: {e}")
    
    # Si no hay fecha, usar fecha actual
    if not info['fecha']:
        info['fecha'] = datetime.now().strftime('%Y-%m-%d')
    
    return info


def show_baseline_preview(baseline_data: dict):
    """Muestra preview del baseline adjustment"""
    
    verificacion = baseline_data.get('verificacion', {})
    
    if verificacion.get('metricas'):
        st.markdown("**📊 Métricas de Verificación Post-Ajuste:**")
        
        # Mostrar métricas en columnas
        metric_cols = st.columns(len(verificacion['metricas']))
        for idx, (key, value) in enumerate(verificacion['metricas'].items()):
            with metric_cols[idx]:
                st.metric(key, value)
        
        st.markdown("---")
        
        estado = verificacion.get('estado', 'UNKNOWN')
        conclusion = verificacion.get('conclusion', '')
        
        status_map = {
            'EXCELENTE': ('success', '✅'),
            'BUENO': ('success', '✅'),
            'ACEPTABLE': ('warning', '⚠️'),
            'REQUIERE REVISIÓN': ('error', '❌'),
            'UNKNOWN': ('info', 'ℹ️')
        }
        
        status_type, icon = status_map.get(estado, ('info', 'ℹ️'))
        
        st.markdown(f"**Conclusión: {estado}**")
        if status_type == 'success':
            st.success(f"{icon} {conclusion}")
        elif status_type == 'warning':
            st.warning(f"{icon} {conclusion}")
        elif status_type == 'error':
            st.error(f"{icon} {conclusion}")
        else:
            st.info(f"{icon} {conclusion}")
    else:
        st.info("No hay datos de verificación disponibles")


def show_validation_preview(validation_data: dict):
    """Muestra preview de validación óptica"""
    
    # Resumen ejecutivo
    exec_summary = validation_data.get('resumen_ejecutivo', {})
    if exec_summary.get('metricas'):
        st.markdown("**📊 Resumen Ejecutivo:**")
        cols = st.columns(len(exec_summary['metricas']))
        for idx, (key, value) in enumerate(exec_summary['metricas'].items()):
            with cols[idx]:
                st.metric(key, value)
        
        st.markdown("---")
    
    # Criterios de validación
    criterios = validation_data.get('criterios_validacion', {})
    if criterios.get('criterios'):
        st.markdown("**📋 Criterios de Validación:**")
        
        criterios_data = []
        for criterio in criterios['criterios']:
            criterios_data.append({
                'Parámetro': criterio['parametro'],
                'Umbral': criterio['umbral'],
                'Descripción': criterio['descripcion']
            })
        
        df_criterios = pd.DataFrame(criterios_data)
        st.dataframe(df_criterios, use_container_width=True, hide_index=True)
        
        st.markdown("---")
    
    # Estadísticas globales
    global_stats = validation_data.get('estadisticas_globales', {})
    if global_stats.get('metricas_agregadas'):
        st.markdown("**📊 Estadísticas Globales:**")
        
        stats_data = []
        for metric_data in global_stats.get('metricas_agregadas', []):
            stats_data.append({
                'Métrica': metric_data['metrica'],
                'Mínimo': metric_data['minimo'],
                'Máximo': metric_data['maximo'],
                'Media': metric_data['media'],
                'Desv. Est.': metric_data['desv_est']
            })
        
        df_stats = pd.DataFrame(stats_data)
        st.dataframe(df_stats, use_container_width=True, hide_index=True)
        
        st.markdown("---")
    
    # Resultados detallados
    detailed = validation_data.get('resultados_detallados', [])
    if detailed:
        st.markdown("**🔬 Resultados por Estándar:**")
        
        df_data = []
        for result in detailed:
            status_icon = {
                'ok': '✅',
                'warning': '⚠️',
                'fail': '❌'
            }.get(result['estado'].lower(), 'ℹ️')
            
            df_data.append({
                'Estándar': result['estandar'],
                'Correlación': result['correlacion'],
                'Max Δ': result['max_diff'],
                'RMS': result['rms'],
                'Estado': f"{status_icon} {result['estado']}"
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True, hide_index=True)


def show_predictions_preview(predictions_data: dict):
    """Muestra preview de predicciones"""
    
    info_general = predictions_data.get('info_general', {})
    
    st.markdown("**📊 Información General:**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Sensor NIR", info_general.get('Sensor NIR', 'N/A'))
        st.metric("Fecha", info_general.get('Fecha del Reporte', 'N/A'))
    
    with col2:
        productos = info_general.get('Productos', [])
        lamparas = info_general.get('Lámparas', [])
        st.metric("Productos Analizados", len(productos))
        st.metric("Lámparas Comparadas", len(lamparas))
    
    st.markdown("---")
    
    # Mostrar listas
    col_list1, col_list2 = st.columns(2)
    
    with col_list1:
        if productos:
            st.markdown("**📦 Productos:**")
            for producto in productos:
                st.markdown(f"- {producto}")
    
    with col_list2:
        if lamparas:
            st.markdown("**💡 Lámparas:**")
            for lampara in lamparas:
                st.markdown(f"- {lampara}")


def show_reports_preview(baseline_html, validation_html, predictions_html):
    """Muestra preview consolidado de todos los informes en expandables"""
    st.markdown("---")
    st.markdown("### 📊 Vista Previa de Información Extraída")
    
    # Contar informes
    files_loaded = sum([
        baseline_html is not None,
        validation_html is not None,
        predictions_html is not None
    ])
    
    if files_loaded == 0:
        return
    
    # Parsear los informes
    baseline_data = None
    validation_data = None
    predictions_data = None
    
    try:
        if baseline_html:
            with st.spinner("Analizando Baseline..."):
                parser = BaselineParser(baseline_html)
                baseline_data = parser.parse()
        
        if validation_html:
            with st.spinner("Analizando Validación..."):
                parser = ValidationParser(validation_html)
                validation_data = parser.parse()
        
        if predictions_html:
            with st.spinner("Analizando Predicciones..."):
                parser = PredictionsParser(predictions_html)
                predictions_data = parser.parse()
    except Exception as e:
        st.error(f"Error al analizar informes: {e}")
        return
    
    # Mostrar cada informe en su propio expandable
    if baseline_data:
        with st.expander("📐 **Baseline Adjustment**", expanded=True):
            show_baseline_preview(baseline_data)
    
    if validation_data:
        with st.expander("✅ **Validación Óptica**", expanded=True):
            show_validation_preview(validation_data)
    
    if predictions_data:
        with st.expander("🔬 **Predicciones con Muestras Reales**", expanded=True):
            show_predictions_preview(predictions_data)


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
        2. Revisa la vista previa de información extraída
        3. Edita la información del servicio si es necesario
        4. Haz clic en "Generar Informe Consolidado"
        5. Descarga el informe final en formato HTML
        
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
    st.info("📌 Carga los informes de baseline adjustment, standards validation y predictions")
    
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
    
    # FORZAR re-extracción cuando cambian los archivos
    # Crear una clave única basada en los archivos cargados
    current_files_key = f"{baseline_file.name if baseline_file else ''}_" \
                       f"{validation_file.name if validation_file else ''}_" \
                       f"{predictions_file.name if predictions_file else ''}"
    
    # Si es la primera vez O los archivos han cambiado, extraer info
    if ('consolidator_files_key' not in st.session_state or 
        st.session_state.consolidator_files_key != current_files_key):
        
        with st.spinner("🔍 Extrayendo información de los archivos..."):
            st.session_state.consolidator_files_key = current_files_key
            st.session_state.consolidator_service_info = extract_service_info(
                baseline_html, validation_html, predictions_html
            )
        st.success("✅ Información extraída automáticamente")
    
    # 🆕 PREVIEW DE INFORMES
    show_reports_preview(baseline_html, validation_html, predictions_html)
    
    st.markdown("---")
    
    # Formulario editable de información de servicio
    st.markdown("### 📋 Información del Servicio")
    
    col_extract1, col_extract2 = st.columns([3, 1])
    with col_extract1:
        st.markdown("*Los datos se extraen automáticamente. Puedes editarlos antes de generar el consolidado.*")
    with col_extract2:
        if st.button("🔄 Re-extraer", help="Volver a extraer datos de los archivos"):
            with st.spinner("🔍 Re-extrayendo información..."):
                st.session_state.consolidator_service_info = extract_service_info(
                    baseline_html, validation_html, predictions_html
                )
            st.rerun()
    
    with st.form("service_info_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            sensor_id = st.text_input(
                "N/S Sensor",
                value=st.session_state.consolidator_service_info.get('sensor_id', ''),
                help="Número de serie del sensor NIR"
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