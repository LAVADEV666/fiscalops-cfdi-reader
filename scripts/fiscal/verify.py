"""Verify fiscal deliverables and protected SPEC011 artifacts. No network or UI mutation."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'tests/fiscal'), str(ROOT/'scripts/fiscal')]
from app.fiscal.service import inspect_invoice, json_data
from app.fiscal.sources import SatSources
from extract_catalogs import extract
from fixtures import concept, invoice, tax


def read(path):
    return json.loads((ROOT/path).read_text(encoding='utf-8'))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, check=True).stdout


def main():
    sources = SatSources()
    assert len(sources.records) == 16
    for source in sources.records:
        sources.resource(source)  # all original source hashes, including binary references
    derived = read('resources/sat/derived.json')
    assert sha((ROOT/'resources/sat/catalogs.json').read_bytes()) == derived['sha256']
    assert extract() == sources.catalogs  # read the official BIFF tables independently of the runtime lookup
    tests = read('tests/fiscal/evidence/tests.json')
    assert tests['success'] and tests['failures'] == tests['errors'] == 0
    assert tests['tests_run'] >= 59
    assert all(c['status'] == 'pass' for c in tests['cases'])
    actual_source_paths = {p.relative_to(ROOT).as_posix() for folder in ('app/fiscal', 'tests/fiscal') for p in (ROOT/folder).glob('*.py')}
    assert actual_source_paths == set(tests['source_sha256'])
    for relative, expected in tests['source_sha256'].items():
        assert sha((ROOT/relative).read_bytes()) == expected, 'Code changed after tests: '+relative
    fixture_results = []
    for fixture in read('tests/fiscal/fixtures/manifest.json')['fixtures']:
        data = (ROOT/'tests/fiscal/fixtures'/fixture['file']).read_bytes()
        assert sha(data) == fixture['sha256']
        result = json_data(inspect_invoice(data, sources=sources))
        assert result['validation']['xsd']['status'] == fixture['xsd_expected']
        assert result['analysis']['status'] == fixture['arithmetic_expected']
        fixture_results.append({'file': fixture['file'], 'xsd': result['validation']['xsd']['status'],
                                'arithmetic': result['analysis']['status']})
    protected = ['FiscalOps_CFDI_READER_SSGT_V21_1_PRO.html', 'legacy/FiscalOps_CFDI_READER_SSGT_V21_1_PRO.html']
    protected += [p.relative_to(ROOT).as_posix() for folder in ('app/ui', 'app/desktop', 'tests/visual/baseline')
                  for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    for relative in protected:
        assert (ROOT/relative).read_bytes() == git('show', 'ec63d840231d64fc872552f9db3fb67c8d9b3485:'+relative), relative
    baseline = read('tests/visual/baseline/manifest.json')
    assert len(baseline['captures']) == 60
    for capture in baseline['captures']:
        assert sha((ROOT/capture['path']).read_bytes()) == capture['sha256']
    report = read('tests/fiscal/evidence/pip-install.json')
    locks = ''.join((ROOT/'requirements'/name).read_text(encoding='utf-8') for name in ('fiscal.txt', 'fiscal-dev.txt'))
    for item in report['install']:
        assert item['metadata']['name']+'=='+item['metadata']['version'] in locks
        assert item['download_info']['archive_info']['hashes']['sha256'] in locks
    pip = subprocess.run([sys.executable, '-m', 'pip', 'check'], capture_output=True, text=True, check=True)
    assert sys.prefix != sys.base_prefix
    for relative in ('docs/06_MATRIZ_NORMATIVA_SAT.md', 'docs/15_MOTOR_FISCAL_P0_REPORT.md', 'docs/16_CONTRATO_MOTOR_FISCAL.md'):
        assert (ROOT/relative).stat().st_size > 1000
    # Regression deltas: old observations are evidence of defects, not expectations for the new engine.
    old = {r['id']: r['value'] for r in read('tests/audit/evidence/node-results.json')['results']}

    def analysis(name):
        return json_data(inspect_invoice((ROOT/'tests/fiscal/fixtures'/name).read_bytes(), sources=sources))['analysis']

    mixed = analysis('p0_iva_ieps_40.xml')['recalculated']
    reten = analysis('p0_isr_retention_40.xml')['recalculated']
    local = analysis('p0_local_once_40.xml')['recalculated']
    fallback = analysis('p0_missing_aggregate_40.xml')['recalculated']
    exempt = tax(factor='Exento', rate=None, amount=None)
    ex = json_data(inspect_invoice(invoice(concepts=[concept(taxes=[exempt])], globals=[exempt],
                                          aggregate_transfer=None, total='100'), sources=sources))['analysis']['recalculated']
    deltas = [
        {'risk': 'F01', 'old': old['N02-iva-ieps'], 'corrected': mixed['federal_by_code'], 'expected_IVA': '16', 'expected_IEPS': '8'},
        {'risk': 'F02', 'old': old['N03-retention-label'], 'corrected_ISR': reten['federal_by_code']['ISR_retention'], 'expected': '10'},
        {'risk': 'F03', 'old_difference': old['N04-local-double'], 'corrected_total': local['total_from_tax_details'],
         'corrected_difference': local['difference_total_minus_details'], 'expected_total': '119'},
        {'risk': 'F04', 'old': old['N06-exempt-zero'], 'corrected': ex['iva_bases'], 'expected_zero': '0', 'expected_exempt': '100'},
        {'risk': 'F05', 'old_IVA': old['N07-fallback-double'], 'corrected_IVA': fallback['federal_by_code']['IVA_transfer'],
         'reported_formula': fallback['total_from_reported_components'], 'expected_IVA': '16'},
        {'risk': 'F06', 'old': old['N08-decimals'], 'corrected': {'sum': '0.3', 'missing': None, 'invalid': None, 'rounded': '1.01'}}]
    assert mixed['federal_by_code']['IVA_transfer'] == '16' and mixed['federal_by_code']['IEPS_transfer'] == '8'
    assert reten['federal_by_code']['ISR_retention'] == '10'
    assert local['total_from_tax_details'] == '119.00' and local['difference_total_minus_details'] == '0.00'
    assert ex['iva_bases']['zero_rate'] == '0' and ex['iva_bases']['exempt'] == '100'
    assert fallback['federal_by_code']['IVA_transfer'] == '16' and fallback['total_from_reported_components'] is None
    (ROOT/'tests/fiscal/evidence/p0-deltas.json').write_text(json.dumps(deltas, indent=2)+'\n', encoding='utf-8')
    verification = {'status': 'pass', 'scope': 'independent XML/Decimal engine I/E CFDI3.3/4.0',
                    'tests': tests['tests_run'], 'recorded_cases_including_subtests': len(tests['cases']),
                    'official_sources_verified': len(sources.records), 'catalog_extraction_matches_official_xls': True,
                    'fixtures': fixture_results, 'protected_files_byte_identical_to_spec011': len(protected),
                    'baseline_images_preserved': 60, 'pip_check': pip.stdout.strip(), 'isolated_venv': True,
                    'qt_fiscal_flow': 'legacy; not migrated', 'global_project_done': False,
                    'not_implemented': ['Qt worker integration', 'ZIP/cache/SQLite', 'complete historical catalogs',
                                        'full complement rules', 'cryptographic/SAT status validation', 'final EXE']}
    (ROOT/'tests/fiscal/evidence/verification.json').write_text(json.dumps(verification, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in verification.items() if k != 'fixtures'}, indent=2))


if __name__ == '__main__':
    main()
