"""
Parser para extraer información del informe de Predicciones con Muestras Reales
"""
from bs4 import BeautifulSoup
import re
from typing import Dict, Any, List


class PredictionsParser:
    def __init__(self, html_content: str):
        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.data = {}
        
    def parse(self) -> Dict[str, Any]:
        """Parse completo del HTML de predicciones"""
        self.data = {
            'tipo_informe': 'Predicciones con Muestras Reales',
            'info_general': self._extract_general_info(),
            'productos': self._extract_products_data(),
            'graficos': self._extract_plotly_charts()
        }
        return self.data
    
    def _extract_general_info(self) -> Dict[str, str]:
        """Extrae información general del reporte"""
        info = {}
        
        # Buscar info-box con información general
        info_box = self.soup.find('div', class_='info-box')
        if info_box:
            info_items = info_box.find_all('div', class_='info-item')
            for item in info_items:
                label = item.find('span', class_='info-label')
                value = item.find('span', class_='info-value')
                if label and value:
                    # Limpiar emojis del label
                    label_text = re.sub(r'[🔬📅📦💡]', '', label.get_text(strip=True)).strip()
                    label_text = label_text.replace(':', '').strip()
                    info[label_text] = value.get_text(strip=True)
            
            # Extraer lista de lámparas
            lamparas_ul = info_box.find('ul')
            if lamparas_ul:
                lamparas = [li.get_text(strip=True) for li in lamparas_ul.find_all('li')]
                info['Lámparas'] = lamparas
        
        return info
    
    def _extract_products_data(self) -> List[Dict[str, Any]]:
        """Extrae datos de predicciones por producto"""
        productos = []
        
        # Buscar todas las secciones de producto
        sections = self.soup.find_all('div', class_='section')
        
        for section in sections:
            h3_tag = section.find('h3')
            if not h3_tag:
                continue
            
            producto_nombre = h3_tag.get_text(strip=True)
            
            # Buscar tabla de resultados
            table = section.find('table')
            if not table:
                continue
            
            # Extraer headers (parámetros)
            headers = []
            header_row = table.find('thead').find('tr')
            for th in header_row.find_all('th'):
                # Extraer texto del header y subheader si existe
                text = th.get_text(separator='|', strip=True)
                # Limpiar formato
                text = text.replace('(Media ± SD)', '').strip()
                headers.append(text)
            
            # Extraer datos por lámpara
            lamparas_data = []
            tbody = table.find('tbody')
            if tbody:
                for row in tbody.find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) > 0:
                        lampara_dict = {}
                        for i, cell in enumerate(cells):
                            if i < len(headers):
                                # Limpiar nombre de lámpara si es el primer cell
                                value = cell.get_text(strip=True)
                                lampara_dict[headers[i]] = value
                        lamparas_data.append(lampara_dict)
            
            productos.append({
                'nombre': producto_nombre,
                'parametros': headers[2:],  # Skip Lámpara y N
                'lamparas': lamparas_data
            })
        
        return productos
    
    def _extract_plotly_charts(self) -> List[Dict[str, str]]:
        """Extrae scripts de gráficos Plotly embebidos"""
        charts = []
        
        # Buscar scripts con Plotly
        scripts = self.soup.find_all('script')
        for script in scripts:
            if script.string and 'Plotly.newPlot' in script.string:
                # Intentar identificar el div asociado
                match = re.search(r"Plotly\.newPlot\('([^']+)'", script.string)
                if match:
                    div_id = match.group(1)
                    charts.append({
                        'id': div_id,
                        'script': script.string
                    })
        
        return charts
    
    def get_summary(self) -> Dict[str, Any]:
        """Genera resumen ejecutivo de las predicciones"""
        if not self.data:
            self.parse()
        
        info_general = self.data.get('info_general', {})
        productos = self.data.get('productos', [])
        
        # Calcular estadísticas de variabilidad entre lámparas
        variabilidad_info = self._analyze_lamp_variability()
        
        summary = {
            'sensor_id': info_general.get('Sensor NIR', 'N/A'),
            'fecha': info_general.get('Fecha del Reporte', 'N/A'),
            'productos_analizados': info_general.get('Productos Analizados', 'N/A'),
            'lamparas_comparadas': info_general.get('Lámparas Comparadas', 'N/A'),
            'lista_lamparas': info_general.get('Lámparas', []),
            'lista_productos': [p['nombre'] for p in productos],
            'variabilidad': variabilidad_info,
            'estado_global': self._determine_status()
        }
        
        return summary
    
    def _analyze_lamp_variability(self) -> Dict[str, Any]:
        """Analiza la variabilidad entre lámparas"""
        if not self.data:
            self.parse()
        
        productos = self.data.get('productos', [])
        
        # Para cada producto, calcular la variabilidad promedio
        variabilidad_por_producto = {}
        
        for producto in productos:
            nombre = producto['nombre']
            lamparas_data = producto['lamparas']
            
            if len(lamparas_data) < 2:
                continue
            
            # Extraer valores numéricos y calcular CV promedio
            # (esto es una aproximación, ya que los valores incluyen ±)
            variabilidad_por_producto[nombre] = {
                'num_lamparas': len(lamparas_data),
                'parametros_evaluados': len(producto['parametros'])
            }
        
        return {
            'productos_evaluados': len(variabilidad_por_producto),
            'detalles': variabilidad_por_producto
        }
    
    def _determine_status(self) -> str:
        """Determina el estado global de las predicciones"""
        # Por ahora, asumimos OK si hay datos
        # En el futuro se podrían añadir criterios de aceptación
        if not self.data:
            self.parse()
        
        productos = self.data.get('productos', [])
        if len(productos) > 0:
            return 'OK'
        else:
            return 'UNKNOWN'
    
    def get_comparative_table(self) -> List[Dict[str, Any]]:
        """Genera tabla comparativa resumida de todas las lámparas y productos"""
        if not self.data:
            self.parse()
        
        productos = self.data.get('productos', [])
        
        comparative_data = []
        for producto in productos:
            for lampara_data in producto['lamparas']:
                row = {
                    'Producto': producto['nombre'],
                    'Lámpara': lampara_data.get('Lámpara', 'N/A'),
                    'N': lampara_data.get('N', 'N/A')
                }
                # Añadir parámetros clave (primeros 3-4)
                for i, param in enumerate(producto['parametros'][:4]):
                    row[param] = lampara_data.get(param, 'N/A')
                
                comparative_data.append(row)
        
        return comparative_data
