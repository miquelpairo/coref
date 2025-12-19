"""
Parsers para informes HTML NIR
Extraen información de los informes de Baseline, Validación y Predicciones
"""

from .baseline_parser import BaselineParser
from .validation_parser import ValidationParser
from .predictions_parser import PredictionsParser

__all__ = [
    'BaselineParser',
    'ValidationParser', 
    'PredictionsParser'
]