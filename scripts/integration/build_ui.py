"""Append native adapters to the frozen SPEC011 runtime; preserve all HTML/CSS/branding bytes."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PREVIOUS = '7846ebe98f0a09cecf83915c8102a6d46ce0ca1d'


def frozen(name):
    return subprocess.run(['git', 'show', PREVIOUS+':'+name], cwd=ROOT, check=True, capture_output=True).stdout


def main():
    ui = ROOT/'app/ui'
    original = (ROOT/'FiscalOps_CFDI_READER_SSGT_V21_1_PRO.html').read_bytes()
    assert hashlib.sha256(original).hexdigest() == '33eeed2334a683b5360c2fc4f9cabc26885be66fef8714e4278f97235b8c373b'
    assert original == (ROOT/'legacy/FiscalOps_CFDI_READER_SSGT_V21_1_PRO.html').read_bytes()
    for name in ('index.html', 'v20-runtime.js', 'column-editor.js'):
        assert (ui/name).read_bytes() == frozen('app/ui/'+name), name
    source = frozen('app/ui/legacy-runtime.js')
    end = source.rfind(b'})();')
    assert end > 0 and not source[end+5:].strip()
    adapter = (ui/'native-integration.js').read_bytes()
    runtime = source[:end]+b'\n/* NATIVE WORKER INTEGRATION */\n'+adapter+b'\n'+source[end:]
    (ui/'legacy-runtime.js').write_bytes(runtime)
    report = {'previous_commit': PREVIOUS, 'original_legacy_unchanged': True, 'html_css_unchanged': True,
              'base_runtime_sha256': hashlib.sha256(source).hexdigest(),
              'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in ui.iterdir() if p.suffix in ('.js', '.html')},
              'native_mode': 'fiscal Python worker; JavaScript fiscal entry points fail closed',
              'browser_mode': 'Processing/export blocked without Qt; legacy execution requires explicit QA-server visual-reference flag'}
    dest = ROOT/'tests/integration/evidence'
    dest.mkdir(parents=True, exist_ok=True)
    (dest/'ui-build.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print('Native runtime built; original, legacy, HTML, CSS and branding preserved')


if __name__ == '__main__':
    main()
