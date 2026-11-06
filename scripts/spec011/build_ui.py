"""Build the development copy with narrowly scoped, audited UI-only edits."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[2]
NAME = 'FiscalOps_CFDI_READER_SSGT_V21_1_PRO.html'
EXPECTED = '33eeed2334a683b5360c2fc4f9cabc26885be66fef8714e4278f97235b8c373b'


def build():
    if (ROOT/'app/ui/native-integration.js').exists():
        raise SystemExit('SPEC011 is a historical builder. Use scripts/integration/build_ui.py for the native worker frontend.')
    data = (ROOT / NAME).read_bytes()
    assert hashlib.sha256(data).hexdigest() == EXPECTED
    assert (ROOT / 'legacy' / NAME).read_bytes() == data
    source = data.decode('utf-8-sig')
    original_lines = source.splitlines(keepends=True)
    lines = original_lines.copy()
    old = "function pg(n){['s1','s2','s3'].forEach((id,i)=>el(id).classList.toggle('on',i===n-1))}setTimeout(()=>pg(2),1600);"
    new = "var splashTimer=null;function pg(n){if(splashTimer!==null){clearTimeout(splashTimer);splashTimer=null;}['s1','s2','s3'].forEach((id,i)=>el(id).classList.toggle('on',i===n-1))}splashTimer=setTimeout(function(){splashTimer=null;if(el('s1').classList.contains('on'))pg(2)},1600);"
    assert old in lines[538]
    lines[538] = lines[538].replace(old, new)
    assert "el('typeTabs').addEventListener('click'" in lines[684]
    lines[684] = '/* SPEC011: typeTabs click is owned solely by setupFilters.onclick. */\n'
    assert "el('modal').classList.remove('on');" in lines[1102]
    lines[1102] = lines[1102].replace("el('modal').classList.remove('on');", '')
    editor = (ROOT / 'app/ui/column-editor.js').read_text(encoding='utf-8')
    assert lines[1126].startswith('function updateColumnSelectionCount()')
    lines[1126] = editor + '\n'
    for index in range(1127, 1131):
        lines[index] = ''
    for index in range(1174, 1177):
        lines[index] = ''  # V20 editor dismissals are now owned by column-editor.
    allowed = {538, 684, 1102, *range(1126, 1131), *range(1174, 1177)}
    assert all(lines[i] == original_lines[i] for i in range(len(lines)) if i not in allowed)
    html = ''.join(lines)
    blocks = list(re.finditer(r'<script\b[^>]*>([\s\S]*?)</script>', html, re.I))
    assert len(blocks) == 2
    ui = ROOT / 'app/ui'
    ui.mkdir(parents=True, exist_ok=True)
    for match, name in zip(blocks, ['legacy-runtime.js', 'v20-runtime.js']):
        (ui / name).write_bytes(match[1].encode('utf-8'))
    for match, name in reversed(list(zip(blocks, ['legacy-runtime.js', 'v20-runtime.js']))):
        html = html[:match.start()] + f'<script src="{name}"></script>' + html[match.end():]
    html = html.replace('</body>', '<script src="desktop-bridge.js"></script></body>')
    (ui / 'index.html').write_bytes(html.encode('utf-8'))
    runtime = (ui / 'legacy-runtime.js').read_text(encoding='utf-8')
    fiscal = {}
    for first, last in [(618, 626), (634, 666), (973, 1020), (1021, 1044)]:
        region = ''.join(original_lines[first-1:last])
        assert region in runtime
        fiscal[f'L{first}-L{last}'] = hashlib.sha256(region.encode()).hexdigest()
    report = {'original_sha256': EXPECTED, 'modified_original_lines': sorted(i+1 for i in allowed),
              'fiscal_regions_unchanged': fiscal,
              'css_unchanged': re.findall(r'<style\b[^>]*>([\s\S]*?)</style>', source.split('</head>',1)[0], re.I) == re.findall(r'<style\b[^>]*>([\s\S]*?)</style>', html.split('</head>',1)[0], re.I),
              'files': {name: hashlib.sha256((ui/name).read_bytes()).hexdigest() for name in ['index.html','legacy-runtime.js','v20-runtime.js','column-editor.js','desktop-bridge.js']}}
    evidence = ROOT / 'tests/spec011/evidence'
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence/'development-build.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    assert report['css_unchanged']
    return report


if __name__ == '__main__':
    print(json.dumps(build(), indent=2))
