# -*- coding: utf-8 -*-
"""
Configuración y constantes para NIR ServiceKit
"""

# ============================================================================
# 1) CONFIGURACIÓN DE LA PÁGINA (STREAMLIT)
# ============================================================================

PAGE_CONFIG = {
    "page_title": "NIR ServiceKit",
    "page_icon": "🏠",
    "layout": "wide",
}

# ============================================================================
# 2) DEFINICIÓN DE PASOS DEL PROCESO
# ============================================================================

STEPS = {
    1: "Datos del cliente",
    2: "Backup de archivos",
    3: "Diagnóstico Inicial",
    4: "Validación",
    5: "Alineamiento de Baseline",
}

# ============================================================================
# 3) RUTAS Y EXTENSIONES SOPORTADAS
# ============================================================================

BASELINE_PATHS = {
    'old_software': r"C:\ProgramData\NIR-Online\SX-Suite",
    'new_software': r"C:\ProgramData\NIR-Online\SX-Suite\Data\Reference",
}

SUPPORTED_EXTENSIONS = {
    'tsv': ['tsv', 'txt', 'csv'],
    'baseline': ['ref', 'csv'],
    'ref': ['ref'],
}

# ============================================================================
# 4) IDENTIFICADORES ESPECIALES
# ============================================================================

SPECIAL_IDS = {
    'wstd': 'WSTD',
}

# ============================================================================
# 5) UMBRALES DE DIAGNÓSTICO (WSTD)
# ============================================================================

WSTD_THRESHOLDS = {
    'good': 0.015,
    'warning': 0.05,
    'bad': float('inf'),
}

DIAGNOSTIC_STATUS = {
    'good': {
        'icon': '🟢',
        'label': 'Bien ajustado',
        'color': 'green',
    },
    'warning': {
        'icon': '🟡',
        'label': 'Desviación moderada',
        'color': 'warning',
    },
    'bad': {
        'icon': '🔴',
        'label': 'Offset, ajustar a offset inicial',
        'color': 'red',
    },
}

# ============================================================================
# 6) METADATOS POR DEFECTO PARA CSV
# ============================================================================

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
    'bounds': '400.0,1000.0',
}

# ============================================================================
# 7) CONFIGURACIÓN DE MUESTRAS DE CONTROL
# ============================================================================

CONTROL_SAMPLES_CONFIG = {
    'min_samples': 1,
    'max_samples': 50,
    'prediction_tolerance': {
        'good': 0.5,
        'warning': 2.0,
        'bad': float('inf'),
    },
}

# ============================================================================
# 8) CONFIGURACIÓN DE GRÁFICOS
# ============================================================================

PLOT_CONFIG = {
    'figsize_default': (12, 6),
    'figsize_large': (12, 8),
    'figsize_report': (14, 7),
    'dpi': 150,
    'alpha_spectrum': 0.85,
    'alpha_grid': 0.3,
    'linewidth_default': 2,
    'linewidth_thin': 1,
}

# ============================================================================
# 9) INSTRUCCIONES POR PASO (UI)
# ============================================================================

INSTRUCTIONS = {
    # ========================================================================
    # STEP 00: CLIENT INFO
    # ========================================================================
    'client_info': """
Por favor, completa los siguientes datos antes de comenzar el proceso de ajuste.
Esta información se incluirá en el informe final.
    """,

    # ========================================================================
    # STEP 01: BACKUP
    # ========================================================================
    'backup': """
### ⚠️ CRÍTICO: Diagnóstico del Estado Actual
**Antes de continuar, debes caracterizar cómo está midiendo el equipo actualmente.**

Lo más importante es documentar el estado actual del sensor para poder alinear correctamente 
la baseline tras el cambio de lámpara. Una copia de seguridad sin esta información de referencia 
no sirve para realizar el ajuste.
    """,

    'backup_procedure': r"""
### Procedimiento para el backup:

**Objetivo:** Identificar la baseline que se usa actualmente y hacer una copia de seguridad.

1. **Localiza la carpeta de baseline según tu versión de software:**
   
   - **SX Suite ≤531**: `C:\ProgramData\NIR-Online\SX-Suite`
     - El archivo tiene un patrón de nombre: `serialnumber.lamp.date.ref` (ej: `316FG103.1.2025-11-21.ref`)
     - La posición de la lámpara: **1** indica primaria, **2** indica secundaria
     - **Copia los archivos .ref de ambas lámparas**
     - **Si no hay archivos .ref**, el equipo está trabajando sin línea base
   
   - **SX Suite ≥554**: `C:\ProgramData\NIR-Online\SX-Suite\Data\Reference`
     - El archivo tiene el nombre: `numerodeserie.baseline.lampara.csv` (ej: `316FG103.Baseline.1.csv')

2. **Haz copia de los archivos**, incluyendo el número de serie en el nombre de la carpeta (ej: `316FG103_Backup_2025-11-21`)

3. **Carga la baseline en el PC de trabajo** para continuar con el proceso

4. **Verifica que la copia se realizó correctamente**
    """,

    # ========================================================================
    # STEP 02: WSTD - DIAGNÓSTICO INICIAL
    # ========================================================================
    'wstd': """
### 📊 Diagnóstico Inicial del Sensor
**Objetivo:** Caracterizar el estado actual del sensor antes de realizar cualquier ajuste.

**Procedimiento:**
1. **Comprueba qué archivo de baseline se está usando actualmente** en el equipo y cárgalo
2. **Mide una referencia blanca** (External White) con el baseline que se está usando. 
3. **Asigna un ID identificable** a la medición (ej: "WHITE"). Usa el mismo ID en todo el proceso.
4. **Exporta el archivo TSV** con las mediciones
5. **Selecciona las filas correspondientes** usando los checkboxes

**¿Qué evaluamos?**
Las desviaciones del espectro respecto a cero nos indican la línea base actual.
Esto sirve como referencia para alinear el sensor a la misma línea base.

**IMPORTANTE:** Este archivo TSV servirá para alinear la lámpara posteriormente. Se cargará como referencia en el Paso 4.
    """,

    'wstd_file_info': """
📋 **Este archivo TSV se usará como referencia en el Paso 5 (Alineamiento de Baseline)**

Asegúrate de medir con el baseline actual del equipo antes de cualquier ajuste.
    """,

    'wstd_selection_instruction': "✅ Marca las casillas de las mediciones que corresponden al White Standard.",

    'wstd_continue_warning': """
⚠️ **Debes cargar el archivo TSV de External White para continuar**

Este archivo es necesario como referencia para el alineamiento de baseline en el Paso 5.
    """,

    # ========================================================================
    # STEP 04: VALIDATION
    # ========================================================================
    'validation_objective': """
### 🎯 Objetivo
Verificar si el equipo está correctamente alineado midiendo el White Standard.

**Proceso:**
1. Mide el White Standard con el baseline actual
2. Comparamos con la referencia del Paso 3
3. **Si está bien alineado** (RMS < 0.005) → Generar informe y finalizar ✅
4. **Si necesita ajuste** (RMS ≥ 0.005) → Ir al Paso 5 para alinear ⚙️
    """,

    'validation_first_measurement': """
**Primera medición:**
1. Con el baseline actual del equipo
2. Mide el MISMO White Standard del Paso 3
3. Exporta el TSV y cárgalo aquí
    """,

    'validation_success_title': """
✅ **VALIDACIÓN EXITOSA**

**White Standard ({white_id}):** RMS = {rms:.6f} < 0.005

El equipo está correctamente alineado y listo para usar.
    """,

    'validation_alignment_needed': """
⚠️ **ALINEAMIENTO NECESARIO**

**White Standard ({white_id}):** RMS = {rms:.6f} ≥ 0.005

El equipo necesita alineamiento de baseline.
    """,

    'validation_option_continue': """
**Recomendado**: Ve al Paso 5 para ajustar el baseline.

En el Paso 5 podrás:
1. Cargar el baseline actual
2. Calcular la corrección necesaria
3. Exportar el baseline corregido
4. Volver a este paso para validar
    """,

    'validation_option_force': """
⚠️ **No recomendado**: Genera el informe con el estado actual 
aunque no se cumpla el umbral de RMS < 0.002.

El informe indicará claramente que el alineamiento no fue exitoso.
    """,

    'validation_report_intro': """
El informe incluirá:
- Datos del cliente y equipo
- Métricas del White Standard
- Gráficos comparativos
- Conclusiones
    """,

    # ========================================================================
    # STEP 05: ALIGNMENT
    # ========================================================================
    'alignment_intro': """
### ⚙️ Alineamiento de Baseline

Has llegado aquí porque el RMS del White Standard es ≥ 0.002.

**En este paso:**
1. Cargas el baseline actual del equipo
2. Calculamos la corrección necesaria
3. Exportas el baseline corregido
4. Lo instalas en el equipo
5. Vuelves al Paso 4 para validar
    """,

    'alignment_procedure': """
### 📋 Procedimiento de Alineamiento

**IMPORTANTE:** El equipo debe estar estabilizado (mínimo 30 minutos encendido) antes de comenzar.

**Pasos a seguir:**

1. **Tomar nueva baseline** en el equipo con la lámpara nueva
   - Asegúrate de que el equipo esté estabilizado (≥30 min)
   - Toma la baseline siguiendo el procedimiento normal del equipo

2. **Medir el White Standard** con la nueva baseline
   - Usa el MISMO White Standard del Paso 3
   - Asigna el mismo ID identificable (ej: "WHITE")
   - Exporta el TSV con esta medición

3. **Cargar los archivos en esta aplicación:**
   - Baseline tomada (archivo .ref o .csv)
   - TSV de referencia (Paso 3) - se carga automáticamente
   - TSV de nueva medición (que acabas de medir)

4. **Generar baseline corregido**
   - La aplicación calculará la corrección necesaria
   - Descarga el archivo baseline corregido

5. **Sustituir el baseline en el equipo:**
   - **SX Suite ≤531**: Copia el archivo .ref corregido a `C:\\ProgramData\\NIR-Online\\SX-Suite`
   - **SX Suite ≥554**: Copia el archivo .csv corregido a `C:\\ProgramData\\NIR-Online\\SX-Suite\\Data\\Reference`
   - Reemplaza el archivo baseline actual con el corregido

**Verificación:** Después de sustituir el baseline, vuelve al Paso 4 para validar el ajuste.
    """,

    'alignment_load_baseline': "### 1️⃣ Cargar Baseline Actual",
    'alignment_baseline_info': "Sube el archivo de baseline actual del equipo (.ref o .csv)",
    'alignment_validation_data': "### 2️⃣ Datos de Validación",

    'alignment_validation_error': """
❌ No hay datos de validación del Paso 4

Vuelve al Paso 4 para realizar la validación primero
    """,

    'alignment_validation_loaded': "✅ Datos de validación cargados (White ID: {white_id})",
    'alignment_apply_correction': "### 3️⃣ Aplicar Corrección al Baseline",
    'alignment_correction_applied': "✅ Corrección aplicada al baseline",

    'alignment_dimension_error': """
❌ Error de dimensiones:
- Baseline: {baseline_points} puntos
- Corrección: {correction_points} puntos
    """,

    'alignment_export': "### 4️⃣ Exportar Baseline Corregido",
    'alignment_export_ref': "**Formato .ref (binario)**",
    'alignment_export_csv': "**Formato .csv (nuevo software)**",
    'alignment_header_preserved': "✅ Cabecera original preservada",
    'alignment_metadata_preserved': "✅ Metadatos originales preservados",
    'alignment_no_header': "⚠️ No hay cabecera original (archivo no era .ref)",
    'alignment_metadata_default': "ℹ️ Usando metadatos por defecto",
    'alignment_return': "### ⬅️ Volver a Validación",

    'alignment_next_steps': """
**⚠️ PRÓXIMOS PASOS:**

1. ✅ Descarga el baseline corregido
2. ✅ Cópialo al equipo (reemplaza el anterior)
3. ✅ Reinicia SX Suite
4. ✅ Haz clic en "Volver a Validación"
5. ✅ Mide de nuevo el White Standard
    """,

    # ========================================================================
    # LEGACY / OTROS (mantener por compatibilidad)
    # ========================================================================
    'control_samples': """
### 🎯 Muestras de Control (Opcional)

**Objetivo:** Validar que el ajuste de baseline mejora las predicciones del equipo.

**¿Qué son muestras de control?**
Muestras reales que medirás **antes** y **después** del ajuste para comparar 
el impacto en las predicciones.
    """,

    'kit': """
### 📦 Archivos para Calcular la Corrección

**La herramienta necesita DOS archivos TSV para calcular el ajuste:**

**Archivo 1 - Referencia (estado deseado):**
- Mediciones del sensor en el estado que quieres replicar

**Archivo 2 - Estado Actual (a corregir):**
- Mediciones del sensor en su estado actual
- Debe contener las **MISMAS muestras** que el archivo de referencia
    """,

    'baseline_load': """
### 📁 Cargar Baseline Actual

**Necesitas el archivo baseline que usaste para medir el "Estado Actual" en el paso anterior.**
    """,
}

# ============================================================================
# 10) MENSAJES DE ÉXITO/ERROR/INFO
# ============================================================================

MESSAGES = {
    # Generales
    'success_file_loaded': "✅ Archivo cargado correctamente",
    'success_dimension_match': "✅ Validación correcta: {n_points} puntos en ambos archivos",
    'success_correction_applied': "✅ Corrección aplicada al baseline",

    # Errores
    'error_no_wstd': "❌ No se encontraron mediciones con ID = 'External White' en el archivo.",
    'error_no_samples': "❌ No se encontraron mediciones de muestras (todas son WSTD).",
    'error_no_common_samples': "❌ No hay muestras comunes entre los dos archivos. Verifica que uses las mismas IDs.",
    'error_dimension_mismatch': "**Error de validación:** El baseline tiene {baseline_points} puntos, pero el TSV tiene {tsv_channels} canales. No coinciden.",
    'error_no_predictions': "❌ El archivo no contiene la columna 'Results' con las predicciones",
    'error_no_common_control': "❌ No se encontraron muestras de control comunes entre las mediciones iniciales y finales",

    # Advertencias
    'warning_no_header': "⚠️ No se puede generar .ref desde CSV: faltan valores de cabecera del sensor",
    'warning_default_metadata': "⚠️ Metadatos generados por defecto",

    # Info
    'info_two_files': "ℹ️ Proceso actualizado: ahora usamos dos archivos TSV separados para mayor flexibilidad",
    'info_control_skipped': "ℹ️ Paso de muestras de control omitido",

    # Muestras de control
    'success_control_initial': "✅ Muestras de control iniciales guardadas correctamente",
    'success_control_final': "✅ Muestras de control finales guardadas correctamente",
}

# ============================================================================
# 11) UMBRALES Y CONFIGURACIÓN DE VALIDACIÓN
# ============================================================================

VALIDATION_THRESHOLDS = {
    'excellent': 0.001,
    'good': 0.01,
    'acceptable': 0.05,
    'bad': float('inf'),
}

VALIDATION_STATUS = {
    'excellent': {
        'icon': '✅',
        'label': 'Excelente',
        'color': 'green',
    },
    'good': {
        'icon': '✅',
        'label': 'Bueno',
        'color': 'green',
    },
    'acceptable': {
        'icon': '⚠️',
        'label': 'Aceptable',
        'color': 'warning',
    },
    'bad': {
        'icon': '❌',
        'label': 'Requiere atención',
        'color': 'red',
    },
}

# Umbral crítico para decidir si necesita alineamiento en Paso 4
VALIDATION_RMS_THRESHOLD = 0.005

WHITE_REFERENCE_THRESHOLDS = {
    'excellent': {'rms': 0.002, 'max_diff': 0.005, 'color': '#4caf50'},
    'good': {'rms': 0.005, 'max_diff': 0.01, 'color': '#8bc34a'},
    'acceptable': {'rms': 0.01, 'max_diff': 0.02, 'color': '#ffc107'},
    'review': {'color': '#f44336'},
}

DEFAULT_VALIDATION_THRESHOLDS = {
    'correlation': 0.9995,
    'max_diff': 0.015,
    'rms': 0.010,
}

CRITICAL_REGIONS = [(1100, 1200), (1400, 1500), (1600, 1700)]

OFFSET_LIMITS = {
    'negligible': 0.001,
    'acceptable': 0.005,
}

# ============================================================================
# 12) CONFIGURACIÓN DE INFORMES HTML
# ============================================================================

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

# ============================================================================
# 13) COLORES Y PLANTILLA PLOTLY
# ============================================================================

BUCHI_COLORS = {
    'primary': '#093A34',
    'secondary': '#289A93',
    'accent': '#00BFA5',
    'success': '#28a745',
    'warning': '#ffc107',
    'danger': '#dc3545',
    'info': '#17a2b8',
    'light': '#f8f9fa',
    'dark': '#343a40',
}

PLOTLY_TEMPLATE = {
    'layout': {
        'colorway': ['#093A34', '#289A93', '#00BFA5', '#FF6B6B', '#4ECDC4'],
        'font': {'family': 'Segoe UI, Arial, sans-serif'},
        'plot_bgcolor': 'white',
        'paper_bgcolor': 'white',
    }
}

# ============================================================================
# 14) INFORMACIÓN DE VERSIÓN
# ============================================================================

VERSION = "3.1.0"
VERSION_DATE = "2025-12-26"
VERSION_NOTES = """
Versión 3.1.0 - Optimización y Refactorización:
- ✅ Mensajes e instrucciones centralizados en config.py
- ✅ Eliminación de duplicación en funciones de visualización
- ✅ Arquitectura modular mejorada (plotly_utils, standards_analysis)
- ✅ CSS centralizado en buchi_streamlit_theme.py
- ✅ Gestión consistente de unsaved_changes en todos los steps
- ✅ Nomenclatura clara para funciones específicas vs genéricas
- 📊 Reducción de ~6,000 líneas de código (-33%)
- 🎨 UI consistente con estilos corporativos BUCHI
"""
