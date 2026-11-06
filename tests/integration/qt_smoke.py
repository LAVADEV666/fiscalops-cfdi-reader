"""Native Windows QWebChannel/worker end-to-end test. Uses synthetic files only."""
from pathlib import Path
import json
import sys
import time
import traceback
from lxml import etree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from PySide6.QtCore import QEventLoop, QPoint, Qt, QTimer, qVersion
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from app.desktop.main import DesktopWindow
from scripts.integration.evidence import source_hashes
from PySide6.QtWebEngineCore import QWebEngineDownloadRequest

OUT = ROOT/'tests/integration/qt'
OUT.mkdir(parents=True, exist_ok=True)
report = {'checks': [], 'qt': qVersion(), 'captures': [], 'source_sha256': source_hashes()}
app = QApplication(sys.argv[:1])
app.setQuitOnLastWindowClosed(False)
window = DesktopWindow(database_path=':memory:')
page = window.web_page
downloads = []
window.save_picker = lambda name: str(OUT/name)
window.profile.downloadRequested.connect(lambda request: downloads.append(request))
ticks = []
heartbeat = QTimer()
heartbeat.timeout.connect(lambda: ticks.append(time.monotonic()))
heartbeat.start(20)


def js(source):
    result, loop = [], QEventLoop()
    def done(value):
        result.append(value)
        loop.quit()
    page.runJavaScript(source, done)
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    timer.start(10000)
    loop.exec()
    timer.stop()
    if not result:
        raise RuntimeError('JS callback timeout')
    return result[0]


def wait(expression, timeout=40):
    end = time.monotonic()+timeout
    while time.monotonic() < end:
        if js(expression):
            return
        QTest.qWait(30)
    raise RuntimeError('Timed out: '+expression)


def save():
    (OUT/'smoke.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


def check(identity, expected, actual):
    report['checks'].append({'id': identity, 'expected': expected, 'actual': actual, 'result': 'PASS' if actual == expected else 'FAIL'})
    save()


def click(identity):
    js(f'document.getElementById({json.dumps(identity)}).click()')


def native_click(identity):
    js(f'document.getElementById({json.dumps(identity)}).scrollIntoView({{block:"center"}})')
    QTest.qWait(60)
    position = json.loads(js(f'JSON.stringify((()=>{{var r=document.getElementById({json.dumps(identity)}).getBoundingClientRect();return {{x:r.x+r.width/2,y:r.y+r.height/2}}}})())'))
    QTest.mouseClick(window.view.focusProxy(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(round(position['x']), round(position['y'])))


def choose(names):
    directory = OUT/'fixtures'
    directory.mkdir(exist_ok=True)
    paths = []
    for index, name in enumerate(names):
        root = etree.fromstring((ROOT/'tests/fiscal/fixtures'/name).read_bytes())
        root.set('Folio', 'CASE-'+str(index))
        path = directory/name
        path.write_bytes(etree.tostring(root, encoding='UTF-8', xml_declaration=True))
        paths.append(str(path))
    window.web_page.file_picker = lambda *args: paths
    native_click('select')
    wait('document.getElementById("filelist").textContent.includes('+json.dumps(names[-1])+')')


try:
    window.show()
    check('native-window-exposed', True, QTest.qWaitForWindowExposed(window, 10000))
    report['platform'] = QGuiApplication.platformName()
    report['native_win_id'] = int(window.winId())
    report['screen'] = {'logical_dpi': window.screen().logicalDotsPerInch(), 'device_pixel_ratio': window.screen().devicePixelRatio(),
                        'geometry': [window.screen().geometry().width(), window.screen().geometry().height()]}
    check('windows-platform', 'windows', report['platform'])
    wait('!!window.FiscalOpsRuntime && !!window.FiscalOpsDesktop && !!document.querySelector("#s2.on")')
    js('FiscalOpsDesktop.ready.then(value=>window.__info=value)')
    wait('!!window.__info')
    check('native-engine-advertised', 'python-decimal-worker', js('window.__info.fiscal_engine'))
    check('runtime-native-mode', 'decimal-worker', js('FiscalOpsRuntime.state.mode'))
    choose(['p0_iva_ieps_40.xml', 'p0_local_once_40.xml', 'p0_isr_retention_40.xml'])
    before_ticks = len(ticks)
    native_click('process')
    wait('FiscalOpsRuntime.state.documents===3 && !FiscalOpsRuntime.state.busy && !!document.querySelector("#s3.on")')
    wait('FiscalOpsRuntime.state.totals==="ready"')
    check('three-documents', 3, js('FiscalOpsRuntime.state.documents'))
    check('native-import-off-gui-thread', True, bool(window.fiscal.worker.thread_ids) and window.fiscal.gui_thread_id not in window.fiscal.worker.thread_ids)
    check('gui-heartbeat-during-import', True, len(ticks)-before_ticks > 2)
    check('iva-not-federal-aggregate', '$16.00', js('document.querySelector("#tbody tr td[data-col=IVA]").textContent.trim()'))
    check('decimal-total-333', True, js('document.getElementById("totalsBox").textContent.includes("$333.00")'))
    check('decimal-iva-32', True, js('document.getElementById("totalsBox").textContent.includes("$32.00")'))
    js('document.querySelector("#tbody tr[data-i]").click()')
    check('visor-five-tabs', 5, js('document.querySelectorAll("#previewBody .pv-tab").length'))
    check('visor-iva-correct', True, js('document.querySelector("#previewBody .preview-kpis").textContent.includes("$16.00")'))
    for tab in ('resumen', 'impuestos', 'conceptos', 'datos', 'xml'):
        js('document.querySelector('+json.dumps('#previewBody [data-pv='+tab+']')+').click()')
        check('visor-tab-'+tab, True, js('document.querySelector('+json.dumps('#previewBody [data-pane='+tab+']')+').classList.contains("on")'))
    click('previewClose')
    for width, height in ((1366, 768), (1600, 900), (1920, 1080)):
        window.setMinimumSize(width, height)
        window.resize(width, height)
        QTest.qWait(250)
        file = OUT/f'report_{width}x{height}.png'
        window.view.grab().save(str(file))
        report['captures'].append(str(file.relative_to(ROOT)))
        check('viewport-'+str(width), f'{width}x{height}', js('innerWidth+"x"+innerHeight'))
    window.setMinimumSize(0, 0)
    window.resize(1366, 768)
    QTest.qWait(350)
    native_click('editcols')
    wait('document.getElementById("modal").classList.contains("on")')
    check('editor-focus', 'colSearch', js('document.activeElement.id'))
    QTest.keyClick(window.view.focusProxy(), Qt.Key.Key_Escape)
    wait('!document.getElementById("modal").classList.contains("on")')
    check('editor-escape-closes', False, js('document.getElementById("modal").classList.contains("on")'))
    check('editor-restores-invoker', 'editcols', js('document.activeElement.id'))
    native_click('excel')
    wait('document.getElementById("exportModal").classList.contains("on")')
    js('document.querySelectorAll("#analysisChoices input").forEach(input=>{input.checked=true;input.dispatchEvent(new Event("change"))})')
    check('analysis-seven-selected', 7, js('document.querySelectorAll("#analysisChoices input:checked").length'))
    report['selected_analysis_ids'] = json.loads(js('JSON.stringify(Array.from(document.querySelectorAll("#analysisChoices input:checked")).map(input=>input.getAttribute("data-analysis")))'))
    native_click('exportGenerate')
    wait('!FiscalOpsRuntime.state.busy && !!FiscalOpsRuntime.state.last_export')
    end = time.monotonic()+20
    while time.monotonic() < end and (not downloads or not downloads[-1].isFinished()):
        QTest.qWait(30)
    check('xlsx-eight-sheets', 8, js('FiscalOpsRuntime.state.last_export.sheets'))
    check('xlsx-three-rows', 3, js('FiscalOpsRuntime.state.last_export.rows'))
    check('xlsx-saved-through-native-dialog', True, (OUT/'FiscalOps_summary.xlsx').exists())
    check('xlsx-download-completed', QWebEngineDownloadRequest.DownloadState.DownloadCompleted.name, downloads[-1].state().name)
    native_click('csv')
    wait('!FiscalOpsRuntime.state.busy && FiscalOpsRuntime.state.last_export.format==="csv"')
    native_click('txt')
    wait('!FiscalOpsRuntime.state.busy && FiscalOpsRuntime.state.last_export.format==="txt"')
    end = time.monotonic()+20
    while time.monotonic() < end and (len(downloads) < 3 or any(not request.isFinished() for request in downloads)):
        QTest.qWait(30)
    check('all-downloads-completed', True, len(downloads) == 3 and all(request.state() == QWebEngineDownloadRequest.DownloadState.DownloadCompleted for request in downloads))
    report['download_files'] = [str(Path(request.downloadDirectory())/request.downloadFileName()) for request in downloads]
    js('document.getElementById("q").value="CASE-1";document.getElementById("q").dispatchEvent(new Event("input"))')
    wait('document.querySelectorAll("#tbody tr[data-i]").length===1 && FiscalOpsRuntime.state.totals==="ready"')
    check('filter-one-document', True, js('document.getElementById("totalsBox").textContent.includes("$119.00")'))
    window.save_picker = lambda name: str(OUT/('filtered_'+name))
    native_click('csv')
    wait('!FiscalOpsRuntime.state.busy && FiscalOpsRuntime.state.last_export.rows===1')
    end = time.monotonic()+20
    while time.monotonic() < end and (len(downloads) < 4 or not downloads[-1].isFinished()):
        QTest.qWait(30)
    check('filtered-export-one-row', 1, js('FiscalOpsRuntime.state.last_export.rows'))
    check('filtered-download-completed', QWebEngineDownloadRequest.DownloadState.DownloadCompleted.name, downloads[-1].state().name)
    report['filtered_download_file'] = str(OUT/'filtered_FiscalOps_summary.csv')
    report['gui_thread_id'] = window.fiscal.gui_thread_id
    report['worker_thread_ids'] = sorted(window.fiscal.worker.thread_ids)
    report['console'] = window.web_page.messages
    check('no-uncaught-javascript', False, any('Uncaught' in item['message'] for item in report['console']))
except Exception as exc:
    report['fatal'] = str(exc)
    report['traceback'] = traceback.format_exc()
    report['failure_state'] = js('JSON.stringify({state:window.FiscalOpsRuntime&&FiscalOpsRuntime.state,status:document.getElementById("status").textContent,files:document.getElementById("filelist").textContent,processDisabled:document.getElementById("process").disabled})')
    report['console'] = window.web_page.messages
    report['pending'] = list(window.fiscal.pending)
    report['worker_thread_ids'] = sorted(window.fiscal.worker.thread_ids)
finally:
    window.close()
    end = time.monotonic()+15
    while time.monotonic() < end and not window._closed:
        QTest.qWait(30)
    report['closed'] = window._closed
    report['worker_stopped'] = not window.fiscal.thread.isRunning()
    check('close-callback-on-gui-thread', True, getattr(window, '_close_callback_thread', None) == window.fiscal.gui_thread_id)
    heartbeat.stop()
    save()
    print(json.dumps({k: v for k, v in report.items() if k not in ('traceback', 'console', 'checks')}, indent=2))
    print(json.dumps([c for c in report['checks'] if c['result'] != 'PASS'], indent=2))
    if report.get('traceback'):
        print(report['traceback'])
    if window.fiscal.thread.isRunning():
        window.fiscal.thread.wait(10000)

raise SystemExit(1 if report.get('fatal') or any(c['result'] != 'PASS' for c in report['checks']) or not report['worker_stopped'] else 0)
