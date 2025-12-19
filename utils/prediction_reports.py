"""
Prediction Reports - Generación de reportes HTML y texto con estilo COREF Suite
"""

from datetime import datetime
from .nir_analyzer import get_params_in_original_order
from .prediction_charts import create_detailed_comparison
import plotly.graph_objects as go


def load_buchi_css():
    """Carga el CSS corporativo de BUCHI (estilo COREF Suite)"""
    try:
        with open('buchi_report_styles_simple.css', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        # CSS inline completo como fallback - Estilo COREF Suite
        return """
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

/* Sidebar corporativo */
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

/* Contenido principal */
.main-content {
    margin-left: 290px;
    padding: 40px;
    max-width: 1400px;
}

/* Títulos */
h1 {
    color: #093A34;
    border-bottom: 4px solid #289A93;
    padding-bottom: 15px;
    margin-bottom: 30px;
    font-size: 2.5em;
}

h2 {
    color: #093A34;
    margin-top: 30px;
    margin-bottom: 15px;
    font-size: 1.8em;
    border-left: 5px solid #289A93;
    padding-left: 15px;
}

h3 {
    color: #289A93;
    margin-top: 25px;
    margin-bottom: 12px;
    font-size: 1.4em;
}

h4 {
    color: #064d45;
    margin-top: 20px;
    margin-bottom: 10px;
}

/* Cajas de información */
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

.status-warning {
    background-color: #fff3cd;
    border-left: 5px solid #ffc107;
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

/* Tablas */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0;
    background-color: white;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

th {
    background-color: #093A34;
    color: white;
    padding: 12px;
    text-align: left;
    font-weight: bold;
    border: 1px solid #ddd;
}

td {
    padding: 10px 12px;
    border: 1px solid #ddd;
}

tr:nth-child(even) {
    background-color: #f8f9fa;
}

tr:hover {
    background-color: #e9ecef;
}

/* Grid de información */
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

/* Expandibles (details/summary) */
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

/* Footer */
.footer {
    text-align: center;
    padding: 30px;
    margin-top: 50px;
    border-top: 3px solid #289A93;
    color: #6c757d;
    background-color: white;
}

/* Pre-formatted text */
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

/* Plot containers */
.plot-container {
    margin: 30px 0;
    padding: 20px;
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

/* Responsive */
@media (max-width: 768px) {
    .sidebar {
        width: 100%;
        height: auto;
        position: relative;
    }
    
    .main-content {
        margin-left: 0;
    }
    
    .info-grid {
        grid-template-columns: 1fr;
    }
}
"""

def wrap_chart_in_expandable(chart_html, title, chart_id, default_open=False):
    """
    Envuelve un gráfico en un elemento expandible HTML con estilo BUCHI.
    
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
    <details {open_attr} id="{chart_id}">
        <summary>📊 {title}</summary>
        <div style="padding: 15px; margin-top: 10px;">
            {chart_html}
        </div>
    </details>
    """


def generate_html_header(sections=None):
    """
    Genera el encabezado HTML con sidebar BUCHI dinámico.
    """
    if sections is None:
        sections = [
            ("info-general", "Información General"),
            ("statistics", "Estadísticas Detalladas"),
            ("comparison-charts", "Gráficos Comparativos"),
            ("differences-by-product", "Diferencias por Producto"),
            ("text-report", "Reporte en Texto")
        ]
    
    sidebar_html = ""
    for section_id, section_name in sections:
        sidebar_html += f'            <li><a href="#{section_id}">{section_name}</a></li>\n'
    
    css_content = load_buchi_css()
    
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte de Predicciones NIR - BUCHI</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
{css_content}
    </style>
</head>
<body>
    <div class="sidebar">
        <ul>
{sidebar_html}        </ul>
    </div>
    
    <div class="main-content">
"""

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
    
    Args:
        differences_data (dict): Datos de diferencias calculadas
        
    Returns:
        str: HTML de la sección
    """
    html = """
    <div class="info-box" id="differences-by-product">
        <h2>📊 Diferencias por Producto</h2>
        <p style='color: #6c757d; font-size: 0.95em; margin-bottom: 25px;'>
            <em>Análisis comparativo detallado entre lámparas para cada producto.</em>
        </p>
    """
    
    for product, product_data in differences_data.items():
        baseline_lamp = product_data['baseline_lamp']
        comparisons = product_data['comparisons']
        
        html += f"""
        <div style="margin-bottom: 40px; padding: 20px; background-color: #f8f9fa; border-radius: 8px; border-left: 4px solid #64B445;">
            <h3 style="margin-top: 0; color: #093A34;">🔬 {product}</h3>
            <p style="color: #6c757d; font-size: 0.9em; margin-bottom: 20px;">
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
                <summary style="padding: 15px;">
                    📍 {comp_lamp} vs {baseline_lamp} (N = {n_compared})
                </summary>
                
                <div style="padding: 20px;">
                    <table>
                        <thead>
                            <tr>
                                <th style="text-align: left;">Parámetro</th>
                                <th style="text-align: center;">{baseline_lamp}<br/><span style="font-weight: normal; font-size: 0.85em;">(Baseline)</span></th>
                                <th style="text-align: center;">{comp_lamp}<br/><span style="font-weight: normal; font-size: 0.85em;">(Comparada)</span></th>
                                <th style="text-align: center;">Δ Absoluta</th>
                                <th style="text-align: center;">Δ Relativa (%)</th>
                                <th style="text-align: center;">Evaluación</th>
                            </tr>
                        </thead>
                        <tbody>
            """
            
            sorted_params = sorted(
                differences.items(), 
                key=lambda x: abs(x[1]['absolute_diff']), 
                reverse=True
            )
            
            for param, diff_data in sorted_params:
                baseline_val = diff_data['baseline_mean']
                compared_val = diff_data['compared_mean']
                abs_diff = diff_data['absolute_diff']
                percent_diff = diff_data['percent_diff']
                
                abs_percent = abs(percent_diff)
                if abs_percent < 2.0:
                    evaluation = '🟢 Excelente'
                    eval_color = '#4caf50'
                    row_bg = '#e8f5e9'
                elif abs_percent < 5.0:
                    evaluation = '🟡 Aceptable'
                    eval_color = '#ffc107'
                    row_bg = '#fff3e0'
                elif abs_percent < 10.0:
                    evaluation = '🟠 Revisar'
                    eval_color = '#ff9800'
                    row_bg = '#ffe8e8'
                else:
                    evaluation = '🔴 Significativo'
                    eval_color = '#f44336'
                    row_bg = '#ffebee'
                
                direction = '↑' if abs_diff > 0 else '↓' if abs_diff < 0 else '='
                
                html += f"""
                    <tr style="background-color: {row_bg};">
                        <td style="font-weight: bold;">{param}</td>
                        <td style="text-align: center;">{baseline_val:.3f}</td>
                        <td style="text-align: center;">{compared_val:.3f}</td>
                        <td style="text-align: center; font-weight: bold;">{direction} {abs(abs_diff):.3f}</td>
                        <td style="text-align: center; font-weight: bold; color: {eval_color};">
                            {abs_diff:+.3f} ({percent_diff:+.2f}%)
                        </td>
                        <td style="text-align: center; color: {eval_color}; font-weight: bold;">
                            {evaluation}
                        </td>
                    </tr>
                """
            
            html += """
                        </tbody>
                    </table>
                    
                    <div style="margin-top: 15px; padding: 10px; background-color: #f1f3f4; border-radius: 5px;">
                        <strong>📌 Leyenda de Evaluación:</strong>
                        <ul style="margin: 10px 0 0 20px; font-size: 0.9em;">
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
    
    # Generar encabezado con sidebar
    html = generate_html_header()
    
    # Título principal
    html += f"""
        <h1>Reporte de Predicciones NIR</h1>
        
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
    
    # Estadísticas por producto
    html += """
        <div class="info-box" id="statistics">
            <h2>Estadísticas por Producto y Lámpara</h2>
            <p style='color: #6c757d; font-size: 0.95em; margin-bottom: 25px;'>
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
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th style="text-align: left;">Lámpara</th>
                            <th>N</th>
        """
        
        for param in params:
            html += f'<th>{param}<br/><span style="font-weight: normal; font-size: 0.85em;">(Media ± SD)</span></th>'
        
        html += """
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for lamp, lamp_stats in stats[product].items():
            html += f"""
                        <tr>
                            <td style="font-weight: bold; background-color: #f8f9fa;">{lamp}</td>
                            <td>{lamp_stats['n']}</td>
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
            <p style='color: #6c757d; font-size: 0.95em;'>
                <em>Análisis visual de las predicciones NIR entre diferentes lámparas.</em>
            </p>
    """
    
    params_ordered = get_params_in_original_order(analyzer, products)
    
    for param in params_ordered:
        fig = create_detailed_comparison(stats, param)
        
        if fig:
            chart_html = fig.to_html(
                include_plotlyjs=False,
                div_id=f"graph_{param.replace(' ', '_')}"
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
            <p style='color: #6c757d; font-size: 0.95em; margin-bottom: 20px;'>
                <em>Reporte completo en formato de texto con análisis estadístico.</em>
            </p>
            <pre>{text_report}</pre>
        </div>
    """
    
    # Footer - DENTRO del main-content pero cerrando main-content después
    html += f"""
        <div class="footer">
            <p><strong>NIR Predictions Analyzer</strong> - Desarrollado para BUCHI</p>
            <p>Reporte generado automáticamente el {timestamp}</p>
            <p>© BUCHI Labortechnik AG</p>
        </div>
    </div>
</body>
</html>
"""
    
    return html