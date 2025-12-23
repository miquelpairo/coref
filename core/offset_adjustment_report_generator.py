"""
Offset Adjustment Report Generator (OPTIMIZED)
===============================================
Genera informes HTML para ajustes de offset en baseline NIR.
OPTIMIZADO: Usa funciones compartidas de core.report_utils

Author: Miquel
Date: December 2024
"""

from typing import Dict, List
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ===== IMPORTAR FUNCIONES COMPARTIDAS =====
from core.report_utils import (
    wrap_chart_in_expandable,
    build_sidebar_html,
    evaluate_offset,
    format_change,
    generate_service_info_section,
    generate_footer,
    start_html_template,
    calculate_global_metrics
)


def generate_executive_summary(report_data):
    """
    Genera la sección de resumen ejecutivo.
    """
    offset_value = report_data['offset_value']
    
    # Calcular offsets globales
    global_offset_orig = report_data['global_offset_original']
    global_offset_sim = report_data['global_offset_simulated']
    
    # Calcular métricas globales usando función compartida
    validation_data_orig = report_data['validation_data_original']
    validation_data_sim = report_data['validation_data_simulated']
    
    metrics_orig = calculate_global_metrics(validation_data_orig)
    metrics_sim = calculate_global_metrics(validation_data_sim)
    
    reduction_max = metrics_orig['max_mean'] - metrics_sim['max_mean']
    reduction_rms = metrics_orig['rms_mean'] - metrics_sim['rms_mean']
    
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
                    <div class="metric-subcaption">
                        {metrics_orig['max_mean']:.6f} → {metrics_sim['max_mean']:.6f}
                    </div>
                </div>
                <div class="metric-card improvement">
                    <div class="metric-value">{reduction_rms:+.6f}</div>
                    <div class="metric-label">Reducción RMS Media</div>
                    <div class="metric-subcaption">
                        {metrics_orig['rms_mean']:.6f} → {metrics_sim['rms_mean']:.6f}
                    </div>
                </div>
            </div>
    """
    
    # Evaluación de la corrección
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
            <div class="{status_class}" class="status-box-top-margin">
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
            <p class="text-spacious">
                El offset aplicado al baseline tiene como objetivo corregir el desplazamiento sistemático 
                detectado en las mediciones de los estándares ópticos. Este desplazamiento puede ser causado por:
            </p>
            <ul class="list-spacious">
                <li><strong>Cambio de lámpara:</strong> Diferencias en la intensidad luminosa entre la lámpara antigua y nueva</li>
                <li><strong>Deriva temporal:</strong> Envejecimiento de componentes ópticos</li>
                <li><strong>Condiciones ambientales:</strong> Cambios en temperatura o humedad durante las mediciones</li>
            </ul>
            
            <h3>Mecanismo de Corrección</h3>
            <p class="text-spacious">
                La corrección por offset es un ajuste <strong>uniforme</strong> aplicado a todos los canales espectrales:
            </p>
            <div class="code-box">
                Baseline_ajustado[i] = Baseline_original[i] - Offset
            </div>
            <p style="margin-top: 10px; line-height: 1.6;">
                Este tipo de corrección:
            </p>
            <ul class="list-spacious">
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
    
    # Calcular estadísticas globales usando función compartida
    metrics_orig = calculate_global_metrics(validation_data_orig)
    metrics_sim = calculate_global_metrics(validation_data_sim)
    
    html = f"""
        <div class="info-box" id="comparacion-metricas">
            <h2>Comparación de Métricas: Original vs Simulado</h2>
            <p class="text-caption description-bottom-margin">
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
    
    # Usar formato_change para formatear cambios
    delta_corr = metrics_sim['corr_mean'] - metrics_orig['corr_mean']
    delta_max = metrics_sim['max_mean'] - metrics_orig['max_mean']
    delta_rms = metrics_sim['rms_mean'] - metrics_orig['rms_mean']
    delta_offset = metrics_sim['offset_mean'] - metrics_orig['offset_mean']
    
    html += f"""
                <tr>
                    <td><strong>Correlación</strong></td>
                    <td>{metrics_orig['corr_mean']:.6f}</td>
                    <td>{metrics_sim['corr_mean']:.6f}</td>
                    <td>{metrics_orig['corr_std']:.6f}</td>
                    <td>{metrics_sim['corr_std']:.6f}</td>
                    <td>{format_change(delta_corr)}</td>
                </tr>
                <tr>
                    <td><strong>Max Δ (AU)</strong></td>
                    <td>{metrics_orig['max_mean']:.6f}</td>
                    <td>{metrics_sim['max_mean']:.6f}</td>
                    <td>{metrics_orig['max_std']:.6f}</td>
                    <td>{metrics_sim['max_std']:.6f}</td>
                    <td>{format_change(delta_max, inverse=True)}</td>
                </tr>
                <tr>
                    <td><strong>RMS</strong></td>
                    <td>{metrics_orig['rms_mean']:.6f}</td>
                    <td>{metrics_sim['rms_mean']:.6f}</td>
                    <td>{metrics_orig['rms_std']:.6f}</td>
                    <td>{metrics_sim['rms_std']:.6f}</td>
                    <td>{format_change(delta_rms, inverse=True)}</td>
                </tr>
                <tr>
                    <td><strong>Offset Medio (AU)</strong></td>
                    <td>{metrics_orig['offset_mean']:+.6f}</td>
                    <td>{metrics_sim['offset_mean']:+.6f}</td>
                    <td>{metrics_orig['offset_std']:.6f}</td>
                    <td>{metrics_sim['offset_std']:.6f}</td>
                    <td>{format_change(delta_offset, inverse=True, show_sign=True)}</td>
                </tr>
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
    
    # Añadir espectros (referencia, original, simulado)
    for i, data in enumerate(validation_data_orig):
        color_ref = colors_ref[i % len(colors_ref)]
        fig.add_trace(go.Scatter(
            x=channels, y=data['reference'], mode='lines',
            name=f"{data['id']} - Ref",
            line=dict(color=color_ref, width=2), legendgroup='reference',
            hovertemplate=f'<b>{data["id"]} - Ref</b><br>Canal: %{{x}}<br>Abs: %{{y:.6f}}<extra></extra>'
        ))
    
    for i, data in enumerate(validation_data_orig):
        color_orig = colors_orig[i % len(colors_orig)]
        fig.add_trace(go.Scatter(
            x=channels, y=data['current'], mode='lines',
            name=f"{data['id']} - Orig",
            line=dict(color=color_orig, width=2, dash='dash'), legendgroup='original',
            hovertemplate=f'<b>{data["id"]} - Orig</b><br>Canal: %{{x}}<br>Abs: %{{y:.6f}}<extra></extra>'
        ))
    
    for i, data in enumerate(validation_data_sim):
        color_sim = colors_sim[i % len(colors_sim)]
        fig.add_trace(go.Scatter(
            x=channels, y=data['current'], mode='lines',
            name=f"{data['id']} - Sim",
            line=dict(color=color_sim, width=2, dash='dot'), legendgroup='simulated',
            hovertemplate=f'<b>{data["id"]} - Sim</b><br>Canal: %{{x}}<br>Abs: %{{y:.6f}}<extra></extra>'
        ))
    
    fig.update_layout(
        title={'text': f'Comparación Global: Referencia vs Original vs Simulado (Offset: {offset_value:+.6f} AU)',
               'x': 0.5, 'xanchor': 'center', 'font': {'size': 16, 'color': '#2c5f3f'}},
        xaxis_title='Canal espectral', yaxis_title='Absorbancia',
        hovermode='closest', template='plotly_white', height=600, showlegend=True,
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02, font=dict(size=9))
    )
    
    chart_html = fig.to_html(include_plotlyjs='cdn', div_id='global_overlay',
                             config={'displayModeBar': True, 'responsive': True})
    
    html = """
        <div class="info-box" id="vista-global">
            <h2>Vista Global de Espectros</h2>
            <p class="text-caption">
                <em>Comparación simultánea de todos los espectros. Líneas sólidas: referencia (azul). 
                Líneas discontinuas: actual sin offset (rojo). Líneas punteadas: actual con offset aplicado (verde).</em>
            </p>
    """
    html += wrap_chart_in_expandable(chart_html, "Ver comparación global de espectros (3 estados)",
                                     "global_overlay_expandable", default_open=False)
    html += "</div>"
    
    return html


def generate_baseline_adjustment_section(report_data):
    """Genera la sección de ajuste del baseline."""
    baseline_original = report_data['baseline_original']
    baseline_adjusted = report_data['baseline_adjusted']
    offset_value = report_data['offset_value']
    
    orig_mean = np.mean(baseline_original)
    adj_mean = np.mean(baseline_adjusted)
    
    html = f"""
        <div class="info-box" id="baseline-adjustment">
            <h2>Ajuste del Baseline</h2>
            <p class="text-caption">
                <em>Visualización del baseline original y el baseline ajustado con el offset aplicado.</em>
            </p>
            
            <h3>Estadísticas del Baseline</h3>
            <table>
                <tr><th>Parámetro</th><th>Original</th><th>Ajustado</th><th>Cambio</th></tr>
                <tr><td><strong>Media</strong></td><td>{orig_mean:.6f} AU</td><td>{adj_mean:.6f} AU</td><td>{offset_value:+.6f} AU</td></tr>
                <tr><td><strong>Mínimo</strong></td><td>{np.min(baseline_original):.6f} AU</td><td>{np.min(baseline_adjusted):.6f} AU</td><td>{np.min(baseline_adjusted) - np.min(baseline_original):+.6f} AU</td></tr>
                <tr><td><strong>Máximo</strong></td><td>{np.max(baseline_original):.6f} AU</td><td>{np.max(baseline_adjusted):.6f} AU</td><td>{np.max(baseline_adjusted) - np.max(baseline_original):+.6f} AU</td></tr>
                <tr><td><strong>Desv. Est.</strong></td><td>{np.std(baseline_original):.6f} AU</td><td>{np.std(baseline_adjusted):.6f} AU</td><td>{np.std(baseline_adjusted) - np.std(baseline_original):+.6f} AU</td></tr>
            </table>
            <p class="text-muted-small">
                <em>Nota: La desviación estándar se mantiene constante, confirmando que la forma espectral ha sido preservada.</em>
            </p>
    """
    
    fig = create_baseline_comparison_plot(baseline_original, baseline_adjusted, offset_value)
    chart_html = fig.to_html(include_plotlyjs='cdn', div_id='baseline_comparison',
                             config={'displayModeBar': True, 'responsive': True})
    html += wrap_chart_in_expandable(chart_html, "Ver gráfico de comparación de baseline",
                                     "baseline_comparison_expandable", default_open=True)
    html += "</div>"
    
    return html


def create_baseline_comparison_plot(baseline_orig, baseline_adj, offset_value):
    """Crea gráfico de comparación del baseline."""
    channels = list(range(1, len(baseline_orig) + 1))
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Baseline: Original vs Ajustado', 'Diferencia Aplicada (Offset)'),
        vertical_spacing=0.15, row_heights=[0.65, 0.35]
    )
    
    fig.add_trace(go.Scatter(x=channels, y=baseline_orig, name='Original',
                            line=dict(color='blue', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=channels, y=baseline_adj, name='Ajustado',
                            line=dict(color='green', width=2, dash='dash')), row=1, col=1)
    
    diff = baseline_adj - baseline_orig
    fig.add_trace(go.Scatter(x=channels, y=diff, name='Diferencia',
                            line=dict(color='red', width=2),
                            fill='tozeroy', fillcolor='rgba(255,0,0,0.1)'), row=2, col=1)
    fig.add_hline(y=-offset_value, line_dash="dash", line_color="orange",
                 annotation_text=f"Offset = {-offset_value:.6f}", row=2, col=1)
    
    fig.update_xaxes(title_text="Canal espectral", row=2, col=1)
    fig.update_yaxes(title_text="Absorbancia", row=1, col=1)
    fig.update_yaxes(title_text="Δ Absorbancia", row=2, col=1)
    fig.update_layout(height=600, showlegend=True, template='plotly_white', hovermode='x unified')
    
    return fig


def generate_individual_analysis(report_data):
    """Genera el análisis individual de cada estándar (compacto)."""
    validation_data_orig = report_data['validation_data_original']
    validation_data_sim = report_data['validation_data_simulated']
    
    html = """
        <div class="info-box" id="analisis-individual">
            <h2>Análisis Individual de Estándares</h2>
            <p class="text-caption">
                <em>Análisis detallado de cada estándar mostrando el impacto del offset en las métricas de validación.</em>
            </p>
    """
    
    for i, (data_orig, data_sim) in enumerate(zip(validation_data_orig, validation_data_sim)):
        sample_id = data_orig['id']
        val_orig = data_orig['validation_results']
        val_sim = data_sim['validation_results']
        
        html += f"""
            <div id="standard-{sample_id}" class="standard-analysis-box">
                <h3>Estándar: {sample_id}</h3>
                <h4>Comparación de Métricas</h4>
                <table>
                    <tr><th>Métrica</th><th>Original</th><th>Simulado</th><th>Cambio</th></tr>
                    <tr><td><strong>Correlación</strong></td><td>{val_orig['correlation']:.6f}</td><td>{val_sim['correlation']:.6f}</td><td>{format_change(val_sim['correlation'] - val_orig['correlation'])}</td></tr>
                    <tr><td><strong>Max Δ</strong></td><td>{val_orig['max_diff']:.6f} AU</td><td>{val_sim['max_diff']:.6f} AU</td><td>{format_change(val_sim['max_diff'] - val_orig['max_diff'], inverse=True)}</td></tr>
                    <tr><td><strong>RMS</strong></td><td>{val_orig['rms']:.6f}</td><td>{val_sim['rms']:.6f}</td><td>{format_change(val_sim['rms'] - val_orig['rms'], inverse=True)}</td></tr>
                    <tr><td><strong>Offset Medio</strong></td><td>{val_orig['mean_diff']:+.6f} AU</td><td>{val_sim['mean_diff']:+.6f} AU</td><td>{format_change(val_sim['mean_diff'] - val_orig['mean_diff'], inverse=True, show_sign=True)}</td></tr>
                </table>
            </div>
        """
    
    html += "</div>"
    return html


def generate_recommendations(report_data):
    """Genera la sección de recomendaciones finales."""
    offset_value = report_data['offset_value']
    global_offset_sim = report_data['global_offset_simulated']
    
    if abs(global_offset_sim) < 0.003:
        return """
        <div class="info-box" id="recomendaciones">
            <h2>💡 Recomendaciones Finales</h2>
            <div class="success-box">
                <h3>✅ Baseline Listo para Producción</h3>
                <p>El ajuste de offset ha sido exitoso. El bias residual es despreciable.</p>
            </div>
            <h3>Próximos Pasos:</h3>
            <ol class="list-spacious">
                <li><strong>Instalar el baseline ajustado</strong> en el equipo NIR</li>
                <li><strong>Verificar con mediciones reales</strong> de los estándares ópticos</li>
                <li><strong>Documentar el cambio</strong> en el log del equipo</li>
                <li><strong>Mantener una copia</strong> del baseline original como backup</li>
                <li><strong>Validar calibraciones</strong> activas con muestras de referencia</li>
            </ol>
        </div>
        """
    else:
        return f"""
        <div class="info-box" id="recomendaciones">
            <h2>💡 Recomendaciones Finales</h2>
            <div class="warning-box">
                <h3>⚠️ Validación Adicional Recomendada</h3>
                <p>El bias residual ({global_offset_sim:+.6f} AU) sugiere que puede ser necesario un ajuste adicional.</p>
            </div>
            <h3>Acciones Recomendadas:</h3>
            <ol class="list-spacious">
                <li><strong>Instalar el baseline ajustado</strong> y medir los estándares realmente</li>
                <li><strong>Evaluar los resultados</strong> de las mediciones reales</li>
                <li><strong>Revisar posibles causas</strong> del bias residual</li>
                <li><strong>Documentar todas las iteraciones</strong> del proceso de ajuste</li>
            </ol>
        </div>
        """


def generate_offset_adjustment_report(data: Dict) -> str:
    """
    Genera un informe HTML completo de ajuste de offset.
    OPTIMIZADO: Usa funciones compartidas de report_utils
    
    Args:
        data: Diccionario con toda la información necesaria
        
    Returns:
        String con contenido HTML del informe
    """
    # Construir sidebar usando función compartida
    sections = [
        ("info-servicio", "Información del Servicio"),
        ("resumen-ejecutivo", "Resumen Ejecutivo"),
        ("analisis-offset", "Análisis del Offset"),
        ("comparacion-metricas", "Comparación de Métricas"),
        ("vista-global", "Vista Global de Espectros"),
        ("baseline-adjustment", "Ajuste del Baseline"),
    ]
    
    sidebar_html = build_sidebar_html(sections=sections,
                                      standards_list=data['validation_data_original'],
                                      show_individual_analysis=True)
    sidebar_html += '<li><a href="#recomendaciones">💡 Recomendaciones</a></li>'
    
    # Iniciar documento usando función compartida
    html = start_html_template(title=f"Informe de Ajuste de Offset - {data['sensor_serial']}",
                               sidebar_html=sidebar_html)
    
    html += "<h1>Informe de Ajuste de Offset para Baseline NIR</h1>"
    
    # Información del servicio usando función compartida
    additional_info = {
        'TSV Referencia': data['ref_filename'],
        'TSV Actual': data['curr_filename'],
        'Baseline Original': data['baseline_filename'],
        'Offset Aplicado': f'<span class="value-highlighted">{data["offset_value"]:+.6f} AU</span>'
    }
    html += generate_service_info_section(data['sensor_serial'], data['customer_name'],
                                          data['technician_name'], data['service_notes'],
                                          additional_info)
    
    # Secciones específicas
    html += generate_executive_summary(data)
    html += generate_offset_analysis(data)
    html += generate_metrics_comparison(data)
    html += generate_global_overlay_plot(data)
    html += generate_baseline_adjustment_section(data)
    html += generate_individual_analysis(data)
    html += generate_recommendations(data)
    
    # Footer usando función compartida
    html += generate_footer("COREF Suite - Baseline Offset Adjustment Tool")
    
    return html