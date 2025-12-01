"""
Offset Adjustment Report Generator
===================================
Genera informes HTML para ajustes de offset en baseline NIR.
Incluye análisis pre/post ajuste con validación de estándares.
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
            .success-box { background-color: #d4edda; padding: 20px; margin: 20px 0; border-radius: 5px; border-left: 4px solid #28a745; }
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
    validation_data_original = report_data['validation_data_original']
    offset_value = report_data['offset_value']
    
    # Construir índice del sidebar
    sections = [
        ("info-servicio", "Información del Servicio"),
        ("resumen-ejecutivo", "Resumen Ejecutivo"),
        ("analisis-offset", "Análisis del Offset"),
        ("comparacion-metricas", "Comparación de Métricas"),
        ("vista-global", "Vista Global de Espectros"),
        ("baseline-adjustment", "Ajuste del Baseline"),
    ]
    
    sidebar_items = []
    for sid, label in sections:
        sidebar_items.append(f'<li><a href="#{sid}">{label}</a></li>')
    
    # Sub-índice de estándares individuales
    standards_submenu = []
    for data in validation_data_original:
        sample_id = data['id']
        standards_submenu.append(f'<li><a href="#standard-{sample_id}">📊 {sample_id}</a></li>')
    
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
    
    # Añadir recomendaciones
    sidebar_items.append('<li><a href="#recomendaciones">💡 Recomendaciones</a></li>')
    
    sidebar_html = "\n".join(sidebar_items)
    
    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Informe de Ajuste de Offset - {sensor_serial}</title>
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
                grid-template-columns: repeat(3, 1fr);
                gap: 20px;
                margin: 20px 0;
            }}
            
            .metric-card {{
                padding: 20px;
                border-radius: 8px;
                text-align: center;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            
            .metric-card.offset {{
                background-color: #e3f2fd;
                border-left: 4px solid #2196f3;
            }}
            
            .metric-card.standards {{
                background-color: #f3e5f5;
                border-left: 4px solid #9c27b0;
            }}
            
            .metric-card.improvement {{
                background-color: #e8f5e9;
                border-left: 4px solid #4caf50;
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
            
            .comparison-table {{
                margin: 20px 0;
            }}
            
            .comparison-table th {{
                text-align: center;
            }}
            
            .improvement {{
                color: #4caf50;
                font-weight: bold;
            }}
            
            .degradation {{
                color: #f44336;
                font-weight: bold;
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
            <h1>Informe de Ajuste de Offset para Baseline NIR</h1>
            
            <div class="info-box" id="info-servicio">
                <h2>Información del Servicio</h2>
                <table>
                    <tr><th>Campo</th><th>Valor</th></tr>
                    <tr><td><strong>Cliente</strong></td><td>{customer_name}</td></tr>
                    <tr><td><strong>Técnico</strong></td><td>{technician_name}</td></tr>
                    <tr><td><strong>Número de Serie</strong></td><td>{sensor_serial}</td></tr>
                    <tr><td><strong>Fecha del Informe</strong></td><td>{report_date}</td></tr>
                    <tr><td><strong>TSV Referencia</strong></td><td>{report_data['ref_filename']}</td></tr>
                    <tr><td><strong>TSV Actual</strong></td><td>{report_data['curr_filename']}</td></tr>
                    <tr><td><strong>Baseline Original</strong></td><td>{report_data['baseline_filename']}</td></tr>
                    <tr><td><strong>Offset Aplicado</strong></td><td><span style="font-size: 18px; font-weight: bold; color: #2196f3;">{offset_value:+.6f} AU</span></td></tr>
                    <tr><td><strong>Notas del Servicio</strong></td><td>{service_notes if service_notes else 'N/A'}</td></tr>
                </table>
            </div>
    """
    
    return html


def generate_executive_summary(report_data):
    """
    Genera la sección de resumen ejecutivo.
    """
    offset_value = report_data['offset_value']
    n_standards = len(report_data['validation_data_original'])
    
    # Calcular offsets globales (AÑADIR ESTAS LÍNEAS AL INICIO)
    global_offset_orig = report_data['global_offset_original']
    global_offset_sim = report_data['global_offset_simulated']
    
    # Calcular reducciones
    validation_data_orig = report_data['validation_data_original']
    validation_data_sim = report_data['validation_data_simulated']

    # Calcular métricas globales
    avg_max_orig = np.mean([d['validation_results']['max_diff'] for d in validation_data_orig])
    avg_max_sim = np.mean([d['validation_results']['max_diff'] for d in validation_data_sim])
    reduction_max = avg_max_orig - avg_max_sim

    avg_rms_orig = np.mean([d['validation_results']['rms'] for d in validation_data_orig])
    avg_rms_sim = np.mean([d['validation_results']['rms'] for d in validation_data_sim])
    reduction_rms = avg_rms_orig - avg_rms_sim
    
    if abs(global_offset_orig) > 0.000001:
        improvement_pct = (1 - abs(global_offset_sim) / abs(global_offset_orig)) * 100
    else:
        improvement_pct = 0
    
    html = f"""
        <div class="info-box" id="resumen-ejecutivo">
            <h2>Resumen Ejecutivo</h2>
            <div class="metrics-grid">
                <div class="metric-card offset">
                    <div class="metric-value">{offset_value:+.6f}</div>
                    <div class="metric-label">Offset Aplicado (AU)</div>
                </div>
                <div class="metric-card improvement">
                    <div class="metric-value">{reduction_max:+.6f}</div>
                    <div class="metric-label">Reducción Max Δ Media (AU)</div>
                    <div style="font-size: 11px; color: #666; margin-top: 8px;">
                        {avg_max_orig:.6f} → {avg_max_sim:.6f}
                    </div>
                </div>
                <div class="metric-card improvement">
                    <div class="metric-value">{reduction_rms:+.6f}</div>
                    <div class="metric-label">Reducción RMS Media</div>
                    <div style="font-size: 11px; color: #666; margin-top: 8px;">
                        {avg_rms_orig:.6f} → {avg_rms_sim:.6f}
                    </div>
                </div>
            </div>
    """
    
    # Evaluación de la corrección
    global_offset_orig = report_data['global_offset_original']
    global_offset_sim = report_data['global_offset_simulated']

    # Evaluar basado en las reducciones de Max Δ y RMS
    if reduction_max > 0 and reduction_rms > 0 and abs(global_offset_sim) < 0.003:
        status = "✅ CORRECCIÓN EXCELENTE"
        status_class = "success-box"
        explanation = f"""
            <p><strong>El ajuste de offset ha sido exitoso.</strong></p>
            <ul>
                <li>Max Δ reducido: <strong>{reduction_max:+.6f} AU</strong></li>
                <li>RMS reducido: <strong>{reduction_rms:+.6f}</strong></li>
                <li>Bias global final: <strong>{global_offset_sim:+.6f} AU</strong> (despreciable)</li>
            </ul>
            <p>El equipo está correctamente ajustado y listo para operación.</p>
        """
    elif reduction_max > 0 and reduction_rms > 0:
        status = "✅ MEJORA SIGNIFICATIVA"
        status_class = "success-box"
        explanation = f"""
            <p><strong>El ajuste de offset ha mejorado las métricas del equipo.</strong></p>
            <ul>
                <li>Max Δ reducido: <strong>{reduction_max:+.6f} AU</strong></li>
                <li>RMS reducido: <strong>{reduction_rms:+.6f}</strong></li>
                <li>Bias global: de <strong>{global_offset_orig:+.6f} AU</strong> a <strong>{global_offset_sim:+.6f} AU</strong></li>
            </ul>
            <p>Se recomienda validar con mediciones reales de los estándares usando el baseline ajustado.</p>
        """
    else:
        status = "⚠️ REQUIERE REVISIÓN"
        status_class = "warning-box"
        explanation = f"""
            <p><strong>El offset aplicado no mejora consistentemente las métricas.</strong></p>
            <ul>
                <li>Cambio en Max Δ: <strong>{reduction_max:+.6f} AU</strong></li>
                <li>Cambio en RMS: <strong>{reduction_rms:+.6f}</strong></li>
                <li>Bias: de <strong>{global_offset_orig:+.6f} AU</strong> a <strong>{global_offset_sim:+.6f} AU</strong></li>
            </ul>
            <p><strong>Recomendaciones:</strong></p>
            <ul>
                <li>Revisar el cálculo del offset necesario</li>
                <li>Considerar aplicar un offset de signo contrario</li>
                <li>Verificar que los estándares de referencia son correctos</li>
            </ul>
        """
    
    html += f"""
            <div class="{status_class}" style="margin-top: 20px;">
                <h3>{status}</h3>
                {explanation}
            </div>
        </div>
    """
    
    return html


def generate_offset_analysis(report_data):
    """
    Genera la sección de análisis del offset.
    """
    offset_value = report_data['offset_value']
    global_offset_orig = report_data['global_offset_original']
    
    html = f"""
        <div class="info-box" id="analisis-offset">
            <h2>Análisis del Offset</h2>
            
            <h3>Cálculo del Offset</h3>
            <table>
                <tr>
                    <th>Parámetro</th>
                    <th>Valor</th>
                    <th>Descripción</th>
                </tr>
                <tr>
                    <td><strong>Offset Global Detectado</strong></td>
                    <td>{global_offset_orig:+.6f} AU</td>
                    <td>Desplazamiento sistemático promedio entre referencia y actual</td>
                </tr>
                <tr>
                    <td><strong>Offset Aplicado al Baseline</strong></td>
                    <td>{offset_value:+.6f} AU</td>
                    <td>Valor de corrección aplicado uniformemente a todos los canales</td>
                </tr>
            </table>
            
            <h3>Justificación del Ajuste</h3>
            <p style="line-height: 1.6;">
                El offset aplicado al baseline tiene como objetivo corregir el desplazamiento sistemático 
                detectado en las mediciones de los estándares ópticos. Este desplazamiento puede ser causado por:
            </p>
            <ul style="line-height: 1.8;">
                <li><strong>Cambio de lámpara:</strong> Diferencias en la intensidad luminosa entre la lámpara antigua y nueva</li>
                <li><strong>Deriva temporal:</strong> Envejecimiento de componentes ópticos</li>
                <li><strong>Condiciones ambientales:</strong> Cambios en temperatura o humedad durante las mediciones</li>
            </ul>
            
            <h3>Mecanismo de Corrección</h3>
            <p style="line-height: 1.6;">
                La corrección por offset es un ajuste <strong>uniforme</strong> aplicado a todos los canales espectrales:
            </p>
            <div style="background-color: #f0f0f0; padding: 15px; border-radius: 5px; font-family: monospace;">
                Baseline_ajustado[i] = Baseline_original[i] - Offset
            </div>
            <p style="margin-top: 10px; line-height: 1.6;">
                Este tipo de corrección:
            </p>
            <ul style="line-height: 1.8;">
                <li>✅ Preserva completamente la <strong>forma espectral</strong></li>
                <li>✅ Es <strong>reversible</strong> (puede deshacerse aplicando el offset opuesto)</li>
                <li>✅ Tiene <strong>bajo riesgo</strong> de introducir artefactos</li>
                <li>✅ Es apropiado para corregir bias sistemáticos</li>
            </ul>
        </div>
    """
    
    return html


def generate_metrics_comparison(report_data):
    """
    Genera la sección de comparación de métricas pre/post ajuste.
    """
    validation_data_orig = report_data['validation_data_original']
    validation_data_sim = report_data['validation_data_simulated']
    offset_value = report_data['offset_value']
    
    # Calcular estadísticas globales
    metrics_orig = calculate_global_metrics(validation_data_orig)
    metrics_sim = calculate_global_metrics(validation_data_sim)
    
    html = f"""
        <div class="info-box" id="comparacion-metricas">
            <h2>Comparación de Métricas: Original vs Simulado</h2>
            <p style="color: #6c757d; font-size: 0.95em; margin-bottom: 20px;">
                <em>Análisis del impacto del offset ({offset_value:+.6f} AU) en las métricas de validación.</em>
            </p>
            
            <h3>Estadísticas Globales del Kit</h3>
            <table class="comparison-table">
                <tr>
                    <th>Métrica</th>
                    <th>Media Original</th>
                    <th>Media Simulado</th>
                    <th>Desv. Est. Original</th>
                    <th>Desv. Est. Simulado</th>
                    <th>Cambio</th>
                </tr>
    """
    
    # Correlación
    delta_corr = metrics_sim['corr_mean'] - metrics_orig['corr_mean']
    html += f"""
                <tr>
                    <td><strong>Correlación</strong></td>
                    <td>{metrics_orig['corr_mean']:.6f}</td>
                    <td>{metrics_sim['corr_mean']:.6f}</td>
                    <td>{metrics_orig['corr_std']:.6f}</td>
                    <td>{metrics_sim['corr_std']:.6f}</td>
                    <td>{format_change(delta_corr)}</td>
                </tr>
    """
    
    # Max Δ
    delta_max = metrics_sim['max_mean'] - metrics_orig['max_mean']
    html += f"""
                <tr>
                    <td><strong>Max Δ (AU)</strong></td>
                    <td>{metrics_orig['max_mean']:.6f}</td>
                    <td>{metrics_sim['max_mean']:.6f}</td>
                    <td>{metrics_orig['max_std']:.6f}</td>
                    <td>{metrics_sim['max_std']:.6f}</td>
                    <td>{format_change(delta_max, inverse=True)}</td>
                </tr>
    """
    
    # RMS
    delta_rms = metrics_sim['rms_mean'] - metrics_orig['rms_mean']
    html += f"""
                <tr>
                    <td><strong>RMS</strong></td>
                    <td>{metrics_orig['rms_mean']:.6f}</td>
                    <td>{metrics_sim['rms_mean']:.6f}</td>
                    <td>{metrics_orig['rms_std']:.6f}</td>
                    <td>{metrics_sim['rms_std']:.6f}</td>
                    <td>{format_change(delta_rms, inverse=True)}</td>
                </tr>
    """
    
    # Offset Medio
    delta_offset = metrics_sim['offset_mean'] - metrics_orig['offset_mean']
    html += f"""
                <tr>
                    <td><strong>Offset Medio (AU)</strong></td>
                    <td>{metrics_orig['offset_mean']:+.6f}</td>
                    <td>{metrics_sim['offset_mean']:+.6f}</td>
                    <td>{metrics_orig['offset_std']:.6f}</td>
                    <td>{metrics_sim['offset_std']:.6f}</td>
                    <td>{format_change(delta_offset, inverse=True, show_sign=True)}</td>
                </tr>
    """
    
    html += """
            </table>
    """
    
    # Gráfico de impacto
    fig = create_impact_comparison_chart(metrics_orig, metrics_sim, offset_value)
    chart_html = fig.to_html(
        include_plotlyjs='cdn',
        div_id='impact_comparison',
        config={'displayModeBar': True, 'responsive': True}
    )
    
    html += wrap_chart_in_expandable(
        chart_html,
        "Ver gráfico de impacto del offset en métricas",
        "impact_comparison_expandable",
        default_open=True
    )
    
    html += """
        </div>
    """
    
    return html


def calculate_global_metrics(validation_data):
    """Calcula métricas globales de un conjunto de validaciones."""
    corr_list = [d['validation_results']['correlation'] for d in validation_data]
    max_list = [d['validation_results']['max_diff'] for d in validation_data]
    rms_list = [d['validation_results']['rms'] for d in validation_data]
    offset_list = [d['validation_results']['mean_diff'] for d in validation_data]
    
    return {
        'corr_mean': np.mean(corr_list),
        'corr_std': np.std(corr_list),
        'max_mean': np.mean(max_list),
        'max_std': np.std(max_list),
        'rms_mean': np.mean(rms_list),
        'rms_std': np.std(rms_list),
        'offset_mean': np.mean(offset_list),
        'offset_std': np.std(offset_list),
    }


def format_change(delta, inverse=False, show_sign=False):
    """
    Formatea el cambio con color según si es mejora o empeoramiento.
    
    Args:
        delta: Cambio en la métrica
        inverse: Si True, un valor negativo es mejora (para Max Δ, RMS)
        show_sign: Si True, muestra el signo incluso para abs()
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


def create_impact_comparison_chart(metrics_orig, metrics_sim, offset_value):
    """Crea gráfico de barras comparando métricas."""
    metrics_names = ['Max Δ (AU)', 'RMS', 'Offset Medio']
    original_values = [
        metrics_orig['max_mean'],
        metrics_orig['rms_mean'],
        abs(metrics_orig['offset_mean'])
    ]
    simulated_values = [
        metrics_sim['max_mean'],
        metrics_sim['rms_mean'],
        abs(metrics_sim['offset_mean'])
    ]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Sin Offset',
        x=metrics_names,
        y=original_values,
        marker_color='lightblue',
        text=[f"{v:.6f}" for v in original_values],
        textposition='outside'
    ))
    
    fig.add_trace(go.Bar(
        name=f'Con Offset ({offset_value:+.6f} AU)',
        x=metrics_names,
        y=simulated_values,
        marker_color='lightgreen',
        text=[f"{v:.6f}" for v in simulated_values],
        textposition='outside'
    ))
    
    fig.update_layout(
        title=f"Impacto del Offset en Métricas de Validación",
        barmode='group',
        yaxis_title="Valor",
        template='plotly_white',
        height=400,
        yaxis=dict(
            range=[0, max(max(original_values), max(simulated_values)) * 1.15]
        )
    )
    
    return fig


def generate_global_overlay_plot(report_data):
    """
    Genera el gráfico de overlay global con 3 tipos de espectros.
    """
    validation_data_orig = report_data['validation_data_original']
    validation_data_sim = report_data['validation_data_simulated']
    offset_value = report_data['offset_value']
    
    colors_ref = ['#1f77b4', '#2ca02c', '#9467bd', '#8c564b', '#e377c2']
    colors_orig = ['#ff7f0e', '#d62728', '#ff69b4', '#ffa500', '#dc143c']
    colors_sim = ['#00cc00', '#00ff00', '#90ee90', '#32cd32', '#00fa9a']
    
    fig = go.Figure()
    
    if len(validation_data_orig) == 0:
        return "<p>No hay datos disponibles</p>"
    
    channels = list(range(1, len(validation_data_orig[0]['reference']) + 1))
    
    # Añadir espectros de referencia
    for i, data in enumerate(validation_data_orig):
        color = colors_ref[i % len(colors_ref)]
        sample_label = f"{data['id']} - Ref"
        
        fig.add_trace(go.Scatter(
            x=channels,
            y=data['reference'],
            mode='lines',
            name=sample_label,
            line=dict(color=color, width=2),
            legendgroup='reference',
            hovertemplate=f'<b>{sample_label}</b><br>Canal: %{{x}}<br>Abs: %{{y:.6f}}<extra></extra>'
        ))
    
    # Añadir espectros originales
    for i, data in enumerate(validation_data_orig):
        color = colors_orig[i % len(colors_orig)]
        sample_label = f"{data['id']} - Orig"
        
        fig.add_trace(go.Scatter(
            x=channels,
            y=data['current'],
            mode='lines',
            name=sample_label,
            line=dict(color=color, width=2, dash='dash'),
            legendgroup='original',
            hovertemplate=f'<b>{sample_label}</b><br>Canal: %{{x}}<br>Abs: %{{y:.6f}}<extra></extra>'
        ))
    
    # Añadir espectros simulados
    for i, data in enumerate(validation_data_sim):
        color = colors_sim[i % len(colors_sim)]
        sample_label = f"{data['id']} - Sim"
        
        fig.add_trace(go.Scatter(
            x=channels,
            y=data['current'],
            mode='lines',
            name=sample_label,
            line=dict(color=color, width=2, dash='dot'),
            legendgroup='simulated',
            hovertemplate=f'<b>{sample_label}</b><br>Canal: %{{x}}<br>Abs: %{{y:.6f}}<extra></extra>'
        ))
    
    fig.update_layout(
        title={
            'text': f'Comparación Global: Referencia vs Original vs Simulado (Offset: {offset_value:+.6f} AU)',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 16, 'color': '#2c5f3f'}
        },
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
            font=dict(size=9)
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
                <em>Comparación simultánea de todos los espectros. Líneas sólidas: referencia (azul). 
                Líneas discontinuas: actual sin offset (rojo). Líneas punteadas: actual con offset aplicado (verde).</em>
            </p>
    """
    
    html += wrap_chart_in_expandable(
        chart_html,
        "Ver comparación global de espectros (3 estados)",
        "global_overlay_expandable",
        default_open=False
    )
    
    html += "</div>"
    
    return html


def generate_baseline_adjustment_section(report_data):
    """
    Genera la sección de ajuste del baseline.
    """
    baseline_original = report_data['baseline_original']
    baseline_adjusted = report_data['baseline_adjusted']
    offset_value = report_data['offset_value']
    
    html = """
        <div class="info-box" id="baseline-adjustment">
            <h2>Ajuste del Baseline</h2>
            <p style="color: #6c757d; font-size: 0.95em;">
                <em>Visualización del baseline original y el baseline ajustado con el offset aplicado.</em>
            </p>
    """
    
    # Estadísticas del baseline
    orig_mean = np.mean(baseline_original)
    adj_mean = np.mean(baseline_adjusted)
    
    html += f"""
            <h3>Estadísticas del Baseline</h3>
            <table>
                <tr>
                    <th>Parámetro</th>
                    <th>Original</th>
                    <th>Ajustado</th>
                    <th>Cambio</th>
                </tr>
                <tr>
                    <td><strong>Media</strong></td>
                    <td>{orig_mean:.6f} AU</td>
                    <td>{adj_mean:.6f} AU</td>
                    <td>{offset_value:+.6f} AU</td>
                </tr>
                <tr>
                    <td><strong>Mínimo</strong></td>
                    <td>{np.min(baseline_original):.6f} AU</td>
                    <td>{np.min(baseline_adjusted):.6f} AU</td>
                    <td>{np.min(baseline_adjusted) - np.min(baseline_original):+.6f} AU</td>
                </tr>
                <tr>
                    <td><strong>Máximo</strong></td>
                    <td>{np.max(baseline_original):.6f} AU</td>
                    <td>{np.max(baseline_adjusted):.6f} AU</td>
                    <td>{np.max(baseline_adjusted) - np.max(baseline_original):+.6f} AU</td>
                </tr>
                <tr>
                    <td><strong>Desv. Est.</strong></td>
                    <td>{np.std(baseline_original):.6f} AU</td>
                    <td>{np.std(baseline_adjusted):.6f} AU</td>
                    <td>{np.std(baseline_adjusted) - np.std(baseline_original):+.6f} AU</td>
                </tr>
            </table>
            <p style="margin-top: 10px; color: #6c757d; font-size: 0.9em;">
                <em>Nota: La desviación estándar se mantiene constante, confirmando que 
                la forma espectral ha sido preservada.</em>
            </p>
    """
    
    # Gráfico del baseline
    fig = create_baseline_comparison_plot(baseline_original, baseline_adjusted, offset_value)
    chart_html = fig.to_html(
        include_plotlyjs='cdn',
        div_id='baseline_comparison',
        config={'displayModeBar': True, 'responsive': True}
    )
    
    html += wrap_chart_in_expandable(
        chart_html,
        "Ver gráfico de comparación de baseline",
        "baseline_comparison_expandable",
        default_open=True
    )
    
    html += """
        </div>
    """
    
    return html


def create_baseline_comparison_plot(baseline_orig, baseline_adj, offset_value):
    """Crea gráfico de comparación del baseline."""
    channels = list(range(1, len(baseline_orig) + 1))
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(
            'Baseline: Original vs Ajustado',
            'Diferencia Aplicada (Offset)'
        ),
        vertical_spacing=0.15,
        row_heights=[0.65, 0.35]
    )
    
    # Panel 1: Overlay
    fig.add_trace(
        go.Scatter(x=channels, y=baseline_orig, name='Original',
                  line=dict(color='blue', width=2)),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=channels, y=baseline_adj, name='Ajustado',
                  line=dict(color='green', width=2, dash='dash')),
        row=1, col=1
    )
    
    # Panel 2: Diferencia (debe ser constante = -offset)
    diff = baseline_adj - baseline_orig
    fig.add_trace(
        go.Scatter(x=channels, y=diff, name='Diferencia',
                  line=dict(color='red', width=2),
                  fill='tozeroy', fillcolor='rgba(255,0,0,0.1)'),
        row=2, col=1
    )
    fig.add_hline(y=-offset_value, line_dash="dash", line_color="orange", 
                 annotation_text=f"Offset = {-offset_value:.6f}", 
                 row=2, col=1)
    
    fig.update_xaxes(title_text="Canal espectral", row=2, col=1)
    fig.update_yaxes(title_text="Absorbancia", row=1, col=1)
    fig.update_yaxes(title_text="Δ Absorbancia", row=2, col=1)
    
    fig.update_layout(
        height=600,
        showlegend=True,
        template='plotly_white',
        hovermode='x unified'
    )
    
    return fig


def generate_individual_analysis(report_data):
    """
    Genera el análisis individual de cada estándar.
    """
    validation_data_orig = report_data['validation_data_original']
    validation_data_sim = report_data['validation_data_simulated']
    offset_value = report_data['offset_value']
    
    html = """
        <div class="info-box" id="analisis-individual">
            <h2>Análisis Individual de Estándares</h2>
            <p style="color: #6c757d; font-size: 0.95em;">
                <em>Análisis detallado de cada estándar mostrando el impacto del offset en las métricas de validación.</em>
            </p>
    """
    
    for i, (data_orig, data_sim) in enumerate(zip(validation_data_orig, validation_data_sim)):
        sample_id = data_orig['id']
        reference = data_orig['reference']
        current_orig = data_orig['current']
        current_sim = data_sim['current']
        
        val_orig = data_orig['validation_results']
        val_sim = data_sim['validation_results']
        
        html += f"""
            <div id="standard-{sample_id}" style="margin: 30px 0; padding: 20px; background-color: #fafafa; border-radius: 8px; page-break-inside: avoid;">
                <h3>Estándar: {sample_id}</h3>
                
                <h4>Comparación de Métricas</h4>
                <table>
                    <tr>
                        <th>Métrica</th>
                        <th>Original</th>
                        <th>Simulado</th>
                        <th>Cambio</th>
                    </tr>
                    <tr>
                        <td><strong>Correlación</strong></td>
                        <td>{val_orig['correlation']:.6f}</td>
                        <td>{val_sim['correlation']:.6f}</td>
                        <td>{format_change(val_sim['correlation'] - val_orig['correlation'])}</td>
                    </tr>
                    <tr>
                        <td><strong>Max Δ</strong></td>
                        <td>{val_orig['max_diff']:.6f} AU</td>
                        <td>{val_sim['max_diff']:.6f} AU</td>
                        <td>{format_change(val_sim['max_diff'] - val_orig['max_diff'], inverse=True)}</td>
                    </tr>
                    <tr>
                        <td><strong>RMS</strong></td>
                        <td>{val_orig['rms']:.6f}</td>
                        <td>{val_sim['rms']:.6f}</td>
                        <td>{format_change(val_sim['rms'] - val_orig['rms'], inverse=True)}</td>
                    </tr>
                    <tr>
                        <td><strong>Offset Medio</strong></td>
                        <td>{val_orig['mean_diff']:+.6f} AU</td>
                        <td>{val_sim['mean_diff']:+.6f} AU</td>
                        <td>{format_change(val_sim['mean_diff'] - val_orig['mean_diff'], inverse=True, show_sign=True)}</td>
                    </tr>
                </table>
        """
        
        # Gráfico del estándar
        fig = create_individual_standard_plot(reference, current_orig, current_sim, sample_id, offset_value)
        chart_html = fig.to_html(
            include_plotlyjs='cdn',
            div_id=f'standard_{sample_id}',
            config={'displayModeBar': True, 'responsive': True}
        )
        
        html += wrap_chart_in_expandable(
            chart_html,
            f"Ver gráficos comparativos - {sample_id}",
            f"standard_{sample_id}_expandable",
            default_open=False
        )
        
        html += """
            </div>
        """
    
    html += "</div>"
    
    return html


def create_individual_standard_plot(reference, current_orig, current_sim, sample_id, offset_value):
    """Crea gráfico de 3 paneles para análisis individual."""
    channels = list(range(1, len(reference) + 1))
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(
            f'Espectros: Referencia vs Actual (Original y Simulado) - {sample_id}',
            'Diferencias vs Referencia'
        ),
        vertical_spacing=0.15,
        row_heights=[0.6, 0.4]
    )
    
    # Panel 1: Overlay de espectros
    fig.add_trace(
        go.Scatter(x=channels, y=reference, name='Referencia',
                  line=dict(color='blue', width=2)),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=channels, y=current_orig, name='Actual (Original)',
                  line=dict(color='red', width=2, dash='dash')),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=channels, y=current_sim, name=f'Actual + Offset ({offset_value:+.6f})',
                  line=dict(color='green', width=2, dash='dot')),
        row=1, col=1
    )
    
    # Panel 2: Diferencias
    diff_orig = current_orig - reference
    diff_sim = current_sim - reference
    
    fig.add_trace(
        go.Scatter(x=channels, y=diff_orig, name='Δ Original',
                  line=dict(color='red', width=2),
                  fill='tozeroy', fillcolor='rgba(255,0,0,0.1)'),
        row=2, col=1
    )
    fig.add_trace(
        go.Scatter(x=channels, y=diff_sim, name='Δ Simulado',
                  line=dict(color='green', width=2),
                  fill='tozeroy', fillcolor='rgba(0,255,0,0.1)'),
        row=2, col=1
    )
    
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5, row=2, col=1)
    
    fig.update_xaxes(title_text="Canal espectral", row=2, col=1)
    fig.update_yaxes(title_text="Absorbancia", row=1, col=1)
    fig.update_yaxes(title_text="Δ Absorbancia", row=2, col=1)
    
    fig.update_layout(
        height=700,
        showlegend=True,
        template='plotly_white',
        hovermode='x unified'
    )
    
    return fig


def generate_recommendations(report_data):
    """
    Genera la sección de recomendaciones finales.
    """
    offset_value = report_data['offset_value']
    global_offset_sim = report_data['global_offset_simulated']
    
    html = """
        <div class="info-box" id="recomendaciones">
            <h2>💡 Recomendaciones Finales</h2>
    """
    
    if abs(global_offset_sim) < 0.003:
        html += """
            <div class="success-box">
                <h3>✅ Baseline Listo para Producción</h3>
                <p>El ajuste de offset ha sido exitoso. El bias residual es despreciable.</p>
            </div>
            
            <h3>Próximos Pasos:</h3>
            <ol style="line-height: 1.8;">
                <li><strong>Instalar el baseline ajustado</strong> en el equipo NIR</li>
                <li><strong>Verificar con mediciones reales</strong> de los estándares ópticos</li>
                <li><strong>Documentar el cambio</strong> en el log del equipo:
                    <ul>
                        <li>Fecha y hora del ajuste</li>
                        <li>Offset aplicado</li>
                        <li>Nombre del técnico</li>
                        <li>Razón del ajuste (cambio de lámpara, mantenimiento, etc.)</li>
                    </ul>
                </li>
                <li><strong>Mantener una copia</strong> del baseline original como backup</li>
                <li><strong>Validar calibraciones</strong> activas con muestras de referencia</li>
            </ol>
        """
    else:
        html += f"""
            <div class="warning-box">
                <h3>⚠️ Validación Adicional Recomendada</h3>
                <p>El bias residual ({global_offset_sim:+.6f} AU) sugiere que puede ser necesario un ajuste adicional.</p>
            </div>
            
            <h3>Acciones Recomendadas:</h3>
            <ol style="line-height: 1.8;">
                <li><strong>Instalar el baseline ajustado</strong> y medir los estándares realmente</li>
                <li><strong>Evaluar los resultados</strong> de las mediciones reales:
                    <ul>
                        <li>Si mejoran: el ajuste es correcto, documentar y finalizar</li>
                        <li>Si no mejoran: considerar ajuste iterativo con el nuevo offset medido</li>
                    </ul>
                </li>
                <li><strong>Revisar posibles causas</strong> del bias residual:
                    <ul>
                        <li>Condiciones ambientales durante las mediciones</li>
                        <li>Estado de los estándares ópticos (limpieza, deterioro)</li>
                        <li>Alineamiento óptico del equipo</li>
                    </ul>
                </li>
                <li><strong>Documentar todas las iteraciones</strong> del proceso de ajuste</li>
            </ol>
        """
    
    html += f"""
            <h3>Límites de Reproducibilidad:</h3>
            <table>
                <tr>
                    <th>Rango de Offset</th>
                    <th>Interpretación</th>
                    <th>Acción</th>
                </tr>
                <tr>
                    <td>&lt; 0.003 AU</td>
                    <td>Despreciable</td>
                    <td>✅ Dentro del ruido instrumental</td>
                </tr>
                <tr>
                    <td>0.003 - 0.010 AU</td>
                    <td>Aceptable</td>
                    <td>✓ Monitorear en próximas validaciones</td>
                </tr>
                <tr>
                    <td>&gt; 0.010 AU</td>
                    <td>Significativo</td>
                    <td>⚠️ Investigar causa raíz</td>
                </tr>
            </table>
            
            <h3>⚠️ Advertencias Importantes:</h3>
            <ul style="line-height: 1.8;">
                <li><strong>NO usar</strong> ajustes de offset para compensar problemas de calibración</li>
                <li><strong>NO aplicar</strong> offsets mayores a 0.020 AU sin investigar la causa</li>
                <li><strong>NO olvidar</strong> validar las calibraciones después del cambio de baseline</li>
                <li><strong>SIEMPRE</strong> mantener una copia del baseline original</li>
            </ul>
            
            <h3>Cuándo NO usar ajuste por offset:</h3>
            <ul style="line-height: 1.8;">
                <li>❌ Problemas de ruido o deriva espectral → Requiere servicio técnico</li>
                <li>❌ Desalineamientos ópticos → Requiere ajuste mecánico</li>
                <li>❌ Variaciones espectrales no uniformes → Requiere recalibración</li>
            </ul>
        </div>
    """
    
    return html


def generate_footer():
    """Genera el footer del informe."""
    html = f"""
        <div style="margin-top: 50px; padding-top: 20px; border-top: 2px solid #eee; text-align: center; color: #666; font-size: 12px;">
            <p>Informe generado automáticamente por COREF Suite - Baseline Offset Adjustment Tool</p>
            <p>Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>© {datetime.now().year} BÜCHI Labortechnik AG</p>
        </div>
    </body>
    </html>
    """
    return html


def generate_offset_adjustment_report(data: Dict) -> str:
    """
    Genera un informe HTML completo de ajuste de offset.
    
    Args:
        data: Diccionario con toda la información necesaria:
            - sensor_serial
            - customer_name
            - technician_name
            - service_notes
            - offset_value
            - validation_data_original (lista de dicts con validaciones sin offset)
            - validation_data_simulated (lista de dicts con validaciones con offset)
            - global_offset_original
            - global_offset_simulated
            - baseline_original (np.array)
            - baseline_adjusted (np.array)
            - ref_filename
            - curr_filename
            - baseline_filename
        
    Returns:
        String con contenido HTML del informe
    """
    html = start_html_document(data)
    html += generate_executive_summary(data)
    html += generate_offset_analysis(data)
    html += generate_metrics_comparison(data)
    html += generate_global_overlay_plot(data)
    html += generate_baseline_adjustment_section(data)
    html += generate_individual_analysis(data)
    html += generate_recommendations(data)
    html += generate_footer()
    
    return html