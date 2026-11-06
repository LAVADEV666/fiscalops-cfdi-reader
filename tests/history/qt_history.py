"""Real Windows Qt history selection, native backup/review/restore, exports and restart."""
import argparse
from contextlib import closing
import csv
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'tests/fiscal')]
from scripts.integration.evidence import source_hashes
from app.desktop.maintenance import validate, read_only, file_hash

parser = argparse.ArgumentParser()
parser.add_argument('--phase', choices=('main', 'restart'))
parser.add_argument('--database')
parser.add_argument('--backup')
parser.add_argument('--ids')
args = parser.parse_args()
OUT = ROOT/'tests/history/qt'
OUT.mkdir(parents=True, exist_ok=True)

if not args.phase:
    import base64
    from lxml import etree
    from fixtures import invoice
    from app.desktop.fiscal_worker import FiscalStore
    work = ROOT/'tests/history/.work'
    work.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=work) as temp:
        dbpath, backup = Path(temp)/'active.sqlite3', Path(temp)/'respaldo ÁRBOL.sqlite3'
        store, event = FiscalStore(dbpath), threading.Event()
        def call(op, payload=None):
            return store.handle(op, payload or {}, 'seed', event, lambda v: None)
        call('import.begin', {'rfc': 'AAA010101AAA'})
        for index, name in enumerate(('p0_iva_ieps_40.xml', 'p0_local_once_40.xml', 'p0_isr_retention_40.xml')):
            doc = etree.fromstring((ROOT/'tests/fiscal/fixtures'/name).read_bytes())
            doc.set('Folio', f'HISTORY-{index}')
            call('import.file', {'name': name, 'base64': base64.b64encode(etree.tostring(doc, encoding='UTF-8')).decode()})
        call('import.prepare')
        first = call('import.commit')['dataset_id']
        call('session.save', {'dataset_id': first, 'view': {'profile': 'fiscal', 'filters': {'q': 'HISTORY-1'}}})
        call('import.begin', {'rfc': 'AAA010101AAA'})
        call('import.file', {'name': 'second.xml', 'base64': base64.b64encode(invoice(total='999')).decode()})
        call('import.prepare')
        second = call('import.commit')['dataset_id']
        store.repository.close()
        ids = json.dumps({'first': first, 'second': second})
        reports = []
        for phase in ('main', 'restart'):
            result = subprocess.run([sys.executable, __file__, '--phase', phase, '--database', str(dbpath), '--backup', str(backup), '--ids', ids], cwd=ROOT, capture_output=True, text=True, timeout=150)
            if result.returncode:
                print(result.stdout, result.stderr)
                raise SystemExit(result.returncode)
            reports.append(json.loads((OUT/f'{phase}.json').read_text(encoding='utf-8')))
        for report in reports:
            assert report['source_sha256'] == source_hashes() and not report.get('fatal') and report['closed'] and report['sqlite_closed']
        with closing(read_only(dbpath)) as db:
            summary = validate(db, event)
        assert summary['active_session'] == first and summary['sessions'] == 2 and summary['documents'] == 4
        with closing(read_only(Path(reports[0]['recovery_path']))) as db:
            preventive = validate(db, event)
        assert preventive['active_session'] == second
        with (OUT/'FiscalOps_summary.csv').open(encoding='utf-8-sig', newline='') as stream:
            rows = list(csv.DictReader(stream))
        assert len(rows) == 1 and rows[0]['Total'] == '119' and rows[0]['IVA trasladado'] == '16'
        with zipfile.ZipFile(OUT/'FiscalOps_summary.xlsx') as archive:
            assert archive.testzip() is None
            assert len([n for n in archive.namelist() if n.startswith('xl/worksheets/')]) == 8
        report = {'success': True, 'source_sha256': source_hashes(), 'checks': sum(len(r['checks']) for r in reports), 'processes': 2,
                  'phases': reports, 'restored_summary': summary, 'preventive_summary': preventive,
                  'backup_sha256': file_hash(backup, event), 'selected_csv_total': '119', 'xlsx_sheets': 8}
        (OUT/'acceptance.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
        print(json.dumps({k: v for k, v in report.items() if k not in ('source_sha256', 'phases')}, indent=2))
    raise SystemExit(0)

from PySide6.QtCore import QEventLoop, QPoint, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineCore import QWebEngineDownloadRequest
from app.desktop.main import DesktopWindow

ids = json.loads(args.ids)
backup = Path(args.backup)
app = QApplication(sys.argv[:1])
app.setQuitOnLastWindowClosed(False)
window = DesktopWindow(database_path=args.database)
window.save_picker = lambda name: str(OUT/name)
downloads, web_responses = [], []
window.profile.downloadRequested.connect(lambda value: downloads.append(value))
window.fiscal.response.connect(lambda value: web_responses.append(value))
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
        raise RuntimeError('JS callback timeout')
    return values[0]


def wait(condition):
    end = time.monotonic()+45
    while time.monotonic() < end:
        if condition() if callable(condition) else js(condition):
            return
        QTest.qWait(30)
    raise RuntimeError('Timeout: '+str(condition))


def check(name, expected, actual):
    report['checks'].append({'id': name, 'expected': expected, 'actual': actual, 'result': 'PASS' if expected == actual else 'FAIL'})
    assert expected == actual, (name, expected, actual)


def web_click(identity):
    js(f'document.getElementById({json.dumps(identity)}).scrollIntoView({{block:"center"}})')
    QTest.qWait(80)
    p = json.loads(js(f'JSON.stringify((()=>{{var r=document.getElementById({json.dumps(identity)}).getBoundingClientRect();return {{x:r.x+r.width/2,y:r.y+r.height/2}}}})())'))
    QTest.mouseClick(window.view.focusProxy(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(round(p['x']), round(p['y'])))


def manager():
    QTest.mouseClick(window.data_button, Qt.MouseButton.LeftButton)
    wait(lambda: window.data_dialog is not None and window.data_dialog.request_id is None and window.data_dialog.table.rowCount() == 2)
    return window.data_dialog


def open_session(identity):
    dialog = manager()
    index = next(i for i, r in enumerate(dialog.rows) if r['dataset_id'] == identity)
    dialog.table.selectRow(index)
    QTest.mouseClick(dialog.open, Qt.MouseButton.LeftButton)
    wait(lambda: window.data_dialog is None)
    wait('!!window.FiscalOpsRuntime && FiscalOpsRuntime.state.persistence==="ready" && !FiscalOpsRuntime.state.busy && FiscalOpsRuntime.state.dataset_id==='+json.dumps(identity))
    wait('FiscalOpsRuntime.state.totals==="ready"')


try:
    window.show()
    check('real-native-window', True, QTest.qWaitForWindowExposed(window, 10000))
    wait('!!window.FiscalOpsRuntime && FiscalOpsRuntime.state.persistence==="ready" && !FiscalOpsRuntime.state.busy')
    wait('FiscalOpsRuntime.state.totals==="ready"')
    if args.phase == 'main':
        check('initial-session-second', ids['second'], js('FiscalOpsRuntime.state.dataset_id'))
        check('viewport-unchanged', '1366x768', js('innerWidth+"x"+innerHeight'))
        dialog = manager()
        check('history-two-sessions', 2, len(dialog.rows))
        check('main-view-disabled-during-maintenance', False, window.view.isEnabled())
        dialog.search.setText(ids['first'])
        wait(lambda: dialog.request_id is None and len(dialog.rows) == 1)
        check('history-search-exact-id', ids['first'], dialog.rows[0]['dataset_id'])
        dialog.search.clear()
        wait(lambda: dialog.request_id is None and len(dialog.rows) == 2)
        QTest.qWait(250)
        dialog.grab().save(str(OUT/'history.png'))
        QTest.mouseClick(dialog.done, Qt.MouseButton.LeftButton)
        wait(lambda: window.data_dialog is None)
        open_session(ids['first'])
        check('historical-query-restored', 'HISTORY-1', js('document.getElementById("q").value'))
        check('historical-profile-restored', 'fiscal', js('document.getElementById("profileSel").value'))
        check('historical-total-119', True, js('document.getElementById("totalsBox").textContent.includes("$119.00")'))
        dialog = manager()
        dialog.picker = lambda kind: ''
        QTest.mouseClick(dialog.backup, Qt.MouseButton.LeftButton)
        check('cancel-file-picker-no-request', None, dialog.request_id)
        dialog.picker = lambda kind: str(backup)
        QTest.mouseClick(dialog.backup, Qt.MouseButton.LeftButton)
        wait(lambda: dialog.request_id is None and 'Respaldo verificado:' in dialog.status.text())
        check('native-backup-saved', True, backup.exists())
        backup_hash = file_hash(backup, threading.Event())
        bad = backup.parent/'invalid.sqlite3'
        bad.write_bytes(b'not SQLite')
        dialog.picker = lambda kind: str(bad)
        QTest.mouseClick(dialog.restore, Qt.MouseButton.LeftButton)
        wait(lambda: dialog.request_id is None and 'No se pudo' in dialog.status.text())
        check('invalid-restore-no-plan', None, dialog.plan)
        dialog.picker = lambda kind: str(backup)
        QTest.mouseClick(dialog.restore, Qt.MouseButton.LeftButton)
        wait(lambda: dialog.request_id is None and dialog.plan is not None)
        check('review-documents-before-confirmation', 4, dialog.plan['documents'])
        check('review-is-explicit', True, 'aún no modifica' in dialog.review.text())
        QTest.mouseClick(dialog.discard, Qt.MouseButton.LeftButton)
        wait(lambda: dialog.request_id is None and dialog.plan is None)
        check('discard-keeps-session', ids['first'], js('FiscalOpsRuntime.state.dataset_id'))
        QTest.mouseClick(dialog.done, Qt.MouseButton.LeftButton)
        wait(lambda: window.data_dialog is None)
        open_session(ids['second'])
        check('pre-restore-session-second', ids['second'], js('FiscalOpsRuntime.state.dataset_id'))
        dialog = manager()
        dialog.picker = lambda kind: str(backup)
        QTest.mouseClick(dialog.restore, Qt.MouseButton.LeftButton)
        wait(lambda: dialog.request_id is None and dialog.plan is not None)
        QTest.qWait(250)
        dialog.grab().save(str(OUT/'restore_review.png'))
        QTest.mouseClick(dialog.confirm, Qt.MouseButton.LeftButton)
        wait(lambda: dialog.request_id is None and dialog.changed and 'Restauración completada' in dialog.review.text())
        check('preventive-copy-shown-to-user', True, 'before_restore_' in dialog.review.text())
        QTest.qWait(200)
        dialog.grab().save(str(OUT/'restore_completed.png'))
        QTest.mouseClick(dialog.done, Qt.MouseButton.LeftButton)
        wait(lambda: window.data_dialog is None)
        wait('!!window.FiscalOpsRuntime && FiscalOpsRuntime.state.persistence==="ready" && !FiscalOpsRuntime.state.busy && FiscalOpsRuntime.state.dataset_id==='+json.dumps(ids['first']))
        wait('FiscalOpsRuntime.state.totals==="ready"')
        check('restore-active-first', ids['first'], js('FiscalOpsRuntime.state.dataset_id'))
        check('restore-query', 'HISTORY-1', js('document.getElementById("q").value'))
        check('restore-documents', 3, js('FiscalOpsRuntime.state.documents'))
        check('backup-not-modified-by-restore', backup_hash, file_hash(backup, threading.Event()))
        report['recovery_path'] = window.last_restore['recovery_path']
        check('preventive-backup-exists', True, Path(report['recovery_path']).exists())
        for kind in ('csv', 'txt', 'xlsx'):
            if kind == 'xlsx':
                web_click('excel')
                wait('document.getElementById("exportModal").classList.contains("on")')
                js('document.querySelectorAll("#analysisChoices input").forEach(i=>{i.checked=true;i.dispatchEvent(new Event("change"))})')
                web_click('exportGenerate')
            else:
                web_click(kind)
            wait('!FiscalOpsRuntime.state.busy && FiscalOpsRuntime.state.last_export && FiscalOpsRuntime.state.last_export.format==='+json.dumps(kind))
            wait(lambda: bool(downloads) and downloads[-1].isFinished())
            check(kind+'-completed', QWebEngineDownloadRequest.DownloadState.DownloadCompleted.name, downloads[-1].state().name)
            check(kind+'-one-selected-row', 1, js('FiscalOpsRuntime.state.last_export.rows'))
        window.raise_()
        window.activateWindow()
        QTest.qWait(1100)
        window.view.grab().save(str(OUT/'restored_report.png'))
        check('native-paths-not-on-webchannel', False, any(str(backup) in text or 'before_restore_' in text for text in web_responses))
    else:
        check('restored-session-survives-restart', ids['first'], js('FiscalOpsRuntime.state.dataset_id'))
        check('restored-view-survives-restart', 'HISTORY-1', js('document.getElementById("q").value'))
        check('restored-total-survives-restart', True, js('document.getElementById("totalsBox").textContent.includes("$119.00")'))
    check('sqlite-worker-affinity', True, window.fiscal.worker.store.repository.owner_thread in window.fiscal.worker.thread_ids and window.fiscal.worker.store.repository.owner_thread != window.fiscal.gui_thread_id)
    check('no-javascript-errors', False, any('Uncaught' in m['message'] for m in window.web_page.messages))
except Exception as exc:
    report['fatal'], report['traceback'] = str(exc), traceback.format_exc()
    report['state'] = js('JSON.stringify(window.FiscalOpsRuntime&&FiscalOpsRuntime.state)')
    if window.data_dialog:
        report['dialog_status'] = window.data_dialog.status.text()
finally:
    if window.data_dialog:
        QTest.mouseClick(window.data_dialog.done, Qt.MouseButton.LeftButton)
        end = time.monotonic()+15
        while window.data_dialog is not None and time.monotonic() < end:
            QTest.qWait(30)
    window.close()
    end = time.monotonic()+15
    while not window._closed and time.monotonic() < end:
        QTest.qWait(30)
    report['closed'] = window._closed and not window.fiscal.thread.isRunning()
    report['sqlite_closed'] = window.fiscal.worker.store.repository.connection is None
    report['console'] = window.web_page.messages
    (OUT/f'{args.phase}.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'source_sha256'}, indent=2))
    if window._closed:
        window.deleteLater()
        QTest.qWait(100)

raise SystemExit(1 if report.get('fatal') or not report['closed'] or not report['sqlite_closed'] else 0)
