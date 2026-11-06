"""Native report/import/export contract tests with retained machine-readable results."""
import importlib.util
import json
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.integration.evidence import source_hashes


def main():
    spec = importlib.util.spec_from_file_location('fiscal_test_records', ROOT/'scripts/fiscal/run_tests.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    suite = unittest.defaultTestLoader.discover(str(ROOT/'tests/integration'), pattern='test_*.py')
    hashes = source_hashes()
    started = time.monotonic()
    result = unittest.TextTestRunner(verbosity=1, resultclass=module.RecordedResult).run(suite)
    assert hashes == source_hashes(), 'Application sources changed during tests'
    report = {'success': result.wasSuccessful(), 'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
              'elapsed_seconds': time.monotonic()-started, 'source_sha256': hashes, 'cases': result.records}
    (ROOT/'tests/integration/evidence/contracts.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
