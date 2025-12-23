"""
Report Utils - Shared Functions
================================
Funciones compartidas para generadores de informes HTML.
Usado por: validation_kit_report_generator y offset_adjustment_report_generator

Author: Miquel
Date: December 2024
"""

from typing import Dict, List
import pandas as pd
import numpy as np
from datetime import datetime


def wrap_chart_in_expandable(chart_html: str, title: str, chart_id: str, 
                             default_open: bool = False) -> str:
    """
    Envuelve un gráfico en un elemento expandible HTML.
    
    Args:
        chart_html: HTML del gráfico
        title: Título del expandible
        chart_id: ID único para el expandible
        default_open: Si debe estar abierto por defecto
        
    Returns:
        str: HTML con el gráfico en un expandible
    """
    open_attr = "open" if default_open else ""
    
    return f"""
    <details class="chart-expandable" {open_attr}>
        <summary style="cursor: pointer; font-weight: bold; padding: 10px; background-color: #f8f9fa; border-radius: 5px; user-select: none; color: #333;">
            📊 {title}
        </summary>
        <div style="padding: 15px; margin-top: 10px;">
            {chart_html}
        </div>
    </details>
    """


def load_buchi_css() -> str:
    """
    Carga el CSS corporativo de Buchi con fallback.
    
    Returns:
        str: Contenido CSS
    """
    try:
        with open('buchi_report_styles_simple.css', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        # Fallback CSS básico
        return """
            body { font-family: Arial, sans-serif; margin: 0; padding: 0; }
            .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
            h1, h2, h3 { color: #2c5f3f; }
            table { width: 100%; border-collapse: collapse; margin: 15px 0; }
            th { background-color: #2c5f3f; color: white; padding: 10px; text-align: left; }
            td { padding: 8px; border-bottom: 1px solid #ddd; }
            .info-box { background-color: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 5px; }
            .warning-box { background-color: #fff3cd; padding: 20px; margin: 20px 0; border-radius: 5px; border-left: 4px solid #ffc107; }
            .success-box { background-color: #d4edda; padding: 20px; margin: 20px 0; border-radius: 5px; border-left: 4px solid #28a745; }
            .status-good { color: #4caf50; font-weight: bold; }
            .status-warning { color: #ff9800; font-weight: bold; }
            .status-bad { color: #f44336; font-weight: bold; }
        """


def get_sidebar_styles() -> str:
    """
    Retorna los estilos CSS para el sidebar del informe.
    CORREGIDO: Usa selectores específicos para evitar conflictos con main-content.
    
    Returns:
        str: CSS del sidebar
    """
    return """
        .sidebar {
            position: fixed; left: 0; top: 0; width: 250px; height: 100%;
            background-color: #093A34; padding: 20px; overflow-y: auto; z-index: 1000;
        }
        .sidebar h2 {
            color: white; font-size: 16px; margin-bottom: 20px; text-align: center;
        }
        .sidebar ul { list-style: none; padding: 0; }
        .sidebar ul li { margin-bottom: 10px; }
        .sidebar ul li a {
            color: white; text-decoration: none; display: block; padding: 8px;
            border-radius: 5px; transition: background-color 0.3s; font-weight: bold;
            font-size: 14px;
        }
        .sidebar ul li a:hover { background-color: #289A93; }
        
        /* Estilos ESPECÍFICOS para details del menú del sidebar */
        .sidebar .sidebar-menu-details {
            margin-bottom: 10px;
        }
        .sidebar .sidebar-menu-details summary {
            color: white;
            list-style: none;
            user-select: none;
            cursor: pointer;
            padding: 8px;
            border-radius: 5px;
            font-weight: bold;
            font-size: 14px;
        }
        .sidebar .sidebar-menu-details summary::-webkit-details-marker {
            display: none;
        }
        .sidebar .sidebar-menu-details summary:hover {
            background-color: #289A93;
        }
        .sidebar .sidebar-menu-details[open] summary {
            background-color: #289A93;
        }
        .sidebar .sidebar-menu-details ul li a {
            font-size: 12px;
            font-weight: normal;
            padding: 6px 8px;
        }
    """


def get_common_report_styles() -> str:
    """
    Retorna estilos CSS comunes para todos los informes.
    
    Returns:
        str: CSS común
    """
    return """
        .main-content { margin-left: 270px; padding: 20px; }
        
        /* Estilos específicos para expandibles de gráficos en main-content */
        .main-content .chart-expandable {
            margin: 20px 0;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 10px;
            background-color: white;
        }
        
        .main-content .chart-expandable summary {
            cursor: pointer;
            font-weight: bold;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 5px;
            user-select: none;
            color: #333;
            list-style: none;
        }
        
        .main-content .chart-expandable summary::-webkit-details-marker {
            display: none;
        }
        
        .main-content .chart-expandable summary:hover {
            background-color: #e9ecef;
        }
        
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
        
        .metric-card.offset {
            background-color: #e3f2fd;
            border-left: 4px solid #2196f3;
        }
        
        .metric-card.standards {
            background-color: #f3e5f5;
            border-left: 4px solid #9c27b0;
        }
        
        .metric-card.improvement {
            background-color: #e8f5e9;
            border-left: 4px solid #4caf50;
        }
        
        .metric-value {
            font-size: 36px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .metric-label {
            font-size: 14px;
            color: #666;
        }
        
        .comparison-table {
            margin: 20px 0;
        }
        
        .comparison-table th {
            text-align: center;
        }
        
        .improvement {
            color: #4caf50;
            font-weight: bold;
        }
        
        .degradation {
            color: #f44336;
            font-weight: bold;
        }
        
        @media print {
            .sidebar { display: none; }
            .main-content { margin-left: 0; }
        }
    """


def build_sidebar_html(sections: List[tuple], standards_list: List[Dict] = None,
                       show_individual_analysis: bool = True) -> str:
    """
    Construye el HTML del sidebar con índice de navegación.
    
    Args:
        sections: Lista de tuplas (id, label) para secciones principales
        standards_list: Lista de diccionarios con datos de estándares para sub-índice
        show_individual_analysis: Si True, incluye sección de análisis individual
        
    Returns:
        str: HTML del sidebar
    """
    sidebar_items = []
    
    # Secciones principales
    for sid, label in sections:
        sidebar_items.append(f'<li><a href="#{sid}">{label}</a></li>')
    
    # Sub-índice de estándares individuales (si se proporciona)
    if show_individual_analysis and standards_list:
        standards_submenu = []
        for data in standards_list:
            sample_id = data.get('id', 'Unknown')
            
            # Determinar icono según estado (si está disponible)
            if 'validation_results' in data:
                val_res = data['validation_results']
                has_shift = data.get('has_shift', False)
                
                if val_res.get('pass', False) and not has_shift:
                    icon = "✅"
                elif val_res.get('pass', False) and has_shift:
                    icon = "⚠️"
                else:
                    icon = "❌"
            else:
                icon = "📊"
            
            standards_submenu.append(
                f'<li><a href="#standard-{sample_id}">{icon} {sample_id}</a></li>'
            )
        
        standards_html = "\n".join(standards_submenu)
        
        sidebar_items.append(f'''
            <li>
                <details class="sidebar-menu-details">
                    <summary>
                        📊 Análisis Individual
                    </summary>
                    <ul style="padding-left: 15px; margin-top: 5px;">
                        {standards_html}
                    </ul>
                </details>
            </li>
        ''')
    
    return "\n".join(sidebar_items)


def evaluate_offset(offset: float) -> str:
    """
    Evalúa el offset según umbrales y retorna HTML con estilo.
    
    Args:
        offset: Valor del offset
        
    Returns:
        str: HTML con evaluación estilizada
    """
    from config import OFFSET_LIMITS
    
    abs_offset = abs(offset)
    
    if abs_offset < OFFSET_LIMITS['negligible']:
        return '<span class="status-good">✅ Despreciable</span>'
    elif abs_offset < OFFSET_LIMITS['acceptable']:
        return '<span class="status-good">✓ Aceptable</span>'
    else:
        return '<span class="status-warning">⚠️ Significativo</span>'


def format_change(delta: float, inverse: bool = False, show_sign: bool = False) -> str:
    """
    Formatea el cambio con color según si es mejora o empeoramiento.
    
    Args:
        delta: Cambio en la métrica
        inverse: Si True, un valor negativo es mejora (para Max Δ, RMS)
        show_sign: Si True, muestra el signo incluso para abs()
    
    Returns:
        str: HTML con cambio formateado y estilizado
    """
    if show_sign:
        text = f"{delta:+.6f}"
    else:
        text = f"{delta:+.6f}"
    
    # Determinar si es mejora
    if inverse:
        is_improvement = delta < 0
    else:
        is_improvement = delta > 0
    
    if abs(delta) < 0.000001:
        return f'<span style="color: #666;">{text}</span>'
    elif is_improvement:
        return f'<span class="improvement">↑ {text}</span>'
    else:
        return f'<span class="degradation">↓ {text}</span>'


def generate_service_info_section(sensor_serial: str, customer_name: str, 
                                  technician_name: str, service_notes: str,
                                  additional_info: Dict = None) -> str:
    """
    Genera la sección de información del servicio.
    
    Args:
        sensor_serial: Número de serie del sensor
        customer_name: Nombre del cliente
        technician_name: Nombre del técnico
        service_notes: Notas del servicio
        additional_info: Diccionario con información adicional a mostrar
        
    Returns:
        str: HTML de la sección de información
    """
    report_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    html = f"""
        <div class="info-box" id="info-servicio">
            <h2>Información del Servicio</h2>
            <table>
                <tr><th>Campo</th><th>Valor</th></tr>
                <tr><td><strong>Cliente</strong></td><td>{customer_name}</td></tr>
                <tr><td><strong>Técnico</strong></td><td>{technician_name}</td></tr>
                <tr><td><strong>Número de Serie</strong></td><td>{sensor_serial}</td></tr>
                <tr><td><strong>Fecha del Informe</strong></td><td>{report_date}</td></tr>
    """
    
    # Añadir información adicional si se proporciona
    if additional_info:
        for key, value in additional_info.items():
            html += f"<tr><td><strong>{key}</strong></td><td>{value}</td></tr>\n"
    
    html += f"""
                <tr><td><strong>Notas del Servicio</strong></td><td>{service_notes if service_notes else 'N/A'}</td></tr>
            </table>
        </div>
    """
    
    return html


def generate_footer(tool_name: str = "COREF Suite") -> str:
    """
    Genera el footer del informe.
    
    Args:
        tool_name: Nombre de la herramienta que generó el informe
        
    Returns:
        str: HTML del footer
    """
    html = f"""
        <div style="margin-top: 50px; padding-top: 20px; border-top: 2px solid #eee; text-align: center; color: #666; font-size: 12px;">
            <p>Informe generado automáticamente por {tool_name}</p>
            <p>Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>© {datetime.now().year} BÜCHI Labortechnik AG</p>
        </div>
    </body>
    </html>
    """
    return html


def start_html_template(title: str, sidebar_html: str) -> str:
    """
    Inicia el documento HTML con estructura base.
    
    Args:
        title: Título del documento
        sidebar_html: HTML del sidebar ya construido
        
    Returns:
        str: HTML inicial del documento
    """
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <style>
            {load_buchi_css()}
            {get_sidebar_styles()}
            {get_common_report_styles()}
        </style>
    </head>
    <body>
        <div class="sidebar">
            <h2>📋 Índice</h2>
            <ul>
                {sidebar_html}
            </ul>
        </div>

        <div class="main-content">
    """


def calculate_global_metrics(validation_data: List[Dict]) -> Dict:
    """
    Calcula métricas globales de un conjunto de validaciones.
    
    Args:
        validation_data: Lista de diccionarios con datos de validación
        
    Returns:
        Dict con métricas agregadas
    """
    corr_list = [d['validation_results']['correlation'] for d in validation_data]
    max_list = [d['validation_results']['max_diff'] for d in validation_data]
    rms_list = [d['validation_results']['rms'] for d in validation_data]
    offset_list = [d['validation_results']['mean_diff'] for d in validation_data]
    
    return {
        'corr_mean': np.mean(corr_list),
        'corr_std': np.std(corr_list),
        'corr_min': np.min(corr_list),
        'corr_max': np.max(corr_list),
        'max_mean': np.mean(max_list),
        'max_std': np.std(max_list),
        'max_min': np.min(max_list),
        'max_max': np.max(max_list),
        'rms_mean': np.mean(rms_list),
        'rms_std': np.std(rms_list),
        'rms_min': np.min(rms_list),
        'rms_max': np.max(rms_list),
        'offset_mean': np.mean(offset_list),
        'offset_std': np.std(offset_list),
        'offset_min': np.min(offset_list),
        'offset_max': np.max(offset_list),
    }