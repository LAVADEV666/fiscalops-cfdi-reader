"""Smoke a REAL Windows Qt window; no offscreen platform or remote-debug port."""
from pathlib import Path
import json
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from PySide6 import __version__
from PySide6.QtCore import QEventLoop, QPoint, Qt, QTimer, qVersion
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineCore import qWebEngineChromiumVersion
from app.desktop.main import DesktopWindow,local_resource_allowed
from PySide6.QtCore import QUrl

OUT=ROOT/'tests/spec011/qt'
OUT.mkdir(parents=True,exist_ok=True)
report={'pyside6':__version__,'qt':qVersion(),'chromium':qWebEngineChromiumVersion(),'checks':[], 'captures':[]}
app=QApplication(sys.argv[:1])
app.setQuitOnLastWindowClosed(False)
window=DesktopWindow()
page=window.web_page


def save():
    (OUT/'smoke.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')


def js(code):
    result=[]
    loop=QEventLoop()
    def done(value):
        result.append(value)
        loop.quit()
    page.runJavaScript(code,done)
    timer=QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    timer.start(8000)
    loop.exec()
    timer.stop()
    if not result:
        raise RuntimeError('JavaScript callback timeout')
    return result[0]


def wait(expression,timeout=10):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        if js(expression):return
        QTest.qWait(30)
    raise RuntimeError('Timed out: '+expression)


def check(name,expected,run):
    try:
        actual=run()
        report['checks'].append({'id':name,'expected':expected,'actual':actual,'result':'PASS' if actual==expected else 'FAIL'})
    except Exception as error:
        report['checks'].append({'id':name,'expected':expected,'error':str(error),'result':'ERROR'})
    save()


def click(identity):
    return js(f'document.getElementById({json.dumps(identity)}).click();true')


def native_click(identity):
    js(f'document.getElementById({json.dumps(identity)}).scrollIntoView({{block:"center"}})')
    QTest.qWait(100)
    rect=js(f'JSON.stringify((()=>{{var r=document.getElementById({json.dumps(identity)}).getBoundingClientRect();return {{x:r.x+r.width/2,y:r.y+r.height/2}}}})())')
    point=json.loads(rect)
    QTest.mouseClick(window.view.focusProxy(),Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,QPoint(round(point['x']),round(point['y'])))
    QTest.qWait(60)


try:
    window.show()
    exposed=QTest.qWaitForWindowExposed(window,10000)
    report['platform']=QGuiApplication.platformName()
    report['native_win_id']=int(window.winId())
    screen=window.screen()
    report['screen']={'name':screen.name(),'logical_dpi':screen.logicalDotsPerInch(),'physical_dpi':screen.physicalDotsPerInch(),'device_pixel_ratio':screen.devicePixelRatio(),'geometry':[screen.geometry().width(),screen.geometry().height()]}
    check('real-windows-platform','windows',lambda:report['platform'])
    check('real-window-exposed',True,lambda:exposed and window.isVisible())
    wait('document.readyState==="complete" && !!document.querySelector("#s2.on")')
    wait('!!window.FiscalOpsDesktop')
    js('window.FiscalOpsDesktop.ready.then(value=>{window.__bridgeInfo=value})')
    wait('!!window.__bridgeInfo')
    check('channel-handshake','fiscalops.desktop/1',lambda:js('window.__bridgeInfo.protocol'))
    js('window.FiscalOpsDesktop.ping("qt-smoke").then(value=>{window.__pingReply=value})')
    wait('!!window.__pingReply')
    check('channel-ping',True,lambda:js('window.__pingReply.ok && window.__pingReply.request_id==="qt-smoke"'))
    check('resources-loaded',True,lambda:js('Array.from(document.images).every(image=>image.complete&&image.naturalWidth>0)'))
    for width,height in [(1366,768),(1600,900),(1920,1080)]:
        # QA-only size constraint: a framed window otherwise gets clamped by
        # the available Windows work area. No display/DPI settings are changed.
        window.setMinimumSize(width,height)
        window.resize(width,height)
        QTest.qWait(300)
        check(f'viewport-{width}',f'{width}x{height}',lambda:js('innerWidth+"x"+innerHeight'))
        file=OUT/f'upload_{width}x{height}.png'
        window.view.grab().save(str(file))
        report['captures'].append({'scene':'upload','file':file.name,'requested_css_viewport':[width,height],'actual_css_viewport':js('innerWidth+"x"+innerHeight'),'native_dpr':window.view.devicePixelRatioF(),'qa_minimum_size_constraint':True})
    window.setMinimumSize(0,0)
    window.showMaximized();QTest.qWait(300)
    check('maximize',True,lambda:window.isMaximized())
    window.showNormal();window.resize(1366,768);QTest.qWait(300)
    fixtures=sorted((ROOT/'tests/visual/fixtures/AAA010101AAA').glob('*'))
    window.web_page.file_picker=lambda *_args:[str(p) for p in fixtures if p.suffix in ('.xml','.txt')]
    js('document.getElementById("rfc").value="AAA010101AAA"')
    native_click('select')
    wait('!document.getElementById("process").disabled')
    check('file-input-via-qt',True,lambda:js('document.getElementById("file").files.length===50'))
    native_click('process')
    wait('!!document.querySelector("#s3.on")')
    QTest.qWait(650)
    check('table-rendered',True,lambda:js('document.querySelectorAll("#tbody tr[data-i]").length>0'))
    js('document.querySelector("#typeTabs [data-type=I]").click()')
    check('single-type-click','I',lambda:js('document.querySelector("#typeTabs button.on").getAttribute("data-type")'))
    js('document.querySelector("#typeTabs [data-type=I]").click()')
    for invoker in ['editcols','editcolsTop']:
        click(invoker)
        wait('!!document.querySelector("#modal.on")')
        check('initial-focus-'+invoker,'colSearch',lambda:js('document.activeElement.id'))
        js('document.getElementById("closecols").focus()')
        QTest.keyClick(window.view.focusProxy(),Qt.Key.Key_Tab,Qt.KeyboardModifier.ShiftModifier)
        QTest.qWait(100)
        check('shift-tab-'+invoker,'applycols',lambda:js('document.activeElement.id'))
        QTest.keyClick(window.view.focusProxy(),Qt.Key.Key_Escape)
        QTest.qWait(100)
        check('escape-restores-'+invoker,invoker,lambda:js('document.activeElement.id'))
    click('editcols');QTest.qWait(400)
    window.view.grab().save(str(OUT/'editor_1366x768.png'))
    click('closecols')
    click('excel');wait('!!document.querySelector("#exportModal.on")');QTest.qWait(400)
    check('export-modal',True,lambda:js('!!document.querySelector("#exportModal.on")'))
    window.view.grab().save(str(OUT/'excel_1366x768.png'))
    click('exportClose')
    js('document.querySelector("#tbody tr[data-i]").click()');wait('!!document.querySelector("#previewModal.on")');QTest.qWait(400)
    check('viewer-modal',True,lambda:js('!!document.querySelector("#previewModal.on")'))
    window.view.grab().save(str(OUT/'viewer_1366x768.png'))
    for tab in ['impuestos','conceptos','datos','xml']:
        js(f'document.querySelector("#previewBody [data-pv={tab}]").click()')
        check('viewer-tab-'+tab,tab,lambda:js('document.querySelector("#previewBody .pv-pane.on").getAttribute("data-pane")'))
    QTest.keyClick(window.view.focusProxy(),Qt.Key.Key_Escape);QTest.qWait(100)
    check('viewer-escape',False,lambda:js('!!document.querySelector("#previewModal.on")'))
    check('horizontal-scroll-available',True,lambda:js('document.querySelector(".tablebox").scrollWidth>document.querySelector(".tablebox").clientWidth'))
    check('local-requests-only',True,lambda:all(r['allowed'] for r in window.interceptor.requests))
    js('fetch("https://example.invalid/spec011-offline").catch(()=>{window.__offlineBlocked=true})')
    wait('window.__offlineBlocked===true')
    # A file-origin page can be rejected by Qt BEFORE the interceptor. Do not
    # weaken that policy merely to manufacture an intercepted request.
    check('external-network-blocked',True,lambda:bool(js('window.__offlineBlocked')) and not local_resource_allowed(QUrl('https://example.invalid/spec011-offline')))
    report['offline_proof']={'fetch_rejected':bool(js('window.__offlineBlocked')),'external_url_allowlisted':False,'intercepted_denials':sum(not r['allowed'] for r in window.interceptor.requests),'transport':'local files; no HTTP server'}
    click('more');click('clear')
    page.file_picker=lambda *_args:[str(ROOT/'tests/visual/.work/progress-synthetic.zip')]
    native_click('select');wait('!document.getElementById("process").disabled')
    click('process')
    try:
        wait('!!document.querySelector("#s2.on") && document.getElementById("status").textContent.includes("Procesados")',timeout=3)
        before=js('JSON.stringify({screen:document.querySelector(".screen.on").id,progress:document.getElementById("prog").value,status:document.getElementById("status").textContent})')
        window.view.grab().save(str(OUT/'progress-attempt.png'))
        after=js('JSON.stringify({screen:document.querySelector(".screen.on").id,progress:document.getElementById("prog").value,status:document.getElementById("status").textContent})')
        prior,next_state=json.loads(before),json.loads(after)
        accepted=all(state['screen']=='s2' and 0<float(state['progress'])<100 and 'Procesados' in state['status'] for state in (prior,next_state))
        report['progress_capture']={'before':prior,'after':next_state,'file':'progress-attempt.png','accepted_stable_capture':accepted}
    except Exception as error:
        report['progress_capture']={'state':'PENDING_STABLE_CAPTURE','reason':str(error)}
    wait('!!document.querySelector("#s3.on")',timeout=20)
    check('qt-batch-completes',True,lambda:js('document.getElementById("sub").textContent.includes("2,000")'))
    report['requests']=window.interceptor.requests
    report['console']=page.messages
except Exception as error:
    report['fatal']=str(error)
finally:
    window.close()
    QTest.qWait(100)
    check('clean-close-window',True,lambda:window._closed and not window.isVisible())
    save()
print(json.dumps({'checks':len(report['checks']),'failures':[c for c in report['checks'] if c['result']!='PASS'],'fatal':report.get('fatal'),'platform':report.get('platform')},indent=2))
raise SystemExit(1 if report.get('fatal') or any(c['result']!='PASS' for c in report['checks']) else 0)
