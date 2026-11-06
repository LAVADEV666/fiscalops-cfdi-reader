"""Inventory every original button and reconcile observed presence with actual tests."""
from html.parser import HTMLParser
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'tests/visual/evidence'


class Buttons(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack, self.buttons, self.current = [], [], None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag not in ('img', 'input', 'meta', 'link', 'br', 'hr'):
            self.stack.append((tag, attrs.get('id', '')))
        if tag == 'button':
            contexts = [identity for _tag, identity in self.stack if identity in ('s1', 's2', 's3', 'modal', 'previewModal', 'exportModal')]
            key = attrs.get('id')
            if not key:
                for field, prefix in [('data-type', 'type'), ('data-origin', 'origin'), ('data-status', 'status'), ('data-metodo', 'method')]:
                    if field in attrs:
                        key = f'{prefix}:{attrs[field]}'
                        break
            self.current = {'key': key or f'button-line-{self.getpos()[0]}-{len(self.buttons)}',
                            'id': attrs.get('id'), 'screen': contexts[-1] if contexts else 'global',
                            'line': self.getpos()[0], 'attrs': attrs, 'label': ''}
            self.buttons.append(self.current)

    def handle_data(self, data):
        if self.current:
            self.current['label'] += data

    def handle_endtag(self, tag):
        if tag == 'button':
            self.current = None
        for index in range(len(self.stack)-1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break


EXPECTED = {
    'start': 'Entrar a carga', 'select': 'Abrir selector y cargar archivos sintéticos',
    'folder': 'Reconectar carpeta autorizada', 'changeFolder': 'Elegir carpeta local',
    'refreshFolder': 'Volver a escanear carpeta conectada', 'process': 'Procesar archivos y mostrar reporte/incidentes',
    'reprocessAll': 'Siguiente según nextScreen; no es reproceso forzado', 'forgetMemory': 'Olvidar memoria por doble clic',
    'clear': 'Limpiar selección, datos y estado de sesión', 'excel': 'Abrir constructor XLSX',
    'excelf': 'Ruta rápida heredada oculta', 'txt': 'Descargar TXT del reporte actual', 'csv': 'Descargar CSV del reporte actual',
    'exportPack': 'Ruta técnica heredada oculta', 'editcols': 'Abrir editor de columnas', 'editcolsTop': 'Abrir el mismo editor desde totales',
    'more': 'Volver a carga', 'densityBtn': 'Alternar densidad de tabla', 'csvQuick': 'Control auxiliar oculto',
    'prev': 'Página anterior', 'next': 'Página siguiente', 'cancel': 'Exportación heredada oculta de cancelados',
    'sinmeta': 'Exportación heredada oculta sin metadata', 'closecols': 'Cerrar editor y restaurar foco',
    'corecols': 'Seleccionar perfil recomendado', 'invoicecols': 'Seleccionar perfil fiscal', 'allcols': 'Seleccionar todas',
    'nocols': 'Deseleccionar todas', 'paycols': 'Atajo heredado oculto a pagos', 'nomcols': 'Atajo heredado oculto a nómina',
    'auditcols': 'Seleccionar perfil auditoría', 'taxcols': 'Seleccionar perfil impuestos', 'applycols': 'Aplicar selección completa sin perder columnas por búsqueda',
    'previewClose': 'Cerrar visor', 'exportClose': 'Cerrar constructor', 'exportCancel': 'Cancelar diálogo sin generar libro',
    'exportGenerate': 'Generar y descargar XLSX real',
}


def main():
    parser = Buttons()
    parser.feed((ROOT / 'FiscalOps_CFDI_READER_SSGT_V21_1_PRO.html').read_text(encoding='utf-8-sig'))
    nav = json.loads((EVIDENCE / 'navigation.json').read_text(encoding='utf-8'))
    controls = json.loads((EVIDENCE / 'controls.json').read_text(encoding='utf-8'))
    checks = controls['checks'][:]
    mappings = {'start': 'start-', 'process': 'table-has-rows-', 'clear': 'clear-disables-process-',
                'type:I': 'report-filter-single-click-', 'applycols': 'column-search-preserves-selection-',
                'exportGenerate': 'xlsx-download-'}
    for control, prefix in mappings.items():
        for item in nav['checks']:
            if item['id'].startswith(prefix):
                checks.append({**item, 'controls': [control]})
    for tab in ['impuestos', 'conceptos', 'datos', 'xml']:
        for item in nav['checks']:
            if item['id'].startswith(f'viewer-tab-{tab}-'):
                checks.append({**item, 'controls': [f'preview:{tab}']})
    for tab in ['resumen', 'impuestos', 'conceptos', 'datos', 'xml']:
        parser.buttons.append({'key': f'preview:{tab}', 'id': None, 'screen': 'previewModal', 'line': 1136,
                               'label': tab, 'attrs': {'data-pv': tab}, 'dynamic': True})
    observed = {}
    for state in nav['buttonStates']:
        for button in state['controls']:
            key = button['id']
            if not key:
                for field, prefix in [('dataType', 'type'), ('dataOrigin', 'origin'), ('dataStatus', 'status'), ('dataMethod', 'method'), ('dataPreview', 'preview')]:
                    if button[field] is not None:
                        key = f'{prefix}:{button[field]}'
                        break
            observed.setdefault(key, []).append({'scene': state['scene'], 'size': state['size'], 'visible': button['visible'], 'disabled': button['disabled']})
    lines = ['# Matriz de compatibilidad UI — V21.1', '',
             'Referencia original sin cambios. Presencia visual y comportamiento probado son categorías distintas. Resultados derivados de `navigation.json`, `controls.json` y las capturas reales; los importes del motor antiguo no son referencias fiscales.', '',
             'La tabla inventaría todos los botones del markup original y las cinco pestañas generadas del visor final. Las cinco pestañas de tipo se reconcilian por data-type aunque se regeneren en ejecución. Controles ocultos se conservan e identifican; no se forzó su interacción para presentarlos como probados.', '',
             '| Pantalla | Elemento | Comportamiento esperado | Prueba ejecutada | Resultado | Evidencia | Diferencia encontrada | Acción requerida |',
             '|---|---|---|---|---|---|---|---|']
    for button in parser.buttons:
        key = button['key']
        tests = [check for check in checks if key in check.get('controls', [])]
        failed = [test for test in tests if test['result'] != 'PASS']
        presence = observed.get(key, [])
        visible = any(item['visible'] for item in presence)
        button.update(observations=presence, checks=tests, visible_observed=visible)
        button['result'] = 'FAIL' if failed else 'PASS limitado a las pruebas citadas' if tests else 'PRESENTE / NO PROBADO' if visible else 'OCULTO o NO OBSERVADO / NO PROBADO'
        expected = EXPECTED.get(key, 'Activar filtro o pestaña y reflejar estado seleccionado')
        difference = '; '.join(f"{test['id']}: esperado={test.get('expected')}, observado={test.get('actual', test.get('error'))}" for test in failed) or 'Ninguna en pruebas ejecutadas' if tests else 'Sin prueba funcional; no inferir funcionamiento por presencia'
        action = 'Corregir tras congelar referencia; conservar diseño' if failed else 'Completar prueba manual si depende de carpeta, memoria o control oculto' if not tests else 'Conservar y repetir contra contenedor Qt'
        evidence = 'tests/visual/evidence/controls.json; navigation.json' if tests else 'navigation.json/buttonStates; HTML L'+str(button['line'])
        label = (key + ' · ' + button['label'].strip()).replace('|', '/')
        lines.append(f"| {button['screen']} | {label} | {expected} | {', '.join(test['id'] for test in tests) or 'No ejecutada'} | {button['result']} | {evidence} | {difference} | {action} |")
    lines += ['', '## Otros contratos y pendientes', '',
              '| Pantalla | Elemento | Comportamiento esperado | Prueba ejecutada | Resultado | Evidencia | Diferencia encontrada | Acción requerida |',
              '|---|---|---|---|---|---|---|---|',
              '| Reportes | Cabeceras, año/mes, paginación, perfiles, CSV/TXT | Orden/filtro/selección compartidos | controls.json | Ver resultados por caso; no certificación fiscal | controls-trace.zip | Ver datos esperados/observados | Repetir en Qt |',
              '| Editor | Shift+Tab/foco | Mantener foco modal y restaurarlo al cierre | modal-keyboard-containment, columns-focus-restored | Ver controls.json | Traza y valores activeElement | Defectos preexistentes si FAIL | Corregir en fase de integración, sin rediseño |',
              '| Carga | Carpeta y memoria real | Conectar raíz sintética y reutilizar caché | No automatizada | PENDIENTE | README de captura manual | Picker nativo no automatizado; sin mocks | Ejecutar procedimiento Windows |',
              '| Carga | Progreso | Estado observado mientras aún procesa | Captura antes/después | TRANSITORIO / NO APROBADO | navigation.json y evidence/transient | Proceso terminó durante screenshot | Captura manual/vídeo real, sin fabricar estado |',
              '| Desktop | Mismos controles en QtWebEngine | Navegar sin cambio de diseño | --check | BLOQUEADO | desktop-check.json | PySide6 ausente | Instalar/verificar dependencias Qt en entorno acordado |',
              '', f"Total: {len(parser.buttons)-5} botones en markup original + 5 pestañas dinámicas finales = {len(parser.buttons)} entradas. El recuento no considera templates de editores sustituidos como botones activos.", '']
    (ROOT / 'docs/08_MATRIZ_COMPATIBILIDAD_UI.md').write_text('\n'.join(lines), encoding='utf-8')
    (EVIDENCE / 'buttons.json').write_text(json.dumps({'original_buttons': len(parser.buttons)-5, 'dynamic_viewer_tabs': 5, 'buttons': parser.buttons}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'original_buttons': len(parser.buttons)-5, 'dynamic_viewer_tabs': 5, 'total': len(parser.buttons)}))


if __name__ == '__main__':
    main()
