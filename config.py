"""
Configuración y constantes para Baseline Adjustment Tool
"""

# Configuración de la página de Streamlit
PAGE_CONFIG = {
    "page_title": "Baseline Adjustment Tool",
    "layout": "wide"
}

# Definición de pasos del proceso (DICCIONARIO como en sidebar.py)
STEPS = {
    1: "Datos del cliente",
    2: "Backup de archivos",
    3: "Diagnóstico External White",
    4: "Medición del Standard Kit",
    5: "Cálculo de corrección",
    6: "Baseline y Exportación",
    7: "Validación"
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
    ### Advertencia: Backup de Archivos Baseline

    **Antes de continuar con este proceso, es CRÍTICO que realices una copia de seguridad manual 
    de los archivos baseline actuales.**

    Este procedimiento modificará los archivos de línea base del equipo NIR. Si algo sale mal, 
    necesitarás los archivos originales para restaurar la configuración.
    """,
    
    'backup_procedure': """
    ### Procedimiento recomendado para el backup:
    1. Copia toda la carpeta correspondiente a tu versión de software
    2. Pégala en una ubicación segura (Desktop, carpeta de backups, etc.)
    3. Renombra la carpeta con la fecha actual (ej: SX-Suite_Backup_2025-01-15)
    4. Verifica que la copia se realizó correctamente
    """,
    
    'wstd': """
    ### Instrucciones para el diagnóstico External White:

    1. **Prepara el External White** (referencia blanca del kit de calibración)
    2. En el equipo NIR, **NO tomes línea base** (medir como muestra normal)
    3. **Mide el External White y asígnale un ID identificable** en el equipo
    4. **Exporta el archivo TSV** con las mediciones
    5. **En la aplicación, selecciona manualmente** las filas que corresponden a las mediciones de referencia

    **¿Por qué este paso?** Si el sistema está bien calibrado, las mediciones del External White 
    sin línea base deberían estar muy cercanas a 0 en todo el espectro. Esto nos permite 
    diagnosticar el estado del equipo antes de realizar el ajuste.
    """,
    
    # ⭐ NUEVO: Instrucciones para muestras de control
    'control_samples': """
    ### Muestras de Control (Opcional pero Recomendado)

    **¿Por qué usar muestras de control?**
    Las muestras de control te permiten validar que el ajuste de baseline mejora las predicciones 
    del equipo. Medirás las mismas muestras **antes** y **después** del ajuste para comparar.

    **Instrucciones:**
    1. **Selecciona 3-10 muestras representativas** de tu rango analítico
    2. **Asígnales IDs identificables** (ej: Control_Protein_High, Control_Moisture_Low, etc.)
    3. **Mide las muestras AHORA** (antes del ajuste) con la lámpara nueva
    4. **Exporta el archivo TSV** - debe incluir las predicciones (columna "Results")
    5. Las medirás de nuevo al final del proceso para comparar

    **Importante:** 
    - Usa muestras con valores de predicción conocidos o esperados
    - Anota los IDs exactos - los necesitarás al final
    - El archivo debe tener la columna "Results" con las predicciones
    """,
    
    'kit': """
    ### Instrucciones para medición del Standard Kit:

    **NUEVO PROCESO CON DOS ARCHIVOS SEPARADOS:**

    **Archivo 1 - TSV de Referencia (histórico):**
    - Mediciones bien calibradas con lámpara de referencia
    - Puede ser un archivo antiguo de tu base de datos
    - Debe incluir IDs de muestra consistentes

    **Archivo 2 - TSV de Nueva Lámpara:**
    - Toma línea base con la lámpara NUEVA
    - Mide las MISMAS muestras que en el archivo de referencia
    - Usa exactamente los MISMOS IDs de muestra
    - Exporta el archivo TSV

    **Importante:** Los archivos se emparejarán por ID de muestra, así que usa identificadores 
    consistentes (ej: Sample01, Sample02, Soja_A, etc.)

    **Recomendación:** 10-20 muestras representativas de tu rango analítico.
    """,
    
    'baseline_load': """
    ### Instrucciones para cargar baseline:

    Necesitas cargar el archivo baseline actual de la lámpara nueva que tomaste antes de 
    medir el Standard Kit.

    Este archivo puede ser:
    - **Archivo .ref** (SX Suite 531 o anterior) - Formato binario
    - **Archivo .csv** (SX Suite 557 o posterior) - Formato de texto

    El archivo debe tener exactamente {n_channels} canales espectrales para coincidir con tus mediciones.
    """,
    
    # ⭐ NUEVO: Instrucciones para validación con muestras de control
    'validation_control': """
    ### Validación con Muestras de Control

    **Ha llegado el momento de validar el ajuste.**

    **Instrucciones:**
    1. **Mide las MISMAS muestras de control** que mediste al inicio
    2. **Usa los MISMOS IDs** para poder comparar
    3. **Exporta el archivo TSV** con las nuevas mediciones
    4. La aplicación comparará automáticamente:
       - Los espectros NIR antes vs. después
       - Las predicciones antes vs. después
       - Te mostrará si el ajuste mejoró la precisión

    **Objetivo:** Verificar que el ajuste de baseline realmente mejora las predicciones.
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
VERSION = "2.2.0"
VERSION_DATE = "2025-01-27"
VERSION_NOTES = """
Versión 2.2.0 - Cambios principales:
- ⭐ NUEVO: Soporte para muestras de control
- ⭐ NUEVO: Comparación de predicciones antes/después del ajuste
- ⭐ NUEVO: Validación espectral de muestras de control
- WSTD: Selección manual de filas mediante checkboxes
- WSTD: Visualización individual de cada medición con gráficos de diferencias
- Gráficos WSTD incluidos en el reporte HTML con Plotly interactivo
- Mejoras en la usabilidad del paso de diagnóstico inicial
- Arquitectura modular mejorada
"""