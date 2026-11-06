"""Freeze actual captures, separating unsuccessful transient shots from baseline."""
from pathlib import Path
import hashlib
import json
import struct

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'tests/visual/evidence'
BASELINE = ROOT / 'tests/visual/baseline'


def image_info(path):
    data = path.read_bytes()
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        dimensions, mime = list(struct.unpack('>II', data[16:24])), 'image/png'
    elif data[:2] == b'\xff\xd8':
        offset = 2
        dimensions = None
        while offset < len(data):
            assert data[offset] == 0xff
            marker = data[offset+1]
            length = struct.unpack('>H', data[offset+2:offset+4])[0]
            if marker in (0xc0, 0xc1, 0xc2):
                height, width = struct.unpack('>HH', data[offset+5:offset+9])
                dimensions = [width, height]
                break
            offset += 2 + length
        assert dimensions
        mime = 'image/jpeg'
    else:
        raise ValueError(f'Unknown screenshot format: {path}')
    return {'sha256': hashlib.sha256(data).hexdigest(), 'pixel_dimensions': dimensions, 'mime': mime}


def main():
    destination = BASELINE / 'manifest.json'
    if destination.exists():
        raise SystemExit('Baseline already frozen; use a candidate directory for new runs')
    nav = json.loads((EVIDENCE / 'navigation.json').read_text(encoding='utf-8'))
    records = []
    transient = EVIDENCE / 'transient'
    transient.mkdir(exist_ok=True)
    for capture in nav['captures']:
        path = BASELINE / capture['file']
        capture['accepted_baseline'] = capture['scene'] != '19_processing_progress'
        if not capture['accepted_baseline']:
            target = transient / path.name
            if target.exists() and path.exists():
                raise SystemExit('Refusing to replace existing transient evidence')
            # Move only this known generated PNG, within the workspace (no recursion).
            assert path.resolve().is_relative_to(ROOT.resolve())
            assert target.resolve().is_relative_to(ROOT.resolve())
            if path.exists():
                path.rename(target)
            path = target
        capture['path'] = path.relative_to(ROOT).as_posix()
        capture['pixel_dimensions'] = image_info(path)['pixel_dimensions']
        if capture['accepted_baseline']:
            assert capture['before']['activeScreen'] == capture['after']['activeScreen']
            records.append({**capture, 'browser': nav['browser'], 'system': nav['system']})
    for path in sorted(BASELINE.glob('iab_*')):
        info = image_info(path)
        if info['mime'] == 'image/jpeg' and path.suffix != '.jpg':
            target = path.with_suffix('.jpg')
            assert not target.exists()
            path.rename(target)
            path = target
        records.append({'scene': path.stem, 'path': path.relative_to(ROOT).as_posix(), **info,
                        'browser': 'ChatGPT in-app browser; exact version not available in this capture',
                        'viewport': 'Explicit viewport override matching filename, reset after capture',
                        'dpi': 'Not independently measured', 'provenance': 'CUA screenshot; supplemental initial/upload reference'})
    manifest = {'status': 'PARTIAL_AUTHENTIC_BASELINE', 'prototype_sha256': nav['prototype_sha256'],
                'preserved_original': 'FiscalOps_CFDI_READER_SSGT_V21_1_PRO.html',
                'captures': records, 'accepted_automated_captures': sum(1 for c in nav['captures'] if c['accepted_baseline']),
                'supplemental_iab_captures': len(records)-sum(1 for c in nav['captures'] if c['accepted_baseline']),
                'pending': nav['blocked'], 'fiscal_reference': False,
                'freeze_rule': 'Do not overwrite PNGs or manifest. New automation runs go to candidate directories; manual additions require review.'}
    destination.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    (EVIDENCE / 'navigation.json').write_text(json.dumps(nav, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'baseline_captures': len(records), 'transient_not_accepted': len(nav['captures'])-manifest['accepted_automated_captures']}))


if __name__ == '__main__':
    main()
