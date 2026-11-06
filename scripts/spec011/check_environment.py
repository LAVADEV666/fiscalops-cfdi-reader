"""Inspect the isolated desktop runtime without claiming that a GUI was run."""
from pathlib import Path
import importlib.metadata as metadata
import importlib.util
import json
import platform
import sys

ROOT=Path(__file__).resolve().parents[2]


def inspect():
    result={'python':sys.version,'executable':sys.executable,'prefix':sys.prefix,'base_prefix':sys.base_prefix,
            'isolated_venv':sys.prefix!=sys.base_prefix,'platform':platform.platform(),'gui_executed':False,'packages':[]}
    if not importlib.util.find_spec('PySide6'):
        result['status']='BLOCKED_MISSING_PYSIDE6'
    else:
        from PySide6.QtCore import qVersion,QFile
        from PySide6.QtWebEngineCore import qWebEngineChromiumVersion
        from PySide6.QtWebChannel import QWebChannel
        result.update(status='AVAILABLE',qt=qVersion(),chromium=qWebEngineChromiumVersion(),qwebchannel_js=QFile.exists(':/qtwebchannel/qwebchannel.js'))
        for name in ['PySide6','PySide6_Essentials','PySide6_Addons','PySide6_WebEngine','PySide6_Pdf','shiboken6']:
            dist=metadata.distribution(name)
            result['packages'].append({'name':dist.metadata['Name'],'version':dist.version,'license_metadata':dist.metadata.get('License-Expression') or dist.metadata.get('License'),'license_files':dist.metadata.get_all('License-File') or []})
    target=ROOT/'tests/spec011/evidence/desktop-environment.json'
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    result=inspect();print(json.dumps(result,indent=2));raise SystemExit(0 if result['status']=='AVAILABLE' else 3)
