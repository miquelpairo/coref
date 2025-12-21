# COREF Suite - Plan de Refactoring a Corto Plazo
**Fecha:** 21 Diciembre 2024  
**Objetivo:** Eliminar duplicidades críticas en páginas principales  
**Tiempo estimado:** 4-6 horas  

---

## 🎯 OBJETIVOS INMEDIATOS

### 1. Unificar Páginas 2 & 3 → "Validation Standards" (con opción Offset)
**Ahorro:** ~900 líneas | **Tiempo:** 2-3 horas

### 2. Unificar Páginas 4 & 5 → "Spectrum Comparison" (con opción White Ref)
**Ahorro:** ~1,700 líneas | **Tiempo:** 2-3 horas

### 3. Revisar y optimizar Page 1 (Baseline Adjustment) + UI
**Ahorro:** ~200-300 líneas | **Tiempo:** 1-2 horas

**TOTAL AHORRO:** ~2,800-2,900 líneas  
**TOTAL TIEMPO:** 5-8 horas

---

## 📋 TAREA 1: UNIFICAR VALIDATION STANDARDS + OFFSET

### Estado actual

```
pages/2_🎯_Validation_Standards.py (45,577 bytes)
  ├── Validación de estándares con umbrales
  ├── Análisis de regiones críticas
  └── Informe de validación

pages/3_🎚️_Offset_Adjustment.py (56,774 bytes)
  ├── Simulación de offset
  ├── Comparación pre/post ajuste
  └── Informe de offset
```

### Estado objetivo

```
pages/2_🎯_Validation_Standards.py (UNIFICADA ~40KB)
  ├── Modo 1: Validación (por defecto)
  └── Modo 2: Offset Adjustment (seleccionable)

pages/3_🎚️_Offset_Adjustment.py → ELIMINAR
```

---

### Paso 1.1: Análisis de diferencias (30 min)

**Elementos compartidos (100%):**
- ✅ Carga de TSV (ref + actual)
- ✅ Selección de estándares (data_editor)
- ✅ Funciones: `find_common_ids()`, `validate_standard()`
- ✅ Visualizaciones overlay
- ✅ Estadísticas globales
- ✅ Formulario de informe

**Elementos específicos:**

| Validación | Offset |
|------------|--------|
| Análisis con umbrales | Simulación de offset |
| Regiones críticas | Comparación pre/post |
| `ValidationKitReportGenerator` | `OffsetAdjustmentReportGenerator` |

**Estrategia:** Añadir selector de modo al inicio

---

### Paso 1.2: Implementar selector de modo (15 min)

```python
# pages/2_Validation_Standards.py (NUEVO)

st.title("🎯 Validation Standards & Offset Adjustment")

# ===== SELECTOR DE MODO =====
mode = st.radio(
    "Selecciona el tipo de análisis:",
    options=["Validación de Estándares", "Ajuste de Offset"],
    horizontal=True,
    help="Validación: verifica que los estándares están dentro de umbrales. "
         "Offset: simula ajuste de baseline para alinear espectros."
)

is_validation_mode = (mode == "Validación de Estándares")

st.markdown("---")

# ===== RESTO DEL CÓDIGO COMÚN =====
# ... carga de TSV, selección de estándares ...

# ===== BIFURCACIÓN SEGÚN MODO =====
if is_validation_mode:
    # Lógica de validación (actual página 2)
    render_validation_analysis(...)
    report_generator = ValidationKitReportGenerator()
else:
    # Lógica de offset (actual página 3)
    render_offset_analysis(...)
    report_generator = OffsetAdjustmentReportGenerator()
```

---

### Paso 1.3: Extraer funciones comunes (30 min)

```python
# pages/2_Validation_Standards.py

# ===== FUNCIONES COMPARTIDAS (al principio del archivo) =====

def load_and_validate_tsv_files():
    """Carga archivos TSV de referencia y actual"""
    col1, col2 = st.columns(2)
    
    with col1:
        ref_file = st.file_uploader("TSV Referencia", type="tsv", key="ref")
    with col2:
        new_file = st.file_uploader("TSV Actual", type="tsv", key="new")
    
    if not ref_file or not new_file:
        return None, None, None
    
    df_ref = load_tsv_file(ref_file)
    df_new = load_tsv_file(new_file)
    spectral_cols = get_spectral_columns(df_ref)
    
    return df_ref, df_new, spectral_cols


def find_common_ids(df_ref, df_new):
    """Encuentra IDs comunes entre dos dataframes"""
    ids_ref = set(df_ref['ID'].unique())
    ids_new = set(df_new['ID'].unique())
    common = sorted(ids_ref.intersection(ids_new))
    return common


def render_standards_selection(df_ref, df_new, common_ids, spectral_cols):
    """Renderiza interfaz de selección de estándares"""
    st.subheader("Selección de Estándares")
    
    # Data editor con checkboxes
    selection_df = pd.DataFrame({
        'ID': common_ids,
        'Seleccionar': [True] * len(common_ids)
    })
    
    # Botones de control
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("✅ Seleccionar todos"):
            selection_df['Seleccionar'] = True
    with col2:
        if st.button("❌ Deseleccionar todos"):
            selection_df['Seleccionar'] = False
    with col3:
        if st.button("🔄 Invertir selección"):
            selection_df['Seleccionar'] = ~selection_df['Seleccionar']
    
    edited_df = st.data_editor(
        selection_df,
        hide_index=True,
        use_container_width=True,
        disabled=['ID']
    )
    
    selected_ids = edited_df[edited_df['Seleccionar']]['ID'].tolist()
    return selected_ids


def create_overlay_plot(df_ref_grouped, df_new_grouped, selected_ids, spectral_cols):
    """Crea gráfico overlay de espectros"""
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Espectros Superpuestos', 'Diferencias'),
        vertical_spacing=0.12
    )
    
    channels = list(range(1, len(spectral_cols) + 1))
    
    # Subplot 1: Overlay
    for id_ in selected_ids:
        ref_spectrum = df_ref_grouped.loc[id_].values
        new_spectrum = df_new_grouped.loc[id_].values
        
        fig.add_trace(
            go.Scatter(x=channels, y=ref_spectrum, name=f"{id_} (Ref)", 
                      line=dict(dash='solid')),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=channels, y=new_spectrum, name=f"{id_} (Nuevo)", 
                      line=dict(dash='dash')),
            row=1, col=1
        )
    
    # Subplot 2: Diferencias
    for id_ in selected_ids:
        ref_spectrum = df_ref_grouped.loc[id_].values
        new_spectrum = df_new_grouped.loc[id_].values
        diff = new_spectrum - ref_spectrum
        
        fig.add_trace(
            go.Scatter(x=channels, y=diff, name=f"{id_} (Δ)"),
            row=2, col=1
        )
    
    fig.add_hline(y=0, line_dash="dash", line_color="gray", row=2, col=1)
    
    fig.update_layout(height=800, template='plotly_white', showlegend=True)
    return fig


# ===== FUNCIONES ESPECÍFICAS DE VALIDACIÓN =====

def render_validation_analysis(df_ref_grouped, df_new_grouped, selected_ids, 
                               spectral_cols):
    """Análisis específico de validación con umbrales"""
    st.subheader("📊 Análisis de Validación")
    
    # Umbrales
    col1, col2, col3 = st.columns(3)
    with col1:
        threshold_correlation = st.number_input("Correlación mínima", 
                                                 value=0.995, step=0.001, 
                                                 format="%.3f")
    with col2:
        threshold_rms = st.number_input("RMS máximo", 
                                        value=0.005, step=0.001, 
                                        format="%.3f")
    with col3:
        threshold_max_diff = st.number_input("Diferencia máxima", 
                                             value=0.02, step=0.001, 
                                             format="%.3f")
    
    # Validación estándar por estándar
    results = []
    for id_ in selected_ids:
        ref_spectrum = df_ref_grouped.loc[id_].values
        new_spectrum = df_new_grouped.loc[id_].values
        
        # Métricas
        correlation = np.corrcoef(ref_spectrum, new_spectrum)[0, 1]
        diff = new_spectrum - ref_spectrum
        rms = np.sqrt(np.mean(diff**2))
        max_diff = np.abs(diff).max()
        
        # Evaluación
        status_corr = "✅" if correlation >= threshold_correlation else "❌"
        status_rms = "✅" if rms <= threshold_rms else "❌"
        status_max = "✅" if max_diff <= threshold_max_diff else "❌"
        
        overall_status = "✅ OK" if all([
            correlation >= threshold_correlation,
            rms <= threshold_rms,
            max_diff <= threshold_max_diff
        ]) else "❌ FAIL"
        
        results.append({
            'ID': id_,
            'Correlación': f"{correlation:.6f} {status_corr}",
            'RMS': f"{rms:.6f} {status_rms}",
            'Max Diff': f"{max_diff:.6f} {status_max}",
            'Estado': overall_status
        })
    
    # Tabla de resultados
    results_df = pd.DataFrame(results)
    st.dataframe(results_df, use_container_width=True, hide_index=True)
    
    # Gráfico overlay
    fig = create_overlay_plot(df_ref_grouped, df_new_grouped, selected_ids, spectral_cols)
    st.plotly_chart(fig, use_container_width=True)
    
    return results


# ===== FUNCIONES ESPECÍFICAS DE OFFSET =====

def render_offset_analysis(df_ref_grouped, df_new_grouped, selected_ids, 
                           spectral_cols):
    """Análisis específico de ajuste de offset"""
    st.subheader("🎚️ Simulación de Ajuste de Offset")
    
    # Calcular corrección promedio
    corrections = []
    for id_ in selected_ids:
        ref_spectrum = df_ref_grouped.loc[id_].values
        new_spectrum = df_new_grouped.loc[id_].values
        diff = ref_spectrum - new_spectrum
        corrections.append(diff)
    
    mean_correction = np.mean(corrections, axis=0)
    
    # Mostrar estadísticas de la corrección
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Corrección promedio", f"{np.mean(mean_correction):.6f}")
    with col2:
        st.metric("Corrección máxima", f"{np.max(np.abs(mean_correction)):.6f}")
    with col3:
        st.metric("Desv. Est.", f"{np.std(mean_correction):.6f}")
    
    # Simular espectros corregidos
    st.markdown("#### Simulación: Espectros después de aplicar corrección")
    
    simulated_df = df_new_grouped.copy()
    simulated_df.loc[selected_ids] = simulated_df.loc[selected_ids] + mean_correction
    
    # Gráfico: Original vs Simulado
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Antes de Corrección', 'Después de Corrección (Simulado)'),
        vertical_spacing=0.12
    )
    
    channels = list(range(1, len(spectral_cols) + 1))
    
    # Antes
    for id_ in selected_ids:
        ref_spectrum = df_ref_grouped.loc[id_].values
        new_spectrum = df_new_grouped.loc[id_].values
        
        fig.add_trace(
            go.Scatter(x=channels, y=ref_spectrum, name=f"{id_} (Ref)", 
                      line=dict(color='blue')),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=channels, y=new_spectrum, name=f"{id_} (Actual)", 
                      line=dict(color='red', dash='dash')),
            row=1, col=1
        )
    
    # Después (simulado)
    for id_ in selected_ids:
        ref_spectrum = df_ref_grouped.loc[id_].values
        sim_spectrum = simulated_df.loc[id_].values
        
        fig.add_trace(
            go.Scatter(x=channels, y=ref_spectrum, name=f"{id_} (Ref)", 
                      line=dict(color='blue'), showlegend=False),
            row=2, col=1
        )
        fig.add_trace(
            go.Scatter(x=channels, y=sim_spectrum, name=f"{id_} (Corregido)", 
                      line=dict(color='green', dash='dash')),
            row=2, col=1
        )
    
    fig.update_layout(height=900, template='plotly_white')
    st.plotly_chart(fig, use_container_width=True)
    
    # Estadísticas post-corrección
    st.markdown("#### Métricas después de corrección simulada")
    
    post_results = []
    for id_ in selected_ids:
        ref_spectrum = df_ref_grouped.loc[id_].values
        sim_spectrum = simulated_df.loc[id_].values
        
        correlation = np.corrcoef(ref_spectrum, sim_spectrum)[0, 1]
        diff = sim_spectrum - ref_spectrum
        rms = np.sqrt(np.mean(diff**2))
        max_diff = np.abs(diff).max()
        
        post_results.append({
            'ID': id_,
            'Correlación': f"{correlation:.6f}",
            'RMS': f"{rms:.6f}",
            'Max Diff': f"{max_diff:.6f}"
        })
    
    post_df = pd.DataFrame(post_results)
    st.dataframe(post_df, use_container_width=True, hide_index=True)
    
    return mean_correction


# ===== FLUJO PRINCIPAL =====

def main():
    st.title("🎯 Validation Standards & Offset Adjustment")
    
    # Selector de modo
    mode = st.radio(
        "Selecciona el tipo de análisis:",
        options=["Validación de Estándares", "Ajuste de Offset"],
        horizontal=True,
        help="Validación: verifica estándares con umbrales. "
             "Offset: simula ajuste de baseline."
    )
    
    is_validation_mode = (mode == "Validación de Estándares")
    
    st.markdown("---")
    
    # 1. Carga de archivos
    st.subheader("1️⃣ Cargar Archivos TSV")
    df_ref, df_new, spectral_cols = load_and_validate_tsv_files()
    
    if df_ref is None:
        st.info("👆 Carga los archivos TSV para continuar")
        return
    
    st.success(f"✅ Archivos cargados ({len(spectral_cols)} canales espectrales)")
    
    st.markdown("---")
    
    # 2. Agrupar por ID
    df_ref_grouped = df_ref.groupby('ID')[spectral_cols].mean()
    df_new_grouped = df_new.groupby('ID')[spectral_cols].mean()
    
    # 3. Encontrar IDs comunes
    common_ids = find_common_ids(df_ref, df_new)
    
    if len(common_ids) == 0:
        st.error("❌ No hay IDs comunes entre los archivos")
        return
    
    st.info(f"📋 {len(common_ids)} IDs comunes encontrados")
    
    # 4. Selección de estándares
    st.markdown("---")
    selected_ids = render_standards_selection(df_ref, df_new, common_ids, spectral_cols)
    
    if len(selected_ids) == 0:
        st.warning("⚠️ Selecciona al menos un estándar")
        return
    
    st.success(f"✅ {len(selected_ids)} estándares seleccionados")
    
    st.markdown("---")
    
    # 5. Análisis según modo
    if is_validation_mode:
        validation_results = render_validation_analysis(
            df_ref_grouped, df_new_grouped, selected_ids, spectral_cols
        )
        report_type = "validation"
    else:
        correction_vector = render_offset_analysis(
            df_ref_grouped, df_new_grouped, selected_ids, spectral_cols
        )
        report_type = "offset"
    
    st.markdown("---")
    
    # 6. Generación de informe
    st.subheader("📄 Generar Informe")
    
    with st.form("report_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            sensor_serial = st.text_input("Número de serie del sensor *")
            customer = st.text_input("Cliente *")
        
        with col2:
            technician = st.text_input("Técnico")
            notes = st.text_area("Notas adicionales")
        
        generate = st.form_submit_button("📥 Generar Informe HTML", 
                                         type="primary", 
                                         use_container_width=True)
        
        if generate:
            if not sensor_serial or not customer:
                st.error("❌ Completa los campos obligatorios (*)")
            else:
                # Generar informe según tipo
                if report_type == "validation":
                    from core.validation_kit_report_generator import generate_validation_report
                    html = generate_validation_report(
                        # ... parámetros
                    )
                    filename = f"Validation_{sensor_serial}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                else:
                    from core.offset_adjustment_report_generator import generate_offset_report
                    html = generate_offset_report(
                        # ... parámetros
                    )
                    filename = f"Offset_{sensor_serial}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                
                st.download_button(
                    "⬇️ Descargar Informe",
                    data=html,
                    file_name=filename,
                    mime="text/html",
                    use_container_width=True
                )


if __name__ == "__main__":
    main()
```

---

### Paso 1.4: Testing (30 min)

**Checklist:**
- [ ] Modo Validación: carga TSV, selecciona estándares, valida, genera informe
- [ ] Modo Offset: carga TSV, selecciona estándares, simula offset, genera informe
- [ ] Cambio entre modos sin errores
- [ ] Estadísticas correctas en ambos modos
- [ ] Gráficos se renderizan correctamente
- [ ] Informes HTML se generan y descargan

---

### Paso 1.5: Eliminar página 3 (5 min)

```bash
# En tu repositorio
git rm pages/3_🎚️_Offset_Adjustment.py
git commit -m "Refactor: Unificar Validation + Offset en una sola página"
```

---

### Paso 1.6: Actualizar navegación (10 min)

Si hay referencias a la página 3 en:
- `app.py` (router principal)
- `0_Home.py` (página de inicio)
- Documentación

Actualizar para que apunten a la página 2 unificada.

---

## 📋 TAREA 2: UNIFICAR SPECTRUM COMPARISON + WHITE REFERENCE

### Estado actual

```
pages/4_🔍_Comparacion_Espectros.py (39,089 bytes)
  ├── Comparación genérica de espectros
  └── Matriz RMS con escala relativa

pages/5_⚪_White_Reference_Comparison.py (42,960 bytes)
  ├── Comparación de white references
  ├── Matriz RMS con escala absoluta
  └── Evaluación automática (✅/⚠️/❌)
```

### Estado objetivo

```
pages/4_🔍_Spectrum_Comparison.py (UNIFICADA ~35KB)
  ├── Modo 1: Comparación genérica (por defecto)
  └── Modo 2: White References (seleccionable)

pages/5_⚪_White_Reference_Comparison.py → ELIMINAR
```

---

### Paso 2.1: Implementar selector de modo (15 min)

```python
# pages/4_Spectrum_Comparison.py (NUEVO)

st.title("📊 NIR Spectrum Comparison Tool")

# ===== SELECTOR DE MODO =====
comparison_type = st.radio(
    "Tipo de espectros a comparar:",
    options=["Espectros generales", "White References (Baseline)"],
    horizontal=True,
    help="White References: usa escala absoluta con umbrales específicos para baseline."
)

is_white_reference_mode = (comparison_type == "White References (Baseline)")

# Configuración según modo
if is_white_reference_mode:
    st.markdown("**Modo White Reference:** Comparación de baseline con umbrales específicos")
    use_absolute_rms = True
    rms_thresholds = {
        'excellent': 0.002,
        'good': 0.005,
        'acceptable': 0.01,
        'max': 0.015
    }
else:
    st.markdown("**Modo General:** Comparación de espectros NIR")
    use_absolute_rms = False
    rms_thresholds = None

st.markdown("---")
```

---

### Paso 2.2: Modificar función de Matriz RMS (20 min)

```python
# pages/4_Spectrum_Comparison.py

def create_rms_heatmap(spectra_list, spectrum_labels, use_absolute_rms=False, 
                       thresholds=None):
    """
    Crea matriz de RMS con escala relativa o absoluta
    
    Args:
        spectra_list: Lista de espectros
        spectrum_labels: Labels de espectros
        use_absolute_rms: Si True, usa escala absoluta con umbrales fijos
        thresholds: Dict con umbrales (solo si use_absolute_rms=True)
    """
    n_spectra = len(spectra_list)
    rms_matrix = np.zeros((n_spectra, n_spectra))
    
    # Calcular RMS
    for i in range(n_spectra):
        for j in range(n_spectra):
            if i == j:
                rms_matrix[i, j] = 0
            else:
                diff = spectra_list[i] - spectra_list[j]
                rms_matrix[i, j] = np.sqrt(np.mean(diff**2))
    
    # Configurar escala de colores según modo
    if use_absolute_rms and thresholds:
        # Escala absoluta para white references
        colorscale = [
            [0.0, '#4caf50'],      # Verde (excelente) 0-0.002
            [0.333, '#8bc34a'],    # Verde claro
            [0.667, '#ffc107'],    # Amarillo (aceptable) 0.005-0.01
            [1.0, '#f44336']       # Rojo (revisar) >0.01
        ]
        
        zmin = 0
        zmax = thresholds['max']
        
        tickvals = [0, thresholds['excellent'], thresholds['good'], 
                   thresholds['acceptable'], thresholds['max']]
        ticktext = ['0.000', 
                   f"{thresholds['excellent']:.3f}<br>(Exc)", 
                   f"{thresholds['good']:.3f}<br>(Bueno)", 
                   f"{thresholds['acceptable']:.3f}<br>(Acept)", 
                   f"{thresholds['max']:.3f}"]
        
        title_suffix = " - Escala Absoluta (White References)"
        
    else:
        # Escala relativa (auto-ajuste)
        colorscale = 'RdYlGn_r'
        zmin = None
        zmax = None
        tickvals = None
        ticktext = None
        title_suffix = " - Escala Relativa"
    
    # Crear figura
    fig = go.Figure(data=go.Heatmap(
        z=rms_matrix,
        x=spectrum_labels,
        y=spectrum_labels,
        colorscale=colorscale,
        zmin=zmin,
        zmax=zmax,
        text=np.round(rms_matrix, 6),
        texttemplate='%{text}',
        textfont={"size": 10},
        colorbar=dict(
            title="RMS (AU)",
            tickvals=tickvals,
            ticktext=ticktext
        ) if use_absolute_rms else dict(title="RMS")
    ))
    
    fig.update_layout(
        title=f'Matriz de Diferencias RMS{title_suffix}',
        height=max(400, 50 * n_spectra),
        template='plotly_white'
    )
    
    return fig
```

---

### Paso 2.3: Añadir evaluación automática (solo White Ref) (15 min)

```python
# pages/4_Spectrum_Comparison.py

# En TAB 4 (Matriz RMS)
with tab4:
    st.subheader("Matriz de Diferencias RMS")
    
    # Toggle solo visible en modo White Reference
    if is_white_reference_mode:
        st.info("📏 **Modo White Reference**: Escala absoluta con umbrales fijos")
        st.caption("Verde < 0.005 AU | Amarillo < 0.01 AU | Rojo ≥ 0.01 AU")
    else:
        st.info("📊 **Modo General**: Escala relativa basada en valores del dataset")
    
    # Crear heatmap
    fig_heatmap = create_rms_heatmap(
        selected_spectra, 
        spectrum_labels, 
        use_absolute_rms=is_white_reference_mode,
        thresholds=rms_thresholds if is_white_reference_mode else None
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)
    
    # Análisis de similitud
    with st.expander("🔍 Análisis de Similitud"):
        n_spectra = len(selected_spectra)
        rms_values = []
        
        for i in range(n_spectra):
            for j in range(i+1, n_spectra):
                diff = selected_spectra[i] - selected_spectra[j]
                rms = np.sqrt(np.mean(diff**2))
                max_diff = np.abs(diff).max()
                
                # Evaluación según modo
                if is_white_reference_mode:
                    # Evaluación específica para white references
                    if rms < 0.002 and max_diff < 0.005:
                        evaluacion = "✅ Excelente"
                    elif rms < 0.005 and max_diff < 0.01:
                        evaluacion = "✓ Bueno"
                    elif rms < 0.01 and max_diff < 0.02:
                        evaluacion = "⚠️ Aceptable"
                    else:
                        evaluacion = "❌ Revisar"
                else:
                    # Evaluación genérica (sin umbrales específicos)
                    evaluacion = "—"
                
                rms_values.append({
                    'Espectro A': spectrum_labels[i],
                    'Espectro B': spectrum_labels[j],
                    'RMS': f"{rms:.6f}",
                    'Max Diff': f"{max_diff:.6f}",
                    'Evaluación': evaluacion
                })
        
        rms_df = pd.DataFrame(rms_values).sort_values('RMS')
        
        st.markdown("**Pares más similares:**")
        st.dataframe(rms_df.head(5), use_container_width=True, hide_index=True)
        
        if is_white_reference_mode:
            st.markdown("**Pares que requieren atención:**")
            problem_pairs = rms_df[rms_df['Evaluación'].str.contains('❌|⚠️')]
            if len(problem_pairs) > 0:
                st.dataframe(problem_pairs, use_container_width=True, hide_index=True)
            else:
                st.success("✅ Todas las comparaciones están en rango excelente/bueno")
```

---

### Paso 2.4: Testing (30 min)

**Checklist:**
- [ ] Modo General: carga TSV, compara espectros, matriz RMS relativa
- [ ] Modo White Reference: carga TSV, compara baseline, matriz RMS absoluta
- [ ] Evaluación automática solo aparece en modo White Reference
- [ ] Colores correctos en ambos modos
- [ ] Cambio entre modos funciona correctamente
- [ ] Tabs funcionan en ambos modos

---

### Paso 2.5: Eliminar página 5 (5 min)

```bash
git rm pages/5_⚪_White_Reference_Comparison.py
git commit -m "Refactor: Unificar Spectrum Comparison + White Reference"
```

---

## 📋 TAREA 3: REVISAR PAGE 1 (BASELINE ADJUSTMENT) + UI

### Objetivo

Revisar código de la página principal y sus componentes UI para:
- ✅ Eliminar duplicaciones restantes
- ✅ Simplificar flujo si es posible
- ✅ Asegurar coherencia con nuevas páginas unificadas

---

### Paso 3.1: Auditar componentes UI (30 min)

**Archivo:** `pages/1_📐_Baseline_adjustment.py` (3.5KB - router)

**Componentes UI auditados:**
```
ui/step_00_client_info.py     (3KB)   ✅ Sin duplicación
ui/step_01_backup.py           (1.5KB) ✅ Sin duplicación
ui/step_02_wstd.py             (12KB)  ⚠️ Selector de filas (duplicado)
ui/step_04_validation.py       (21KB)  ⚠️ Selector de filas (duplicado)
ui/step_05_baseline_alignment.py (14KB) ✅ Lógica única
ui/sidebar.py                  (6.5KB) ✅ Sin duplicación
ui/utilities.py                (2.5KB) ✅ Sin duplicación
```

---

### Paso 3.2: Crear módulo compartido para selección TSV (45 min)

**Problema detectado:**
- `step_02_wstd.py` y `step_04_validation.py` tienen código idéntico para:
  - Carga de TSV con `file_uploader`
  - Selección de filas con `data_editor`
  - Validación de selección
  - Conversión a numérico

**Solución:**

```python
# ui/shared/tsv_helpers.py (NUEVO)

import streamlit as st
import pandas as pd
from core.file_handlers import load_tsv_file, get_spectral_columns

def render_tsv_uploader_with_row_selector(
    label: str,
    key: str,
    help_text: str = None,
    allow_multiple: bool = False
) -> tuple:
    """
    Carga TSV y permite seleccionar filas con data_editor
    
    Returns:
        (df_selected, indices, spectral_cols) o (None, None, None) si no hay selección
    """
    
    # Upload
    uploaded_file = st.file_uploader(
        label,
        type=['tsv', 'txt', 'csv'],
        key=key,
        help=help_text
    )
    
    if not uploaded_file:
        return None, None, None
    
    try:
        # Cargar
        df = load_tsv_file(uploaded_file)
        spectral_cols = get_spectral_columns(df)
        
        st.success(f"✅ Archivo cargado: {len(df)} filas, {len(spectral_cols)} canales")
        
        # Mostrar selector de filas
        st.markdown("#### Selecciona las filas a usar")
        
        df_display = df[['ID', 'Note']].copy()
        df_display.insert(0, 'Seleccionar', False)
        
        # Botones de control
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("✅ Todos", key=f"{key}_all"):
                df_display['Seleccionar'] = True
        with col2:
            if st.button("❌ Ninguno", key=f"{key}_none"):
                df_display['Seleccionar'] = False
        with col3:
            if st.button("🔄 Invertir", key=f"{key}_invert"):
                df_display['Seleccionar'] = ~df_display['Seleccionar']
        
        # Editor
        edited_df = st.data_editor(
            df_display,
            hide_index=False,
            use_container_width=True,
            disabled=['ID', 'Note'],
            key=f"{key}_editor"
        )
        
        # Obtener selección
        selected_indices = edited_df[edited_df['Seleccionar'] == True].index.tolist()
        
        if len(selected_indices) == 0:
            st.warning("⚠️ No has seleccionado ninguna fila")
            return None, None, None
        
        df_selected = df.loc[selected_indices].copy()
        
        # Convertir a numérico
        df_selected[spectral_cols] = df_selected[spectral_cols].apply(
            pd.to_numeric, errors='coerce'
        )
        
        st.info(f"📝 {len(selected_indices)} filas seleccionadas")
        
        return df_selected, selected_indices, spectral_cols
        
    except Exception as e:
        st.error(f"❌ Error al cargar archivo: {str(e)}")
        return None, None, None


def group_by_id_and_average(df, spectral_cols):
    """Agrupa por ID y calcula promedio de espectros"""
    df_grouped = df.groupby('ID')[spectral_cols].mean().reset_index()
    return df_grouped
```

---

### Paso 3.3: Refactorizar step_02 y step_04 (30 min)

**step_02_wstd.py - ANTES:**
```python
# 150 líneas de código para cargar TSV y seleccionar filas
wstd_file = st.file_uploader(...)
df = load_tsv_file(wstd_file)
spectral_cols = get_spectral_columns(df)
# ... 100 líneas más de data_editor, botones, etc.
```

**step_02_wstd.py - DESPUÉS:**
```python
from ui.shared.tsv_helpers import render_tsv_uploader_with_row_selector

# 5 líneas
df_wstd, selected_indices, spectral_cols = render_tsv_uploader_with_row_selector(
    label="Archivo TSV con External White",
    key="wstd_upload",
    help_text="Mediciones del White Standard con el baseline actual"
)

if df_wstd is None:
    st.info("👆 Carga el archivo TSV para continuar")
    return

# Continuar con análisis...
```

**Ahorro:** ~150 líneas en cada step = ~300 líneas totales

---

### Paso 3.4: Simplificar flujo de navegación (20 min)

**Revisar si se puede simplificar:**

```python
# ui/step_XX.py (patrón actual en todos)

# Botones de navegación al final
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("⬅️ Anterior"):
        st.session_state.step = X
        st.rerun()
with col2:
    if st.button("Siguiente ➡️", type="primary"):
        st.session_state.step = Y
        st.rerun()
```

**Propuesta de helper:**

```python
# ui/shared/navigation.py (NUEVO)

def render_step_navigation(prev_step=None, next_step=None, 
                           can_proceed=True, unsaved_warning=False):
    """
    Renderiza botones de navegación estándar
    
    Args:
        prev_step: Número del paso anterior (None si es el primero)
        next_step: Número del paso siguiente (None si es el último)
        can_proceed: Si False, deshabilita botón "Siguiente"
        unsaved_warning: Si True, muestra advertencia de cambios sin guardar
    """
    
    if unsaved_warning:
        st.warning("⚠️ Tienes cambios sin guardar")
    
    cols = st.columns([1, 1])
    
    with cols[0]:
        if prev_step is not None:
            if st.button("⬅️ Anterior", use_container_width=True):
                st.session_state.step = prev_step
                st.rerun()
    
    with cols[1]:
        if next_step is not None:
            if st.button("Siguiente ➡️", type="primary", 
                        disabled=not can_proceed, 
                        use_container_width=True):
                st.session_state.unsaved_changes = False
                st.session_state.step = next_step
                st.rerun()
```

**Uso en steps:**
```python
# Al final de cada step
from ui.shared.navigation import render_step_navigation

render_step_navigation(
    prev_step=2,
    next_step=4,
    can_proceed=st.session_state.get('wstd_validated', False)
)
```

**Ahorro:** ~20 líneas × 6 steps = ~120 líneas

---

### Paso 3.5: Testing completo del workflow (45 min)

**Flujo completo a testear:**

1. **Paso 0 - Cliente:**
   - [ ] Formulario se muestra correctamente
   - [ ] Validación de campos obligatorios
   - [ ] Navegación a paso 1

2. **Paso 1 - Backup:**
   - [ ] Advertencia se muestra
   - [ ] Botones funcionan
   - [ ] Navegación bidireccional

3. **Paso 2 - WSTD:**
   - [ ] Nuevo helper `render_tsv_uploader_with_row_selector` funciona
   - [ ] Selección de filas correcta
   - [ ] Diagnóstico se muestra
   - [ ] Guarda IDs seleccionados para paso 5

4. **Paso 4 - Validación:**
   - [ ] Nuevo helper funciona
   - [ ] Cálculo de RMS correcto
   - [ ] Decisión: OK → informe | FAIL → paso 5

5. **Paso 5 - Alineamiento:**
   - [ ] Usa IDs del paso 2
   - [ ] Corrección se aplica correctamente
   - [ ] Exporta .ref y .csv
   - [ ] Vuelve a paso 4 correctamente

---

## 📊 RESUMEN DEL PLAN

### Tiempo total estimado

| Tarea | Tiempo | Ahorro |
|-------|--------|--------|
| **Tarea 1: Unificar Validación + Offset** | 2-3 horas | ~900 líneas |
| **Tarea 2: Unificar Spectrum Comparison** | 2-3 horas | ~1,700 líneas |
| **Tarea 3: Revisar Page 1 + UI** | 2-3 horas | ~420 líneas |
| **TOTAL** | **6-9 horas** | **~3,020 líneas** |

### Archivos afectados

**Eliminados:**
- ❌ `pages/3_🎚️_Offset_Adjustment.py`
- ❌ `pages/5_⚪_White_Reference_Comparison.py`

**Modificados:**
- 🔄 `pages/2_🎯_Validation_Standards.py` (unificada)
- 🔄 `pages/4_🔍_Spectrum_Comparison.py` (unificada)
- 🔄 `ui/step_02_wstd.py` (usa helpers)
- 🔄 `ui/step_04_validation.py` (usa helpers)

**Nuevos:**
- ✨ `ui/shared/tsv_helpers.py` (~100 líneas)
- ✨ `ui/shared/navigation.py` (~50 líneas)

### Commits recomendados

```bash
# 1. Unificar Validación + Offset
git commit -m "Refactor: Unify Validation Standards + Offset Adjustment

- Merge pages 2 & 3 into single page with mode selector
- Extract common functions (find_common_ids, validate_standard, etc.)
- Add mode toggle: Validation vs Offset
- Remove page 3 (now integrated in page 2)
- Saves ~900 lines of duplicated code"

# 2. Unificar Spectrum Comparison
git commit -m "Refactor: Unify Spectrum Comparison + White Reference

- Merge pages 4 & 5 into single page with mode selector
- Add toggle: General vs White Reference mode
- Implement absolute vs relative RMS scale
- Add automatic evaluation for White Reference mode
- Remove page 5 (now integrated in page 4)
- Saves ~1,700 lines of duplicated code"

# 3. Refactorizar UI helpers
git commit -m "Refactor: Create shared UI helpers for Page 1 workflow

- Create ui/shared/tsv_helpers.py for TSV loading + row selection
- Create ui/shared/navigation.py for step navigation
- Refactor step_02 and step_04 to use shared helpers
- Simplify navigation in all steps
- Saves ~420 lines of duplicated code"
```

---

## ⚠️ PUNTOS IMPORTANTES QUE PODRÍAS ESTAR OMITIENDO

### 1. Actualizar referencias de navegación

**Archivo:** `pages/0_🏠_Home.py`

Si la página Home tiene links directos a las páginas eliminadas (3 y 5), actualizar:

```python
# ANTES
st.page_link("pages/3_🎚️_Offset_Adjustment.py", label="Offset Adjustment")
st.page_link("pages/5_⚪_White_Reference_Comparison.py", label="White Reference")

# DESPUÉS
st.markdown("**Validación y Offset:** Usa la página 'Validation Standards' y selecciona el modo")
st.markdown("**White Reference:** Usa la página 'Spectrum Comparison' en modo White Reference")
```

---

### 2. Actualizar documentación

**Archivos a revisar:**
- `README.md` - Descripción de páginas
- Cualquier guía de usuario
- Comentarios en `app.py`

---

### 3. Gestión de session_state

**Verificar que no haya conflictos:**

Cuando unificas páginas, algunos estados de `st.session_state` pueden entrar en conflicto:

```python
# Revisar si existen keys duplicadas como:
st.session_state.selected_standards_page2
st.session_state.selected_standards_page3

# Unificar a:
st.session_state.selected_standards  # Único
```

---

### 4. Backward compatibility con informes antiguos

Si tienes informes HTML generados con las páginas antiguas (3 y 5), asegúrate de que:

- Los nuevos informes generados son compatibles
- Los nombres de archivos siguen el mismo patrón
- Los consolidators (GRUPO 2) pueden parsear ambos formatos

---

### 5. Testing de edge cases

**Casos a testear:**

- [ ] ¿Qué pasa si cambias de modo después de cargar datos?
  - Solución: Limpiar datos al cambiar modo
  
- [ ] ¿Qué pasa si intentas generar informe sin seleccionar estándares?
  - Solución: Deshabilitar botón si `len(selected_ids) == 0`
  
- [ ] ¿Los gráficos se actualizan correctamente al cambiar de modo?
  - Solución: Usar `key` únicos en cada modo

---

### 6. Mantener compatibilidad con parsers (GRUPO 2)

**IMPORTANTE:** Si los parsers de MetaReports esperan estructura específica de HTML:

- Asegúrate de que los informes unificados siguen generando HTML compatible
- O actualiza los parsers para soportar ambos formatos (antiguo y nuevo)

---

## ✅ CHECKLIST FINAL

### Antes de empezar
- [ ] Backup del código actual (git tag o branch)
- [ ] Revisar que no hay cambios sin commitear
- [ ] Crear branch de trabajo: `git checkout -b refactor/unify-pages`

### Durante el refactoring
- [ ] Commits atómicos por cada tarea
- [ ] Testing manual después de cada cambio
- [ ] Documentar cambios en commit messages

### Después del refactoring
- [ ] Testing completo del flujo end-to-end
- [ ] Actualizar README.md
- [ ] Actualizar referencias en Home
- [ ] Merge a main: `git checkout main && git merge refactor/unify-pages`
- [ ] Eliminar branch de trabajo: `git branch -d refactor/unify-pages`

---

## 🚀 ORDEN RECOMENDADO DE EJECUCIÓN

**Opción A (menos riesgo):**
1. Tarea 3 primero (UI helpers) - Menos crítico, más modular
2. Tarea 2 (Spectrum Comparison) - Más fácil, menos dependencias
3. Tarea 1 (Validation + Offset) - Más complejo, depende de report generators

**Opción B (más impacto visual):**
1. Tarea 2 (Spectrum Comparison) - Usuario ve mejora inmediata
2. Tarea 1 (Validation + Offset) - Segunda mejora visible
3. Tarea 3 (UI helpers) - Optimización interna

**Opción C (tu propuesta):**
1. Tarea 1 (Validation + Offset) ✅
2. Tarea 2 (Spectrum Comparison) ✅
3. Tarea 3 (UI helpers) ✅

**Recomiendo Opción B** para ver resultados rápido y mantener motivación.

---

¿Te parece bien este plan? ¿Empezamos con la Tarea 2 (Spectrum Comparison)?