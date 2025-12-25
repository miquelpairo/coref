"""
COREF - Home
============
Baseline Correction Tool Suite
Página principal con navegación a herramientas.

Author: Miquel
Date: 2024
"""

import streamlit as st
from auth import check_password
from buchi_streamlit_theme import apply_buchi_styles

# Aplicar estilos corporativos
apply_buchi_styles()

# Verificación de autenticación
if not check_password():
    st.stop()

# ============================================================================
# PÁGINA HOME
# ============================================================================

st.title("🏠 COREF - Baseline Correction Tool Suite")
st.markdown("### Herramientas de calibración y validación para espectrómetros NIR")

st.divider()

# Descripción general
st.markdown(
    """
**COREF** es un conjunto de herramientas diseñadas para facilitar el mantenimiento 
y validación de equipos NIR (Near-Infrared), especialmente NIR Online con detectores DAD.

Estas aplicaciones ayudan a técnicos de servicio en:
- Ajuste de baseline post-cambio de lámpara
- Validación de estándares ópticos
- Corrección de offset fino
- Comparación y análisis de espectros
- Comparación de predicciones entre lámparas (SX Center)
- Consolidación de informes en un metainforme único
- Generación de informes de validación desde ficheros TSV
"""
)

st.divider()

# Tarjetas de navegación
st.markdown("## 🧰 Herramientas Disponibles")

# ---------------------------------------------------------------------------
# FILA 1 (3 columnas): Baseline | Validation | Offset
# ---------------------------------------------------------------------------
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        """
    <div class="card-container card-blue">
        <h3>📐 Baseline Adjustment</h3>
        <p>Ajuste de baseline tras cambio de lámpara. Calcula correcciones basadas en mediciones 
        de referencia blanca externa.</p>
        <ul>
            <li>Análisis de diferencias espectrales</li>
            <li>Cálculo automático de correcciones</li>
            <li>Corrección de forma espectral</li>
        </ul>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.write("")
    if st.button(
        "🚀 Abrir Baseline Adjustment",
        key="btn_baseline",
        use_container_width=True,
        type="primary",
    ):
        st.switch_page("pages/1_📐_Baseline adjustment.py")

with col2:
    st.markdown(
        """
    <div class="card-container card-red">
        <h3>🎯 Standard Validation</h3>
        <p>Validación automática de estándares ópticos post-mantenimiento mediante emparejamiento por ID.</p>
        <ul>
            <li>Detección automática de IDs comunes</li>
            <li>Validación múltiple simultánea</li>
            <li>Análisis de regiones críticas</li>
            <li>Detección de offset global</li>
        </ul>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.write("")
    if st.button(
        "🚀 Abrir Standard Validation",
        key="btn_validation",
        use_container_width=True,
        type="primary",
    ):
        st.switch_page("pages/2_🎯_Validation_Standards.py")

with col3:
    st.markdown(
        """
    <div class="card-container card-orange">
        <h3>🎚️ Offset Adjustment</h3>
        <p>Ajuste fino de offset vertical al baseline preservando la forma espectral.</p>
        <ul>
            <li>Corrección de bias sistemático</li>
            <li>Simulación con estándares ópticos</li>
            <li>Visualización de impacto</li>
        </ul>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.write("")
    if st.button(
        "🚀 Abrir Offset Adjustment",
        key="btn_offset",
        use_container_width=True,
        type="primary",
    ):
        st.switch_page("pages/3_🎚️_Offset_Adjustment.py")

# ---------------------------------------------------------------------------
# FILA 2 (2 columnas): Spectrum | Predictions
# ---------------------------------------------------------------------------
col4, col5 = st.columns(2)

with col4:
    st.markdown(
        """
    <div class="card-container card-green">
        <h3>🔍 Spectrum Comparison</h3>
        <p>Comparación avanzada de múltiples espectros NIR con análisis estadístico completo.</p>
        <ul>
            <li>Overlay de espectros</li>
            <li>Análisis de residuales y correlación</li>
            <li>Agrupamiento de réplicas</li>
            <li>Modo White Reference integrado</li>
        </ul>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.write("")
    if st.button(
        "🚀 Abrir Spectrum Comparison",
        key="btn_comparison",
        use_container_width=True,
        type="primary",
    ):
        st.switch_page("pages/4_🔍_Comparacion_Espectros.py")

with col5:
    st.markdown(
        """
    <div class="card-container card-teal">
        <h3>📊 Prediction Reports</h3>
        <p>Comparación de predicciones entre lámparas usando informes <strong>XML</strong> generados desde SX Center.</p>
        <ul>
            <li>Cargar reporte XML de SX Center</li>
            <li>Comparar predicciones entre lámparas</li>
            <li>Analizar diferencias por muestra/parámetro</li>
        </ul>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.write("")
    if st.button(
        "🚀 Abrir Prediction Reports",
        key="btn_predictions",
        use_container_width=True,
        type="primary",
    ):
        st.switch_page("pages/6_📊_Prediction_Reports.py")

# ---------------------------------------------------------------------------
# FILA 3 (2 tarjetas centradas): MetaReports | TSV Validation Reports
# ---------------------------------------------------------------------------
sp1, c1, c2, sp2 = st.columns([0.5, 1, 1, 0.5])

with c1:
    st.markdown(
        """
    <div class="card-container card-gray">
        <h3>📦 Report Consolidator</h3>
        <p>Consolida en un <strong>metainforme</strong> único los informes de Baseline, Validación y Predicciones.</p>
        <ul>
            <li>Subir 1-3 informes (HTML/XML según módulo)</li>
            <li>Resumen ejecutivo y estado global</li>
            <li>Navegación lateral e informes embebidos</li>
        </ul>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.write("")
    if st.button(
        "🚀 Abrir Report Consolidator",
        key="btn_metareports",
        use_container_width=True,
        type="primary",
    ):
        st.switch_page("pages/07_📦_MetaReports.py")

with c2:
    st.markdown(
        """
    <div class="card-container card-lime">
        <h3>✅ TSV Validation Reports</h3>
        <p>Genera informes de validación a partir de ficheros <strong>TSV</strong> (journal) y produce un HTML interactivo.</p>
        <ul>
            <li>Cargar uno o varios TSV</li>
            <li>Limpieza y reorganización automática</li>
            <li>Gráficos interactivos y tabla exportable</li>
        </ul>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.write("")
    if st.button(
        "🚀 Abrir TSV Validation Reports",
        key="btn_tsv_validation_reports",
        use_container_width=True,
        type="primary",
    ):
        st.switch_page("pages/08_✅_TSV_Validation_Reports.py")

st.divider()

# Información adicional actualizada
st.markdown(
    """
### 📋 Flujo de trabajo típico

**Workflow completo de mantenimiento:**

1. **Pre-mantenimiento**: 
   - Medir y guardar referencia blanca (TSV)
   - Medir estándares ópticos certificados (TSV)

2. **Cambio de lámpara** en NIR Online
   - Warm-up 15-30 minutos

3. **Baseline Adjustment** (Corrección de forma):
   - Nueva medición de referencia blanca
   - Cálculo de corrección espectral
   - Exportar baseline corregido

4. **Standard Validation** (Detección de offset):
   - Medir mismos estándares ópticos con baseline nuevo
   - Validar correlación, RMS, Max Δ
   - **Detectar offset global del kit**

5. **Offset Adjustment** (Corrección de bias - OPCIONAL):
   - Si offset global > 0.003 AU
   - Simular impacto del offset en estándares
   - Aplicar corrección al baseline
   - Re-exportar baseline final

6. **Prediction Reports (SX Center)**:
   - Cargar informe XML con predicciones
   - Comparar resultados entre lámparas / configuraciones
   - Detectar sesgos y desviaciones por parámetro

7. **MetaReports**:
   - Consolidar Baseline + Validación + Predicciones
   - Generar un informe único con resumen ejecutivo
   - ✅ Documentación completa para cierre de servicio

8. **TSV Validation Reports**:
   - Cargar TSV(s) desde journal / export
   - Generar informes HTML interactivos (parity, residuum, histograma)
   - Exportar CSV limpio para trazabilidad

---

**Herramientas complementarias:**
- **Spectrum Comparison**: Análisis comparativo general con modo White Reference integrado
"""
)

st.divider()

# Footer actualizado
st.markdown(
    """
<div style="text-align: center; color: #666; padding: 20px;">
    <p><strong>COREF Suite</strong> | Versión 2.0 | Desarrollado por MPC</p>
    <p>Para soporte técnico o consultas, contacta con el departamento de servicio.</p>
</div>
""",
    unsafe_allow_html=True,
)