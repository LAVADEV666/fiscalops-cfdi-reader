"""Read-only extraction of SAT BIFF catalogs into versioned runtime JSON (xlrd is build-only)."""
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import xlrd

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT/'resources/sat'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract():
    manifest = json.loads((DEST/'manifest.json').read_text(encoding='utf-8'))
    sources = {r['id']: r for r in manifest['sources']}
    result = {'snapshot': manifest['snapshot'], 'versions': {}}
    for version, suffix in [('4.0', '40'), ('3.3', '33')]:
        source = sources['catalog'+suffix]
        path = DEST/source['file']
        assert sha(path) == source['sha256']
        book = xlrd.open_workbook(path, on_demand=True)

        def date(cell):
            if cell.ctype == xlrd.XL_CELL_DATE or isinstance(cell.value, float) and cell.value > 20000:
                return xlrd.xldate_as_datetime(cell.value, book.datemode).date().isoformat()
            text = str(cell.value).strip()
            if not text:
                return None
            for pattern in ('%d/%m/%Y', '%Y-%m-%d'):
                try:
                    return datetime.strptime(text, pattern).date().isoformat()
                except ValueError:
                    pass
            raise ValueError('Unrecognized official catalog date: '+text)

        currencies = []
        sheet = book.sheet_by_name('c_Moneda')
        for row in range(5, sheet.nrows):
            key = str(sheet.cell_value(row, 0)).strip()
            if len(key) != 3:
                continue
            currencies.append({'code': key, 'digits': int(sheet.cell_value(row, 2)),
                               'valid_from': date(sheet.cell(row, 4)), 'valid_to': date(sheet.cell(row, 5)),
                               'sheet': sheet.name, 'row': row+1})
        rates = []
        sheet = book.sheet_by_name('c_TasaOCuota')
        for row in range(6, sheet.nrows):
            values = sheet.row_values(row)
            if values[0] not in ('Fijo', 'Rango'):
                continue
            def decimal(value):
                return format(Decimal(str(value)), '.6f') if value != '' else None
            rates.append({'kind': values[0], 'minimum': decimal(values[1]), 'maximum': decimal(values[2]),
                          'tax': str(values[3]), 'factor': str(values[4]),
                          'tax_code': {'ISR': '001', 'IVA': '002', 'IVA Crédito aplicado del 50%': '002', 'IEPS': '003'}[str(values[3])],
                          'transfer': str(values[5]).strip().lower() in ('sí', 'si'),
                          'retention': str(values[6]).strip().lower() in ('sí', 'si'),
                          'valid_from': date(sheet.cell(row, 7)), 'valid_to': date(sheet.cell(row, 8)),
                          'sheet': sheet.name, 'row': row+1})
        book.release_resources()
        matrix_source = sources['matrix'+suffix]
        matrix_path = DEST/matrix_source['file']
        assert sha(matrix_path) == matrix_source['sha256']
        matrix = xlrd.open_workbook(matrix_path, on_demand=True)
        sheet = matrix.sheet_by_index(0)
        rules = []
        for row in range(2, sheet.nrows):
            code = sheet.cell_value(row, 4 if suffix == '40' else 3)
            if not str(code).startswith('CFDI'):
                continue
            rules.append({'code': code, 'field': sheet.cell_value(row, 2 if suffix == '40' else 1),
                          'sheet': sheet.name, 'row': row+1})
        matrix.release_resources()
        result['versions'][version] = {'source_id': source['id'], 'source_sha256': source['sha256'],
                                       'matrix_source_id': matrix_source['id'], 'matrix_sha256': matrix_source['sha256'],
                                       'currencies': currencies, 'rates': rates, 'rules': rules}
    return result


def main():
    data = (json.dumps(extract(), ensure_ascii=False, indent=2)+'\n').encode('utf-8')
    (DEST/'catalogs.json').write_bytes(data)
    provenance = {'file': 'catalogs.json', 'sha256': hashlib.sha256(data).hexdigest(),
                  'extractor': 'scripts/fiscal/extract_catalogs.py',
                  'note': 'BIFF numeric rate cells converted via Decimal(str(value)) to six decimal places. Invoice money never uses BIFF/float.'}
    (DEST/'derived.json').write_text(json.dumps(provenance, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({v: {k: len(record[k]) for k in ('currencies', 'rates', 'rules')} for v, record in extract()['versions'].items()}, indent=2))


if __name__ == '__main__':
    main()
