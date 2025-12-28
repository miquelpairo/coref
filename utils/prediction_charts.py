"""
Prediction Charts - Funciones para crear gráficos de comparación NIR
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from .nir_analyzer import get_params_in_original_order


def create_comparison_plots(stats, analyzer):
    """Crear gráficos comparativos entre lámparas para todos los parámetros"""
    
    # Preparar datos para gráficos
    products = list(stats.keys())
    
    # Obtener todas las lámparas
    lamps = set()
    for product_stats in stats.values():
        lamps.update(product_stats.keys())
    
    lamps = sorted(list(lamps))
    
    if len(lamps) < 2:
        st.warning("Se necesitan al menos 2 lámparas diferentes para comparar.")
        return None
    
    # Selector de producto
    st.markdown("### Configuración de comparación")
    selected_product = st.selectbox(
        "Selecciona el producto a visualizar:",
        products,
        key='comparison_product'
    )
    
    # Verificar que el producto tenga lámparas disponibles
    if selected_product not in stats or not stats[selected_product]:
        st.warning(f"No hay datos disponibles para {selected_product}")
        return None
    
    available_lamps_for_product = sorted(list(stats[selected_product].keys()))
    
    # Selector de lámparas (hasta 4)
    st.markdown("#### Selecciona las lámparas a comparar (mínimo 2, máximo 4)")
    
    col1, col2, col3, col4 = st.columns(4)
    
    selected_lamps = []
    
    with col1:
        lamp1 = st.selectbox("Lámpara 1:", available_lamps_for_product, key='comp_lamp1')
        selected_lamps.append(lamp1)
    
    with col2:
        available_for_lamp2 = [l for l in available_lamps_for_product if l != lamp1]
        if available_for_lamp2:
            lamp2 = st.selectbox("Lámpara 2:", available_for_lamp2, key='comp_lamp2')
            selected_lamps.append(lamp2)
    
    with col3:
        available_for_lamp3 = [l for l in available_lamps_for_product if l not in selected_lamps]
        if len(available_for_lamp3) > 0:
            lamp3_options = ["(ninguna)"] + available_for_lamp3
            lamp3 = st.selectbox("Lámpara 3 (opcional):", lamp3_options, key='comp_lamp3')
            if lamp3 != "(ninguna)":
                selected_lamps.append(lamp3)
    
    with col4:
        available_for_lamp4 = [l for l in available_lamps_for_product if l not in selected_lamps]
        if len(available_for_lamp4) > 0:
            lamp4_options = ["(ninguna)"] + available_for_lamp4
            lamp4 = st.selectbox("Lámpara 4 (opcional):", lamp4_options, key='comp_lamp4')
            if lamp4 != "(ninguna)":
                selected_lamps.append(lamp4)
    
    if len(selected_lamps) < 2:
        st.warning("Por favor selecciona al menos 2 lámparas para comparar.")
        return None
    
    # Obtener todos los parámetros disponibles para el producto seleccionado
    all_params = set()
    for lamp in selected_lamps:
        if lamp in stats[selected_product]:
            all_params.update([k for k in stats[selected_product][lamp].keys() if k not in ['n', 'note']])
    
    all_params = sorted(list(all_params))
    
    if not all_params:
        st.warning("No se encontraron parámetros para comparar.")
        return None
    
    # Usar la primera lámpara como baseline
    baseline_lamp = selected_lamps[0]
    comparison_lamps = selected_lamps[1:]
    
    # Calcular diferencias para cada lámpara comparada con el baseline
    differences = {param: {} for param in all_params}
    
    for param in all_params:
        if param in stats[selected_product][baseline_lamp]:
            baseline_value = stats[selected_product][baseline_lamp][param]['mean']
            
            for lamp in comparison_lamps:
                if lamp in stats[selected_product] and param in stats[selected_product][lamp]:
                    lamp_value = stats[selected_product][lamp][param]['mean']
                    diff = lamp_value - baseline_value
                    differences[param][lamp] = diff
    
    # Filtrar parámetros que tienen al menos un valor
    params_with_data = [p for p in all_params if any(differences[p].values() if differences[p] else [])]
    
    if not params_with_data:
        st.warning("No hay datos suficientes para comparar entre las lámparas seleccionadas.")
        return None
    
    # Calcular número de filas y columnas para subplots
    n_params = len(params_with_data)
    n_cols = min(3, n_params)
    n_rows = (n_params + n_cols - 1) // n_cols
    
    # Crear subplots
    fig = make_subplots(
        rows=n_rows, 
        cols=n_cols,
        subplot_titles=[f'{param}' for param in params_with_data],
        vertical_spacing=0.15,
        horizontal_spacing=0.10
    )
    
    # Colores para cada lámpara
    lamp_colors = {}
    color_palette = ['#FF6B6B', '#4ECDC4', '#95E1D3']
    
    for idx, lamp in enumerate(comparison_lamps):
        lamp_colors[lamp] = color_palette[idx] if idx < len(color_palette) else '#95A5A6'
    
    for idx, param in enumerate(params_with_data):
        row = idx // n_cols + 1
        col = idx % n_cols + 1
        
        # Obtener valores de diferencia para este parámetro
        lamps_list = list(differences[param].keys())
        values = list(differences[param].values())
        
        if not values:
            continue
        
        # Crear barras para cada lámpara comparada
        for lamp_idx, lamp in enumerate(lamps_list):
            if lamp in differences[param]:
                value = differences[param][lamp]
                color = lamp_colors.get(lamp, '#95A5A6')
                
                fig.add_trace(
                    go.Bar(
                        name=lamp,
                        x=[lamp],
                        y=[value],
                        marker=dict(color=color),
                        text=[f"{value:+.3f}"],
                        textposition='inside',
                        textfont=dict(color='white', size=10),
                        showlegend=(idx == 0),
                        legendgroup=lamp
                    ),
                    row=row, col=col
                )
        
        # Configurar eje Y independiente para cada parámetro
        if values:
            max_abs = max(abs(v) for v in values)
            y_range = [-max_abs * 1.2, max_abs * 1.2]
            
            fig.update_yaxes(
                title_text=f"Δ (%)",
                row=row, 
                col=col,
                range=y_range,
                zeroline=True,
                zerolinewidth=2,
                zerolinecolor='black'
            )
        
        fig.update_xaxes(title_text="", row=row, col=col)
    
    # Configurar layout
    fig.update_layout(
        height=300 * n_rows,
        title_text=f"<b>{selected_product}</b> - Diferencias respecto a {baseline_lamp}",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5,
            title=dict(text="Lámparas comparadas:")
        ),
        barmode='group'
    )
    
    return fig


def create_detailed_comparison(stats, param='H'):
    """Crear gráfico de comparación detallada por producto"""
    
    from app_config.plotting import PLOTLY_TEMPLATE
    
    products = list(stats.keys())
    lamps = set()
    for product_stats in stats.values():
        lamps.update(product_stats.keys())
    lamps = sorted(list(lamps))
    
    # Filtrar productos que tienen datos para el parámetro seleccionado
    products_with_data = []
    for product in products:
        has_data = False
        for lamp in lamps:
            if lamp in stats[product] and param in stats[product][lamp]:
                has_data = True
                break
        if has_data:
            products_with_data.append(product)
    
    if not products_with_data:
        return None
    
    # Calcular valor máximo para ajustar escala Y
    max_val = 0
    for product in products_with_data:
        for lamp in lamps:
            if lamp in stats[product] and param in stats[product][lamp]:
                max_val = max(max_val, stats[product][lamp][param]['mean'])
    
    # Número de subplots
    n_products = len(products_with_data)
    
    # Calcular anchos proporcionales
    column_widths = [1.0 / n_products] * n_products
    
    fig = make_subplots(
        rows=1, cols=n_products,
        subplot_titles=[f"{prod}" for prod in products_with_data],
        column_widths=column_widths,
        horizontal_spacing=0.02
    )
    
    # Colores BUCHI importados
    colors = PLOTLY_TEMPLATE['layout']['colorway']
    
    for col_idx, product in enumerate(products_with_data):
        for lamp_idx, lamp in enumerate(lamps):
            if lamp in stats[product]:
                if param in stats[product][lamp]:
                    mean_val = stats[product][lamp][param]['mean']
                    
                    fig.add_trace(
                        go.Bar(
                            name=lamp,
                            x=[lamp],
                            y=[mean_val],
                            marker=dict(color=colors[lamp_idx % len(colors)]),
                            showlegend=(col_idx == 0),
                            text=[f"{mean_val:.2f}"],
                            textposition='inside'
                        ),
                        row=1, col=col_idx+1
                    )
        
        # Eliminar título del eje Y
        fig.update_yaxes(
            title_text="",
            row=1, 
            col=col_idx+1,
            range=[0, max_val * 1.15]
        )
    
    # Ajustar layout con ancho fijo
    fig.update_layout(
        width=1150,
        height=500,
        autosize=False,
        showlegend=True,
        barmode='group',
        margin=dict(l=50, r=50, t=80, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig

def create_box_plots(stats, analyzer):
    """Crear box plots para todos los productos y parámetros"""
    
    products = list(stats.keys())
    
    # Obtener parámetros en orden original
    params = get_params_in_original_order(analyzer, products)
    
    # Permitir selección de parámetros
    selected_params = st.multiselect(
        "Selecciona parámetros para visualizar en box plots:",
        params,
        default=params[:2] if len(params) >= 2 else params,
        key='boxplot_params'
    )
    
    if not selected_params:
        return None
    
    colors = px.colors.qualitative.Plotly
    lamps = set()
    for product_stats in stats.values():
        lamps.update(product_stats.keys())
    lamps = sorted(list(lamps))
    
    # Para cada parámetro, verificar qué productos tienen datos
    params_products_data = {}
    for param in selected_params:
        products_with_data = []
        for product in products:
            has_data = False
            for lamp in lamps:
                if lamp in stats[product] and param in stats[product][lamp]:
                    has_data = True
                    break
            if has_data:
                products_with_data.append(product)
        
        if products_with_data:
            params_products_data[param] = products_with_data
    
    if not params_products_data:
        st.warning("No hay datos disponibles para los parámetros seleccionados")
        return None
    
    # Calcular estructura de subplots
    n_params = len(params_products_data)
    max_products = max(len(prods) for prods in params_products_data.values())
    
    # Crear títulos correctos
    titles = []
    for param in selected_params:
        if param in params_products_data:
            for product in params_products_data[param]:
                titles.append(f"{product} - {param}")
    
    fig = make_subplots(
        rows=n_params, 
        cols=max_products,
        subplot_titles=titles if len(titles) <= n_params * max_products else None,
        vertical_spacing=0.1,
        horizontal_spacing=0.05
    )
    
    # Recrear trazas con estructura correcta
    row_idx = 0
    for param in selected_params:
        if param not in params_products_data:
            continue
            
        row_idx += 1
        products_with_data = params_products_data[param]
        
        for col_idx, product in enumerate(products_with_data):
            for lamp_idx, lamp in enumerate(lamps):
                if lamp in stats[product] and param in stats[product][lamp]:
                    values = stats[product][lamp][param]['values']
                    
                    fig.add_trace(
                        go.Box(
                            name=lamp,
                            y=values,
                            marker=dict(color=colors[lamp_idx % len(colors)]),
                            showlegend=(row_idx == 1 and col_idx == 0),
                            boxmean='sd'
                        ),
                        row=row_idx, col=col_idx+1
                    )
            
            if col_idx == 0:
                fig.update_yaxes(title_text=f"{param} (%)", row=row_idx, col=col_idx+1)
    
    fig.update_layout(
        height=300 * n_params,
        title_text="Comparación de Predicciones por Lámpara",
        showlegend=True
    )
    
    return fig


def create_scatter_plots(stats):
    """Crear scatter plots H vs PB"""
    
    products = list(stats.keys())
    lamps = set()
    for product_stats in stats.values():
        lamps.update(product_stats.keys())
    lamps = sorted(list(lamps))
    
    # Buscar parámetros H y PB (o similares)
    param_h = None
    param_pb = None
    
    for product_stats in stats.values():
        for lamp_stats in product_stats.values():
            for param in lamp_stats.keys():
                if param not in ['n', 'note']:
                    if 'H' in param.upper() and param_h is None:
                        param_h = param
                    if 'PB' in param.upper() or 'PROTEIN' in param.upper():
                        param_pb = param
    
    if param_h is None or param_pb is None:
        st.warning("No se encontraron parámetros de Humedad (H) y Proteína (PB)")
        return None
    
    n_products = len(products)
    
    fig = make_subplots(
        rows=1, cols=n_products,
        subplot_titles=[f"{prod} - {param_h} vs {param_pb}" for prod in products]
    )
    
    colors = px.colors.qualitative.Plotly
    
    for col_idx, product in enumerate(products):
        for lamp_idx, lamp in enumerate(lamps):
            if lamp in stats[product]:
                if param_h in stats[product][lamp] and param_pb in stats[product][lamp]:
                    h_values = stats[product][lamp][param_h]['values']
                    pb_values = stats[product][lamp][param_pb]['values']
                    
                    fig.add_trace(
                        go.Scatter(
                            name=lamp,
                            x=h_values,
                            y=pb_values,
                            mode='markers',
                            marker=dict(
                                color=colors[lamp_idx % len(colors)],
                                size=10,
                                line=dict(width=1, color='white')
                            ),
                            showlegend=(col_idx == 0)
                        ),
                        row=1, col=col_idx+1
                    )
        
        fig.update_xaxes(title_text=f"{param_h} (%)", row=1, col=col_idx+1)
        if col_idx == 0:
            fig.update_yaxes(title_text=f"{param_pb} (%)", row=1, col=col_idx+1)
    
    fig.update_layout(
        height=400,
        title_text=f"{param_h} vs {param_pb}",
        showlegend=True
    )
    
    return fig