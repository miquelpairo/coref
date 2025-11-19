"""
Configuración y constantes para Baseline Adjustment Tool
"""

# Configuración de la página de Streamlit
PAGE_CONFIG = {
    "page_title": "Baseline Adjustment Tool",
    "layout": "wide"
}

# Definición de pasos del proceso (⭐ ACTUALIZADO A 5 PASOS)
STEPS = {
    1: "Datos del cliente",
    2: "Backup de archivos",
    3: "Diagnóstico Inicial",
    4: "Alineamiento de Baseline",  # ⭐ NUEVO - Fusiona antiguos pasos 4, 5 y 6
    5: "Validación"  # ⭐ Antes era paso 7
}

# Rutas de archivos baseline
BASELINE_PATHS = {
    'old_software': r"C:\ProgramData\NIR-Online\SX-Suite",
    'new_software': r"C:\ProgramData\NIR-Online\SX-Suite\Data\Reference"
}

# Extensiones de archivo soportadas
SUPPORTED_EXTENSIONS = {
    'tsv': ['tsv', 'txt', 'csv'],
    'baseline': ['ref', 'csv'],
    'ref': ['ref']
}

# Umbrales de diagnóstico para External White
WSTD_THRESHOLDS = {
    'good': 0.01,           # Bien ajustado
    'warning': 0.05,        # Desviación moderada
    'bad': float('inf')     # Requiere ajuste
}

# Estados de diagnóstico
DIAGNOSTIC_STATUS = {
    'good': {
        'icon': '🟢',
        'label': 'Bien ajustado',
        'color': 'green'
    },
    'warning': {
        'icon': '🟡',
        'label': 'Desviación moderada',
        'color': 'warning'
    },
    'bad': {
        'icon': '🔴',
        'label': 'Requiere ajuste',
        'color': 'red'
    }
}

# Metadatos por defecto para archivos CSV
DEFAULT_CSV_METADATA = {
    'expires': '',
    'sys_temp': 35.0,
    'tec_temp': 25.0,
    'lamp_time': '0:00:00',
    'count': 1,
    'vis_avg': 32000,
    'vis_max': 65535,
    'vis_int_time': 100,
    'vis_gain': 1,
    'vis_offset': 0,
    'vis_scans': 10,
    'vis_first': 0,
    'vis_pixels': 256,
    'nir_avg': 1000.0,
    'nir_max': 4095,
    'nir_int_time': 10.0,
    'nir_gain': 1.0,
    'nir_offset': 0,
    'nir_scans': 10,
    'nir_first': 0,
    'bounds': '400.0,1000.0'
}

# Identificadores especiales
SPECIAL_IDS = {
    'wstd': 'WSTD'  # White Standard ID (ya no es obligatorio)
}

# ⭐ NUEVO: Configuración de muestras de control
CONTROL_SAMPLES_CONFIG = {
    'min_samples': 1,
    'max_samples': 50,
    'prediction_tolerance': {
        'good': 0.5,      # Diferencia < 0.5% = buena reproducibilidad
        'warning': 2.0,   # Diferencia < 2% = aceptable
        'bad': float('inf')  # Diferencia > 2% = revisar
    }
}

# Configuración de gráficos
PLOT_CONFIG = {
    'figsize_default': (12, 6),
    'figsize_large': (12, 8),
    'figsize_report': (14, 7),
    'dpi': 150,
    'alpha_spectrum': 0.85,
    'alpha_grid': 0.3,
    'linewidth_default': 2,
    'linewidth_thin': 1
}

# Mensajes de instrucciones
INSTRUCTIONS = {
    'client_info': """
    Por favor, completa los siguientes datos antes de comenzar el proceso de ajuste.
    Esta información se incluirá en el informe final.
    """,
    
    'backup': """
    ### ⚠️ CRÍTICO: Backup de Archivos Baseline

    **Antes de continuar, realiza una copia de seguridad manual de los archivos baseline actuales.**

    Este procedimiento modificará los archivos de línea base del equipo NIR. Si algo sale mal, 
    necesitarás los archivos originales para restaurar la configuración.
    """,
    
    'backup_procedure': """
    ### Procedimiento para el backup:
    1. Localiza la carpeta de baseline según tu versión de software:
       - **SX Suite ≤531**: `C:\\ProgramData\\NIR-Online\\SX-Suite`
       - **SX Suite ≥557**: `C:\\ProgramData\\NIR-Online\\SX-Suite\\Data\\Reference`
    2. Copia la carpeta completa a una ubicación segura
    3. Renombra la copia con fecha (ej: `SX-Suite_Backup_2025-01-15`)
    4. Verifica que la copia se realizó correctamente
    """,
    
    'wstd': """
    ### 📊 Diagnóstico Inicial del Sensor

    **Objetivo:** Caracterizar el estado actual del sensor antes de realizar cualquier ajuste.

    **Procedimiento:**
    1. **Mide una referencia blanca** (External White) con la configuración actual del equipo
    2. **NO tomes nueva baseline** - usa la configuración actual del sensor
    3. **Asigna un ID identificable** a la medición (ej: "WHITE", "WSTD", "WhiteRef"). Usa el mismo ID en todo el proceso.
    4. **Exporta el archivo TSV** con las mediciones
    5. **Selecciona las filas correspondientes** usando los checkboxes

    **¿Qué evaluamos?**
    Las desviaciones del espectro respecto a cero nos indican la línea base actual.
    Esto sirve como referencia para alinear el sensor a la misma linea base.
    
    **IMPORTANTE:** Este archivo TSV se usará automáticamente como referencia en el Paso 4.
    """,
    
    'control_samples': """
    ### 🎯 Muestras de Control (Opcional)

    **Objetivo:** Validar que el ajuste de baseline mejora las predicciones del equipo.

    **¿Qué son muestras de control?**
    Muestras reales que medirás **antes** y **después** del ajuste para comparar 
    el impacto en las predicciones.

    **Procedimiento:**
    1. **Mide 3-10 muestras representativas** con la configuración actual
    2. **Asigna IDs únicos** a cada muestra (serán necesarios después)
    3. **Exporta el archivo TSV** - debe incluir la columna "Results" con predicciones
    4. Después del ajuste, medirás las mismas muestras para comparar

    **Requisitos del archivo:**
    - Debe contener la columna "Results" con las predicciones NIR
    - Los IDs deben ser consistentes y fáciles de identificar
    """,
    
    'kit': """
    ### 📦 Archivos para Calcular la Corrección

    **La herramienta necesita DOS archivos TSV para calcular el ajuste:**

    **Archivo 1 - Referencia (estado deseado):**
    - Mediciones del sensor en el estado que quieres replicar
    - Puede ser de un equipo de referencia, o del mismo equipo en buen estado
    - Contiene los espectros "objetivo"

    **Archivo 2 - Estado Actual (a corregir):**
    - Mediciones del sensor en su estado actual
    - Debe contener las **MISMAS muestras** que el archivo de referencia
    - Usa **EXACTAMENTE los MISMOS IDs** de muestra

    **Importante:** 
    - Los archivos se emparejan por ID de muestra
    - Cuantas más muestras uses (10-30), mejor será el ajuste
    - Las muestras deben cubrir el rango analítico de interés
    """,
    
    'baseline_load': """
    ### 📁 Cargar Baseline Actual

    **Necesitas el archivo baseline que usaste para medir el "Estado Actual" en el paso anterior.**

    **Formatos soportados:**
    - **Archivo .ref** (SX Suite ≤531) - Formato binario
    - **Archivo .csv** (SX Suite ≥557) - Formato de texto

    **Validación:** El archivo debe tener exactamente **{n_channels} canales** espectrales 
    para coincidir con tus mediciones TSV.
    
    Este baseline será corregido y podrás exportarlo en ambos formatos.
    """,
    
    'validation_control': """
    ### ✅ Validación con Muestras de Control

    **Si definiste muestras de control al inicio, ahora puedes validar el ajuste.**

    **Procedimiento:**
    1. **Aplica el nuevo baseline corregido** al equipo NIR
    2. **Mide las MISMAS muestras de control** que mediste al inicio
    3. **Usa los MISMOS IDs** para poder comparar
    4. **Exporta el archivo TSV** con las mediciones

    **Análisis automático:**
    La aplicación comparará:
    - Espectros NIR antes vs. después del ajuste
    - Predicciones antes vs. después del ajuste
    - Te mostrará si las predicciones mejoraron

    **Nota:** Este paso es opcional. Si no tienes muestras de control, puedes omitirlo.
    """
}

# Mensajes de éxito/error comunes
MESSAGES = {
    'success_file_loaded': "✅ Archivo cargado correctamente",
    'error_no_wstd': "❌ No se encontraron mediciones con ID = 'External White' en el archivo.",
    'error_no_samples': "❌ No se encontraron mediciones de muestras (todas son WSTD).",
    'error_no_common_samples': "❌ No hay muestras comunes entre los dos archivos. Verifica que uses las mismas IDs.",
    'error_dimension_mismatch': "**Error de validación:** El baseline tiene {baseline_points} puntos, pero el TSV tiene {tsv_channels} canales. No coinciden.",
    'success_dimension_match': "✅ Validación correcta: {n_points} puntos en ambos archivos",
    'success_correction_applied': "✅ Corrección aplicada al baseline",
    'warning_no_header': "⚠️ No se puede generar .ref desde CSV: faltan valores de cabecera del sensor",
    'warning_default_metadata': "⚠️ Metadatos generados por defecto",
    'info_two_files': "ℹ️ Proceso actualizado: ahora usamos dos archivos TSV separados para mayor flexibilidad",
    # ⭐ NUEVO: Mensajes para muestras de control
    'success_control_initial': "✅ Muestras de control iniciales guardadas correctamente",
    'success_control_final': "✅ Muestras de control finales guardadas correctamente",
    'error_no_predictions': "❌ El archivo no contiene la columna 'Results' con las predicciones",
    'error_no_common_control': "❌ No se encontraron muestras de control comunes entre las mediciones iniciales y finales",
    'info_control_skipped': "ℹ️ Paso de muestras de control omitido"
}

# Configuración de informes HTML
REPORT_STYLE = """
body { font-family: Arial, sans-serif; margin: 40px; }
h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
h2 { color: #34495e; margin-top: 30px; }
h3 { color: #5a6c7d; margin-top: 20px; }
.info-box { background-color: #ecf0f1; padding: 15px; border-radius: 5px; margin: 10px 0; }
.warning-box { background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #ffc107; }
.success-box { background-color: #d4edda; padding: 15px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #28a745; }
.metric { display: inline-block; margin: 10px 20px 10px 0; }
.metric-label { font-weight: bold; color: #7f8c8d; }
.metric-value { color: #2c3e50; font-size: 1.1em; }
table { border-collapse: collapse; width: 100%; margin: 20px 0; }
th, td { border: 1px solid #bdc3c7; padding: 10px; text-align: left; }
th { background-color: #3498db; color: white; }
tr:nth-child(even) { background-color: #f2f2f2; }
.status-good { color: #28a745; font-weight: bold; }
.status-warning { color: #ffc107; font-weight: bold; }
.status-bad { color: #dc3545; font-weight: bold; }
.footer { margin-top: 50px; padding-top: 20px; border-top: 1px solid #bdc3c7; text-align: center; color: #7f8c8d; font-size: 0.9em; }
.tag { display:inline-block; padding:2px 8px; border-radius:12px; font-size:0.85em; margin: 2px; }
.tag-ok { background:#e8f5e9; color:#2e7d32; border:1px solid #c8e6c9; }
.tag-no { background:#fff3e0; color:#e65100; border:1px solid #ffe0b2; }
img { max-width: 100%; height: auto; margin: 20px 0; }
"""

# Información de versión
VERSION = "3.0.0"  # ⭐ ACTUALIZADO
VERSION_DATE = "2025-01-16"  # ⭐ ACTUALIZADO
VERSION_NOTES = """
Versión 3.0.0 - Refactorización Mayor:
- ⭐ NUEVO: Proceso simplificado de 7 a 5 pasos
- ⭐ NUEVO: Paso 4 "Alineamiento de Baseline" - integra carga de baseline, TSV, corrección y exportación
- ⭐ NUEVO: TSV de referencia se arrastra automáticamente desde Paso 3
- Paso 3 (WSTD): Ahora obligatorio y genera TSV de referencia
- Arquitectura modular mejorada
- Flujo de trabajo más intuitivo y eficiente
- Mantenimiento de todas las funcionalidades previas
"""