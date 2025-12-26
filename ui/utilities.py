"""
Sección de utilidades (conversión de archivos)
"""
import streamlit as st
import numpy as np
import pandas as pd
import io
import json
from datetime import datetime
from app_config import DEFAULT_CSV_METADATA


def render_utilities_section():
    """
    Renderiza la sección de utilidades en un expander.
    """
    with st.expander("Utilidades: Conversión de archivos"):
        st.markdown("### Convertir archivo .ref a .csv")
        st.info(
            "Convierte un archivo .ref (formato antiguo) a .csv (formato nuevo) con metadatos por defecto."
        )

        util_ref_file = st.file_uploader(
            "Selecciona archivo .ref",
            type="ref",
            key="util_ref"
        )

        if util_ref_file:
            try:
                process_ref_to_csv_conversion(util_ref_file)
            except Exception as e:
                st.error(f"Error: {str(e)}")


def process_ref_to_csv_conversion(file):
    """
    Procesa la conversión de .ref a .csv.

    Args:
        file: Archivo .ref subido
    """
    # Leer archivo .ref
    ref_data = np.frombuffer(file.read(), dtype=np.float32)
    header = ref_data[:3]
    ref_spectrum = ref_data[3:]

    st.write(f"Archivo cargado: {len(ref_spectrum)} puntos espectrales")

    if st.button("Generar CSV desde .ref", key="util_convert"):
        # Crear DataFrame con metadatos por defecto
        metadata = DEFAULT_CSV_METADATA.copy()
        metadata["time_stamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        metadata["nir_pixels"] = len(ref_spectrum)
        metadata["data"] = json.dumps(ref_spectrum.tolist())

        df_export_csv = pd.DataFrame([metadata])

        csv_bytes = io.StringIO()
        df_export_csv.to_csv(csv_bytes, index=False)

        st.warning(
            "CSV generado con metadatos por defecto. Solo 'nir_pixels' y 'data' son valores reales."
        )
        st.download_button(
            "Descargar CSV convertido",
            data=csv_bytes.getvalue(),
            file_name=file.name.replace(".ref", ".csv"),
            mime="text/csv",
            key="util_download_csv"
        )
