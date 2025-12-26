"""
Manejo de archivos (lectura y escritura)
"""
import pandas as pd
import numpy as np
import io
import json
from datetime import datetime
from app_config import DEFAULT_CSV_METADATA


def load_tsv_file(file):
    """
    Carga un archivo TSV y lo convierte a DataFrame.
    
    Args:
        file: Archivo subido por Streamlit
        
    Returns:
        pd.DataFrame: DataFrame con los datos del archivo
    """
    content = file.read().decode("utf-8").replace(",", ".")
    df = pd.read_csv(io.StringIO(content), sep="\t")
    return df


def get_spectral_columns(df):
    """
    Extrae las columnas espectrales de un DataFrame.
    Las columnas espectrales comienzan con # seguido de dígitos.
    
    Args:
        df (pd.DataFrame): DataFrame con datos espectrales
        
    Returns:
        list: Lista de nombres de columnas espectrales
    """
    spectral_cols = [
        col for col in df.columns 
        if col.startswith("#") and col[1:].isdigit()
    ]
    return spectral_cols


def load_ref_file(file):
    """
    Carga un archivo .ref (formato binario).
    
    Args:
        file: Archivo subido por Streamlit
        
    Returns:
        tuple: (header, spectrum) donde header son los 3 primeros valores
               y spectrum es el array con los datos espectrales
    """
    ref_data = np.frombuffer(file.read(), dtype=np.float32)
    header = ref_data[:3]
    spectrum = ref_data[3:]
    return header, spectrum


def load_csv_baseline(file):
    """
    Carga un archivo CSV de baseline (formato nuevo).
    Lee la última línea del CSV (baseline más reciente).
    
    Args:
        file: Archivo subido por Streamlit
        
    Returns:
        tuple: (df, spectrum) donde df es el DataFrame completo
               y spectrum es el array de datos espectrales de la última línea
    """
    df = pd.read_csv(file)
    
    if 'data' not in df.columns:
        raise ValueError("El archivo CSV no tiene la columna 'data'")
    
    # Leer la ÚLTIMA línea (baseline más reciente)
    data_string = df['data'].iloc[-1]  # Cambio: iloc[0] → iloc[-1]
    spectrum = np.array(json.loads(data_string))
    
    return df, spectrum


def export_ref_file(spectrum, header):
    """
    Exporta un espectro como archivo .ref binario.
    
    Args:
        spectrum (np.array): Espectro a exportar
        header (np.array): Cabecera del sensor (3 valores)
        
    Returns:
        bytes: Contenido del archivo .ref en bytes
    """
    final_ref = np.concatenate([header, spectrum.astype(np.float32)])
    ref_bytes = io.BytesIO()
    ref_bytes.write(final_ref.astype(np.float32).tobytes())
    ref_bytes.seek(0)
    return ref_bytes.getvalue()


def export_csv_file(spectrum, df_baseline=None):
    """
    Exporta un espectro como archivo CSV.
    Si existe un baseline previo, AÑADE la nueva línea al final.
    Si no existe, crea un CSV nuevo con una sola línea.
    
    Args:
        spectrum (np.array): Espectro a exportar
        df_baseline (pd.DataFrame, optional): DataFrame base con metadatos.
                                              Si es None, usa valores por defecto.
        
    Returns:
        str: Contenido del archivo CSV
    """
    # Crear nueva fila con el espectro ajustado
    if df_baseline is not None:
        # Tomar la última fila como template para metadatos
        new_row = df_baseline.iloc[-1].copy()
        
        # Actualizar timestamp y data
        new_row['time_stamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        new_row['data'] = json.dumps(spectrum.tolist())
        
        # AÑADIR la nueva fila al final del DataFrame existente
        df_export = pd.concat([df_baseline, pd.DataFrame([new_row])], ignore_index=True)
    else:
        # Usar metadatos por defecto (CSV nuevo)
        metadata = DEFAULT_CSV_METADATA.copy()
        metadata['time_stamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        metadata['nir_pixels'] = len(spectrum)
        metadata['data'] = json.dumps(spectrum.tolist())
        df_export = pd.DataFrame([metadata])
    
    csv_bytes = io.StringIO()
    df_export.to_csv(csv_bytes, index=False)
    return csv_bytes.getvalue()
