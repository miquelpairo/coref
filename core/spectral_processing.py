"""
Procesamiento de datos espectrales
"""
import pandas as pd
import numpy as np
from config import SPECIAL_IDS


def group_measurements_by_lamp(df, spectral_cols, lamp_ref, lamp_new):
    """
    Agrupa las mediciones por lámpara y calcula promedios.
    
    Args:
        df (pd.DataFrame): DataFrame con mediciones
        spectral_cols (list): Lista de columnas espectrales
        lamp_ref (str): Nombre de la lámpara de referencia
        lamp_new (str): Nombre de la lámpara nueva
        
    Returns:
        tuple: (df_ref_grouped, df_new_grouped) DataFrames agrupados por ID
    """
    df_ref = df[df["Note"] == lamp_ref].copy()
    df_new = df[df["Note"] == lamp_new].copy()
    
    df_ref_grouped = df_ref.groupby("ID")[spectral_cols].mean()
    df_new_grouped = df_new.groupby("ID")[spectral_cols].mean()
    
    return df_ref_grouped, df_new_grouped


def find_common_samples(df_ref_grouped, df_new_grouped):
    """
    Encuentra las muestras comunes entre dos DataFrames.
    
    Args:
        df_ref_grouped (pd.DataFrame): DataFrame de referencia
        df_new_grouped (pd.DataFrame): DataFrame nuevo
        
    Returns:
        pd.Index: Índice con los IDs comunes
    """
    common_ids = df_ref_grouped.index.intersection(df_new_grouped.index)
    return common_ids


def calculate_spectral_correction(df_ref_grouped, df_new_grouped, selected_ids=None):
    """
    Calcula la corrección espectral promedio entre dos conjuntos de mediciones.
    
    Args:
        df_ref_grouped (pd.DataFrame): Mediciones de referencia
        df_new_grouped (pd.DataFrame): Mediciones nuevas
        selected_ids (list, optional): IDs a usar. Si None, usa todos.
        
    Returns:
        np.array: Vector de corrección espectral promedio
    """
    if selected_ids is None:
        selected_ids = df_ref_grouped.index.tolist()
    
    # Filtrar solo las muestras seleccionadas
    try:
        df_ref_sel = df_ref_grouped.loc[selected_ids]
        df_new_sel = df_new_grouped.loc[selected_ids]
    except KeyError:
        # Si algún ID no existe, filtrar solo los válidos
        valid_ids = [
            i for i in selected_ids 
            if i in df_ref_grouped.index and i in df_new_grouped.index
        ]
        df_ref_sel = df_ref_grouped.loc[valid_ids]
        df_new_sel = df_new_grouped.loc[valid_ids]
    
    # Calcular diferencias
    diff_matrix = df_ref_sel.values - df_new_sel.values
    mean_diff = diff_matrix.mean(axis=0)
    
    return mean_diff


def apply_baseline_correction(baseline_spectrum, correction_vector):
    """
    Aplica una corrección espectral a un baseline.
    
    Args:
        baseline_spectrum (np.array): Espectro del baseline original
        correction_vector (np.array): Vector de corrección
        
    Returns:
        np.array: Baseline corregido
    """
    corrected = baseline_spectrum - correction_vector
    return corrected


def simulate_corrected_spectra(df_kit, spectral_cols, lamp_new, 
                               baseline_original, baseline_corrected):
    """
    Simula cómo quedarían los espectros después de aplicar el baseline corregido.
    
    Args:
        df_kit (pd.DataFrame): DataFrame con mediciones del kit
        spectral_cols (list): Lista de columnas espectrales
        lamp_new (str): Nombre de la lámpara nueva
        baseline_original (np.array): Baseline original
        baseline_corrected (np.array): Baseline corregido
        
    Returns:
        pd.DataFrame: DataFrame con espectros corregidos
    """
    df_corrected = df_kit[df_kit["Note"] == lamp_new].copy()
    
    # Aplicar corrección
    correction = baseline_original - baseline_corrected
    df_corrected[spectral_cols] = (
        df_corrected[spectral_cols].astype(float).values + correction
    )
    
    return df_corrected
