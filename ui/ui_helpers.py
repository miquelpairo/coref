"""
UI Helpers - Funciones reutilizables para interfaz Streamlit
============================================================
Funciones comunes de UI para páginas de COREF Suite

Author: Miquel
Date: December 2024
"""

import streamlit as st


def show_success(message: str) -> None:
    """
    Muestra un mensaje de éxito con estilo corporativo.
    
    Args:
        message: Texto del mensaje a mostrar
    
    Example:
        >>> show_success("✅ Archivo cargado correctamente")
    """
    st.markdown(
        f'<div class="success-box">{message}</div>', 
        unsafe_allow_html=True
    )


def show_info(message: str) -> None:
    """
    Muestra un mensaje informativo con estilo corporativo.
    
    Args:
        message: Texto del mensaje a mostrar
    
    Example:
        >>> show_info("📌 Por favor, sube al menos un archivo")
    """
    st.markdown(
        f'<div class="info-box">{message}</div>', 
        unsafe_allow_html=True
    )


def show_warning(message: str) -> None:
    """
    Muestra un mensaje de advertencia con estilo corporativo.
    
    Args:
        message: Texto del mensaje a mostrar
    
    Example:
        >>> show_warning("⚠️ Este proceso puede tardar varios minutos")
    """
    st.markdown(
        f'<div class="warning-box">{message}</div>', 
        unsafe_allow_html=True
    )


def show_error(message: str) -> None:
    """
    Muestra un mensaje de error usando el componente nativo de Streamlit.
    
    Args:
        message: Texto del mensaje de error
    
    Example:
        >>> show_error("Error al procesar el archivo")
    """
    st.error(message)


def create_upload_section(title: str, key: str, file_types: list = None, 
                          help_text: str = None) -> object:
    """
    Crea una sección de carga de archivos con estilo corporativo.
    
    Args:
        title: Título de la sección
        key: Key único para el file_uploader
        file_types: Lista de extensiones permitidas (ej: ['html', 'xml'])
        help_text: Texto de ayuda opcional
    
    Returns:
        Objeto file_uploader o None si no se cargó archivo
    
    Example:
        >>> file = create_upload_section(
        ...     title="📊 Baseline Report",
        ...     key="baseline_upload",
        ...     file_types=['html'],
        ...     help_text="Informe generado por COREF Suite"
        ... )
    """
    if file_types is None:
        file_types = ['html']
    
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    st.markdown(f"#### {title}")
    
    uploaded_file = st.file_uploader(
        f"Subir archivo",
        type=file_types,
        key=key,
        help=help_text,
        label_visibility="collapsed"
    )
    
    if uploaded_file:
        show_success("✅ Archivo cargado")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    return uploaded_file


def show_metric_card(label: str, value: str, delta: str = None, 
                     delta_color: str = "normal") -> None:
    """
    Muestra una métrica en formato de tarjeta (wrapper de st.metric).
    
    Args:
        label: Etiqueta de la métrica
        value: Valor de la métrica
        delta: Cambio o valor adicional (opcional)
        delta_color: Color del delta ("normal", "inverse", "off")
    
    Example:
        >>> show_metric_card("Sensor ID", "NIR-12345")
        >>> show_metric_card("Estado", "✅ OK", delta="Validado")
    """
    st.metric(label=label, value=value, delta=delta, delta_color=delta_color)


def create_download_button(label: str, data: str, filename: str, 
                           mime_type: str = "text/html",
                           use_container_width: bool = True) -> bool:
    """
    Crea un botón de descarga estandarizado.
    
    Args:
        label: Texto del botón
        data: Contenido a descargar
        filename: Nombre del archivo
        mime_type: Tipo MIME del archivo
        use_container_width: Si usar todo el ancho del contenedor
    
    Returns:
        bool: True si se hizo clic en el botón
    
    Example:
        >>> clicked = create_download_button(
        ...     label="📥 Descargar Informe",
        ...     data=html_content,
        ...     filename="informe.html"
        ... )
    """
    return st.download_button(
        label=label,
        data=data,
        file_name=filename,
        mime=mime_type,
        use_container_width=use_container_width
    )


def create_section_header(title: str, description: str = None, 
                          icon: str = None) -> None:
    """
    Crea un encabezado de sección estandarizado.
    
    Args:
        title: Título de la sección
        description: Descripción opcional
        icon: Emoji o icono opcional
    
    Example:
        >>> create_section_header(
        ...     title="Cargar Archivos",
        ...     description="Sube los informes HTML a consolidar",
        ...     icon="📁"
        ... )
    """
    if icon:
        st.markdown(f"### {icon} {title}")
    else:
        st.markdown(f"### {title}")
    
    if description:
        st.markdown(f"*{description}*")
    
    st.markdown("---")


def create_expander_with_info(title: str, content: str, 
                               expanded: bool = False) -> None:
    """
    Crea un expander con contenido informativo.
    
    Args:
        title: Título del expander
        content: Contenido en Markdown
        expanded: Si debe estar expandido por defecto
    
    Example:
        >>> create_expander_with_info(
        ...     title="ℹ️ Instrucciones",
        ...     content="## Paso 1\\nCargar archivo..."
        ... )
    """
    with st.expander(title, expanded=expanded):
        st.markdown(content)