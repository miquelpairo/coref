"""
Generador de informes HTML para Baseline Adjustment
Optimizado: sin CSS inline, usando report_utils, sidebar estandarizado
"""
import numpy as np
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Imports de módulos internos
from app_config import WSTD_THRESHOLDS
from utils.plotting import (
    plot_kit_spectra,
    plot_correction_differences,
    plot_baseline_comparison
)

# Imports de funciones compartidas
from core.report_utils import (
    wrap_chart_in_expandable,
    load_buchi_css,
    get_sidebar_styles,
    get_common_report_styles,
    build_sidebar_html,
    start_html_template,
    generate_client_info_section,
    generate_notes_section,
    generate_footer,
    df_to_html_table
)


def generate_html_report(kit_data, baseline_data, ref_corrected, origin, validation_data=None):
    """
    Genera el informe HTML completo del proceso de ajuste de baseline.
    
    Args:
        kit_data (dict): Datos del proceso (white standards)
        baseline_data (dict): Datos del baseline original
        ref_corrected (np.array): Baseline corregido
        origin (str): Tipo de archivo ('ref' o 'csv')
        validation_data (dict, optional): Datos de validación post-ajuste
        
    Returns:
        str: Contenido HTML del informe
    """
    import streamlit as st

    # Contexto de sesión
    client_data = st.session_state.get('client_data', {}) or {}
    wstd_data = st.session_state.get('wstd_data', {}) or {}

    # Extraer datos necesarios
    try:
        df = kit_data["df"]
        df_ref_grouped = kit_data["df_ref_grouped"]
        df_new_grouped = kit_data["df_new_grouped"]
        spectral_cols = kit_data["spectral_cols"]
        lamp_ref = kit_data["lamp_ref"]
        lamp_new = kit_data["lamp_new"]
        common_ids = kit_data["common_ids"]
        mean_diff = kit_data["mean_diff"]
    except Exception as e:
        raise ValueError(f"[generate_html_report] kit_data incompleto: {e}")

    try:
        ref_spectrum = baseline_data["ref_spectrum"]
        header = baseline_data.get("header")
    except Exception as e:
        raise ValueError(f"[generate_html_report] baseline_data incompleto: {e}")

    # IDs seleccionados
    selected_ids = st.session_state.get("selected_ids", list(common_ids))

    # Construir secciones del sidebar
    sections = [
        ("process-details", "Detalles del Proceso"),
        ("white-correction", "Corrección con White Standard"),
        ("correction-stats", "Estadísticas de la Corrección"),
        ("correction-vector", "Vector de Corrección"),
        ("baseline-info", "Baseline Generado"),
    ]
    
    # Añadir WSTD al inicio si existe
    if isinstance(wstd_data, dict) and wstd_data.get("df") is not None:
        sections.insert(0, ("wstd-section", "Diagnóstico WSTD Inicial"))
    
    # Añadir validación al sidebar si existe
    if validation_data is not None:
        sections.append(("verification-section", "Verificación Post-Ajuste"))

    # Iniciar HTML con template estandarizado
    html = start_html_template(
        title="Informe de Ajuste de Baseline NIR",
        sidebar_sections=sections,
        client_info=client_data
    )

    # Secciones del informe
    
    # WSTD inicial (si existe)
    if isinstance(wstd_data, dict) and wstd_data.get("df") is not None:
        html += generate_wstd_section(wstd_data)

    # Detalles del proceso
    html += generate_process_details(
        lamp_ref, lamp_new, len(spectral_cols),
        len(common_ids), origin, selected_ids
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

    # Añadir validación ANTES del footer si existe
    if validation_data is not None:
        html += generate_validation_section(
            validation_data,
            mean_diff_before=mean_diff,
            mean_diff_after=validation_data['diff']
        )

    # Notas adicionales (si existen)
    if client_data.get("notes"):
        html += generate_notes_section(client_data["notes"])

    # Footer
    html += generate_footer()

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
    
    # Iterar sobre cada medición
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
            <p class="table-footnote">
            <em>Nota: Las mediciones del White Standard sin línea base deben estar cercanas a 0 
            en todo el espectro si el sistema está bien calibrado. Estas métricas muestran 
            la desviación respecto al valor ideal (0).</em>
            </p>
        </div>
    """
    
    # Añadir gráficos
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
    
    # Línea de referencia en y=0
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
    
    # Envolver en expandible
    html += wrap_chart_in_expandable(
        chart_html,
        "Ver gráficos de diagnóstico WSTD",
        "wstd_charts_expandable",
        default_open=False
    )
    
    return html


def generate_process_details(lamp_ref, lamp_new, n_spectral, n_samples, origin, selected_ids):
    """
    Genera la sección de detalles del proceso.
    
    Args:
        lamp_ref (str): Lámpara de referencia
        lamp_new (str): Lámpara nueva
        n_spectral (int): Número de canales espectrales
        n_samples (int): Número de mediciones white standard
        origin (str): Tipo de archivo
        selected_ids (list): IDs seleccionados
        
    Returns:
        str: HTML de detalles
    """
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
                    <td>{len(selected_ids)}</td>
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
    html = """
        <div class="info-box" id="white-correction">
            <h2>Corrección con White Standard</h2>
            <h3>Mediciones White Standard Usadas en la Corrección</h3>
            <p class="text-caption">
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
            <table class="table-margin-top">
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
    """
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
            <p class="text-caption">
                <em>El vector de corrección representa el ajuste espectral calculado a partir de las 
                diferencias entre las mediciones white standard con baseline original y baseline nueva.</em>
            </p>
    """
    
    # GRÁFICO 1: Mediciones usadas
    html += "<h3>Diferencias Espectrales - Mediciones Usadas</h3>"
    
    if len(selected_ids) < len(common_ids):
        html += f"<p class='text-caption'><em>Mostrando {len(selected_ids)} de {len(common_ids)} mediciones (usadas en el cálculo)</em></p>"
    else:
        html += f"<p class='text-caption'><em>Mostrando todas las {len(selected_ids)} mediciones</em></p>"
    
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
    
    # GRÁFICO 2: Validación interna (si existen)
    if len(ids_not_used) > 0:
        html += "<h3>Validación Interna - Mediciones NO Usadas</h3>"
        html += f"""
            <p class='text-caption'>
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
            <p class="info-highlight">
                <strong>ℹ️ Información:</strong> Todas las mediciones white standard se usaron para calcular la corrección. 
                No hay mediciones de validación interna disponibles.
            </p>
        """
    
    html += "</div>"
    
    return html


def generate_baseline_info(ref_corrected, header, origin, ref_spectrum, spectral_cols):
    """
    Genera la sección de información del baseline generado con gráfico comparativo.
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
            
            <h3 class="metrics-section">Comparación: Baseline Original vs Corregido</h3>
            <p class="text-caption">
                <em>Visualización del baseline antes y después de aplicar la corrección calculada.</em>
            </p>
    """
    
    fig = plot_baseline_comparison(ref_spectrum, ref_corrected, spectral_cols)
    
    chart_html = fig.to_html(
        include_plotlyjs='cdn',
        div_id='baseline_comparison_chart',
        config={'displayModeBar': True, 'responsive': True}
    )
    
    html += wrap_chart_in_expandable(
        chart_html,
        "Ver comparación de baseline (Original vs Corregido)",
        "baseline_comparison_expandable",
        default_open=False
    )
    
    html += "</div>"
    
    return html


def generate_validation_section(validation_data, mean_diff_before, mean_diff_after):
    """
    Genera la sección de verificación post-ajuste.
    """
    df_ref_val = validation_data['df_ref_val']
    df_new_val = validation_data['df_new_val']
    lamp_ref = validation_data['lamp_ref']
    lamp_new = validation_data['lamp_new']
    selected_ids = validation_data['selected_ids']
    spectral_cols = validation_data.get('spectral_cols', df_ref_val.columns.tolist())
    
    # Métricas del estado final
    max_diff = np.max(np.abs(mean_diff_after))
    mean_diff = np.mean(np.abs(mean_diff_after))
    rms = np.sqrt(np.mean(mean_diff_after**2))
    
    # Detectar si se forzó el informe
    final_status = validation_data.get('final_status', 'SUCCESS')
    
    if final_status == 'FAILED_THRESHOLD':
        html = f"""
            <div class="warning-box verification-title" id="verification-section">
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
                        <td>⚠️ ≥ 0.005 (no cumple)</td>
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
            
            <div class="status-bad verification-status status-failed">
                <h2>❌ ADVERTENCIA: Informe Generado sin Cumplir Umbral</h2>
                <p class="text-spacious">
                    <strong>RMS:</strong> {rms:.6f} AU (Umbral recomendado: < 0.005 AU)
                </p>
                <p class="text-muted-note">
                    Este informe se generó a petición del usuario aunque el alineamiento 
                    no cumple los criterios de calidad establecidos.
                </p>
                <p class="text-muted-note">
                    <strong>Razones posibles:</strong>
                </p>
                <ul class="list-spacious">
                    <li>Limitaciones del equipo que impiden alcanzar el umbral ideal</li>
                    <li>Necesidad de documentar el estado actual para trazabilidad</li>
                    <li>Decisión operativa de continuar con el alineamiento actual</li>
                </ul>
                <p class="text-muted-note">
                    ⚠️ RECOMENDACIÓN: Se recomienda revisar el proceso de alineamiento 
                    y considerar repetir el procedimiento en condiciones más estables.
                </p>
            </div>
        """
        
        # Añadir gráficos
        html += generate_verification_charts(
            df_ref_val, df_new_val, spectral_cols,
            lamp_ref, lamp_new, selected_ids,
            mean_diff_before, mean_diff_after
        )
        
        return html
    
    # Evaluación normal
    if rms < 0.002 and max_diff < 0.005:
        status_class = "status-good"
        status_text = "EXCELENTE"
        status_icon = "🟢"
        recommendation = """
            <p class="text-muted-note">
                <strong>El ajuste de baseline es óptimo.</strong> Las lámparas están perfectamente alineadas 
                y el sistema está listo para uso en producción.
            </p>
        """
    elif rms < 0.005 and max_diff < 0.01:
        status_class = "status-good"
        status_text = "BUENO"
        status_icon = "🟢"
        recommendation = """
            <p class="text-muted-note">
                <strong>El ajuste de baseline funciona correctamente.</strong> Las lámparas están bien alineadas 
                y el sistema puede usarse con confianza.
            </p>
        """
    elif rms < 0.01 and max_diff < 0.02:
        status_class = "status-warning"
        status_text = "ACEPTABLE"
        status_icon = "🟡"
        recommendation = """
            <p class="text-muted-note">
                <strong>Corrección aceptable pero mejorable.</strong> Se recomienda:
                <ul class="list-spacious">
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
            <p class="text-muted-note">
                <strong>La corrección requiere revisión.</strong> Acciones recomendadas:
                <ul class="list-spacious">
                    <li>Verificar que el baseline corregido se instaló correctamente</li>
                    <li>Reiniciar el equipo si es necesario</li>
                    <li>Asegurar condiciones estables durante las mediciones</li>
                    <li>Considerar repetir el proceso con nuevas mediciones</li>
                </ul>
            </p>
        """
    
    html = f"""
        <div class="warning-box verification-title" id="verification-section">
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
            <p class="table-footnote">
                <em>Umbrales basados en criterios de White Standard Reference.</em>
            </p>
        </div>
    """
    
    # Gráficos
    html += generate_verification_charts(
        df_ref_val, df_new_val, spectral_cols,
        lamp_ref, lamp_new, selected_ids,
        mean_diff_before, mean_diff_after
    )
    
    # Conclusión
    html += f"""
        <div class="{status_class} verification-status">
            <h2>{status_icon} Conclusión de la Verificación: {status_text}</h2>
            <p class="text-spacious">
                <strong>RMS:</strong> {rms:.6f} AU | <strong>Diferencia máxima:</strong> {max_diff:.6f} AU
            </p>
            {recommendation}
        </div>
    """
    
    return html


def generate_verification_charts(df_ref_val, df_new_val, spectral_cols,
                                 lamp_ref, lamp_new, selected_ids,
                                 mean_diff_before, mean_diff_after):
    """
    Genera los gráficos de verificación post-ajuste.
    """
    html = "<h2>Análisis de Verificación</h2>"
    
    # Preparar datos
    spectra_ref = []
    spectra_new = []
    labels = []
    
    for sid in selected_ids:
        if sid in df_ref_val.index and sid in df_new_val.index:
            spectra_ref.append(df_ref_val.loc[sid, spectral_cols].values)
            spectra_new.append(df_new_val.loc[sid, spectral_cols].values)
            labels.append(f"{sid}")
    
    channels = list(range(1, len(spectral_cols) + 1))
    
    # TAB 1: OVERLAY
    html += "<h3>1) Overlay de Espectros</h3>"
    html += "<p class='text-caption'><em>Comparación visual de todas las mediciones de verificación.</em></p>"
    
    fig_overlay = go.Figure()
    
    colors_ref = ['#1f77b4', '#2ca02c', '#9467bd', '#8c564b', '#e377c2']
    colors_new = ['#ff7f0e', '#d62728', '#bcbd22', '#7f7f7f', '#17becf']
    
    for i, (spec_ref, spec_new, label) in enumerate(zip(spectra_ref, spectra_new, labels)):
        fig_overlay.add_trace(go.Scatter(
            x=channels,
            y=spec_ref,
            mode='lines',
            name=f"{lamp_ref} - {label}",
            line=dict(color=colors_ref[i % len(colors_ref)], width=2),
            hovertemplate=f'<b>{lamp_ref} - {label}</b><br>Canal: %{{x}}<br>Valor: %{{y:.6f}}<extra></extra>'
        ))
        
        fig_overlay.add_trace(go.Scatter(
            x=channels,
            y=spec_new,
            mode='lines',
            name=f"{lamp_new} - {label}",
            line=dict(color=colors_new[i % len(colors_new)], width=2, dash='dash'),
            hovertemplate=f'<b>{lamp_new} - {label}</b><br>Canal: %{{x}}<br>Valor: %{{y:.6f}}<extra></extra>'
        ))
    
    fig_overlay.update_layout(
        title='Mediciones White Standard Post-Ajuste',
        xaxis_title='Canal espectral',
        yaxis_title='Absorbancia',
        height=600,
        hovermode='closest',
        template='plotly_white',
        legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5)
    )
    
    chart_html_overlay = fig_overlay.to_html(
        include_plotlyjs='cdn',
        div_id='verification_overlay',
        config={'displayModeBar': True, 'responsive': True}
    )
    
    html += wrap_chart_in_expandable(
        chart_html_overlay,
        "Ver overlay de espectros",
        "verification_overlay_expandable",
        default_open=False
    )
    
    # TAB 2: RESIDUALES
    html += "<h3>2) Análisis de Residuales</h3>"
    html += "<p class='text-caption'><em>Diferencias punto a punto entre lámparas.</em></p>"
    
    fig_residuals = go.Figure()
    
    for i, (spec_ref, spec_new, label) in enumerate(zip(spectra_ref, spectra_new, labels)):
        residual = spec_new - spec_ref
        
        fig_residuals.add_trace(go.Scatter(
            x=channels,
            y=residual,
            mode='lines',
            name=label,
            line=dict(width=2),
            hovertemplate=f'<b>{label}</b><br>Canal: %{{x}}<br>Δ: %{{y:.6f}}<extra></extra>'
        ))
    
    fig_residuals.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    fig_residuals.update_layout(
        title='Residuales (Nueva - Referencia)',
        xaxis_title='Canal espectral',
        yaxis_title='Residual (AU)',
        height=600,
        hovermode='closest',
        template='plotly_white',
        legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5)
    )
    
    chart_html_residuals = fig_residuals.to_html(
        include_plotlyjs='cdn',
        div_id='verification_residuals',
        config={'displayModeBar': True, 'responsive': True}
    )
    
    html += wrap_chart_in_expandable(
        chart_html_residuals,
        "Ver análisis de residuales",
        "verification_residuals_expandable",
        default_open=False
    )
    
    # Tabla de estadísticas
    html += "<h4>Estadísticas de Residuales</h4>"
    residual_stats = []
    
    for spec_ref, spec_new, label in zip(spectra_ref, spectra_new, labels):
        residual = spec_new - spec_ref
        rms = np.sqrt(np.mean(residual**2))
        max_diff = np.abs(residual).max()
        
        if rms < 0.002 and max_diff < 0.005:
            evaluacion = "✅ Excelente"
        elif rms < 0.005 and max_diff < 0.01:
            evaluacion = "✓ Bueno"
        elif rms < 0.01 and max_diff < 0.02:
            evaluacion = "⚠️ Aceptable"
        else:
            evaluacion = "❌ Revisar"
        
        residual_stats.append({
            'Muestra': label,
            'RMS': f"{rms:.6f}",
            'Max |Δ|': f"{max_diff:.6f}",
            'Media Δ': f"{np.mean(residual):.6f}",
            'Desv. Est.': f"{np.std(residual):.6f}",
            'Evaluación': evaluacion
        })
    
    residual_df = pd.DataFrame(residual_stats)
    html += df_to_html_table(residual_df, index=False)
    
    # TAB 3: ESTADÍSTICAS
    html += "<h3>3) Estadísticas Espectrales</h3>"
    
    stats = []
    for spec_ref, spec_new, label in zip(spectra_ref, spectra_new, labels):
        stats.append({
            'Muestra': f"{label} - {lamp_ref}",
            'Min': f"{spec_ref.min():.6f}",
            'Max': f"{spec_ref.max():.6f}",
            'Media': f"{spec_ref.mean():.6f}",
            'Desv. Est.': f"{spec_ref.std():.6f}",
            'Rango': f"{spec_ref.max() - spec_ref.min():.6f}"
        })
        stats.append({
            'Muestra': f"{label} - {lamp_new}",
            'Min': f"{spec_new.min():.6f}",
            'Max': f"{spec_new.max():.6f}",
            'Media': f"{spec_new.mean():.6f}",
            'Desv. Est.': f"{spec_new.std():.6f}",
            'Rango': f"{spec_new.max() - spec_new.min():.6f}"
        })
    
    stats_df = pd.DataFrame(stats)
    stats_html = df_to_html_table(stats_df, index=False)
    
    html += wrap_chart_in_expandable(
        stats_html,
        "Ver estadísticas espectrales completas",
        "verification_stats_expandable",
        default_open=False
    )
    
    # TAB 4: MATRIZ RMS
    html += "<h3>4) Matriz de Diferencias RMS</h3>"
    html += "<p class='text-caption'><em>Escala absoluta basada en umbrales de white standards.</em></p>"
    
    # Combinar espectros
    all_spectra = []
    all_labels = []
    for spec_ref, spec_new, label in zip(spectra_ref, spectra_new, labels):
        all_spectra.append(spec_ref)
        all_labels.append(f"{label} - {lamp_ref}")
        all_spectra.append(spec_new)
        all_labels.append(f"{label} - {lamp_new}")
    
    # Calcular matriz
    n_spectra = len(all_spectra)
    rms_matrix = np.zeros((n_spectra, n_spectra))
    
    for i in range(n_spectra):
        for j in range(n_spectra):
            if i == j:
                rms_matrix[i, j] = 0
            else:
                diff = all_spectra[i] - all_spectra[j]
                rms_matrix[i, j] = np.sqrt(np.mean(diff**2))
    
    # Heatmap
    colorscale = [
        [0.0, '#4caf50'],
        [0.333, '#8bc34a'],
        [0.667, '#ffc107'],
        [1.0, '#f44336']
    ]
    
    fig_heatmap = go.Figure(data=go.Heatmap(
        z=rms_matrix,
        x=all_labels,
        y=all_labels,
        colorscale=colorscale,
        zmin=0,
        zmax=0.015,
        text=np.round(rms_matrix, 6),
        texttemplate='%{text}',
        textfont={"size": 10},
        colorbar=dict(
            title="RMS (AU)",
            tickvals=[0, 0.002, 0.005, 0.01, 0.015],
            ticktext=['0.000', '0.002<br>(Exc)', '0.005<br>(Bueno)', '0.010<br>(Acept)', '0.015']
        )
    ))
    
    fig_heatmap.update_layout(
        title='Matriz de Diferencias RMS - Escala Absoluta',
        height=max(400, 50 * n_spectra),
        template='plotly_white'
    )
    
    chart_html_heatmap = fig_heatmap.to_html(
        include_plotlyjs='cdn',
        div_id='verification_heatmap',
        config={'displayModeBar': True, 'responsive': True}
    )
    
    html += wrap_chart_in_expandable(
        chart_html_heatmap,
        "Ver matriz RMS",
        "verification_heatmap_expandable",
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
    """
    Genera informe parcial con las secciones disponibles.
    
    Returns:
        str: HTML del informe parcial
    """
    import streamlit as st

    client_data = st.session_state.get('client_data', {})
    wstd_data = st.session_state.get('wstd_data')

    # Construir secciones disponibles
    sections = []
    
    # WSTD si existe
    if isinstance(wstd_data, dict) and wstd_data.get('df') is not None:
        sections.append(("wstd-section", "Diagnóstico WSTD Inicial"))
    
    # Verificación si hay datos
    has_verification = (
        validation_data is not None
        and mean_diff_before is not None
        and mean_diff_after is not None
    )
    if has_verification:
        sections.append(("verification-section", "Verificación Post-Ajuste"))

    # Iniciar HTML
    html = start_html_template(
        title="Informe de Ajuste de Baseline NIR",
        sidebar_sections=sections,
        client_info=client_data
    )

    # WSTD inicial (si existe)
    if isinstance(wstd_data, dict) and wstd_data.get('df') is not None:
        try:
            html += generate_wstd_section(wstd_data)
        except Exception as e:
            html += f"""
                <div class="warning-box" id="wstd-section">
                    <h2>Diagnóstico WSTD Inicial</h2>
                    <p><em>No se pudo renderizar la sección WSTD: {e}</em></p>
                </div>
            """

    # Si NO hay baseline/kit completos, avisa
    if not (kit_data and baseline_data and ref_corrected and origin):
        html += """
            <div class="warning-box">
                <h2>Proceso Incompleto</h2>
                <p><em>No hay datos suficientes para generar el informe completo. 
                Complete el proceso de ajuste de baseline.</em></p>
            </div>
        """

    # Verificación (si hay datos)
    if has_verification:
        try:
            html += generate_validation_section(validation_data, mean_diff_before, mean_diff_after)
        except Exception as e:
            html += f"""
                <div class="warning-box verification-title" id="verification-section">
                    <h2>Verificación Post-Ajuste</h2>
                    <p><em>No se pudo renderizar la verificación: {e}</em></p>
                </div>
            """

    html += generate_footer()
    return html