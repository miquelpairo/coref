# COREF Suite - Audit & Refactoring Plan
**Fecha:** 21 Diciembre 2024  
**Versión:** 2.0  
**Líneas totales:** ~17,869 (después de limpieza Fase 1)  
**Autor:** Miquel (NIR Technical Specialist, BUCHI Spain)

---

## 📋 TABLA DE CONTENIDOS

1. [Resumen Ejecutivo](#-resumen-ejecutivo)
2. [Estructura del Proyecto](#-estructura-del-proyecto)
3. [Fase 1: Limpieza Completada](#-fase-1-limpieza-completada)
4. [Análisis de Duplicación (Priorizado)](#-análisis-de-duplicación-por-prioridad)
5. [Resumen del Audit](#-resumen-del-audit-completo)
6. [Roadmap de Refactoring](#-roadmap-de-refactoring)
7. [Estimación de Costes](#-estimación-de-costes-continue-api)
8. [Métricas Objetivo](#-métricas-objetivo)
9. [Decisiones Pendientes](#-decisiones-pendientes)

---

## 🎯 RESUMEN EJECUTIVO

### Estado del Audit
- **GRUPO 1 (Baseline Adjustment):** ✅ 100% Auditado (COMPLETO)
- **GRUPO 2 (Consolidators):** ⏳ Pendiente (páginas 6-8 + parsers)

### Duplicación Total Detectada

| # | Categoría | Líneas | % Total | Prioridad | Fase |
|---|-----------|--------|---------|-----------|------|
| 1 | **Páginas 4 & 5** (Spectrum Comparison) | ~1,700 | 9.5% | 🔴 CRÍTICA | Fase 4 |
| 2 | **Report Generators** (/core) | ~1,200 | 6.7% | 🔴 ALTA | Fase 2 |
| 3 | **Páginas 2 & 3** (Validation) | ~900 | 5.0% | 🔴 ALTA | Fase 4 |
| 4 | **UI Components** (steps) | ~650 | 3.6% | 🟡 MEDIA | Fase 4 |
| 5 | **Utils Plotting** (triple) | ~300 | 1.7% | 🟡 MEDIA | Fase 5 |
| 6 | **Parsers HTML** (GRUPO 2) | ~200 | 1.1% | 🟡 MEDIA | Fase 3 |
| | **TOTAL** | **~4,950** | **27.7%** | | |

### Impacto del Refactoring

```
📊 ANTES:  17,869 líneas (27.7% duplicadas)
📉 DESPUÉS: 12,900-13,500 líneas
✅ AHORRO: ~4,950 líneas (-28%)
```

**Tiempo estimado:** 10-15 horas  
**Coste estimado:** $3.30 (Continue API)  
**Budget disponible:** $6.05 → **Sobrante: $2.75**

---

## 📊 ESTRUCTURA DEL PROYECTO

### Arquitectura General

```
COREF Suite (17,869 líneas)
│
├── app.py (router principal Streamlit)
│
├── GRUPO 1: Baseline Adjustment Tool (Arquitectura coherente) ✅ AUDITADO
│   ├── Pages 0-5 (6 archivos, ~140KB)
│   │   ├── 0_🏠_Home.py (11KB) ✅
│   │   ├── 1_📐_Baseline_adjustment.py (3.5KB - router) ✅
│   │   ├── 2_🎯_Validation_Standards.py (46KB) ⚠️ ALTA DUPLICACIÓN
│   │   ├── 3_🎚️_Offset_Adjustment.py (57KB) ⚠️ ALTA DUPLICACIÓN
│   │   ├── 4_🔍_Comparacion_Espectros.py (39KB) 🔴 DUPLICACIÓN EXTREMA
│   │   └── 5_⚪_White_Reference_Comparison.py (43KB) 🔴 DUPLICACIÓN EXTREMA
│   │
│   ├── /core - Procesamiento NIR (4 módulos, ~1,888 líneas)
│   │   ├── file_handlers.py (142 líneas) ✅ SIN DUPLICACIÓN
│   │   ├── spectral_processing.py (96 líneas) ✅ SIN DUPLICACIÓN
│   │   ├── report_generator.py (~600 líneas) ⚠️ 60% duplicado
│   │   ├── offset_adjustment_report_generator.py (~550 líneas) ⚠️ 60% duplicado
│   │   └── validation_kit_report_generator.py (~500 líneas) ⚠️ 60% duplicado
│   │
│   ├── /ui - Workflow Components (8 archivos, ~60KB)
│   │   ├── sidebar.py (6.5KB) ✅ Único (navegación + modal)
│   │   ├── step_00_client_info.py (3KB) ✅
│   │   ├── step_01_backup.py (1.5KB) ✅
│   │   ├── step_02_wstd.py (12KB) ⚠️ Duplicación con step_04
│   │   ├── step_04_validation.py (21KB) ⚠️ Duplicación con step_02, pages 2/3
│   │   ├── step_05_baseline_alignment.py (14KB) ✅
│   │   ├── test_step_04_checkpoints.py (13KB) ✅
│   │   └── utilities.py (2.5KB) ✅
│   │
│   └── /utils - Helpers (6 archivos, ~81KB)
│       ├── plotting.py (12KB) ⚠️ Triple duplicación
│       ├── prediction_charts.py (16KB) ⚠️ Triple duplicación
│       ├── prediction_reports.py (28KB) ⚠️ Triple duplicación
│       ├── control_samples.py (15KB) ❌ OBSOLETO - ELIMINAR
│       ├── nir_analyzer.py (9KB) ✅ Único (parser XML)
│       └── validators.py (1.3KB) ✅ Único
│
└── GRUPO 2: Consolidator Tools (Arquitectura ad-hoc) ⏳ PENDIENTE AUDIT
    ├── Pages 6-8 (3 archivos, ~66KB)
    │   ├── 6_📊_Prediction_Reports.py (12KB)
    │   ├── 7_📑_MetaReports.py (19KB)
    │   └── 8_✅_TSV_Validation_Reports.py (34KB)
    │
    └── /modules/consolidator
        └── /parsers (3 parsers HTML)
            ├── baseline_parser.py ⚠️ _extract_plotly_charts() 100% duplicada
            ├── predictions_parser.py ⚠️ _extract_plotly_charts() 100% duplicada
            └── validation_parser.py ⚠️ _extract_plotly_charts() 100% duplicada
```

**Leyenda:**
- ✅ Sin duplicación / Bien diseñado
- ⚠️ Duplicación moderada (40-80%)
- 🔴 Duplicación extrema (>80%)
- ❌ Obsoleto / Eliminar
- ⏳ Pendiente de auditar

---

## ✅ FASE 1: LIMPIEZA COMPLETADA

**Commit:** `0088199 - Eliminar scripts ui obsoletos`  
**Fecha:** 21 Diciembre 2024

### Archivos eliminados

| Archivo | Líneas | Motivo |
|---------|--------|--------|
| `ui/History/step_05_baseline.py` | ~600 | Obsoleto - funcionalidad movida a step_05 |
| `ui/History/step_06_export.py` | ~500 | Obsoleto - funcionalidad integrada |
| `ui/step_04_baseline_alignment.py` | ~531 | Obsoleto - renombrado y refactorizado |
| `ui/step_06_validation.py` | ~500 | Obsoleto - renombrado a step_04 |

**Resultado:** -2,131 líneas eliminadas

### Archivos activos en /ui

```
✅ step_00_client_info.py     - Formulario de datos del cliente
✅ step_01_backup.py           - Advertencia de backup
✅ step_02_wstd.py             - Diagnóstico White Standard
✅ step_04_validation.py       - Validación del alineamiento
✅ step_05_baseline_alignment.py - Alineamiento de baseline
✅ sidebar.py                  - Navegación con progreso
✅ utilities.py                - Conversión .ref → .csv
✅ test_step_04_checkpoints.py - Checkpoints de mantenimiento
```

---

## 🔍 ANÁLISIS DE DUPLICACIÓN (POR PRIORIDAD)

### 1. 🔴 PÁGINAS 4 & 5 - DUPLICACIÓN EXTREMA (95%)

**PRIORIDAD: CRÍTICA** | **Ahorro: ~1,700 líneas** | **Fase: 4**

#### Archivos afectados
- `pages/4_🔍_Comparacion_Espectros.py` (39,089 bytes)
- `pages/5_⚪_White_Reference_Comparison.py` (42,960 bytes)

#### Problema
Ambas páginas son **prácticamente idénticas** (95% del código duplicado). Solo difieren en:
- Título y subtítulo (2 líneas)
- Configuración de Matriz RMS: escala relativa vs absoluta (50 líneas)
- Evaluación automática en página 5 (30 líneas)

#### Arquitectura compartida

```python
1️⃣ Carga múltiple de TSV (sidebar con file_uploader)
2️⃣ Selección de filas con data_editor + checkboxes
3️⃣ Agrupamiento opcional de réplicas (promedio por ID)
4️⃣ Sistema de confirmación (5 botones: ✅❌🔄✔️🗑️)
5️⃣ 4 tabs: Overlay | Residuales | Estadísticas | Matriz RMS
6️⃣ Control de visibilidad de trazas (checkbox por espectro)
```

#### Código 100% duplicado

| Componente | Líneas | % |
|------------|--------|---|
| **CSS Sidebar** (estilos Buchi completos) | ~200 | 100% |
| **Sistema selección de filas** (data_editor + session_state) | ~800 | 100% |
| **Funciones procesamiento** (validate, calculate_stats, residuals) | ~150 | 100% |
| **Visualizaciones Plotly** (overlay, residuals, heatmaps) | ~300 | 100% |
| **Estructura de tabs** (4 tabs completas) | ~200 | 100% |
| **TOTAL** | **~1,650** | **95%** |

#### Solución propuesta

```python
# Crear módulo compartido
/pages/shared/spectrum_comparison_base.py (NUEVO ~1,600 líneas)

class SpectrumComparisonApp:
    """Aplicación base para comparación de espectros NIR"""
    
    def __init__(self, config: dict):
        self.title = config['title']
        self.subtitle = config['subtitle']
        self.use_absolute_rms = config.get('use_absolute_rms', False)
        self.enable_evaluation = config.get('enable_evaluation', False)
        self.rms_thresholds = config.get('rms_thresholds', None)
    
    # ===== MÉTODOS COMPARTIDOS (1,500 líneas) =====
    
    # Validación y procesamiento
    def validate_spectra_compatibility(self, spectra_list)
    def calculate_statistics(self, spectra_list, names)
    def calculate_residuals(self, spectra_list, reference_idx)
    def calculate_correlation_matrix(self, spectra_list, names)
    
    # Visualizaciones Plotly
    def create_overlay_plot(self, spectra_list, names, visible_spectra)
    def create_residuals_plot(self, spectra_list, names, reference_idx, visible_spectra)
    def create_residuals_heatmap(self, spectra_list, names)
    
    # UI Components
    def render_header(self)
    def render_file_uploader_section(self)
    def render_row_selector_section(self, all_data)
    def render_tabs(self, selected_spectra, spectrum_labels)
    
    # Template method (flujo principal)
    def main(self):
        self.render_header()
        
        # Carga de archivos
        uploaded_files = self.render_file_uploader_section()
        if not uploaded_files:
            return
        
        # Procesamiento
        all_data = self.load_and_process_files(uploaded_files)
        selected_spectra, spectrum_labels = self.render_row_selector_section(all_data)
        
        # Validación
        is_valid, msg = self.validate_spectra_compatibility(selected_spectra)
        if not is_valid:
            st.error(msg)
            return
        
        # Tabs principales
        self.render_tabs(selected_spectra, spectrum_labels)
    
    # ===== MÉTODO CUSTOMIZABLE POR SUBCLASE =====
    def create_rms_heatmap_custom(self, spectra_list, names):
        """Override en subclases para escala relativa vs absoluta"""
        if self.use_absolute_rms:
            return self._create_absolute_rms_heatmap(
                spectra_list, names, self.rms_thresholds
            )
        else:
            return self._create_relative_rms_heatmap(spectra_list, names)
```

```python
# PÁGINA 4: Wrapper minimalista (~50 líneas)
# pages/4_Comparacion_Espectros.py

import streamlit as st
from pages.shared.spectrum_comparison_base import SpectrumComparisonApp

# Configuración específica
config = {
    'title': "📊 NIR Spectrum Comparison Tool",
    'subtitle': "Herramienta de comparación de espectros NIR - COREF Suite",
    'use_absolute_rms': False,  # Escala relativa
    'enable_evaluation': False
}

# Ejecutar aplicación
app = SpectrumComparisonApp(config)
app.main()
```

```python
# PÁGINA 5: Wrapper minimalista (~80 líneas)
# pages/5_White_Reference_Comparison.py

import streamlit as st
from pages.shared.spectrum_comparison_base import SpectrumComparisonApp

# Configuración específica para white references
config = {
    'title': "📊 NIR White Standard Comparison Tool",
    'subtitle': "Herramienta de comparación de Baseline",
    'use_absolute_rms': True,  # Escala absoluta con umbrales fijos
    'enable_evaluation': True,  # Evaluación automática ✅/⚠️/❌
    'rms_thresholds': {
        'excellent': 0.002,
        'good': 0.005,
        'acceptable': 0.01,
        'max': 0.015
    }
}

# Ejecutar aplicación
app = SpectrumComparisonApp(config)
app.main()
```

#### Impacto

```
📊 ANTES:
  - pages/4_*.py: 39,089 bytes
  - pages/5_*.py: 42,960 bytes
  - TOTAL: ~82KB (3,400 líneas)

📉 DESPUÉS:
  - pages/shared/spectrum_comparison_base.py: ~1,600 líneas (NUEVO)
  - pages/4_*.py: ~50 líneas (wrapper)
  - pages/5_*.py: ~80 líneas (wrapper)
  - TOTAL: ~1,730 líneas

✅ AHORRO NETO: ~1,670 líneas (-49%)
```

**Beneficios adicionales:**
- ✅ Mantenibilidad: Bugs se corrigen una sola vez
- ✅ Escalabilidad: Fácil añadir nuevos tipos de comparación
- ✅ Testing: Test suite único para toda la lógica compartida
- ✅ Consistencia: UI idéntica garantizada

---

### 2. 🔴 REPORT GENERATORS - DUPLICACIÓN ALTA (60%)

**PRIORIDAD: ALTA** | **Ahorro: ~400-600 líneas** | **Fase: 2**

#### Archivos afectados
- `core/report_generator.py` (~600 líneas)
- `core/offset_adjustment_report_generator.py` (~550 líneas)
- `core/validation_kit_report_generator.py` (~500 líneas)

#### Duplicación detectada (100% idéntica)

| Componente | Líneas |
|------------|--------|
| CSS Buchi corporativo | ~150 |
| Estructura HTML base (header, body, footer) | ~100 |
| Sidebar navegable con anchors | ~80 |
| Secciones expandibles con Plotly | ~60 |
| Footer con timestamp | ~30 |
| Tarjetas de métricas | ~40 |
| **TOTAL** | **~460** |

#### Solución propuesta

```python
# core/base_report_generator.py (NUEVO ~400 líneas)

from abc import ABC, abstractmethod
from datetime import datetime
import plotly.graph_objects as go

class AbstractReportGenerator(ABC):
    """Clase base abstracta para todos los generadores de informes HTML"""
    
    # ===== MÉTODOS CONCRETOS (COMPARTIDOS) =====
    
    def _load_buchi_css(self) -> str:
        """CSS corporativo BUCHI (verde #64B445)"""
        return """
        <style>
            :root {
                --buchi-green: #64B445;
                --buchi-dark-green: #4a8533;
                --buchi-light-green: #e8f5e0;
            }
            body { font-family: 'Segoe UI', Arial, sans-serif; }
            .metric-card { ... }
            .sidebar { ... }
            /* ~150 líneas de CSS */
        </style>
        """
    
    def _start_html_document(self, title: str) -> str:
        """Cabecera HTML con meta tags y CSS"""
        return f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            {self._load_buchi_css()}
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        </head>
        <body>
        """
    
    def _generate_sidebar(self, sections: list[dict]) -> str:
        """Sidebar navegable con anchors a secciones"""
        html = '<div class="sidebar"><nav><ul>'
        for section in sections:
            html += f'<li><a href="#{section["id"]}">{section["title"]}</a></li>'
        html += '</ul></nav></div>'
        return html
    
    def _wrap_chart_in_expandable(self, chart_html: str, title: str, 
                                   section_id: str, expanded: bool = False) -> str:
        """Envuelve un gráfico Plotly en sección expandible"""
        expanded_class = "expanded" if expanded else ""
        return f"""
        <div class="expandable-section {expanded_class}" id="{section_id}">
            <h3 class="section-title" onclick="toggleSection('{section_id}')">
                {title} <span class="toggle-icon">▼</span>
            </h3>
            <div class="section-content">
                {chart_html}
            </div>
        </div>
        """
    
    def _format_metric_card(self, label: str, value: str, 
                           status: str = "neutral") -> str:
        """Tarjeta de métrica con color según status"""
        status_colors = {
            "good": "var(--buchi-green)",
            "warning": "#ffa500",
            "bad": "#dc3545",
            "neutral": "#6c757d"
        }
        color = status_colors.get(status, status_colors["neutral"])
        
        return f"""
        <div class="metric-card" style="border-left: 4px solid {color}">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """
    
    def _generate_footer(self) -> str:
        """Footer con timestamp y logo BUCHI"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"""
        <footer class="report-footer">
            <p>Generado: {timestamp}</p>
            <p>COREF Suite v1.0 | BUCHI NIR-Online</p>
        </footer>
        </body>
        </html>
        """
    
    # ===== TEMPLATE METHOD (FLUJO COMÚN) =====
    
    def generate_report(self, **kwargs) -> str:
        """Template method: define el flujo de generación del informe"""
        
        # 1. Iniciar documento
        html = self._start_html_document(self._get_report_title())
        
        # 2. Sidebar
        sections = self._get_sections()
        html += self._generate_sidebar(sections)
        
        # 3. Contenido principal
        html += '<div class="main-content">'
        html += self._generate_executive_summary(**kwargs)
        html += self._generate_main_analysis(**kwargs)
        html += self._generate_recommendations(**kwargs)
        html += '</div>'
        
        # 4. Footer
        html += self._generate_footer()
        
        return html
    
    # ===== MÉTODOS ABSTRACTOS (CADA SUBCLASE IMPLEMENTA) =====
    
    @abstractmethod
    def _get_report_title(self) -> str:
        """Título del informe"""
        pass
    
    @abstractmethod
    def _get_sections(self) -> list[dict]:
        """Lista de secciones para el sidebar"""
        pass
    
    @abstractmethod
    def _generate_executive_summary(self, **kwargs) -> str:
        """Resumen ejecutivo con métricas clave"""
        pass
    
    @abstractmethod
    def _generate_main_analysis(self, **kwargs) -> str:
        """Análisis principal con gráficos"""
        pass
    
    @abstractmethod
    def _generate_recommendations(self, **kwargs) -> str:
        """Recomendaciones y conclusiones"""
        pass
```

```python
# core/validation_kit_report_generator.py (REFACTORIZADO ~150 líneas)

from core.base_report_generator import AbstractReportGenerator

class ValidationKitReportGenerator(AbstractReportGenerator):
    """Generador de informes de validación de kit"""
    
    def _get_report_title(self) -> str:
        return "Informe de Validación de Kit NIR"
    
    def _get_sections(self) -> list[dict]:
        return [
            {"id": "summary", "title": "Resumen Ejecutivo"},
            {"id": "spectra", "title": "Análisis Espectral"},
            {"id": "validation", "title": "Validación de Muestras"},
            {"id": "recommendations", "title": "Recomendaciones"}
        ]
    
    def _generate_executive_summary(self, **kwargs) -> str:
        kit_data = kwargs.get('kit_data')
        validation_data = kwargs.get('validation_data')
        
        html = '<section id="summary"><h2>Resumen Ejecutivo</h2>'
        
        # Métrica RMS
        rms = validation_data.get('rms', 0)
        status = "good" if rms < 0.002 else "warning" if rms < 0.005 else "bad"
        html += self._format_metric_card("RMS Global", f"{rms:.6f}", status)
        
        # Más métricas...
        html += '</section>'
        return html
    
    def _generate_main_analysis(self, **kwargs) -> str:
        # Lógica específica de validación con gráficos Plotly
        ...
    
    def _generate_recommendations(self, **kwargs) -> str:
        # Recomendaciones específicas según resultados
        ...
```

#### Impacto

```
📊 ANTES:
  - 3 archivos con ~1,650 líneas totales
  - ~460 líneas duplicadas en cada uno

📉 DESPUÉS:
  - base_report_generator.py: ~400 líneas (NUEVO)
  - validation_kit_report_generator.py: ~150 líneas
  - offset_adjustment_report_generator.py: ~150 líneas
  - report_generator.py: ~150 líneas
  - TOTAL: ~850 líneas

✅ AHORRO NETO: ~800 líneas (-48%)
```

---

### 3. 🔴 PÁGINAS 2 & 3 - DUPLICACIÓN ALTA (80%)

**PRIORIDAD: ALTA** | **Ahorro: ~800-1,000 líneas** | **Fase: 4**

#### Archivos afectados
- `pages/2_🎯_Validation_Standards.py` (45,577 bytes)
- `pages/3_🎚️_Offset_Adjustment.py` (56,774 bytes)

#### Arquitectura compartida

```python
1️⃣ Carga de TSV (referencia + actual)
2️⃣ Selección de estándares (data_editor interactivo + botones)
3️⃣ Análisis/Configuración
4️⃣ Visualización con Plotly (overlay + diferencias)
5️⃣ Generación de informe HTML
```

#### Código duplicado

| Componente | Duplicación | Líneas |
|------------|-------------|--------|
| `find_common_ids()` | 100% | ~30 |
| `validate_standard()` | 100% | ~40 |
| Interfaz selección (data_editor + botones) | 100% | ~500 |
| Carga archivos TSV | 100% | ~80 |
| Visualizaciones Plotly | 90% | ~200 |
| Generación informes HTML | 80% | ~150 |
| **TOTAL** | | **~1,000** |

#### Solución propuesta

```python
# ui/validation_commons.py (NUEVO ~600 líneas)

def find_common_ids(df_ref: pd.DataFrame, df_new: pd.DataFrame) -> list:
    """Encuentra IDs comunes entre dos dataframes de espectros"""
    ...

def validate_standard(ref_spectrum: np.ndarray, new_spectrum: np.ndarray, 
                     thresholds: dict) -> dict:
    """Valida un estándar comparando espectros"""
    ...

def render_standards_upload_section() -> tuple:
    """Renderiza sección de carga de TSV (ref + actual)"""
    ...

def render_standards_selection_ui(df: pd.DataFrame, spectral_cols: list) -> list:
    """
    Renderiza interfaz de selección con:
    - data_editor con checkboxes
    - Botones: Todos/Ninguno/Invertir/Confirmar
    - Manejo de session_state
    """
    ...

def create_overlay_plot(ref: np.ndarray, new: np.ndarray, 
                       spectral_cols: list) -> go.Figure:
    """Gráfico overlay con espectros superpuestos"""
    ...

def create_global_statistics_table(validation_results: list) -> pd.DataFrame:
    """Tabla de estadísticas globales (correlación, RMS, max_diff)"""
    ...

def render_report_generation_form() -> dict:
    """Formulario para metadatos del informe (sensor, cliente, técnico)"""
    ...
```

```python
# Páginas 2 y 3 importan funciones comunes
from ui.validation_commons import (
    find_common_ids,
    validate_standard,
    render_standards_upload_section,
    render_standards_selection_ui,
    create_overlay_plot,
    render_report_generation_form
)
```

#### Diferencias específicas
- **Página 2:** Validación con umbrales, análisis regiones críticas
- **Página 3:** Simulación offset, comparación pre/post ajuste

**Ahorro estimado:** ~800-1,000 líneas

---

### 4. 🟡 UI COMPONENTS - DUPLICACIÓN MEDIA

**PRIORIDAD: MEDIA** | **Ahorro: ~650 líneas** | **Fase: 4**

#### Archivos afectados
- `ui/step_02_wstd.py` (12KB)
- `ui/step_04_validation.py` (21KB)
- Todos los steps (navegación)

#### Duplicación detectada

| Componente | Duplicación | Archivos |
|------------|-------------|----------|
| Selección filas TSV (data_editor) | 100% | step_02, step_04, pages 2/3 |
| Agrupamiento por ID (mean) | 100% | step_02, step_04, pages 2/3 |
| Visualización Plotly (subplots) | 80% | step_02, step_04, utils/plotting |
| Botones navegación | 100% | Todos los steps |
| Sistema unsaved_changes | 100% | Todos los steps |

#### Solución propuesta

```python
# ui/shared/tsv_processor.py (NUEVO ~300 líneas)

def load_and_select_tsv_rows(
    label: str,
    key: str,
    help_text: str = None
) -> tuple[pd.DataFrame, list]:
    """
    Carga TSV y permite seleccionar filas con data_editor
    
    Returns:
        (df_selected, indices): DataFrame seleccionado y sus índices
    """
    ...

def group_spectra_by_id(df: pd.DataFrame, spectral_cols: list) -> pd.DataFrame:
    """Agrupa espectros por ID (promedio)"""
    ...

def plot_spectra_comparison_subplot(
    ref: np.ndarray, 
    new: np.ndarray, 
    diff: np.ndarray,
    title: str
) -> go.Figure:
    """Subplots: espectros + diferencias"""
    ...
```

```python
# ui/shared/navigation.py (NUEVO ~100 líneas)

def render_step_navigation(
    current_step: int,
    can_proceed: bool = True,
    unsaved_changes: bool = False
):
    """
    Botones de navegación estándar:
    [⬅️ Anterior] [Siguiente ➡️]
    """
    ...
```

**Ahorro estimado:** ~400-500 líneas

---

### 5. 🟡 UTILS PLOTTING - TRIPLE DUPLICACIÓN

**PRIORIDAD: MEDIA** | **Ahorro: ~300 líneas** | **Fase: 5**

#### Archivos afectados
- `utils/plotting.py` (12KB) - GRUPO 1
- `utils/prediction_charts.py` (16KB) - GRUPO 2
- `utils/prediction_reports.py` (28KB) - GRUPO 2
- `utils/control_samples.py` (15KB) ❌ **OBSOLETO**

#### Duplicación detectada

**Patrón común (100% idéntico):**
```python
# En los 3 archivos activos:
fig = make_subplots(rows=X, cols=Y, subplot_titles=(...))
fig.add_trace(go.Scatter(...), row=R, col=C)
fig.update_layout(template='plotly_white', height=600)
```

**Configuración compartida:**
- Colores corporativos: `['#1f77b4', '#ff7f0e', '#2ca02c', ...]`
- Hovertemplates con mismo formato
- Template 'plotly_white' en todos

#### Solución propuesta

**Opción 1: Consolidar en módulo base**
```python
# utils/plotting_base.py (NUEVO)
def create_subplot_figure(rows, cols, titles, ...):
    """Factory para crear subplots consistentes"""
    ...

def add_spectrum_trace(fig, spectrum, name, color, ...):
    """Añade traza espectral con configuración estándar"""
    ...

BUCHI_COLORS = ['#1f77b4', '#ff7f0e', ...]
```

**Opción 2: Mantener separados**
- `plotting.py`: Espectros NIR (GRUPO 1)
- `prediction_charts.py` + `prediction_reports.py`: Predicciones (GRUPO 2)

**Recomendación:** Opción 2 + eliminar `control_samples.py`

**Ahorro estimado:** ~300 líneas (principalmente `control_samples.py`)

---

### 6. 🟡 PARSERS HTML - DUPLICACIÓN MEDIA (GRUPO 2)

**PRIORIDAD: MEDIA** | **Ahorro: ~200 líneas** | **Fase: 3**

#### Archivos afectados (GRUPO 2 - Pendiente audit completo)
- `modules/consolidator/parsers/baseline_parser.py`
- `modules/consolidator/parsers/predictions_parser.py`
- `modules/consolidator/parsers/validation_parser.py`

#### Duplicación detectada

| Método | Duplicación |
|--------|-------------|
| `_extract_plotly_charts()` | 100% idéntico en los 3 |
| `__init__` + BeautifulSoup | 90% similar |
| Extracción de tablas HTML | 80% similar |
| `get_summary()` | Misma lógica, campos diferentes |

#### Solución propuesta

```python
# modules/consolidator/parsers/base_parser.py (NUEVO)

from abc import ABC, abstractmethod
from bs4 import BeautifulSoup

class AbstractParser(ABC):
    """Clase base para parsers de informes HTML"""
    
    def __init__(self, html_content: str):
        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.charts = self._extract_plotly_charts()
    
    def _extract_plotly_charts(self) -> list:
        """Extrae gráficos Plotly (100% compartido)"""
        ...
    
    def _extract_table_data(self, table_id: str) -> pd.DataFrame:
        """Extrae datos de tabla HTML"""
        ...
    
    @abstractmethod
    def _parse_sections(self) -> dict:
        """Parsea secciones específicas del informe"""
        pass
    
    @abstractmethod
    def get_summary(self) -> dict:
        """Genera resumen del informe"""
        pass
```

**⚠️ IMPORTANTE:** Requiere modificar `pages/07_MetaReports.py` (refactoring atómico)

**Ahorro estimado:** ~200 líneas

---

### ✅ CORE MODULES - SIN DUPLICACIÓN

**file_handlers.py** (142 líneas) ✅  
**spectral_processing.py** (96 líneas) ✅

**Funciones exportadas:**
```python
# file_handlers.py
load_tsv_file(file) → pd.DataFrame
get_spectral_columns(df) → list
load_ref_file(file) → (header, spectrum)
load_csv_baseline(file) → (df, spectrum)
export_ref_file(spectrum, header) → bytes
export_csv_file(spectrum, df_baseline) → str

# spectral_processing.py
group_measurements_by_lamp(df, ...) → (df_ref, df_new)
find_common_samples(df_ref, df_new) → pd.Index
calculate_spectral_correction(df_ref, df_new, ids) → np.array
apply_baseline_correction(baseline, correction) → np.array
simulate_corrected_spectra(df_new, ...) → pd.DataFrame
```

**Análisis:**
- ✅ Funciones puras sin efectos secundarios
- ✅ Responsabilidad única y clara
- ✅ Usadas extensivamente en todo el proyecto
- ✅ Bien diseñadas - **NO REQUIEREN REFACTORING**

---

## 📊 RESUMEN DEL AUDIT COMPLETO

### Estado por grupo

| Grupo | Estado | Archivos | Líneas | Duplicación |
|-------|--------|----------|--------|-------------|
| **GRUPO 1** | ✅ 100% Auditado | 24 archivos | ~15,000 | ~4,750 (31.7%) |
| **GRUPO 2** | ⏳ Pendiente | ~6 archivos | ~2,869 | ~200 (estimado) |
| **TOTAL** | | 30 archivos | ~17,869 | ~4,950 (27.7%) |

### Duplicación por categoría (GRUPO 1)

| # | Categoría | Archivos | Líneas Dup. | % Total | Prioridad |
|---|-----------|----------|-------------|---------|-----------|
| 1 | Páginas 4 & 5 | 2 | ~1,700 | 9.5% | 🔴 CRÍTICA |
| 2 | Report Generators | 3 | ~1,200 | 6.7% | 🔴 ALTA |
| 3 | Páginas 2 & 3 | 2 | ~900 | 5.0% | 🔴 ALTA |
| 4 | UI Components | ~8 | ~650 | 3.6% | 🟡 MEDIA |
| 5 | Utils Plotting | 3 | ~300 | 1.7% | 🟡 MEDIA |
| | **TOTAL GRUPO 1** | | **~4,750** | **26.6%** | |

### Archivos sin duplicación (excelentes)

```
✅ core/file_handlers.py (142 líneas)
✅ core/spectral_processing.py (96 líneas)
✅ ui/sidebar.py (navegación única)
✅ ui/step_00_client_info.py
✅ ui/step_01_backup.py
✅ ui/test_step_04_checkpoints.py
✅ utils/nir_analyzer.py (parser XML)
✅ utils/validators.py
```

### Archivos obsoletos detectados

```
❌ utils/control_samples.py (14,644 bytes)
   → Sustituido por prediction_reports.py
   → ELIMINAR en Fase 5
```

---

## 🎯 ROADMAP DE REFACTORING

### Visión general

```
Fase 1 ✅ → Fase 2 → Fase 3 → Fase 4 → Fase 5 → Fase 6
Limpieza  Report   Parsers   Pages    Utils    Docs
          Generators (GRUPO2) (GRUPO1)
```

### Fase 1: ✅ COMPLETADA - Limpieza
- ✅ Eliminar 4 archivos obsoletos de /ui
- ✅ Reducción: -2,131 líneas
- ✅ Commit: `0088199`

---

### Fase 2: Report Generators (GRUPO 1)

**Tiempo:** 3-4 horas | **Complejidad:** Media | **Impacto:** Alto  
**Ahorro:** ~800 líneas | **Coste:** ~$1.50

#### Pasos
1. Crear `core/base_report_generator.py` (~400 líneas)
   - Implementar `AbstractReportGenerator`
   - Métodos compartidos: CSS, sidebar, footer, métricas
   - Template method: `generate_report()`

2. Refactorizar `core/report_generator.py`
   - Heredar de `AbstractReportGenerator`
   - Implementar métodos abstractos
   - Testing manual

3. Refactorizar `core/offset_adjustment_report_generator.py`
   - Heredar de `AbstractReportGenerator`
   - Implementar métodos abstractos
   - Testing manual

4. Refactorizar `core/validation_kit_report_generator.py`
   - Heredar de `AbstractReportGenerator`
   - Implementar métodos abstractos
   - Testing manual

5. Testing completo
   - Generar informes de validación
   - Generar informes de offset
   - Comparar HTML con versión anterior

6. Commit: `"Refactor: Abstract base for report generators"`

#### Archivos afectados
- **Nuevos:** 1 (`core/base_report_generator.py`)
- **Modificados:** 3 (generators)
- **Eliminados:** 0
- **Páginas que usan:** 1, 2, 3

---

### Fase 3: Parsers HTML (GRUPO 2)

**Tiempo:** 2-3 horas | **Complejidad:** Media | **Impacto:** Medio  
**Ahorro:** ~200 líneas | **Coste:** ~$0.80

**⚠️ REFACTORING ATÓMICO REQUERIDO**

#### Pasos
1. Crear `modules/consolidator/parsers/base_parser.py`
   - Implementar `AbstractParser`
   - Método compartido: `_extract_plotly_charts()`
   - Métodos abstractos: `_parse_sections()`, `get_summary()`

2. Refactorizar 3 parsers → heredar de base
   - `baseline_parser.py`
   - `predictions_parser.py`
   - `validation_parser.py`

3. **Modificar `pages/07_MetaReports.py`**
   - Actualizar imports
   - Adaptar a nueva API de parsers
   - Testing exhaustivo

4. Testing completo del consolidator
   - Cargar múltiples informes
   - Verificar extracción de gráficos
   - Verificar resúmenes

5. Commit: `"Refactor: Abstract base for HTML parsers"`

#### Archivos afectados
- **Nuevos:** 1 (`base_parser.py`)
- **Modificados parsers:** 3
- **Modificados pages:** 1 (`07_MetaReports.py`)

---

### Fase 4: Pages & UI Components (GRUPO 1)

**Tiempo:** 5-7 horas | **Complejidad:** Alta | **Impacto:** Muy Alto  
**Ahorro:** ~3,350 líneas | **Coste:** ~$2.00

#### Sub-fase 4A: Páginas 4 & 5 (PRIORIDAD CRÍTICA)

**Tiempo:** 3-4 horas | **Ahorro:** ~1,700 líneas

1. Crear `/pages/shared/spectrum_comparison_base.py`
   - Implementar clase `SpectrumComparisonApp`
   - Migrar todas las funciones comunes
   - Testing exhaustivo

2. Refactorizar `pages/4_Comparacion_Espectros.py`
   - Convertir a wrapper (~50 líneas)
   - Configuración: escala relativa

3. Refactorizar `pages/5_White_Reference_Comparison.py`
   - Convertir a wrapper (~80 líneas)
   - Configuración: escala absoluta + evaluación

4. Testing completo
   - Carga múltiple de TSV
   - Selección de filas
   - Agrupamiento de réplicas
   - 4 tabs funcionales
   - Matrices RMS (relativa vs absoluta)

5. Commit: `"Refactor: Unified spectrum comparison base (pages 4 & 5)"`

#### Sub-fase 4B: Páginas 2 & 3

**Tiempo:** 2-3 horas | **Ahorro:** ~900 líneas

1. Crear `ui/validation_commons.py`
   - Funciones compartidas de validación
   - Selección de estándares (data_editor)
   - Visualizaciones comunes

2. Refactorizar páginas 2 y 3
   - Importar desde `validation_commons`
   - Mantener lógica específica

3. Testing
   - Validación de estándares
   - Offset adjustment
   - Generación de informes

4. Commit: `"Refactor: Extract validation commons (pages 2 & 3)"`

#### Sub-fase 4C: UI Components

**Tiempo:** 1-2 horas | **Ahorro:** ~650 líneas

1. Crear `ui/shared/tsv_processor.py`
   - `load_and_select_tsv_rows()`
   - `group_spectra_by_id()`

2. Crear `ui/shared/navigation.py`
   - `render_step_navigation()`

3. Refactorizar steps que usan TSV
   - step_02, step_04
   - Importar funciones compartidas

4. Commit: `"Refactor: Shared UI components for TSV processing and navigation"`

---

### Fase 5: Utils Cleanup

**Tiempo:** 1-2 horas | **Complejidad:** Baja | **Impacto:** Medio  
**Ahorro:** ~300 líneas | **Coste:** ~$0.50

#### Pasos
1. Eliminar `utils/control_samples.py` (obsoleto)
   - Verificar que no se usa en ningún sitio
   - Commit: `"Remove obsolete control_samples.py"`

2. (Opcional) Consolidar funciones de plotting
   - Evaluar si vale la pena
   - O mantener separados (propósitos diferentes)

3. Verificar imports no utilizados
   - Revisar todos los archivos

---

### Fase 6: Documentación

**Tiempo:** 2-3 horas | **Complejidad:** Baja  
**Coste:** ~$0.50

#### Tareas
1. Actualizar `README.md`
   - Arquitectura GRUPO 1 vs GRUPO 2
   - Estructura de módulos
   - Flujo de trabajo

2. Docstrings en clases principales
   - `AbstractReportGenerator`
   - `AbstractParser`
   - `SpectrumComparisonApp`

3. Comentarios en código complejo
   - Algoritmos espectrales
   - Lógica de validación

4. Guía de uso para técnicos
   - Screenshots de UI
   - Casos de uso típicos

5. Commit: `"Docs: Complete documentation update"`

---

## 💰 ESTIMACIÓN DE COSTES (Continue API)

### Por fase

| Fase | Descripción | Sonnet | Haiku | Coste |
|------|-------------|--------|-------|-------|
| 1 ✅ | Limpieza | 0 | 0 | $0.00 |
| 2 | Report Generators | 5-8 | 15-20 | $1.50 |
| 3 | Parsers HTML | 3-5 | 10-15 | $0.80 |
| 4A | Páginas 4 & 5 | 4-6 | 15-20 | $1.20 |
| 4B | Páginas 2 & 3 | 2-4 | 10-15 | $0.80 |
| 4C | UI Components | 1-2 | 8-12 | $0.40 |
| 5 | Utils Cleanup | 1-2 | 5-8 | $0.30 |
| 6 | Documentación | 0-1 | 10-15 | $0.30 |
| | **TOTAL** | **16-28** | **73-105** | **~$5.30** |

### Budget

```
💰 Disponible:   $6.05
📊 Estimado:     $5.30
✅ Sobrante:     $0.75
```

**Contingencia:** 12% del budget disponible

---

## 📊 MÉTRICAS OBJETIVO

### Estado actual (Post Fase 1)

```
📏 Líneas totales:        17,869
📁 Archivos Python:       43
🔄 Código duplicado:      ~4,950 líneas (27.7%)
🏗️ Arquitectura:          Grupo 1 coherente, Grupo 2 ad-hoc
📝 Documentación:         Limitada
✅ Tests:                  Ninguno (testing manual)
```

### Estado objetivo (Post refactoring completo)

```
📏 Líneas totales:        12,900-13,500 (-28%)
📁 Archivos Python:       48 (+5 nuevos módulos base)
🔄 Código duplicado:      ~200-300 líneas (-94%)
🏗️ Arquitectura:          Coherente con clases base
📝 Documentación:         Completa (README + docstrings)
✅ Tests:                  Manual (estrategia para v2.0)
```

### Impacto por fase

| Fase | Antes | Después | Ahorro | % |
|------|-------|---------|--------|---|
| 1 ✅ | 20,000 | 17,869 | -2,131 | -11% |
| 2 | 17,869 | 17,069 | -800 | -4% |
| 3 | 17,069 | 16,869 | -200 | -1% |
| 4A | 16,869 | 15,169 | -1,700 | -10% |
| 4B | 15,169 | 14,269 | -900 | -6% |
| 4C | 14,269 | 13,619 | -650 | -5% |
| 5 | 13,619 | 13,319 | -300 | -2% |
| **Total** | **20,000** | **~13,300** | **-6,700** | **-33%** |

### Beneficios esperados

**Cuantitativos:**
- ✅ -6,700 líneas de código (-33%)
- ✅ -94% de duplicación
- ✅ +5 módulos base reutilizables
- ✅ 48 archivos bien organizados

**Cualitativos:**
- ✅ **Mantenibilidad:** Bugs se corrigen una vez
- ✅ **Escalabilidad:** Fácil añadir nuevas funcionalidades
- ✅ **Testability:** Módulos base son testeables
- ✅ **Consistencia:** UI uniforme garantizada
- ✅ **Legibilidad:** Código más limpio y organizado
- ✅ **Onboarding:** Más fácil para nuevos desarrolladores

---

## 🚀 DECISIONES PENDIENTES

### Para v1.0 (Post-refactoring)

- [ ] **¿Refactorizar GRUPO 2 para seguir patrón de GRUPO 1?**
  - Pros: Arquitectura unificada, mejor mantenibilidad
  - Contras: Tiempo adicional (~5-8 horas)
  - Decisión: Evaluar después de Fase 6

- [ ] **¿Mantener separación GRUPO 1 / GRUPO 2?**
  - Actual: Separados (coherente vs ad-hoc)
  - Opción: Integrar ambos bajo arquitectura común
  - Decisión: Mantener separados por ahora

- [ ] **¿Crear módulo común de estilos Buchi?**
  - Actualmente: CSS duplicado en reportes + páginas
  - Propuesta: `/core/buchi_styles.py` con constantes
  - Decisión: Considerar en Fase 2

### Para v2.0 (Futuro)

- [ ] **Unificar arquitectura completa**
  - GRUPO 1 + GRUPO 2 bajo misma estructura
  - Migrar GRUPO 2 a seguir patrones de GRUPO 1

- [ ] **Sistema de plugins para nuevas páginas**
  - Plugin API para extensiones
  - Hot-reload de módulos

- [ ] **Tests unitarios**
  - pytest para módulos core
  - Coverage >80%

- [ ] **CI/CD Pipeline**
  - GitHub Actions
  - Tests automáticos
  - Linting (black, flake8)

- [ ] **Logging estructurado**
  - Logs de errores
  - Tracking de uso

---

## 📝 NOTAS FINALES

### Prioridades establecidas

1. **🔴 CRÍTICO:** Páginas 4 & 5 (95% duplicadas, ~1,700 líneas)
2. **🔴 ALTA:** Report Generators (~1,200 líneas)
3. **🔴 ALTA:** Páginas 2 & 3 (~900 líneas)
4. **🟡 MEDIA:** UI Components (~650 líneas)
5. **🟡 MEDIA:** Utils (~300 líneas)
6. **🟡 MEDIA:** Parsers (~200 líneas)

### Bloqueadores identificados

- ❌ **Ninguno** para GRUPO 1
- ⚠️ **Fase 3 requiere cambio atómico** en `07_MetaReports.py`

### Riesgos

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Romper funcionalidad existente | Alto | Testing exhaustivo manual |
| Introducir nuevos bugs | Medio | Code review + testing |
| Superar budget Continue | Bajo | Monitorizar uso, parar si necesario |
| Incompatibilidad GRUPO 2 | Bajo | GRUPO 2 es independiente |

### Próximos pasos inmediatos

1. ✅ Revisar y aprobar este plan
2. ⏳ Decidir cuál fase ejecutar primero
3. ⏳ Crear branch de desarrollo: `refactor/phase-X`
4. ⏳ Ejecutar fase seleccionada
5. ⏳ Testing manual exhaustivo
6. ⏳ Commit y merge a main

### Recomendaciones

- **Empezar por Fase 4A** (Páginas 4 & 5) - Mayor impacto visual
- **O empezar por Fase 2** (Report Generators) - Más conceptual, establece patrón
- **Hacer commits atómicos** por cada sub-tarea
- **Testing manual exhaustivo** antes de cada commit
- **Documentar cambios** en commit messages

---

**Última actualización:** 21 Diciembre 2024 - 19:00  
**Próxima revisión:** Después de ejecutar Fase 2 o Fase 4A  
**Estado:** ✅ AUDIT COMPLETO GRUPO 1 | ⏳ PENDIENTE GRUPO 2

---

*Documento generado con Claude Sonnet 3.5 (Continue.dev)*