"""Bind native history/backup acceptance to current sources and protected artifacts."""
import ast
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.integration.evidence import source_hashes
from app.fiscal.sources import SatSources


def read(name):
    return json.loads((ROOT/name).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    current = source_hashes()
    for name, count in (('tests/history/evidence/contracts.json', 20), ('tests/persistence/evidence/contracts.json', 20),
                        ('tests/integration/evidence/contracts.json', 28)):
        report = read(name)
        assert report['source_sha256'] == current and report['success'] and report['tests'] == count
        assert report['failures'] == report['errors'] == 0 and all(c['status'] == 'pass' for c in report['cases'])
    fiscal = read('tests/history/evidence/fiscal-tests.json')
    assert fiscal['success'] and fiscal['tests_run'] == 59 and fiscal['failures'] == fiscal['errors'] == 0
    for name, digest in fiscal['source_sha256'].items():
        assert sha(ROOT/name) == digest
    for name, count in (('tests/integration/qt/smoke.json', 34), ('tests/integration/jobs/jobs.json', 17)):
        report = read(name)
        assert report['source_sha256'] == current and not report.get('fatal') and report['closed'] and report['worker_stopped']
        assert len(report['checks']) == count and all(c['result'] == 'PASS' for c in report['checks'])
    qt = read('tests/history/qt/acceptance.json')
    assert qt['success'] and qt['source_sha256'] == current and qt['checks'] == 37 and qt['processes'] == 2
    for phase in qt['phases']:
        assert phase['source_sha256'] == current and not phase.get('fatal') and phase['closed'] and phase['sqlite_closed']
        assert all(c['result'] == 'PASS' for c in phase['checks'])
        assert not any('Uncaught' in item['message'] for item in phase['console'])
    assert qt['restored_summary']['sessions'] == qt['preventive_summary']['sessions'] == 2
    assert qt['restored_summary']['documents'] == qt['preventive_summary']['documents'] == 4
    assert qt['restored_summary']['active_session'] != qt['preventive_summary']['active_session']
    with (ROOT/'tests/history/qt/FiscalOps_summary.csv').open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 1 and rows[0]['Total'] == '119' and rows[0]['IVA trasladado'] == '16'
    assert len((ROOT/'tests/history/qt/FiscalOps_summary.txt').read_text(encoding='utf-8-sig').splitlines()) == 2
    with zipfile.ZipFile(ROOT/'tests/history/qt/FiscalOps_summary.xlsx') as archive:
        assert archive.testzip() is None and len([n for n in archive.namelist() if n.startswith('xl/worksheets/')]) == 8
        for name in archive.namelist():
            if name.endswith(('.xml', '.rels')):
                ET.fromstring(archive.read(name))
        assert b'<v>119</v>' in archive.read('xl/worksheets/sheet1.xml')
    no_native = read('tests/integration/evidence/no-native.json')
    assert no_native['success'] and no_native['development_runtime_sha256'] == current['app/ui/legacy-runtime.js']
    comparison = read('tests/history/visual/comparison.json')
    assert comparison['source_sha256'] == current and len(comparison['pairs']) == 3
    assert all(p['comparable'] and p['changedPercent'] < 1 for p in comparison['pairs'])
    maximum = max(p['changedPercent'] for p in comparison['pairs'])
    original = ROOT/'FiscalOps_CFDI_READER_SSGT_V21_1_PRO.html'
    assert sha(original) == '33eeed2334a683b5360c2fc4f9cabc26885be66fef8714e4278f97235b8c373b'
    assert original.read_bytes() == (ROOT/'legacy'/original.name).read_bytes()
    for name in ('app/ui/index.html', 'app/ui/v20-runtime.js', 'app/ui/column-editor.js', 'tests/visual/baseline/manifest.json'):
        frozen = subprocess.run(['git', 'show', 'ec95bbbb05c4eed81856b034c01e02b8ac5e7b4e:'+name], cwd=ROOT, capture_output=True, check=True).stdout
        assert (ROOT/name).read_bytes() == frozen
    baseline = read('tests/visual/baseline/manifest.json')
    assert len(baseline['captures']) == 60
    for capture in baseline['captures']:
        assert sha(ROOT/capture['path']) == capture['sha256']
    sources = SatSources()
    for identity in sources.records:
        sources.resource(identity)
    build = read('tests/integration/evidence/ui-build.json')
    for name, digest in build['files'].items():
        assert sha(ROOT/'app/ui'/name) == digest
    for folder in ('app/desktop', 'scripts/history', 'tests/history'):
        for path in (ROOT/folder).glob('*.py'):
            ast.parse(path.read_text(encoding='utf-8-sig'))
    assert subprocess.run([sys.executable, '-m', 'pip', 'check'], capture_output=True).returncode == 0
    for name in ('FiscalOpsData/fiscalops.sqlite3', 'FiscalOps_respaldo.sqlite3', 'FiscalOps_respaldo.db'):
        assert subprocess.run(['git', 'check-ignore', name], cwd=ROOT, capture_output=True).returncode == 0
    assert (ROOT/'docs/21_HISTORIAL_RESPALDOS_SQLITE.md').stat().st_size > 1000
    result = {'status': 'pass', 'source_sha256': current, 'history_contracts': 20, 'sqlite_contracts': 20,
              'integration_contracts': 28, 'fiscal_tests': 59, 'qt_history': 37, 'qt_smoke': 34, 'qt_jobs': 17,
              'crash_restore_rollback': True, 'review_before_restore': True, 'verified_preventive_backup': True,
              'native_paths_not_exposed_to_webchannel': True, 'restored_export_csv_total': '119', 'xlsx_sheets': 8,
              'baseline_preserved': 60, 'official_sources_preserved': len(sources.records),
              'visual_pairs': 3, 'maximum_visual_percent': maximum,
              'remaining': ['repair/overwrite of corrupt active database', 'encryption and scheduled backups',
                            'shared/multi-device synchronized writes', 'folder grants and incremental cache',
                            'full complementary SAT validation', 'clean Windows/DPI125/150 and EXE']}
    (ROOT/'tests/history/evidence/verification.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    report = f'''# Historial visual y respaldos SQLite — entrega

Implementados en Qt mediante **Sesiones y respaldos**, en la cabecera. El historial muestra fecha UTC, RFC, CFDI, estado e ID; permite buscar, paginar y abrir una sesión compatible con su vista guardada. Los reportes conservan el viewport y los22 tipos existentes. El respaldo y la restauración trabajan en el worker; ninguna ruta de esos flujos se entrega al WebChannel.

Crear respaldo usa la API de SQLite, valida una copia temporal y publica el archivo final. Restaurar abre el archivo de sólo lectura, verifica esquema/hashes/conteos y muestra un resumen que aún no modifica datos. Tras confirmar crea un respaldo preventivo, sustituye todo el contenido mediante una transacción y muestra la copia preventiva antes de volver al reporte. Cancelar, fallar o morir antes del COMMIT conserva la base anterior.

| Evidencia actual | Resultado |
|---|---|
| Contratos nuevos de historial/respaldo/restauración |20/20 PASS |
| Persistencia SQLite |20/20 PASS |
| Integración/reportes |28/28 PASS |
| Motor fiscal |59/59 PASS |
| Historial y restauración en dos procesos Qt reales |37/37 PASS |
| Ventana, visor y exportaciones Qt |34/34 PASS |
| Jobs Qt y cancelación/cierre |17/17 PASS |
| HTML sin Qt |Procesamiento/exportación bloqueados |
| Comparación nativa a tres tamaños |Máximo {maximum:.6f}% de píxeles distintos |
| Original, legacy, HTML/CSS/editor y baseline60 |Preservados |
| Fuentes oficiales fijadas |{len(sources.records)} hashes verificados |

La prueba Qt crea dos sesiones sintéticas, busca y abre la primera, guarda un respaldo nativo, cancela un selector de archivo, rechaza un archivo inválido, revisa/descarta un candidato y confirma después una restauración. La copia preventiva conserva la segunda sesión activa; la base restaurada vuelve a la primera con su filtro HISTORY-1 y perfil fiscal. La pantalla de éxito muestra el path preventivo. Un segundo proceso Qt confirma persistencia tras reiniciar.

Después de restaurar se guardan CSV/TXT/XLSX reales de una fila: IVA16 y Total119. El XLSX mantiene ocho hojas y todas sus partes XML/CRC se verifican; las descargas llegan a DownloadCompleted. No se afirma validación visual en Microsoft Excel instalado. La prueba anterior Qt verifica las cinco pestañas del visor, foco del editor, tres tamaños y cálculos Decimal; no cambia el motor fiscal ni el manifiesto normativo.

Los contratos provocan una caída real con os._exit(24) durante la sustitución de tablas y comprueban rollback al abrir otra conexión. También verifican cancelación, fallo de publicación/INSERT, backup vacío, paths activos/auxiliares/enlaces duros, fuente cambiada después de revisar, candidato alterado, conflictos entre ventanas, tipos JSON dañados, esquema/versión/hash inválidos, búsqueda literal y paginación de56 sesiones sin omitir/duplicar IDs. El fallo de escritura se simula; no se llenó físicamente el disco.

Se inspeccionaron capturas reales del historial, revisión, confirmación y reporte restaurado. Frente al checkpoint SQLite anterior se observan el botón Qt añadido y pequeñas variaciones de rasterización en la captura inicial. No hay cambio de dimensiones del reporte, HTML/CSS/editor ni del baseline original. Los140 checks de navegador y las capturas anteriores permanecen como evidencia histórica, no se cuentan como ejecuciones nuevas de esta fase.

La base activa debe ser legible para producir el respaldo preventivo; no se sobrescribe una base activa corrupta ni se realiza reparación forense. Permanecen fuera cifrado, limpieza/retención automática de backups, programación de respaldos, edición compartida/sincronizada entre equipos, grants/caché incremental, Windows limpio/DPI125/150, validación integral de complementos y EXE final. Las comprobaciones de hashes no autentican un archivo frente a modificaciones deliberadas de datos y hashes.

[Contrato y límites](21_HISTORIAL_RESPALDOS_SQLITE.md) · [Reproducción](../scripts/history/README.md). Evidencia en `tests/history/evidence/verification.json`, contratos y `tests/history/qt/acceptance.json`; capturas y exportaciones usan únicamente datos sintéticos. La verificación vincula fuentes actuales con las ejecuciones. Commit/bundle nuevos locales, sin bases del usuario ni remotos.
'''
    (ROOT/'docs/22_HISTORIAL_RESPALDOS_REPORT.md').write_text(report, encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'source_sha256'}, indent=2))


if __name__ == '__main__':
    main()
