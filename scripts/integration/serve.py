"""QA-only loopback server; never starts from the desktop application."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.spec011.serve import create_server
from scripts.spec011.serve import Handler
from urllib.parse import urlsplit


class QAHandler(Handler):
    def do_GET(self):
        route = urlsplit(self.path).path
        if self.headers.get('Host') != f'127.0.0.1:{self.server.server_port}':
            self.send_error(403)
            return
        if route in ('/', '/index.html'):
            data = (ROOT/'app/ui/index.html').read_bytes().replace(b'<script src="legacy-runtime.js">', b'<script>window.FiscalOpsVisualReference=true;</script><script src="legacy-runtime.js">')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(data)
            return
        if route.startswith('/without-native/'):
            self.path = self.path.replace('/without-native/', '/', 1)
            if self.path in ('/', '/index.html'):
                data = (ROOT/'app/ui/index.html').read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
        super().do_GET()

server = create_server()
server.RequestHandlerClass = QAHandler
info = {'url': f'http://127.0.0.1:{server.server_port}', 'purpose': 'browser UI reference QA only; explicitly enables the frozen legacy visual path. /without-native/ tests fail-closed production HTML.'}
(ROOT/'tests/integration/evidence/server.json').write_text(json.dumps(info), encoding='utf-8')
print(json.dumps(info), flush=True)
try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    server.server_close()
