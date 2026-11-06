"""Windows QtWebEngine container for the SPEC011 development frontend."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import threading

from PySide6.QtCore import QFile, QIODevice, QObject, QUrl, Slot, Qt
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineScript, QWebEngineUrlRequestInterceptor, QWebEngineDownloadRequest
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
from app.resources import ROOT, ORIGINAL, EXPECTED, UI
from app.desktop.fiscal_worker import FiscalBridge
from PySide6.QtWidgets import QFileDialog

ALLOWED_FILES = {ORIGINAL.resolve(), *(p.resolve() for p in UI.glob('*.js')), (UI/'index.html').resolve()}


def local_resource_allowed(url):
    if url.scheme() in ('data','qrc','blob'):
        return True
    return url.scheme() == 'file' and Path(url.toLocalFile()).resolve() in ALLOWED_FILES


class Diagnostics(QObject):
    """Diagnostics only; the separate fiscal object accepts selected bytes, never paths."""
    @Slot(result=str)
    def describe(self):
        return json.dumps({'protocol':'fiscalops.desktop/2', 'capabilities':['diagnostics.describe','diagnostics.ping','fiscal.worker','fiscal.import','fiscal.export','fiscal.cancel'],
                           'fiscal_engine':'python-decimal-worker', 'filesystem':'user-selected browser bytes; native save dialog'})

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
        self.fiscal = FiscalBridge(self.channel)
        self.channel.registerObject('fiscal', self.fiscal)
        self.fiscal.thread.finished.connect(self._worker_stopped, Qt.ConnectionType.QueuedConnection)
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
        self._closing = False
        self.save_picker = None  # Python-only test hook; no path is accepted from JavaScript.
        self.active_downloads = set()
        self.profile.downloadRequested.connect(self._download_requested)
        self.view.load(self.reference_url if reference else self.frontend_url)

    def closeEvent(self, event):
        if self.active_downloads:
            event.ignore()
            self._closing = True
            self.setEnabled(False)
            return
        if self.fiscal.thread.isRunning():
            event.ignore()
            self._closing = True
            self.setEnabled(False)
            self.view.stop()
            self.fiscal.shutdown()
            return
        self.view.stop()
        self._closed = True
        super().closeEvent(event)

    @Slot()
    def _worker_stopped(self):
        self._close_callback_thread = threading.get_ident()
        if self._closing:
            self.close()

    def _download_requested(self, request):
        suggested = Path(request.suggestedFileName()).name
        target = self.save_picker(suggested) if self.save_picker else QFileDialog.getSaveFileName(self, 'Guardar exportación FiscalOps', suggested)[0]
        if not target:
            request.cancel()
            self.fiscal.downloadStatus.emit('cancelled')
            return
        path = Path(target)
        request.setDownloadDirectory(str(path.parent))
        request.setDownloadFileName(path.name)
        self.active_downloads.add(request)
        request.isFinishedChanged.connect(lambda: self._download_finished(request))
        request.accept()

    def _download_finished(self, request):
        if not request.isFinished():
            return
        self.active_downloads.discard(request)
        state = 'saved' if request.state() == QWebEngineDownloadRequest.DownloadState.DownloadCompleted else 'failed'
        self.fiscal.downloadStatus.emit(state)
        if self._closing and not self.active_downloads:
            self.close()


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
