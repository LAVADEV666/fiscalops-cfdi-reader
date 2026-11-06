"""Verify SPEC011 evidence, source boundaries and frozen artifacts."""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import xml.etree.ElementTree as ET
import zipfile

ROOT=Path(__file__).resolve().parents[2]
EXPECTED='33eeed2334a683b5360c2fc4f9cabc26885be66fef8714e4278f97235b8c373b'


def read(relative):return json.loads((ROOT/relative).read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert sha(ROOT/'FiscalOps_CFDI_READER_SSGT_V21_1_PRO.html')==EXPECTED
    assert sha(ROOT/'legacy/FiscalOps_CFDI_READER_SSGT_V21_1_PRO.html')==EXPECTED
    manifest=ROOT/'tests/visual/baseline/manifest.json'
    frozen=subprocess.run(['git','show','spec011-start-20261106:tests/visual/baseline/manifest.json'],cwd=ROOT,capture_output=True,check=True).stdout
    assert manifest.read_bytes()==frozen
    baseline=read('tests/visual/baseline/manifest.json')
    assert len(baseline['captures'])==60
    assert all(sha(ROOT/c['path'])==c['sha256'] for c in baseline['captures'])
    build=read('tests/spec011/evidence/development-build.json')
    assert build['css_unchanged'] and len(build['fiscal_regions_unchanged'])==4
    for name,digest in build['files'].items():assert sha(ROOT/'app/ui'/name)==digest
    nav=read('tests/spec011/browser/evidence/navigation.json')
    controls=read('tests/spec011/controls/controls.json')
    targeted=read('tests/spec011/targeted/results.json')
    qt=read('tests/spec011/qt/smoke.json')
    assert nav['development_runtime_sha256']==build['files']['legacy-runtime.js']
    suites={'navigation':nav['checks'],'controls':controls['checks'],'targeted':targeted['after'],'qt':qt['checks']}
    expected={'navigation':48,'controls':30,'targeted':62,'qt':30}
    for name,cases in suites.items():
        assert len(cases)==expected[name]
        assert all(case['result']=='PASS' for case in cases),(name,[c for c in cases if c['result']!='PASS'])
    assert sum(c['result']=='FAIL' for c in targeted['before'])==5
    assert not any(d.get('fatal') for d in [nav,controls,targeted,qt])
    assert not any(c['type']=='pageerror' for c in nav['console'])
    assert qt['platform']=='windows' and qt['native_win_id']>0
    assert qt['offline_proof']['fetch_rejected'] and not qt['offline_proof']['external_url_allowlisted']
    assert qt['offline_proof']['transport']=='local files; no HTTP server'
    visual=read('tests/spec011/visual/comparison.json')
    qt_visual=read('tests/spec011/qt-visual/comparison.json')
    assert len(visual['pairs'])==18 and all(v['changedPixels']==0 for v in visual['pairs'])
    assert len(visual['baselineComparisons'])==54
    assert len(qt_visual['pairs'])==18 and max(v['changedPercent'] for v in qt_visual['pairs'])<0.3
    assert all(v['changedPixels']==0 for v in qt_visual['pairs'] if v['scene'] in ('editor','viewer','excel'))
    exported=targeted['export']
    book=ROOT/'tests/spec011/targeted'/exported['file']
    with zipfile.ZipFile(book) as archive:
        assert archive.testzip() is None
        ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        sheet=ET.fromstring(archive.read('xl/worksheets/sheet1.xml'))
        headers=[''.join(c.itertext()) for c in sheet.findall('.//s:row[@r="1"]/s:c/s:is/s:t',ns)]
        assert headers==exported['expectedHeaders']
    dependency=read('tests/spec011/evidence/desktop-environment.json')
    assert dependency['isolated_venv'] and dependency['qt']=='6.12.0' and dependency['qwebchannel_js']
    lock=(ROOT/'requirements/desktop-spec011.txt').read_text(encoding='utf-8')
    installed=read('tests/spec011/evidence/pip-install.json')['install']
    for item in installed:
        assert item['metadata']['name']+'=='+item['metadata']['version'] in lock
        assert item['download_info']['archive_info']['hashes']['sha256'] in lock
    for name in ['11_UI_STABILIZATION_REPORT','12_DESKTOP_SMOKE_REPORT','13_UI_REGRESSION_MATRIX','14_HANDOFF_MOTOR_FISCAL']:
        assert (ROOT/'docs'/(name+'.md')).stat().st_size>1000
    report={'phase_1_1':'DONE','phase_1_2':'DONE (native Windows smoke scope)','original_and_legacy_sha256':EXPECTED,
            'baseline_images_unchanged':60,'baseline_metadata_unchanged':True,'fiscal_regions_unchanged':True,
            'suites':{name:{'pass':len(cases),'fail':0} for name,cases in suites.items()},
            'original_defects_reproduced':5,'chromium_paired_comparisons':18,'chromium_paired_max_percent':0,
            'qt_paired_max_percent':max(v['changedPercent'] for v in qt_visual['pairs']),
            'qt_cross_renderer_max_percent':max(v['changedPercent'] for v in qt_visual['crossRenderer']),
            'export_headers_match_applied':True,'global_python_pyside6_present':bool(importlib.util.find_spec('PySide6')),
            'native_progress_stable':qt.get('progress_capture',{}).get('accepted_stable_capture',False),
            'not_certified':['native folder grants/reconnect','portable profile persistence','stable progress capture','DPI125/150','SAT/fiscal correctness','portable EXE']}
    (ROOT/'tests/spec011/evidence/verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
