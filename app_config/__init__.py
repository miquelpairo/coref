# -*- coding: utf-8 -*-
"""
NIR ServiceKit - Configuración Central
Re-exporta todos los módulos de configuración
"""

# Importar módulos individualmente
import config.app
import config.paths
import config.thresholds
import config.plotting
import config.messages
import config.reports
import config.metadata

# Re-exportar todo explícitamente
from config.app import PAGE_CONFIG, STEPS, VERSION, VERSION_DATE, VERSION_NOTES
from config.paths import BASELINE_PATHS, SUPPORTED_EXTENSIONS
from config.thresholds import (
    WSTD_THRESHOLDS, VALIDATION_THRESHOLDS, VALIDATION_RMS_THRESHOLD,
    WHITE_REFERENCE_THRESHOLDS, DEFAULT_VALIDATION_THRESHOLDS,
    CRITICAL_REGIONS, OFFSET_LIMITS, DIAGNOSTIC_STATUS, VALIDATION_STATUS
)
from config.plotting import PLOT_CONFIG, BUCHI_COLORS, PLOTLY_TEMPLATE
from config.messages import MESSAGES, INSTRUCTIONS, SPECIAL_IDS
from config.reports import REPORT_STYLE
from config.metadata import DEFAULT_CSV_METADATA, CONTROL_SAMPLES_CONFIG

__all__ = [
    # App
    'PAGE_CONFIG', 'STEPS', 'VERSION', 'VERSION_DATE', 'VERSION_NOTES',
    # Paths
    'BASELINE_PATHS', 'SUPPORTED_EXTENSIONS',
    # Thresholds
    'WSTD_THRESHOLDS', 'VALIDATION_THRESHOLDS', 'VALIDATION_RMS_THRESHOLD',
    'WHITE_REFERENCE_THRESHOLDS', 'DEFAULT_VALIDATION_THRESHOLDS',
    'CRITICAL_REGIONS', 'OFFSET_LIMITS', 'DIAGNOSTIC_STATUS', 'VALIDATION_STATUS',
    # Plotting
    'PLOT_CONFIG', 'BUCHI_COLORS', 'PLOTLY_TEMPLATE',
    # Messages
    'MESSAGES', 'INSTRUCTIONS', 'SPECIAL_IDS',
    # Reports
    'REPORT_STYLE',
    # Metadata
    'DEFAULT_CSV_METADATA', 'CONTROL_SAMPLES_CONFIG',
]