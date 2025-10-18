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


def plot_correction_differences(df_diff, common_ids, selected_ids):
    """
    Crea gráfico de diferencias espectrales y corrección promedio.
    
    Args:
        df_diff (pd.DataFrame): DataFrame con diferencias y corrección
        common_ids (list): IDs comunes
        selected_ids (list): IDs seleccionados para corrección
        
    Returns:
        matplotlib.figure.Figure: Figura con el gráfico
    """
    fig, ax = plt.subplots(figsize=PLOT_CONFIG['figsize_default'])
    
    # Graficar diferencias por muestra
    for id_ in common_ids:
        alpha = 0.7 if id_ in selected_ids else 0.3
        linewidth = 1.5 if id_ in selected_ids else 0.8
        label_prefix = "✓ " if id_ in selected_ids else "✗ "
        
        ax.plot(
            df_diff["Canal"], 
            df_diff[f"DIF_{id_}"], 
            label=f"{label_prefix}{id_}", 
            alpha=alpha, 
            linewidth=linewidth
        )
    
    # Graficar corrección promedio
    ax.plot(
        df_diff["Canal"], 
        df_diff["CORRECCION_PROMEDIO"], 
        linewidth=3, 
        label="Corrección Promedio", 
        color='red',
        zorder=10
    )
    
    ax.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    ax.set_title(
        "Diferencias espectrales por muestra", 
        fontsize=12, 
        fontweight='bold'
    )
    ax.set_xlabel("Canal espectral")
    ax.set_ylabel("Diferencia")
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
    ax.grid(True, alpha=PLOT_CONFIG['alpha_grid'])
    plt.tight_layout()
    
    return fig


def plot_correction_summary(mean_diff):
    """
    Crea un gráfico simple del vector de corrección.
    
    Args:
        mean_diff (np.array): Vector de corrección promedio
        
    Returns:
        matplotlib.figure.Figure: Figura con el gráfico
    """
    fig, ax = plt.subplots(figsize=PLOT_CONFIG['figsize_default'])
    
    ax.plot(
        range(1, len(mean_diff) + 1), 
        mean_diff, 
        linewidth=PLOT_CONFIG['linewidth_default'],
        color='red'
    )
    ax.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    ax.set_title("Vector de Corrección Espectral", fontsize=12, fontweight='bold')
    ax.set_xlabel("Canal espectral")
    ax.set_ylabel("Corrección")
    ax.grid(True, alpha=PLOT_CONFIG['alpha_grid'])
    plt.tight_layout()
    
    return fig


def plot_baseline_comparison(baseline_original, baseline_corrected, spectral_cols):
    """
    Crea gráfico comparativo de baseline original vs corregido.
    
    Args:
        baseline_original (np.array): Baseline original
        baseline_corrected (np.array): Baseline corregido
        spectral_cols (list): Lista de columnas espectrales
        
    Returns:
        matplotlib.figure.Figure: Figura con el gráfico
    """
    fig, ax = plt.subplots(figsize=PLOT_CONFIG['figsize_default'])
    
    channels = range(1, len(baseline_original) + 1)
    
    ax.plot(
        channels, 
        baseline_original, 
        label="Baseline original", 
        linewidth=PLOT_CONFIG['linewidth_default']
    )
    ax.plot(
        channels, 
        baseline_corrected, 
        label="Baseline corregido", 
        linewidth=PLOT_CONFIG['linewidth_default'], 
        linestyle="--"
    )
    
    ax.set_title(
        "Comparación: baseline original vs corregido", 
        fontsize=12, 
        fontweight='bold'
    )
    ax.set_xlabel("Canal espectral")
    ax.set_ylabel("Intensidad")
    ax.legend()
    ax.grid(True, alpha=PLOT_CONFIG['alpha_grid'])
    plt.tight_layout()
    
    return fig


def plot_corrected_spectra_comparison(df_ref_grouped, df_corrected, spectral_cols, 
                                      lamp_ref, lamp_new, sample_ids, 
                                      title="Comparación de espectros"):
    """
    Crea gráfico comparando espectros de referencia vs corregidos.
    
    Args:
        df_ref_grouped (pd.DataFrame): Espectros de referencia
        df_corrected (pd.DataFrame): Espectros corregidos
        spectral_cols (list): Columnas espectrales
        lamp_ref (str): Nombre lámpara referencia
        lamp_new (str): Nombre lámpara nueva
        sample_ids (list): IDs de muestras a graficar
        title (str): Título del gráfico
        
    Returns:
        matplotlib.figure.Figure: Figura con el gráfico
    """
    fig, ax = plt.subplots(figsize=PLOT_CONFIG['figsize_report'])
    
    for id_ in sample_ids:
        spec_ref = df_ref_grouped.loc[id_].values
        spec_corr = df_corrected[df_corrected['ID'] == id_][spectral_cols].astype(float).mean().values
        
        ax.plot(
            range(1, len(spec_ref) + 1), 
            spec_ref, 
            label=f"{lamp_ref} - {id_}", 
            linewidth=1.5, 
            alpha=PLOT_CONFIG['alpha_spectrum']
        )
        ax.plot(
            range(1, len(spec_corr) + 1), 
            spec_corr, 
            linestyle="--", 
            label=f"{lamp_new} corregido - {id_}", 
            linewidth=1.5, 
            alpha=PLOT_CONFIG['alpha_spectrum']
        )
    
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.set_xlabel("Canal espectral")
    ax.set_ylabel("Absorbancia")
    ax.grid(True, alpha=PLOT_CONFIG['alpha_grid'])
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    
    return fig

def plot_baseline_spectrum(baseline_spectrum, lamp_name):
    """
    Crea gráfico del espectro de baseline.
    
    Args:
        baseline_spectrum (np.array): Espectro del baseline
        lamp_name (str): Nombre de la lámpara
        
    Returns:
        matplotlib.figure.Figure: Figura con el gráfico
    """
    fig, ax = plt.subplots(figsize=(12, 4))
    
    ax.plot(
        range(1, len(baseline_spectrum) + 1), 
        baseline_spectrum, 
        linewidth=PLOT_CONFIG['linewidth_default']
    )
    ax.set_title(
        f"Baseline original de {lamp_name}", 
        fontsize=12, 
        fontweight='bold'
    )
    ax.set_xlabel("Canal espectral")
    ax.set_ylabel("Intensidad")
    ax.grid(True, alpha=PLOT_CONFIG['alpha_grid'])
    plt.tight_layout()
    
    return fig
