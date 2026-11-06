"""Freeze only the actually installed fiscal wheels from pip's retained install report."""
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
from lxml import etree

ROOT = Path(__file__).resolve().parents[2]


def main():
    report = json.loads((ROOT/'tests/fiscal/evidence/pip-install.json').read_text(encoding='utf-8'))
    lines = {}
    wheels = []
    for item in report['install']:
        metadata = item['metadata']
        name = metadata['name']
        assert name.lower() in ('lxml', 'xlrd')
        assert importlib.metadata.version(name) == metadata['version']
        digest = item['download_info']['archive_info']['hashes']['sha256']
        lines[name.lower()] = f"{name}=={metadata['version']} --hash=sha256:{digest}\n"
        wheels.append({'name': name, 'version': metadata['version'], 'url': item['download_info']['url'],
                       'sha256': digest, 'license_expression': metadata.get('license_expression'), 'license': metadata.get('license')})
    header = '# Windows x64 / CPython 3.11; install into project .venv only.\n--index-url https://pypi.org/simple\n--only-binary=:all:\n'
    (ROOT/'requirements/fiscal.txt').write_text(header+lines['lxml'], encoding='utf-8')
    (ROOT/'requirements/fiscal-dev.txt').write_text('# Catalog maintenance only; not required to inspect CFDI.\n-r fiscal.txt\n'+lines['xlrd'], encoding='utf-8')
    environment = {'isolated_venv': sys.prefix != sys.base_prefix, 'python': platform.python_version(),
                   'platform': platform.platform(), 'lxml': etree.LXML_VERSION, 'libxml2': etree.LIBXML_VERSION,
                   'libxslt': etree.LIBXSLT_VERSION, 'wheels': wheels,
                   'note': 'Observed wheel license metadata; no final distribution/license certification.'}
    assert environment['isolated_venv']
    (ROOT/'tests/fiscal/evidence/environment.json').write_text(json.dumps(environment, indent=2), encoding='utf-8')
    print('Fiscal runtime/development wheel hashes locked; isolated venv verified')


if __name__ == '__main__':
    main()
