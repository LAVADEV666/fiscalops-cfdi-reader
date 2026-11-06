"""Local-only server integration tests; no external network access."""
from pathlib import Path
import hashlib
import importlib.util
import json
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

MODULE = Path(__file__).with_name('serve.py')
spec = importlib.util.spec_from_file_location('visual_server', MODULE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), module.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def get(self, path, host=None):
        connection = HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        connection.request('GET', path, headers={'Host': host or f'127.0.0.1:{self.server.server_port}'})
        response = connection.getresponse()
        status, body = response.status, response.read()
        connection.close()
        return status, body

    def test_original_bytes(self):
        status, body = self.get('/')
        self.assertEqual(status, 200)
        self.assertEqual(hashlib.sha256(body).hexdigest(), module.EXPECTED)

    def test_health(self):
        status, body = self.get('/health')
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['prototype_sha256'], module.EXPECTED)

    def test_no_directory_listing(self):
        self.assertEqual(self.get('/docs/')[0], 404)

    def test_no_path_traversal(self):
        self.assertEqual(self.get('/%2e%2e/README.md')[0], 404)

    def test_no_arbitrary_project_files(self):
        self.assertEqual(self.get('/.git/config')[0], 404)

    def test_host_is_loopback(self):
        self.assertEqual(self.get('/', host='untrusted.example')[0], 403)


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ServerTest))
    evidence = module.ROOT / 'tests/visual/evidence/server-tests.json'
    evidence.write_text(json.dumps({'tests': result.testsRun, 'failures': len(result.failures),
                                    'errors': len(result.errors), 'successful': result.wasSuccessful()}, indent=2), encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
