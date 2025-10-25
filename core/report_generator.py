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


def generate_html_report(kit_data, baseline_data, ref_corrected, origin):
    """Genera un informe HTML completo del proceso de ajuste."""
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
    
    # Obtener selected_ids
    selected_ids = st.session_state.get('selected_ids', list(common_ids))
    
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
    
    # Gráficos ← AQUÍ ESTÁ EL ERROR
    html += generate_charts_section(
        df,                 # 1
        df_ref_grouped,     # 2
        spectral_cols,      # 3
        lamp_ref,           # 4
        lamp_new,           # 5
        common_ids,         # 6
        selected_ids,       # 7 ← ESTE ESTABA FALTANDO
        ref_spectrum,       # 8
        ref_corrected       # 9
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
                <span class="metric-label">Técnico:</span>
                <span class="metric-value">{client_data.get('technician', 'N/A')}</span>
            </div>
            <br>
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
    max_corr = np.max(np.abs(mean_diff))
    mean_corr = np.mean(np.abs(mean_diff))
    std_corr = np.std(mean_diff)
    
    html = f"""
        <div class="info-box">
            <h2>📈 Estadísticas de la Corrección</h2>
            <div class="metric">
                <span class="metric-label">Corrección Máxima:</span>
                <span class="metric-value">{max_corr:.6f}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Corrección Media:</span>
                <span class="metric-value">{mean_corr:.6f}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Desviación Estándar:</span>
                <span class="metric-value">{std_corr:.6f}</span>
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


def generate_charts_section(df, df_ref_grouped, spectral_cols,
                           lamp_ref, lamp_new, common_ids, selected_ids,
                           ref_spectrum, ref_corrected):
    """
    Genera la sección de gráficos del informe.
    
    Args:
        df (pd.DataFrame): DataFrame completo
        df_ref_grouped (pd.DataFrame): Espectros de referencia
        spectral_cols (list): Columnas espectrales
        lamp_ref (str): Nombre lámpara referencia
        lamp_new (str): Nombre lámpara nueva
        common_ids (list): IDs comunes
        selected_ids (list): IDs seleccionados para corrección  ← NUEVO
        ref_spectrum (np.array): Baseline original
        ref_corrected (np.array): Baseline corregido
        
    Returns:
        str: HTML de la sección de gráficos
    """
    import streamlit as st
    
    # Agrupar DataFrame por ID para obtener df_new_grouped
    df_new_grouped = df.groupby("ID")[spectral_cols].mean()
    
    # Simular espectros corregidos
    df_new_corr = simulate_corrected_spectra(
        df_new_grouped,
        spectral_cols, 
        ref_spectrum, 
        ref_corrected
    )
    
    # Obtener muestras usadas y no usadas
    used_ids = st.session_state.get('selected_ids', list(common_ids))
    other_ids = [i for i in common_ids if i not in used_ids]
    
    html = "<h2>📊 Resultados gráficos</h2>"
    
    # Gráfico de muestras usadas
    html += "<h3>✅ Muestras usadas en la corrección</h3>"
    fig_used = plot_corrected_spectra_comparison(
        df_ref_grouped, df_new_corr, spectral_cols,
        lamp_ref, lamp_new, used_ids,
        "Resultado (usadas para corrección): Referencia vs Nueva corregida"
    )
    # Convertir a HTML interactivo
    html += fig_used.to_html(include_plotlyjs='cdn', div_id='chart_used')
    
    # Gráfico de muestras no usadas (si existen)
    if len(other_ids) > 0:
        html += "<h3>🔎 Muestras de validación (no usadas)</h3>"
        fig_val = plot_corrected_spectra_comparison(
            df_ref_grouped, df_new_corr, spectral_cols,
            lamp_ref, lamp_new, other_ids,
            "Resultado (validación): Referencia vs Nueva corregida"
        )
        html += fig_val.to_html(include_plotlyjs='cdn', div_id='chart_validation')
    
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
        <div class="warning-box" style="margin-top: 30px;">
            <h2>✅ Validacion Post-Correccion</h2>
            <p><strong>Verificacion del ajuste con mediciones reales:</strong></p>
        </div>
        
        <div class="info-box">
            <h2>📋 Detalles de la Validacion</h2>
            <div class="metric">
                <span class="metric-label">Lampara de Referencia:</span>
                <span class="metric-value">{lamp_ref}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Lampara Nueva:</span>
                <span class="metric-value">{lamp_new}</span>
            </div>
            <br>
            <div class="metric">
                <span class="metric-label">Muestras medidas:</span>
                <span class="metric-value">{len(common_ids)}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Muestras usadas en validacion:</span>
                <span class="metric-value">{len(selected_ids)}</span>
            </div>
        </div>
        
        <div class="info-box">
            <h2>📊 Resultados de la Validacion</h2>
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
            ✅ <strong>El ajuste de baseline es optimo.</strong> Las lamparas estan perfectamente alineadas 
            y el sistema esta listo para uso en produccion.
            </p>
        """
    elif max_after < 0.01:
        html += """
            <p style="margin-top: 15px;">
            ✅ <strong>El ajuste de baseline funciona correctamente.</strong> Las lamparas estan bien alineadas 
            y el sistema puede usarse con confianza.
            </p>
        """
    elif improvement_mean > 50:
        html += """
            <p style="margin-top: 15px;">
            ⚠️ <strong>Correccion aceptable pero mejorable.</strong> Se recomienda:
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
            🔴 <strong>La correccion requiere revision.</strong> Acciones recomendadas:
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
        
        <h2>📦 Muestras de Validacion</h2>
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
    
    html = "<h2>📊 Graficos de Validacion</h2>"
    
    # Grafico 1: Espectros de validacion
    html += "<h3>Espectros de las muestras de validacion</h3>"
    html += "<p style='color: #6c757d; font-size: 0.95em;'><em>Comparacion de espectros medidos con ambas lamparas despues de aplicar la correccion.</em></p>"
    
    fig_spectra = plot_kit_spectra(
        df_ref_val, df_new_val, spectral_cols,
        lamp_ref, lamp_new, selected_ids
    )
    
    html += fig_spectra.to_html(
        include_plotlyjs='cdn',
        div_id='validation_spectra',
        config={'displayModeBar': True, 'responsive': True}
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
    
    html += fig_comparison.to_html(
        include_plotlyjs='cdn',
        div_id='validation_comparison',
        config={'displayModeBar': True, 'responsive': True}
    )
    
    return html