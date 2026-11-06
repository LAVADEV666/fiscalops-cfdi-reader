"""Verify audit deliverables and generated ZIP/XML evidence using stdlib only."""
from pathlib import Path
import hashlib
import json
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'tests/audit/evidence'
NAME = 'FiscalOps_CFDI_READER_SSGT_V21_1_PRO.html'


def main():
    inventory = json.loads((EVIDENCE / 'inventory.json').read_text(encoding='utf-8'))
    assert hashlib.sha256((ROOT / NAME).read_bytes()).hexdigest() == inventory['sha256']
    assert (ROOT / NAME).read_bytes() == (ROOT / 'legacy' / NAME).read_bytes()
    for item in inventory['styles'] + inventory['images']:
        assert hashlib.sha256((ROOT / item['path']).read_bytes()).hexdigest() == item['sha256']
    docs = ['00_AUDITORIA_LEGACY', '01_INVENTARIO_FUNCIONAL', '02_MATRIZ_DE_RIESGOS',
            '03_PLAN_DE_MIGRACION', '04_CONTRATOS_UI', '05_BACKLOG_PRIORIZADO']
    for name in docs:
        assert (ROOT / 'docs' / f'{name}.md').stat().st_size > 1000
    with zipfile.ZipFile(EVIDENCE / 'synthetic-export.xlsx') as archive:
        assert archive.testzip() is None
        names = archive.namelist()
        for name in names:
            ET.fromstring(archive.read(name))
        ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        sheet = ET.fromstring(archive.read('xl/worksheets/sheet1.xml'))
        assert sheet.find('.//s:c[@r="B2"]/s:v', ns).text == '116.25'
        assert sheet.find('.//s:c[@r="A2"]', ns).get('t') == 'inlineStr'
        empty = ET.fromstring(archive.read('xl/worksheets/sheet2.xml'))
        assert len(empty.findall('.//s:row', ns)) == 1
    invalid_control_reproduced = False
    try:
        ET.fromstring((EVIDENCE / 'invalid-control-cell.xml').read_bytes())
    except ET.ParseError:
        invalid_control_reproduced = True
    assert invalid_control_reproduced
    results = json.loads((EVIDENCE / 'node-results.json').read_text(encoding='utf-8'))
    assert len(results['results']) == 26
    assert all(item['status'] == 'REPRODUCED' for item in results['results'])
    report = {'preservation': 'PASS', 'resource_hashes': 'PASS', 'required_documents': len(docs),
              'diagnostic_observations': len(results['results']), 'xlsx_crc': 'PASS',
              'xlsx_xml_parts': len(names), 'numeric_cell': '116.25', 'uuid_text': 'PASS',
              'empty_sheet': 'PASS', 'invalid_xml_control_reproduced': invalid_control_reproduced,
              'visual_baseline': 'BLOCKED_VISUAL_BASELINE', 'excel_application_open': 'NOT_TESTED',
              'fiscal_compliance': 'NOT_CERTIFIED'}
    (EVIDENCE / 'verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
