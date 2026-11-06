"""Minimal Qt container for the unchanged prototype. No new fiscal engine."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys
import threading
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit

from scripts.visual.serve import Handler, ROOT, NAME, EXPECTED


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='Report dependencies without starting GUI')
    parser.add_argument('--width', type=int, default=1366)
    parser.add_argument('--height', type=int, default=768)
    args = parser.parse_args()
    if hashlib.sha256((ROOT / NAME).read_bytes()).hexdigest() != EXPECTED:
        raise SystemExit('PROTOTYPE_HASH_MISMATCH')
    if (ROOT / 'legacy' / NAME).read_bytes() != (ROOT / NAME).read_bytes():
        raise SystemExit('LEGACY_MISMATCH')
    available = bool(importlib.util.find_spec('PySide6'))
    report = {'status': 'AVAILABLE' if available else 'BLOCKED_MISSING_PYSIDE6',
              'python': sys.version, 'prototype_sha256': EXPECTED,
              'engine': 'Legacy JavaScript only; no new fiscal bridge',
              'gui_executed': False, 'qt_webengine': False, 'qwebchannel': False,
              'sqlite_runtime': __import__('sqlite3').sqlite_version}
    if available:
        try:
            from PySide6 import __version__
            from PySide6.QtCore import QObject, QUrl, Slot
            from PySide6.QtWidgets import QApplication, QMainWindow
            from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineUrlRequestInterceptor
            from PySide6.QtWebEngineWidgets import QWebEngineView
            from PySide6.QtWebChannel import QWebChannel
            report.update(pyside6=__version__, qt_webengine=True, qwebchannel=True)
        except ImportError as error:
            report.update(status='BLOCKED_QT_COMPONENTS', error=str(error))
    evidence = ROOT / 'tests/visual/evidence'
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / 'desktop-check.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    if args.check or report['status'] != 'AVAILABLE':
        print(json.dumps(report, indent=2))
        return 0 if report['status'] == 'AVAILABLE' else 3

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    origin = f'http://127.0.0.1:{server.server_port}'

    class LocalRequests(QWebEngineUrlRequestInterceptor):
        def interceptRequest(self, request):
            request_url = request.requestUrl().toString()
            parsed = urlsplit(request_url)
            if parsed.scheme in ('data', 'qrc', 'blob'):
                return
            if f'{parsed.scheme}://{parsed.netloc}' != origin:
                request.block(True)

    class LocalPage(QWebEnginePage):
        def acceptNavigationRequest(self, target, navigation_type, is_main_frame):
            parsed = urlsplit(target.toString())
            return f'{parsed.scheme}://{parsed.netloc}' == origin

    class Diagnostics(QObject):
        @Slot(result=str)
        def ping(self):
            return 'FiscalOps desktop smoke; fiscal backend not connected'

    app = QApplication(sys.argv[:1])
    app.setApplicationName('FiscalOps Desktop Smoke')
    window = QMainWindow()
    window.setWindowTitle('FiscalOps V21.1 — contenedor de prueba')
    view = QWebEngineView(window)
    # Off-the-record profile: no client-browser history or credentials are read.
    profile = QWebEngineProfile(view)
    interceptor = LocalRequests(profile)
    profile.setUrlRequestInterceptor(interceptor)
    page = LocalPage(profile, view)
    view.setPage(page)
    channel = QWebChannel(page)
    diagnostics = Diagnostics(channel)
    channel.registerObject('diagnostics', diagnostics)
    page.setWebChannel(channel)
    # Bridge is registered only; original HTML does not load qwebchannel.js.
    # Handshake is intentionally NOT claimed as tested or connected to fiscal logic.
    window.setCentralWidget(view)
    window.resize(args.width, args.height)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    view.load(QUrl(origin))
    window.show()
    try:
        return app.exec()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    raise SystemExit(main())
