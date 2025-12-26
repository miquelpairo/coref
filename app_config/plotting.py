# -*- coding: utf-8 -*-
"""
Configuración de gráficos y visualizaciones
"""

# ============================================================================
# CONFIGURACIÓN DE GRÁFICOS
# ============================================================================

PLOT_CONFIG = {
    'figsize_default': (12, 6),
    'figsize_large': (12, 8),
    'figsize_report': (14, 7),
    'dpi': 150,
    'alpha_spectrum': 0.85,
    'alpha_grid': 0.3,
    'linewidth_default': 2,
    'linewidth_thin': 1,
}

# ============================================================================
# COLORES CORPORATIVOS BUCHI
# ============================================================================

BUCHI_COLORS = {
    'primary': '#093A34',
    'secondary': '#289A93',
    'accent': '#00BFA5',
    'success': '#28a745',
    'warning': '#ffc107',
    'danger': '#dc3545',
    'info': '#17a2b8',
    'light': '#f8f9fa',
    'dark': '#343a40',
}

# ============================================================================
# PLANTILLA PLOTLY
# ============================================================================

PLOTLY_TEMPLATE = {
    'layout': {
        'colorway': ['#093A34', '#289A93', '#00BFA5', '#FF6B6B', '#4ECDC4'],
        'font': {'family': 'Segoe UI, Arial, sans-serif'},
        'plot_bgcolor': 'white',
        'paper_bgcolor': 'white',
    }
}