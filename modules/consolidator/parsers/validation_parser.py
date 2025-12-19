"""
Parser para extraer información del informe de Validación con Standards Ópticos
"""
from bs4 import BeautifulSoup
import re
from typing import Dict, Any, List


class ValidationParser:
    def __init__(self, html_content: str):
        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.data = {}
        
    def parse(self) -> Dict[str, Any]:
        """Parse completo del HTML de validación óptica"""
        self.data = {
            'tipo_informe': 'Validación Óptica',
            'info_servicio': self._extract_service_info(),
            'resumen_ejecutivo': self._extract_executive_summary(),
            'criterios_validacion': self._extract_validation_criteria(),
            'estadisticas_globales': self._extract_global_stats(),
            'resultados_detallados': self._extract_detailed_results(),
            'graficos': self._extract_plotly_charts()
        }
        return self.data
    
    def _extract_service_info(self) -> Dict[str, str]:
        """Extrae información del servicio"""
        info = {}
        service_section = self.soup.find('div', id='info-servicio')
        if service_section:
            table = service_section.find('table')
            if table:
                for row in table.find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) == 2:
                        key = cells[0].get_text(strip=True).replace(':', '')
                        value = cells[1].get_text(strip=True)
                        info[key] = value
        return info
    
    def _extract_executive_summary(self) -> Dict[str, Any]:
        """Extrae resumen ejecutivo con métricas principales"""
        summary = {}
        exec_section = self.soup.find('div', id='resumen-ejecutivo')
        if exec_section:
            # Extraer métricas numéricas
            metric_cards = exec_section.find_all('div', class_='metric-card')
            metrics = {}
            for card in metric_cards:
                value_div = card.find('div', class_='metric-value')
                label_div = card.find('div', class_='metric-label')
                if value_div and label_div:
                    label = label_div.get_text(strip=True)
                    value = value_div.get_text(strip=True)
                    # Limpiar emojis del label
                    label_clean = re.sub(r'[✅⚠️❌]', '', label).strip()
                    metrics[label_clean] = value
            summary['metricas'] = metrics
            
            # Extraer conclusión
            h3_tags = exec_section.find_all('h3')
            for h3 in h3_tags:
                text = h3.get_text(strip=True)
                if 'VALIDACIÓN' in text:
                    summary['conclusion'] = text
                    # Buscar descripción
                    next_p = h3.find_next('p')
                    if next_p:
                        summary['descripcion'] = next_p.get_text(strip=True)
        
        return summary
    
    def _extract_validation_criteria(self) -> Dict[str, List[Dict[str, str]]]:
        """Extrae criterios de validación utilizados"""
        criteria = {'criterios': []}
        criteria_section = self.soup.find('div', id='criterios-validacion')
        if criteria_section:
            table = criteria_section.find('table')
            if table:
                rows = table.find_all('tr')[1:]  # Skip header
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 3:
                        criteria['criterios'].append({
                            'parametro': cells[0].get_text(strip=True),
                            'umbral': cells[1].get_text(strip=True),
                            'descripcion': cells[2].get_text(strip=True)
                        })
        
        return criteria
    
    def _extract_global_stats(self) -> Dict[str, Any]:
        """Extrae estadísticas globales del kit completo"""
        stats = {}
        stats_section = self.soup.find('div', id='estadisticas-globales')
        if stats_section:
            # Primera tabla: estadísticas agregadas
            tables = stats_section.find_all('table')
            if len(tables) >= 1:
                stats['metricas_agregadas'] = []
                for row in tables[0].find_all('tr')[1:]:
                    cells = row.find_all('td')
                    if len(cells) >= 5:
                        stats['metricas_agregadas'].append({
                            'metrica': cells[0].get_text(strip=True),
                            'minimo': cells[1].get_text(strip=True),
                            'maximo': cells[2].get_text(strip=True),
                            'media': cells[3].get_text(strip=True),
                            'desv_est': cells[4].get_text(strip=True)
                        })
            
            # Segunda tabla: métricas clave
            if len(tables) >= 2:
                stats['metricas_clave'] = []
                for row in tables[1].find_all('tr')[1:]:
                    cells = row.find_all('td')
                    if len(cells) >= 3:
                        stats['metricas_clave'].append({
                            'metrica': cells[0].get_text(strip=True),
                            'valor': cells[1].get_text(strip=True),
                            'evaluacion': cells[2].get_text(strip=True)
                        })
        
        return stats
    
    def _extract_detailed_results(self) -> List[Dict[str, Any]]:
        """Extrae resultados individuales por estándar"""
        results = []
        results_section = self.soup.find('div', id='resultados-detallados')
        if results_section:
            table = results_section.find('table')
            if table:
                rows = table.find_all('tr')[1:]  # Skip header
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 7:  # Al menos 7 columnas: Estado, ID, Note(Ref), Note(Actual), Correlación, Max Δ, RMS
                        # Estructura de columnas:
                        # 0: Estado (✅ OK, ⚠️ WARNING, ❌ FAIL)
                        # 1: ID (V01, V02, etc.)
                        # 2: Note (Ref) - Lámpara de referencia
                        # 3: Note (Actual) - Lámpara nueva
                        # 4: Correlación (0.999502)
                        # 5: Max Δ (AU) (0.002910)
                        # 6: RMS (0.001674)
                        # 7: Shift (px) - opcional
                        
                        estado_text = cells[0].get_text(strip=True)
                        # Determinar estado desde el texto
                        status = 'UNKNOWN'
                        if '✅' in estado_text or 'OK' in estado_text.upper():
                            status = 'OK'
                        elif '⚠️' in estado_text or 'WARNING' in estado_text.upper():
                            status = 'WARNING'
                        elif '❌' in estado_text or 'FAIL' in estado_text.upper():
                            status = 'FAIL'
                        
                        results.append({
                            'estandar': cells[1].get_text(strip=True),  # ID
                            'lampara_ref': cells[2].get_text(strip=True),  # Note (Ref)
                            'lampara_nueva': cells[3].get_text(strip=True),  # Note (Actual)
                            'correlacion': cells[4].get_text(strip=True),  # Correlación
                            'max_diff': cells[5].get_text(strip=True),  # Max Δ (AU)
                            'rms': cells[6].get_text(strip=True),  # RMS
                            'shift': cells[7].get_text(strip=True) if len(cells) > 7 else 'N/A',  # Shift (px)
                            'estado': status
                        })
        
        return results
    
    def _extract_plotly_charts(self) -> List[Dict[str, str]]:
        """Extrae scripts de gráficos Plotly embebidos"""
        charts = []
        
        # Buscar divs de Plotly
        plot_divs = self.soup.find_all('div', id=re.compile(r'.*-plot$|plotly-.*'))
        
        for plot_div in plot_divs:
            chart_id = plot_div.get('id', '')
            
            # Buscar script asociado
            script_tag = plot_div.find_next_sibling('script')
            if script_tag:
                script_content = script_tag.string
                if script_content and 'Plotly.newPlot' in script_content:
                    charts.append({
                        'id': chart_id,
                        'script': script_content
                    })
        
        return charts
    
    def get_summary(self) -> Dict[str, Any]:
        """Genera resumen ejecutivo de la validación óptica"""
        if not self.data:
            self.parse()
        
        service_info = self.data.get('info_servicio', {})
        exec_summary = self.data.get('resumen_ejecutivo', {})
        stats = self.data.get('estadisticas_globales', {})
        
        # Extraer offset global del kit
        offset_global = 'N/A'
        metricas_clave = stats.get('metricas_clave', [])
        for metrica in metricas_clave:
            if 'Offset Global' in metrica.get('metrica', ''):
                offset_global = metrica.get('valor', 'N/A')
                break
        
        # Determinar correlación media
        correlacion_media = 'N/A'
        for metrica in metricas_clave:
            if 'Correlación Media' in metrica.get('metrica', ''):
                correlacion_media = metrica.get('valor', 'N/A')
                break
        
        summary = {
            'sensor_id': service_info.get('ID del Sensor', 'N/A'),
            'fecha': service_info.get('Fecha del Informe', 'N/A'),
            'total_estandares': exec_summary.get('metricas', {}).get('Total Estándares', 'N/A'),
            'validados': exec_summary.get('metricas', {}).get('Validados', 'N/A'),
            'revisar': exec_summary.get('metricas', {}).get('Revisar', 'N/A'),
            'fallidos': exec_summary.get('metricas', {}).get('Fallidos', 'N/A'),
            'offset_global': offset_global,
            'correlacion_media': correlacion_media,
            'conclusion': exec_summary.get('conclusion', 'N/A'),
            'estado_global': self._determine_status()
        }
        
        return summary
    
    def _determine_status(self) -> str:
        """Determina el estado global de la validación"""
        if not self.data:
            self.parse()
        
        exec_summary = self.data.get('resumen_ejecutivo', {})
        metricas = exec_summary.get('metricas', {})
        
        # Convertir a números
        try:
            fallidos = int(metricas.get('Fallidos', '0'))
            revisar = int(metricas.get('Revisar', '0'))
            
            if fallidos > 0:
                return 'FAIL'
            elif revisar > 0:
                return 'WARNING'
            else:
                return 'OK'
        except:
            return 'UNKNOWN'
    
    def extract_all_charts(self) -> List[str]:
        """Extrae TODOS los gráficos Plotly del HTML original"""
        charts = []
        
        # Buscar todos los divs que contienen gráficos Plotly
        plotly_divs = self.soup.find_all('div', class_='plotly-graph-div')
        
        for div in plotly_divs:
            chart_id = div.get('id', '')
            if not chart_id:
                continue
            
            # Construir el HTML completo del gráfico
            chart_html = []
            
            # Buscar el script CDN de Plotly (solo una vez)
            parent = div.parent
            while parent:
                cdn_script = parent.find('script', src=lambda x: x and 'plotly' in str(x).lower())
                if cdn_script:
                    chart_html.append(str(cdn_script))
                    break
                parent = parent.parent if hasattr(parent, 'parent') else None
            
            # Agregar el div del gráfico
            chart_html.append(str(div))
            
            # Buscar el script que inicializa ESTE gráfico específico
            all_scripts = self.soup.find_all('script', type='text/javascript')
            for script in all_scripts:
                if script.string and 'Plotly.newPlot' in script.string and chart_id in script.string:
                    chart_html.append(str(script))
                    break
            
            if len(chart_html) >= 2:  # Al menos div + script
                charts.append('\n'.join(chart_html))
        
        return charts