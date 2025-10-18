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


def generate_html_report(kit_data, baseline_data, ref_corrected, origin):
    """
    Genera un informe HTML completo del proceso de ajuste.
    
    Args:
        kit_data (dict): Datos del Standard Kit
        baseline_data (dict): Datos del baseline
        ref_corrected (np.array): Baseline corregido
        origin (str): Tipo de archivo ('ref' o 'csv')
        
    Returns:
        str: Contenido HTML del informe
    """
    import streamlit as st
    
    client_data = st.session_state.client_data or {}
    wstd_data = st.session_state.wstd_data or {}
    
    # Extraer datos necesarios
    df = kit_data['df']
    df_ref_grouped = kit_data['df_ref_grouped']
    df_new_grouped = kit_data['df_new_grouped']
    spectral_cols = kit_data['spectral_cols']
    lamp_ref = kit_data['lamp_ref']
    lamp_new = kit_data['lamp_new']
    common_ids = kit_data['common_ids']
    mean_diff = kit_data['mean_diff']
    
    ref_spectrum = baseline_data['ref_spectrum']
    header = baseline_data.get('header')
    
    # Iniciar HTML
    html = start_html_document(client_data)
    
    # Agregar diagnóstico WSTD si existe
    if wstd_data and 'grouped' in wstd_data:
        html += generate_wstd_section(wstd_data)
    
    # Detalles del proceso
    html += generate_process_details(
        lamp_ref, lamp_new, len(spectral_cols), 
        len(common_ids), origin
    )
    
    # Tabla de muestras
    html += generate_samples_table(df, common_ids, lamp_ref, lamp_new)
    
    # Estadísticas de corrección
    html += generate_correction_statistics(mean_diff)
    
    # Información del baseline generado
    html += generate_baseline_info(ref_corrected, header, origin)
    
    # Notas adicionales
    if client_data.get('notes'):
        html += generate_notes_section(client_data['notes'])
    
    # Gráficos
    html += generate_charts_section(
        df, df_ref_grouped, spectral_cols,
        lamp_ref, lamp_new, common_ids,
        ref_spectrum, ref_corrected
    )
    
    # Footer
    html += generate_footer()
    
    return html


def start_html_document(client_data):
    """
    Inicia el documento HTML con información del cliente.
    
    Args:
        client_data (dict): Datos del cliente
        
    Returns:
        str: HTML inicial
    """
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            {REPORT_STYLE}
        </style>
    </head>
    <body>
        <h1>📊 Informe de Ajuste de Baseline NIR</h1>

        <div class="info-box">
            <h2>👤 Información del Cliente</h2>
            <div class="metric">
                <span class="metric-label">Cliente:</span>
                <span class="metric-value">{client_data.get('client_name', 'N/A')}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Contacto:</span>
                <span class="metric-value">{client_data.get('contact_person', 'N/A')}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Email:</span>
                <span class="metric-value">{client_data.get('contact_email', 'N/A')}</span>
            </div>
            <br>
            <div class="metric">
                <span class="metric-label">N/S Sensor:</span>
                <span class="metric-value">{client_data.get('sensor_sn', 'N/A')}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Modelo:</span>
                <span class="metric-value">{client_data.get('equipment_model', 'N/A')}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Ubicación:</span>
                <span class="metric-value">{client_data.get('location', 'N/A')}</span>
            </div>
            <br>
            <div class="metric">
                <span class="metric-label">Fecha del Proceso:</span>
                <span class="metric-value">{client_data.get('date', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}</span>
            </div>
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
    df_wstd_grouped = wstd_data['grouped']
    
    html = """
        <div class="warning-box">
            <h2>🔍 Diagnóstico Inicial - White Standard (sin línea base)</h2>
            <p><strong>Estado del sistema ANTES del ajuste:</strong></p>
            <table>
                <tr>
                    <th>Lámpara</th>
                    <th>Desv. Máxima</th>
                    <th>Desv. Media</th>
                    <th>Desv. Estándar</th>
                    <th>Estado</th>
                </tr>
    """
    
    for lamp in df_wstd_grouped.index:
        spectrum = df_wstd_grouped.loc[lamp].values
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
                <td><strong>{lamp}</strong></td>
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
        <div class="info-box">
            <h2>🔬 Detalles del Proceso</h2>
            <div class="metric">
                <span class="metric-label">Lámpara de Referencia:</span>
                <span class="metric-value">{lamp_ref}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Lámpara Nueva:</span>
                <span class="metric-value">{lamp_new}</span>
            </div>
            <br>
            <div class="metric">
                <span class="metric-label">Canales Espectrales:</span>
                <span class="metric-value">{n_spectral}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Muestras Comunes:</span>
                <span class="metric-value">{n_samples}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Muestras usadas en corrección:</span>
                <span class="metric-value">{len(used_ids)}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Formato Baseline:</span>
                <span class="metric-value">.{origin}</span>
            </div>
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
    
    html = """
        <h2>📦 Muestras del Standard Kit</h2>
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
        
        html += f"""
            <tr>
                <td>{id_}</td>
                <td>{count_ref}</td>
                <td>{count_new}</td>
                <td>{used_tag}</td>
            </tr>
        """
    
    html += "</table>"
    return html


def generate_correction_statistics(mean_diff):
    """
    Genera la sección de estadísticas de corrección.
    
    Args:
        mean_diff (np.array): Vector de corrección
        
    Returns:
        str: HTML de estadísticas
    """
    html = f"""
        <div class="info-box">
            <h2>📈 Estadísticas de la Corrección</h2>
            <div class="metric">
                <span class="metric-label">Corrección Máxima:</span>
                <span class="metric-value">{np.max(np.abs(mean_diff)):.6f}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Corrección Media:</span>
                <span class="metric-value">{np.mean(np.abs
  <span class="metric-value">{np.mean(np.abs(mean_diff)):.6f}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Desviación Estándar:</span>
                <span class="metric-value">{np.std(mean_diff):.6f}</span>
            </div>
        </div>
    """
    return html


def generate_baseline_info(ref_corrected, header, origin):
    """
    Genera la sección de información del baseline generado.
    
    Args:
        ref_corrected (np.array): Baseline corregido
        header (np.array): Cabecera del .ref
        origin (str): Tipo de archivo
        
    Returns:
        str: HTML de información del baseline
    """
    html = f"""
        <div class="info-box">
            <h2>📊 Baseline Generado</h2>
            <div class="metric">
                <span class="metric-label">Puntos Espectrales:</span>
                <span class="metric-value">{len(ref_corrected)}</span>
            </div>
    """
    
    if origin == 'ref' and header is not None:
        html += f"""
            <div class="metric">
                <span class="metric-label">Cabecera X1:</span>
                <span class="metric-value">{header[0]:.6e}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Cabecera X2:</span>
                <span class="metric-value">{header[1]:.6e}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Cabecera X3:</span>
                <span class="metric-value">{header[2]:.6e}</span>
            </div>
        """
    
    html += f"""
            <br>
            <div class="metric">
                <span class="metric-label">Valor Mínimo:</span>
                <span class="metric-value">{np.min(ref_corrected):.6f}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Valor Máximo:</span>
                <span class="metric-value">{np.max(ref_corrected):.6f}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Valor Medio:</span>
                <span class="metric-value">{np.mean(ref_corrected):.6f}</span>
            </div>
        </div>
    """
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


def generate_charts_section(df, df_ref_grouped, spectral_cols,
                           lamp_ref, lamp_new, common_ids,
                           ref_spectrum, ref_corrected):
    """
    Genera la sección de gráficos del informe.
    
    Args:
        df (pd.DataFrame): DataFrame completo
        df_ref_grouped (pd.DataFrame): Mediciones de referencia
        spectral_cols (list): Columnas espectrales
        lamp_ref (str): Lámpara de referencia
        lamp_new (str): Lámpara nueva
        common_ids (list): IDs comunes
        ref_spectrum (np.array): Baseline original
        ref_corrected (np.array): Baseline corregido
        
    Returns:
        str: HTML de la sección de gráficos
    """
    import streamlit as st
    
    # Simular espectros corregidos
    df_new_corr = simulate_corrected_spectra(
        df, spectral_cols, lamp_new,
        ref_spectrum, ref_corrected
    )
    
    used_ids = st.session_state.get('selected_ids', list(common_ids))
    other_ids = [i for i in common_ids if i not in used_ids]
    
    html = "<h2>📊 Resultados gráficos</h2>"
    
    # Gráfico de muestras usadas
    html += "<h3>✅ Muestras usadas en la corrección</h3>"
    img_used = create_comparison_chart_image(
        df_ref_grouped, df_new_corr, spectral_cols,
        lamp_ref, lamp_new, used_ids,
        "Resultado (usadas para corrección): Referencia vs Nueva corregida"
    )
    html += f'<img src="data:image/png;base64,{img_used}" style="width:100%; max-width:1000px;">'
    
    # Gráfico de muestras no usadas (si existen)
    if len(other_ids) > 0:
        html += "<h3>🔎 Muestras de validación (no usadas)</h3>"
        img_val = create_comparison_chart_image(
            df_ref_grouped, df_new_corr, spectral_cols,
            lamp_ref, lamp_new, other_ids,
            "Resultado (validación): Referencia vs Nueva corregida"
        )
        html += f'<img src="data:image/png;base64,{img_val}" style="width:100%; max-width:1000px;">'
    
    return html


def create_comparison_chart_image(df_ref_grouped, df_corrected, spectral_cols,
                                  lamp_ref, lamp_new, sample_ids, title):
    """
    Crea una imagen base64 del gráfico de comparación.
    
    Args:
        df_ref_grouped (pd.DataFrame): Espectros de referencia
        df_corrected (pd.DataFrame): Espectros corregidos
        spectral_cols (list): Columnas espectrales
        lamp_ref (str): Lámpara de referencia
        lamp_new (str): Lámpara nueva
        sample_ids (list): IDs de muestras
        title (str): Título del gráfico
        
    Returns:
        str: Imagen codificada en base64
    """
    fig = plot_corrected_spectra_comparison(
        df_ref_grouped, df_corrected, spectral_cols,
        lamp_ref, lamp_new, sample_ids, title
    )
    
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    
    return img_base64


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
