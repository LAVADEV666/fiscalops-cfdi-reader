"""Materialize the synthetic fixtures and their immutable expectations for review."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tests/fiscal'))
from fixtures import samples


def main():
    entries = []
    for name, data in samples().items():
        (ROOT/'tests/fiscal/fixtures'/name).write_bytes(data)
        entries.append({'file': name, 'sha256': hashlib.sha256(data).hexdigest(),
                        'xsd_expected': 'fail' if 'missing_subtotal' in name else 'pending' if 'unknown_' in name else 'pass',
                        'arithmetic_expected': 'error' if 'missing_' in name else 'partial' if 'unknown_' in name else 'consistent-in-scope'})
    (ROOT/'tests/fiscal/fixtures/manifest.json').write_text(json.dumps({
        'provenance': 'Synthetic fixtures constructed from official schemas and scoped rule expectations; not SAT-issued/certified or cryptographically signed.',
        'fixtures': entries}, indent=2)+'\n', encoding='utf-8')
    print(f'{len(entries)} synthetic fixtures built')


if __name__ == '__main__':
    main()
