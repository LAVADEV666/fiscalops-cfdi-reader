"""Verify SQLite delivery evidence and frozen artifacts; generate the acceptance report."""
import ast
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


def read(relative):
    return json.loads((ROOT/relative).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    current = source_hashes()
    sql = read('tests/persistence/evidence/contracts.json')
    contracts = read('tests/integration/evidence/contracts.json')
    for report, count in ((sql, 20), (contracts, 28)):
        assert report['source_sha256'] == current and report['success'] and report['tests'] == count
        assert report['errors'] == report['failures'] == 0
        assert all(c['status'] == 'pass' for c in report['cases'])
    fiscal = read('tests/persistence/evidence/fiscal-tests.json')
    assert fiscal['success'] and fiscal['tests_run'] == 59 and fiscal['errors'] == fiscal['failures'] == 0
    for relative, digest in fiscal['source_sha256'].items():
        assert sha(ROOT/relative) == digest
    for relative, count in (('qt/smoke.json', 34), ('jobs/jobs.json', 17)):
        report = read('tests/integration/'+relative)
        assert report['source_sha256'] == current and not report.get('fatal') and report['closed'] and report['worker_stopped']
        assert len(report['checks']) == count and all(c['result'] == 'PASS' for c in report['checks'])
        assert not any('Uncaught' in c['message'] for c in report['console'])
    qt = read('tests/persistence/qt/recovery.json')
    assert qt['success'] and qt['source_sha256'] == current and qt['separate_processes'] == 3 and qt['checks'] == 34
    for phase in qt['phases']:
        assert phase['source_sha256'] == current and not phase.get('fatal') and phase['closed'] and phase['sqlite_closed_on_worker']
        assert all(c['result'] == 'PASS' for c in phase['checks'])
        assert not any('Uncaught' in c['message'] for c in phase['console'])
    assert qt['phases'][0]['close_save_result']['ok']
    assert qt['exported_csv_total'] == '119' and qt['xlsx_sheets'] == 8
    for name, digest in qt['exports_sha256'].items():
        assert sha(ROOT/'tests/persistence/qt'/name) == digest
    for folder in ('tests/persistence/qt', 'tests/integration/qt'):
        with zipfile.ZipFile(ROOT/folder/'FiscalOps_summary.xlsx') as archive:
            assert archive.testzip() is None
            assert len([n for n in archive.namelist() if n.startswith('xl/worksheets/')]) == 8
            for name in archive.namelist():
                if name.endswith(('.xml', '.rels')):
                    ET.fromstring(archive.read(name))
    no_native = read('tests/integration/evidence/no-native.json')
    assert no_native['success'] and no_native['development_runtime_sha256'] == current['app/ui/legacy-runtime.js']
    visuals = read('tests/persistence/visual/comparison.json')
    assert visuals['source_sha256'] == current and len(visuals['pairs']) == 3
    assert all(p['comparable'] and p['changedPercent'] < .02 for p in visuals['pairs'])
    maximum = max(p['changedPercent'] for p in visuals['pairs'])
    original = ROOT/'FiscalOps_CFDI_READER_SSGT_V21_1_PRO.html'
    assert sha(original) == '33eeed2334a683b5360c2fc4f9cabc26885be66fef8714e4278f97235b8c373b'
    assert original.read_bytes() == (ROOT/'legacy'/original.name).read_bytes()
    for relative in ('app/ui/index.html', 'app/ui/v20-runtime.js', 'app/ui/column-editor.js', 'tests/visual/baseline/manifest.json'):
        previous = subprocess.run(['git', 'show', '0b19884ea75875eb7c0208d18c18d62d86d89093:'+relative], cwd=ROOT, capture_output=True, check=True).stdout
        assert (ROOT/relative).read_bytes() == previous
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
    for folder in ('app/desktop', 'scripts/persistence', 'tests/persistence'):
        for path in (ROOT/folder).glob('*.py'):
            ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
    assert subprocess.run([sys.executable, '-m', 'pip', 'check'], capture_output=True).returncode == 0
    assert subprocess.run(['git', 'check-ignore', 'FiscalOpsData/fiscalops.sqlite3'], cwd=ROOT, capture_output=True).returncode == 0
    assert (ROOT/'docs/19_PERSISTENCIA_SQLITE.md').stat().st_size > 1000
    result = {'status': 'pass', 'source_sha256': current, 'sqlite_contracts': 20, 'integration_contracts': 28,
              'fiscal_tests': 59, 'qt_smoke': 34, 'qt_jobs': 17, 'qt_recovery': 34, 'qt_recovery_processes': 3,
              'crash_rollback_verified': True, 'immediate_close_view_saved': True, 'database_owned_and_closed_by_worker': True,
              'xlsx_sheets': 8, 'filtered_csv_total': '119', 'baseline_preserved': 60,
              'visual_pairs': 3, 'maximum_visual_percent': maximum, 'official_sources_preserved': len(sources.records),
              'remaining': ['visual history manager and backup/restore UI', 'incremental cache and persistent folder grants',
                            'shared/multi-device database and file synchronization', 'full complementary SAT validation', 'clean Windows/DPI125/150 and EXE']}
    (ROOT/'tests/persistence/evidence/verification.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    text = f'''# Persistencia SQLite — entrega y evidencia

Implementada en Qt: originales y metadata, resultados fiscales, proyecciones de los22 reportes y sesiones se guardan en `FiscalOpsData/fiscalops.sqlite3`. La última sesión activa se recupera sin releer los archivos ni volver al parser JavaScript. Los filtros, perfil, columnas y XML del visor sobreviven al cierre.

La conexión es exclusiva del worker; se abre y se cierra en ese hilo. Una transacción confirma toda la carga y la sesión activa antes de publicar el reporte. Cancelación, bloqueo, escritura fallida o caída a mitad de transacción conservan la sesión confirmada anterior. Los importes usan cadenas decimales y nulos, sin REAL/float ni cálculos SQL.

| Verificación actual | Resultado |
|---|---|
| Contratos SQLite |20/20 PASS |
| Contratos de integración/reportes |28/28 PASS |
| Motor fiscal |59/59 PASS |
| Ventana Qt y exportaciones |34/34 PASS |
| Jobs Qt, cancelación/reintento/cierre |17/17 PASS |
| Recuperación en tres procesos Qt Windows |34/34 PASS |
| HTML distribuido sin Qt |Bloquea procesamiento/exportación; sin fallback |
| Comparación de reportes a tres tamaños |Máximo {maximum:.6f}% de píxeles distintos |
| HTML/CSS/editor y baseline60 |Preservados |
| Fuentes oficiales fijadas |{len(sources.records)} hashes verificados |

La prueba de recuperación crea una base temporal real, carga tres CFDI sintéticos, guarda un filtro/columnas, cierra inmediatamente después de cambiar el filtro y abre otro proceso Qt. El segundo recupera las mismas identidades, perfil fiscal, columnas y búsqueda, muestra las cinco pestañas del visor y exporta XLSX, CSV y TXT de una sola fila: IVA16 y Total119. XLSX contiene8 hojas y todas sus partes XML/CRC se verifican. Se comprueba DownloadCompleted; no se presenta la existencia de un archivo parcial como guardado exitoso.

El segundo proceso limpia la sesión activa; el tercero permanece vacío. SQLite conserva el historial anterior y sus tres resultados, con integridad correcta. Los tests de contrato prueban además apertura de historial y purga completa, originales UTF16, metadata/incidencias, las22 familias de reporte, cero/NULL, deduplicación de bytes conservando instancias, identidades/orden de exportación, versiones futuras, hashes alterados y conflicto entre ventanas.

La caída se provoca con `os._exit(23)` en un subproceso dentro de la transacción, antes de activar la nueva sesión. La recuperación vuelve al commit anterior. El fallo de escritura se inyecta con un trigger temporal de prueba: no se llenó físicamente el disco. Se mantiene la protección de hilo de sqlite3 y se prueba su rechazo desde otro hilo.

La comparación visual usa capturas reales de los reportes Qt actuales contra el commit anterior a1366×768,1600×900 y1920×1080. Se inspeccionaron el reporte recuperado y la diferencia: las variaciones pequeñas provienen del logotipo animado, sin cambio del diseño. No se modificó el baseline. Las140 comprobaciones de navegador y las36 capturas del hito anterior permanecen como evidencia histórica; no se cuentan como una nueva ejecución SQLite.

Limpiar desactiva la sesión sin destruir historial. Doble clic en Borrar memoria elimina el contenido persistido, sin tocar originales seleccionados. El guardado de vista tiene debounce y captura final al cerrar; si el renderizador no responde o falla ese último guardado, permanece la última vista confirmada. No se afirma cifrado, borrado seguro, certificación SAT o validación visual mediante Microsoft Excel instalado.

Persisten los límites de carga del hito anterior. Historial sin borrado automático, selector visual de historial, backup/restauración desde UI, caché incremental, grants permanentes, base compartida entre equipos/sincronización, Windows limpio/DPI125/150 y EXE siguen fuera de esta fase. La cobertura normativa del motor permanece igual.

Evidencia: `tests/persistence/evidence/verification.json`, `contracts.json`, `fiscal-tests.json`, `tests/persistence/qt/recovery.json`, descargas reales y comparación visual. El verificador vincula los resultados a hashes actuales de aplicación. [Contrato y límites](19_PERSISTENCIA_SQLITE.md) · [Reproducción](../scripts/persistence/README.md).

Abrir desde la raíz con `.\\.venv\\Scripts\\python.exe -m app.desktop.main`. No cambia el lanzador ni se requiere instalar una dependencia adicional. Se guarda commit/bundle local nuevo sin remotos ni datos del usuario.
'''
    (ROOT/'docs/20_PERSISTENCIA_SQLITE_REPORT.md').write_text(text, encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'source_sha256'}, indent=2))


if __name__ == '__main__':
    main()
