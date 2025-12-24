"""
Prediction Reports - Generación de reportes HTML y texto con estilo COREF Suite
Optimizado: sin CSS inline, usando report_utils, sidebar estandarizado
FIXED: Tablas con scroll horizontal + Título "Índice" en sidebar
"""

from datetime import datetime
from .nir_analyzer import get_params_in_original_order
from .prediction_charts import create_detailed_comparison
import plotly.graph_objects as go

# Imports de funciones compartidas
from core.report_utils import (
    load_buchi_css,
    wrap_chart_in_expandable,
    start_html_template,
    build_sidebar_html,
    generate_footer,
    generate_evaluated_table
)


def calculate_lamp_differences(stats, analyzer):
    """
    Calcula diferencias entre lámparas para cada producto.
    
    Args:
        stats (dict): Estadísticas por producto y lámpara
        analyzer: Objeto analizador con los datos
        
    Returns:
        dict: Diferencias calculadas por producto
    """
    differences_by_product = {}
    
    for product, product_stats in stats.items():
        lamps = sorted(list(product_stats.keys()))
        
        if len(lamps) < 2:
            continue
        
        baseline_lamp = lamps[0]
        comparison_lamps = lamps[1:]
        
        # Obtener parámetros en orden original
        if product in analyzer.data:
            df = analyzer.data[product]
            excluded_cols = ['No', 'ID', 'Note', 'Product', 'Method', 'Unit', 'Begin', 'End', 'Length']
            if len(df.columns) > 1:
                excluded_cols.append(df.columns[1])
            params = [col for col in df.columns if col not in excluded_cols]
        else:
            params = set()
            for lamp_stats in product_stats.values():
                params.update([k for k in lamp_stats.keys() if k not in ['n', 'note']])
            params = sorted(list(params))
        
        comparisons = []
        
        for comp_lamp in comparison_lamps:
            comparison = {
                'lamp': comp_lamp,
                'n_baseline': product_stats[baseline_lamp]['n'],
                'n_compared': product_stats[comp_lamp]['n'],
                'differences': {}
            }
            
            for param in params:
                if (param in product_stats[baseline_lamp] and 
                    param in product_stats[comp_lamp]):
                    
                    baseline_mean = product_stats[baseline_lamp][param]['mean']
                    compared_mean = product_stats[comp_lamp][param]['mean']
                    
                    abs_diff = compared_mean - baseline_mean
                    percent_diff = (abs_diff / baseline_mean * 100) if baseline_mean != 0 else 0
                    
                    comparison['differences'][param] = {
                        'baseline_mean': baseline_mean,
                        'compared_mean': compared_mean,
                        'absolute_diff': abs_diff,
                        'percent_diff': percent_diff
                    }
            
            comparisons.append(comparison)
        
        differences_by_product[product] = {
            'baseline_lamp': baseline_lamp,
            'comparisons': comparisons
        }
    
    return differences_by_product


def generate_differences_section(differences_data):
    """
    Genera HTML para la sección de diferencias por producto.
    Usa generate_evaluated_table() para las tablas de comparación.
    
    Args:
        differences_data (dict): Datos de diferencias calculadas
        
    Returns:
        str: HTML de la sección
    """
    html = """
    <div class="info-box" id="differences-by-product">
        <h2>📊 Diferencias por Producto</h2>
        <p class="text-caption section-description">
            <em>Análisis comparativo detallado entre lámparas para cada producto.</em>
        </p>
    """
    
    for product, product_data in differences_data.items():
        baseline_lamp = product_data['baseline_lamp']
        comparisons = product_data['comparisons']
        
        html += f"""
        <div class="product-section">
            <h3 class="product-title">🔬 {product}</h3>
            <p class="text-caption-small">
                <strong>Lámpara Baseline:</strong> {baseline_lamp} 
                (N = {comparisons[0]['n_baseline'] if comparisons else 'N/A'})
            </p>
        """
        
        for comparison in comparisons:
            comp_lamp = comparison['lamp']
            n_compared = comparison['n_compared']
            differences = comparison['differences']
            
            html += f"""
            <details open>
                <summary>📍 {comp_lamp} vs {baseline_lamp} (N = {n_compared})</summary>
                
                <div class="comparison-container">
            """
            
            # Preparar datos para generate_evaluated_table
            sorted_params = sorted(
                differences.items(), 
                key=lambda x: abs(x[1]['absolute_diff']), 
                reverse=True
            )
            
            table_data = []
            for param, diff_data in sorted_params:
                baseline_val = diff_data['baseline_mean']
                compared_val = diff_data['compared_mean']
                abs_diff = diff_data['absolute_diff']
                percent_diff = diff_data['percent_diff']
                
                direction = '↑' if abs_diff > 0 else '↓' if abs_diff < 0 else '='
                
                # Determinar evaluación
                abs_percent = abs(percent_diff)
                if abs_percent < 2.0:
                    evaluation = '🟢 Excelente'
                    eval_color = '#4caf50'
                elif abs_percent < 5.0:
                    evaluation = '🟡 Aceptable'
                    eval_color = '#ffc107'
                elif abs_percent < 10.0:
                    evaluation = '🟠 Revisar'
                    eval_color = '#ff9800'
                else:
                    evaluation = '🔴 Significativo'
                    eval_color = '#f44336'
                
                table_data.append({
                    'param': param,
                    'baseline': baseline_val,
                    'compared': compared_val,
                    'abs_diff': f"{direction} {abs(abs_diff):.3f}",
                    'percent_diff': abs_percent,  # Para evaluación
                    'percent_display': f"{abs_diff:+.3f} ({percent_diff:+.2f}%)",
                    'evaluation': evaluation,
                    'eval_color': eval_color
                })
            
            # Definir columnas
            columns = [
                {'key': 'param', 'header': 'Parámetro', 'align': 'left'},
                {'key': 'baseline', 'header': f'{baseline_lamp}<br/><span class="text-caption-small">(Baseline)</span>', 'format': '{:.3f}'},
                {'key': 'compared', 'header': f'{comp_lamp}<br/><span class="text-caption-small">(Comparada)</span>', 'format': '{:.3f}'},
                {'key': 'abs_diff', 'header': 'Δ Absoluta', 'align': 'center'},
                {'key': 'percent_display', 'header': 'Δ Relativa (%)', 'align': 'center'},
                {'key': 'evaluation', 'header': 'Evaluación', 'align': 'center'}
            ]
            
            # Definir umbrales para colorear filas
            thresholds = {
                'excellent': {'max': 2.0, 'class': 'eval-excellent'},
                'acceptable': {'max': 5.0, 'class': 'eval-acceptable'},
                'review': {'max': 10.0, 'class': 'eval-review'},
                'critical': {'class': 'eval-significant'}
            }
            
            # Generar tabla usando función compartida
            html += generate_evaluated_table(
                table_data,
                columns,
                evaluation_column='percent_diff',
                evaluation_thresholds=thresholds
            )
            
            # Añadir leyenda
            html += """
                    <div class="comparison-footer">
                        <strong>📌 Leyenda de Evaluación:</strong>
                        <ul class="legend-list">
                            <li><strong>🟢 Excelente:</strong> Δ < 2% - Diferencia despreciable</li>
                            <li><strong>🟡 Aceptable:</strong> 2% ≤ Δ < 5% - Dentro del rango esperado</li>
                            <li><strong>🟠 Revisar:</strong> 5% ≤ Δ < 10% - Diferencia notable</li>
                            <li><strong>🔴 Significativo:</strong> Δ ≥ 10% - Requiere investigación</li>
                        </ul>
                    </div>
                </div>
            </details>
            """
        
        html += """
        </div>
        """
    
    html += """
    </div>
    """
    
    return html


def generate_text_report(stats, analyzer):
    """
    Generar reporte de texto completo.
    
    Args:
        stats (dict): Estadísticas por producto y lámpara
        analyzer: Objeto analizador con los datos
        
    Returns:
        str: Reporte en texto plano
    """
    report = []
    report.append("=" * 120)
    report.append("INFORME COMPARATIVO DE LÁMPARAS NIR")
    report.append("Análisis de Predicciones - Reporte Completo")
    report.append("=" * 120)
    report.append("")
    report.append(f"Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    if analyzer.sensor_serial:
        report.append(f"Sensor NIR: {analyzer.sensor_serial}")
    
    report.append("")
    
    lamps = set()
    for product_stats in stats.values():
        lamps.update(product_stats.keys())
    lamps = sorted(list(lamps))
    
    report.append("LÁMPARAS COMPARADAS:")
    for lamp in lamps:
        report.append(f"  • {lamp}")
    report.append("")
    
    for product, product_stats in stats.items():
        report.append("-" * 120)
        report.append(f"PRODUCTO: {product.upper()}")
        report.append("-" * 120)
        report.append("")
        
        if product in analyzer.data:
            df = analyzer.data[product]
            excluded_cols = ['No', 'ID', 'Note', 'Product', 'Method', 'Unit', 'Begin', 'End', 'Length']
            if len(df.columns) > 1:
                excluded_cols.append(df.columns[1])
            params = [col for col in df.columns if col not in excluded_cols]
        else:
            params = set()
            for lamp_stats in product_stats.values():
                params.update([k for k in lamp_stats.keys() if k not in ['n', 'note']])
            params = sorted(list(params))
        
        report.append("RESULTADOS DE PREDICCIÓN:")
        report.append("")
        
        for lamp, lamp_stats in product_stats.items():
            report.append(f"  Lámpara: {lamp} (N={lamp_stats['n']})")
            report.append("  " + "-" * 100)
            
            for param in params:
                if param in lamp_stats:
                    mean = lamp_stats[param]['mean']
                    std = lamp_stats[param]['std']
                    min_val = lamp_stats[param]['min']
                    max_val = lamp_stats[param]['max']
                    report.append(f"    {param:<25} {mean:>10.3f} ± {std:<8.3f}   (min: {min_val:>8.3f}, max: {max_val:>8.3f})")
            
            report.append("")
        
        if len(lamps) >= 2:
            report.append("  ANÁLISIS DE DIFERENCIAS:")
            report.append("")
            
            base_lamp = sorted(list(product_stats.keys()))[0]
            
            for lamp in sorted(list(product_stats.keys()))[1:]:
                report.append(f"    {lamp} vs {base_lamp} (baseline):")
                
                for param in params:
                    if param in product_stats[base_lamp] and param in product_stats[lamp]:
                        base_mean = product_stats[base_lamp][param]['mean']
                        comp_mean = product_stats[lamp][param]['mean']
                        diff = comp_mean - base_mean
                        percent_diff = (diff / base_mean * 100) if base_mean != 0 else 0
                        
                        report.append(f"      {param:<25} Δ = {diff:+.3f}  ({percent_diff:+.2f}%)")
                
                report.append("")
        
        report.append("")
    
    report.append("=" * 120)
    report.append("RESUMEN ESTADÍSTICO GENERAL")
    report.append("=" * 120)
    report.append("")
    
    for product in stats.keys():
        report.append(f"Producto: {product}")
        
        if product in analyzer.data:
            df = analyzer.data[product]
            excluded_cols = ['No', 'ID', 'Note', 'Product', 'Method', 'Unit', 'Begin', 'End', 'Length']
            if len(df.columns) > 1:
                excluded_cols.append(df.columns[1])
            params = [col for col in df.columns if col not in excluded_cols]
        else:
            params = list(stats[product][list(stats[product].keys())[0]].keys())
            params = [p for p in params if p not in ['n', 'note']]
        
        for param in params[:5]:
            report.append(f"  {param}:")
            
            values = []
            for lamp_stats in stats[product].values():
                if param in lamp_stats:
                    values.append(lamp_stats[param]['mean'])
            
            if values:
                overall_mean = sum(values) / len(values)
                overall_std = (sum((x - overall_mean) ** 2 for x in values) / len(values)) ** 0.5
                overall_range = max(values) - min(values)
                
                report.append(f"    Media entre lámparas: {overall_mean:.3f} ± {overall_std:.3f}")
                report.append(f"    Rango: {overall_range:.3f}")
        
        report.append("")
    
    report.append("=" * 120)
    report.append("FIN DEL INFORME")
    report.append("=" * 120)
    
    return "\n".join(report)


def generate_html_report(stats, analyzer, filename):
    """
    Generar reporte HTML completo con estilo corporativo BUCHI.
    
    Args:
        stats (dict): Estadísticas por producto y lámpara
        analyzer: Objeto analizador con los datos
        filename (str): Nombre del archivo de salida
        
    Returns:
        str: HTML completo del reporte
    """
    products = list(stats.keys())
    all_lamps = set()
    for product_stats in stats.values():
        all_lamps.update(product_stats.keys())
    all_lamps = sorted(list(all_lamps))
    
    sensor_serial = analyzer.sensor_serial if analyzer.sensor_serial else "N/A"
    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    
    # Definir secciones del sidebar
    sections = [
        ("info-general", "Información General"),
        ("statistics", "Estadísticas Detalladas"),
        ("comparison-charts", "Gráficos Comparativos"),
        ("differences-by-product", "Diferencias por Producto"),
        ("text-report", "Reporte en Texto")
    ]
    
    # ⭐ FIX: Construir sidebar manualmente con título "Índice"
    sidebar_html = '<h2>📋 Índice</h2>\n'
    for section_id, section_label in sections:
        sidebar_html += f'            <li><a href="#{section_id}">{section_label}</a></li>\n'
    
    # Iniciar HTML con template estandarizado
    html = start_html_template(
        title="Reporte de Predicciones NIR",
        sidebar_html=sidebar_html  # ⭐ Usar sidebar_html en lugar de sidebar_sections
    )
    
    # Información general
    html += f"""
        <div class="info-box" id="info-general">
            <h2>Información General del Análisis</h2>
            <div class="info-grid">
                <div class="info-item">
                    <span class="info-label">🔬 Sensor NIR</span>
                    <span class="info-value">{sensor_serial}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">📅 Fecha del Reporte</span>
                    <span class="info-value">{timestamp}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">📦 Productos Analizados</span>
                    <span class="info-value">{len(products)}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">💡 Lámparas Comparadas</span>
                    <span class="info-value">{len(all_lamps)}</span>
                </div>
            </div>
            
            <table>
                <tr>
                    <th>Productos</th>
                    <td>{', '.join(products)}</td>
                </tr>
                <tr>
                    <th>Lámparas</th>
                    <td>{', '.join(all_lamps)}</td>
                </tr>
            </table>
        </div>
    """
    
    # ⭐ FIX: Estadísticas por producto CON SCROLL HORIZONTAL
    html += """
        <div class="info-box" id="statistics">
            <h2>Estadísticas por Producto y Lámpara</h2>
            <p class="text-caption section-description">
                <em>Valores promedio y desviación estándar de cada parámetro analítico.</em>
            </p>
    """
    
    for product in products:
        if product in analyzer.data:
            df = analyzer.data[product]
            excluded_cols = ['No', 'ID', 'Note', 'Product', 'Method', 'Unit', 'Begin', 'End', 'Length']
            if len(df.columns) > 1:
                excluded_cols.append(df.columns[1])
            params = [col for col in df.columns if col not in excluded_cols]
        else:
            params = set()
            for lamp_stats in stats[product].values():
                params.update([k for k in lamp_stats.keys() if k not in ['n', 'note']])
            params = sorted(list(params))
        
        html += f"""
            <h3>{product}</h3>
            <div class="stats-table-container">
                <table class="stats-table">
                    <thead>
                        <tr>
                            <th class="sticky-col-lamp">Lámpara</th>
                            <th class="sticky-col-n">N</th>
        """
        
        for param in params:
            html += f'<th>{param}<br/><span class="text-caption-small">(Media ± SD)</span></th>'
        
        html += """
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for lamp, lamp_stats in stats[product].items():
            html += f"""
                <tr>
                    <td class="sticky-col-lamp">{lamp}</td>
                    <td class="sticky-col-n">{lamp_stats['n']}</td>
            """
            
            for param in params:
                if param in lamp_stats:
                    mean = lamp_stats[param]['mean']
                    std = lamp_stats[param]['std']
                    html += f'<td>{mean:.3f} ± {std:.3f}</td>'
                else:
                    html += '<td>-</td>'
            
            html += """
                        </tr>
            """
        
        html += """
                    </tbody>
                </table>
            </div>
        """
    
    html += """
        </div>
    """
    
    # Gráficos comparativos
    html += """
        <div class="info-box" id="comparison-charts">
            <h2>Gráficos Comparativos</h2>
            <p class="text-caption">
                <em>Análisis visual de las predicciones NIR entre diferentes lámparas.</em>
            </p>
    """
    
    params_ordered = get_params_in_original_order(analyzer, products)
    
    for param in params_ordered:
        fig = create_detailed_comparison(stats, param)
        
        if fig:
            chart_html = fig.to_html(
                include_plotlyjs='cdn',
                div_id=f"graph_{param.replace(' ', '_')}",
                config={'displayModeBar': True, 'responsive': True}
            )
            
            html += wrap_chart_in_expandable(
                chart_html,
                f"Comparación detallada: {param}",
                f"chart_{param.replace(' ', '_')}",
                default_open=False
            )
    
    html += """
        </div>
    """
    
    # Diferencias por producto
    differences_data = calculate_lamp_differences(stats, analyzer)
    
    if differences_data:
        html += generate_differences_section(differences_data)
    
    # Reporte de texto
    text_report = generate_text_report(stats, analyzer)
    
    html += f"""
        <div class="info-box" id="text-report">
            <h2>Informe Detallado en Texto</h2>
            <p class="text-caption description-bottom-margin">
                <em>Reporte completo en formato de texto con análisis estadístico.</em>
            </p>
            <pre>{text_report}</pre>
        </div>
    """
    
    # Footer
    html += generate_footer()
    
    return html