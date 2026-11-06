"""Render SPEC011 traceability from historical and current test results."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[2]


def read(name):
    return json.loads((ROOT/name).read_text(encoding='utf-8-sig'))


def main():
    nav=read('tests/spec011/browser/evidence/navigation.json')
    controls=read('tests/spec011/controls/controls.json')
    targeted=read('tests/spec011/targeted/results.json')
    qt=read('tests/spec011/qt/smoke.json')
    text=['# SPEC 011 — Matriz de regresión UI', '',
          'Resultados reales. PASS de navegación no certifica cálculos fiscales. Original/legacy/baseline preservados. Los cinco FAIL previos se reproducen por separado; los intentos de implementación fallidos no se confunden con resultados finales.', '',
          '## Casos históricos conservados', '',
          'Las48 expectativas de navegación y las30 de controles se mantienen. El único ajuste de secuencia restablece el tipo después de comprobar su clic corregido, para conservar el ámbito sin filtro de los siguientes casos.', '']
    for title,old_name,current in [('Navegación','tests/visual/evidence/navigation.json',nav),('Controles','tests/visual/evidence/controls.json',controls)]:
        old=read(old_name)
        previous={c['id']:c for c in old['checks']}
        assert set(previous)=={c['id'] for c in current['checks']}
        assert all(c['expected']==previous[c['id']]['expected'] for c in current['checks'])
        text += [f'### {title}', '', '| Caso | Antes | Después | Expectativa conservada |', '|---|---|---|---|']
        for case in current['checks']:
            text.append(f"| {case['id']} | {previous[case['id']]['result']} | {case['result']} | Sí |")
        text += ['']
    text += ['## Reproducciones antes/después', '', '| Defecto | Original | Desarrollo |', '|---|---|---|']
    after={c['id']:c for c in targeted['after']}
    for case in targeted['before']:
        if case['id'].startswith(('P0-','P1-')):
            text.append(f"| {case['id']} | {case['result']}: {str(case.get('actual')).replace('|','/')} | {after[case['id']]['result']} |")
    text += ['', '## Regresión ampliada', '', '| Caso | Resultado | Evidencia |', '|---|---|---|']
    for case in targeted['after']:
        text.append(f"| {case['id']} | {case['result']} | tests/spec011/targeted/results.json |")
    text += ['', '## Escritorio Windows real', '', '| Caso | Resultado | Evidencia |', '|---|---|---|']
    for case in qt['checks']:
        text.append(f"| {case['id']} | {case['result']} | tests/spec011/qt/smoke.json |")
    visuals=read('tests/spec011/visual/comparison.json')
    qt_visuals=read('tests/spec011/qt-visual/comparison.json')
    text += ['', '## Comparaciones visuales medidas', '', '| Grupo | Comparaciones | Máximo de píxeles distintos | Observación |', '|---|---:|---:|---|',
             f"| Original/desarrollo, mismo Chromium151 | {len(visuals['pairs'])} | {max(c['changedPercent'] for c in visuals['pairs']):.6f}% | Mismas escenas, datos, viewport, fases de animación; no CSS de producto modificado |",
             f"| Baseline histórica/captura posterior | {len(visuals['baselineComparisons'])} | {max(c['changedPercent'] for c in visuals['baselineComparisons'] if not c['intentionalStateChange']):.6f}% sin estados intencionales | Escenas05/14 etiquetadas; baseline no sobrescrita |",
             f"| Original/desarrollo, mismo Qt | {len(qt_visuals['pairs'])} | {max(c['changedPercent'] for c in qt_visuals['pairs']):.6f}% | Editor/visor/Excel0%; ruido restante en animaciones/raster |",
             f"| Baseline Chromium151 / QtWebEngine140 | {len(qt_visuals['crossRenderer'])} | {max(c['changedPercent'] for c in qt_visuals['crossRenderer']):.6f}% | Diferencia real de renderizador y scrollbar; no llamarla fidelidad100% |",
             '', 'Se usó pixelmatch threshold0.1 y exclusión de antialias; los porcentajes cuentan píxeles, no una certificación perceptual global. Diffs y capturas originales/candidatas permanecen disponibles.', '',
             '## Capacidades pendientes, sin aprobación implícita', '',
             '| Capacidad | Resultado | Motivo / acción |', '|---|---|---|',
             '| Carpeta/permisos/reconexión nativos | PENDIENTE | Contrato propuesto en12; no sustituir flujo sin implementarlo y probarlo |',
             '| Progreso estable | NO APROBADO | Lote2000 completó; screenshot cruzó a reporte final. Ver progress_capture |',
             '| DPI125/150% | NO PROBADO | Entorno nativo actual96/DPR1 observado; no modificar seguridad/pantalla para fingir cobertura |',
             '| Persistencia portable tras cerrar Qt | PENDIENTE | Perfil Qt de smoke off-the-record; preferencias probadas en recarga, no almacenamiento portable de producción |',
             '| Fiscal / SAT / EXE portable | FUERA DE SPEC011 | RiesgosP0 continúan en02 y14; sin nuevo motor ni empaquetado |', '',
             f"Resumen posterior: {len(nav['checks'])}/{len(nav['checks'])} navegación, {len(controls['checks'])}/{len(controls['checks'])} controles, {len(targeted['after'])}/{len(targeted['after'])} específicos y {len(qt['checks'])}/{len(qt['checks'])} Qt si todos los registros muestranPASS. Los JSON son la autoridad si se repite una ejecución.", '']
    (ROOT/'docs/13_UI_REGRESSION_MATRIX.md').write_text('\n'.join(text),encoding='utf-8')
    print(json.dumps({'navigation':len(nav['checks']),'controls':len(controls['checks']),'targeted':len(targeted['after']),'qt':len(qt['checks'])}))


if __name__=='__main__':main()
