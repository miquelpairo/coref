# -*- coding: utf-8 -*-
"""
Step 4: Checkpoints de Mantenimiento
Verificaciones y registros del mantenimiento realizado
"""

import streamlit as st
from datetime import datetime
import pandas as pd


def render_checkpoints_step():
    """Renderiza el paso 4: Checkpoints de Mantenimiento"""
    
    st.header("📋 Step 4: Checkpoints de Mantenimiento")
    st.markdown("""
    Registra las verificaciones y tareas de mantenimiento realizadas durante el servicio.
    """)
    
    # Inicializar estado si no existe o es None
    if 'checkpoints' not in st.session_state or st.session_state.checkpoints is None:
        st.session_state.checkpoints = {
            # Información general
            'date': datetime.now().strftime("%Y-%m-%d"),
            'firmware_version': '',
            'optical_cleaning': False,
            'observations': '',
            
            # Lámpara Primaria
            'lamp1_changed': False,
            'lamp1_signal': '',
            'lamp1_int_time': '',
            'lamp1_hours': '',
            'lamp1_precalentamiento': '',
            'lamp1_ref_ext': '',
            'lamp1_lb_guardada': '',
            
            # Lámpara Secundaria
            'lamp2_changed': False,
            'lamp2_signal': '',
            'lamp2_int_time': '',
            'lamp2_hours': '',
            'lamp2_precalentamiento': '',
            'lamp2_ref_ext': '',
            'lamp2_lb_guardada': '',
        }
    
    checkpoints = st.session_state.checkpoints
    
    # Sección 1: Información del servicio
    st.subheader("1️⃣ Información del Servicio")
    col1, col2 = st.columns(2)
    
    with col1:
        checkpoints['date'] = st.date_input(
            "Fecha del servicio",
            value=datetime.strptime(checkpoints['date'], "%Y-%m-%d").date(),
            key="service_date"
        ).strftime("%Y-%m-%d")
    
    with col2:
        checkpoints['firmware_version'] = st.text_input(
            "Versión de Firmware",
            value=checkpoints['firmware_version'],
            placeholder="ej: 1.2.3",
            key="firmware_ver"
        )
    
    st.markdown("---")
    
    # Sección 2: Lámparas
    st.subheader("2️⃣ Información de Lámparas")
    
    # Lámpara Primaria
    st.markdown("### 💡 Lámpara Primaria")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        checkpoints['lamp1_changed'] = st.checkbox(
            "Cambio de lámpara realizado",
            value=checkpoints['lamp1_changed'],
            key="lamp1_change"
        )
        
        checkpoints['lamp1_signal'] = st.text_input(
            "Signal Lámpara (%)",
            value=checkpoints['lamp1_signal'],
            placeholder="ej: 81.69%",
            key="lamp1_sig"
        )
    
    with col2:
        checkpoints['lamp1_int_time'] = st.text_input(
            "INT TIME",
            value=checkpoints['lamp1_int_time'],
            placeholder="ej: 12.79",
            key="lamp1_int"
        )
        
        if checkpoints['lamp1_changed']:
            checkpoints['lamp1_hours'] = st.text_input(
                "Horas de lámpara anterior",
                value=checkpoints['lamp1_hours'],
                placeholder="ej: 2500",
                key="lamp1_hrs"
            )
    
    with col3:
        checkpoints['lamp1_precalentamiento'] = st.selectbox(
            "Precalentamiento",
            options=["", "SI", "NO"],
            index=["", "SI", "NO"].index(checkpoints['lamp1_precalentamiento']) if checkpoints['lamp1_precalentamiento'] in ["", "SI", "NO"] else 0,
            key="lamp1_precal"
        )
        
        checkpoints['lamp1_ref_ext'] = st.selectbox(
            "Ref. Ext. Medida",
            options=["", "SI", "NO"],
            index=["", "SI", "NO"].index(checkpoints['lamp1_ref_ext']) if checkpoints['lamp1_ref_ext'] in ["", "SI", "NO"] else 0,
            key="lamp1_ref"
        )
        
        checkpoints['lamp1_lb_guardada'] = st.selectbox(
            "LB Guardada",
            options=["", "SI", "NO"],
            index=["", "SI", "NO"].index(checkpoints['lamp1_lb_guardada']) if checkpoints['lamp1_lb_guardada'] in ["", "SI", "NO"] else 0,
            key="lamp1_lb"
        )
    
    st.markdown("")  # Espaciado
    
    # Lámpara Secundaria
    st.markdown("### 💡 Lámpara Secundaria")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        checkpoints['lamp2_changed'] = st.checkbox(
            "Cambio de lámpara realizado",
            value=checkpoints['lamp2_changed'],
            key="lamp2_change"
        )
        
        checkpoints['lamp2_signal'] = st.text_input(
            "Signal Lámpara (%)",
            value=checkpoints['lamp2_signal'],
            placeholder="ej: 76.06%",
            key="lamp2_sig"
        )
    
    with col2:
        checkpoints['lamp2_int_time'] = st.text_input(
            "INT TIME",
            value=checkpoints['lamp2_int_time'],
            placeholder="ej: 12.79",
            key="lamp2_int"
        )
        
        if checkpoints['lamp2_changed']:
            checkpoints['lamp2_hours'] = st.text_input(
                "Horas de lámpara anterior",
                value=checkpoints['lamp2_hours'],
                placeholder="ej: 2500",
                key="lamp2_hrs"
            )
    
    with col3:
        checkpoints['lamp2_precalentamiento'] = st.selectbox(
            "Precalentamiento",
            options=["", "SI", "NO"],
            index=["", "SI", "NO"].index(checkpoints['lamp2_precalentamiento']) if checkpoints['lamp2_precalentamiento'] in ["", "SI", "NO"] else 0,
            key="lamp2_precal"
        )
        
        checkpoints['lamp2_ref_ext'] = st.selectbox(
            "Ref. Ext. Medida",
            options=["", "SI", "NO"],
            index=["", "SI", "NO"].index(checkpoints['lamp2_ref_ext']) if checkpoints['lamp2_ref_ext'] in ["", "SI", "NO"] else 0,
            key="lamp2_ref"
        )
        
        checkpoints['lamp2_lb_guardada'] = st.selectbox(
            "LB Guardada",
            options=["", "SI", "NO"],
            index=["", "SI", "NO"].index(checkpoints['lamp2_lb_guardada']) if checkpoints['lamp2_lb_guardada'] in ["", "SI", "NO"] else 0,
            key="lamp2_lb"
        )
    
    st.markdown("---")
    
    # Sección 3: Otras verificaciones
    st.subheader("3️⃣ Otras Verificaciones")
    
    checkpoints['optical_cleaning'] = st.checkbox(
        "🧹 Limpieza óptica realizada",
        value=checkpoints['optical_cleaning'],
        key="opt_clean"
    )
    
    st.markdown("---")
    
    # Sección 4: Observaciones
    st.subheader("4️⃣ Observaciones y Notas")
    checkpoints['observations'] = st.text_area(
        "Observaciones del mantenimiento",
        value=checkpoints['observations'],
        height=150,
        placeholder="Describe cualquier incidencia, observación o nota relevante del servicio...",
        key="obs_notes"
    )
    
    st.markdown("---")
    
    # Sección 5: Resumen de Checkpoints
    st.subheader("5️⃣ Resumen de Información Registrada")
    
    # Crear DataFrame para visualización
    data_rows = []
    
    # Información general
    data_rows.append({'Categoría': 'General', 'Campo': 'Fecha del servicio', 'Valor': checkpoints['date']})
    data_rows.append({'Categoría': 'General', 'Campo': 'Versión Firmware', 'Valor': checkpoints['firmware_version'] or '-'})
    data_rows.append({'Categoría': 'General', 'Campo': 'Limpieza óptica', 'Valor': '✅ SI' if checkpoints['optical_cleaning'] else '⬜ NO'})
    
    # Lámpara Primaria
    data_rows.append({'Categoría': 'Lámpara 1', 'Campo': 'Cambio realizado', 'Valor': '✅ SI' if checkpoints['lamp1_changed'] else '⬜ NO'})
    data_rows.append({'Categoría': 'Lámpara 1', 'Campo': 'Signal (%)', 'Valor': checkpoints['lamp1_signal'] or '-'})
    data_rows.append({'Categoría': 'Lámpara 1', 'Campo': 'INT TIME', 'Valor': checkpoints['lamp1_int_time'] or '-'})
    if checkpoints['lamp1_changed']:
        data_rows.append({'Categoría': 'Lámpara 1', 'Campo': 'Horas anterior', 'Valor': checkpoints['lamp1_hours'] or '-'})
    data_rows.append({'Categoría': 'Lámpara 1', 'Campo': 'Precalentamiento', 'Valor': checkpoints['lamp1_precalentamiento'] or '-'})
    data_rows.append({'Categoría': 'Lámpara 1', 'Campo': 'Ref. Ext. Medida', 'Valor': checkpoints['lamp1_ref_ext'] or '-'})
    data_rows.append({'Categoría': 'Lámpara 1', 'Campo': 'LB Guardada', 'Valor': checkpoints['lamp1_lb_guardada'] or '-'})
    
    # Lámpara Secundaria
    data_rows.append({'Categoría': 'Lámpara 2', 'Campo': 'Cambio realizado', 'Valor': '✅ SI' if checkpoints['lamp2_changed'] else '⬜ NO'})
    data_rows.append({'Categoría': 'Lámpara 2', 'Campo': 'Signal (%)', 'Valor': checkpoints['lamp2_signal'] or '-'})
    data_rows.append({'Categoría': 'Lámpara 2', 'Campo': 'INT TIME', 'Valor': checkpoints['lamp2_int_time'] or '-'})
    if checkpoints['lamp2_changed']:
        data_rows.append({'Categoría': 'Lámpara 2', 'Campo': 'Horas anterior', 'Valor': checkpoints['lamp2_hours'] or '-'})
    data_rows.append({'Categoría': 'Lámpara 2', 'Campo': 'Precalentamiento', 'Valor': checkpoints['lamp2_precalentamiento'] or '-'})
    data_rows.append({'Categoría': 'Lámpara 2', 'Campo': 'Ref. Ext. Medida', 'Valor': checkpoints['lamp2_ref_ext'] or '-'})
    data_rows.append({'Categoría': 'Lámpara 2', 'Campo': 'LB Guardada', 'Valor': checkpoints['lamp2_lb_guardada'] or '-'})
    
    df_checkpoints = pd.DataFrame(data_rows)
    st.dataframe(df_checkpoints, use_container_width=True, hide_index=True)
    
    # Calcular completitud (campos críticos rellenados)
    critical_fields = [
        checkpoints['firmware_version'],
        checkpoints['lamp1_signal'],
        checkpoints['lamp1_int_time'],
        checkpoints['lamp2_signal'],
        checkpoints['lamp2_int_time'],
    ]
    
    filled_fields = sum(1 for field in critical_fields if field and str(field).strip())
    total_critical = len(critical_fields)
    completion_pct = (filled_fields / total_critical) * 100
    
    # Mostrar progreso
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Campos críticos completados", f"{filled_fields}/{total_critical}")
    with col2:
        st.metric("Completitud", f"{completion_pct:.0f}%")
    with col3:
        if completion_pct >= 80:
            st.success("✅ Información completa")
        elif completion_pct >= 50:
            st.warning("⚠️ Información parcial")
        else:
            st.error("❌ Información incompleta")
    
    # Barra de progreso
    st.progress(completion_pct / 100)
    
    st.markdown("---")
    
    # Validación para continuar
    can_proceed = True
    validation_messages = []
    
    # No hay campos obligatorios, pero recomendamos completar algunos
    if not checkpoints['firmware_version']:
        validation_messages.append("💡 Recomendado: registrar la versión de firmware")
    
    if not checkpoints['lamp1_signal'] and not checkpoints['lamp2_signal']:
        validation_messages.append("💡 Recomendado: registrar al menos el signal de una lámpara")
    
    if completion_pct < 40:
        validation_messages.append("💡 Recomendado: completar al menos 40% de la información crítica")
    
    if validation_messages:
        for msg in validation_messages:
            st.info(msg)
    
    # Botones de navegación
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.button("⬅️ Anterior", use_container_width=True):
            st.session_state.step = 3
            st.session_state._scroll_to_top = True
            st.rerun()
    
    with col3:
        if st.button(
            "Siguiente ➡️",
            use_container_width=True,
            type="primary"
        ):
            # Guardar checkpoints en session_state antes de continuar
            from session_manager import save_checkpoints_data
            save_checkpoints_data(checkpoints)
            
            st.session_state.step = 5
            st.session_state._scroll_to_top = True
            st.rerun()
    
    # Mensaje informativo
    st.info("💾 Los datos se guardan automáticamente y se incluirán en el informe final")