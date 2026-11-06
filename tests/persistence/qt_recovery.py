"""Actual Windows Qt process restart, persisted view and native exports (synthetic data)."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import traceback
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.integration.evidence import source_hashes

parser = argparse.ArgumentParser()
parser.add_argument('--phase', choices=('seed', 'recover', 'empty'))
parser.add_argument('--database')
args = parser.parse_args()
OUT = ROOT/'tests/persistence/qt'
OUT.mkdir(parents=True, exist_ok=True)
if not args.phase:
    work = ROOT/'tests/persistence/.work'
    work.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=work) as directory:
        database = Path(directory)/'fiscalops.sqlite3'
        for phase in ('seed', 'recover', 'empty'):
            result = subprocess.run([sys.executable, __file__, '--phase', phase, '--database', str(database)], cwd=ROOT, capture_output=True, text=True, timeout=120)
            if result.returncode:
                print(result.stdout, result.stderr)
                raise SystemExit(result.returncode)
        reports = [json.loads((OUT/f'{p}.json').read_text(encoding='utf-8')) for p in ('seed', 'recover', 'empty')]
        assert all(r['source_sha256'] == source_hashes() for r in reports)
        with sqlite3.connect(database) as db:
            assert db.execute('PRAGMA integrity_check').fetchone() == ('ok',)
            assert db.execute('SELECT active_session FROM workspace').fetchone() == (None,)
            assert db.execute('SELECT count(*) FROM sessions').fetchone() == (1,)
            assert db.execute('SELECT count(*) FROM fiscal_results').fetchone() == (3,)
        db.close()
        assert reports[0]['close_save_result']['ok'], reports[0]['close_save_result']
        with (OUT/'FiscalOps_summary.csv').open(encoding='utf-8-sig', newline='') as stream:
            rows = list(csv.DictReader(stream))
        assert len(rows) == 1 and rows[0]['Total'] == '119' and rows[0]['IVA trasladado'] == '16'
        with zipfile.ZipFile(OUT/'FiscalOps_summary.xlsx') as archive:
            assert archive.testzip() is None
            assert len([n for n in archive.namelist() if n.startswith('xl/worksheets/')]) == 8
            assert b'<v>119</v>' in archive.read('xl/worksheets/sheet1.xml')
        assert len((OUT/'FiscalOps_summary.txt').read_text(encoding='utf-8-sig').splitlines()) == 2
        report = {'success': True, 'source_sha256': source_hashes(), 'separate_processes': 3,
                  'checks': sum(len(r['checks']) for r in reports), 'phases': reports,
                  'exported_csv_total': '119', 'xlsx_sheets': 8, 'clear_keeps_history': True,
                  'originals_and_results_durable': True,
                  'exports_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.glob('FiscalOps_summary.*')}}
        (OUT/'recovery.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
        print(json.dumps({k: v for k, v in report.items() if k not in ('source_sha256', 'phases')}, indent=2))
    raise SystemExit(0)

from lxml import etree
from PySide6.QtCore import QEventLoop, QPoint, Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineCore import QWebEngineDownloadRequest
from app.desktop.main import DesktopWindow

app = QApplication(sys.argv[:1])
app.setQuitOnLastWindowClosed(False)
window = DesktopWindow(database_path=args.database)
window.save_picker = lambda name: str(OUT/name)
downloads = []
window.profile.downloadRequested.connect(lambda item: downloads.append(item))
report = {'phase': args.phase, 'checks': [], 'source_sha256': source_hashes()}


def js(code):
    values, loop = [], QEventLoop()
    def done(value):
        values.append(value)
        loop.quit()
    window.web_page.runJavaScript(code, done)
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    timer.start(10000)
    loop.exec()
    timer.stop()
    if not values:
        raise RuntimeError('JS timeout')
    return values[0]


def wait(code):
    until = time.monotonic()+40
    while time.monotonic() < until:
        if js(code):
            return
        QTest.qWait(30)
    raise RuntimeError('Timeout: '+code)


def check(name, expected, actual):
    report['checks'].append({'id': name, 'expected': expected, 'actual': actual, 'result': 'PASS' if expected == actual else 'FAIL'})
    assert expected == actual, (name, expected, actual)


def click(identity):
    js(f'document.getElementById({json.dumps(identity)}).scrollIntoView({{block:"center"}})')
    QTest.qWait(60)
    p = json.loads(js(f'JSON.stringify((()=>{{var r=document.getElementById({json.dumps(identity)}).getBoundingClientRect();return {{x:r.x+r.width/2,y:r.y+r.height/2}}}})())'))
    QTest.mouseClick(window.view.focusProxy(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(round(p['x']), round(p['y'])))


try:
    window.show()
    check('native-window', True, QTest.qWaitForWindowExposed(window, 10000))
    check('windows', 'windows', QGuiApplication.platformName())
    wait('!!window.FiscalOpsRuntime && FiscalOpsRuntime.state.persistence==="ready" && !FiscalOpsRuntime.state.busy')
    if args.phase == 'seed':
        wait('document.getElementById("s2").classList.contains("on")')
        QTest.qWait(300)
        check('fresh-empty', 0, js('FiscalOpsRuntime.state.documents'))
        paths = []
        directory = OUT/'fixtures'
        directory.mkdir(exist_ok=True)
        for index, name in enumerate(('p0_iva_ieps_40.xml', 'p0_local_once_40.xml', 'p0_isr_retention_40.xml')):
            doc = etree.fromstring((ROOT/'tests/fiscal/fixtures'/name).read_bytes())
            doc.set('Folio', f'SQLITE-{index}')
            file = directory/name
            file.write_bytes(etree.tostring(doc, encoding='UTF-8', xml_declaration=True))
            paths.append(str(file))
        window.web_page.file_picker = lambda *a: paths
        click('select')
        wait('document.getElementById("filelist").textContent.includes("p0_isr_retention_40.xml")')
        click('process')
        wait('FiscalOpsRuntime.state.documents===3 && !FiscalOpsRuntime.state.busy')
        wait('FiscalOpsRuntime.state.totals==="ready"')
        check('total-333', True, js('document.getElementById("totalsBox").textContent.includes("$333.00")'))
        js('document.getElementById("q").value="SQLITE-1";document.getElementById("q").dispatchEvent(new Event("input",{bubbles:true}))')
        # Exercise report kind, profile and sort persistence through the existing controls.
        js('document.getElementById("profileSel").value="fiscal";document.getElementById("profileSel").dispatchEvent(new Event("change",{bubbles:true}))')
        wait('FiscalOpsRuntime.state.view_saved && document.querySelectorAll("#tbody tr[data-i]").length===1')
        check('filtered-total-119', True, js('document.getElementById("totalsBox").textContent.includes("$119.00")'))
        report['dataset_id'] = js('FiscalOpsRuntime.state.dataset_id')
        report['columns'] = json.loads(js('JSON.stringify(Array.from(document.querySelectorAll("#thead th")).map(x=>x.getAttribute("data-col")))'))
        check('nonempty-fiscal-columns', True, len(report['columns']) > 15)
        # Close immediately after an input change, before the 180ms autosave timer.
        js('document.getElementById("q").value="SQLITE-1 ";document.getElementById("q").dispatchEvent(new Event("input",{bubbles:true}))')
        (OUT/'expected.json').write_text(json.dumps({'dataset_id': report['dataset_id'], 'columns': report['columns']}), encoding='utf-8')
    elif args.phase == 'recover':
        expected = json.loads((OUT/'expected.json').read_text(encoding='utf-8'))
        check('dataset-id-recovered', expected['dataset_id'], js('FiscalOpsRuntime.state.dataset_id'))
        check('three-documents-recovered', 3, js('FiscalOpsRuntime.state.documents'))
        check('immediate-close-query-recovered', 'SQLITE-1 ', js('document.getElementById("q").value'))
        check('profile-recovered', 'fiscal', js('document.getElementById("profileSel").value'))
        check('columns-recovered', expected['columns'], json.loads(js('JSON.stringify(Array.from(document.querySelectorAll("#thead th")).map(x=>x.getAttribute("data-col")))')))
        wait('FiscalOpsRuntime.state.totals==="ready" && FiscalOpsRuntime.state.view_saved')
        check('recovered-total-119', True, js('document.getElementById("totalsBox").textContent.includes("$119.00")'))
        js('document.querySelector("#tbody tr[data-i]").click()')
        check('five-visor-tabs', 5, js('document.querySelectorAll("#previewBody .pv-tab").length'))
        check('preview-xml-kept', True, js('document.getElementById("previewBody").textContent.includes("SQLITE-1")'))
        click('previewClose')
        wait('document.getElementById("s3").classList.contains("on") && !document.getElementById("previewModal").classList.contains("on")')
        window.raise_()
        window.activateWindow()
        QTest.qWait(1100)  # Let the real close/open transitions paint before capturing.
        window.view.grab().save(str(OUT/'recovered_report.png'))
        for kind in ('csv', 'txt', 'xlsx'):
            if kind == 'xlsx':
                click('excel')
                wait('document.getElementById("exportModal").classList.contains("on")')
                js('document.querySelectorAll("#analysisChoices input").forEach(i=>{i.checked=true;i.dispatchEvent(new Event("change"))})')
                click('exportGenerate')
            else:
                click(kind)
            wait('!FiscalOpsRuntime.state.busy && FiscalOpsRuntime.state.last_export && FiscalOpsRuntime.state.last_export.format==='+json.dumps(kind))
            end = time.monotonic()+20
            while time.monotonic() < end and (not downloads or not downloads[-1].isFinished()):
                QTest.qWait(30)
            check(kind+'-download-completed', QWebEngineDownloadRequest.DownloadState.DownloadCompleted.name, downloads[-1].state().name)
            check(kind+'-one-selected-row', 1, js('FiscalOpsRuntime.state.last_export.rows'))
        click('more')
        click('clear')
        wait('!FiscalOpsRuntime.state.busy && FiscalOpsRuntime.state.dataset_id===null')
        check('clear-deactivates', 0, js('FiscalOpsRuntime.state.documents'))
    else:
        check('clear-remains-empty-after-restart', 0, js('FiscalOpsRuntime.state.documents'))
        check('clear-did-not-reopen-history', True, js('FiscalOpsRuntime.state.dataset_id===null'))
        wait('document.getElementById("s2").classList.contains("on")')
        check('upload-screen', True, js('document.getElementById("s2").classList.contains("on")'))
    check('sqlite-owned-by-worker', True, window.fiscal.worker.store.repository.owner_thread in window.fiscal.worker.thread_ids and window.fiscal.worker.store.repository.owner_thread != window.fiscal.gui_thread_id)
    check('no-javascript-errors', False, any('Uncaught' in m['message'] for m in window.web_page.messages))
except Exception as exc:
    report['fatal'], report['traceback'] = str(exc), traceback.format_exc()
    report['ui_state'] = js('JSON.stringify({state:window.FiscalOpsRuntime&&FiscalOpsRuntime.state,status:document.getElementById("status").textContent})')
finally:
    window.close()
    end = time.monotonic()+15
    while time.monotonic() < end and not window._closed:
        QTest.qWait(30)
    report['closed'] = window._closed and not window.fiscal.thread.isRunning()
    report['sqlite_closed_on_worker'] = window.fiscal.worker.store.repository.connection is None
    report['close_save_result'] = getattr(window.fiscal, 'close_save_result', None)
    report['console'] = window.web_page.messages
    (OUT/f'{args.phase}.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'source_sha256'}, indent=2))
    if window._closed:
        window.deleteLater()
        QTest.qWait(100)

raise SystemExit(1 if report.get('fatal') or not report['closed'] or not report['sqlite_closed_on_worker'] else 0)
