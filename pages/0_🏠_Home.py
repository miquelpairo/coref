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
- Comparación y análisis de espectros
""")

st.divider()

# Tarjetas de navegación
st.markdown("## 🧰 Herramientas Disponibles")

# CSS para igualar alturas - ahora con 4 columnas
st.markdown("""
<style>
.card-container {
    min-height: 280px;
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

.card-container h3 { margin-top: 0; }
.card-blue h3 { color: #1976d2; }
.card-red h3 { color: #d32f2f; }
.card-green h3 { color: #388e3c; }
.card-purple h3 { color: #7b1fa2; }
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
            <li>Exportación de reportes</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("")  # Espaciado
    
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
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("")
    
    if st.button("🚀 Abrir Standard Validation", key="btn_validation", use_container_width=True, type="primary"):
        st.switch_page("pages/2_🎯_Validation_Standards.py")

# Segunda fila - 2 columnas
col3, col4 = st.columns(2)

with col3:
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
        st.switch_page("pages/3_🔍_Comparacion_Espectros.py")

with col4:
    st.markdown("""
    <div class="card-container card-purple">
        <h3>⚪ White Reference Analysis</h3>
        <p>Análisis especializado para referencias blancas con métricas apropiadas (RMS, diferencias absolutas).</p>
        <ul>
            <li>Escala absoluta de evaluación</li>
            <li>Sin correlación (no aplicable)</li>
            <li>Umbrales específicos para white refs</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("")
    
    if st.button("🚀 Abrir White Reference Analysis", key="btn_white", use_container_width=True, type="primary"):
        st.switch_page("pages/4_⚪_White_Reference_Comparison.py")

st.divider()

# Información adicional
st.markdown("""
### 📋 Flujo de trabajo típico

1. **Pre-mantenimiento**: Medir y guardar referencia blanca + estándares ópticos
2. **Cambio de lámpara** en NIR Online
3. **Baseline Adjustment**: Nueva medición de referencia blanca y cálculo de corrección
4. **Standard Validation**: Validar alineamiento con estándares ópticos
5. **Spectrum Comparison / White Reference Analysis**: Análisis comparativo si es necesario
""")

st.divider()

# Footer
st.markdown("""
<div style="text-align: center; color: #666; padding: 20px;">
    <p><strong>COREF Suite</strong> | Versión 1.0 | Desarrollado por MPC</p>
    <p>Para soporte técnico o consultas, contacta con el departamento de servicio.</p>
</div>
""", unsafe_allow_html=True)