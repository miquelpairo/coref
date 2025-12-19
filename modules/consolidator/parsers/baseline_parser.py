"""
Parser para extraer información del informe de Baseline Adjustment
"""
from bs4 import BeautifulSoup
import re
from typing import Dict, Any, List, Optional


class BaselineParser:
    def __init__(self, html_content: str):
        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.data = {}
        
    def parse(self) -> Dict[str, Any]:
        """Parse completo del HTML de baseline adjustment"""
        self.data = {
            'tipo_informe': 'Baseline Adjustment',
            'info_cliente': self._extract_client_info(),
            'diagnostico_wstd': self._extract_wstd_diagnostics(),
            'detalles_proceso': self._extract_process_details(),
            'estadisticas_correccion': self._extract_correction_stats(),
            'baseline_generado': self._extract_baseline_info(),
            'verificacion': self._extract_verification(),
            'graficos': self._extract_plotly_charts()
        }
        return self.data
    
    def _extract_client_info(self) -> Dict[str, str]:
        """Extrae información del cliente y equipo"""
        info = {}
        info_section = self.soup.find('div', id='info-cliente')
        if info_section:
            table = info_section.find('table')
            if table:
                for row in table.find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) == 2:
                        key = cells[0].get_text(strip=True).replace(':', '')
                        value = cells[1].get_text(strip=True)
                        info[key] = value
        return info
    
    def _extract_wstd_diagnostics(self) -> Dict[str, Any]:
        """Extrae diagnóstico del White Standard inicial"""
        diagnostics = {}
        wstd_section = self.soup.find('div', id='wstd-section')
        if wstd_section:
            # Buscar tabla de métricas
            table = wstd_section.find('table')
            if table:
                metrics = {}
                for row in table.find_all('tr')[1:]:  # Skip header
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        metric = cells[0].get_text(strip=True)
                        value = cells[1].get_text(strip=True)
                        metrics[metric] = value
                diagnostics['metricas'] = metrics
            
            # Buscar estado (OK/Warning/Fail)
            status_spans = wstd_section.find_all('span', class_=['status-good', 'status-warning', 'status-fail'])
            if status_spans:
                diagnostics['estado'] = status_spans[0].get_text(strip=True)
        
        return diagnostics
    
    def _extract_process_details(self) -> Dict[str, str]:
        """Extrae detalles del proceso de corrección"""
        details = {}
        process_section = self.soup.find('div', id='process-details')
        if process_section:
            table = process_section.find('table')
            if table:
                for row in table.find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) == 2:
                        key = cells[0].get_text(strip=True)
                        value = cells[1].get_text(strip=True)
                        details[key] = value
        return details
    
    def _extract_correction_stats(self) -> Dict[str, str]:
        """Extrae estadísticas de la corrección aplicada"""
        stats = {}
        stats_section = self.soup.find('div', id='correction-stats')
        if stats_section:
            table = stats_section.find('table')
            if table:
                for row in table.find_all('tr')[1:]:  # Skip header
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        metric = cells[0].get_text(strip=True)
                        value = cells[1].get_text(strip=True)
                        stats[metric] = value
        return stats
    
    def _extract_baseline_info(self) -> Dict[str, str]:
        """Extrae información del baseline generado"""
        info = {}
        baseline_section = self.soup.find('div', id='baseline-info')
        if baseline_section:
            table = baseline_section.find('table')
            if table:
                for row in table.find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) == 2:
                        key = cells[0].get_text(strip=True)
                        value = cells[1].get_text(strip=True)
                        info[key] = value
        return info
    
    def _extract_verification(self) -> Dict[str, Any]:
        """Extrae datos de verificación post-ajuste"""
        verification = {}
        verif_section = self.soup.find('div', id='verification-section')
        
        if not verif_section:
            return verification
        
        # ============================================
        # 1. EXTRAER MÉTRICAS DE LA TABLA
        # ============================================
        info_boxes = verif_section.find_next_siblings('div', class_='info-box')
        
        for box in info_boxes:
            h2 = box.find('h2')
            if h2 and 'Métricas de Verificación' in h2.get_text():
                table = box.find('table')
                if table:
                    metrics = {}
                    for row in table.find_all('tr')[1:]:  # Skip header
                        cells = row.find_all('td')
                        if len(cells) >= 2:
                            metric = cells[0].get_text(strip=True)
                            value = cells[1].get_text(strip=True)
                            metrics[metric] = value
                    verification['metricas'] = metrics
                break
        
        # ============================================
        # 2. DETERMINAR ESTADO BASADO EN MÉTRICAS
        # ============================================
        if verification.get('metricas'):
            try:
                # Extraer valores numéricos
                rms_str = verification['metricas'].get('RMS', '0')
                max_diff_str = verification['metricas'].get('Diferencia Máxima', '0')
                
                # Limpiar y convertir a float
                rms = float(rms_str.replace(',', '.'))
                max_diff = float(max_diff_str.replace(',', '.'))
                
                # ⭐ UMBRALES ACTUALIZADOS - MÁS EXIGENTES
                if rms < 0.005 and max_diff < 0.01:
                    verification['estado'] = 'EXCELENTE'
                elif rms < 0.01 and max_diff < 0.015:
                    verification['estado'] = 'BUENO'
                elif rms < 0.015 and max_diff < 0.03:
                    verification['estado'] = 'ACEPTABLE'
                else:
                    verification['estado'] = 'REQUIERE REVISIÓN'
                    
            except (ValueError, AttributeError):
                verification['estado'] = 'UNKNOWN'
        
        # ============================================
        # 3. EXTRAER CONCLUSIÓN DEL HTML
        # ============================================
        status_divs = verif_section.find_all('div', class_=re.compile(r'status-(good|warning|bad|fail)'))
        
        if not status_divs:
            next_divs = verif_section.find_next_siblings('div')
            for div in next_divs:
                if any(cls in div.get('class', []) for cls in ['status-good', 'status-warning', 'status-bad', 'status-fail']):
                    status_divs = [div]
                    break
        
        if status_divs:
            status_div = status_divs[0]
            
            # Extraer conclusión completa
            paragraphs = status_div.find_all('p')
            if paragraphs:
                conclusion_parts = []
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if text:
                        conclusion_parts.append(text)
                verification['conclusion'] = ' '.join(conclusion_parts)
            
            # Extraer recomendaciones
            ul = status_div.find('ul')
            if ul:
                recommendations = []
                for li in ul.find_all('li'):
                    recommendations.append(li.get_text(strip=True))
                if recommendations:
                    verification['recomendaciones'] = recommendations
        
        return verification        
        
    def _extract_plotly_charts(self) -> List[Dict[str, str]]:
        """Extrae scripts de gráficos Plotly embebidos"""
        charts = []
        
        # Buscar todos los divs que contienen gráficos Plotly
        plot_divs = self.soup.find_all('div', id=re.compile(r'.*-plot$|plotly-.*'))
        
        for plot_div in plot_divs:
            chart_id = plot_div.get('id', '')
            
            # Buscar el script asociado con Plotly.newPlot
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
        """Genera resumen ejecutivo del baseline adjustment"""
        if not self.data:
            self.parse()
        
        summary = {
            'sensor_id': self.data.get('info_cliente', {}).get('ID del Sensor', 'N/A'),
            'fecha': self.data.get('info_cliente', {}).get('Fecha', 'N/A'),
            'configuracion': self.data.get('detalles_proceso', {}).get('Configuración', 'N/A'),
            'correccion_maxima': self.data.get('estadisticas_correccion', {}).get('Corrección Máxima', 'N/A'),
            'rms': self.data.get('estadisticas_correccion', {}).get('RMS de la Corrección', 'N/A'),
            'estado_verificacion': self._determine_status()
        }
        
        return summary
    
    def _determine_status(self) -> str:
        """Determina el estado global del baseline adjustment"""
        verification = self.data.get('verificacion', {})
        
        # Buscar indicadores de éxito/fallo
        if verification:
            conclusion = verification.get('conclusion', '')
            if 'exitosa' in conclusion.lower() or 'correctamente' in conclusion.lower():
                return 'OK'
            elif 'warning' in conclusion.lower() or 'revisar' in conclusion.lower():
                return 'WARNING'
            else:
                return 'FAIL'
        
        return 'UNKNOWN'
