"""
Manejo de archivos (lectura y escritura)
"""
import pandas as pd
import numpy as np
import io


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
    
    Args:
        file: Archivo subido por Streamlit
        
    Returns:
        tuple: (df, spectrum) donde df es el DataFrame completo
               y spectrum es el array de datos espectrales
    """
    import json
    
    df = pd.read_csv(file)
    
    if 'data' not in df.columns:
        raise ValueError("El archivo CSV no tiene la columna 'data'")
    
    data_string = df['data'].iloc[0]
    spectrum = np.array(json.loads(data_string))
    
    return df, spectrum
