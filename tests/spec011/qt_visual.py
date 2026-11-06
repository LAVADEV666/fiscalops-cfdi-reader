"""Actual native Qt screenshots of reference and development under equal conditions."""
from pathlib import Path
import json
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from PySide6.QtCore import QEventLoop,QPoint,Qt,QTimer,QUrl
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from app.desktop.main import DesktopWindow

OUT=ROOT/'tests/spec011/qt-visual'
OUT.mkdir(parents=True,exist_ok=True)
app=QApplication(sys.argv[:1]);app.setQuitOnLastWindowClosed(False)
window=DesktopWindow();page=window.web_page
report={'platform':app.platformName(),'captures':[],'qa_only':'Infinite animations paused at currentTime0 on both original/development. Minimum client size used for screen-workarea limit.'}


def js(code):
    values=[];loop=QEventLoop()
    def done(value):values.append(value);loop.quit()
    page.runJavaScript(code,done)
    timer=QTimer();timer.setSingleShot(True);timer.timeout.connect(loop.quit);timer.start(8000);loop.exec();timer.stop()
    if not values:raise RuntimeError('JavaScript timeout')
    return values[0]


def wait(code,seconds=10):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        if js(code):return
        QTest.qWait(30)
    raise RuntimeError('Timed out: '+code)


def click(identity):js('document.getElementById('+json.dumps(identity)+').click()')


def snap(scene,variant,width,height):
    QTest.qWait(500)
    js('document.getAnimations().filter(a=>a.effect?.getComputedTiming().iterations===Infinity).forEach(a=>{a.pause();a.currentTime=0})')
    QTest.qWait(60)
    file=OUT/f'{scene}_{variant}_{width}.png'
    assert window.view.grab().save(str(file))
    metadata=json.loads(js('JSON.stringify({viewport:[innerWidth,innerHeight],dpr:devicePixelRatio,screen:document.querySelector(".screen.on").id,modal:Array.from(document.querySelectorAll(".modal.on")).map(n=>n.id)})'))
    assert metadata['viewport']==[width,height]
    if scene=='initial':assert metadata['screen']=='s1'
    report['captures'].append({'scene':scene,'variant':variant,'file':file.name,**metadata})
    (OUT/'captures.json').write_text(json.dumps(report,indent=2),encoding='utf-8')


try:
    window.show();assert QTest.qWaitForWindowExposed(window,10000)
    assert app.platformName()=='windows'
    fixtures=sorted((ROOT/'tests/visual/fixtures/AAA010101AAA').glob('*'))
    page.file_picker=lambda *_:[str(p) for p in fixtures if p.suffix in ('.xml','.txt')]
    for width,height in [(1366,768),(1600,900),(1920,1080)]:
        window.setMinimumSize(width,height);window.resize(width,height);QTest.qWait(200)
        for variant in ['reference','development']:
            loaded=[]
            def on_loaded(ok):loaded.append(ok)
            page.loadFinished.connect(on_loaded)
            window.view.load(window.reference_url if variant=='reference' else window.frontend_url)
            end=time.monotonic()+10
            while not loaded and time.monotonic()<end:QTest.qWait(30)
            page.loadFinished.disconnect(on_loaded)
            assert loaded and loaded[-1]
            wait('document.readyState==="complete" && !!document.querySelector("#s1.on")')
            snap('initial',variant,width,height)
            wait('!!document.querySelector("#s2.on")');snap('upload',variant,width,height)
            js('document.getElementById("rfc").value="AAA010101AAA";document.getElementById("select").scrollIntoView({block:"center"})')
            QTest.qWait(100)
            point=json.loads(js('JSON.stringify((()=>{var r=document.getElementById("select").getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})())'))
            QTest.mouseClick(window.view.focusProxy(),Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,QPoint(round(point['x']),round(point['y'])))
            wait('!document.getElementById("process").disabled')
            click('process');wait('!!document.querySelector("#s3.on")');snap('reports',variant,width,height)
            click('editcols');wait('!!document.querySelector("#modal.on")');snap('editor',variant,width,height);click('closecols')
            js('var row=document.querySelector("#tbody tr[data-i]");row.focus();row.click()');wait('!!document.querySelector("#previewModal.on")');snap('viewer',variant,width,height)
            QTest.keyClick(window.view.focusProxy(),Qt.Key.Key_Escape);QTest.qWait(50)
            click('excel');wait('!!document.querySelector("#exportModal.on")');snap('excel',variant,width,height)
            click('exportClose')
except Exception as error:
    report['fatal']=str(error)
finally:
    window.close();QTest.qWait(100)
    report['clean_close']=window._closed
    (OUT/'captures.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'captures':len(report['captures']),'fatal':report.get('fatal'),'clean_close':report['clean_close']}))
raise SystemExit(1 if report.get('fatal') else 0)
