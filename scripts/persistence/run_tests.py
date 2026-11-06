"""Retain SQLite acceptance results, bound to the current application sources."""
import json
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.fiscal.run_tests import RecordedResult
from scripts.integration.evidence import source_hashes


def main():
    start, hashes = time.monotonic(), source_hashes()
    suite = unittest.defaultTestLoader.discover(str(ROOT/'tests/persistence'), pattern='test_*.py')
    result = unittest.TextTestRunner(verbosity=2, resultclass=RecordedResult).run(suite)
    assert hashes == source_hashes()
    report = {'success': result.wasSuccessful(), 'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
              'elapsed_seconds': time.monotonic()-start, 'source_sha256': hashes, 'cases': result.records}
    out = ROOT/'tests/persistence/evidence'
    out.mkdir(parents=True, exist_ok=True)
    (out/'contracts.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
