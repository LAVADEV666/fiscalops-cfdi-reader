"""Verify actual screenshot artifacts and the stage's reported evidence."""
from pathlib import Path
import hashlib
import json
import subprocess
import zipfile
import xml.etree.ElementTree as ET
from freeze_manifest import image_info

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'tests/visual/evidence'
EXPECTED = '33eeed2334a683b5360c2fc4f9cabc26885be66fef8714e4278f97235b8c373b'


def main():
    for path in [ROOT / 'FiscalOps_CFDI_READER_SSGT_V21_1_PRO.html', ROOT / 'legacy/FiscalOps_CFDI_READER_SSGT_V21_1_PRO.html']:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == EXPECTED
    blob = subprocess.run(['git', 'show', 'HEAD:FiscalOps_CFDI_READER_SSGT_V21_1_PRO.html'], capture_output=True, check=True).stdout
    assert hashlib.sha256(blob).hexdigest() == EXPECTED
    baseline = json.loads((ROOT / 'tests/visual/baseline/manifest.json').read_text(encoding='utf-8'))
    assert baseline['prototype_sha256'] == EXPECTED
    sizes = {(1366, 768), (1600, 900), (1920, 1080)}
    for capture in baseline['captures']:
        path = ROOT / capture['path']
        assert path.resolve().is_relative_to(ROOT.resolve())
        info = image_info(path)
        assert info['sha256'] == capture['sha256']
        if 'before' in capture:
            assert tuple(info['pixel_dimensions']) in sizes
            before, after = capture['before'], capture['after']
            assert [before['viewport']['width'], before['viewport']['height']] == info['pixel_dimensions']
            assert before['deviceScaleFactor'] == after['deviceScaleFactor'] == 1
        else:
            assert info['pixel_dimensions'] == capture['pixel_dimensions']
            assert 'x'.join(map(str, info['pixel_dimensions'])) in path.stem
    assert baseline['accepted_automated_captures'] == 54
    assert baseline['supplemental_iab_captures'] == 6
    nav = json.loads((EVIDENCE / 'navigation.json').read_text(encoding='utf-8'))
    controls = json.loads((EVIDENCE / 'controls.json').read_text(encoding='utf-8'))
    assert 'fatal' not in nav and 'fatal' not in controls
    checks = nav['checks'] + controls['checks']
    assert len(checks) == 78
    assert sum(check['result'] == 'PASS' for check in checks) == 70
    assert sum(check['result'] == 'FAIL' for check in checks) == 8
    assert all(request['url'].startswith('http://127.0.0.1:') for request in nav['requests'])
    exports = []
    for path in sorted(EVIDENCE.glob('visual-export-*.xlsx')):
        with zipfile.ZipFile(path) as archive:
            assert archive.testzip() is None
            for name in archive.namelist():
                if name.endswith(('.xml', '.rels')):
                    ET.fromstring(archive.read(name))
            exports.append({'file': path.name, 'parts': len(archive.namelist()), 'zip_xml': 'PASS'})
    assert len(exports) == 3
    assert (EVIDENCE / 'controls-export.csv').stat().st_size > 0
    assert (EVIDENCE / 'controls-export.txt').stat().st_size > 0
    buttons = json.loads((EVIDENCE / 'buttons.json').read_text(encoding='utf-8'))
    assert buttons['original_buttons'] == 50 and len(buttons['buttons']) == 55
    docs = ['07_BASELINE_VISUAL', '08_MATRIZ_COMPATIBILIDAD_UI', '09_ARQUITECTURA_DESKTOP', '10_PLAN_RECONSTRUCCION_MOTOR']
    for name in docs:
        assert (ROOT / 'docs' / (name+'.md')).stat().st_size > 1000
    server = json.loads((EVIDENCE / 'server-tests.json').read_text(encoding='utf-8'))
    assert server['successful'] and server['tests'] == 6
    qt = json.loads((EVIDENCE / 'desktop-check.json').read_text(encoding='utf-8'))
    assert not qt['gui_executed']
    report = {'prototype_and_legacy_hash': EXPECTED, 'git_blob_hash': 'MATCH',
              'baseline_images_verified': len(baseline['captures']), 'accepted_automated_png': 54, 'supplemental_native_jpeg': 6,
              'viewport_sizes': sorted(sizes), 'navigation_checks': len(checks), 'pass': 70, 'preexisting_fail': 8,
              'server_tests_pass': 6, 'buttons_original': 50, 'viewer_tabs_dynamic': 5,
              'xlsx_actual_downloads': exports, 'desktop_status': qt['status'],
              'overall_stage': 'PARTIAL', 'windows_dpi': 'NOT_MEASURED',
              'folder_memory': 'MANUAL_PENDING', 'progress': 'TRANSIENT_NOT_ACCEPTED',
              'fiscal_compliance': 'NOT_CERTIFIED'}
    (EVIDENCE / 'verification-stage1.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
