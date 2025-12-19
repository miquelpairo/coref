"""
Consolidador de informes NIR - Versión 2.0 Híbrida
Combina parsing para resumen ejecutivo + HTML completo embebido
Parte del módulo COREF Suite
"""
from typing import Dict, Any, Optional
from datetime import datetime
import base64


class ReportConsolidatorV2:
    """
    Consolidador de informes de mantenimiento NIR
    Genera un informe HTML unificado con resúmenes parseados y HTMLs originales embebidos
    """
    
    def __init__(self):
        self.baseline_data = None
        self.baseline_html = None
        self.validation_data = None
        self.validation_html = None
        self.predictions_data = None
        self.predictions_html = None
        self.service_info = {}
        
    def add_baseline(self, data: Dict[str, Any], html: str):
        """Añade datos parseados y HTML completo del baseline"""
        self.baseline_data = data
        self.baseline_html = html
        
    def add_validation(self, data: Dict[str, Any], html: str):
        """Añade datos parseados y HTML completo de validación"""
        self.validation_data = data
        self.validation_html = html
        
    def add_predictions(self, data: Dict[str, Any], html: str):
        """Añade datos parseados y HTML completo de predicciones"""
        self.predictions_data = data
        self.predictions_html = html
    
    def set_service_info(self, service_info: Dict[str, str]):
        """Establece la información del servicio (editable por el usuario)"""
        self.service_info = service_info
    
    def generate_html(self) -> str:
        """Genera el HTML del informe consolidado"""
        sensor_id = self.service_info.get('sensor_id', 'N/A')
        
        # Construir índice dinámico
        index_items = self._generate_index()
        
        # Construir secciones colapsables con resumen parseado + iframe
        sections_html = []
        
        if self.baseline_html and self.baseline_data:
            sections_html.append(self._generate_collapsible_section(
                'baseline',
                '📐 Baseline Adjustment',
                self._generate_baseline_summary(),
                self.baseline_html
            ))
        
        if self.validation_html and self.validation_data:
            sections_html.append(self._generate_collapsible_section(
                'validation',
                '✅ Validación Óptica',
                self._generate_validation_summary(),
                self.validation_html
            ))
        
        if self.predictions_html and self.predictions_data:
            sections_html.append(self._generate_collapsible_section(
                'predictions',
                '🔬 Predicciones con Muestras Reales',
                self._generate_predictions_summary(),
                self.predictions_html
            ))
        
        # Ensamblar HTML completo
        html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Informe Consolidado - {sensor_id}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        {self._get_styles()}
    </style>
</head>
<body>
    <div class="sidebar">
        <h2>📋 Índice</h2>
        <ul>
            {index_items}
        </ul>
    </div>
    
    <div class="main-content">
        {self._generate_header()}
        
        {''.join(sections_html)}
        
        {self._generate_footer()}
    </div>
</body>
</html>
"""
        return html
    
    def _generate_header(self) -> str:
        """Genera el header con información del servicio y descripciones"""
        # Construir tabla de información en formato 2 columnas
        sensor_id = self.service_info.get('sensor_id', 'N/A')
        fecha = self.service_info.get('fecha', 'N/A')
        cliente = self.service_info.get('cliente', 'N/A')
        tecnico = self.service_info.get('tecnico', 'N/A')
        ubicacion = self.service_info.get('ubicacion', 'N/A')
        modelo = self.service_info.get('modelo', 'N/A')
        
        # Campos estructurados
        mantenimiento = self.service_info.get('mantenimiento', False)
        ajuste_baseline = self.service_info.get('ajuste_baseline', False)
        lampara_referencia = self.service_info.get('lampara_referencia', '')
        lampara_nueva = self.service_info.get('lampara_nueva', '')
        validacion_optica = self.service_info.get('validacion_optica', False)
        predicciones_muestras = self.service_info.get('predicciones_muestras', False)
        notas = self.service_info.get('notas', '')
        
        info_table = f"""
        <div style="margin-top: 20px;">
            <h3 style="margin-top: 0;">Información del Servicio</h3>
            <table style="width: 100%; margin-top: 15px;">
                <tr>
                    <td style="width: 150px;"><strong>ID del Sensor</strong></td>
                    <td style="width: 35%;">{sensor_id}</td>
                    <td style="width: 150px;"><strong>Cliente</strong></td>
                    <td>{cliente}</td>
                </tr>
                <tr>
                    <td><strong>Fecha</strong></td>
                    <td>{fecha}</td>
                    <td><strong>Técnico</strong></td>
                    <td>{tecnico}</td>
                </tr>
                <tr>
                    <td><strong>Ubicación</strong></td>
                    <td>{ubicacion}</td>
                    <td><strong>Modelo</strong></td>
                    <td>{modelo}</td>
                </tr>
            </table>
        </div>
        """
        
        # Sección de contexto del mantenimiento
        contexto_section = ""
        actividades = []
        if mantenimiento:
            actividades.append("✓ Mantenimiento preventivo/correctivo")
        if ajuste_baseline:
            actividades.append("✓ Ajuste de Baseline a 0")
        if validacion_optica:
            actividades.append("✓ Validación con Estándares Ópticos")
        if predicciones_muestras:
            actividades.append("✓ Predicciones con Muestras Reales")
        
        # Información de lámparas
        lamparas_info = ""
        if lampara_referencia or lampara_nueva:
            lamparas_rows = []
            if lampara_referencia:
                lamparas_rows.append(f"<tr><td><strong>Lámpara de Referencia</strong></td><td>{lampara_referencia}</td></tr>")
            if lampara_nueva:
                lamparas_rows.append(f"<tr><td><strong>Lámpara Nueva</strong></td><td>{lampara_nueva}</td></tr>")
            
            lamparas_info = f"""
            <table style="width: 100%; margin-top: 15px;">
                {''.join(lamparas_rows)}
            </table>
            """
        
        # Construir sección de contexto solo si hay información
        if actividades or lamparas_info:
            actividades_html = ""
            if actividades:
                actividades_list = ''.join([f"<li style='margin: 5px 0;'>{act}</li>" for act in actividades])
                actividades_html = f"""
                <div style="margin-bottom: 15px;">
                    <strong>Actividades Realizadas:</strong>
                    <ul style="margin-top: 10px; margin-bottom: 0;">
                        {actividades_list}
                    </ul>
                </div>
                """
            
            contexto_section = f"""
            <div style="margin-top: 20px; padding: 20px; background-color: #e3f2fd; border-left: 4px solid #2196f3; border-radius: 5px;">
                <h4 style="margin-top: 0;">🔧 Contexto del Mantenimiento</h4>
                {actividades_html}
                {lamparas_info}
            </div>
            """
        
        # Sección de notas
        notas_section = ""
        if notas:
            notas_section = f"""
            <div style="margin-top: 15px; padding: 15px; background-color: #fff3e0; border-left: 4px solid #ff9800; border-radius: 5px;">
                <strong>📝 Notas Adicionales:</strong> 
                <p style="margin: 10px 0 0 0; line-height: 1.6; white-space: pre-line;">{notas}</p>
            </div>
            """
        
        # Descripción detallada del informe (colapsable)
        descripcion = """
        <details open style="margin-top: 25px;">
            <summary style="cursor: pointer; padding: 20px; background-color: #ffffff; border-radius: 8px; border: 1px solid #dee2e6; list-style: none; user-select: none;">
                <span style="font-size: 1.2em; font-weight: bold; color: #000000;">📖 Acerca de Este Informe</span>
                <span style="float: right; color: #6c757d;">▶ Click para expandir</span>
            </summary>
            
            <div style="padding: 25px; background-color: #ffffff; border-radius: 0 0 8px 8px; border: 1px solid #dee2e6; border-top: none; margin-top: -1px;">
                <p style="line-height: 1.6; margin-bottom: 20px; color: #333;">
                    Este informe consolida los resultados de los procedimientos de mantenimiento preventivo y validación 
                    realizados en el espectrómetro NIR. Los procedimientos incluidos garantizan el correcto funcionamiento 
                    del equipo y la fiabilidad de las mediciones analíticas.
                </p>
                
                <div style="margin-top: 25px;">
                    <h4 style="color: #000000; margin-bottom: 15px;">🔧 Procedimientos Incluidos:</h4>
                    
                    <div style="margin-bottom: 20px; padding-left: 15px;">
                        <strong style="color: #64B445; font-size: 1.05em;">📐 Baseline Adjustment (Ajuste de Línea Base)</strong>
                        <p style="margin: 8px 0 0 20px; line-height: 1.6; color: #444;">
                            Procedimiento de corrección del baseline del espectrómetro tras el cambio de lámpara. 
                            Se utiliza el White Standard Reference (WSTD) para diagnosticar desviaciones y generar 
                            un archivo de corrección (COREF) que compensa las diferencias espectrales entre la lámpara 
                            anterior y la nueva. Este proceso asegura la continuidad de las calibraciones existentes 
                            sin necesidad de recalibrar.
                        </p>
                    </div>
                    
                    <div style="margin-bottom: 20px; padding-left: 15px;">
                        <strong style="color: #289A93; font-size: 1.05em;">✅ Validación con Standards Ópticos</strong>
                        <p style="margin: 8px 0 0 20px; line-height: 1.6; color: #444;">
                            Verificación de la alineación óptica del espectrómetro mediante un kit de standards certificados. 
                            Se evalúa la correlación espectral, diferencias máximas (Max Δ) y error cuadrático medio (RMS) 
                            entre mediciones de referencia y actuales. Este test confirma que el sistema óptico está 
                            correctamente alineado y que las mediciones son reproducibles y precisas.
                        </p>
                    </div>
                    
                    <div style="margin-bottom: 20px; padding-left: 15px;">
                        <strong style="color: #2196f3; font-size: 1.05em;">🔬 Predicciones con Muestras Reales</strong>
                        <p style="margin: 8px 0 0 20px; line-height: 1.6; color: #444;">
                            Análisis comparativo de predicciones realizadas con diferentes lámparas sobre muestras reales 
                            del proceso productivo. Se comparan los valores predichos para múltiples parámetros entre 
                            la lámpara de referencia y la nueva lámpara, validando que las calibraciones NIR siguen 
                            funcionando correctamente tras el mantenimiento.
                        </p>
                    </div>
                </div>
                
                <div style="margin-top: 25px; padding: 15px; background-color: #f8f9fa; border-radius: 5px; border: 1px solid #e9ecef;">
                    <p style="margin: 0; color: #6c757d; font-size: 0.95em; line-height: 1.5;">
                        <strong>💡 Cómo usar este informe:</strong> Cada sección puede expandirse para ver el resumen 
                        detallado con tablas y métricas clave. Los informes originales completos con todos los gráficos 
                        interactivos pueden abrirse en una nueva pestaña mediante el botón 
                        "📄 Abrir Informe Completo" disponible en cada sección.
                    </p>
                </div>
            </div>
        </details>
        
        <style>
        details[open] > summary span:last-child::before {
            content: "▼ ";
        }
        details > summary span:last-child::before {
            content: "▶ ";
        }
        details > summary::-webkit-details-marker {
            display: none;
        }
        </style>
        """
        
        return f"""
        <div style="background-color: #f8f9fa; padding: 30px; border-radius: 10px; margin-bottom: 30px; border: 1px solid #ddd;">
            <h1 style="margin: 0; color: #000000;">Informe Consolidado de Mantenimiento Preventivo NIR</h1>
            {info_table}
            {contexto_section}
            {notas_section}
        </div>
        {descripcion}
        """
    
    def _generate_executive_summary(self) -> str:
        """Genera el resumen ejecutivo usando datos parseados"""
        estado_global = self._determine_global_status()
        
        metrics_cards = []
        
        # Baseline
        if self.baseline_data:
            summary = self.baseline_data.get('summary', {})
            stats = self.baseline_data.get('estadisticas_correccion', {})
            offset = stats.get('Corrección Máxima', 'N/A')
            estado = summary.get('estado_global', 'N/A')
            
            metrics_cards.append(f"""
                <div class="metric-card info">
                    <div class="metric-label">Baseline Adjustment</div>
                    <div class="metric-value-small">{offset}</div>
                    <div class="metric-sublabel">Offset Global | Estado: {estado}</div>
                </div>
            """)
        
        # Validación
        if self.validation_data:
            exec_summary = self.validation_data.get('resumen_ejecutivo', {})
            metricas = exec_summary.get('metricas', {})
            total = metricas.get('Total Estándares', '0')
            validados = metricas.get('Validados', '0')
            revisar = metricas.get('Revisar', '0')
            fallidos = metricas.get('Fallidos', '0')
            
            card_class = 'ok' if fallidos == '0' else 'fail'
            
            metrics_cards.append(f"""
                <div class="metric-card {card_class}">
                    <div class="metric-label">Validación Óptica</div>
                    <div class="metric-value">{validados}/{total}</div>
                    <div class="metric-sublabel">Validados (⚠️{revisar} | ❌{fallidos})</div>
                </div>
            """)
        
        # Predicciones
        if self.predictions_data:
            info = self.predictions_data.get('info_general', {})
            productos = info.get('Productos Analizados', 'N/A')
            lamparas = info.get('Lámparas Comparadas', 'N/A')
            
            metrics_cards.append(f"""
                <div class="metric-card info">
                    <div class="metric-label">Predicciones</div>
                    <div class="metric-value">{productos}</div>
                    <div class="metric-sublabel">Productos ({lamparas} lámparas)</div>
                </div>
            """)
        
        status_class = {
            'OK': 'ok',
            'WARNING': 'warning',
            'FAIL': 'fail',
            'UNKNOWN': 'info'
        }.get(estado_global, 'info')
        
        status_icon = {
            'OK': '✅',
            'WARNING': '⚠️',
            'FAIL': '❌',
            'UNKNOWN': 'ℹ️'
        }.get(estado_global, 'ℹ️')
        
        status_text = {
            'OK': 'VALIDACIÓN EXITOSA',
            'WARNING': 'REVISAR RESULTADOS',
            'FAIL': 'VALIDACIÓN FALLIDA',
            'UNKNOWN': 'ESTADO DESCONOCIDO'
        }.get(estado_global, 'ESTADO DESCONOCIDO')
        
        return f"""
        <div class="info-box" id="resumen-ejecutivo">
            <h2>📊 Resumen Ejecutivo</h2>
            
            <div class="metrics-grid">
                <div class="metric-card total">
                    <div class="metric-value">{len([x for x in [self.baseline_data, self.validation_data, self.predictions_data] if x])}</div>
                    <div class="metric-label">Informes Consolidados</div>
                </div>
                {''.join(metrics_cards)}
            </div>
            
            <div class="info-box status-box-{status_class}" style="margin-top: 20px;">
                <h3>{status_icon} {status_text}</h3>
                <p>{self._get_status_description(estado_global)}</p>
            </div>
        </div>
        """
    
    def _determine_global_status(self) -> str:
        """Determina el estado global del servicio"""
        statuses = []
        
        if self.baseline_data:
            verification = self.baseline_data.get('verificacion', {})
            conclusion = verification.get('conclusion', '')
            if 'exitosa' in conclusion.lower():
                statuses.append('OK')
            else:
                statuses.append('WARNING')
        
        if self.validation_data:
            exec_summary = self.validation_data.get('resumen_ejecutivo', {})
            metricas = exec_summary.get('metricas', {})
            try:
                fallidos = int(metricas.get('Fallidos', '0'))
                revisar = int(metricas.get('Revisar', '0'))
                if fallidos > 0:
                    statuses.append('FAIL')
                elif revisar > 0:
                    statuses.append('WARNING')
                else:
                    statuses.append('OK')
            except:
                statuses.append('UNKNOWN')
        
        if self.predictions_data:
            statuses.append('OK')
        
        # Lógica de prioridad: FAIL > WARNING > OK
        if 'FAIL' in statuses:
            return 'FAIL'
        elif 'WARNING' in statuses:
            return 'WARNING'
        elif 'OK' in statuses:
            return 'OK'
        else:
            return 'UNKNOWN'
    
    def _get_status_description(self, status: str) -> str:
        """Obtiene descripción del estado global"""
        descriptions = {
            'OK': "Todos los procesos de validación han sido completados exitosamente. El equipo está correctamente alineado y listo para uso en producción.",
            'WARNING': "Algunos resultados requieren revisión. Consultar las secciones detalladas para más información.",
            'FAIL': "La validación ha fallado. El equipo requiere ajustes antes de ser utilizado en producción.",
            'UNKNOWN': "Estado de validación indeterminado. Revisar informes individuales."
        }
        return descriptions.get(status, "Estado desconocido")
    
    def _generate_baseline_summary(self) -> str:
        """Genera resumen parseado del baseline"""
        verificacion = self.baseline_data.get('verificacion', {})
        
        verif_html = ""
        if verificacion.get('metricas'):
            verif_rows = []
            for key, value in verificacion['metricas'].items():
                verif_rows.append(f"<tr><td><strong>{key}</strong></td><td>{value}</td></tr>")
            
            conclusion = verificacion.get('conclusion', '')
            estado = verificacion.get('estado', 'UNKNOWN')
            
            status_class_map = {
                'EXCELENTE': 'ok',
                'BUENO': 'ok',
                'ACEPTABLE': 'warning',
                'REQUIERE REVISIÓN': 'fail',
                'UNKNOWN': 'info'
            }
            status_class = status_class_map.get(estado, 'info')
            
            status_icon_map = {
                'EXCELENTE': '✅',
                'BUENO': '✅',
                'ACEPTABLE': '⚠️',
                'REQUIERE REVISIÓN': '❌',
                'UNKNOWN': 'ℹ️'
            }
            status_icon = status_icon_map.get(estado, 'ℹ️')
            
            verif_html = f"""
            <h3>📊 Métricas de Verificación Post-Ajuste</h3>
            <table>
                {''.join(verif_rows)}
            </table>
            
            <div class="info-box status-box-{status_class}" style="margin-top: 20px; padding: 15px; border-radius: 8px;">
                <h4 style="margin-top: 0;">{status_icon} Conclusión: {estado}</h4>
                <p style="margin: 10px 0 0 0; line-height: 1.6;">{conclusion}</p>
            </div>
            """
        else:
            verif_html = """
            <div class="info-box status-box-info" style="margin-top: 20px; padding: 15px;">
                <p><em>No hay datos de verificación disponibles en este reporte.</em></p>
            </div>
            """
        
        charts_note = """
        <div style="margin-top: 30px; padding: 15px; background-color: #e3f2fd; border-left: 4px solid #2196f3; border-radius: 5px;">
            <p style="margin: 0; color: #1976d2;">
                <strong>📈 Gráficos Interactivos:</strong> Para visualizar el overlay de espectros y la matriz RMS 
                de verificación, abra el informe completo usando el botón "📄 Abrir Informe Completo" más abajo.
            </p>
        </div>
        """
        
        return f"{verif_html}{charts_note}"
    
    def _generate_validation_summary(self) -> str:
        """Genera resumen parseado de validación"""
        criterios = self.validation_data.get('criterios_validacion', {})
        global_stats = self.validation_data.get('estadisticas_globales', {})
        detailed = self.validation_data.get('resultados_detallados', [])
        
        # Criterios de validación
        criterios_html = ""
        if criterios.get('criterios'):
            criterios_rows = []
            for criterio in criterios['criterios']:
                criterios_rows.append(f"""
                    <tr>
                        <td><strong>{criterio['parametro']}</strong></td>
                        <td>{criterio['umbral']}</td>
                        <td>{criterio['descripcion']}</td>
                    </tr>
                """)
            criterios_html = f"""
            <h3>📋 Criterios de Validación</h3>
            <p style='color: #6c757d; font-size: 0.95em;'>
                <em>Umbrales utilizados para evaluar la calidad óptica de cada estándar.</em>
            </p>
            <table>
                <tr>
                    <th>Parámetro</th>
                    <th>Umbral</th>
                    <th>Descripción</th>
                </tr>
                {''.join(criterios_rows)}
            </table>
            """
        
        # Estadísticas globales
        stats_html = ""
        if global_stats.get('metricas_agregadas'):
            stats_rows = []
            for metric_data in global_stats.get('metricas_agregadas', []):
                stats_rows.append(f"""
                    <tr>
                        <td><strong>{metric_data['metrica']}</strong></td>
                        <td>{metric_data['minimo']}</td>
                        <td>{metric_data['maximo']}</td>
                        <td>{metric_data['media']}</td>
                        <td>{metric_data['desv_est']}</td>
                    </tr>
                """)
            
            stats_html = f"""
            <h3 style="margin-top: 30px;">📊 Estadísticas Globales</h3>
            <p style='color: #6c757d; font-size: 0.95em;'>
                <em>Métricas agregadas de todos los estándares analizados.</em>
            </p>
            <table>
                <tr>
                    <th>Métrica</th>
                    <th>Mínimo</th>
                    <th>Máximo</th>
                    <th>Media</th>
                    <th>Desv. Est.</th>
                </tr>
                {''.join(stats_rows)}
            </table>
            """
        
        # Resultados detallados por estándar
        detail_html = ""
        if detailed:
            detail_rows = []
            for result in detailed:
                status_class = result['estado'].lower()
                status_icon = {
                    'ok': '✅',
                    'warning': '⚠️',
                    'fail': '❌'
                }.get(status_class, 'ℹ️')
                
                detail_rows.append(f"""
                    <tr>
                        <td><strong>{result['estandar']}</strong></td>
                        <td>{result.get('lampara_ref', 'N/A')}</td>
                        <td>{result.get('lampara_nueva', 'N/A')}</td>
                        <td>{result['correlacion']}</td>
                        <td>{result['max_diff']}</td>
                        <td>{result['rms']}</td>
                        <td>{status_icon} {result['estado']}</td>
                    </tr>
                """)
            
            detail_html = f"""
            <h3 style="margin-top: 30px;">🔬 Resultados por Estándar</h3>
            <p style='color: #6c757d; font-size: 0.95em;'>
                <em>Evaluación detallada de cada estándar óptico medido.</em>
            </p>
            <table>
                <tr>
                    <th>Estándar (ID)</th>
                    <th>Lámpara Ref.</th>
                    <th>Lámpara Nueva</th>
                    <th>Correlación</th>
                    <th>Max Δ (AU)</th>
                    <th>RMS</th>
                    <th>Estado</th>
                </tr>
                {''.join(detail_rows)}
            </table>
            """
        
        charts_note = """
        <div style="margin-top: 30px; padding: 15px; background-color: #e3f2fd; border-left: 4px solid #2196f3; border-radius: 5px;">
            <p style="margin: 0; color: #1976d2;">
                <strong>📈 Ver Análisis Completo:</strong> Para visualizar los gráficos de 
                correlación espectral, overlays y análisis detallado, abra el informe completo 
                usando el botón "📄 Abrir Informe Completo" más abajo.
            </p>
        </div>
        """
        
        return f"{criterios_html}{stats_html}{detail_html}{charts_note}"
    
    def _generate_predictions_summary(self) -> str:
        """Genera resumen parseado de predicciones"""
        info_general = self.predictions_data.get('info_general', {})
        
        lamparas_html = ""
        if info_general.get('Lámparas'):
            lamparas_list = info_general['Lámparas']
            lamparas_items = ''.join([f"<li>{lamp}</li>" for lamp in lamparas_list])
            lamparas_html = f"""
            <div style="margin-top: 15px;">
                <strong>Lámparas Comparadas:</strong>
                <ul style="margin-top: 10px;">
                    {lamparas_items}
                </ul>
            </div>
            """
        
        charts_note = """
        <div style="margin-top: 30px; padding: 15px; background-color: #e3f2fd; border-left: 4px solid #2196f3; border-radius: 5px;">
            <p style="margin: 0; color: #1976d2;">
                <strong>📈 Ver Análisis Completo:</strong> Para visualizar estadísticas detalladas, 
                gráficos comparativos y análisis de diferencias por producto, abra el informe completo 
                usando el botón "📄 Abrir Informe Completo" más abajo.
            </p>
        </div>
        """
        
        return f"""
            <h3>📊 Información General</h3>
            <p style='color: #6c757d; font-size: 0.95em;'>
                <em>Resumen del análisis de predicciones NIR entre diferentes lámparas.</em>
            </p>
            <table>
                <tr><td><strong>Sensor NIR</strong></td><td>{info_general.get('Sensor NIR', 'N/A')}</td></tr>
                <tr><td><strong>Fecha del Reporte</strong></td><td>{info_general.get('Fecha del Reporte', 'N/A')}</td></tr>
                <tr><td><strong>Productos Analizados</strong></td><td>{info_general.get('Productos Analizados', 'N/A')}</td></tr>
                <tr><td><strong>Lámparas Comparadas</strong></td><td>{info_general.get('Lámparas Comparadas', 'N/A')}</td></tr>
            </table>
            
            {lamparas_html}
            {charts_note}
        """
    
    def _generate_index(self) -> str:
        """Genera los items del índice lateral"""
        items = []
        
        if self.baseline_html:
            items.append('<li><a href="#baseline">📐 Baseline Adjustment</a></li>')
        
        if self.validation_html:
            items.append('<li><a href="#validation">✅ Validación Óptica</a></li>')
        
        if self.predictions_html:
            items.append('<li><a href="#predictions">🔬 Predicciones</a></li>')
        
        return '\n'.join(items)
    
    def _generate_collapsible_section(self, section_id: str, title: str, parsed_summary: str, html_content: str) -> str:
        """Genera una sección colapsable con resumen parseado + link a HTML completo"""
        # Inyectar script para arreglar navegación en Blob URLs
        sidebar_fix_script = """
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            const sidebarLinks = document.querySelectorAll('.sidebar a[href^="#"]');
            sidebarLinks.forEach(link => {
                link.addEventListener('click', function(e) {
                    e.preventDefault();
                    const targetId = this.getAttribute('href').substring(1);
                    const targetElement = document.getElementById(targetId);
                    if (targetElement) {
                        targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                });
            });
        });
        </script>
        """
        
        # Inyectar el script
        if '</body>' in html_content:
            html_modified = html_content.replace('</body>', sidebar_fix_script + '</body>')
        else:
            html_modified = html_content + sidebar_fix_script
        
        # Convertir HTML a base64
        html_bytes = html_modified.encode('utf-8')
        html_base64 = base64.b64encode(html_bytes).decode('ascii')
        
        # Generar ID único para el botón
        button_id = f"btn-{section_id}-{id(html_content) % 100000}"
        
        return f"""
        <div class="report-section" id="{section_id}">
            <details open>
                <summary class="section-header">
                    <h2>{title}</h2>
                </summary>
                
                <div class="parsed-content">
                    {parsed_summary}
                </div>
                
                <div class="full-report-link">
                    <button id="{button_id}" class="open-full-report-btn">
                        📄 Abrir Informe Completo en Nueva Pestaña
                    </button>
                    <p class="report-link-description">
                        Se abrirá el informe original completo con todos los gráficos interactivos y detalles.
                    </p>
                </div>
            </details>
        </div>
        
        <script>
        (function() {{
            const btn = document.getElementById('{button_id}');
            const htmlBase64 = '{html_base64}';
            
            btn.addEventListener('click', function() {{
                try {{
                    const binaryString = atob(htmlBase64);
                    const bytes = new Uint8Array(binaryString.length);
                    for (let i = 0; i < binaryString.length; i++) {{
                        bytes[i] = binaryString.charCodeAt(i);
                    }}
                    const htmlContent = new TextDecoder('utf-8').decode(bytes);
                    const blob = new Blob([htmlContent], {{ type: 'text/html;charset=utf-8' }});
                    const blobUrl = URL.createObjectURL(blob);
                    window.open(blobUrl, '_blank');
                    setTimeout(function() {{
                        URL.revokeObjectURL(blobUrl);
                    }}, 5000);
                }} catch (error) {{
                    console.error('Error al abrir el informe:', error);
                    alert('Error al abrir el informe. Por favor, intente nuevamente.');
                }}
            }});
        }})();
        </script>
        """
    
    def _generate_footer(self) -> str:
        """Genera el footer del informe"""
        return """
        <div style="text-align: center; margin-top: 50px; padding: 20px; border-top: 2px solid #f8f9fa; color: #6c757d;">
            <p><strong>COREF Suite - NIR Maintenance Consolidator v2.0</strong></p>
            <p>Desarrollado por BUCHI Spain</p>
        </div>
        """
    
    def _get_styles(self) -> str:
        """Retorna los estilos CSS con el sidebar corregido"""
        return """
/* ===== ESTILOS CORPORATIVOS BUCHI - COREF REPORTS CON SIDEBAR ===== */

/* Reset básico */
* {
    box-sizing: border-box;
}

/* Estilos globales */
body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    line-height: 1.6;
    color: #333;
    background-color: #f5f5f5;
    margin: 0;
    padding: 0;
}

body > *:first-child {
    margin-top: 0;
}

/* ===== SIDEBAR CORPORATIVO FIJO ===== */
.sidebar {
    position: fixed;
    left: 0;
    top: 0;
    width: 250px;
    height: 100vh;
    background-color: #093A34;
    padding: 20px;
    overflow-y: auto;
    z-index: 1000;
    box-shadow: 2px 0 5px rgba(0,0,0,0.1);
}

.sidebar ul {
    list-style: none;
    padding: 0;
    margin: 0;
}

.sidebar ul li {
    margin-bottom: 10px;
}

.sidebar ul li a {
    color: white;
    text-decoration: none;
    display: block;
    padding: 10px;
    border-radius: 5px;
    transition: background-color 0.3s;
    font-weight: bold;
}

.sidebar ul li a:hover {
    background-color: #289A93;
}

/* ===== CONTENIDO PRINCIPAL CON MARGEN PARA SIDEBAR ===== */
.main-content {
    margin-left: 290px;
    padding: 40px;
    max-width: 1400px;
}

/* ===== Títulos ===== */
h1 {
    color: #000000;
    margin-top: 0px;
    font-weight: bold;
    padding: 15px;
}

h2 {
    color: #000000;
    font-weight: bold;
    margin-top: 20px;
    padding: 10px;
}

h3 {
    color: #000000;
    margin-top: 15px;
}

/* ===== Títulos especiales ===== */
.param-title {
    font-size: 18px;
    font-weight: bold;
    margin-top: 20px;
    color: #000000;
    padding: 10px;
    background-color: #f8f9fa;
    border-radius: 10px;
}

/* ===== Container ===== */
.container {
    width: 90%;
    margin: 0 auto;
    background-color: #ffffff;
    padding: 20px;
}

/* ===== Tablas ===== */
table {
    border-collapse: collapse;
    margin: 20px 0;
    width: 100%;
    border-radius: 10px;
    overflow: hidden;
}

table, th, td {
    border: 1px solid #ddd;
}

th {
    padding: 12px 10px;
    text-align: left;
    font-size: 14px;
    background-color: #f8f9fa;
    color: #000000;
    font-weight: bold;
}

td {
    padding: 10px;
    text-align: left;
    font-size: 13px;
    background-color: #ffffff;
    color: #000000;
}

tr:hover {
    background-color: #f5f5f5;
}

/* ===== Tabla de resumen ===== */
.summary-table {
    font-size: 14px;
    margin-top: 40px;
    margin-bottom: 40px;
    width: 100%;
    border-collapse: collapse;
}

.summary-table th, .summary-table td {
    padding: 12px 15px;
    text-align: left;
    border: 1px solid #ddd;
}

.summary-table th {
    font-weight: bold;
    background-color: #f8f9fa;
    color: #000000;
}

.summary-table td {
    background-color: #ffffff;
    color: #000000;
}

/* ===== Info de archivo ===== */
.file-info {
    display: flex;
    margin-top: 20px;
    gap: 20px;
    align-items: center;
    padding: 15px;
    background-color: #f8f9fa;
    border-radius: 10px;
}

/* ===== Contenedores de gráficos ===== */
.row-wrapper {
    overflow-x: auto;
    white-space: nowrap;
    margin: 20px 0;
}

.plot-container {
    display: inline-block;
    width: 900px;
    margin-right: 20px;
    background-color: #ffffff;
    padding: 15px;
    border-radius: 10px;
}

/* ===== Caja de estadísticas ===== */
.stats-box {
    background-color: #f8f9fa;
    border: 2px solid #ddd;
    border-radius: 10px;
    padding: 15px 20px;
    font-size: 13px;
    color: #000000;
    margin-bottom: 20px;
    width: fit-content;
}

.stats-box h3 {
    color: #000000;
    margin-top: 0;
    font-size: 16px;
}

/* ===== Navegación con pestañas ===== */
.nav-link {
    color: #64B445 !important;
    padding: 10px 20px;
    border-radius: 10px 10px 0 0;
    transition: all 0.3s ease;
}

.nav-link:hover {
    background-color: #f8f9fa;
}

.nav-link.active {
    color: white !important;
    background-color: #64B445 !important;
    font-weight: bold;
}

/* ===== Controles de carrusel ===== */
.carousel-control-prev-icon,
.carousel-control-next-icon {
    background-color: #64B445;
    width: 50px;
    height: 50px;
    border-radius: 50%;
    background-image: none;
    transition: all 0.3s ease;
}

.carousel-control-prev-icon {
    position: absolute;
    left: 20px;
    margin-left: -50px;
    top: 50%;
    transform: translateY(-50%);
}

.carousel-control-prev-icon::before {
    content: '‹';
    font-size: 40px;
    color: white;
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
}

.carousel-control-next-icon::before {
    content: '›';
    font-size: 40px;
    color: white;
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
}

.carousel-control-prev:hover .carousel-control-prev-icon,
.carousel-control-next:hover .carousel-control-next-icon {
    background-color: #289A93;
}

/* ===== Botones ===== */
.btn-primary {
    background-color: #64B445;
    color: white;
    padding: 10px 20px;
    border: none;
    border-radius: 10px;
    cursor: pointer;
    font-weight: bold;
    transition: all 0.3s ease;
}

.btn-primary:hover {
    background-color: #289A93;
}

/* ===== Badges/Etiquetas ===== */
.badge {
    padding: 5px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: bold;
    display: inline-block;
}

.badge-success {
    background-color: #64B445;
    color: white;
}

.badge-info {
    background-color: #4DB9D2;
    color: white;
}

.badge-warning {
    background-color: #E08B55;
    color: white;
}

/* ===== Cajas de información (PARA COREF) ===== */
.info-box {
    background-color: white;
    border-radius: 8px;
    padding: 25px;
    margin: 20px 0;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.warning-box {
    background-color: #fff3cd;
    border-left: 5px solid #ffc107;
    border-radius: 8px;
    padding: 20px;
    margin: 20px 0;
}

.status-good {
    background-color: #d4edda;
    border-left: 5px solid #28a745;
    border-radius: 8px;
    padding: 20px;
    margin: 20px 0;
}

.status-bad {
    background-color: #f8d7da;
    border-left: 5px solid #dc3545;
    border-radius: 8px;
    padding: 20px;
    margin: 20px 0;
}

/* ===== Grid de información ===== */
.info-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 20px;
    margin: 20px 0;
}

.info-item {
    background-color: #f8f9fa;
    padding: 15px;
    border-radius: 5px;
    border-left: 3px solid #289A93;
}

.info-label {
    font-weight: bold;
    color: #093A34;
    display: block;
    margin-bottom: 5px;
    font-size: 0.9em;
}

.info-value {
    color: #333;
    font-size: 1.1em;
}

/* ===== Expandibles ===== */
details {
    margin: 20px 0;
    border: 1px solid #ddd;
    border-radius: 5px;
    padding: 10px;
    background-color: white;
}

summary {
    cursor: pointer;
    font-weight: bold;
    padding: 10px;
    background-color: #f8f9fa;
    border-radius: 5px;
    user-select: none;
    color: #093A34;
}

summary:hover {
    background-color: #e9ecef;
}

details[open] summary {
    border-bottom: 2px solid #289A93;
    margin-bottom: 10px;
}

/* ===== Footer ===== */
.footer {
    text-align: center;
    padding: 30px;
    margin-top: 50px;
    border-top: 3px solid #289A93;
    color: #6c757d;
    background-color: white;
}

/* ===== Pre-formatted text ===== */
pre {
    background-color: #f8f9fa;
    padding: 20px;
    border-radius: 8px;
    border: 1px solid #dee2e6;
    overflow-x: auto;
    font-family: 'Courier New', monospace;
    font-size: 0.85em;
    line-height: 1.5;
    white-space: pre-wrap;
}

/* ===== Collapsible Sections (CONSOLIDATOR) ===== */
.report-section {
    background-color: #ffffff;
    padding: 20px;
    margin: 25px 0;
    border-radius: 10px;
    border: 1px solid #ddd;
}

.report-section > details {
    margin: 0;
}

.report-section > details > summary {
    cursor: pointer;
    user-select: none;
    list-style: none;
    padding: 15px;
    background-color: #f8f9fa;
    border-radius: 8px;
    transition: background-color 0.3s;
}

.report-section > details > summary::-webkit-details-marker {
    display: none;
}

.report-section > details > summary::before {
    content: '▶ ';
    display: inline-block;
    margin-right: 10px;
    transition: transform 0.3s;
}

.report-section > details[open] > summary::before {
    transform: rotate(90deg);
}

.report-section > details > summary:hover {
    background-color: #e9ecef;
}

.section-header h2 {
    display: inline;
    margin: 0;
    font-size: 1.5em;
}

.parsed-content {
    padding: 20px 0;
}

/* ===== Full Report Link ===== */
.full-report-link {
    margin-top: 30px;
    padding: 20px;
    border-top: 2px solid #e9ecef;
    text-align: center;
}

.open-full-report-btn {
    display: inline-block;
    padding: 15px 30px;
    background: #64B445;
    color: white;
    text-decoration: none;
    border-radius: 8px;
    font-weight: bold;
    font-size: 1.1em;
    transition: transform 0.2s, box-shadow 0.2s;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    border: none;
    cursor: pointer;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.open-full-report-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    background-color: #289A93;
}

.open-full-report-btn:active {
    transform: translateY(0);
}

.report-link-description {
    margin-top: 10px;
    color: #6c757d;
    font-size: 0.9em;
    font-style: italic;
}

/* ===== Metrics Grid (CONSOLIDATOR) ===== */
.metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    margin: 20px 0;
}

.metric-card {
    padding: 20px;
    border-radius: 8px;
    text-align: center;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.metric-card.ok {
    background-color: #e8f5e9;
    border-left: 4px solid #4caf50;
}

.metric-card.warning {
    background-color: #fff3e0;
    border-left: 4px solid #ff9800;
}

.metric-card.fail {
    background-color: #ffebee;
    border-left: 4px solid #f44336;
}

.metric-card.total {
    background-color: #e3f2fd;
    border-left: 4px solid #2196f3;
}

.metric-card.info {
    background-color: #f8f9fa;
    border-left: 4px solid #64B445;
}

.metric-value {
    font-size: 36px;
    font-weight: bold;
    margin-bottom: 5px;
    color: #000000;
}

.metric-value-small {
    font-size: 24px;
    font-weight: bold;
    margin-bottom: 5px;
    color: #000000;
}

.metric-label {
    font-size: 14px;
    color: #666;
    font-weight: bold;
}

.metric-sublabel {
    font-size: 12px;
    color: #999;
    margin-top: 5px;
}

/* ===== Status Boxes ===== */
.status-box-ok {
    background-color: #e8f5e9 !important;
    border-left: 4px solid #4caf50 !important;
}

.status-box-warning {
    background-color: #fff3e0 !important;
    border-left: 4px solid #ff9800 !important;
}

.status-box-fail {
    background-color: #ffebee !important;
    border-left: 4px solid #f44336 !important;
}

.status-box-info {
    background-color: #e3f2fd !important;
    border-left: 4px solid #2196f3 !important;
}

/* ===== Responsive ===== */
@media screen and (max-width: 992px) {
    .sidebar {
        width: 100%;
        height: auto;
        position: relative;
    }

    .main-content {
        margin-left: 0;
        padding: 20px;
    }

    .container {
        width: 95%;
        margin: 10px auto;
    }

    .plot-container {
        width: 100%;
    }

    table {
        font-size: 12px;
    }

    th, td {
        padding: 8px 5px;
    }

    .info-grid {
        grid-template-columns: 1fr;
    }
}
"""