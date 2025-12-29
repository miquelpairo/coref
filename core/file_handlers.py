"""
Manejo de archivos (lectura y escritura)
"""
import pandas as pd
import numpy as np
import io
import json
from datetime import datetime
from app_config import DEFAULT_CSV_METADATA
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET


def load_tsv_file(file):
    """
    Carga un archivo TSV y lo convierte a DataFrame.
    Maneja múltiples encodings, BOM y compatibilidad con iOS.
    
    Args:
        file: Archivo subido por Streamlit
        
    Returns:
        pd.DataFrame: DataFrame con los datos del archivo
    """
    # Probar varios encodings en orden (añadido más encodings comunes)
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1', 'windows-1252']
    
    # CRÍTICO: Leer TODO el archivo como bytes UNA SOLA VEZ
    file.seek(0)
    try:
        raw_content = file.read()
    except Exception as e:
        raise ValueError(f"Error al leer el archivo: {e}")
    
    # Asegurar que tenemos bytes
    if not isinstance(raw_content, bytes):
        # Si ya es string, intentar convertir
        try:
            raw_content = raw_content.encode('utf-8')
        except:
            raw_content = str(raw_content).encode('utf-8')
    
    # Intentar cada encoding
    last_error = None
    for encoding in encodings:
        try:
            # Decodificar bytes a string
            content = raw_content.decode(encoding)
            
            # Eliminar BOM si existe (común en archivos de Windows)
            if content.startswith('\ufeff'):
                content = content[1:]
            
            # Reemplazar comas por puntos (formato decimal europeo)
            content = content.replace(",", ".")
            
            # Normalizar saltos de línea (crítico para iOS)
            content = content.replace('\r\n', '\n').replace('\r', '\n')
            
            # Eliminar líneas vacías al inicio y final
            content = content.strip()
            
            # Leer como CSV con pandas
            df = pd.read_csv(
                io.StringIO(content), 
                sep="\t",
                encoding=None,  # Ya está decodificado
                on_bad_lines='skip',  # Ignorar líneas problemáticas
                engine='python'  # Motor más robusto para casos edge
            )
            
            # Validar que tiene columnas y filas
            if len(df.columns) == 0:
                last_error = f"Encoding {encoding}: DataFrame vacío (sin columnas)"
                continue
            
            if len(df) == 0:
                last_error = f"Encoding {encoding}: DataFrame vacío (sin filas)"
                continue
            
            # ✅ Si llegamos aquí, el archivo se cargó correctamente
            return df
            
        except (UnicodeDecodeError, UnicodeError) as e:
            last_error = f"Encoding {encoding}: {str(e)[:50]}"
            continue
        except pd.errors.ParserError as e:
            last_error = f"Encoding {encoding}: Error de parseo - {str(e)[:50]}"
            continue
        except Exception as e:
            last_error = f"Encoding {encoding}: {str(e)[:50]}"
            continue
    
    # Si todos los encodings fallan, dar mensaje detallado
    error_msg = (
        "❌ No se pudo cargar el archivo TSV.\n\n"
        f"Último error: {last_error}\n\n"
        "Verifica que:\n"
        "1. El archivo está separado por TABULADORES (\\t)\n"
        "2. El archivo no está corrupto\n"
        "3. En iPhone: usa Safari en lugar de Chrome\n"
        "4. Si persiste, intenta:\n"
        "   - Abrir el archivo en Excel/Numbers\n"
        "   - Guardar como CSV UTF-8\n"
        "   - Volver a intentar la carga"
    )
    raise ValueError(error_msg)


def load_xml_file(file):
    """
    Carga un archivo XML y devuelve el árbol parseado.
    Maneja múltiples encodings y compatibilidad con iOS.
    
    Args:
        file: Archivo subido por Streamlit
        
    Returns:
        tuple: (tree, root, encoding_used) donde:
            - tree: ElementTree completo
            - root: Elemento raíz del XML
            - encoding_used: Encoding detectado que funcionó
    """
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1', 'windows-1252']
    
    # Leer archivo como bytes UNA SOLA VEZ
    file.seek(0)
    try:
        raw_content = file.read()
    except Exception as e:
        raise ValueError(f"Error al leer el archivo XML: {e}")
    
    # Asegurar que tenemos bytes
    if not isinstance(raw_content, bytes):
        try:
            raw_content = raw_content.encode('utf-8')
        except:
            raw_content = str(raw_content).encode('utf-8')
    
    last_error = None
    for encoding in encodings:
        try:
            # Decodificar bytes a string
            content = raw_content.decode(encoding)
            
            # Eliminar BOM si existe
            if content.startswith('\ufeff'):
                content = content[1:]
            
            # Normalizar saltos de línea
            content = content.replace('\r\n', '\n').replace('\r', '\n')
            
            # Parsear XML
            tree = ET.ElementTree(ET.fromstring(content))
            root = tree.getroot()
            
            # ✅ Si llegamos aquí, el XML se parseó correctamente
            return tree, root, encoding
            
        except (UnicodeDecodeError, UnicodeError) as e:
            last_error = f"Encoding {encoding}: {str(e)[:50]}"
            continue
        except ET.ParseError as e:
            last_error = f"Encoding {encoding}: Error de parseo XML - {str(e)[:100]}"
            continue
        except Exception as e:
            last_error = f"Encoding {encoding}: {str(e)[:50]}"
            continue
    
    # Si todos fallan
    error_msg = (
        "❌ No se pudo cargar el archivo XML.\n\n"
        f"Último error: {last_error}\n\n"
        "Verifica que:\n"
        "1. El archivo es un XML válido\n"
        "2. El archivo no está corrupto\n"
        "3. En iPhone: usa Safari en lugar de Chrome"
    )
    raise ValueError(error_msg)


def load_html_file(file):
    """
    Carga un archivo HTML y devuelve el objeto BeautifulSoup parseado.
    Maneja múltiples encodings y compatibilidad con iOS.
    
    Args:
        file: Archivo subido por Streamlit
        
    Returns:
        tuple: (soup, encoding_used) donde:
            - soup: Objeto BeautifulSoup con el HTML parseado
            - encoding_used: Encoding detectado que funcionó
    """
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1', 'windows-1252']
    
    # Leer archivo como bytes UNA SOLA VEZ
    file.seek(0)
    try:
        raw_content = file.read()
    except Exception as e:
        raise ValueError(f"Error al leer el archivo HTML: {e}")
    
    # Asegurar que tenemos bytes
    if not isinstance(raw_content, bytes):
        try:
            raw_content = raw_content.encode('utf-8')
        except:
            raw_content = str(raw_content).encode('utf-8')
    
    last_error = None
    for encoding in encodings:
        try:
            # Decodificar bytes a string
            content = raw_content.decode(encoding)
            
            # Eliminar BOM si existe
            if content.startswith('\ufeff'):
                content = content[1:]
            
            # Normalizar saltos de línea
            content = content.replace('\r\n', '\n').replace('\r', '\n')
            
            # Parsear HTML con BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # Validar que se parseó algo
            if soup is None or len(soup.get_text().strip()) == 0:
                last_error = f"Encoding {encoding}: HTML vacío después de parsear"
                continue
            
            # ✅ Si llegamos aquí, el HTML se parseó correctamente
            return soup, encoding
            
        except (UnicodeDecodeError, UnicodeError) as e:
            last_error = f"Encoding {encoding}: {str(e)[:50]}"
            continue
        except Exception as e:
            last_error = f"Encoding {encoding}: {str(e)[:50]}"
            continue
    
    # Si todos fallan
    error_msg = (
        "❌ No se pudo cargar el archivo HTML.\n\n"
        f"Último error: {last_error}\n\n"
        "Verifica que:\n"
        "1. El archivo es un HTML válido\n"
        "2. El archivo no está corrupto\n"
        "3. En iPhone: usa Safari en lugar de Chrome"
    )
    raise ValueError(error_msg)


def xml_to_dict(element):
    """
    Convierte un elemento XML a diccionario recursivamente.
    Útil para trabajar con datos XML de forma más sencilla.
    
    Args:
        element: Elemento XML (ET.Element)
        
    Returns:
        dict: Diccionario con la estructura del XML
    """
    result = {}
    
    # Agregar atributos
    if element.attrib:
        result['@attributes'] = element.attrib
    
    # Agregar texto
    if element.text and element.text.strip():
        result['text'] = element.text.strip()
    
    # Agregar hijos recursivamente
    for child in element:
        child_data = xml_to_dict(child)
        
        if child.tag in result:
            # Si ya existe, convertir a lista
            if not isinstance(result[child.tag], list):
                result[child.tag] = [result[child.tag]]
            result[child.tag].append(child_data)
        else:
            result[child.tag] = child_data
    
    return result


def extract_tables_from_html(soup):
    """
    Extrae todas las tablas de un HTML y las convierte a DataFrames.
    
    Args:
        soup: Objeto BeautifulSoup con el HTML parseado
        
    Returns:
        list: Lista de DataFrames, uno por cada tabla encontrada
    """
    tables = soup.find_all('table')
    dataframes = []
    
    for table in tables:
        # Intentar parsear cada tabla
        try:
            df = pd.read_html(str(table))[0]
            dataframes.append(df)
        except Exception as e:
            # Si falla una tabla, continuar con las demás
            continue
    
    return dataframes


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
        if col.startswith("#") and col[1:].replace('.', '').replace('-', '').isdigit()
    ]
    return spectral_cols


def load_ref_file(file):
    """
    Carga un archivo .ref (formato binario).
    Compatible con iOS.
    
    Args:
        file: Archivo subido por Streamlit
        
    Returns:
        tuple: (header, spectrum) donde header son los 3 primeros valores
               y spectrum es el array con los datos espectrales
    """
    try:
        file.seek(0)
        raw_bytes = file.read()
        
        # Asegurar que tenemos bytes
        if not isinstance(raw_bytes, bytes):
            raise ValueError("El archivo .ref no es binario")
        
        ref_data = np.frombuffer(raw_bytes, dtype=np.float32)
        
        if len(ref_data) < 4:
            raise ValueError("El archivo .ref es demasiado pequeño")
        
        header = ref_data[:3]
        spectrum = ref_data[3:]
        
        return header, spectrum
        
    except Exception as e:
        raise ValueError(f"Error al leer archivo .ref: {e}")


def load_csv_baseline(file):
    """
    Carga un archivo CSV de baseline (formato nuevo).
    Lee la última línea del CSV (baseline más reciente).
    Compatible con iOS.
    
    Args:
        file: Archivo subido por Streamlit
        
    Returns:
        tuple: (df, spectrum) donde df es el DataFrame completo
               y spectrum es el array de datos espectrales de la última línea
    """
    try:
        # Leer bytes primero (mejor para iOS)
        file.seek(0)
        raw_content = file.read()
        
        # Convertir a string si es necesario
        if isinstance(raw_content, bytes):
            # Probar UTF-8 primero, luego latin-1
            try:
                content = raw_content.decode('utf-8')
            except UnicodeDecodeError:
                content = raw_content.decode('latin-1')
        else:
            content = raw_content
        
        # Leer CSV desde string
        df = pd.read_csv(io.StringIO(content))
        
        if 'data' not in df.columns:
            raise ValueError("El archivo CSV no tiene la columna 'data'")
        
        # Leer la ÚLTIMA línea (baseline más reciente)
        data_string = df['data'].iloc[-1]
        spectrum = np.array(json.loads(data_string))
        
        return df, spectrum
        
    except Exception as e:
        raise ValueError(f"Error al cargar CSV baseline: {e}")


def export_ref_file(spectrum, header):
    """
    Exporta un espectro como archivo .ref binario.
    
    Args:
        spectrum (np.array): Espectro a exportar
        header (np.array): Cabecera del sensor (3 valores)
        
    Returns:
        bytes: Contenido del archivo .ref en bytes
    """
    final_ref = np.concatenate([header, spectrum.astype(np.float32)])
    ref_bytes = io.BytesIO()
    ref_bytes.write(final_ref.astype(np.float32).tobytes())
    ref_bytes.seek(0)
    return ref_bytes.getvalue()


def export_csv_file(spectrum, df_baseline=None):
    """
    Exporta un espectro como archivo CSV.
    Si existe un baseline previo, AÑADE la nueva línea al final.
    Si no existe, crea un CSV nuevo con una sola línea.
    
    Args:
        spectrum (np.array): Espectro a exportar
        df_baseline (pd.DataFrame, optional): DataFrame base con metadatos.
                                              Si es None, usa valores por defecto.
        
    Returns:
        str: Contenido del archivo CSV
    """
    # Crear nueva fila con el espectro ajustado
    if df_baseline is not None:
        # Tomar la última fila como template para metadatos
        new_row = df_baseline.iloc[-1].copy()
        
        # Actualizar timestamp y data
        new_row['time_stamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        new_row['data'] = json.dumps(spectrum.tolist())
        
        # AÑADIR la nueva fila al final del DataFrame existente
        df_export = pd.concat([df_baseline, pd.DataFrame([new_row])], ignore_index=True)
    else:
        # Usar metadatos por defecto (CSV nuevo)
        metadata = DEFAULT_CSV_METADATA.copy()
        metadata['time_stamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        metadata['nir_pixels'] = len(spectrum)
        metadata['data'] = json.dumps(spectrum.tolist())
        df_export = pd.DataFrame([metadata])
    
    csv_bytes = io.StringIO()
    df_export.to_csv(csv_bytes, index=False)
    return csv_bytes.getvalue()


def export_xml_file(data_dict, root_tag='root'):
    """
    Exporta un diccionario a formato XML.
    
    Args:
        data_dict (dict): Diccionario con los datos a exportar
        root_tag (str): Nombre del tag raíz del XML
        
    Returns:
        str: Contenido del archivo XML como string
    """
    def dict_to_xml(parent, data):
        """Función recursiva para convertir dict a XML"""
        if isinstance(data, dict):
            for key, value in data.items():
                if key == '@attributes':
                    # Agregar atributos al elemento padre
                    for attr_key, attr_value in value.items():
                        parent.set(attr_key, str(attr_value))
                elif key == 'text':
                    parent.text = str(value)
                else:
                    child = ET.SubElement(parent, key)
                    dict_to_xml(child, value)
        elif isinstance(data, list):
            for item in data:
                dict_to_xml(parent, item)
        else:
            parent.text = str(data)
    
    # Crear elemento raíz
    root = ET.Element(root_tag)
    dict_to_xml(root, data_dict)
    
    # Convertir a string con formato bonito
    tree = ET.ElementTree(root)
    xml_bytes = io.BytesIO()
    tree.write(xml_bytes, encoding='utf-8', xml_declaration=True)
    
    return xml_bytes.getvalue().decode('utf-8')