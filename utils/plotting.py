"""
Funciones de visualización con Matplotlib
"""
import matplotlib.pyplot as plt
import numpy as np
from config import PLOT_CONFIG


def plot_wstd_spectra(df_wstd_grouped, spectral_cols, lamps):
    """
    Crea gráficos de espectros WSTD y diferencias.
    
    Args:
        df_wstd_grouped (pd.DataFrame): DataFrame agrupado por lámpara
        spectral_cols (list): Lista de columnas espectrales
        lamps (list): Lista de nombres de lámparas
        
    Returns:
        matplotlib.figure.Figure: Figura con los gráficos
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=PLOT_CONFIG['figsize_large'])
    
    # Gráfico 1: Espectros de cada lámpara
    for lamp in df_wstd_grouped.index:
        spectrum = df_wstd_grouped.loc[lamp].values
        ax1.plot(
            range(1, len(spectral_cols) + 1), 
            spectrum, 
            label=lamp, 
            linewidth=PLOT_CONFIG['linewidth_default']
        )
    
    ax1.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    ax1.set_title(
        "Espectros del White Standard (sin línea base)", 
        fontsize=12, 
        fontweight='bold'
    )
    ax1.set_xlabel("Canal espectral")
    ax1.set_ylabel("Intensidad")
    ax1.legend()
    ax1.grid(True, alpha=PLOT_CONFIG['alpha_grid'])
    
    # Gráfico 2: Diferencia entre lámparas
    if len(df_wstd_grouped) == 2:
        lamp1, lamp2 = df_wstd_grouped.index[0], df_wstd_grouped.index[1]
        diff = df_wstd_grouped.loc[lamp1].values - df_wstd_grouped.loc[lamp2].values
        ax2.plot(
            range(1, len(spectral_cols) + 1), 
            diff, 
            linewidth=PLOT_CONFIG['linewidth_default']
        )
        ax2.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        ax2.set_title(
            f"Diferencia espectral: {lamp1} - {lamp2}", 
            fontsize=12, 
            fontweight='bold'
        )
        ax2.set_xlabel("Canal espectral")
        ax2.set_ylabel("Diferencia")
        ax2.grid(True, alpha=PLOT_CONFIG['alpha_grid'])
    else:
        ax2.text(
            0.5, 0.5, 
            'Se necesitan 2 lámparas para mostrar diferencias',
            ha='center', 
            va='center', 
            transform=ax2.transAxes
        )
        ax2.set_xlim(0, 1)
        ax2.set_ylim(0, 1)
    
    plt.tight_layout()
    return fig


def plot_wstd_difference(df_wstd_grouped, spectral_cols):
    """
    Crea un gráfico solo con la diferencia entre dos lámparas.
    
    Args:
        df_wstd_grouped (pd.DataFrame): DataFrame agrupado por lámpara
        spectral_cols (list): Lista de columnas espectrales
        
    Returns:
        matplotlib.figure.Figure: Figura con el gráfico de diferencia
    """
    fig, ax = plt.subplots(figsize=PLOT_CONFIG['figsize_default'])
    
    if len(df_wstd_grouped) >= 2:
        lamp1, lamp2 = df_wstd_grouped.index[0], df_wstd_grouped.index[1]
        diff = df_wstd_grouped.loc[lamp1].values - df_wstd_grouped.loc[lamp2].values
        
        ax.plot(
            range(1, len(spectral_cols) + 1), 
            diff, 
            linewidth=PLOT_CONFIG['linewidth_default']
        )
        ax.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        ax.set_title(
            f"Diferencia espectral: {lamp1} - {lamp2}", 
            fontsize=12, 
            fontweight='bold'
        )
        ax.set_xlabel("Canal espectral")
        ax.set_ylabel("Diferencia")
        ax.grid(True, alpha=PLOT_CONFIG['alpha_grid'])
    
    plt.tight_layout()
    return fig

def plot_kit_spectra(df_ref_grouped, df_new_grouped, spectral_cols, 
                     lamp_ref, lamp_new, common_ids):
    """
    Crea gráfico comparativo de espectros del kit.
    
    Args:
        df_ref_grouped (pd.DataFrame): Mediciones de referencia
        df_new_grouped (pd.DataFrame): Mediciones nuevas
        spectral_cols (list): Columnas espectrales
        lamp_ref (str): Nombre lámpara referencia
        lamp_new (str): Nombre lámpara nueva
        common_ids (list): IDs comunes
        
    Returns:
        matplotlib.figure.Figure: Figura con el gráfico
    """
    fig, ax = plt.subplots(figsize=PLOT_CONFIG['figsize_default'])
    
    for id_ in common_ids:
        ax.plot(
            range(1, len(spectral_cols) + 1), 
            df_ref_grouped.loc[id_],
            label=f"{lamp_ref} - {id_}", 
            alpha=0.7, 
            linewidth=PLOT_CONFIG['linewidth_thin']
        )
        ax.plot(
            range(1, len(spectral_cols) + 1), 
            df_new_grouped.loc[id_],
            linestyle="--", 
            label=f"{lamp_new} - {id_}", 
            alpha=0.7, 
            linewidth=PLOT_CONFIG['linewidth_thin']
        )
    
    ax.set_title("Espectros promedio por muestra")
    ax.set_xlabel("Canal espectral")
    ax.set_ylabel("Absorbancia")
    ax.grid(True, alpha=PLOT_CONFIG['alpha_grid'])
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    
    return fig
