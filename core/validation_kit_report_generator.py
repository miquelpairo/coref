"""
Validation Kit Report Generator
================================
Genera informes HTML para validación de estándares ópticos NIR.
Sigue el mismo estilo y estructura que report_generator.py
"""

from typing import Dict, List
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def wrap_chart_in_expandable(chart_html, title, chart_id, default_open=False):
    """
    Envuelve un gráfico en un elemento expandible HTML.
    
    Args:
        chart_html (str): HTML del gráfico
        title (str): Título del expandible
        chart_id (str): ID único para el expandible
        default_open (bool): Si debe estar abierto por defecto
        
    Returns:
        str: HTML con el gráfico en un expandible
    """
    open_attr = "open" if default_open else ""
    
    return f"""
    <details {open_attr} style="margin: 20px 0; border: 1px solid #ddd; border-radius: 5px; padding: 10px;">
        <summary style="cursor: pointer; font-weight: bold; padding: 10px; background-color: #f8f9fa; border-radius: 5px; user-select: none;">
            📊 {title}
        </summary>
        <div style="padding: 15px; margin-top: 10px;">
            {chart_html}
        </div>
    </details>
    """


def load_buchi_css():
    """Carga el CSS corporativo de Buchi"""
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
            .status-good { color: #4caf50; font-weight: bold; }
            .status-warning { color: #ff9800; font-weight: bold; }
            .status-bad { color: #f44336; font-weight: bold; }
        """


def start_html_document(report_data):
    """
    Inicia el documento HTML con información del servicio y barra lateral.
    """
    sensor_serial = report_data['sensor_serial']
    customer_name = report_data['customer_name']
    technician_name = report_data['technician_name']
    service_notes = report_data['service_notes']
    report_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    validation_data = report_data['validation_data']
    
    # Construir índice del sidebar con secciones normales
    sections = [
        ("info-servicio", "Información del Servicio"),
        ("resumen-ejecutivo", "Resumen Ejecutivo"),
        ("criterios-validacion", "Criterios de Validación"),
        ("estadisticas-globales", "Estadísticas Globales"),
        ("resultados-detallados", "Resultados Detallados"),
        ("vista-global", "Vista Global de Espectros"),
    ]
    
    sidebar_items = []
    for sid, label in sections:
        sidebar_items.append(f'<li><a href="#{sid}">{label}</a></li>')
    
    # Sub-índice de estándares individuales (construir HTML)
    standards_submenu = []
    for data in validation_data:
        sample_id = data['id']
        val_res = data['validation_results']
        if val_res['pass'] and not data['has_shift']:
            icon = "✅"
        elif val_res['pass'] and data['has_shift']:
            icon = "⚠️"
        else:
            icon = "❌"
        standards_submenu.append(f'<li><a href="#standard-{sample_id}">{icon} {sample_id}</a></li>')
    
    standards_html = "\n".join(standards_submenu)
    
    # Añadir análisis individual como expandable
    sidebar_items.append(f'''
        <li>
            <details>
                <summary style="cursor: pointer; padding: 8px; border-radius: 5px; font-weight: bold; font-size: 14px;">
                    📊 Análisis Individual
                </summary>
                <ul style="padding-left: 15px; margin-top: 5px;">
                    {standards_html}
                </ul>
            </details>
        </li>
    ''')
    
    sidebar_html = "\n".join(sidebar_items)
    
    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Informe de Validación - {sensor_serial}</title>
        <style>
            {load_buchi_css()}
            .sidebar {{
                position: fixed; left: 0; top: 0; width: 250px; height: 100%;
                background-color: #093A34; padding: 20px; overflow-y: auto; z-index: 1000;
            }}
            .sidebar h2 {{
                color: white; font-size: 16px; margin-bottom: 20px; text-align: center;
            }}
            .sidebar ul {{ list-style: none; padding: 0; }}
            .sidebar ul li {{ margin-bottom: 10px; }}
            .sidebar ul li a {{
                color: white; text-decoration: none; display: block; padding: 8px;
                border-radius: 5px; transition: background-color 0.3s; font-weight: bold;
                font-size: 14px;
            }}
            .sidebar ul li a:hover {{ background-color: #289A93; }}
            
            /* Estilos para el expandable */
            .sidebar details {{ margin-bottom: 10px; }}
            .sidebar details summary {{
                color: white;
                list-style: none;
                user-select: none;
            }}
            .sidebar details summary::-webkit-details-marker {{
                display: none;
            }}
            .sidebar details summary:hover {{
                background-color: #289A93;
            }}
            .sidebar details[open] summary {{
                background-color: #289A93;
            }}
            .sidebar details ul li a {{
                font-size: 12px;
                font-weight: normal;
                padding: 6px 8px;
            }}
            
            .main-content {{ margin-left: 270px; padding: 20px; }}
            
            .metrics-grid {{
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 20px;
                margin: 20px 0;
            }}
            
            .metric-card {{
                padding: 20px;
                border-radius: 8px;
                text-align: center;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            
            .metric-card.ok {{
                background-color: #e8f5e9;
                border-left: 4px solid #4caf50;
            }}
            
            .metric-card.warning {{
                background-color: #fff3e0;
                border-left: 4px solid #ff9800;
            }}
            
            .metric-card.fail {{
                background-color: #ffebee;
                border-left: 4px solid #f44336;
            }}
            
            .metric-card.total {{
                background-color: #e3f2fd;
                border-left: 4px solid #2196f3;
            }}
            
            .metric-value {{
                font-size: 36px;
                font-weight: bold;
                margin-bottom: 5px;
            }}
            
            .metric-label {{
                font-size: 14px;
                color: #666;
            }}
            
            @media print {{
                .sidebar {{ display: none; }}
                .main-content {{ margin-left: 0; }}
            }}
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
            <h1>Informe de Validación de Estándares NIR</h1>
            
            <div class="info-box" id="info-servicio">
                <h2>Información del Servicio</h2>
                <table>
                    <tr><th>Campo</th><th>Valor</th></tr>
                    <tr><td><strong>Cliente</strong></td><td>{customer_name}</td></tr>
                    <tr><td><strong>Técnico</strong></td><td>{technician_name}</td></tr>
                    <tr><td><strong>Número de Serie</strong></td><td>{sensor_serial}</td></tr>
                    <tr><td><strong>Fecha del Informe</strong></td><td>{report_date}</td></tr>
                    <tr><td><strong>Archivo Referencia</strong></td><td>{report_data['ref_filename']}</td></tr>
                    <tr><td><strong>Archivo Post-Mantenimiento</strong></td><td>{report_data['curr_filename']}</td></tr>
                    <tr><td><strong>Notas del Servicio</strong></td><td>{service_notes if service_notes else 'N/A'}</td></tr>
                </table>
            </div>
    """
    
    return html

def generate_executive_summary(report_data):
    """
    Genera la sección de resumen ejecutivo.
    
    Args:
        report_data (dict): Datos del informe
        
    Returns:
        str: HTML del resumen ejecutivo
    """
    n_ok = report_data['n_ok']
    n_warn = report_data['n_warn']
    n_fail = report_data['n_fail']
    total = len(report_data['validation_data'])
    
    html = f"""
        <div class="info-box" id="resumen-ejecutivo">
            <h2>Resumen Ejecutivo</h2>
            <div class="metrics-grid">
                <div class="metric-card total">
                    <div class="metric-value">{total}</div>
                    <div class="metric-label">Total Estándares</div>
                </div>
                <div class="metric-card ok">
                    <div class="metric-value">{n_ok}</div>
                    <div class="metric-label">✅ Validados</div>
                </div>
                <div class="metric-card warning">
                    <div class="metric-value">{n_warn}</div>
                    <div class="metric-label">⚠️ Revisar</div>
                </div>
                <div class="metric-card fail">
                    <div class="metric-value">{n_fail}</div>
                    <div class="metric-label">❌ Fallidos</div>
                </div>
            </div>
    """
    
    # Determinar estado general
    if n_fail > 0:
        status = "❌ REQUIERE ATENCIÓN"
        status_class = "warning-box"
        recommendation = """
            <p><strong>Se detectaron estándares que no pasaron la validación.</strong></p>
            <p>Acciones recomendadas:</p>
            <ul>
                <li>Revisar las mediciones que fallaron en la sección de análisis individual</li>
                <li>Verificar las condiciones ambientales durante las mediciones</li>
                <li>Considerar repetir las mediciones de los estándares que fallaron</li>
                <li>Revisar el estado del equipo y de los estándares ópticos</li>
            </ul>
        """
    elif n_warn > 0:
        status = "⚠️ ACEPTABLE CON OBSERVACIONES"
        status_class = "warning-box"
        recommendation = """
            <p><strong>Algunos estándares requieren revisión adicional.</strong></p>
            <p>Se recomienda:</p>
            <ul>
                <li>Revisar los estándares marcados para verificación</li>
                <li>Monitorear el rendimiento en las próximas mediciones</li>
                <li>Documentar cualquier tendencia observada</li>
            </ul>
        """
    else:
        status = "✅ VALIDACIÓN EXITOSA"
        status_class = "info-box"
        recommendation = """
            <p><strong>Todos los estándares pasaron la validación correctamente.</strong></p>
            <p>El equipo está correctamente alineado y listo para uso en producción.</p>
        """
    
    html += f"""
            <div class="{status_class}" style="margin-top: 20px;">
                <h3>{status}</h3>
                {recommendation}
            </div>
        </div>
    """
    
    return html


def generate_validation_criteria(thresholds):
    """
    Genera la sección de criterios de validación.
    
    Args:
        thresholds (dict): Umbrales de validación
        
    Returns:
        str: HTML de criterios
    """
    html = f"""
        <div class="info-box" id="criterios-validacion">
            <h2>Criterios de Validación</h2>
            <table>
                <tr>
                    <th>Parámetro</th>
                    <th>Umbral</th>
                    <th>Descripción</th>
                </tr>
                <tr>
                    <td><strong>Correlación Espectral</strong></td>
                    <td>≥ {thresholds['correlation']}</td>
                    <td>Similitud entre espectros de referencia y actual. Valores cercanos a 1.0 indican alta similitud.</td>
                </tr>
                <tr>
                    <td><strong>Diferencia Máxima</strong></td>
                    <td>≤ {thresholds['max_diff']} AU</td>
                    <td>Máxima desviación puntual permitida en cualquier canal espectral.</td>
                </tr>
                <tr>
                    <td><strong>RMS</strong></td>
                    <td>≤ {thresholds['rms']}</td>
                    <td>Error cuadrático medio. Mide la magnitud promedio de las diferencias entre espectros.</td>
                </tr>
            </table>
            <p style="margin-top: 15px; color: #6c757d; font-size: 0.95em;">
                <em>Un estándar pasa la validación si cumple TODOS los criterios simultáneamente. 
                Adicionalmente, se detectan shifts espectrales que podrían indicar problemas de alineamiento.</em>
            </p>
        </div>
    """
    
    return html


def generate_global_statistics(validation_data, thresholds):
    """
    Genera la sección de estadísticas globales.
    
    Args:
        validation_data (list): Datos de validación
        thresholds (dict): Umbrales de validación
        
    Returns:
        str: HTML de estadísticas globales
    """
    # Calcular estadísticas
    all_correlations = [d['validation_results']['correlation'] for d in validation_data]
    all_max_diffs = [d['validation_results']['max_diff'] for d in validation_data]
    all_rms = [d['validation_results']['rms'] for d in validation_data]
    all_mean_diffs = [d['validation_results']['mean_diff'] for d in validation_data]
    
    html = """
        <div class="info-box" id="estadisticas-globales">
            <h2>Estadísticas Globales</h2>
            <p style="color: #6c757d; font-size: 0.95em;">
                <em>Análisis agregado de todos los estándares validados.</em>
            </p>
            <table>
                <tr>
                    <th>Métrica</th>
                    <th>Mínimo</th>
                    <th>Máximo</th>
                    <th>Media</th>
                    <th>Desv. Est.</th>
                </tr>
    """
    
    metrics = [
        ('Correlación', all_correlations, '{:.6f}'),
        ('Max Diferencia (AU)', all_max_diffs, '{:.6f}'),
        ('RMS', all_rms, '{:.6f}'),
        ('Offset Medio (AU)', all_mean_diffs, '{:.6f}')
    ]
    
    for name, values, fmt in metrics:
        html += f"""
                <tr>
                    <td><strong>{name}</strong></td>
                    <td>{fmt.format(min(values))}</td>
                    <td>{fmt.format(max(values))}</td>
                    <td>{fmt.format(np.mean(values))}</td>
                    <td>{fmt.format(np.std(values))}</td>
                </tr>
        """
    
    html += """
            </table>
    """
    
    # Offset global
    global_offset = np.mean(all_mean_diffs)
    avg_corr = np.mean(all_correlations)
    avg_max_diff = np.mean(all_max_diffs)
    avg_rms = np.mean(all_rms)
    
    html += f"""
            <h3 style="margin-top: 30px;">Métricas Clave</h3>
            <table>
                <tr>
                    <th>Métrica</th>
                    <th>Valor</th>
                    <th>Evaluación</th>
                </tr>
                <tr>
                    <td><strong>Offset Global del Kit</strong></td>
                    <td>{global_offset:.6f} AU</td>
                    <td>{evaluate_offset(global_offset)}</td>
                </tr>
                <tr>
                    <td><strong>Correlación Media</strong></td>
                    <td>{avg_corr:.6f}</td>
                    <td>{'<span class="status-good">✅ OK</span>' if avg_corr >= thresholds['correlation'] else '<span class="status-warning">⚠️ Revisar</span>'}</td>
                </tr>
                <tr>
                    <td><strong>Max Diferencia Media</strong></td>
                    <td>{avg_max_diff:.6f} AU</td>
                    <td>{'<span class="status-good">✅ OK</span>' if avg_max_diff <= thresholds['max_diff'] else '<span class="status-warning">⚠️ Revisar</span>'}</td>
                </tr>
                <tr>
                    <td><strong>RMS Media</strong></td>
                    <td>{avg_rms:.6f}</td>
                    <td>{'<span class="status-good">✅ OK</span>' if avg_rms <= thresholds['rms'] else '<span class="status-warning">⚠️ Revisar</span>'}</td>
                </tr>
            </table>
            <p style="margin-top: 10px; color: #6c757d; font-size: 0.9em;">
                <em><strong>Offset Global:</strong> Desplazamiento sistemático promedio entre mediciones pre y post-mantenimiento. 
                Valores cercanos a cero indican excelente alineamiento.</em>
            </p>
        </div>
    """
    
    return html


def evaluate_offset(offset):
    """Evalúa el offset según umbrales."""
    from config import OFFSET_LIMITS
    
    abs_offset = abs(offset)
    
    if abs_offset < OFFSET_LIMITS['negligible']:
        return '<span class="status-good">✅ Despreciable</span>'
    elif abs_offset < OFFSET_LIMITS['acceptable']:
        return '<span class="status-good">✓ Aceptable</span>'
    else:
        return '<span class="status-warning">⚠️ Significativo</span>'


def generate_results_table(results_df):
    """
    Genera la tabla de resultados detallados.
    
    Args:
        results_df (pd.DataFrame): DataFrame con resultados
        
    Returns:
        str: HTML de la tabla
    """
    html = """
        <div class="info-box" id="resultados-detallados">
            <h2>Resultados Detallados por Estándar</h2>
    """
    
    html += results_df.to_html(index=False, classes='table', border=0)
    
    html += """
        </div>
    """
    
    return html


def generate_global_overlay_plot(validation_data):
    """
    Genera el gráfico de overlay global.
    
    Args:
        validation_data (list): Datos de validación
        
    Returns:
        str: HTML con el gráfico embebido
    """
    colors_ref = ['#1f77b4', '#2ca02c', '#9467bd', '#8c564b', '#e377c2', 
                  '#7f7f7f', '#bcbd22', '#17becf', '#ff9896', '#c5b0d5']
    colors_curr = ['#ff7f0e', '#d62728', '#ff69b4', '#ffa500', '#dc143c',
                   '#ff4500', '#ff1493', '#ff6347', '#ff8c00', '#ff00ff']
    
    fig = go.Figure()
    
    if len(validation_data) == 0:
        return "<p>No hay datos disponibles</p>"
    
    channels = list(range(1, len(validation_data[0]['reference']) + 1))
    
    # Añadir espectros de referencia
    for i, data in enumerate(validation_data):
        color = colors_ref[i % len(colors_ref)]
        sample_label = f"{data['id']} - Ref"
        
        fig.add_trace(go.Scatter(
            x=channels,
            y=data['reference'],
            mode='lines',
            name=sample_label,
            line=dict(color=color, width=2),
            hovertemplate=f'<b>{sample_label}</b><br>Canal: %{{x}}<br>Absorbancia: %{{y:.6f}}<extra></extra>'
        ))
    
    # Añadir espectros actuales
    for i, data in enumerate(validation_data):
        color = colors_curr[i % len(colors_curr)]
        sample_label = f"{data['id']} - Act"
        
        fig.add_trace(go.Scatter(
            x=channels,
            y=data['current'],
            mode='lines',
            name=sample_label,
            line=dict(color=color, width=2, dash='dash'),
            hovertemplate=f'<b>{sample_label}</b><br>Canal: %{{x}}<br>Absorbancia: %{{y:.6f}}<extra></extra>'
        ))
    
    fig.update_layout(
        title='Comparación Global de Todos los Estándares',
        xaxis_title='Canal espectral',
        yaxis_title='Absorbancia',
        hovermode='closest',
        template='plotly_white',
        height=600,
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            font=dict(size=10)
        )
    )
    
    chart_html = fig.to_html(
        include_plotlyjs='cdn',
        div_id='global_overlay',
        config={'displayModeBar': True, 'responsive': True}
    )
    
    html = """
        <div class="info-box" id="vista-global">
            <h2>Vista Global de Espectros</h2>
            <p style="color: #6c757d; font-size: 0.95em;">
                <em>Comparación simultánea de todos los espectros validados. Las líneas sólidas representan 
                las mediciones de referencia (pre-mantenimiento) y las líneas punteadas las mediciones 
                actuales (post-mantenimiento).</em>
            </p>
    """
    
    html += wrap_chart_in_expandable(
        chart_html,
        "Ver comparación global de espectros",
        "global_overlay_expandable",
        default_open=False
    )
    
    html += "</div>"
    
    return html


def generate_individual_analysis(validation_data, num_channels):
    """
    Genera el análisis individual de cada estándar.
    
    Args:
        validation_data (list): Datos de validación
        num_channels (int): Número de canales espectrales
        
    Returns:
        str: HTML con análisis individual
    """
    from config import CRITICAL_REGIONS
    
    html = """
        <div class="info-box" id="analisis-individual">
            <h2>Análisis Individual de Estándares</h2>
            <p style="color: #6c757d; font-size: 0.95em;">
                <em>Análisis detallado de cada estándar validado con gráficos de espectros, 
                diferencias y regiones críticas.</em>
            </p>
    """
    
    for data in validation_data:
        sample_id = data['id']
        reference = data['reference']
        current = data['current']
        diff = data['diff']
        val_res = data['validation_results']
        
        # Determinar estado
        if val_res['pass'] and not data['has_shift']:
            estado = "✅ OK"
            estado_class = "status-good"
        elif val_res['pass'] and data['has_shift']:
            estado = "⚠️ Revisar"
            estado_class = "status-warning"
        else:
            estado = "❌ Fallo"
            estado_class = "status-bad"
        
        html += f"""
            <div id="standard-{sample_id}" style="margin: 30px 0; padding: 20px; background-color: #fafafa; border-radius: 8px; page-break-inside: avoid;">
                <h3>Estándar: {sample_id} <span class="{estado_class}">[{estado}]</span></h3>
                
                <table style="margin: 15px 0;">
                    <tr>
                        <th>Métrica</th>
                        <th>Valor</th>
                        <th>Evaluación</th>
                    </tr>
                    <tr>
                        <td><strong>Correlación</strong></td>
                        <td>{val_res['correlation']:.6f}</td>
                        <td>{'✅' if val_res['checks']['correlation'] else '❌'}</td>
                    </tr>
                    <tr>
                        <td><strong>Max Diferencia</strong></td>
                        <td>{val_res['max_diff']:.6f} AU</td>
                        <td>{'✅' if val_res['checks']['max_diff'] else '❌'}</td>
                    </tr>
                    <tr>
                        <td><strong>RMS</strong></td>
                        <td>{val_res['rms']:.6f}</td>
                        <td>{'✅' if val_res['checks']['rms'] else '❌'}</td>
                    </tr>
                    <tr>
                        <td><strong>Offset Medio</strong></td>
                        <td>{val_res['mean_diff']:.6f} AU</td>
                        <td>Referencia</td>
                    </tr>
                    <tr>
                        <td><strong>Shift Espectral</strong></td>
                        <td>{data['shift_magnitude']:.1f} px</td>
                        <td>{'⚠️ Detectado' if data['has_shift'] else '✅ No detectado'}</td>
                    </tr>
                </table>
        """
        
        # Gráfico de validación
        fig = create_validation_plot_for_report(reference, current, diff, sample_id)
        chart_html = fig.to_html(
            include_plotlyjs='cdn',
            div_id=f'validation_{sample_id}',
            config={'displayModeBar': True, 'responsive': True}
        )
        
        html += wrap_chart_in_expandable(
            chart_html,
            f"Ver gráficos de validación - {sample_id}",
            f"validation_{sample_id}_expandable",
            default_open=False
        )
        
        # Análisis de regiones críticas
        regions_df = analyze_critical_regions_for_report(reference, current, CRITICAL_REGIONS, num_channels)
        html += f"""
                <h4>Regiones Espectrales Críticas</h4>
                {regions_df.to_html(index=False, classes='table', border=0)}
                <p style="color: #6c757d; font-size: 0.9em; margin-top: 5px;">
                    <em>* = Región ajustada a rango del instrumento (900-1700 nm)</em>
                </p>
            </div>
        """
    
    html += "</div>"
    
    return html


def create_validation_plot_for_report(reference, current, diff, sample_label):
    """Crea gráfico de 3 paneles para el reporte."""
    channels = list(range(1, len(reference) + 1))
    
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=(
            f'Espectros: Referencia vs Actual',
            'Diferencia (Actual - Referencia)',
            'Diferencia Acumulada'
        ),
        vertical_spacing=0.1,
        row_heights=[0.4, 0.3, 0.3]
    )
    
    # Panel 1: Overlay
    fig.add_trace(
        go.Scatter(x=channels, y=reference, name='Referencia',
                  line=dict(color='blue', width=2)),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=channels, y=current, name='Actual',
                  line=dict(color='red', width=2, dash='dash')),
        row=1, col=1
    )
    
    # Panel 2: Diferencia
    fig.add_trace(
        go.Scatter(x=channels, y=diff, name='Δ',
                  line=dict(color='green', width=2),
                  fill='tozeroy', fillcolor='rgba(0,255,0,0.1)'),
        row=2, col=1
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5, row=2, col=1)
    
    # Panel 3: Diferencia acumulada
    cumsum_diff = np.cumsum(diff)
    fig.add_trace(
        go.Scatter(x=channels, y=cumsum_diff, name='Σ Δ',
                  line=dict(color='purple', width=2)),
        row=3, col=1
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5, row=3, col=1)
    
    fig.update_xaxes(title_text="Canal espectral", row=3, col=1)
    fig.update_yaxes(title_text="Absorbancia", row=1, col=1)
    fig.update_yaxes(title_text="Δ Absorbancia", row=2, col=1)
    fig.update_yaxes(title_text="Σ Δ", row=3, col=1)
    
    fig.update_layout(
        height=800,
        showlegend=False,
        template='plotly_white',
        hovermode='x unified'
    )
    
    return fig


def analyze_critical_regions_for_report(reference, current, regions, num_channels):
    """Analiza regiones críticas para el reporte."""
    wavelength_per_pixel = 800 / num_channels
    start_wl = 900
    end_wl = 1700
    
    results = []
    
    for wl_start, wl_end in regions:
        if wl_end < start_wl or wl_start > end_wl:
            results.append({
                'Región (nm)': f"{wl_start}-{wl_end}",
                'Canales': "Fuera de rango",
                'Max |Δ|': "N/A",
                'RMS': "N/A",
                'Media Δ': "N/A"
            })
            continue
        
        wl_start_adjusted = max(wl_start, start_wl)
        wl_end_adjusted = min(wl_end, end_wl)
        
        px_start = int((wl_start_adjusted - start_wl) / wavelength_per_pixel)
        px_end = int((wl_end_adjusted - start_wl) / wavelength_per_pixel)
        
        px_start = max(0, px_start)
        px_end = min(num_channels, px_end)
        
        if px_end <= px_start:
            results.append({
                'Región (nm)': f"{wl_start}-{wl_end}",
                'Canales': "Región muy pequeña",
                'Max |Δ|': "N/A",
                'RMS': "N/A",
                'Media Δ': "N/A"
            })
            continue
        
        ref_region = reference[px_start:px_end]
        curr_region = current[px_start:px_end]
        diff_region = curr_region - ref_region
        
        region_label = f"{wl_start}-{wl_end}"
        if wl_start_adjusted != wl_start or wl_end_adjusted != wl_end:
            region_label += " *"
        
        results.append({
            'Región (nm)': region_label,
            'Canales': f"{px_start}-{px_end}",
            'Max |Δ|': f"{np.abs(diff_region).max():.6f}",
            'RMS': f"{np.sqrt(np.mean(diff_region**2)):.6f}",
            'Media Δ': f"{np.mean(diff_region):.6f}"
        })
    
    return pd.DataFrame(results)


def generate_footer():
    """Genera el footer del informe."""
    html = f"""
        <div style="margin-top: 50px; padding-top: 20px; border-top: 2px solid #eee; text-align: center; color: #666; font-size: 12px;">
            <p>Informe generado automáticamente por COREF Suite - Standard Validation Tool</p>
            <p>Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>© {datetime.now().year} BÜCHI Labortechnik AG</p>
        </div>
    </body>
    </html>
    """
    return html


def generate_validation_report(data: Dict) -> str:
    """
    Genera un informe HTML completo de validación de estándares.
    
    Args:
        data: Diccionario con toda la información necesaria:
            - sensor_serial
            - customer_name
            - technician_name
            - service_notes
            - validation_data
            - results_df
            - thresholds
            - n_ok, n_warn, n_fail
            - num_channels
            - ref_filename, curr_filename
        
    Returns:
        String con contenido HTML del informe
    """
    html = start_html_document(data)
    html += generate_executive_summary(data)
    html += generate_validation_criteria(data['thresholds'])
    html += generate_global_statistics(data['validation_data'], data['thresholds'])
    html += generate_results_table(data['results_df'])
    html += generate_global_overlay_plot(data['validation_data'])
    html += generate_individual_analysis(data['validation_data'], data['num_channels'])
    html += generate_footer()
    
    return html