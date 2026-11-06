"""Read-only loopback server for the development copy and frozen reference."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import argparse
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = '33eeed2334a683b5360c2fc4f9cabc26885be66fef8714e4278f97235b8c373b'
ORIGINAL = ROOT / 'FiscalOps_CFDI_READER_SSGT_V21_1_PRO.html'
RESOURCES = {'/': ('index.html','text/html'), '/index.html': ('index.html','text/html'),
             '/legacy-runtime.js': ('legacy-runtime.js','text/javascript'),
             '/v20-runtime.js': ('v20-runtime.js','text/javascript'),
             '/desktop-bridge.js': ('desktop-bridge.js','text/javascript')}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.headers.get('Host') != f'127.0.0.1:{self.server.server_port}':
            self.send_error(403)
            return
        route = urlsplit(self.path).path
        if route in ('/reference/', '/reference/index.html'):
            data, mime = ORIGINAL.read_bytes(), 'text/html'
            if hashlib.sha256(data).hexdigest() != EXPECTED:
                self.send_error(409)
                return
        elif route in RESOURCES:
            name, mime = RESOURCES[route]
            data = (ROOT/'app/ui'/name).read_bytes()
        elif route == '/favicon.ico':
            self.send_response(204)
            self.end_headers()
            return
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', mime+'; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_args):
        pass


def create_server(port=0):
    assert hashlib.sha256(ORIGINAL.read_bytes()).hexdigest() == EXPECTED
    assert (ROOT/'legacy'/ORIGINAL.name).read_bytes() == ORIGINAL.read_bytes()
    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=0)
    args = parser.parse_args()
    server = create_server(args.port)
    info = {'url':f'http://127.0.0.1:{server.server_port}', 'reference':f'http://127.0.0.1:{server.server_port}/reference/'}
    (ROOT/'tests/spec011/evidence/server.json').write_text(json.dumps(info),encoding='utf-8')
    print(json.dumps(info),flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
