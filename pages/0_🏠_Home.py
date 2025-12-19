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
st.markdown("""
**COREF** es un conjunto de herramientas diseñadas para facilitar el mantenimiento 
y validación de equipos NIR (Near-Infrared), especialmente NIR Online con detectores DAD.

Estas aplicaciones ayudan a técnicos de servicio en:
- Ajuste de baseline post-cambio de lámpara
- Validación de estándares ópticos
- Corrección de offset fino
- Comparación y análisis de espectros
- Comparación de predicciones entre lámparas (SX Center)
- Consolidación de informes en un metainforme único
""")

st.divider()

# Tarjetas de navegación
st.markdown("## 🧰 Herramientas Disponibles")

# CSS para igualar alturas - ahora con 7 tarjetas
st.markdown("""
<style>
.card-container {
    min-height: 350px;
    padding: 20px;
    border-radius: 10px;
    background-color: #f5f5f5;
    display: flex;
    flex-direction: column;
}
.card-blue { border: 2px solid #1976d2; }
.card-red { border: 2px solid #d32f2f; }
.card-green { border: 2px solid #388e3c; }
.card-purple { border: 2px solid #7b1fa2; }
.card-orange { border: 2px solid #f57c00; }
.card-teal { border: 2px solid #00897b; }
.card-gray { border: 2px solid #546e7a; }

.card-container h3 { margin-top: 0; }
.card-blue h3 { color: #1976d2; }
.card-red h3 { color: #d32f2f; }
.card-green h3 { color: #388e3c; }
.card-purple h3 { color: #7b1fa2; }
.card-orange h3 { color: #f57c00; }
.card-teal h3 { color: #00897b; }
.card-gray h3 { color: #546e7a; }
</style>
""", unsafe_allow_html=True)

# Primera fila - 2 columnas
col1, col2 = st.columns(2)

with col1:
    st.markdown("""
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
    """, unsafe_allow_html=True)

    st.write("")
    if st.button("🚀 Abrir Baseline Adjustment", key="btn_baseline", use_container_width=True, type="primary"):
        st.switch_page("pages/1_📐_Baseline adjustment.py")

with col2:
    st.markdown("""
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
    """, unsafe_allow_html=True)

    st.write("")
    if st.button("🚀 Abrir Standard Validation", key="btn_validation", use_container_width=True, type="primary"):
        st.switch_page("pages/2_🎯_Validation_Standards.py")

# Segunda fila - 3 columnas
col3, col4, col5 = st.columns(3)

with col3:
    st.markdown("""
    <div class="card-container card-orange">
        <h3>🎚️ Offset Adjustment</h3>
        <p>Ajuste fino de offset vertical al baseline preservando la forma espectral.</p>
        <ul>
            <li>Corrección de bias sistemático</li>
            <li>Simulación con estándares ópticos</li>
            <li>Visualización de impacto</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    if st.button("🚀 Abrir Offset Adjustment", key="btn_offset", use_container_width=True, type="primary"):
        st.switch_page("pages/3_🎚️_Offset_Adjustment.py")

with col4:
    st.markdown("""
    <div class="card-container card-green">
        <h3>🔍 Spectrum Comparison</h3>
        <p>Comparación avanzada de múltiples espectros NIR con análisis estadístico completo.</p>
        <ul>
            <li>Overlay de espectros</li>
            <li>Análisis de residuales y correlación</li>
            <li>Agrupamiento de réplicas</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    if st.button("🚀 Abrir Spectrum Comparison", key="btn_comparison", use_container_width=True, type="primary"):
        st.switch_page("pages/4_🔍_Comparacion_Espectros.py")

with col5:
    st.markdown("""
    <div class="card-container card-purple">
        <h3>⚪ White Reference Analysis</h3>
        <p>Análisis especializado para referencias blancas con métricas apropiadas.</p>
        <ul>
            <li>Escala absoluta de evaluación</li>
            <li>RMS y diferencias absolutas</li>
            <li>Umbrales específicos</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    if st.button("🚀 Abrir White Reference Analysis", key="btn_white", use_container_width=True, type="primary"):
        st.switch_page("pages/5_⚪_White_Reference_Comparison.py")

# Tercera fila - 2 columnas (NUEVAS PÁGINAS)
col6, col7 = st.columns(2)

with col6:
    st.markdown("""
    <div class="card-container card-teal">
        <h3>📊 Prediction Reports</h3>
        <p>Comparación de predicciones entre lámparas usando informes <strong>XML</strong> generados desde SX Center.</p>
        <ul>
            <li>Cargar reporte XML de SX Center</li>
            <li>Comparar predicciones entre lámparas</li>
            <li>Analizar diferencias por muestra/parámetro</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    if st.button("🚀 Abrir Prediction Reports", key="btn_predictions", use_container_width=True, type="primary"):
        st.switch_page("pages/6_📊_Prediction_Reports.py")

with col7:
    st.markdown("""
    <div class="card-container card-gray">
        <h3>📦 Report Consolidator</h3>
        <p>Consolida en un <strong>metainforme</strong> único los informes de Baseline, Validación y Predicciones.</p>
        <ul>
            <li>Subir 1-3 informes (HTML/XML según módulo)</li>
            <li>Resumen ejecutivo y estado global</li>
            <li>Navegación lateral e informes embebidos</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    # OJO: ajusta el nombre del archivo si el tuyo es 07_📦_Consolidator.py o 07_📦_MetaReports.py
    if st.button("🚀 Abrir Report Consolidator", key="btn_metareports", use_container_width=True, type="primary"):
        st.switch_page("pages/07_📦_MetaReports.py")
        # Si tu archivo real es este, usa:
        # st.switch_page("pages/07_📦_Consolidator.py")

st.divider()

# Información adicional actualizada
st.markdown("""
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

---

**Herramientas complementarias:**
- **Spectrum Comparison**: Análisis comparativo general
- **White Reference Analysis**: Análisis específico de referencias blancas
""")

st.divider()

# Footer actualizado
st.markdown("""
<div style="text-align: center; color: #666; padding: 20px;">
    <p><strong>COREF Suite</strong> | Versión 2.0 | Desarrollado por MPC</p>
    <p>Para soporte técnico o consultas, contacta con el departamento de servicio.</p>
</div>
""", unsafe_allow_html=True)
