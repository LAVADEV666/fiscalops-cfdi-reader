"""Record available local runtimes without installing software."""
from pathlib import Path
import argparse
import importlib.util
import json
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--bundled-python', type=Path)
parser.add_argument('--node-modules', type=Path)
args = parser.parse_args()
modules = ['playwright', 'PySide6', 'PyQt6', 'selenium']
result = {'system': platform.platform(), 'primary_python': {'version': sys.version, 'executable': sys.executable,
          'modules': {name: bool(importlib.util.find_spec(name)) for name in modules}},
          'bundled_python': None, 'node_packages': {}, 'installed_browser_executables': []}
if args.bundled_python and args.bundled_python.is_file():
    code = "import json,sys,importlib.util; print(json.dumps({'version':sys.version,'modules':{m:bool(importlib.util.find_spec(m)) for m in ['playwright','PySide6','PyQt6','selenium']}}))"
    run = subprocess.run([str(args.bundled_python), '-c', code], capture_output=True, text=True, check=True)
    result['bundled_python'] = json.loads(run.stdout)
if args.node_modules:
    for name in ['playwright', 'playwright-core', '@playwright/test', 'pngjs', 'pixelmatch']:
        package = args.node_modules / name / 'package.json'
        result['node_packages'][name] = json.loads(package.read_text(encoding='utf-8'))['version'] if package.is_file() else None
for path in [Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'), Path('C:/Program Files/Google/Chrome/Application/chrome.exe')]:
    result['installed_browser_executables'].append({'path': str(path), 'present': path.is_file(), 'launch_not_implied_by_presence': True})
destination = ROOT / 'tests/visual/evidence/environment.json'
destination.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
