"""
Consolidador de informes NIR - Versión 2.0 Optimizada
Combina parsing para resumen ejecutivo + HTML completo embebido
Parte del módulo COREF Suite

Optimizaciones v2024.12:
- CSS cargado desde buchi_report_styles.css
- Sin CSS inline (todo en archivo CSS)
- Funciones compartidas desde report_utils
"""
from typing import Dict, Any
from datetime import datetime
import base64

# Importar funciones compartidas
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.report_utils import load_buchi_css, generate_footer


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
        
        # Construir secciones colapsables
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
        
        # Cargar CSS (todo desde archivo)
        buchi_css = load_buchi_css()
        
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
{buchi_css}
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
        
{generate_footer()}
    </div>
</body>
</html>
"""
        return html
    
    def _generate_header(self) -> str:
        """Genera el header con información del servicio"""
        sensor_id = self.service_info.get('sensor_id', 'N/A')
        fecha = self.service_info.get('fecha', 'N/A')
        cliente = self.service_info.get('cliente', 'N/A')
        tecnico = self.service_info.get('tecnico', 'N/A')
        ubicacion = self.service_info.get('ubicacion', 'N/A')
        modelo = self.service_info.get('modelo', 'N/A')
        
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
        
        # Contexto del mantenimiento
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
        
        notas_section = ""
        if notas:
            notas_section = f"""
            <div style="margin-top: 15px; padding: 15px; background-color: #fff3e0; border-left: 4px solid #ff9800; border-radius: 5px;">
                <strong>📝 Notas Adicionales:</strong> 
                <p style="margin: 10px 0 0 0; line-height: 1.6; white-space: pre-line;">{notas}</p>
            </div>
            """
        
        descripcion = """
        <details open style="margin-top: 25px;">
            <summary style="cursor: pointer; padding: 20px; background-color: #ffffff; border-radius: 8px; border: 1px solid #dee2e6; list-style: none; user-select: none;">
                <span style="font-size: 1.2em; font-weight: bold; color: #000000;">📖 Acerca de Este Informe</span>
                <span style="float: right; color: #6c757d;">▶</span>
            </summary>
            
            <div style="padding: 25px; background-color: #ffffff; border-radius: 0 0 8px 8px; border: 1px solid #dee2e6; border-top: none; margin-top: -1px;">
                <p style="line-height: 1.6; margin-bottom: 20px; color: #333;">
                    Este informe consolida los resultados de los procedimientos de mantenimiento preventivo y validación 
                    realizados en el espectrómetro NIR.
                </p>
                
                <div style="margin-top: 25px;">
                    <h4 style="color: #000000; margin-bottom: 15px;">🔧 Procedimientos Incluidos:</h4>
                    
                    <div style="margin-bottom: 20px; padding-left: 15px;">
                        <strong style="color: #64B445; font-size: 1.05em;">📐 Baseline Adjustment</strong>
                        <p style="margin: 8px 0 0 20px; line-height: 1.6; color: #444;">
                            Corrección del baseline tras cambio de lámpara usando el White Standard Reference.
                        </p>
                    </div>
                    
                    <div style="margin-bottom: 20px; padding-left: 15px;">
                        <strong style="color: #289A93; font-size: 1.05em;">✅ Validación Óptica</strong>
                        <p style="margin: 8px 0 0 20px; line-height: 1.6; color: #444;">
                            Verificación de alineación óptica mediante kit de standards certificados.
                        </p>
                    </div>
                    
                    <div style="margin-bottom: 20px; padding-left: 15px;">
                        <strong style="color: #2196f3; font-size: 1.05em;">🔬 Predicciones</strong>
                        <p style="margin: 8px 0 0 20px; line-height: 1.6; color: #444;">
                            Análisis comparativo de predicciones entre diferentes lámparas.
                        </p>
                    </div>
                </div>
                
                <div style="margin-top: 25px; padding: 15px; background-color: #f8f9fa; border-radius: 5px;">
                    <p style="margin: 0; color: #6c757d; font-size: 0.95em;">
                        <strong>💡 Uso:</strong> Expanda cada sección para ver resúmenes. 
                        Use "📄 Abrir Informe Completo" para gráficos interactivos.
                    </p>
                </div>
            </div>
        </details>
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
        
        if 'FAIL' in statuses:
            return 'FAIL'
        elif 'WARNING' in statuses:
            return 'WARNING'
        elif 'OK' in statuses:
            return 'OK'
        else:
            return 'UNKNOWN'
    
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
                'EXCELENTE': 'ok', 'BUENO': 'ok', 'ACEPTABLE': 'warning',
                'REQUIERE REVISIÓN': 'fail', 'UNKNOWN': 'info'
            }
            status_class = status_class_map.get(estado, 'info')
            
            status_icon_map = {
                'EXCELENTE': '✅', 'BUENO': '✅', 'ACEPTABLE': '⚠️',
                'REQUIERE REVISIÓN': '❌', 'UNKNOWN': 'ℹ️'
            }
            status_icon = status_icon_map.get(estado, 'ℹ️')
            
            verif_html = f"""
            <h3>📊 Métricas de Verificación Post-Ajuste</h3>
            <table>
                {''.join(verif_rows)}
            </table>
            
            <div class="consolidator-status-box consolidator-status-{status_class}">
                <h4 style="margin-top: 0;">{status_icon} Conclusión: {estado}</h4>
                <p style="margin: 10px 0 0 0; line-height: 1.6;">{conclusion}</p>
            </div>
            """
        else:
            verif_html = """
            <div class="consolidator-status-box consolidator-status-info">
                <p><em>No hay datos de verificación disponibles.</em></p>
            </div>
            """
        
        charts_note = """
        <div class="consolidator-charts-note">
            <p style="margin: 0; color: #1976d2;">
                <strong>📈 Gráficos:</strong> Abra el informe completo para ver overlay de espectros y matriz RMS.
            </p>
        </div>
        """
        
        return f"{verif_html}{charts_note}"
    
    def _generate_validation_summary(self) -> str:
        """Genera resumen parseado de validación"""
        criterios = self.validation_data.get('criterios_validacion', {})
        global_stats = self.validation_data.get('estadisticas_globales', {})
        detailed = self.validation_data.get('resultados_detallados', [])
        
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
            <p class="consolidator-description"><em>Umbrales de evaluación.</em></p>
            <table>
                <tr><th>Parámetro</th><th>Umbral</th><th>Descripción</th></tr>
                {''.join(criterios_rows)}
            </table>
            """
        
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
            <p class="consolidator-description"><em>Métricas agregadas.</em></p>
            <table>
                <tr><th>Métrica</th><th>Mínimo</th><th>Máximo</th><th>Media</th><th>Desv. Est.</th></tr>
                {''.join(stats_rows)}
            </table>
            """
        
        detail_html = ""
        if detailed:
            detail_rows = []
            for result in detailed:
                status_icon = {'ok': '✅', 'warning': '⚠️', 'fail': '❌'}.get(result['estado'].lower(), 'ℹ️')
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
            <table>
                <tr><th>Estándar</th><th>Lámpara Ref.</th><th>Lámpara Nueva</th><th>Correlación</th><th>Max Δ</th><th>RMS</th><th>Estado</th></tr>
                {''.join(detail_rows)}
            </table>
            """
        
        charts_note = """
        <div class="consolidator-charts-note">
            <p style="margin: 0; color: #1976d2;">
                <strong>📈 Ver Completo:</strong> Abra el informe para gráficos de correlación y overlays.
            </p>
        </div>
        """
        
        return f"{criterios_html}{stats_html}{detail_html}{charts_note}"
    
    def _generate_predictions_summary(self) -> str:
        """Genera resumen parseado de predicciones"""
        info_general = self.predictions_data.get('info_general', {})
        
        lamparas_html = ""
        if info_general.get('Lámparas'):
            lamparas_items = ''.join([f"<li>{lamp}</li>" for lamp in info_general['Lámparas']])
            lamparas_html = f"""
            <div style="margin-top: 15px;">
                <strong>Lámparas Comparadas:</strong>
                <ul style="margin-top: 10px;">{lamparas_items}</ul>
            </div>
            """
        
        charts_note = """
        <div class="consolidator-charts-note">
            <p style="margin: 0; color: #1976d2;">
                <strong>📈 Ver Completo:</strong> Abra el informe para estadísticas y gráficos comparativos.
            </p>
        </div>
        """
        
        return f"""
            <h3>📊 Información General</h3>
            <p class="consolidator-description"><em>Resumen del análisis NIR.</em></p>
            <table>
                <tr><td><strong>Sensor NIR</strong></td><td>{info_general.get('Sensor NIR', 'N/A')}</td></tr>
                <tr><td><strong>Fecha</strong></td><td>{info_general.get('Fecha del Reporte', 'N/A')}</td></tr>
                <tr><td><strong>Productos</strong></td><td>{info_general.get('Productos Analizados', 'N/A')}</td></tr>
                <tr><td><strong>Lámparas</strong></td><td>{info_general.get('Lámparas Comparadas', 'N/A')}</td></tr>
            </table>
            {lamparas_html}
            {charts_note}
        """
    
    def _generate_index(self) -> str:
        """Genera items del índice lateral"""
        items = []
        if self.baseline_html:
            items.append('            <li><a href="#baseline">📐 Baseline Adjustment</a></li>')
        if self.validation_html:
            items.append('            <li><a href="#validation">✅ Validación Óptica</a></li>')
        if self.predictions_html:
            items.append('            <li><a href="#predictions">🔬 Predicciones</a></li>')
        return '\n'.join(items)
    
    def _generate_collapsible_section(self, section_id: str, title: str, 
                                     parsed_summary: str, html_content: str) -> str:
        """Genera sección colapsable con resumen + link a HTML completo"""
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
        
        if '</body>' in html_content:
            html_modified = html_content.replace('</body>', sidebar_fix_script + '</body>')
        else:
            html_modified = html_content + sidebar_fix_script
        
        html_bytes = html_modified.encode('utf-8')
        html_base64 = base64.b64encode(html_bytes).decode('ascii')
        button_id = f"btn-{section_id}-{id(html_content) % 100000}"
        
        return f"""
        <div class="consolidator-section" id="{section_id}">
            <details open>
                <summary class="consolidator-section-header">
                    <h2>{title}</h2>
                </summary>
                
                <div class="consolidator-parsed-content">
                    {parsed_summary}
                </div>
                
                <div class="consolidator-full-report-link">
                    <button id="{button_id}" class="consolidator-open-btn">
                        📄 Abrir Informe Completo en Nueva Pestaña
                    </button>
                    <p class="consolidator-link-description">
                        Informe original con gráficos interactivos.
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
                    console.error('Error:', error);
                    alert('Error al abrir el informe.');
                }}
            }});
        }})();
        </script>
        """