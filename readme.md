COREF Suite
Comprehensive Baseline Correction and Validation Tool for NIR Spectroscopy
Mostrar imagen
Mostrar imagen
Mostrar imagen
Mostrar imagen

📋 Tabla de Contenidos

Descripción
Características Principales
Arquitectura
Instalación
Uso
Estructura del Proyecto
Herramientas Disponibles
Workflow Guiado
Generación de Reportes
Requisitos del Sistema
Contribución
Licencia
Contacto


🎯 Descripción
COREF Suite es una herramienta profesional desarrollada para técnicos de servicio de equipos NIR (Near-Infrared Spectroscopy) de BÜCHI Labortechnik AG. Proporciona un conjunto completo de utilidades para:

Corrección y alineamiento de baseline después de cambios de lámpara
Validación de estándares ópticos
Ajuste fino mediante offset vertical
Generación automática de reportes HTML profesionales
Comparación y análisis espectral avanzado

La suite integra múltiples herramientas en una interfaz web intuitiva construida con Streamlit, permitiendo a los técnicos realizar tareas complejas de mantenimiento y validación de forma guiada y documentada.

✨ Características Principales
🔧 Herramientas Standalone

Baseline Adjustment: Workflow completo de 6 pasos para ajuste post-mantenimiento
Validation Standards: Validación de kits de estándares ópticos con análisis estadístico
Offset Adjustment: Corrección de offset vertical con simulación y análisis de impacto
Comparación de Espectros: Análisis comparativo detallado de mediciones
White Reference Comparison: Comparación de referencias blancas (WSTD)
Conversión de Archivos: Conversión entre formatos .ref y .csv

📊 Capacidades de Análisis

Validación espectral con métricas de correlación, RMS y diferencias máximas
Detección automática de shifts espectrales
Análisis de regiones críticas del espectro NIR
Estadísticas globales y por muestra individual
Visualizaciones interactivas con Plotly

📄 Generación de Reportes

Reportes HTML profesionales con estilo corporativo BÜCHI
Dos tipos de reportes especializados:

Validation Report: Para validación de estándares ópticos
Offset Adjustment Report: Para ajustes de offset con análisis pre/post


Exportación de datos en CSV para análisis adicional
Documentación completa del proceso de mantenimiento

🎨 Interfaz de Usuario

Interfaz web moderna y responsive
Tema corporativo BÜCHI personalizado
Navegación intuitiva paso a paso
Sistema de autenticación integrado
Gestión de sesión con recuperación de estado


🏗️ Arquitectura
COREF Suite (14,008 líneas de código)
│
├── 📦 Core (3,691 líneas)
│   ├── file_handlers.py           # Manejo de archivos .ref/.csv
│   ├── spectral_processing.py     # Procesamiento espectral
│   ├── validation.py              # Lógica de validación
│   ├── report_generator.py        # Generador de reportes principal
│   ├── validation_kit_report_generator.py
│   └── offset_adjustment_report_generator.py
│
├── 🖥️ Pages (5,025 líneas)
│   ├── Baseline adjustment        # Workflow completo guiado
│   ├── Validation Standards       # Validación de kits
│   ├── Offset Adjustment          # Ajuste de offset
│   ├── Comparación Espectros      # Análisis comparativo
│   ├── White Reference            # Comparación WSTD
│   └── File Conversion            # Conversión de formatos
│
├── 🎨 UI (2,799 líneas)
│   ├── step_01_conversion.py      # Paso 1: Conversión
│   ├── step_02_wstd.py            # Paso 2: White reference
│   ├── step_03_lamp.py            # Paso 3: Comparación lámparas
│   ├── step_04_baseline_alignment.py  # Paso 4: Alineamiento
│   ├── step_05_standards.py       # Paso 5: Carga estándares
│   └── step_06_validation.py      # Paso 6: Validación final
│
└── 🛠️ Utils (881 líneas)
    ├── plotting.py                # Visualizaciones Plotly
    ├── validators.py              # Validaciones y checks
    └── control_samples.py         # Gestión de muestras control

📥 Instalación
Requisitos Previos

Python 3.12 o superior
pip (gestor de paquetes de Python)
Git (opcional, para clonar el repositorio)

Paso 1: Clonar el repositorio
bashgit clone https://github.com/your-organization/coref-suite.git
cd coref-suite
Paso 2: Crear entorno virtual (recomendado)
bashpython -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
Paso 3: Instalar dependencias
bashpip install -r requirements.txt
Paso 4: Configurar autenticación
Edita el archivo auth.py y configura tu contraseña:
python# auth.py
VALID_PASSWORD = "tu_contraseña_aqui"
Paso 5: Ejecutar la aplicación
bashstreamlit run app.py
La aplicación se abrirá automáticamente en http://localhost:8501

🚀 Uso
Inicio Rápido

Autenticación: Introduce la contraseña configurada
Selecciona herramienta: Elige entre workflow guiado o herramientas standalone
Carga archivos: Sube los archivos TSV/REF/CSV necesarios
Análisis: Sigue las instrucciones en pantalla
Exporta resultados: Descarga reportes y archivos corregidos

Ejemplo: Workflow Completo de Baseline Adjustment
bash1. Conversión de archivos → Convierte .ref a .csv si es necesario
2. White Reference → Compara WSTD pre/post mantenimiento
3. Comparación Lámparas → Analiza diferencias espectrales
4. Alineamiento → Calcula y aplica corrección al baseline
5. Carga Estándares → Importa kit de validación
6. Validación → Verifica con estándares ópticos
Ejemplo: Ajuste Rápido de Offset
bash1. Carga TSV de referencia y actual
2. Selecciona estándares para análisis
3. Configura valor de offset
4. Visualiza impacto en métricas
5. Carga baseline y aplica corrección
6. Descarga baseline ajustado
7. Genera reporte HTML

📂 Estructura del Proyecto
coref-suite/
│
├── app.py                      # Punto de entrada principal
├── auth.py                     # Sistema de autenticación
├── config.py                   # Configuraciones globales (557 líneas)
├── session_manager.py          # Gestión de estado de sesión (411 líneas)
├── buchi_streamlit_theme.py    # Tema corporativo BÜCHI (472 líneas)
├── requirements.txt            # Dependencias del proyecto
├── README.md                   # Este archivo
│
├── core/                       # Lógica de negocio principal
│   ├── file_handlers.py
│   ├── spectral_processing.py
│   ├── validation.py
│   ├── report_generator.py
│   ├── validation_kit_report_generator.py
│   └── offset_adjustment_report_generator.py
│
├── pages/                      # Herramientas standalone
│   ├── 1_📐_Baseline_adjustment.py
│   ├── 2_🎯_Validation_Standards.py
│   ├── 3_🎚️_Offset_Adjustment.py
│   ├── 4_🔍_Comparacion_Espectros.py
│   ├── 5_⚪_White_Reference_Comparison.py
│   └── 6_🔄_File_Conversion.py
│
├── ui/                         # Componentes del workflow guiado
│   ├── step_01_conversion.py
│   ├── step_02_wstd.py
│   ├── step_03_lamp.py
│   ├── step_04_baseline_alignment.py
│   ├── step_05_standards.py
│   └── step_06_validation.py
│
└── utils/                      # Utilidades y helpers
    ├── plotting.py
    ├── validators.py
    └── control_samples.py

🛠️ Herramientas Disponibles
1. Baseline Adjustment (Workflow Guiado)
Propósito: Proceso completo de ajuste de baseline después de mantenimiento
Pasos:

Conversión de formatos
Comparación de white references
Análisis de lámparas pre/post
Alineamiento espectral
Carga de estándares de validación
Validación final con generación de reporte

Salidas:

Baseline corregido (.ref/.csv)
Reporte HTML completo
Datos de validación en CSV

2. Validation Standards (Standalone)
Propósito: Validación independiente de kits de estándares ópticos
Características:

Análisis de correlación espectral
Detección de shifts espectrales
Métricas de validación (Max Δ, RMS, Offset)
Análisis por regiones críticas
Reporte HTML profesional

Requisitos:

TSV de referencia (pre-mantenimiento)
TSV actual (post-mantenimiento)

3. Offset Adjustment (Standalone)
Propósito: Ajuste fino de offset vertical en baseline
Características:

Simulación de impacto en tiempo real
Comparación pre/post ajuste
Análisis global del kit
Gráficos interactivos
Reporte detallado con recomendaciones

Casos de uso:

Fine-tuning post-validación
Corrección de bias sistemático
Alineamiento con equipo de referencia

4. Comparación de Espectros
Propósito: Análisis comparativo detallado entre mediciones
Visualizaciones:

Overlay de espectros
Diferencias punto a punto
Diferencias acumuladas
Estadísticas por muestra

5. White Reference Comparison
Propósito: Comparación de referencias blancas (WSTD)
Análisis:

Overlay temporal
Diferencias absolutas y relativas
Estadísticas de estabilidad
Detección de deriva

6. File Conversion
Propósito: Conversión entre formatos de baseline
Formatos soportados:

.ref → .csv (con metadatos)
.csv → .ref (preservando cabecera)


🔄 Workflow Guiado
El workflow guiado de 6 pasos proporciona un proceso estructurado para el ajuste completo de baseline:
mermaidgraph LR
    A[1. Conversión] --> B[2. WSTD]
    B --> C[3. Lámparas]
    C --> D[4. Alineamiento]
    D --> E[5. Estándares]
    E --> F[6. Validación]
    F --> G[Reporte Final]
Ventajas del Workflow

✅ Proceso guiado paso a paso
✅ Validaciones automáticas en cada etapa
✅ Persistencia de datos entre pasos
✅ Imposible saltarse pasos críticos
✅ Documentación automática del proceso
✅ Reporte final comprehensivo


📊 Generación de Reportes
Validation Report
Contenido:

Información del servicio
Resumen ejecutivo con métricas clave
Criterios de validación aplicados
Estadísticas globales del kit
Resultados detallados por estándar
Vista global de espectros
Análisis individual con gráficos
Análisis de regiones críticas

Formato: HTML con estilo corporativo BÜCHI, navegación lateral, gráficos interactivos
Offset Adjustment Report
Contenido:

Información del servicio y ajuste
Resumen ejecutivo con impacto
Justificación técnica del offset
Comparación de métricas pre/post
Vista global de espectros (3 estados)
Baseline original vs ajustado
Análisis individual por estándar
Recomendaciones finales

Formato: HTML profesional con análisis comparativo completo

💻 Requisitos del Sistema
Software

Python: 3.12 o superior
Sistema Operativo: Windows 10/11, Linux, macOS
Navegador: Chrome, Firefox, Edge (versiones recientes)
RAM: Mínimo 4 GB (recomendado 8 GB)
Espacio en disco: 500 MB para instalación + datos

Dependencias Principales
streamlit==1.39.0
pandas==2.2.3
numpy==2.1.2
plotly==5.24.1
openpyxl==3.1.5
python-pptx==1.0.2
python-docx==1.1.2
Ver requirements.txt para la lista completa de dependencias.

🧪 Testing
Datos de Prueba
Los datos de ejemplo se encuentran en la carpeta test_data/ (no incluida en el repositorio por tamaño):
test_data/
├── baselines/          # Archivos .ref y .csv de ejemplo
├── tsv_files/          # Archivos TSV de mediciones
└── validation_kits/    # Kits completos de validación
Casos de Uso de Prueba

Workflow completo: Usar datos de mantenimiento real
Validación standalone: Kit de 5 estándares Buchi
Offset adjustment: Simulación con offset conocido
Comparación espectral: Mediciones pre/post lámpara


🤝 Contribución
Este es un proyecto interno de BÜCHI Labortechnik AG. Para contribuir:

Fork el proyecto
Crea una rama para tu feature (git checkout -b feature/AmazingFeature)
Commit tus cambios (git commit -m 'Add some AmazingFeature')
Push a la rama (git push origin feature/AmazingFeature)
Abre un Pull Request

Estándares de Código

Seguir PEP 8 para estilo de código Python
Documentar todas las funciones con docstrings
Añadir type hints donde sea apropiado
Mantener funciones < 50 líneas cuando sea posible
Escribir tests para nuevas funcionalidades
