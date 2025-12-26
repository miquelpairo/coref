"""
Funciones de validación
"""
import streamlit as st
from app_config import MESSAGES


def validate_wstd_measurements(df_wstd, lamps):
    """
    Valida que las mediciones WSTD sean correctas.
    
    Args:
        df_wstd (pd.DataFrame): DataFrame con mediciones WSTD
        lamps (list): Lista de lámparas detectadas
        
    Returns:
        bool: True si la validación es exitosa
    """
    if len(lamps) == 0:
        st.error("❌ No se detectaron lámparas en las mediciones WSTD")
        return False
    
    return True


def validate_common_samples(common_ids):
    """
    Valida que existan muestras comunes entre lámparas.
    
    Args:
        common_ids (list): Lista de IDs comunes
        
    Returns:
        bool: True si hay muestras comunes
    """
    if len(common_ids) == 0:
        st.error(MESSAGES['error_no_common_samples'])
        return False
    
    return True


def validate_dimension_match(baseline_length, tsv_length):
    """
    Valida que las dimensiones del baseline y TSV coincidan.
    
    Args:
        baseline_length (int): Número de puntos en el baseline
        tsv_length (int): Número de canales en el TSV
        
    Returns:
        bool: True si las dimensiones coinciden
    """
    return baseline_length == tsv_length
