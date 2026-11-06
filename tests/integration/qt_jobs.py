"""Native worker cancellation, directory chooser, repeated imports and close-in-flight evidence."""
from pathlib import Path
import json
import sys
import time
import traceback
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from PySide6.QtCore import QEventLoop, QPoint, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from app.desktop.main import DesktopWindow
from scripts.integration.evidence import source_hashes

OUT = ROOT/'tests/integration/jobs'
OUT.mkdir(parents=True, exist_ok=True)
base = ROOT/'tests/fiscal/fixtures/p0_iva_ieps_40.xml'
large = OUT/'batch1000.zip'
with zipfile.ZipFile(large, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
    for i in range(1000):
        archive.writestr(f'synthetic-{i:04}.xml', base.read_bytes())
directory = OUT/'AAA010101AAA'
directory.mkdir(exist_ok=True)
(directory/'original.xml').write_bytes(base.read_bytes())
app = QApplication(sys.argv[:1])
app.setQuitOnLastWindowClosed(False)
window = DesktopWindow()
downloads = []
window.save_picker = lambda name: str(OUT/name)
window.profile.downloadRequested.connect(lambda request: downloads.append(request))
report = {'checks': [], 'dataset_size': 1000, 'source_sha256': source_hashes()}
ticks = []
timer = QTimer()
timer.timeout.connect(lambda: ticks.append(time.monotonic()))
timer.start(20)


def js(code):
    loop, result = QEventLoop(), []
    def done(value):
        result.append(value)
        loop.quit()
    window.web_page.runJavaScript(code, done)
    deadline = QTimer()
    deadline.setSingleShot(True)
    deadline.timeout.connect(loop.quit)
    deadline.start(10000)
    loop.exec()
    deadline.stop()
    if not result:
        raise RuntimeError('JS timeout')
    return result[0]


def wait(code, timeout=40):
    end = time.monotonic()+timeout
    while time.monotonic() < end:
        if js(code):
            return
        QTest.qWait(15)
    raise RuntimeError('Timed out: '+code)


def click(identity):
    js(f'document.getElementById({json.dumps(identity)}).click()')


def native_click(identity):
    js(f'document.getElementById({json.dumps(identity)}).scrollIntoView({{block:"center"}})')
    QTest.qWait(50)
    rect = json.loads(js(f'JSON.stringify((()=>{{var r=document.getElementById({json.dumps(identity)}).getBoundingClientRect();return {{x:r.x+r.width/2,y:r.y+r.height/2}}}})())'))
    QTest.mouseClick(window.view.focusProxy(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(round(rect['x']), round(rect['y'])))


def check(name, expected, actual):
    report['checks'].append({'id': name, 'expected': expected, 'actual': actual, 'result': 'PASS' if actual == expected else 'FAIL'})
    save()


def save():
    (OUT/'jobs.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


try:
    window.show()
    check('real-window', True, QTest.qWaitForWindowExposed(window, 10000))
    wait('!!window.FiscalOpsRuntime && !!window.FiscalOpsDesktop && !!document.querySelector("#s2.on")')
    modes = []
    def choose(mode, old_files, accepted):
        modes.append(str(mode))
        return [str(directory)]
    window.web_page.file_picker = choose
    native_click('folder')
    wait('document.getElementById("filelist").textContent.includes("original.xml")')
    check('directory-input-native-selection', True, bool(modes))
    check('directory-rfc-detected', 'AAA010101AAA', js('document.getElementById("rfc").value'))
    click('process')
    wait('FiscalOpsRuntime.state.documents===1 && !FiscalOpsRuntime.state.busy')
    previous = js('FiscalOpsRuntime.state.dataset_id')
    click('more')
    window.web_page.file_picker = lambda *args: [str(large)]
    native_click('select')
    wait('document.getElementById("filelist").textContent.includes("batch1000.zip")')
    before = len(ticks)
    click('process')
    wait('FiscalOpsRuntime.state.busy && FiscalOpsRuntime.state.progress && FiscalOpsRuntime.state.progress.documents>5')
    progress_before = json.loads(js('JSON.stringify({busy:FiscalOpsRuntime.state.busy,screen:document.querySelector("section.on").id,progress:FiscalOpsRuntime.state.progress})'))
    window.view.grab().save(str(OUT/'progress_before_cancel.png'))
    progress_after = json.loads(js('JSON.stringify({busy:FiscalOpsRuntime.state.busy,screen:document.querySelector("section.on").id,progress:FiscalOpsRuntime.state.progress})'))
    report['progress_capture'] = {'before': progress_before, 'after': progress_after,
                                  'accepted': progress_before['busy'] and progress_after['busy'] and progress_before['screen'] == progress_after['screen'] == 's2'}
    check('stable-processing-screen-captured', True, report['progress_capture']['accepted'])
    check('gui-heartbeat-during-zip', True, len(ticks)-before > 2)
    started = time.monotonic()
    click('clear')
    wait('!FiscalOpsRuntime.state.busy')
    report['cancellation_seconds'] = time.monotonic()-started
    check('cancel-keeps-previous-dataset', previous, js('FiscalOpsRuntime.state.dataset_id'))
    check('cancel-keeps-previous-documents', 1, js('FiscalOpsRuntime.state.documents'))
    check('cancel-status', True, js('document.getElementById("status").textContent.includes("cancelada")'))
    click('process')
    wait('FiscalOpsRuntime.state.busy')
    click('process')  # Disabled control / duplicate call must not start another job.
    wait('!FiscalOpsRuntime.state.busy && FiscalOpsRuntime.state.documents===1001', 120)
    check('retry-after-cancel-completes', 1001, js('FiscalOpsRuntime.state.documents'))
    check('retry-replaces-dataset', True, previous != js('FiscalOpsRuntime.state.dataset_id'))
    check('progress-completed', 100, js('document.getElementById("prog").value'))
    wait('FiscalOpsRuntime.state.totals==="ready"')
    check('worker-total-124124', True, js('document.getElementById("totalsBox").textContent.includes("$124,124.00")'))
    click('excel')
    wait('document.getElementById("exportModal").classList.contains("on")')
    click('exportGenerate')
    click('exportCancel')
    wait('!FiscalOpsRuntime.state.busy')
    check('export-cancel-no-artifact', True, js('FiscalOpsRuntime.state.last_export===null'))
    check('export-cancel-no-download-request', 0, len(downloads))
    click('more')
    click('process')
    wait('FiscalOpsRuntime.state.busy && FiscalOpsRuntime.state.progress && FiscalOpsRuntime.state.progress.documents>5')
    started = time.monotonic()
    window.close()
    end = time.monotonic()+15
    while time.monotonic() < end and not window._closed:
        QTest.qWait(20)
    report['close_seconds'] = time.monotonic()-started
    check('close-cancels-inflight-and-stops-thread', True, window._closed and not window.fiscal.thread.isRunning())
    check('close-callback-on-gui-thread', True, getattr(window, '_close_callback_thread', None) == window.fiscal.gui_thread_id)
    report['console'] = window.web_page.messages
    check('no-uncaught-javascript', False, any('Uncaught' in m['message'] for m in report['console']))
except Exception as exc:
    report['fatal'], report['traceback'] = str(exc), traceback.format_exc()
    report['state'] = js('JSON.stringify(FiscalOpsRuntime.state)')
    report['status'] = js('document.getElementById("status").textContent')
finally:
    if not window._closed:
        window.close()
        for _ in range(500):
            if window._closed:
                break
            QTest.qWait(20)
    timer.stop()
    report['closed'], report['worker_stopped'] = window._closed, not window.fiscal.thread.isRunning()
    save()
    print(json.dumps({k: v for k, v in report.items() if k not in ('checks', 'console', 'traceback')}, indent=2))
    print(json.dumps([c for c in report['checks'] if c['result'] != 'PASS'], indent=2))
    if report.get('traceback'):
        print(report['traceback'])
    if window.fiscal.thread.isRunning():
        window.fiscal.thread.wait(10000)

raise SystemExit(1 if report.get('fatal') or any(c['result'] != 'PASS' for c in report['checks']) else 0)
