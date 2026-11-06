"""Standard-library test runner with machine-readable cases and nonzero failure status."""
import json
import hashlib
import argparse
from pathlib import Path
import platform
import sys
import time
import unittest
from xml.parsers import expat
from lxml import etree

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'tests/fiscal')]


class RecordedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.records.append({'id': test.id(), 'status': 'pass'})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.records.append({'id': test.id(), 'status': 'fail', 'error': self._exc_info_to_string(err, test)})

    def addError(self, test, err):
        super().addError(test, err)
        self.records.append({'id': test.id(), 'status': 'error', 'error': self._exc_info_to_string(err, test)})

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        self.records.append({'id': subtest.id(), 'status': 'pass' if err is None else 'fail',
                             **({'error': self._exc_info_to_string(err, subtest)} if err else {})})


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='tests/fiscal/evidence/tests.json')
    args=parser.parse_args()
    suite = unittest.defaultTestLoader.discover(str(ROOT/'tests/fiscal'), pattern='test_*.py')
    started = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2, resultclass=RecordedResult).run(suite)
    bound = sorted((ROOT/'app/fiscal').glob('*.py')) + sorted((ROOT/'tests/fiscal').glob('*.py'))
    evidence = {'scope': 'synthetic normative/security tests; not SAT certification',
                'source_sha256': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in bound},
                'python': platform.python_version(), 'platform': platform.platform(),
                'lxml': etree.LXML_VERSION, 'libxml2': etree.LIBXML_VERSION, 'expat': expat.EXPAT_VERSION,
                'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
                'success': result.wasSuccessful(), 'elapsed_seconds': time.perf_counter()-started, 'cases': result.records}
    destination=(ROOT/args.output).resolve()
    if not destination.is_relative_to(ROOT):
        raise ValueError('Test evidence outside workspace')
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
