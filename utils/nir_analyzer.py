"""
NIR Analyzer - Clase para analizar datos NIR desde archivos XML
"""

import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET
import streamlit as st


class NIRAnalyzer:
    """Clase para analizar datos NIR desde archivos XML"""
    
    def __init__(self):
        self.data = {}
        self.products = []
        self.sensor_serial = None
        
    def parse_xml(self, uploaded_file):
        """Parse XML file from NIR-Online software"""
        try:
            # Leer el contenido del archivo
            content = uploaded_file.read()
            
            # Parse XML
            root = ET.fromstring(content)
            
            # Namespace del XML
            ns = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet'}
            
            # Variable para almacenar el número de serie del sensor
            sensor_serial = None
            
            # Encontrar todas las worksheets (productos)
            worksheets = root.findall('.//ss:Worksheet', ns)
            
            for worksheet in worksheets:
                product_name = worksheet.get('{urn:schemas-microsoft-com:office:spreadsheet}Name')
                
                # Saltar hojas que no son productos
                if product_name in ['Espectros', 'Summary'] or product_name is None:
                    continue
                
                # Extraer datos de la tabla
                table = worksheet.find('.//ss:Table', ns)
                if table is None:
                    continue
                
                rows = table.findall('.//ss:Row', ns)
                
                # Encontrar la fila de encabezado
                headers = []
                data_rows = []
                start_data = False
                
                for row in rows:
                    cells = row.findall('.//ss:Cell', ns)
                    row_data = []
                    
                    for cell in cells:
                        data_elem = cell.find('.//ss:Data', ns)
                        if data_elem is not None:
                            row_data.append(data_elem.text)
                        else:
                            row_data.append(None)
                    
                    # Detectar fila de encabezado
                    if (not start_data and row_data and 
                        'ID' in row_data and 'Note' in row_data and 
                        ('Product' in row_data or 'Method' in row_data)):
                        headers = row_data
                        # Normalizar el nombre de la primera columna a "No"
                        if headers[0] in ['#', 'No']:
                            headers[0] = 'No'
                        start_data = True
                        continue
                    
                    # Recoger filas de datos
                    if start_data and row_data:
                        # Verificar si es una fila de datos
                        if row_data[0] and str(row_data[0]).replace('.', '').isdigit():
                            data_rows.append(row_data)
                            
                            # Extraer número de serie del sensor
                            if sensor_serial is None and 'Unit' in headers:
                                unit_idx = headers.index('Unit')
                                if unit_idx < len(row_data) and row_data[unit_idx]:
                                    sensor_serial = row_data[unit_idx]
                        # Verificar si llegamos a las filas de estadísticas
                        elif len(row_data) > 1 and row_data[1] in ['Average', 'Min', 'Max', 'Std.Dev.', 'Target']:
                            break
                
                # Crear DataFrame
                if headers and data_rows:
                    # Asegurar que todas las filas tengan la misma longitud
                    max_len = len(headers)
                    data_rows = [row + [None] * (max_len - len(row)) if len(row) < max_len else row[:max_len] 
                                for row in data_rows]
                    
                    df = pd.DataFrame(data_rows, columns=headers)
                    
                    # Convertir columnas numéricas
                    for col in df.columns:
                        if col not in ['No', 'ID', 'Note', 'Product', 'Method', 'Unit']:
                            try:
                                df[col] = pd.to_numeric(df[col], errors='coerce')
                            except:
                                pass
                    
                    self.data[product_name] = df
                    self.products.append(product_name)
            
            # Guardar el número de serie del sensor
            self.sensor_serial = sensor_serial
            
            return True
            
        except Exception as e:
            st.error(f"Error al parsear el archivo XML: {str(e)}")
            return False
    
    def get_id_note_combinations(self, products):
        """Obtener combinaciones únicas de ID y Note para productos seleccionados"""
        combinations = set()
        
        for product in products:
            if product in self.data:
                df = self.data[product]
                for _, row in df.iterrows():
                    id_val = row.get('ID', '')
                    note_val = row.get('Note', '')
                    if pd.notna(id_val) and pd.notna(note_val):
                        combinations.add((id_val, note_val))
        
        return sorted(list(combinations))
    
    def filter_data(self, products, id_note_combinations):
        """Filtrar datos por productos y combinaciones ID-Note"""
        filtered_data = {}
        
        for product in products:
            if product not in self.data:
                continue
                
            df = self.data[product].copy()
            
            # Filtrar por combinaciones ID-Note
            mask = pd.Series([False] * len(df))
            for id_val, note_val in id_note_combinations:
                mask |= ((df['ID'] == id_val) & (df['Note'] == note_val))
            
            filtered_df = df[mask]
            
            if not filtered_df.empty:
                filtered_data[product] = filtered_df
        
        return filtered_data
    
    def calculate_statistics(self, filtered_data):
        """Calcular estadísticas por producto y lámpara (Note)"""
        stats = {}
        
        for product, df in filtered_data.items():
            product_stats = {}
            
            # Agrupar por Note (lámpara)
            for note in df['Note'].unique():
                note_df = df[df['Note'] == note]
                
                note_stats = {
                    'n': len(note_df),
                    'note': note
                }
                
                # Calcular media y std para cada parámetro numérico
                numeric_cols = note_df.select_dtypes(include=[np.number]).columns
                
                for col in numeric_cols:
                    if col != 'No':
                        values = note_df[col].dropna()
                        if len(values) > 0:
                            note_stats[col] = {
                                'mean': values.mean(),
                                'std': values.std(),
                                'min': values.min(),
                                'max': values.max(),
                                'values': values.tolist()
                            }
                
                product_stats[note] = note_stats
            
            stats[product] = product_stats
        
        return stats


def get_params_in_original_order(analyzer, products):
    """Obtener parámetros en el orden original del archivo XML"""
    params_order = []
    
    # Usar el primer producto para obtener el orden de columnas
    for product in products:
        if product in analyzer.data:
            df = analyzer.data[product]
            # Excluir columnas no numéricas y metadatos
            excluded_cols = ['No', 'ID', 'Note', 'Product', 'Method', 'Unit', 'Begin', 'End', 'Length']
            # También excluir las columnas que son nombres de productos
            if len(df.columns) > 1:
                excluded_cols.append(df.columns[1])
            
            params = [col for col in df.columns if col not in excluded_cols]
            params_order.extend([p for p in params if p not in params_order])
    
    return params_order