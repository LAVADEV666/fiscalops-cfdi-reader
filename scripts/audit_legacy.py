"""Preserve and inventory the supplied prototype without changing it (stdlib only)."""
from pathlib import Path
from html.parser import HTMLParser
import base64
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
NAME = 'FiscalOps_CFDI_READER_SSGT_V21_1_PRO.html'


class MarkupInventory(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []
        self.resources = []
        self.blocks = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('style', 'script'):
            self.current = {'tag': tag, 'line': self.getpos()[0], 'text': ''}
        if attrs.get('id'):
            self.elements.append({'tag': tag, 'line': self.getpos()[0], **attrs})
        for key in ('src', 'href'):
            if key in attrs and not attrs[key].startswith('data:'):
                self.resources.append({'tag': tag, key: attrs[key], 'line': self.getpos()[0]})

    def handle_data(self, data):
        if self.current:
            self.current['text'] += data

    def handle_endtag(self, tag):
        if self.current and self.current['tag'] == tag:
            self.blocks.append(self.current)
            self.current = None


def main():
    source = ROOT / NAME
    if not source.exists():
        raise SystemExit('BLOCKED_MISSING_PROTOTYPE')
    data = source.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    legacy = ROOT / 'legacy' / NAME
    legacy.parent.mkdir(exist_ok=True)
    if legacy.exists() and legacy.read_bytes() != data:
        raise SystemExit('Existing legacy copy differs; refusing to overwrite')
    legacy.write_bytes(data)
    text = data.decode('utf-8-sig')
    output = ROOT / 'assets' / 'legacy'
    output.mkdir(parents=True, exist_ok=True)
    evidence = ROOT / 'tests' / 'audit' / 'evidence'
    evidence.mkdir(parents=True, exist_ok=True)
    parser = MarkupInventory()
    parser.feed(text)
    styles = []
    for i, block in enumerate((b for b in parser.blocks if b['tag'] == 'style'), 1):
        path = output / f'style-{i:02}.css'
        path.write_text(block['text'], encoding='utf-8')
        styles.append({'path': str(path.relative_to(ROOT)), 'line': block['line'],
                       'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    images = {}
    for match in re.finditer(r'data:([^;,]+);base64,([A-Za-z0-9+/=]+)', text):
        image = base64.b64decode(match[2], validate=True)
        digest = hashlib.sha256(image).hexdigest()
        if digest not in images:
            path = output / f'embedded-{len(images)+1:02}.png'
            path.write_bytes(image)
            images[digest] = {'path': str(path.relative_to(ROOT)), 'mime': match[1], 'sha256': digest,
                              'bytes': len(image), 'occurrences': []}
        images[digest]['occurrences'].append(text.count('\n', 0, match.start()) + 1)
    functions = []
    # Lexical index, not an AST or a call graph. Keep every occurrence for manual review.
    for match in re.finditer(r'\b(?:(async)\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(', text):
        functions.append({'name': match[2], 'line': text.count('\n', 0, match.start()) + 1,
                          'async': bool(match[1])})
    assignments = []
    for match in re.finditer(r'\b([A-Za-z_$][\w$]*)\s*=\s*(?:async\s+)?function\s*\(', text):
        assignments.append({'name': match[1], 'line': text.count('\n', 0, match.start()) + 1})
    scripts = []
    for i, block in enumerate((b for b in parser.blocks if b['tag'] == 'script'), 1):
        path = evidence / f'script-{i:02}.js'
        path.write_text(block['text'], encoding='utf-8')
        scripts.append({'path': str(path.relative_to(ROOT)), 'line': block['line']})
    raw = re.search(r'var SATCAT_RAW=(\{.*?\});', text)
    catalogs = json.loads(raw[1]) if raw else {}
    (output / 'catalogs-original.json').write_text(json.dumps(catalogs, ensure_ascii=False, indent=2), encoding='utf-8')
    manifest = {'prototype': NAME, 'bytes': len(data), 'lines': len(text.splitlines()), 'sha256': sha,
                'legacy_sha256': hashlib.sha256(legacy.read_bytes()).hexdigest(),
                'styles': styles, 'images': list(images.values()), 'scripts': scripts,
                'functions': functions, 'function_assignments': assignments,
                'elements': parser.elements, 'external_resources': parser.resources,
                'catalog_families': {k: len(v) for k, v in catalogs.get('catalogs', {}).items()}}
    (evidence / 'inventory.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: manifest[k] for k in ['sha256', 'legacy_sha256', 'bytes', 'lines', 'catalog_families']}, ensure_ascii=False))
    print(f'Preserved; {len(functions)} named declarations, {len(assignments)} function assignments, '
          f'{len(parser.elements)} element IDs, {len(images)} unique embedded images, {len(styles)} styles')


if __name__ == '__main__':
    main()
