"""
Prediction Reports - Generación de reportes HTML y texto con estilo COREF Suite
Optimizado: sin CSS inline, usando report_utils, sidebar estandarizado
FIXED: Tablas con scroll horizontal + Título "Índice" en sidebar
NUEVO: Carruseles Bootstrap para gráficos + Orden personalizado de parámetros
REORDENADO: Gráficos comparativos antes de estadísticas
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


def generate_differences_section(differences_data, stats, analyzer):
    """
    Genera HTML para la sección de diferencias por producto con pestañas.
    Cada producto es una pestaña.
    
    Args:
        differences_data (dict): Datos de diferencias calculadas
        stats (dict): Estadísticas originales
        analyzer: Objeto analizador
        
    Returns:
        str: HTML de la sección
    """
    html = """
    <div class="info-box" id="differences-by-product">
        <h2>📊 Diferencias por Producto</h2>
        <p class="text-caption section-description">
            <em>Análisis comparativo detallado entre lámparas para cada producto.</em>
        </p>
        
        <ul class="nav nav-tabs" id="differences-tabs" role="tablist">
    """
    
    # Generar pestañas
    for idx, product in enumerate(differences_data.keys()):
        active_class = "active" if idx == 0 else ""
        product_id = product.replace(' ', '-').replace('/', '-')
        html += f"""
                <li class="nav-item">
                    <a class="nav-link {active_class}" id="diff-tab-{product_id}" data-toggle="tab"
                       href="#diff-content-{product_id}" role="tab">{product}</a>
                </li>
        """
    
    html += """
            </ul>
            
            <div class="tab-content" id="differences-tabs-content">
    """
    
    # Generar contenido de cada pestaña
    for idx, (product, product_data) in enumerate(differences_data.items()):
        active_class = "show active" if idx == 0 else ""
        product_id = product.replace(' ', '-').replace('/', '-')
        baseline_lamp = product_data['baseline_lamp']
        comparisons = product_data['comparisons']
        
        html += f"""
                <div class="tab-pane fade {active_class}" id="diff-content-{product_id}" role="tabpanel">
                    <div class="product-section" style="margin-top: 20px;">
                        <h3 class="product-title">🔬 {product}</h3>
                        <p class="text-caption-small">
                            <strong>Lámpara Baseline:</strong> {baseline_lamp} 
                            (N = {comparisons[0]['n_baseline'] if comparisons else 'N/A'})
                        </p>
        """
        
        # Todas las comparaciones de este producto
        for comparison in comparisons:
            comp_lamp = comparison['lamp']
            n_compared = comparison['n_compared']
            differences = comparison['differences']
            
            # Obtener parámetros ordenados
            all_params = list(differences.keys())
            normal_params, mahalanobis_params = sort_params_custom(all_params)
            ordered_params = normal_params + mahalanobis_params
            
            # Preparar datos ordenados para la tabla
            table_data = []
            for param in ordered_params:
                if param in differences:
                    diff_data = differences[param]
                    baseline_val = diff_data['baseline_mean']
                    compared_val = diff_data['compared_mean']
                    abs_diff = diff_data['absolute_diff']
                    percent_diff = diff_data['percent_diff']
                    
                    direction = '↑' if abs_diff > 0 else '↓' if abs_diff < 0 else '='
                    
                    table_data.append({
                        'param': param,
                        'baseline': baseline_val,
                        'compared': compared_val,
                        'abs_diff': f"{direction} {abs(abs_diff):.3f}",
                        'percent_diff': f"{percent_diff:+.2f}%"
                    })
            
            # Definir columnas (SIN evaluación)
            columns = [
                {'key': 'param', 'header': 'Parámetro', 'align': 'left'},
                {'key': 'baseline', 'header': f'{baseline_lamp}<br/><span class="text-caption-small">(Baseline)</span>', 'format': '{:.3f}'},
                {'key': 'compared', 'header': f'{comp_lamp}<br/><span class="text-caption-small">(Comparada)</span>', 'format': '{:.3f}'},
                {'key': 'abs_diff', 'header': 'Δ Absoluta', 'align': 'center'},
                {'key': 'percent_diff', 'header': 'Δ Relativa (%)', 'align': 'center'}
            ]
            
            html += f"""
                        <h4 style="margin-top: 20px;">📍 {comp_lamp} vs {baseline_lamp} (N = {n_compared})</h4>
                        
                        <div class="table-overflow">
                            <table class="comparison-table">
                                <thead>
                                    <tr>
            """
            
            for col in columns:
                align = col.get('align', 'left')
                html += f'                                        <th style="text-align: {align};">{col["header"]}</th>\n'
            
            html += """
                                    </tr>
                                </thead>
                                <tbody>
            """
            
            for row in table_data:
                html += "                                    <tr>\n"
                for col in columns:
                    key = col['key']
                    value = row[key]
                    align = col.get('align', 'left')
                    
                    # Formatear si es necesario
                    if 'format' in col and isinstance(value, (int, float)):
                        value = col['format'].format(value)
                    
                    html += f'                                        <td style="text-align: {align};">{value}</td>\n'
                
                html += "                                    </tr>\n"
            
            html += """
                                </tbody>
                            </table>
                        </div>
            """
        
        html += """
                    </div>
                </div>
        """
    
    html += """
            </div>
        </div>
    """
    
    return html


def sort_params_custom(params: list) -> tuple:
    """
    Ordena parámetros en dos grupos: normales y Mahalanobis.
    
    Args:
        params: Lista de nombres de parámetros
        
    Returns:
        tuple: (normal_params, mahalanobis_params)
    """
    # Orden predefinido para parámetros normales
    normal_order = [
        'H', 'PB', 'FB', 'GB', 'Grasa Bruta', 'GT', 'Cz', 
        'ALM', 'Aw', 'Fosforo', 'Calcio'
    ]
    
    # Orden predefinido para Mahalanobis
    mahalanobis_order = [
        'MahalanobisH', 'MahalanobisPB', 'MahalanobisFB', 
        'MahalanobisGB', 'MahalanobisGT', 'MahalanobisCz', 
        'MahalanobisALM', 'MahalanobisP', 'MahalanobisCa'
    ]
    
    # Separar en dos grupos
    normal_params = []
    mahalanobis_params = []
    
    for param in params:
        if param.startswith('Mahalanobis'):
            mahalanobis_params.append(param)
        else:
            normal_params.append(param)
    
    # Función auxiliar para ordenar según lista predefinida
    def custom_sort(param_list, order_list):
        # Primero los que están en order_list (en ese orden)
        ordered = [p for p in order_list if p in param_list]
        # Luego los que NO están (alfabético)
        remaining = sorted([p for p in param_list if p not in order_list])
        return ordered + remaining
    
    normal_params = custom_sort(normal_params, normal_order)
    mahalanobis_params = custom_sort(mahalanobis_params, mahalanobis_order)
    
    return normal_params, mahalanobis_params


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
    
    # Definir secciones del sidebar - ORDEN ACTUALIZADO
    sections = [
        ("info-general", "Información General"),
        ("comparison-charts", "Gráficos Comparativos"),      # ⬆️ SUBIDO
        ("statistics", "Estadísticas Detalladas"),           # ⬇️ BAJADO
        ("differences-by-product", "Diferencias por Producto")
    ]
    
    # Iniciar HTML con template estandarizado (con Bootstrap)
    html = start_html_template(
        title="Reporte de Predicciones NIR",
        sidebar_sections=sections,
        include_bootstrap=True
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
    
    # ========================================================================
    # GRÁFICOS COMPARATIVOS CON PESTAÑAS - AHORA PRIMERO
    # ========================================================================
    params_ordered = get_params_in_original_order(analyzer, products)
    normal_params, mahalanobis_params = sort_params_custom(params_ordered)

    html += """
        <div class="info-box" id="comparison-charts">
            <h2>Gráficos Comparativos</h2>
            <p class="text-caption">
                <em>Análisis visual de las predicciones NIR entre diferentes lámparas.</em>
            </p>
    """

    # PESTAÑAS: PARÁMETROS NORMALES
    if normal_params:
        html += """
            <h3>📈 Parámetros Analíticos</h3>
            
            <ul class="nav nav-tabs" id="charts-normal-tabs" role="tablist">
        """
        
        for idx, param in enumerate(normal_params):
            active_class = "active" if idx == 0 else ""
            param_id = param.replace(' ', '-').replace('/', '-')
            html += f"""
                <li class="nav-item">
                    <a class="nav-link {active_class}" id="chart-tab-{param_id}" data-toggle="tab"
                       href="#chart-content-{param_id}" role="tab">{param}</a>
                </li>
            """
        
        html += """
            </ul>
            
            <div class="tab-content" id="charts-normal-tabs-content">
        """
        
        for idx, param in enumerate(normal_params):
            active_class = "show active" if idx == 0 else ""
            param_id = param.replace(' ', '-').replace('/', '-')
            fig = create_detailed_comparison(stats, param)
            
            if fig:
                chart_html = fig.to_html(
                    include_plotlyjs='cdn' if idx == 0 else False,
                    div_id=f"graph_{param.replace(' ', '_')}",
                    config={'displayModeBar': True, 'responsive': True}
                )
                
                html += f"""
                <div class="tab-pane fade {active_class}" id="chart-content-{param_id}" role="tabpanel">
                    <div class="plot-container" style="margin-top: 20px;">
                        {chart_html}
                    </div>
                </div>
                """
        
        html += """
            </div>
        """

    # PESTAÑAS: MAHALANOBIS
    if mahalanobis_params:
        html += """
            <h3 style="margin-top: 40px;">📊 Distancia de Mahalanobis</h3>
            
            <ul class="nav nav-tabs" id="charts-mahalanobis-tabs" role="tablist">
        """
        
        for idx, param in enumerate(mahalanobis_params):
            active_class = "active" if idx == 0 else ""
            param_id = param.replace(' ', '-').replace('/', '-')
            html += f"""
                <li class="nav-item">
                    <a class="nav-link {active_class}" id="chart-maha-tab-{param_id}" data-toggle="tab"
                       href="#chart-maha-content-{param_id}" role="tab">{param}</a>
                </li>
            """
        
        html += """
            </ul>
            
            <div class="tab-content" id="charts-mahalanobis-tabs-content">
        """
        
        for idx, param in enumerate(mahalanobis_params):
            active_class = "show active" if idx == 0 else ""
            param_id = param.replace(' ', '-').replace('/', '-')
            fig = create_detailed_comparison(stats, param)
            
            if fig:
                chart_html = fig.to_html(
                    include_plotlyjs=False,
                    div_id=f"graph_{param.replace(' ', '_')}",
                    config={'displayModeBar': True, 'responsive': True}
                )
                
                html += f"""
                <div class="tab-pane fade {active_class}" id="chart-maha-content-{param_id}" role="tabpanel">
                    <div class="plot-container" style="margin-top: 20px;">
                        {chart_html}
                    </div>
                </div>
                """
        
        html += """
            </div>
        """

    html += """
        </div>
    """
    
    # ========================================================================
    # ESTADÍSTICAS POR PRODUCTO - AHORA DESPUÉS DE LOS GRÁFICOS
    # ========================================================================
    html += """
        <div class="info-box" id="statistics">
            <h2>Estadísticas por Producto y Lámpara</h2>
            <p class="text-caption section-description">
                <em>Valores promedio y desviación estándar de cada parámetro analítico.</em>
            </p>
            
            <ul class="nav nav-tabs" id="stats-tabs" role="tablist">
    """
    
    # Generar pestañas
    for idx, product in enumerate(products):
        active_class = "active" if idx == 0 else ""
        product_id = product.replace(' ', '-').replace('/', '-')
        html += f"""
                <li class="nav-item">
                    <a class="nav-link {active_class}" id="tab-{product_id}" data-toggle="tab"
                       href="#content-{product_id}" role="tab">{product}</a>
                </li>
        """
    
    html += """
            </ul>
            
            <div class="tab-content" id="stats-tabs-content">
    """
    
    # Generar contenido de cada pestaña
    for idx, product in enumerate(products):
        active_class = "show active" if idx == 0 else ""
        product_id = product.replace(' ', '-').replace('/', '-')
        
        # Obtener parámetros del producto
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
                <div class="tab-pane fade {active_class}" id="content-{product_id}" role="tabpanel">
                    <div class="stats-table-container" style="margin-top: 20px;">
                        <table class="stats-table">
                            <thead>
                                <tr>
                                    <th class="sticky-col">Lámpara</th>
                                    <th>N</th>
        """
        
        for param in params:
            html += f'                                    <th>{param}<br/><span class="text-caption-small">(Media ± SD)</span></th>\n'
        
        html += """
                                </tr>
                            </thead>
                            <tbody>
        """
        
        for lamp, lamp_stats in stats[product].items():
            html += f"""
                                <tr>
                                    <td class="sticky-col">{lamp}</td>
                                    <td>{lamp_stats['n']}</td>
            """
            
            for param in params:
                if param in lamp_stats:
                    mean = lamp_stats[param]['mean']
                    std = lamp_stats[param]['std']
                    html += f'                                    <td>{mean:.3f} ± {std:.3f}</td>\n'
                else:
                    html += '                                    <td>-</td>\n'
            
            html += """
                                </tr>
            """
        
        html += """
                            </tbody>
                        </table>
                    </div>
                </div>
        """
    
    html += """
            </div>
        </div>
    """
    
    # Diferencias por producto
    differences_data = calculate_lamp_differences(stats, analyzer)
    
    if differences_data:
        html += generate_differences_section(differences_data, stats, analyzer)
    
    # Footer
    html += generate_footer()
    
    return html