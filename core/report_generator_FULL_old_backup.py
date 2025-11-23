"""
Generador de informes HTML
"""
import numpy as np
import pandas as pd
from datetime import datetime
import base64
from io import BytesIO
import matplotlib.pyplot as plt
from config import REPORT_STYLE, WSTD_THRESHOLDS, DIAGNOSTIC_STATUS
from core.spectral_processing import simulate_corrected_spectra
from utils.plotting import plot_corrected_spectra_comparison
import plotly.io as pio
from datetime import datetime

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
        # Fallback al CSS original si no encuentra el archivo
        from config import REPORT_STYLE
        return REPORT_STYLE

def generate_html_report(kit_data, baseline_data, ref_corrected, origin):
    import streamlit as st

    # === Contexto de sesión (opcionales) ===
    client_data = st.session_state.get('client_data', {}) or {}
    wstd_data   = st.session_state.get('wstd_data', {}) or {}

    # === (1) Extraer datos necesarios de kit_data y baseline_data ===
    # kit_data: esperado del pipeline de pasos 1–5
    try:
        df               = kit_data["df"]
        df_ref_grouped   = kit_data["df_ref_grouped"]
        df_new_grouped   = kit_data["df_new_grouped"]
        spectral_cols    = kit_data["spectral_cols"]
        lamp_ref         = kit_data["lamp_ref"]
        lamp_new         = kit_data["lamp_new"]
        common_ids       = kit_data["common_ids"]
        mean_diff        = kit_data["mean_diff"]
    except Exception as e:
        raise ValueError(f"[generate_html_report] kit_data incompleto: {e}")

    # baseline_data: baseline original (.ref o .csv) y cabecera si aplica
    try:
        ref_spectrum = baseline_data["ref_spectrum"]
        header       = baseline_data.get("header")
    except Exception as e:
        raise ValueError(f"[generate_html_report] baseline_data incompleto: {e}")

    # IDs seleccionados (si no hay, usa todas las comunes)
    selected_ids = st.session_state.get("selected_ids", list(common_ids))

    # === (2) Construir índice lateral dinámico ===
    sections = [
        "info-cliente",
        "process-details",
        "samples",
        "correction-stats",
        "correction-differences",
        "baseline-info",
        "charts-section",
        # "validation-section" se añade solo en generate_validation_report
        "control-samples-section",  # se mostrará solo si hay datos; la sección ya controla su visibilidad
    ]
    if isinstance(wstd_data, dict) and wstd_data.get("df") is not None:
        sections.insert(1, "wstd-section")

    # === (3) HTML inicial con sidebar ===
    html = start_html_document(client_data, sections=sections)

    # === (4) Secciones condicionales / fijas ===

    # 4.1 WSTD (si existe)
    if isinstance(wstd_data, dict) and wstd_data.get("df") is not None:
        html += generate_wstd_section(wstd_data)

    # 4.2 Detalles del proceso
    html += generate_process_details(
        lamp_ref, lamp_new, len(spectral_cols),
        len(common_ids), origin
    )

    # 4.3 Tabla de muestras
    html += generate_samples_table(df, common_ids, lamp_ref, lamp_new)

    # 4.4 Espectros seleccionados ANTES de corrección
    html += generate_selected_samples_chart(
        df_ref_grouped, df_new_grouped, spectral_cols,
        lamp_ref, lamp_new, selected_ids
    )

    # 4.5 Estadísticas de corrección
    html += generate_correction_statistics(mean_diff)

    # 4.6 Gráficos de diferencias espectrales (Paso 5)
    html += generate_correction_differences_charts(
        df_ref_grouped, df_new_grouped, mean_diff,
        common_ids, selected_ids, lamp_ref, lamp_new
    )

    # 4.7 Baseline: info + gráfico Original vs Corregido
    html += generate_baseline_info(
        ref_corrected, header, origin,
        ref_spectrum, spectral_cols
    )

    # 4.8 Notas adicionales (si el usuario las guardó)
    if client_data.get("notes"):
        html += generate_notes_section(client_data["notes"])

    # 4.9 Resultados gráficos (ANTES vs DESPUÉS con corrección simulada)
    html += generate_charts_section(
        df_ref_grouped=df_ref_grouped,
        df_new_grouped=df_new_grouped,
        spectral_cols=spectral_cols,
        lamp_ref=lamp_ref,
        lamp_new=lamp_new,
        common_ids=common_ids,
        selected_ids=selected_ids,
        ref_spectrum=ref_spectrum,
        ref_corrected=ref_corrected
    )

    # 4.10 Footer
    html += generate_footer()

    return html

def start_html_document(client_data, sections=None):
    """
    Inicia el documento HTML con información del cliente y barra lateral dinámica.
    """
    # Si no se pasa lista de secciones, usa todas
    default_sections = [
        "info-cliente",
        "wstd-section",
        "process-details",
        "samples",
        "correction-stats",
        "correction-differences",
        "baseline-info",
        "charts-section",
        "validation-section",
        "control-samples-section",
    ]
    sections = sections or default_sections

    labels = {
        "info-cliente": "Información del Cliente",
        "wstd-section": "Diagnóstico WSTD",
        "process-details": "Detalles del Proceso",
        "samples": "Muestras del Standard Kit",
        "correction-stats": "Estadísticas de la Corrección",
        "correction-differences": "Diferencias Espectrales",
        "baseline-info": "Baseline Generado",
        "charts-section": "Resultados Gráficos",
        "validation-section": "Validación",
        "control-samples-section": "Muestras de Control",
    }

    sidebar_items = "\n".join(
        f'<li><a href="#{sid}">{labels.get(sid, sid)}</a></li>'
        for sid in sections if sid in labels
    )

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            {load_buchi_css()}
            .sidebar {{
                position: fixed; left: 0; top: 0; width: 250px; height: 100%;
                background-color: #093A34; padding: 20px; overflow-y: auto; z-index: 1000;
            }}
            .sidebar ul {{ list-style: none; padding: 0; }}
            .sidebar ul li {{ margin-bottom: 10px; }}
            .sidebar ul li a {{
                color: white; text-decoration: none; display: block; padding: 8px;
                border-radius: 5px; transition: background-color 0.3s; font-weight: bold;
            }}
            .sidebar ul li a:hover {{ background-color: #289A93; }}
            .main-content {{ margin-left: 270px; padding: 20px; }}
        </style>
    </head>
    <body>
        <div class="sidebar">
            <ul>
                {sidebar_items}
            </ul>
        </div>

        <div class="main-content">
        <h1>Informe de Ajuste de Baseline NIR</h1>
        <div class="info-box" id="info-cliente">
            <h2>Información del Cliente</h2>
            <table>
                <tr><th>Campo</th><th>Valor</th></tr>
                <tr><td><strong>Cliente</strong></td><td>{client_data.get('client_name', 'N/A')}</td></tr>
                <tr><td><strong>Contacto</strong></td><td>{client_data.get('contact_person', 'N/A')}</td></tr>
                <tr><td><strong>Email</strong></td><td>{client_data.get('contact_email', 'N/A')}</td></tr>
                <tr><td><strong>N/S Sensor</strong></td><td>{client_data.get('sensor_sn', 'N/A')}</td></tr>
                <tr><td><strong>Modelo</strong></td><td>{client_data.get('equipment_model', 'N/A')}</td></tr>
                <tr><td><strong>Técnico</strong></td><td>{client_data.get('technician', 'N/A')}</td></tr>
                <tr><td><strong>Ubicación</strong></td><td>{client_data.get('location', 'N/A')}</td></tr>
                <tr><td><strong>Fecha del Proceso</strong></td><td>{client_data.get('date', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}</td></tr>
            </table>
        </div>
    """
    return html


def generate_wstd_section(wstd_data):
    """
    Genera la sección de diagnóstico WSTD.
    
    Args:
        wstd_data (dict): Datos del diagnóstico WSTD
        
    Returns:
        str: HTML de la sección WSTD
    """
    df_wstd = wstd_data['df']
    spectral_cols = wstd_data['spectral_cols']
    
    html = """
        <div class="warning-box" id="wstd-section">
            <h2>Diagnóstico Inicial - White Standard (sin línea base)</h2>
            <p><strong>Estado del sistema ANTES del ajuste:</strong></p>
            <table>
                <tr>
                    <th>ID</th>
                    <th>Desv. Máxima</th>
                    <th>Desv. Media</th>
                    <th>Desv. Estándar</th>
                    <th>Estado</th>
                </tr>
    """
    
    # Iterar sobre cada medición individual
    for idx, row in df_wstd.iterrows():
        spectrum = row[spectral_cols].values
        max_val = np.max(np.abs(spectrum))
        mean_val = np.mean(np.abs(spectrum))
        std_val = np.std(spectrum)
        
        # Determinar estado
        if max_val < WSTD_THRESHOLDS['good']:
            status = '<span class="status-good">🟢 Bien ajustado</span>'
        elif max_val < WSTD_THRESHOLDS['warning']:
            status = '<span class="status-warning">🟡 Desviación moderada</span>'
        else:
            status = '<span class="status-bad">🔴 Requiere ajuste</span>'
        
        html += f"""
            <tr>
                <td><strong>{row['ID']}</strong></td>
                <td>{max_val:.6f}</td>
                <td>{mean_val:.6f}</td>
                <td>{std_val:.6f}</td>
                <td>{status}</td>
            </tr>
        """
    
    html += """
            </table>
            <p style="margin-top: 10px; font-size: 0.9em; color: #6c757d;">
            <em>Nota: Las mediciones del White Standard sin línea base deben estar cercanas a 0 
            en todo el espectro si el sistema está bien calibrado. Estas métricas muestran 
            la desviación respecto al valor ideal (0).</em>
            </p>
        </div>
    """
    
    # NUEVO: Añadir gráficos
    html += generate_wstd_charts(df_wstd, spectral_cols)
    
    return html


def generate_wstd_charts(df_wstd, spectral_cols):
    """
    Genera los gráficos de WSTD para el reporte.
    
    Args:
        df_wstd (pd.DataFrame): DataFrame con mediciones WSTD
        spectral_cols (list): Lista de columnas espectrales
        
    Returns:
        str: HTML con los gráficos embebidos
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    
    html = "<h2>Gráficos de Diagnóstico WSTD</h2>"
    
    # Crear el gráfico
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(
            'Espectros WSTD - Desviación respecto a referencia ideal',
            'Diferencias entre mediciones WSTD'
        ),
        vertical_spacing=0.12
    )
    
    channels = list(range(1, len(spectral_cols) + 1))
    selected_indices = df_wstd.index.tolist()
    
    # Subplot 1: Espectros individuales
    for i, (idx, row) in enumerate(df_wstd.iterrows()):
        spectrum = row[spectral_cols].values
        label = f"Fila {idx}: {row['ID']}"
        
        fig.add_trace(
            go.Scatter(
                x=channels,
                y=spectrum,
                mode='lines',
                name=label,
                line=dict(width=1.5),
                hovertemplate=f'{label}<br>Canal: %{{x}}<br>Desviación: %{{y:.6f}}<extra></extra>'
            ),
            row=1, col=1
        )
    
    # Línea de referencia en y=0 para subplot 1
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5, row=1, col=1)
    
    # Subplot 2: Diferencias entre mediciones
    if len(df_wstd) >= 2:
        spectra_list = [row[spectral_cols].values for idx, row in df_wstd.iterrows()]
        
        if len(df_wstd) == 2:
            diff = spectra_list[0] - spectra_list[1]
            label_diff = f"Fila {selected_indices[0]} - Fila {selected_indices[1]}"
            
            fig.add_trace(
                go.Scatter(
                    x=channels,
                    y=diff,
                    mode='lines',
                    name=label_diff,
                    line=dict(width=2, color='red'),
                    hovertemplate=f'{label_diff}<br>Canal: %{{x}}<br>Diferencia: %{{y:.6f}}<extra></extra>',
                    showlegend=False
                ),
                row=2, col=1
            )
        else:
            for i in range(1, len(spectra_list)):
                diff = spectra_list[0] - spectra_list[i]
                label_diff = f"Fila {selected_indices[0]} - Fila {selected_indices[i]}"
                
                fig.add_trace(
                    go.Scatter(
                        x=channels,
                        y=diff,
                        mode='lines',
                        name=label_diff,
                        line=dict(width=1.5),
                        hovertemplate=f'{label_diff}<br>Canal: %{{x}}<br>Diferencia: %{{y:.6f}}<extra></extra>',
                        showlegend=False
                    ),
                    row=2, col=1
                )
        
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5, row=2, col=1)
    
    # Layout
    fig.update_xaxes(title_text="Canal espectral", row=1, col=1)
    fig.update_xaxes(title_text="Canal espectral", row=2, col=1)
    fig.update_yaxes(title_text="Desviación", row=1, col=1)
    fig.update_yaxes(title_text="Diferencia", row=2, col=1)
    
    fig.update_layout(
        height=800,
        showlegend=True,
        hovermode='closest',
        template='plotly_white'
    )
    
    # Convertir a HTML
    chart_html = fig.to_html(
        include_plotlyjs='cdn',
        div_id='wstd_charts',
        config={'displayModeBar': True, 'responsive': True}
    )
    
    # ⭐ CAMBIO: Envolver en expandible
    html += wrap_chart_in_expandable(
        chart_html,
        "Ver gráficos de diagnóstico WSTD",
        "wstd_charts_expandable",
        default_open=False
    )
    
    return html

def generate_process_details(lamp_ref, lamp_new, n_spectral, n_samples, origin):
    """
    Genera la sección de detalles del proceso.
    
    Args:
        lamp_ref (str): Lámpara de referencia
        lamp_new (str): Lámpara nueva
        n_spectral (int): Número de canales espectrales
        n_samples (int): Número de muestras
        origin (str): Tipo de archivo
        
    Returns:
        str: HTML de detalles
    """
    import streamlit as st
    
    used_ids = st.session_state.get('selected_ids', [])
    
    html = f"""
        <div class="info-box" id="process-details">
            <h2>Detalles del Proceso</h2>
            <table>
                <tr>
                    <th>Parámetro</th>
                    <th>Valor</th>
                </tr>
                <tr>
                    <td><strong>Lámpara de Referencia</strong></td>
                    <td>{lamp_ref}</td>
                </tr>
                <tr>
                    <td><strong>Lámpara Nueva</strong></td>
                    <td>{lamp_new}</td>
                </tr>
                <tr>
                    <td><strong>Canales Espectrales</strong></td>
                    <td>{n_spectral}</td>
                </tr>
                <tr>
                    <td><strong>Muestras Comunes</strong></td>
                    <td>{n_samples}</td>
                </tr>
                <tr>
                    <td><strong>Muestras usadas en corrección</strong></td>
                    <td>{len(used_ids)}</td>
                </tr>
                <tr>
                    <td><strong>Formato Baseline</strong></td>
                    <td>.{origin}</td>
                </tr>
            </table>
        </div>
    """
    return html

def generate_samples_table(df, common_ids, lamp_ref, lamp_new):
    """
    Genera la tabla de muestras del Standard Kit.
    
    Args:
        df (pd.DataFrame): DataFrame completo
        common_ids (list): IDs comunes
        lamp_ref (str): Lámpara de referencia
        lamp_new (str): Lámpara nueva
        
    Returns:
        str: HTML de la tabla
    """
    import streamlit as st
    
    used_ids = st.session_state.get('selected_ids', list(common_ids))
    
    html = "<h2 id='samples'>Muestras del Standard Kit</h2>"
    
    # Construir la tabla
    table_html = """
        <table>
            <tr>
                <th>ID Muestra</th>
                <th>Mediciones """ + lamp_ref + """</th>
                <th>Mediciones """ + lamp_new + """</th>
                <th>Usada para corrección</th>
            </tr>
    """
    
    for id_ in common_ids:
        count_ref = len(df[(df['ID'] == id_) & (df['Note'] == lamp_ref)])
        count_new = len(df[(df['ID'] == id_) & (df['Note'] == lamp_new)])
        used_tag = '<span class="tag tag-ok">✓ Sí</span>' if id_ in used_ids else '<span class="tag tag-no">✗ No</span>'
        
        table_html += f"""
            <tr>
                <td>{id_}</td>
                <td>{count_ref}</td>
                <td>{count_new}</td>
                <td>{used_tag}</td>
            </tr>
        """
    
    table_html += "</table>"
    
    # ⭐ CAMBIO: Envolver tabla en expandible
    html += wrap_chart_in_expandable(
        table_html,
        f"Ver detalle de muestras ({len(common_ids)} muestras)",
        "samples_table_expandable",
        default_open=False
    )
    
    return html

def generate_selected_samples_chart(df_ref_grouped, df_new_grouped, spectral_cols,
                                    lamp_ref, lamp_new, selected_ids):
    """
    Genera el gráfico de muestras seleccionadas ANTES de la corrección.
    
    Args:
        df_ref_grouped (pd.DataFrame): Espectros de referencia
        df_new_grouped (pd.DataFrame): Espectros nuevos (sin corregir)
        spectral_cols (list): Columnas espectrales
        lamp_ref (str): Nombre lámpara referencia
        lamp_new (str): Nombre lámpara nueva
        selected_ids (list): IDs seleccionados
        
    Returns:
        str: HTML con el gráfico embebido
    """
    from utils.plotting import plot_kit_spectra
    
    html = """
        <div class="info-box">
            <h3>Espectros de las Muestras Seleccionadas (ANTES de corrección)</h3>
            <p style='color: #6c757d; font-size: 0.95em;'>
                <em>Comparación de los espectros medidos con ambas lámparas antes de aplicar 
                la corrección. Estas muestras fueron usadas para calcular el ajuste de baseline.</em>
            </p>
    """
    
    fig = plot_kit_spectra(
        df_ref_grouped, df_new_grouped, spectral_cols,
        lamp_ref, lamp_new, selected_ids
    )
    
    chart_html = fig.to_html(
        include_plotlyjs='cdn',
        div_id='selected_samples_before',
        config={'displayModeBar': True, 'responsive': True}
    )
    
    # ⭐ CAMBIO: Envolver en expandible
    html += wrap_chart_in_expandable(
        chart_html,
        "Ver espectros de muestras seleccionadas",
        "selected_samples_expandable",
        default_open=False
    )
    
    html += "</div>"
    
    return html

def generate_correction_statistics(mean_diff):
    """
    Genera la sección de estadísticas de corrección.
    
    Args:
        mean_diff (np.array): Vector de corrección
        
    Returns:
        str: HTML de estadísticas
    """
    max_corr = np.max(np.abs(mean_diff))
    mean_corr = np.mean(np.abs(mean_diff))
    std_corr = np.std(mean_diff)
    
    html = f"""
        <div class="info-box" id="correction-stats">
            <h2>Estadísticas de la Corrección</h2>
            <table style="margin-top: 15px;">
                <tr>
                    <th>Métrica</th>
                    <th>Valor</th>
                    <th>Descripción</th>
                </tr>
                <tr>
                    <td><strong>Corrección Máxima</strong></td>
                    <td>{max_corr:.6f}</td>
                    <td>Máxima desviación absoluta que se corrige en cualquier canal espectral</td>
                </tr>
                <tr>
                    <td><strong>Corrección Media</strong></td>
                    <td>{mean_corr:.6f}</td>
                    <td>Promedio de las correcciones aplicadas a lo largo de todos los canales</td>
                </tr>
                <tr>
                    <td><strong>Desviación Estándar</strong></td>
                    <td>{std_corr:.6f}</td>
                    <td>Variabilidad de la corrección entre diferentes canales espectrales</td>
                </tr>
            </table>
        </div>
    """
    return html

def generate_correction_differences_charts(df_ref_grouped, df_new_grouped, mean_diff,
                                          common_ids, selected_ids, lamp_ref, lamp_new):
    """
    Genera los gráficos de diferencias espectrales (del Paso 5).
    
    Args:
        df_ref_grouped (pd.DataFrame): Espectros de referencia
        df_new_grouped (pd.DataFrame): Espectros nuevos
        mean_diff (np.array): Vector de corrección promedio
        common_ids (list): Todos los IDs comunes
        selected_ids (list): IDs usados en corrección
        lamp_ref (str): Nombre lámpara referencia
        lamp_new (str): Nombre lámpara nueva
        
    Returns:
        str: HTML con los gráficos embebidos
    """
    from utils.plotting import plot_correction_differences
    
    # Construir DataFrame de diferencias (igual que en el Paso 5)
    df_diff = pd.DataFrame({"Canal": range(1, len(mean_diff) + 1)})
    
    for id_ in common_ids:
        df_diff[f"{lamp_ref}_{id_}"] = df_ref_grouped.loc[id_].values
        df_diff[f"{lamp_new}_{id_}"] = df_new_grouped.loc[id_].values
        df_diff[f"DIF_{id_}"] = (
            df_ref_grouped.loc[id_].values - df_new_grouped.loc[id_].values
        )
    
    df_diff["CORRECCION_PROMEDIO"] = mean_diff
    
    # Identificar muestras no usadas
    ids_not_used = [id_ for id_ in common_ids if id_ not in selected_ids]
    
    html = """
        <div class="info-box" id="correction-differences">
            <h2>Diferencias Espectrales - Análisis Detallado</h2>
    """
    
    # GRÁFICO 1: Muestras usadas en la corrección
    html += "<h3>Muestras Usadas en la Corrección</h3>"
    
    if len(selected_ids) < len(common_ids):
        html += f"<p style='color: #6c757d; font-size: 0.95em;'><em>Mostrando {len(selected_ids)} de {len(common_ids)} muestras (usadas en la corrección)</em></p>"
    else:
        html += f"<p style='color: #6c757d; font-size: 0.95em;'><em>Mostrando todas las {len(selected_ids)} muestras</em></p>"
    
    fig_used = plot_correction_differences(df_diff, selected_ids, selected_ids)
    chart_html_used = fig_used.to_html(
        include_plotlyjs='cdn',
        div_id='correction_differences_used',
        config={'displayModeBar': True, 'responsive': True}
    )
    
    # ⭐ CAMBIO: Envolver en expandible
    html += wrap_chart_in_expandable(
        chart_html_used,
        "Ver gráfico de diferencias espectrales (muestras usadas)",
        "correction_used_expandable",
        default_open=False
    )
    
    # GRÁFICO 2: Muestras de validación (si existen)
    if len(ids_not_used) > 0:
        html += "<h3>Validación - Muestras NO Usadas en la Corrección</h3>"
        html += f"""
            <p style='color: #6c757d; font-size: 0.95em;'>
                <em>Mostrando {len(ids_not_used)} muestras que <strong>NO</strong> se usaron para calcular la corrección.<br>
                Este gráfico muestra cómo la corrección calculada afecta a muestras independientes,
                permitiendo validar que la corrección es robusta y generalizable.</em>
            </p>
        """
        
        fig_validation = plot_correction_differences(df_diff, ids_not_used, ids_not_used)
        chart_html_validation = fig_validation.to_html(
            include_plotlyjs='cdn',
            div_id='correction_differences_validation',
            config={'displayModeBar': True, 'responsive': True}
        )
        
        # ⭐ CAMBIO: Envolver en expandible
        html += wrap_chart_in_expandable(
            chart_html_validation,
            "Ver gráfico de validación (muestras NO usadas)",
            "correction_validation_expandable",
            default_open=False
        )
        
        # Estadísticas de validación
        html += generate_validation_statistics_html(df_diff, ids_not_used, mean_diff)
    else:
        html += """
            <p style='color: #17a2b8; background-color: #d1ecf1; padding: 15px; border-radius: 5px; border-left: 4px solid #17a2b8;'>
                <strong>ℹ️ Información:</strong> Todas las muestras se están usando para la corrección. 
                No hay muestras de validación disponibles.
            </p>
        """
    
    html += "</div>"
    
    return html

def generate_validation_statistics_html(df_diff, ids_not_used, mean_diff):
    """
    Genera las estadísticas de validación en formato HTML.
    
    Args:
        df_diff (pd.DataFrame): DataFrame con diferencias
        ids_not_used (list): IDs no usados en corrección
        mean_diff (np.array): Vector de corrección promedio
        
    Returns:
        str: HTML con estadísticas
    """
    html = "<h4>Estadísticas de Validación</h4>"
    
    # Calcular diferencias promedio por muestra de validación
    validation_diffs = []
    for id_ in ids_not_used:
        diff_col = f"DIF_{id_}"
        if diff_col in df_diff.columns:
            sample_diff = df_diff[diff_col].values
            validation_diffs.append(sample_diff)
    
    if validation_diffs:
        validation_diffs = np.array(validation_diffs)
        validation_mean = np.mean(validation_diffs, axis=0)
        
        # Comparar con la corrección calculada
        residual = validation_mean - mean_diff
        
        max_residual = np.max(np.abs(residual))
        mean_residual = np.mean(np.abs(residual))
        std_residual = np.std(residual)
        
        html += """
            <table style="margin-top: 15px;">
                <tr>
                    <th>Métrica</th>
                    <th>Valor</th>
                    <th>Descripción</th>
                </tr>
        """
        
        html += f"""
                <tr>
                    <td><strong>Residuo máximo</strong></td>
                    <td>{max_residual:.6f}</td>
                    <td>Diferencia máxima entre la corrección calculada y las muestras de validación</td>
                </tr>
                <tr>
                    <td><strong>Residuo medio</strong></td>
                    <td>{mean_residual:.6f}</td>
                    <td>Diferencia media entre la corrección calculada y las muestras de validación</td>
                </tr>
                <tr>
                    <td><strong>Desv. estándar residuo</strong></td>
                    <td>{std_residual:.6f}</td>
                    <td>Variabilidad del residuo</td>
                </tr>
            </table>
        """
        
        # Interpretación
        if max_residual < 0.01:
            html += """
                <div class="status-good" style="margin-top: 15px; padding: 15px; border-radius: 5px;">
                    <strong>✅ Excelente validación:</strong> Las muestras no usadas muestran diferencias 
                    muy similares a la corrección calculada.
                </div>
            """
        elif max_residual < 0.05:
            html += """
                <div style="margin-top: 15px; padding: 15px; border-radius: 5px; background-color: #d1ecf1; border-left: 4px solid #17a2b8;">
                    <strong>ℹ️ Buena validación:</strong> Las muestras no usadas son consistentes con la corrección.
                </div>
            """
        else:
            html += """
                <div class="status-warning" style="margin-top: 15px; padding: 15px; border-radius: 5px;">
                    <strong>⚠️ Atención:</strong> Hay diferencias significativas en las muestras de validación. 
                    Considera revisar la selección de muestras.
                </div>
            """
    
    return html

def generate_baseline_info(ref_corrected, header, origin, ref_spectrum, spectral_cols):
    """
    Genera la sección de información del baseline generado con gráfico comparativo.
    
    Args:
        ref_corrected (np.array): Baseline corregido
        header (np.array): Cabecera del .ref
        origin (str): Tipo de archivo
        ref_spectrum (np.array): Baseline original
        spectral_cols (list): Columnas espectrales
        
    Returns:
        str: HTML de información del baseline
    """
    html = f"""
        <div class="info-box" id="baseline-info">
            <h2>Baseline Generado</h2>
            <table>
                <tr>
                    <th>Parámetro</th>
                    <th>Valor</th>
                </tr>
                <tr>
                    <td><strong>Puntos Espectrales</strong></td>
                    <td>{len(ref_corrected)}</td>
                </tr>
    """
    
    if origin == 'ref' and header is not None:
        html += f"""
                <tr>
                    <td><strong>Cabecera X1</strong></td>
                    <td>{header[0]:.6e}</td>
                </tr>
                <tr>
                    <td><strong>Cabecera X2</strong></td>
                    <td>{header[1]:.6e}</td>
                </tr>
                <tr>
                    <td><strong>Cabecera X3</strong></td>
                    <td>{header[2]:.6e}</td>
                </tr>
        """
    
    html += """
            </table>
            
            <h3 style="margin-top: 30px;">Comparación: Baseline Original vs Corregido</h3>
            <p style='color: #6c757d; font-size: 0.95em;'>
                <em>Visualización del baseline antes y después de aplicar la corrección calculada.</em>
            </p>
    """
    
    from utils.plotting import plot_baseline_comparison
    
    fig = plot_baseline_comparison(ref_spectrum, ref_corrected, spectral_cols)
    
    # Convertir a HTML
    chart_html = fig.to_html(
        include_plotlyjs='cdn',
        div_id='baseline_comparison_chart',
        config={'displayModeBar': True, 'responsive': True}
    )
    
    # ⭐ CAMBIO: Envolver en expandible
    html += wrap_chart_in_expandable(
        chart_html,
        "Ver comparación de baseline (Original vs Corregido)",
        "baseline_comparison_expandable",
        default_open=False
    )
    
    html += "</div>"
    
    return html

def generate_notes_section(notes):
    """
    Genera la sección de notas adicionales.
    
    Args:
        notes (str): Notas del cliente
        
    Returns:
        str: HTML de notas
    """
    html = f"""
        <div class="info-box">
            <h2>📝 Notas Adicionales</h2>
            <p>{notes}</p>
        </div>
    """
    return html

def generate_charts_section(
    df_ref_grouped,
    df_new_grouped,
    spectral_cols,
    lamp_ref,
    lamp_new,
    common_ids,
    selected_ids,
    ref_spectrum,
    ref_corrected
):
    """
    Genera la sección de gráficos del informe comparando:
    - ANTES: espectros sin corrección
    - DESPUÉS: espectros con corrección aplicada
    """

    # 1) Aplicar corrección simulada a la lámpara nueva
    df_new_corr = simulate_corrected_spectra(
        df_new_grouped,
        spectral_cols,
        ref_spectrum,
        ref_corrected
    )

    # 2) Separar en "usadas en corrección" vs "no usadas"
    used_ids = list(selected_ids)
    other_ids = [i for i in common_ids if i not in used_ids]

    html = '<h2 id="charts-section">Resultados Gráficos</h2>'

    # 3) Muestras usadas en la corrección → ANTES y DESPUÉS (en vertical)
    if len(used_ids) > 0:
        html += "<h3>Muestras usadas en la corrección</h3>"
        html += "<p style='color: #6c757d; font-size: 0.95em;'><em>Comparativa antes y después de aplicar la corrección.</em></p>"

        # ANTES: SIN corrección
        fig_used_before = plot_corrected_spectra_comparison(
            df_ref_grouped,
            df_new_grouped,  # SIN corrección
            spectral_cols,
            lamp_ref,
            lamp_new + " (original)",
            used_ids,
            "Referencia vs Nueva ORIGINAL (muestras usadas)"
        )
        chart_used_before = fig_used_before.to_html(
            include_plotlyjs='cdn',
            div_id='chart_used_before',
            config={'displayModeBar': True, 'responsive': True}
        )
        html += wrap_chart_in_expandable(
            chart_used_before,
            "Ver espectros SIN corrección (muestras usadas)",
            "chart_used_before_expandable",
            default_open=False
        )

        # DESPUÉS: CON corrección
        fig_used_after = plot_corrected_spectra_comparison(
            df_ref_grouped,
            df_new_corr,  # CON corrección
            spectral_cols,
            lamp_ref,
            lamp_new + " (corregida)",
            used_ids,
            "Referencia vs Nueva CORREGIDA (muestras usadas)"
        )
        chart_used_after = fig_used_after.to_html(
            include_plotlyjs=False,
            div_id='chart_used_after',
            config={'displayModeBar': True, 'responsive': True}
        )
        html += wrap_chart_in_expandable(
            chart_used_after,
            "Ver espectros CON corrección (muestras usadas)",
            "chart_used_after_expandable",
            default_open=False
        )

    # 4) Muestras NO usadas (validación) → ANTES y DESPUÉS (en vertical)
    if len(other_ids) > 0:
        html += '<h3 id="validation-section">Muestras de Validación (no usadas en la corrección)</h3>'
        html += "<p style='color: #6c757d; font-size: 0.95em;'><em>Comparativa antes y después de aplicar la corrección.</em></p>"

        # ANTES: SIN corrección
        include_js = 'cdn' if len(used_ids) == 0 else False
        fig_val_before = plot_corrected_spectra_comparison(
            df_ref_grouped,
            df_new_grouped,  # SIN corrección
            spectral_cols,
            lamp_ref,
            lamp_new + " (original)",
            other_ids,
            "Referencia vs Nueva ORIGINAL (validación)"
        )
        chart_val_before = fig_val_before.to_html(
            include_plotlyjs=include_js,
            div_id='chart_validation_before',
            config={'displayModeBar': True, 'responsive': True}
        )
        html += wrap_chart_in_expandable(
            chart_val_before,
            "Ver espectros SIN corrección (validación)",
            "chart_validation_before_expandable",
            default_open=False
        )

        # DESPUÉS: CON corrección
        fig_val_after = plot_corrected_spectra_comparison(
            df_ref_grouped,
            df_new_corr,  # CON corrección
            spectral_cols,
            lamp_ref,
            lamp_new + " (corregida)",
            other_ids,
            "Referencia vs Nueva CORREGIDA (validación)"
        )
        chart_val_after = fig_val_after.to_html(
            include_plotlyjs=False,
            div_id='chart_validation_after',
            config={'displayModeBar': True, 'responsive': True}
        )
        html += wrap_chart_in_expandable(
            chart_val_after,
            "Ver espectros CON corrección (validación)",
            "chart_validation_after_expandable",
            default_open=False
        )

    return html

def _df_to_html_table(df: pd.DataFrame, float_fmt="{:.2f}", index=False) -> str:
    if df is None or df.empty:
        return "<p><em>Sin datos</em></p>"
    df_fmt = df.copy()
    for c in df_fmt.select_dtypes(include="number").columns:
        df_fmt[c] = df_fmt[c].apply(lambda x: float_fmt.format(x) if pd.notna(x) else "")
    return df_fmt.to_html(index=index, classes="table", border=0)

def generate_control_samples_section():
    """
    Sección de 'Validación con Muestras de Control' (opcional).
    Requiere que existan en session_state:
      - control_samples_initial: {'df', 'spectral_cols', 'sample_ids'}
      - control_samples_final:   {'df', 'spectral_cols', 'sample_ids'}
    """
    import streamlit as st
    import pandas as pd
    from utils.control_samples import (
        extract_predictions_from_results,
        get_prediction_parameters,
        compare_predictions,
        plot_spectra_comparison,
        plot_predictions_comparison,
        calculate_spectral_metrics
    )

    ctrl_ini = st.session_state.get('control_samples_initial')
    ctrl_fin = st.session_state.get('control_samples_final')
    if not ctrl_ini or not ctrl_fin:
        return ""  # no hay sección

    # --- Datos base ---
    df_initial = ctrl_ini['df'].copy()
    df_final   = ctrl_fin['df'].copy()
    spec_ini   = ctrl_ini.get('spectral_cols', [])
    spec_fin   = ctrl_fin.get('spectral_cols', [])
    ids_ini    = [str(x).strip() for x in ctrl_ini.get('sample_ids', [])]
    ids_fin    = [str(x).strip() for x in ctrl_fin.get('sample_ids', [])]

    # Normaliza IDs
    df_initial['ID'] = df_initial['ID'].astype(str).str.strip()
    df_final['ID']   = df_final['ID'].astype(str).str.strip()

    # IDs comunes
    common_ids = sorted(list(set(ids_ini) & set(ids_fin)))
    if not common_ids:
        return """
        <div class="warning-box" id="control-samples-section" style="margin-top: 30px;">
            <h2>Validación con Muestras de Control</h2>
            <p><em>No se encontraron IDs comunes entre las muestras de control iniciales y finales.</em></p>
        </div>
        """

    # Columnas espectrales compatibles
    if len(spec_ini) != len(spec_fin):
        min_len = min(len(spec_ini), len(spec_fin))
        spectral_cols = spec_ini[:min_len]
        note_specs = f"⚠️ Inicial: {len(spec_ini)} canales, Final: {len(spec_fin)} canales → usando {min_len} comunes."
    else:
        spectral_cols = spec_ini
        note_specs = f"Canales espectrales: {len(spectral_cols)}"

    # === 1) Comparación espectral ===
    fig_spectra = plot_spectra_comparison(
        df_initial[df_initial['ID'].isin(common_ids)],
        df_final[df_final['ID'].isin(common_ids)],
        spectral_cols,
        common_ids
    )
    chart_html_spectra = fig_spectra.to_html(
        include_plotlyjs='cdn',
        div_id='ctrl_spectra',
        config={'displayModeBar': True, 'responsive': True}
    )

    spectral_metrics = calculate_spectral_metrics(
        df_initial[df_initial['ID'].isin(common_ids)],
        df_final[df_final['ID'].isin(common_ids)],
        spectral_cols,
        common_ids
    )
    # spectral_metrics -> dict; lo paso a DF para tabla
    rows = []
    for sid, m in spectral_metrics.items():
        rows.append({
            "Muestra": sid,
            "Dif. media": m['mean_diff'],
            "Desv. estándar": m['std_diff'],
            "Dif. máx. abs.": m['max_diff'],
            "RMSE": m['rmse'],
            "Correlación": m['correlation'],
        })
    df_spec_metrics = pd.DataFrame(rows)

    # Tabla de métricas (HTML)
    spec_table_html = _df_to_html_table(df_spec_metrics, float_fmt="{:.6f}", index=False)

    # === 2) Comparación de predicciones ===
    pred_ini = extract_predictions_from_results(df_initial[df_initial['ID'].isin(common_ids)])
    pred_fin = extract_predictions_from_results(df_final[df_final['ID'].isin(common_ids)])

    pred_block = ""
    if pred_ini is not None and not pred_ini.empty and pred_fin is not None and not pred_fin.empty:
        params_initial = get_prediction_parameters(pred_ini)
        params_final   = get_prediction_parameters(pred_fin)
        common_params  = [p for p in params_initial if p in params_final]

        if common_params:
            cmp_df = compare_predictions(pred_ini, pred_fin, common_ids)

            # Gráfico barras
            fig_pred = plot_predictions_comparison(cmp_df, common_params)
            chart_html_pred = (
                fig_pred.to_html(
                    include_plotlyjs='cdn',
                    div_id='ctrl_predictions',
                    config={'displayModeBar': True, 'responsive': True}
                ) if fig_pred else "<p><em>Sin gráfico</em></p>"
            )

            # Tabla bonita (solo columnas relevantes y en orden)
            cols = ['ID']
            for p in common_params:
                cols += [f'{p}_initial', f'{p}_final', f'{p}_diff', f'{p}_diff_pct']
            cmp_show = cmp_df[cols].copy()
            for c in cmp_show.columns:
                if c.endswith('_diff_pct'):
                    cmp_show[c] = cmp_show[c].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "")
                elif c != 'ID':
                    cmp_show[c] = cmp_show[c].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "")

            # Render tabla a HTML y envolverla en expandible con scroll
            table_html = _df_to_html_table(cmp_show, float_fmt="{:.2f}", index=False)
            table_html_scroll = f"<div style='overflow-x:auto'>{table_html}</div>"
            table_wrapped = wrap_chart_in_expandable(
                table_html_scroll,
                "Ver tabla completa de comparación",
                "ctrl_pred_table_expand",
                False
            )

            pred_block = (
                f"<h3>2) Comparación de Predicciones</h3>"
                f"<p style='color:#6c757d;font-size:0.95em;'>Parámetros detectados: {', '.join(common_params)}.</p>"
                f"{wrap_chart_in_expandable(chart_html_pred, 'Ver comparación de predicciones', 'ctrl_pred_expand', False)}"
                f"{table_wrapped}"
            )
        else:
            pred_block = """
                <h3>2) Comparación de Predicciones</h3>
                <p><em>No hay parámetros comunes (ParamN) entre inicial y final.</em></p>
            """
    else:
        pred_block = """
            <h3>2) Comparación de Predicciones</h3>
            <p><em>No se pudieron extraer predicciones de uno o ambos conjuntos.</em></p>
        """

    # Empaquetado HTML (gráficos en vertical + expandibles cerrados)
    html = f"""
        <div class="info-box" id="control-samples-section" style="margin-top: 30px;">
            <h2>Validación con Muestras de Control</h2>
            <p style="color:#6c757d;font-size:0.95em;">
                IDs comunes: {", ".join(common_ids)}<br>
                {note_specs}
            </p>

            <h3>1) Comparación Espectral</h3>
            {wrap_chart_in_expandable(chart_html_spectra, "Ver comparación de espectros (control)", "ctrl_spec_expand", False)}
            <h4>Métricas espectrales</h4>
            {spec_table_html}

            {pred_block}
        </div>
    """
    return html
    
def generate_footer():
    """
    Genera el footer del informe.
    
    Returns:
        str: HTML del footer
    """
    html = f"""
        <div class="footer">
            <p>Informe generado automáticamente por Baseline Adjustment Tool</p>
            <p>Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </body>
    </html>
    """
    return html

def generate_validation_report(kit_data, baseline_data, ref_corrected, origin, 
                               validation_data, mean_diff_before, mean_diff_after):
    """
    Genera un informe HTML completo incluyendo validacion.
    
    Args:
        kit_data (dict): Datos del Standard Kit original
        baseline_data (dict): Datos del baseline
        ref_corrected (np.array): Baseline corregido
        origin (str): Tipo de archivo ('ref' o 'csv')
        validation_data (dict): Datos de validacion
        mean_diff_before (np.array): Diferencia antes de correccion
        mean_diff_after (np.array): Diferencia despues de correccion
        
    Returns:
        str: Contenido HTML del informe completo
    """
    import streamlit as st
    
    # Generar el informe base (pasos 1-5)
    html = generate_html_report(kit_data, baseline_data, ref_corrected, origin)
    
    # Quitar el footer temporal
    html = html.replace(generate_footer(), "")
    
    # Agregar seccion de validacion
    html += generate_validation_section(validation_data, mean_diff_before, mean_diff_after)
    
    # >>> NUEVO: Sección de Muestras de Control (si existen en session_state)
    html += generate_control_samples_section()
    
    # Agregar footer final
    html += generate_footer()
    
    return html

def generate_validation_section(validation_data, mean_diff_before, mean_diff_after):
    """
    Genera la seccion de validacion para el informe.
    
    Args:
        validation_data (dict): Datos de validacion
        mean_diff_before (np.array): Diferencia antes
        mean_diff_after (np.array): Diferencia despues
        
    Returns:
        str: HTML de la seccion de validacion
    """
    df_ref_val = validation_data['df_ref_val']
    df_new_val = validation_data['df_new_val']
    lamp_ref = validation_data['lamp_ref']
    lamp_new = validation_data['lamp_new']
    common_ids = validation_data['common_ids']
    selected_ids = validation_data['selected_ids']
    spectral_cols = validation_data.get('spectral_cols', df_ref_val.columns.tolist())
    
    # Calcular metricas
    max_before = np.max(np.abs(mean_diff_before))
    max_after = np.max(np.abs(mean_diff_after))
    mean_before = np.mean(np.abs(mean_diff_before))
    mean_after = np.mean(np.abs(mean_diff_after))
    std_before = np.std(mean_diff_before)
    std_after = np.std(mean_diff_after)
    
    improvement_max = ((max_before - max_after) / max_before * 100) if max_before != 0 else 0
    improvement_mean = ((mean_before - mean_after) / mean_before * 100) if mean_before != 0 else 0
    
    # Determinar estado
    if max_after < 0.001:
        status_class = "status-good"
        status_text = "EXCELENTE"
        status_icon = "🟢"
    elif max_after < 0.01:
        status_class = "status-good"
        status_text = "BUENO"
        status_icon = "🟢"
    elif improvement_mean > 50:
        status_class = "status-warning"
        status_text = "ACEPTABLE"
        status_icon = "🟡"
    else:
        status_class = "status-bad"
        status_text = "REQUIERE REVISION"
        status_icon = "🔴"
    
    html = f"""
        <div class="warning-box" id="validation-section" style="margin-top: 30px;">
            <h2>Validacion Post-Correccion</h2>
            <p><strong>Verificacion del ajuste con mediciones reales:</strong></p>
        </div>
        
        <div class="info-box">
            <h2>Detalles de la Validacion</h2>
            <table>
                <tr>
                    <th>Parámetro</th>
                    <th>Valor</th>
                </tr>
                <tr>
                    <td><strong>Lámpara de Referencia</strong></td>
                    <td>{lamp_ref}</td>
                </tr>
                <tr>
                    <td><strong>Lámpara Nueva</strong></td>
                    <td>{lamp_new}</td>
                </tr>
                <tr>
                    <td><strong>Muestras medidas</strong></td>
                    <td>{len(common_ids)}</td>
                </tr>
                <tr>
                    <td><strong>Muestras usadas en validación</strong></td>
                    <td>{len(selected_ids)}</td>
                </tr>
            </table>
        </div>
        
        <div class="info-box">
            <h2>Resultados de la Validacion</h2>
            <table>
                <tr>
                    <th>Metrica</th>
                    <th>Antes de Correccion</th>
                    <th>Despues de Correccion</th>
                    <th>Mejora</th>
                </tr>
                <tr>
                    <td><strong>Diferencia Maxima</strong></td>
                    <td>{max_before:.6f}</td>
                    <td>{max_after:.6f}</td>
                    <td><span class="status-good">↓ {improvement_max:.1f}%</span></td>
                </tr>
                <tr>
                    <td><strong>Diferencia Media</strong></td>
                    <td>{mean_before:.6f}</td>
                    <td>{mean_after:.6f}</td>
                    <td><span class="status-good">↓ {improvement_mean:.1f}%</span></td>
                </tr>
                <tr>
                    <td><strong>Desviacion Estandar</strong></td>
                    <td>{std_before:.6f}</td>
                    <td>{std_after:.6f}</td>
                    <td><span class="status-good">↓ {std_before - std_after:.6f}</span></td>
                </tr>
            </table>
        </div>
    """
    
    # NUEVO: Agregar graficos de validacion
    html += generate_validation_charts(
        df_ref_val, df_new_val, spectral_cols,
        lamp_ref, lamp_new, selected_ids,
        mean_diff_before, mean_diff_after
    )
    
    html += f"""
        <div class="{status_class}" style="padding: 20px; margin: 20px 0; border-radius: 5px;">
            <h2>{status_icon} Conclusion de la Validacion: {status_text}</h2>
            <p style="font-size: 1.1em; margin: 10px 0;">
                La diferencia espectral entre lamparas se redujo en un <strong>{improvement_mean:.1f}%</strong>.
            </p>
            <p style="margin: 10px 0;">
                Diferencia maxima actual: <strong>{max_after:.6f}</strong>
            </p>
    """
    
    # Agregar recomendaciones segun el resultado
    if max_after < 0.001:
        html += """
            <p style="margin-top: 15px;">
                <strong>El ajuste de baseline es optimo.</strong> Las lamparas estan perfectamente alineadas 
                y el sistema esta listo para uso en produccion.
            </p>
        """
    elif max_after < 0.01:
        html += """
            <p style="margin-top: 15px;">
                <strong>El ajuste de baseline funciona correctamente.</strong> Las lamparas estan bien alineadas 
                y el sistema puede usarse con confianza.
            </p>
        """
    elif improvement_mean > 50:
        html += """
            <p style="margin-top: 15px;">
                <strong>Correccion aceptable pero mejorable.</strong> Se recomienda:
                <ul>
                    <li>Revisar la calidad de las mediciones del Standard Kit</li>
                    <li>Verificar las condiciones ambientales durante las mediciones</li>
                    <li>Evaluar el estado de las lamparas</li>
                </ul>
            </p>
        """
    else:
        html += """
            <p style="margin-top: 15px;">
                <strong>La correccion requiere revision.</strong> Acciones recomendadas:
                <ul>
                    <li>Verificar que el baseline corregido se instalo correctamente</li>
                    <li>Reiniciar el equipo si es necesario</li>
                    <li>Asegurar condiciones estables durante las mediciones</li>
                    <li>Considerar repetir el proceso con diferentes muestras</li>
                </ul>
            </p>
        """
    
    html += """
        </div>
        
        <div class="info-box">
            <h2>Muestras de Validacion</h2>
    """
    
    # Envolver tabla en expandible
    table_html = """
        <table>
            <tr>
                <th>ID Muestra</th>
                <th>Mediciones """ + lamp_ref + """</th>
                <th>Mediciones """ + lamp_new + """</th>
                <th>Usada en validacion</th>
            </tr>
    """
    
    for id_ in common_ids:
        count_ref = 1 if id_ in df_ref_val.index else 0
        count_new = 1 if id_ in df_new_val.index else 0
        used_tag = '<span class="tag tag-ok">✓ Si</span>' if id_ in selected_ids else '<span class="tag tag-no">✗ No</span>'
        
        table_html += f"""
            <tr>
                <td>{id_}</td>
                <td>{count_ref}</td>
                <td>{count_new}</td>
                <td>{used_tag}</td>
            </tr>
        """
    
    table_html += "</table>"
    
    # Envolver tabla en expandible
    html += wrap_chart_in_expandable(
        table_html,
        f"Ver detalle de muestras de validación ({len(common_ids)} muestras)",
        "validation_samples_table_expandable",
        default_open=False
    )
    
    html += "</div>"
    
    return html

def generate_validation_charts(df_ref_val, df_new_val, spectral_cols,
                               lamp_ref, lamp_new, selected_ids,
                               mean_diff_before, mean_diff_after):
    """
    Genera los graficos de validacion.
    
    Args:
        df_ref_val (pd.DataFrame): Espectros de referencia en validacion
        df_new_val (pd.DataFrame): Espectros nuevos en validacion
        spectral_cols (list): Columnas espectrales
        lamp_ref (str): Lampara de referencia
        lamp_new (str): Lampara nueva
        selected_ids (list): IDs seleccionados
        mean_diff_before (np.array): Diferencia antes
        mean_diff_after (np.array): Diferencia despues
        
    Returns:
        str: HTML con los graficos embebidos
    """
    from utils.plotting import plot_kit_spectra
    import plotly.graph_objects as go
    
    html = "<h2>Graficos de Validacion</h2>"
    
    # Grafico 1: Espectros de validacion
    html += "<h3>Espectros de las muestras de validacion</h3>"
    html += "<p style='color: #6c757d; font-size: 0.95em;'><em>Comparacion de espectros medidos con ambas lamparas despues de aplicar la correccion.</em></p>"
    
    fig_spectra = plot_kit_spectra(
        df_ref_val, df_new_val, spectral_cols,
        lamp_ref, lamp_new, selected_ids
    )
    
    chart_html_spectra = fig_spectra.to_html(
        include_plotlyjs='cdn',
        div_id='validation_spectra',
        config={'displayModeBar': True, 'responsive': True}
    )
    
    # ⭐ CAMBIO: Envolver en expandible
    html += wrap_chart_in_expandable(
        chart_html_spectra,
        "Ver espectros de validación",
        "validation_spectra_expandable",
        default_open=False
    )
    
    # Grafico 2: Comparacion ANTES vs DESPUES
    html += "<h3>Comparacion: Diferencia espectral ANTES vs DESPUES</h3>"
    html += "<p style='color: #6c757d; font-size: 0.95em;'><em>Visualizacion de la mejora obtenida tras aplicar la correccion de baseline.</em></p>"
    
    fig_comparison = go.Figure()
    
    channels = list(range(1, len(mean_diff_before) + 1))
    
    # Diferencia ANTES
    fig_comparison.add_trace(go.Scatter(
        x=channels,
        y=mean_diff_before,
        mode='lines',
        name='ANTES de correccion',
        line=dict(width=2, color='red'),
        hovertemplate='Canal: %{x}<br>Diferencia: %{y:.6f}<extra></extra>'
    ))
    
    # Diferencia DESPUES
    fig_comparison.add_trace(go.Scatter(
        x=channels,
        y=mean_diff_after,
        mode='lines',
        name='DESPUES de correccion',
        line=dict(width=2, color='green'),
        hovertemplate='Canal: %{x}<br>Diferencia: %{y:.6f}<extra></extra>'
    ))
    
    # Linea de referencia
    fig_comparison.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    fig_comparison.update_layout(
        title='Diferencia espectral: ANTES vs DESPUES de aplicar correccion',
        xaxis_title='Canal espectral',
        yaxis_title='Diferencia',
        height=600,
        hovermode='closest',
        template='plotly_white',
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="right",
            x=0.99
        )
    )
    
    chart_html_comparison = fig_comparison.to_html(
        include_plotlyjs='cdn',
        div_id='validation_comparison',
        config={'displayModeBar': True, 'responsive': True}
    )
    
    # ⭐ CAMBIO: Envolver en expandible
    html += wrap_chart_in_expandable(
        chart_html_comparison,
        "Ver comparación ANTES vs DESPUÉS",
        "validation_comparison_expandable",
        default_open=False
    )
    
    return html

def generate_partial_report(
    kit_data=None,
    baseline_data=None,
    ref_corrected=None,
    origin=None,
    validation_data=None,
    mean_diff_before=None,
    mean_diff_after=None
):
    import streamlit as st

    client_data = st.session_state.get('client_data', {})
    wstd_data   = st.session_state.get('wstd_data')

    # Construye el índice dinámico
    sections = ["info-cliente"]
    if isinstance(wstd_data, dict) and wstd_data.get('df') is not None:
        sections.append("wstd-section")
    # Si habrá validación, añade la entrada al índice
    has_validation = (
        validation_data is not None
        and mean_diff_before is not None
        and mean_diff_after is not None
    )
    if has_validation:
        sections.append("validation-section")
    # Muestras de control se anexa si hay datos (la función ya gestiona vacío)
    sections.append("control-samples-section")

    html = start_html_document(client_data, sections=sections)

    # WSTD (si existe)
    if isinstance(wstd_data, dict) and wstd_data.get('df') is not None:
        try:
            html += generate_wstd_section(wstd_data)
        except Exception as e:
            html += f"""
                <div class="warning-box" id="wstd-section">
                    <h2>Diagnóstico WSTD</h2>
                    <p><em>No se pudo renderizar la sección WSTD: {e}</em></p>
                </div>
            """

    # Si NO hay baseline/kit completos, avisa
    if not (kit_data and baseline_data and ref_corrected and origin):
        html += """
            <div class="warning-box" style="margin-top: 20px;">
                <h2>Secciones no disponibles</h2>
                <p><em>No hay datos suficientes para el informe completo (pasos 1–6).</em></p>
            </div>
        """

    # Validación (si hay datos “after”)
    if has_validation:
        try:
            html += generate_validation_section(validation_data, mean_diff_before, mean_diff_after)
        except Exception as e:
            html += f"""
                <div class="warning-box" id="validation-section" style="margin-top: 20px;">
                    <h2>Validación</h2>
                    <p><em>No se pudo renderizar la validación: {e}</em></p>
                </div>
            """

    # Muestras de Control (si existen en session_state)
    try:
        ctrl_html = generate_control_samples_section()
        if ctrl_html:
            html += ctrl_html
    except Exception as e:
        html += f"""
            <div class="warning-box" id="control-samples-section">
                <h2>Muestras de Control</h2>
                <p><em>No se pudo renderizar la sección de control: {e}</em></p>
            </div>
        """

    html += generate_footer()
    return html
