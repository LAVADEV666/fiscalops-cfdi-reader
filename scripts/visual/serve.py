"""Serve only explicitly allowed FiscalOps visual-test resources on loopback."""
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, unquote
import argparse
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
NAME = 'FiscalOps_CFDI_READER_SSGT_V21_1_PRO.html'
EXPECTED = '33eeed2334a683b5360c2fc4f9cabc26885be66fef8714e4278f97235b8c373b'


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.headers.get('Host') not in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'):
            self.send_error(403, 'Loopback host required')
            return
        route = unquote(urlsplit(self.path).path)
        if route in ('/', '/prototype.html'):
            data, content_type = (ROOT / NAME).read_bytes(), 'text/html; charset=utf-8'
            if hashlib.sha256(data).hexdigest() != EXPECTED:
                self.send_error(409, 'Prototype hash changed')
                return
        elif route == '/health':
            data, content_type = json.dumps({'prototype_sha256': EXPECTED}).encode(), 'application/json'
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_args):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=0)
    args = parser.parse_args()
    original = (ROOT / NAME).read_bytes()
    assert hashlib.sha256(original).hexdigest() == EXPECTED, 'Original prototype changed'
    assert (ROOT / 'legacy' / NAME).read_bytes() == original, 'Legacy copy differs'
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    evidence = ROOT / 'tests/visual/evidence'
    evidence.mkdir(parents=True, exist_ok=True)
    info = {'host': '127.0.0.1', 'port': server.server_port,
            'url': f'http://127.0.0.1:{server.server_port}', 'prototype_sha256': EXPECTED}
    (evidence / 'server.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
    print(json.dumps(info), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
