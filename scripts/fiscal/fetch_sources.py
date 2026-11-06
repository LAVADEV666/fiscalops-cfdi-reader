"""Explicit maintenance command: snapshot SAT resources; never used by the reader."""
from concurrent.futures import ThreadPoolExecutor
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'resources/sat'
BASE = 'http://omawww.sat.gob.mx/tramitesyservicios/Paginas/'
SAT = 'https://www.sat.gob.mx/sitio_internet/cfd/'
SOURCES = {
    'portal': (BASE+'anexo_20.htm', 'anexo_20.htm'),
    'cfdi40': (SAT+'4/cfdv40.xsd', 'cfdv40.xsd'),
    'cfdi33': (SAT+'3/cfdv33.xsd', 'cfdv33.xsd'),
    'catalog_xsd': (SAT+'catalogos/catCFDI.xsd', 'catCFDI.xsd'),
    'types': (SAT+'tipoDatos/tdCFDI/tdCFDI.xsd', 'tdCFDI.xsd'),
    'local10': (SAT+'implocal/implocal.xsd', 'implocal.xsd'),
    'tfd11': (SAT+'TimbreFiscalDigital/TimbreFiscalDigitalv11.xsd', 'TimbreFiscalDigitalv11.xsd'),
    'matrix40': (BASE+'documentos/MatrizDeErrores_CFDI_v40_20260325.xls', 'matrix40.xls'),
    'matrix33': (BASE+'documentos/MatrizDeErrores_CFDI_v33.xls', 'matrix33.xls'),
    'catalog40': (BASE+'documentos/catCFDI_V_4_20261106.xls', 'catalog40.xls'),
    'catalog33': (BASE+'documentos/catCFDI_V_33_31032023.xls', 'catalog33.xls'),
    'standard40': (BASE+'documentos/Anexo20_2022.pdf', 'standard40.pdf'),
    'standard33': (BASE+'documentos/cfdv33.pdf', 'standard33.pdf'),
    'faq40': (BASE+'documentos/PregFrecCFDIVer4_0.pdf', 'faq40.pdf'),
    'chain40': (SAT+'4/cadenaoriginal_4_0/cadenaoriginal_4_0.xslt', 'cadenaoriginal_4_0.xslt'),
    'chain33': (SAT+'3/cadenaoriginal_3_3/cadenaoriginal_3_3.xslt', 'cadenaoriginal_3_3.xslt'),
}


def fetch(item):
    key, (url, name) = item
    record = {'id': key, 'url': url, 'file': name,
              'acquired_at': datetime.now(timezone.utc).isoformat()}
    try:
        with urlopen(url, timeout=20) as response:
            host = urlparse(response.url).hostname or ''
            if not (host == 'sat.gob.mx' or host.endswith('.sat.gob.mx')):
                raise ValueError('Non-SAT redirect refused')
            data = response.read(64*1024*1024+1)
            if len(data) > 64*1024*1024:
                raise ValueError('Source exceeds download limit')
            record.update(final_url=response.url, last_modified=response.headers.get('Last-Modified'),
                          content_type=response.headers.get('Content-Type'))
        if name.endswith(('.xsd', '.xslt')) and b'<html' in data[:1000].lower():
            raise ValueError('HTML returned instead of XML resource')
        path = DEST / name
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Existing snapshot differs; review/version it before replacing')
        path.write_bytes(data)
        record.update(status='downloaded', bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    except Exception as exc:
        record.update(status='unavailable', error=str(exc))
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--only', choices=list(SOURCES))
    args = parser.parse_args()
    DEST.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=6) as pool:
        records = list(pool.map(fetch, ((k, v) for k, v in SOURCES.items() if not args.only or k == args.only)))
    if args.only:
        previous = json.loads((DEST/'manifest.json').read_text(encoding='utf-8'))['sources']
        records = [next((r for r in records if r['id'] == p['id']), p) for p in previous]
    manifest = {'snapshot': 'sat-2026-11-06', 'historical_validity': 'not inferred from retrieval date',
                'sources': records}
    (DEST / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps([{k: r[k] for k in ('id', 'status', 'bytes', 'error') if k in r} for r in records], indent=2))


if __name__ == '__main__':
    main()
