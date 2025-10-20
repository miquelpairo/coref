"""
Configuración y constantes para Baseline Adjustment Tool
"""

# Configuración de la página de Streamlit
PAGE_CONFIG = {
    "page_title": "Baseline Adjustment Tool",
    "layout": "wide"
}

# Definición de pasos del proceso
STEPS = {
    1: "Info del Cliente",
    2: "Backup",
    3: "Diagnostico WSTD",
    4: "Medicion del Kit",
    5: "Calculo de Correccion",
    6: "Baseline y Exportacion",
    7: "Validacion"
}

# Rutas de archivos baseline
BASELINE_PATHS = {
    'old_software': r"C:\ProgramData\NIR-Online\SX-Suite",
    'new_software': r"C:\ProgramData\NIR-Online\SX-Suite\Data\Reference"
}

# Extensiones de archivo soportadas
SUPPORTED_EXTENSIONS = {
    'tsv': ['tsv'],
    'baseline': ['ref', 'csv'],
    'ref': ['ref']
}

# Umbrales de diagnóstico para WSTD
WSTD_THRESHOLDS = {
    'good': 0.01,      # Bien ajustado
    'warning': 0.05,   # Desviación moderada
    'bad': float('inf')  # Requiere ajuste
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
    'wstd': 'WSTD'  # White Standard ID
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
    ### ⚠️ ATENCIÓN: Backup de Archivos Baseline

    **Antes de continuar con este proceso, es CRÍTICO que realices una copia de seguridad manual 
    de los archivos baseline actuales.**

    Este procedimiento modificará los archivos de línea base del equipo NIR. Si algo sale mal, 
    necesitarás los archivos originales para restaurar la configuración.
    """,
    
    'backup_procedure': """
    ### 📋 Procedimiento recomendado para el backup:
    1. Copia toda la carpeta correspondiente a tu versión de software
    2. Pégala en una ubicación segura (Desktop, carpeta de backups, etc.)
    3. Renombra la carpeta con la fecha actual (ej: `SX-Suite_Backup_2025-01-15`)
    4. Verifica que la copia se realizó correctamente
    """,
    
    'wstd': """
    ### 📋 Instrucciones para el técnico:

    1. **Prepara el White Standard** (referencia blanca del kit)
    2. En el equipo NIR, **NO tomes línea base** (medir como muestra normal)
    3. **Mide el White Standard con la lámpara de referencia** (la que está en uso actualmente)
       - 📝 ID: `WSTD`
       - 📝 Note: nombre de tu lámpara de referencia (ej: "L1", "LampOld", etc.)
    4. **Cambia a la lámpara nueva** en el equipo
    5. **Mide el White Standard con la lámpara nueva**
       - 📝 ID: `WSTD`
       - 📝 Note: nombre de tu lámpara nueva (ej: "L2", "LampNew", etc.)
    6. **Exporta el archivo TSV** con ambas mediciones

    ℹ️ **¿Por qué este paso?** Si el sistema está bien calibrado, las mediciones del White Standard 
    sin línea base deberían estar muy cercanas a 0 en todo el espectro. Este diagnóstico nos muestra 
    el estado actual del sistema antes del ajuste.
    """,
    
    'kit': """
    ### 📋 Instrucciones para el técnico:

    1. **Toma línea base con la lámpara NUEVA** usando el White Reference
    2. **Mide todas las muestras del Standard Kit con la lámpara de REFERENCIA**
       - 📝 Usa IDs consistentes para cada muestra (ej: "Sample01", "Sample02", "Soja_A", etc.)
       - 📝 Note: nombre de tu lámpara de referencia (el mismo del Paso 1)
    3. **Mide las MISMAS muestras con la lámpara NUEVA**
       - 📝 **Usa exactamente las mismas IDs** que en el paso anterior
       - 📝 Note: nombre de tu lámpara nueva (el mismo del Paso 1)
    4. **Exporta el archivo TSV** con todas las mediciones

    ⚠️ **Importante:** Es crítico que uses las mismas IDs para las mismas muestras en ambas lámparas. 
    El script emparejará las mediciones por ID.

    💡 **Tip:** Se recomienda medir entre 10-20 muestras representativas de tu rango analítico habitual.
    """,
    
    'baseline_load': """
    ### 📋 Instrucciones:

    Necesitas cargar el archivo baseline actual de la lámpara **{lamp_name}** que tomaste en el Paso 2.

    Este archivo puede ser:
    - 📄 **Archivo .ref** (SX Suite 531 o anterior) - Formato binario
    - 📄 **Archivo .csv** (SX Suite 557 o posterior) - Formato de texto

    El archivo debe tener **exactamente {n_channels} canales espectrales** para coincidir con tus mediciones.
    """
}

# Mensajes de éxito/error comunes
MESSAGES = {
    'success_file_loaded': "✅ Archivo cargado correctamente",
    'error_no_wstd': "❌ No se encontraron mediciones con ID = 'WSTD' en el archivo.",
    'error_no_samples': "❌ No se encontraron mediciones de muestras (todas son WSTD).",
    'error_no_common_samples': "❌ No hay muestras comunes entre las dos lámparas. Verifica que uses las mismas IDs.",
    'error_dimension_mismatch': "❌ **Error de validación:** El baseline tiene {baseline_points} puntos, pero el TSV tiene {tsv_channels} canales. No coinciden.",
    'success_dimension_match': "✅ Validación correcta: {n_points} puntos en ambos archivos",
    'success_correction_applied': "✅ Corrección aplicada al baseline",
    'warning_no_header': "⚠️ No se puede generar .ref desde CSV: faltan valores de cabecera del sensor",
    'warning_default_metadata': "⚠️ Metadatos generados por defecto"
}

# Configuración de informes HTML
REPORT_STYLE = """
body { font-family: Arial, sans-serif; margin: 40px; }
h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
h2 { color: #34495e; margin-top: 30px; }
.info-box { background-color: #ecf0f1; padding: 15px; border-radius: 5px; margin: 10px 0; }
.warning-box { background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #ffc107; }
.success-box { background-color: #d4edda; padding: 15px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #28a745; }
.metric { display: inline-block; margin: 10px 20px 10px 0; }
.metric-label { font-weight: bold; color: #7f8c8d; }
.metric-value { color: #2c3e50; font-size: 1.1em; }
table { border-collapse: collapse; width: 100%; margin: 20px 0; }
th, td { border: 1px solid #bdc3c7; padding: 10px; text-align: left; }
th { background-color: #3498db; color: white; }
.status-good { color: #28a745; font-weight: bold; }
.status-warning { color: #ffc107; font-weight: bold; }
.status-bad { color: #dc3545; font-weight: bold; }
.footer { margin-top: 50px; padding-top: 20px; border-top: 1px solid #bdc3c7; text-align: center; color: #7f8c8d; }
.tag { display:inline-block; padding:2px 8px; border-radius:12px; font-size:0.85em; }
.tag-ok { background:#e8f5e9; color:#2e7d32; border:1px solid #c8e6c9; }
.tag-no { background:#fff3e0; color:#e65100; border:1px solid #ffe0b2; }
"""
