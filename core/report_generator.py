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
    """
    Genera el informe HTML completo del proceso de ajuste de baseline.
    
    Args:
        kit_data (dict): Datos del proceso (white standards)
        baseline_data (dict): Datos del baseline original
        ref_corrected (np.array): Baseline corregido
        origin (str): Tipo de archivo ('ref' o 'csv')
        
    Returns:
        str: Contenido HTML del informe
    """
    import streamlit as st

    # Contexto de sesión
    client_data = st.session_state.get('client_data', {}) or {}
    wstd_data   = st.session_state.get('wstd_data', {}) or {}

    # Extraer datos necesarios de kit_data y baseline_data
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

    try:
        ref_spectrum = baseline_data["ref_spectrum"]
        header       = baseline_data.get("header")
    except Exception as e:
        raise ValueError(f"[generate_html_report] baseline_data incompleto: {e}")

    # IDs seleccionados
    selected_ids = st.session_state.get("selected_ids", list(common_ids))

    # Construir índice lateral dinámico
    sections = [
        "info-cliente",
        "process-details",
        "white-correction",
        "correction-stats",
        "correction-vector",
        "baseline-info",
    ]
    if isinstance(wstd_data, dict) and wstd_data.get("df") is not None:
        sections.insert(1, "wstd-section")

    # HTML inicial con sidebar
    html = start_html_document(client_data, sections=sections)

    # Secciones del informe
    
    # WSTD inicial (si existe)
    if isinstance(wstd_data, dict) and wstd_data.get("df") is not None:
        html += generate_wstd_section(wstd_data)

    # Detalles del proceso
    html += generate_process_details(
        lamp_ref, lamp_new, len(spectral_cols),
        len(common_ids), origin
    )

    # Mediciones white standard usadas en la corrección
    html += generate_white_correction_chart(
        df_ref_grouped, df_new_grouped, spectral_cols,
        lamp_ref, lamp_new, selected_ids
    )

    # Estadísticas de corrección
    html += generate_correction_statistics(mean_diff)

    # Vector de corrección
    html += generate_correction_vector_section(
        df_ref_grouped, df_new_grouped, mean_diff,
        common_ids, selected_ids, lamp_ref, lamp_new
    )

    # Baseline: info + gráfico Original vs Corregido
    html += generate_baseline_info(
        ref_corrected, header, origin,
        ref_spectrum, spectral_cols
    )

    # Notas adicionales (si el usuario las guardó)
    if client_data.get("notes"):
        html += generate_notes_section(client_data["notes"])

    # Footer
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
        "white-correction",
        "correction-stats",
        "correction-vector",
        "baseline-info",
        "verification-section",
    ]
    sections = sections or default_sections

    labels = {
        "info-cliente": "Información del Cliente",
        "wstd-section": "Diagnóstico WSTD Inicial",
        "process-details": "Detalles del Proceso",
        "white-correction": "Corrección con White Standard",
        "correction-stats": "Estadísticas de la Corrección",
        "correction-vector": "Vector de Corrección",
        "baseline-info": "Baseline Generado",
        "verification-section": "Verificación Post-Ajuste",
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
        n_samples (int): Número de mediciones white standard
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
                    <td><strong>Mediciones White Standard</strong></td>
                    <td>{n_samples}</td>
                </tr>
                <tr>
                    <td><strong>Mediciones usadas en corrección</strong></td>
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


def generate_white_correction_chart(df_ref_grouped, df_new_grouped, spectral_cols,
                                    lamp_ref, lamp_new, selected_ids):
    """
    Genera el gráfico de white standards usados para calcular la corrección.
    
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
        <div class="info-box" id="white-correction">
            <h2>Corrección con White Standard</h2>
            <h3>Mediciones White Standard Usadas en la Corrección</h3>
            <p style='color: #6c757d; font-size: 0.95em;'>
                <em>Comparación de las mediciones de white standard con baseline original (referencia) 
                y baseline nueva (antes de corrección). Estas mediciones se usaron para calcular el vector de corrección.</em>
            </p>
    """
    
    fig = plot_kit_spectra(
        df_ref_grouped, df_new_grouped, spectral_cols,
        lamp_ref, lamp_new, selected_ids
    )
    
    chart_html = fig.to_html(
        include_plotlyjs='cdn',
        div_id='white_correction_chart',
        config={'displayModeBar': True, 'responsive': True}
    )
    
    html += wrap_chart_in_expandable(
        chart_html,
        "Ver mediciones white standard usadas",
        "white_correction_expandable",
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

def generate_correction_vector_section(df_ref_grouped, df_new_grouped, mean_diff,
                                       common_ids, selected_ids, lamp_ref, lamp_new):
    """
    Genera la sección del vector de corrección calculado.
    
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
    
    # Construir DataFrame de diferencias
    df_diff = pd.DataFrame({"Canal": range(1, len(mean_diff) + 1)})
    
    for id_ in common_ids:
        df_diff[f"{lamp_ref}_{id_}"] = df_ref_grouped.loc[id_].values
        df_diff[f"{lamp_new}_{id_}"] = df_new_grouped.loc[id_].values
        df_diff[f"DIF_{id_}"] = (
            df_ref_grouped.loc[id_].values - df_new_grouped.loc[id_].values
        )
    
    df_diff["CORRECCION_PROMEDIO"] = mean_diff
    
    # Identificar mediciones no usadas
    ids_not_used = [id_ for id_ in common_ids if id_ not in selected_ids]
    
    html = """
        <div class="info-box" id="correction-vector">
            <h2>Vector de Corrección</h2>
            <p style='color: #6c757d; font-size: 0.95em;'>
                <em>El vector de corrección representa el ajuste espectral calculado a partir de las 
                diferencias entre las mediciones white standard con baseline original y baseline nueva.</em>
            </p>
    """
    
    # GRÁFICO 1: Mediciones usadas en la corrección
    html += "<h3>Diferencias Espectrales - Mediciones Usadas</h3>"
    
    if len(selected_ids) < len(common_ids):
        html += f"<p style='color: #6c757d; font-size: 0.95em;'><em>Mostrando {len(selected_ids)} de {len(common_ids)} mediciones (usadas en el cálculo)</em></p>"
    else:
        html += f"<p style='color: #6c757d; font-size: 0.95em;'><em>Mostrando todas las {len(selected_ids)} mediciones</em></p>"
    
    fig_used = plot_correction_differences(df_diff, selected_ids, selected_ids)
    chart_html_used = fig_used.to_html(
        include_plotlyjs='cdn',
        div_id='correction_vector_used',
        config={'displayModeBar': True, 'responsive': True}
    )
    
    html += wrap_chart_in_expandable(
        chart_html_used,
        "Ver vector de corrección (mediciones usadas)",
        "correction_used_expandable",
        default_open=False
    )
    
    # GRÁFICO 2: Mediciones de validación interna (si existen)
    if len(ids_not_used) > 0:
        html += "<h3>Validación Interna - Mediciones NO Usadas</h3>"
        html += f"""
            <p style='color: #6c757d; font-size: 0.95em;'>
                <em>Mostrando {len(ids_not_used)} mediciones que <strong>NO</strong> se usaron para calcular la corrección.<br>
                Permite verificar que el vector de corrección es robusto y aplicable a mediciones independientes.</em>
            </p>
        """
        
        fig_validation = plot_correction_differences(df_diff, ids_not_used, ids_not_used)
        chart_html_validation = fig_validation.to_html(
            include_plotlyjs='cdn',
            div_id='correction_vector_validation',
            config={'displayModeBar': True, 'responsive': True}
        )
        
        html += wrap_chart_in_expandable(
            chart_html_validation,
            "Ver validación interna (mediciones NO usadas)",
            "correction_validation_expandable",
            default_open=False
        )
    else:
        html += """
            <p style='color: #17a2b8; background-color: #d1ecf1; padding: 15px; border-radius: 5px; border-left: 4px solid #17a2b8;'>
                <strong>ℹ️ Información:</strong> Todas las mediciones white standard se usaron para calcular la corrección. 
                No hay mediciones de validación interna disponibles.
            </p>
        """
    
    html += "</div>"
    
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

def _df_to_html_table(df: pd.DataFrame, float_fmt="{:.2f}", index=False) -> str:
    if df is None or df.empty:
        return "<p><em>Sin datos</em></p>"
    df_fmt = df.copy()
    for c in df_fmt.select_dtypes(include="number").columns:
        df_fmt[c] = df_fmt[c].apply(lambda x: float_fmt.format(x) if pd.notna(x) else "")
    return df_fmt.to_html(index=index, classes="table", border=0)


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

def generate_validation_section(validation_data, mean_diff_before, mean_diff_after):
    """
    Genera la sección de verificación post-ajuste (simplificada, solo estado final).
    
    Args:
        validation_data (dict): Datos de verificación
        mean_diff_before (np.array): Diferencia antes (no se usa en display)
        mean_diff_after (np.array): Diferencia después (criterio de evaluación)
        
    Returns:
        str: HTML de la sección de verificación
    """
    df_ref_val = validation_data['df_ref_val']
    df_new_val = validation_data['df_new_val']
    lamp_ref = validation_data['lamp_ref']
    lamp_new = validation_data['lamp_new']
    selected_ids = validation_data['selected_ids']
    spectral_cols = validation_data.get('spectral_cols', df_ref_val.columns.tolist())
    
    # Calcular métricas SOLO del estado final (después de corrección)
    max_diff = np.max(np.abs(mean_diff_after))
    mean_diff = np.mean(np.abs(mean_diff_after))
    rms = np.sqrt(np.mean(mean_diff_after**2))
    
    # ============================================
    # Detectar si se forzó el informe sin cumplir umbral
    # ============================================
    final_status = validation_data.get('final_status', 'SUCCESS')
    
    if final_status == 'FAILED_THRESHOLD':
        html = f"""
            <div class="warning-box" id="verification-section" style="margin-top: 30px;">
                <h2>Verificación Post-Ajuste</h2>
                <p><strong>Comprobación del ajuste de baseline con mediciones independientes:</strong></p>
            </div>
            
            <div class="info-box">
                <h2>Métricas de Verificación</h2>
                <table>
                    <tr>
                        <th>Métrica</th>
                        <th>Valor</th>
                        <th>Umbral</th>
                    </tr>
                    <tr>
                        <td><strong>RMS</strong></td>
                        <td>{rms:.6f}</td>
                        <td>⚠️ ≥ 0.002 (no cumple)</td>
                    </tr>
                    <tr>
                        <td><strong>Diferencia Máxima</strong></td>
                        <td>{max_diff:.6f}</td>
                        <td>{'⚠️ ≥ 0.01' if max_diff >= 0.01 else '✓ < 0.01'}</td>
                    </tr>
                    <tr>
                        <td><strong>Diferencia Media</strong></td>
                        <td>{mean_diff:.6f}</td>
                        <td>Referencia</td>
                    </tr>
                </table>
            </div>
            
            <div class="status-bad" style="padding: 20px; margin: 20px 0; border-radius: 5px; border: 3px solid #dc3545; background-color: #f8d7da;">
                <h2>❌ ADVERTENCIA: Informe Generado sin Cumplir Umbral</h2>
                <p style="font-size: 1.1em; margin: 10px 0;">
                    <strong>RMS:</strong> {rms:.6f} AU (Umbral recomendado: < 0.002 AU)
                </p>
                <p style="margin-top: 15px; font-weight: bold;">
                    Este informe se generó a petición del usuario aunque el alineamiento 
                    no cumple los criterios de calidad establecidos.
                </p>
                <p style="margin-top: 15px;">
                    <strong>Razones posibles:</strong>
                </p>
                <ul>
                    <li>Limitaciones del equipo que impiden alcanzar el umbral ideal</li>
                    <li>Necesidad de documentar el estado actual para trazabilidad</li>
                    <li>Decisión operativa de continuar con el alineamiento actual</li>
                </ul>
                <p style="margin-top: 15px; color: #721c24; font-weight: bold;">
                    ⚠️ RECOMENDACIÓN: Se recomienda revisar el proceso de alineamiento 
                    y considerar repetir el procedimiento en condiciones más estables.
                </p>
            </div>
        """
        
        # Gráficos de verificación (si hay datos)
        if df_ref_val is not None and df_new_val is not None and len(spectral_cols) > 0:
            html += generate_verification_charts(
                df_ref_val, df_new_val, spectral_cols,
                lamp_ref, lamp_new, selected_ids,
                mean_diff_before, mean_diff_after
            )
        
        return html  # Terminar aquí, no evaluar con criterios normales
    
    # ============================================
    # CONTINÚA CON EVALUACIÓN NORMAL
    # ============================================
    
    # Determinar estado según criterios de White Reference
    if rms < 0.002 and max_diff < 0.005:
        status_class = "status-good"
        status_text = "EXCELENTE"
        status_icon = "🟢"
        recommendation = """
            <p style="margin-top: 15px;">
                <strong>El ajuste de baseline es óptimo.</strong> Las lámparas están perfectamente alineadas 
                y el sistema está listo para uso en producción.
            </p>
        """
    elif rms < 0.005 and max_diff < 0.01:
        status_class = "status-good"
        status_text = "BUENO"
        status_icon = "🟢"
        recommendation = """
            <p style="margin-top: 15px;">
                <strong>El ajuste de baseline funciona correctamente.</strong> Las lámparas están bien alineadas 
                y el sistema puede usarse con confianza.
            </p>
        """
    elif rms < 0.01 and max_diff < 0.02:
        status_class = "status-warning"
        status_text = "ACEPTABLE"
        status_icon = "🟡"
        recommendation = """
            <p style="margin-top: 15px;">
                <strong>Corrección aceptable pero mejorable.</strong> Se recomienda:
                <ul>
                    <li>Revisar la calidad de las mediciones white standard</li>
                    <li>Verificar las condiciones ambientales durante las mediciones</li>
                    <li>Evaluar el estado de las lámparas</li>
                </ul>
            </p>
        """
    else:
        status_class = "status-bad"
        status_text = "REQUIERE REVISIÓN"
        status_icon = "🔴"
        recommendation = """
            <p style="margin-top: 15px;">
                <strong>La corrección requiere revisión.</strong> Acciones recomendadas:
                <ul>
                    <li>Verificar que el baseline corregido se instaló correctamente</li>
                    <li>Reiniciar el equipo si es necesario</li>
                    <li>Asegurar condiciones estables durante las mediciones</li>
                    <li>Considerar repetir el proceso con nuevas mediciones</li>
                </ul>
            </p>
        """
    
    html = f"""
        <div class="warning-box" id="verification-section" style="margin-top: 30px;">
            <h2>Verificación Post-Ajuste</h2>
            <p><strong>Comprobación del ajuste de baseline con mediciones independientes:</strong></p>
        </div>
        
        <div class="info-box">
            <h2>Métricas de Verificación</h2>
            <table>
                <tr>
                    <th>Métrica</th>
                    <th>Valor</th>
                    <th>Umbral</th>
                </tr>
                <tr>
                    <td><strong>RMS</strong></td>
                    <td>{rms:.6f}</td>
                    <td>{'✅ < 0.005' if rms < 0.005 else ('✓ < 0.01' if rms < 0.01 else '⚠️ ≥ 0.01')}</td>
                </tr>
                <tr>
                    <td><strong>Diferencia Máxima</strong></td>
                    <td>{max_diff:.6f}</td>
                    <td>{'✅ < 0.01' if max_diff < 0.01 else ('✓ < 0.02' if max_diff < 0.02 else '⚠️ ≥ 0.02')}</td>
                </tr>
                <tr>
                    <td><strong>Diferencia Media</strong></td>
                    <td>{mean_diff:.6f}</td>
                    <td>Referencia</td>
                </tr>
            </table>
            <p style='color: #6c757d; font-size: 0.9em; margin-top: 10px;'>
                <em>Umbrales basados en criterios de White Standard Reference.</em>
            </p>
        </div>
    """
    
    # Gráficos de verificación
    html += generate_verification_charts(
        df_ref_val, df_new_val, spectral_cols,
        lamp_ref, lamp_new, selected_ids,
        mean_diff_before, mean_diff_after
    )
    
    # Conclusión
    html += f"""
        <div class="{status_class}" style="padding: 20px; margin: 20px 0; border-radius: 5px;">
            <h2>{status_icon} Conclusión de la Verificación: {status_text}</h2>
            <p style="font-size: 1.1em; margin: 10px 0;">
                <strong>RMS:</strong> {rms:.6f} AU | <strong>Diferencia máxima:</strong> {max_diff:.6f} AU
            </p>
            {recommendation}
        </div>
    """
    
    return html