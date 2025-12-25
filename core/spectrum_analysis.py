"""
Spectrum Analysis Utilities
============================
Funciones reutilizables para análisis de espectros NIR.
Parte del ecosistema COREF.

Author: Miquel
Date: 2024
"""

import numpy as np
import pandas as pd
from typing import List, Tuple


def validate_spectra_compatibility(spectra_list: List[np.ndarray]) -> Tuple[bool, str]:
    """
    Valida que todos los espectros tengan el mismo número de píxeles.
    
    Args:
        spectra_list: Lista de arrays numpy con espectros
        
    Returns:
        Tuple con (es_válido, mensaje_descriptivo)
    """
    if len(spectra_list) < 2:
        return False, "Se necesitan al menos 2 espectros para comparar"
    
    pixel_counts = [len(spec) for spec in spectra_list]
    
    if len(set(pixel_counts)) > 1:
        msg = "⚠️ Los espectros tienen diferente número de píxeles:\n"
        for i, count in enumerate(pixel_counts, 1):
            msg += f"  - Espectro {i}: {count} píxeles\n"
        return False, msg
    
    return True, f"✅ {len(spectra_list)} espectros compatibles ({pixel_counts[0]} píxeles cada uno)"


def calculate_statistics(spectra_list: List[np.ndarray], names: List[str], 
                         num_channels: int) -> pd.DataFrame:
    """
    Calcula estadísticas descriptivas para cada espectro.
    
    Args:
        spectra_list: Lista de arrays numpy con espectros
        names: Lista de nombres/etiquetas para cada espectro
        num_channels: Número de canales espectrales
        
    Returns:
        DataFrame con estadísticas por espectro
    """
    stats = []
    
    for name, spectrum in zip(names, spectra_list):
        stats.append({
            'Espectro': name,
            'Canales': num_channels,
            'Min': f"{spectrum.min():.6f}",
            'Max': f"{spectrum.max():.6f}",
            'Media': f"{spectrum.mean():.6f}",
            'Desv. Est.': f"{spectrum.std():.6f}",
            'Rango': f"{spectrum.max() - spectrum.min():.6f}"
        })
    
    return pd.DataFrame(stats)


def calculate_residuals(spectra_list: List[np.ndarray], reference_idx: int) -> List[np.ndarray]:
    """
    Calcula residuales de todos los espectros respecto a uno de referencia.
    
    Args:
        spectra_list: Lista de arrays numpy con espectros
        reference_idx: Índice del espectro de referencia
        
    Returns:
        Lista de arrays con residuales (diferencias punto a punto)
    """
    reference = spectra_list[reference_idx]
    residuals = []
    
    for i, spectrum in enumerate(spectra_list):
        if i == reference_idx:
            residuals.append(np.zeros_like(reference))
        else:
            residuals.append(spectrum - reference)
    
    return residuals


def calculate_correlation_matrix(spectra_list: List[np.ndarray], names: List[str]) -> np.ndarray:
    """
    Calcula matriz de correlación entre todos los espectros.
    
    Args:
        spectra_list: Lista de arrays numpy con espectros
        names: Lista de nombres (para debug, no se usa en cálculo)
        
    Returns:
        Matriz numpy NxN con coeficientes de correlación
    """
    n_spectra = len(spectra_list)
    corr_matrix = np.ones((n_spectra, n_spectra))
    
    for i in range(n_spectra):
        for j in range(i+1, n_spectra):
            try:
                # Validar y convertir a float64
                spec_i = np.asarray(spectra_list[i], dtype=np.float64).flatten()
                spec_j = np.asarray(spectra_list[j], dtype=np.float64).flatten()
                
                # Validaciones
                if len(spec_i) != len(spec_j) or len(spec_i) < 2:
                    corr_matrix[i, j] = np.nan
                    corr_matrix[j, i] = np.nan
                    continue
                
                if np.any(~np.isfinite(spec_i)) or np.any(~np.isfinite(spec_j)):
                    corr_matrix[i, j] = np.nan
                    corr_matrix[j, i] = np.nan
                    continue
                
                # Normalizar
                spec_i_norm = (spec_i - np.mean(spec_i)) / (np.std(spec_i) + 1e-10)
                spec_j_norm = (spec_j - np.mean(spec_j)) / (np.std(spec_j) + 1e-10)
                
                # Correlación manual
                corr = np.sum(spec_i_norm * spec_j_norm) / len(spec_i_norm)
                
                if np.isfinite(corr):
                    corr_matrix[i, j] = corr
                    corr_matrix[j, i] = corr
                else:
                    corr_matrix[i, j] = np.nan
                    corr_matrix[j, i] = np.nan
                    
            except Exception as e:
                print(f"Error calculando correlación ({i},{j}): {e}")
                corr_matrix[i, j] = np.nan
                corr_matrix[j, i] = np.nan
    
    return corr_matrix


def calculate_rms_matrix(spectra_list: List[np.ndarray]) -> np.ndarray:
    """
    Calcula matriz de diferencias RMS entre todos los pares de espectros.
    
    Args:
        spectra_list: Lista de arrays numpy con espectros
        
    Returns:
        Matriz numpy NxN con valores RMS
    """
    n_spectra = len(spectra_list)
    rms_matrix = np.zeros((n_spectra, n_spectra))
    
    for i in range(n_spectra):
        for j in range(n_spectra):
            if i == j:
                rms_matrix[i, j] = 0
            else:
                diff = spectra_list[i] - spectra_list[j]
                rms_matrix[i, j] = np.sqrt(np.mean(diff**2))
    
    return rms_matrix