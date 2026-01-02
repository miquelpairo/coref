"""
tsv_processing.py
=================
Funciones para limpieza y transformación de archivos TSV de NIR-Online.
Implementa la lógica de Node-RED para procesamiento de exports/journals.
"""

from typing import List, Dict, Optional
import re
import pandas as pd
from dateutil import parser as date_parser


# =============================================================================
# CONSTANTES Y REGEX
# =============================================================================

# Regex para detectar columnas espectrales (acepta #123 y 123)
PIXEL_RE = re.compile(r"^(#)?\d+$")


# =============================================================================
# FUNCIONES DE VALIDACIÓN
# =============================================================================

def is_pixel_col(col: str) -> bool:
    """
    Verifica si una columna es una columna espectral (píxel).
    
    Args:
        col: Nombre de la columna
        
    Returns:
        True si es columna espectral (#1, #2, ... o 1, 2, ...)
    """
    return bool(PIXEL_RE.fullmatch(str(col)))


def pixel_number(col: str) -> int:
    """
    Extrae el número de píxel de una columna espectral.
    
    Args:
        col: Nombre de la columna (#123 o 123)
        
    Returns:
        Número de píxel como int
    """
    s = str(col)
    return int(s[1:]) if s.startswith("#") else int(s)


# =============================================================================
# LIMPIEZA DE VALORES
# =============================================================================

def clean_value(v: str) -> Optional[float]:
    """
    Limpia un valor removiendo unidades comunes y convirtiendo a float.
    
    Maneja casos como:
    - Valores vacíos, "-", "NA", "NaN"
    - Valores con unidades: "12.5%", "100ppm"
    - Comas decimales: "12,5" -> 12.5
    - Valores malformados: "-.", "-.-"
    
    Args:
        v: Valor a limpiar (string)
        
    Returns:
        Valor float o None si no se pudo convertir
    """
    if v is None:
        return None
    
    s = str(v).strip()
    
    # Valores vacíos o especiales
    if s in ("", "-", "NA", "NaN", "nan"):
        return None
    
    # Valores malformados
    if s.startswith("-.") or s.startswith("-.-"):
        return None
    
    # Remover unidades comunes
    s = s.replace("%", "").replace("ppm", "").replace(",", ".").strip()
    
    # Re-verificar después de limpieza
    if s in ("", "-", "NA", "NaN", "nan"):
        return None
    
    try:
        return float(s)
    except Exception:
        return None


# =============================================================================
# FILTRADO DE COLUMNAS
# =============================================================================

def filter_relevant_data(data: List[Dict]) -> List[Dict]:
    """
    Mantiene metadata hasta columna #X1 + todas las columnas espectrales.
    
    Lógica Node-RED:
    - Columnas metadata: desde inicio hasta #X1 (exclusive)
    - Columnas espectrales: todas las que cumplen PIXEL_RE
    
    Args:
        data: Lista de diccionarios (filas del TSV)
        
    Returns:
        Lista filtrada con solo columnas relevantes
    """
    if not data:
        return []
    
    all_columns = list(data[0].keys())
    stop_column = "#X1"
    
    # Extraer columnas metadata (hasta #X1)
    base_cols: List[str] = []
    for col in all_columns:
        if col == stop_column:
            break
        base_cols.append(col)
    
    # Extraer columnas espectrales y ordenar por número
    pixel_cols = sorted(
        [c for c in all_columns if is_pixel_col(c)],
        key=pixel_number
    )
    
    columns_to_keep = base_cols + pixel_cols
    
    # Filtrar cada fila
    filtered: List[Dict] = []
    for row in data:
        new_row = {}
        for col in columns_to_keep:
            v = row.get(col, None)
            new_row[col] = v if v not in ("", None) else None
        filtered.append(new_row)
    
    return filtered


# =============================================================================
# LIMPIEZA DE FILAS
# =============================================================================

def delete_zero_rows(data: List[Dict]) -> List[Dict]:
    """
    Elimina filas donde Result esté vacío o todos los valores sean 0.
    
    Criterios de eliminación:
    - Sin columna "Result"
    - Result vacío o None
    - Todos los valores Result son 0.0
    
    Args:
        data: Lista de diccionarios (filas)
        
    Returns:
        Lista filtrada sin filas inválidas
    """
    out: List[Dict] = []
    
    for row in data:
        if "Result" not in row:
            continue
        
        result_val = row.get("Result")
        if result_val is None or str(result_val).strip() == "":
            continue
        
        # Result puede tener múltiples valores separados por ";"
        result_values = str(result_val).split(";")
        cleaned = [clean_value(v) for v in result_values]
        cleaned = [v for v in cleaned if v is not None]
        
        if not cleaned:
            continue
        
        # Descartar si todos los valores son 0
        if all(v == 0.0 for v in cleaned):
            continue
        
        out.append(row)
    
    return out


# =============================================================================
# REORGANIZACIÓN DE PARÁMETROS
# =============================================================================

def reorganize_results_and_reference(data: List[Dict]) -> List[Dict]:
    """
    Reorganiza columnas a formato: Reference <param>, Result <param>, Residuum <param>.
    
    Lógica:
    - Extrae parámetros entre "Reference" y "Begin"
    - Para cada parámetro crea 3 columnas: Reference, Result, Residuum
    - Result puede venir de columna "Result" (valores separados por ";")
    - Residuum = Result - Reference
    
    Args:
        data: Lista de diccionarios (filas)
        
    Returns:
        Lista con columnas reorganizadas
    """
    if not data:
        return []
    
    reorganized: List[Dict] = []
    
    for row in data:
        all_cols = list(row.keys())
        
        # Verificar que existan columnas clave
        if "Reference" not in all_cols or "Begin" not in all_cols:
            reorganized.append(row)
            continue
        
        ref_i = all_cols.index("Reference")
        begin_i = all_cols.index("Begin")
        
        # Columnas de parámetros (entre Reference y Begin)
        parameter_cols = all_cols[ref_i + 1: begin_i]
        
        # Construir nueva fila
        new_row: Dict = {}
        
        # Copiar columnas que no son parámetros ni Result/Reference
        for key in all_cols:
            if key in parameter_cols or key in ("Result", "Reference"):
                continue
            new_row[key] = row.get(key)
        
        # Extraer valores Result (separados por ";")
        result_values: List[str] = []
        if row.get("Result") is not None:
            result_values = [v.strip() for v in str(row["Result"]).split(";")]
        
        # Para cada parámetro, crear Reference/Result/Residuum
        for idx, param in enumerate(parameter_cols):
            ref_val = row.get(param)
            ref_val_f = clean_value(ref_val) if (ref_val not in (None, "")) else None
            
            # Result puede venir de lista Result o de la columna del parámetro
            res_val_f = None
            if idx < len(result_values):
                res_val_f = clean_value(result_values[idx])
            
            # Fallback: usar valor directo de la columna del parámetro
            if res_val_f is None:
                param_col_val = row.get(param)
                if param_col_val is not None and param_col_val != "":
                    res_val_f = clean_value(param_col_val)
            
            # Crear columnas
            new_row[f"Reference {param}"] = ref_val_f
            new_row[f"Result {param}"] = res_val_f
            
            # Calcular residuum
            if ref_val_f is not None and res_val_f is not None:
                new_row[f"Residuum {param}"] = res_val_f - ref_val_f
            else:
                new_row[f"Residuum {param}"] = None
        
        reorganized.append(new_row)
    
    return reorganized


# =============================================================================
# PARSING DE FECHAS
# =============================================================================

def try_parse_date(date_str) -> pd.Timestamp:
    """
    Intenta convertir una fecha con múltiples formatos comunes.
    
    Formatos soportados:
    - dd/mm/yyyy
    - mm/dd/yyyy
    - yyyy-mm-dd
    - yyyy-mm-dd HH:MM:SS
    - Cualquier formato válido detectado por dateutil
    
    Args:
        date_str: String con la fecha
        
    Returns:
        pd.Timestamp o pd.NaT si no se pudo parsear
    """
    if pd.isna(date_str) or date_str is None or str(date_str).strip() == "":
        return pd.NaT
    
    s = str(date_str).strip()
    
    # Intentar formatos comunes primero
    formats = [
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%m-%d-%Y",
        "%Y-%m-%d %H:%M:%S"
    ]
    
    for fmt in formats:
        try:
            return pd.to_datetime(s, format=fmt)
        except Exception:
            pass
    
    # Fallback: usar dateutil parser
    try:
        return pd.to_datetime(date_parser.parse(s, dayfirst=True))
    except Exception:
        return pd.NaT


# =============================================================================
# PIPELINE COMPLETO
# =============================================================================

def clean_tsv_file(uploaded_file, encodings_to_try: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Pipeline completo de limpieza de archivo TSV.
    
    Pasos:
    1. Lectura con múltiples encodings
    2. Filtrado de columnas relevantes
    3. Eliminación de filas inválidas
    4. Reorganización de parámetros
    5. Conversión de columnas espectrales a float
    6. Parsing de fechas
    
    Args:
        uploaded_file: Archivo cargado (BytesIO o similar)
        encodings_to_try: Lista de encodings a probar (opcional)
        
    Returns:
        DataFrame limpio y procesado
        
    Raises:
        ValueError: Si no se pudo leer el archivo con ningún encoding
    """
    if encodings_to_try is None:
        encodings_to_try = ["utf-8", "ISO-8859-1", "latin-1", "cp1252"]
    
    uploaded_file.seek(0)
    df_raw = None
    
    # Intentar leer con diferentes encodings
    for encoding in encodings_to_try:
        try:
            uploaded_file.seek(0)
            df_raw = pd.read_csv(
                uploaded_file,
                delimiter="\t",
                keep_default_na=False,
                encoding=encoding
            )
            break
        except UnicodeDecodeError:
            continue
        except Exception:
            # Intentar con escapechar si falla
            try:
                uploaded_file.seek(0)
                df_raw = pd.read_csv(
                    uploaded_file,
                    delimiter="\t",
                    keep_default_na=False,
                    encoding=encoding,
                    doublequote=False,
                    escapechar="\\"
                )
                break
            except Exception:
                continue
    
    if df_raw is None:
        raise ValueError("❌ No se pudo leer el archivo con ningún encoding")
    
    # Pipeline de transformaciones
    data = df_raw.to_dict("records")
    data = filter_relevant_data(data)
    data = delete_zero_rows(data)
    data = reorganize_results_and_reference(data)
    
    df = pd.DataFrame(data)
    
    # Convertir columnas espectrales a float
    if not df.empty:
        pixel_cols = [c for c in df.columns if is_pixel_col(c)]
        if pixel_cols:
            df[pixel_cols] = df[pixel_cols].astype(str).replace(",", ".", regex=True)
            df[pixel_cols] = df[pixel_cols].apply(pd.to_numeric, errors="coerce")
    
    # Parsear columna Date si existe
    if "Date" in df.columns:
        df["Date"] = df["Date"].apply(try_parse_date)
    
    return df


# =============================================================================
# UTILIDADES AUXILIARES
# =============================================================================

def get_spectral_columns(df: pd.DataFrame) -> List[str]:
    """
    Extrae las columnas espectrales de un DataFrame.
    
    Args:
        df: DataFrame procesado
        
    Returns:
        Lista ordenada de nombres de columnas espectrales
    """
    pixel_cols = [c for c in df.columns if is_pixel_col(c)]
    return sorted(pixel_cols, key=pixel_number)


def get_parameter_columns(df: pd.DataFrame, prefix: str = "Result ") -> List[str]:
    """
    Extrae columnas de parámetros con un prefijo dado.
    
    Args:
        df: DataFrame procesado
        prefix: Prefijo a buscar ("Result ", "Reference ", "Residuum ")
        
    Returns:
        Lista de nombres de columnas que empiezan con el prefijo
    """
    return [c for c in df.columns if str(c).startswith(prefix)]


def extract_parameter_names(df: pd.DataFrame) -> List[str]:
    """
    Extrae nombres de parámetros (sin prefijo "Result ").
    
    Args:
        df: DataFrame procesado
        
    Returns:
        Lista de nombres de parámetros
    """
    result_cols = get_parameter_columns(df, "Result ")
    return [str(c).replace("Result ", "") for c in result_cols]