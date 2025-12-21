# COREF Suite - Audit & Refactoring Plan
**Fecha:** 21 Diciembre 2024  
**Líneas totales:** ~17,869 (después de limpieza)

---

## 📊 ESTRUCTURA DEL PROYECTO

### Arquitectura General
```
app.py (router) → Solo navegación Streamlit
│
├── GRUPO 1: Páginas 0-5 (Original, coherente)
│   ├── 0_Home
│   ├── 1_Baseline adjustment
│   ├── 2_Validation_Standards
│   ├── 3_Offset_Adjustment
│   ├── 4_Comparacion_Espectros
│   └── 5_White_Reference_Comparison
│   
│   Usan: /core + /ui + /utils
│
└── GRUPO 2: Páginas 6-8 (Añadidas posteriormente, ad-hoc)
    ├── 6_Prediction_Reports
    ├── 7_MetaReports (consolidator)
    └── 8_TSV_Validation_Reports
    
    Usan: /modules (lógica propia, menos integrado)
```

---

## ✅ LIMPIEZA REALIZADA (Fase 1)

**Commit:** `0088199 - Eliminar scripts ui obsoletos`

**Archivos eliminados:**
- ❌ ui/History/step_05_baseline.py
- ❌ ui/History/step_06_export.py  
- ❌ ui/step_04_baseline_alignment.py
- ❌ ui/step_06_validation.py

**Resultado:** -2,131 líneas eliminadas

**Archivos activos en /ui:**
- ✅ step_00_client_info.py
- ✅ step_01_backup.py
- ✅ step_02_wstd.py
- ✅ step_04_validation.py
- ✅ step_05_baseline_alignment.py
- ✅ sidebar.py
- ✅ utilities.py

---

## 🔍 CÓDIGO DUPLICADO IDENTIFICADO

### 1. Report Generators (/core) - ALTA PRIORIDAD

**Archivos:**
- `core/report_generator.py` (Baseline adjustment)
- `core/offset_adjustment_report_generator.py` (Offset)
- `core/validation_kit_report_generator.py` (Validation kit)

**Duplicación detectada:**
- ✅ CSS Buchi corporativo (idéntico)
- ✅ Sidebar navegable (misma estructura)
- ✅ Secciones expandibles con Plotly (mismo patrón)
- ✅ Resumen ejecutivo + análisis + recomendaciones (lógica similar)
- ✅ Footer con timestamp (idéntico)
- ✅ Tarjetas de métricas (mismo formato)

**Estructura sugerida:**
```python
AbstractReportGenerator (base)
├── ValidationKitReportGenerator
├── OffsetAdjustmentReportGenerator
└── GenericReportGenerator
```

**Métodos comunes a implementar:**
- `_load_buchi_css()`
- `_start_html_document()`
- `_generate_sidebar()`
- `_wrap_chart_in_expandable()`
- `_format_metric_card()`
- `_generate_footer()`

**Métodos abstractos:**
- `_get_report_title()`
- `_generate_executive_summary()`
- `_generate_main_analysis()`
- `_generate_detailed_sections()`
- `_generate_recommendations()`

**Ahorro estimado:** ~400-600 líneas

---

### 2. HTML Parsers (/modules/consolidator/parsers) - ALTA PRIORIDAD

**Archivos:**
- `modules/consolidator/parsers/baseline_parser.py`
- `modules/consolidator/parsers/predictions_parser.py`
- `modules/consolidator/parsers/validation_parser.py`

**Duplicación detectada:**
- ✅ `_extract_plotly_charts()` - IDÉNTICO en los 3
- ✅ Estructura `__init__` + BeautifulSoup
- ✅ Patrón extracción de tablas HTML (80% similar)
- ✅ `get_summary()` - misma lógica, campos diferentes
- ✅ `_determine_status()` - mismo approach (OK/WARNING/FAIL)
- ✅ Regex y limpieza de texto

**Estructura sugerida:**
```python
AbstractParser (base)
├── BaselineParser
├── ValidationParser
└── PredictionsParser
```

**Métodos comunes a implementar:**
- `_extract_plotly_charts()` - 100% reutilizable
- `_extract_table_data(table)` - patrón común
- `_extract_info_box(section_id)` - patrón común
- `get_summary()` - template method

**Métodos abstractos:**
- `_get_report_type()`
- `_parse_sections()`
- `_build_summary()`
- `_determine_status()`

**⚠️ IMPORTANTE:** 
- Refactoring de parsers requiere modificar `pages/07_MetaReports.py`
- Ambos cambios deben hacerse juntos (refactoring atómico)

**Ahorro estimado:** ~200 líneas

---

## 📋 ÁREAS PENDIENTES DE AUDIT

### Por revisar:
- [ ] `/utils` - 6 archivos (plotting, validators, nir_analyzer, etc.)
- [ ] Relación entre páginas 0-5 y módulos `/core` + `/ui`
- [ ] Posible consolidación de funciones de plotting
- [ ] Verificar imports no utilizados

---

## 🎯 ROADMAP DE REFACTORING

### Fase 1: ✅ COMPLETADA - Limpieza
- Eliminar archivos obsoletos
- Reducción de 2,131 líneas

### Fase 2: Report Generators (GRUPO 1)
**Tiempo estimado:** 3-4 horas  
**Complejidad:** Media  
**Impacto:** Alto

**Pasos:**
1. Crear `core/base_report_generator.py`
2. Implementar `AbstractReportGenerator`
3. Refactorizar `report_generator.py` → heredar de base
4. Refactorizar `offset_adjustment_report_generator.py`
5. Refactorizar `validation_kit_report_generator.py`
6. Testing manual de los 3 generadores
7. Commit: "Refactor: Abstract base for report generators"

**Archivos afectados:**
- Nuevos: 1 (`core/base_report_generator.py`)
- Modificados: 3 (generators)
- Páginas que usan: 1, 2, 3

### Fase 3: Parsers (GRUPO 2)
**Tiempo estimado:** 2-3 horas  
**Complejidad:** Media  
**Impacto:** Medio

**⚠️ Refactoring atómico requerido:**

**Pasos:**
1. Crear `modules/consolidator/parsers/base_parser.py`
2. Implementar `AbstractParser`
3. Refactorizar los 3 parsers → heredar de base
4. **Modificar `pages/07_MetaReports.py`** para usar nueva API
5. Testing completo del consolidator
6. Commit: "Refactor: Abstract base for HTML parsers"

**Archivos afectados:**
- Nuevos: 1 (`base_parser.py`)
- Modificados parsers: 3
- Modificados pages: 1 (`07_MetaReports.py`)

### Fase 4: Audit `/utils` (pendiente)
**Tiempo estimado:** 1-2 horas  
**Complejidad:** Baja

**Revisar:**
- Duplicación en funciones de plotting
- Consolidar validators si hay duplicación
- Verificar imports no utilizados

### Fase 5: Documentación
**Tiempo estimado:** 2-3 horas  
**Complejidad:** Baja

**Tareas:**
1. Actualizar README.md con arquitectura GRUPO 1 vs GRUPO 2
2. Docstrings en clases principales
3. Comentarios en código complejo
4. Guía de uso para técnicos

---

## 💰 ESTIMACIÓN DE COSTES (Continue API)

| Fase | Preguntas Sonnet | Preguntas Haiku | Costo |
|------|------------------|-----------------|-------|
| Fase 1 ✅ | 0 | 0 | $0 |
| Fase 2 | 5-8 | 15-20 | $1.50 |
| Fase 3 | 3-5 | 10-15 | $0.80 |
| Fase 4 | 2-3 | 10-12 | $0.50 |
| Fase 5 | 0-1 | 20-30 | $0.50 |
| **TOTAL** | **10-17** | **55-77** | **~$3.30** |

**Budget disponible:** $6.05  
**Sobrante tras refactoring:** ~$2.75

---

## 📊 MÉTRICAS OBJETIVO

### Antes del refactoring:
- Líneas totales: ~17,869
- Archivos Python: 43
- Código duplicado estimado: ~600-800 líneas

### Después del refactoring:
- Líneas totales: ~17,000 (-5%)
- Código duplicado: ~100-200 líneas (-75%)
- Clases base: 2 nuevas (AbstractReportGenerator, AbstractParser)
- Mantenibilidad: ⭐⭐⭐⭐⭐

---

## 🚀 DECISIONES PENDIENTES

### Para v1.0:
- [ ] ¿Refactorizar GRUPO 2 para seguir patrón de GRUPO 1?
- [ ] ¿Mantener separación GRUPO 1 / GRUPO 2?
- [ ] ¿Crear módulo común de estilos Buchi?

### Para v2.0:
- [ ] Unificar arquitectura de ambos grupos
- [ ] Sistema de plugins para nuevas páginas
- [ ] Tests unitarios

---

## 📝 NOTAS

- **Prioridad alta:** Report Generators (más duplicación)
- **Prioridad media:** Parsers (requiere cambio en MetaReports)
- **Bloqueadores:** Ninguno identificado
- **Riesgos:** Cambios en parsers requieren testing exhaustivo de consolidator

---

**Última actualización:** 21 Dic 2024 - Tarde  
**Próximo paso:** Iniciar Fase 2 (Report Generators)