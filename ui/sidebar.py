"""
Componente de barra lateral con progreso del proceso
"""
import streamlit as st
from config import STEPS
from session_manager import go_to_previous_step, get_current_step


def render_sidebar():
    """
    Renderiza la barra lateral con el progreso de los pasos.
    """
    with st.sidebar:
        st.markdown("## 📊 Progreso")
        
        current_step = get_current_step()
        
        # Renderizar cada paso con su estado
        for i, step_name in enumerate(STEPS):
            step_idx = i - 1  # Ajustar porque comenzamos en -1
            
            if step_idx < current_step:
                # Paso completado
                st.markdown(f"✅ **{i}. {step_name}**")
            elif step_idx == current_step:
                # Paso actual
                st.markdown(f"⏳ **{i}. {step_name}**")
            else:
                # Paso pendiente
                st.markdown(f"○ {i}. {step_name}")
        
        st.markdown("---")
        
        # Botón para volver al paso anterior
        if current_step > -1:
            if st.button("⬅️ Volver al paso anterior"):
                go_to_previous_step()
```

---

## ✅ Verifica que todo esté correcto

Tu estructura debería verse así:
```
baseline_adjustment_tool/
│
├── app.py
├── config.py
├── session_manager.py
│
├── ui/
│   ├── __init__.py
│   └── sidebar.py
│
├── core/
│   └── __init__.py
│
└── utils/
    └── __init__.py
