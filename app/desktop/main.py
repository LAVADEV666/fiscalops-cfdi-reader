"""Windows QtWebEngine container for the SPEC011 development frontend."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

from PySide6.QtCore import QFile, QIODevice, QObject, QUrl, Slot
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineScript, QWebEngineUrlRequestInterceptor
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
from app.resources import ROOT, ORIGINAL, EXPECTED, UI

ALLOWED_FILES = {ORIGINAL.resolve(), *(p.resolve() for p in UI.glob('*.js')), (UI/'index.html').resolve()}


def local_resource_allowed(url):
    if url.scheme() in ('data','qrc','blob'):
        return True
    return url.scheme() == 'file' and Path(url.toLocalFile()).resolve() in ALLOWED_FILES


class Diagnostics(QObject):
    """No filesystem, SQL or fiscal capabilities exposed to the page."""
    @Slot(result=str)
    def describe(self):
        return json.dumps({'protocol':'fiscalops.desktop/1', 'capabilities':['diagnostics.describe','diagnostics.ping'],
                           'fiscal_engine':'legacy-javascript-unchanged', 'filesystem':'legacy-browser-flow'})

    @Slot(str, result=str)
    def ping(self, request_id):
        return json.dumps({'request_id':request_id[:128], 'ok':True})


class LocalRequests(QWebEngineUrlRequestInterceptor):
    def __init__(self, parent):
        super().__init__(parent)
        self.requests = []

    def interceptRequest(self, info):
        url = info.requestUrl()
        allowed = local_resource_allowed(url)
        # Avoid retaining imported data URIs or personal content in diagnostics.
        self.requests.append({'scheme':url.scheme(), 'resource':url.fileName() if url.scheme()=='file' else '(embedded or blocked)', 'allowed':allowed})
        if not allowed:
            info.block(True)


class LocalPage(QWebEnginePage):
    def __init__(self, profile, parent):
        super().__init__(profile, parent)
        self.messages = []
        self.file_picker = None  # Injectable only from Python QA; never exposed over QWebChannel.

    def chooseFiles(self, mode, old_files, accepted_mime_types):
        if self.file_picker is not None:
            return self.file_picker(mode, old_files, accepted_mime_types)
        return super().chooseFiles(mode, old_files, accepted_mime_types)

    def acceptNavigationRequest(self, target, navigation_type, main_frame):
        return target.scheme()=='file' and Path(target.toLocalFile()).resolve() in {ORIGINAL.resolve(),(UI/'index.html').resolve()}

    def javaScriptConsoleMessage(self, level, message, line, source):
        self.messages.append({'level':str(level), 'message':message, 'line':line})


class DesktopWindow(QMainWindow):
    def __init__(self, width=1366, height=768, reference=False):
        super().__init__()
        assert hashlib.sha256(ORIGINAL.read_bytes()).hexdigest()==EXPECTED
        assert (ROOT/'legacy'/ORIGINAL.name).read_bytes()==ORIGINAL.read_bytes()
        self.setWindowTitle('FiscalOps CFDI Reader V21.1')
        self.frontend_url=QUrl.fromLocalFile(str(UI/'index.html'))
        self.reference_url=QUrl.fromLocalFile(str(ORIGINAL))
        self.view = QWebEngineView(self)
        self.profile = QWebEngineProfile(self.view)  # off-the-record; not a personal browser profile
        self.interceptor = LocalRequests(self.profile)
        self.profile.setUrlRequestInterceptor(self.interceptor)
        self.web_page = LocalPage(self.profile, self.view)
        self.view.setPage(self.web_page)
        self.channel = QWebChannel(self.web_page)
        self.diagnostics = Diagnostics(self.channel)
        self.channel.registerObject('desktop', self.diagnostics)
        self.web_page.setWebChannel(self.channel)
        library = QFile(':/qtwebchannel/qwebchannel.js')
        if not library.open(QIODevice.OpenModeFlag.ReadOnly):
            raise RuntimeError('Qt WebChannel JavaScript resource unavailable')
        source = bytes(library.readAll()).decode('utf-8')
        library.close()
        script = QWebEngineScript()
        script.setName('fiscalops-diagnostic-channel')
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        script.setRunsOnSubFrames(False)
        script.setSourceCode(source)
        self.web_page.scripts().insert(script)
        self.setCentralWidget(self.view)
        self.resize(width,height)
        self._closed = False
        self.view.load(self.reference_url if reference else self.frontend_url)

    def closeEvent(self, event):
        self.view.stop()
        self._closed = True
        super().closeEvent(event)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--width',type=int,default=1366)
    parser.add_argument('--height',type=int,default=768)
    args=parser.parse_args()
    app=QApplication(sys.argv[:1])
    app.setApplicationName('FiscalOps CFDI Reader')
    window=DesktopWindow(args.width,args.height)
    window.show()
    return app.exec()


if __name__=='__main__':
    raise SystemExit(main())
