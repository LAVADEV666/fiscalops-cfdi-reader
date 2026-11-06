"""Paired REAL Qt captures: protected original versus native engine on arithmetically compatible data."""
from pathlib import Path
import hashlib
import json
import sys
import time
import argparse
import subprocess

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'tests/fiscal')]
parser = argparse.ArgumentParser()
parser.add_argument('--variant', choices=('before', 'after'))
args = parser.parse_args()
if not args.variant:
    folder = ROOT/'tests/integration/visual'
    variants = []
    for variant in ('before', 'after'):
        result = subprocess.run([sys.executable, __file__, '--variant', variant], cwd=ROOT, capture_output=True, text=True, timeout=180)
        if result.returncode:
            print(result.stdout, result.stderr)
            raise SystemExit(result.returncode)
        variants.append(json.loads((folder/f'captures_{variant}.json').read_text(encoding='utf-8')))
    assert variants[0]['source_sha256'] == variants[1]['source_sha256']
    merged = dict(variants[0], captures=variants[0]['captures']+variants[1]['captures'], windows_closed=variants[0]['windows_closed']+variants[1]['windows_closed'])
    (folder/'captures.json').write_text(json.dumps(merged, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'captures': len(merged['captures']), 'closed': merged['windows_closed'], 'separate_processes': True}))
    raise SystemExit(0)
from PySide6.QtCore import QEventLoop, QTimer, Qt, QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from app.desktop.main import DesktopWindow
from fixtures import invoice
from scripts.integration.evidence import source_hashes

OUT = ROOT/'tests/integration/visual'
OUT.mkdir(parents=True, exist_ok=True)
TFD = '<t:TimbreFiscalDigital xmlns:t="http://www.sat.gob.mx/TimbreFiscalDigital" Version="1.1" UUID="11111111-1111-4111-8111-111111111111" FechaTimbrado="2026-11-06T12:34:57" RfcProvCertif="AAA010101AAA" SelloCFD="QUFB" NoCertificadoSAT="00001000000500000000" SelloSAT="QUFB"/>'
fixture = OUT/'compatible.xml'
fixture.write_bytes(invoice(extra=TFD))
app = QApplication(sys.argv[:1])
app.setQuitOnLastWindowClosed(False)
report = {'source_sha256': source_hashes(), 'fixture_sha256': hashlib.sha256(fixture.read_bytes()).hexdigest(),
          'captures': [], 'windows_closed': [], 'purpose': 'UI preservation on compatible values; P0 numeric differences verified separately'}


def js(page, code):
    result, loop = [], QEventLoop()
    def done(value):
        result.append(value)
        loop.quit()
    page.runJavaScript(code, done)
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    timer.start(10000)
    loop.exec()
    timer.stop()
    if not result:
        raise RuntimeError('JS timeout')
    return result[0]


def wait(page, expression):
    end = time.monotonic()+40
    while time.monotonic() < end:
        if js(page, expression):
            return
        QTest.qWait(20)
    raise RuntimeError('Timeout: '+expression)


def native_click(window, identity):
    page = window.web_page
    js(page, f'document.getElementById({json.dumps(identity)}).scrollIntoView({{block:"center"}})')
    QTest.qWait(70)
    rect = json.loads(js(page, f'JSON.stringify((()=>{{var r=document.getElementById({json.dumps(identity)}).getBoundingClientRect();return {{x:r.x+r.width/2,y:r.y+r.height/2}}}})())'))
    QTest.mouseClick(window.view.focusProxy(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(round(rect['x']), round(rect['y'])))


try:
    for reference in (args.variant == 'before',):
        window = DesktopWindow(reference=reference)
        page = window.web_page
        window.web_page.file_picker = lambda *args: [str(fixture)]
        window.show()
        assert QTest.qWaitForWindowExposed(window, 10000)
        wait(page, 'document.readyState==="complete" && !!document.querySelector("#s2.on")')
        role = 'before' if reference else 'after'
        for width, height in ((1366, 768), (1600, 900), (1920, 1080)):
            window.setMinimumSize(width, height)
            window.resize(width, height)
            def capture(scene):
                # Pause only test animations, at the same instant in both renderers; no production CSS changes.
                window.raise_()
                window.activateWindow()
                js(page, 'document.getAnimations().filter(a=>a.effect.getComputedTiming().iterations===Infinity).forEach(a=>{a.pause();a.currentTime=0;})')
                QTest.qWait(1100)
                file = OUT/f'{scene}_{role}_{width}x{height}.png'
                window.view.grab().save(str(file))
                report['captures'].append({'role': role, 'scene': scene, 'width': width, 'height': height,
                                            'actual_viewport': js(page, 'innerWidth+"x"+innerHeight'), 'file': file.relative_to(ROOT).as_posix(),
                                            'sha256': hashlib.sha256(file.read_bytes()).hexdigest()})
            js(page, 'document.getElementById("more").click()')
            capture('upload')
            if width == 1366:
                native_click(window, 'select')
                wait(page, 'document.getElementById("filelist").textContent.includes("compatible.xml")')
                js(page, 'document.getElementById("process").click()')
                wait(page, '!!document.querySelector("#s3.on") && !!document.querySelector("#tbody tr[data-i]")')
            else:
                js(page, 'document.getElementById("process").click()')
                wait(page, '!!document.querySelector("#s3.on")')
            if not reference:
                wait(page, 'FiscalOpsRuntime.state.totals==="ready" && !FiscalOpsRuntime.state.busy')
            js(page, 'scrollTo(0,0)')
            capture('report')
            js(page, 'document.getElementById("editcols").click()')
            capture('editor')
            js(page, 'document.getElementById("closecols").click()')
            js(page, 'document.querySelector("#tbody tr[data-i]").click()')
            wait(page, 'document.getElementById("previewModal").classList.contains("on") && document.querySelectorAll("#previewBody .pv-tab").length===5')
            capture('visor')
            js(page, 'document.querySelector("#previewBody [data-pv=impuestos]").click()')
            capture('taxes')
            js(page, 'document.getElementById("previewClose").click();document.getElementById("excel").click()')
            capture('excel')
            js(page, 'document.getElementById("exportCancel").click()')
        window.close()
        end = time.monotonic()+15
        while time.monotonic() < end and not window._closed:
            QTest.qWait(20)
        report['windows_closed'].append(window._closed and not window.fiscal.thread.isRunning())
        assert report['windows_closed'][-1]
except Exception as exc:
    report['fatal'] = str(exc)
finally:
    if 'window' in globals() and not window._closed:
        window.close()
        for _ in range(500):
            if window._closed:
                break
            QTest.qWait(20)
    (OUT/f'captures_{args.variant}.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'captures': len(report['captures']), 'closed': report['windows_closed'], 'fatal': report.get('fatal')}))
    if window._closed:
        window.deleteLater()
        QTest.qWait(100)

raise SystemExit(1 if report.get('fatal') or len(report['captures']) != 18 else 0)
