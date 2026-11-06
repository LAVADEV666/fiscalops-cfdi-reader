"""End-to-end delivery verification, including native downloads and protected artifacts."""
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


def read(relative):
    return json.loads((ROOT/relative).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen(relative):
    return subprocess.run(['git', 'show', '7846ebe98f0a09cecf83915c8102a6d46ce0ca1d:'+relative], cwd=ROOT, capture_output=True, check=True).stdout


def main():
    current = source_hashes()
    contracts = read('tests/integration/evidence/contracts.json')
    assert contracts['success'] and contracts['tests'] == 28 and contracts['failures'] == contracts['errors'] == 0
    assert contracts['source_sha256'] == current
    assert all(c['status'] == 'pass' for c in contracts['cases'])
    fiscal = read('tests/integration/evidence/fiscal-tests.json')
    assert fiscal['success'] and fiscal['tests_run'] == 59 and fiscal['failures'] == fiscal['errors'] == 0
    for relative, expected in fiscal['source_sha256'].items():
        assert sha(ROOT/relative) == expected
    suites = {}
    for relative, label, count in [('qt/smoke.json', 'qt-smoke', 34), ('jobs/jobs.json', 'qt-jobs', 17)]:
        report = read('tests/integration/'+relative)
        assert not report.get('fatal') and report['closed'] and report['worker_stopped']
        assert report['source_sha256'] == current
        assert len(report['checks']) == count
        assert all(c['result'] == 'PASS' for c in report['checks'])
        assert not any('Uncaught' in item['message'] for item in report['console'])
        suites[label] = count
    qt = read('tests/integration/qt/smoke.json')
    assert qt['platform'] == 'windows' and qt['native_win_id'] > 0
    assert qt['gui_thread_id'] not in qt['worker_thread_ids'] and qt['worker_thread_ids']
    jobs = read('tests/integration/jobs/jobs.json')
    assert jobs['progress_capture']['accepted'] and jobs['cancellation_seconds'] < 5 and jobs['close_seconds'] < 5
    for relative, key, label, count in [('browser/evidence/navigation.json', 'checks', 'browser-navigation-reference', 48),
                                       ('controls/controls.json', 'checks', 'browser-controls-reference', 30),
                                       ('targeted/results.json', 'after', 'browser-targeted-reference', 62)]:
        report = read('tests/integration/'+relative)
        assert not report.get('fatal') and len(report[key]) == count
        assert all(c['result'] == 'PASS' for c in report[key])
        suites[label] = count
    nav = read('tests/integration/browser/evidence/navigation.json')
    assert nav['development_runtime_sha256'] == current['app/ui/legacy-runtime.js']
    assert not any(c.get('type') == 'pageerror' for c in nav['console'])
    no_native = read('tests/integration/evidence/no-native.json')
    assert no_native['success'] and no_native['development_runtime_sha256'] == current['app/ui/legacy-runtime.js']
    captures = read('tests/integration/visual/captures.json')
    comparison = read('tests/integration/visual/comparison.json')
    assert captures['source_sha256'] == comparison['source_sha256'] == current
    assert not captures.get('fatal') and captures['windows_closed'] == [True, True]
    assert len(captures['captures']) == 36 and len(comparison['pairs']) == 18
    for capture in captures['captures']:
        assert capture['actual_viewport'] == f'{capture["width"]}x{capture["height"]}'
        assert sha(ROOT/capture['file']) == capture['sha256']
    assert all(p['comparable'] and p['changedPercent'] < 1 for p in comparison['pairs'])
    assert all(p['changedPixels'] == 0 for p in comparison['pairs'] if p['scene'] in ('visor', 'taxes', 'excel'))
    assert all(p['changedPercent'] < .05 for p in comparison['pairs'] if p['scene'] == 'report')
    original = ROOT/'FiscalOps_CFDI_READER_SSGT_V21_1_PRO.html'
    assert sha(original) == '33eeed2334a683b5360c2fc4f9cabc26885be66fef8714e4278f97235b8c373b'
    assert original.read_bytes() == (ROOT/'legacy'/original.name).read_bytes()
    for relative in ('app/ui/index.html', 'app/ui/column-editor.js', 'app/ui/v20-runtime.js', 'tests/visual/baseline/manifest.json'):
        assert (ROOT/relative).read_bytes() == frozen(relative), relative
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
    output = ROOT/'tests/integration/qt'
    worksheet_ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(output/'FiscalOps_summary.xlsx') as archive:
        assert archive.testzip() is None
        assert len([p for p in archive.namelist() if p.startswith('xl/worksheets/sheet')]) == 8
        for name in archive.namelist():
            if name.endswith(('.xml', '.rels')):
                ET.fromstring(archive.read(name))
        sheet = ET.fromstring(archive.read('xl/worksheets/sheet1.xml'))
        header = [''.join(c.itertext()) for c in sheet.findall('./s:sheetData/s:row[@r="1"]/s:c/s:is/s:t', worksheet_ns)]
        rows = []
        for xml_row in sheet.findall('./s:sheetData/s:row', worksheet_ns)[1:]:
            rows.append([''.join(c.itertext()) for c in xml_row])
        iva, retained, total = map(header.index, ('IVA trasladado', 'Retenciones', 'Total'))
        assert [r[iva] for r in rows] == ['16', '16', '0']
        assert [r[retained] for r in rows] == ['0', '0', '10']
        assert [r[total] for r in rows] == ['124', '119', '90']
        assert 'FF4F2D7F' in archive.read('xl/styles.xml').decode()
        assert b'FiscalOps V21' in archive.read('docProps/core.xml')
        assert b'FiscalOps V21' in archive.read('docProps/app.xml')
        assert b'Generado' in archive.read('xl/worksheets/sheet2.xml')
        assert sheet.find('./s:sheetViews/s:sheetView/s:pane', worksheet_ns).get('ySplit') == '1'
    with (output/'FiscalOps_summary.csv').open(encoding='utf-8-sig', newline='') as stream:
        csv_rows = list(csv.DictReader(stream))
    assert len(csv_rows) == 3 and [row['IVA trasladado'] for row in csv_rows] == ['16', '16', '0']
    with (output/'filtered_FiscalOps_summary.csv').open(encoding='utf-8-sig', newline='') as stream:
        filtered = list(csv.DictReader(stream))
    assert len(filtered) == 1 and filtered[0]['Folio'] == 'CASE-1' and filtered[0]['Total'] == '119'
    lines = (output/'FiscalOps_summary.txt').read_text(encoding='utf-8-sig').splitlines()
    assert len(lines) == 4 and all(len(line.split('~')) == len(header) for line in lines)
    assert lines[-1].split('~')[iva] == '0'
    for folder in ('app/desktop', 'app/fiscal', 'scripts/integration', 'tests/integration'):
        for path in (ROOT/folder).glob('*.py'):
            ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
    assert subprocess.run([sys.executable, '-m', 'pip', 'check'], capture_output=True).returncode == 0
    for relative in ('docs/17_INTEGRACION_QT_WORKERS_REPORT.md', 'docs/18_CONTRATO_QT_WORKERS.md'):
        assert (ROOT/relative).stat().st_size > 1000
    result = {'status': 'pass', 'scope': 'Qt worker integration; not global SAT certification',
              'fiscal_tests': 59, 'contract_tests': 28, 'suites': suites,
              'native_window_and_thread_verified': True, 'no_native_no_legacy_fallback': True,
              'xlsx_sheets': 8, 'native_downloads_completed': True, 'filtered_export_rows': 1,
              'visual_pairs': 18, 'maximum_visual_percent': max(p['changedPercent'] for p in comparison['pairs']),
              'baseline_images_unchanged': 60, 'original_legacy_html_css_unchanged': True,
              'cancellation_seconds': jobs['cancellation_seconds'], 'close_seconds': jobs['close_seconds'],
              'progress_capture_accepted': True, 'official_source_hashes_preserved': len(sources.records),
              'source_sha256': current,
              'remaining': ['persistent SQLite/cache/grants', 'full complement/SAT/signature validation', 'DPI125/150 and clean Windows', 'final EXE']}
    (ROOT/'tests/integration/evidence/verification.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'source_sha256'}, indent=2))


if __name__ == '__main__':
    main()
