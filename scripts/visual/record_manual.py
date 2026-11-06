"""Register an operator-created screenshot without fabricating or replacing evidence."""
from pathlib import Path
import argparse
import hashlib
import json
import platform
import struct
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--png', required=True, type=Path)
    parser.add_argument('--scene', choices=['folder_connected', 'memory_cached', 'processing_progress', 'native_error', 'qt_container'], required=True)
    parser.add_argument('--viewport-width', required=True, type=int)
    parser.add_argument('--viewport-height', required=True, type=int)
    parser.add_argument('--browser', required=True)
    parser.add_argument('--windows-dpi-percent', required=True, type=int)
    parser.add_argument('--zoom-percent', required=True, type=int)
    parser.add_argument('--notes', default='')
    args = parser.parse_args()
    data = args.png.read_bytes()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise SystemExit('An authentic PNG screenshot is required')
    width, height = struct.unpack('>II', data[16:24])
    original = ROOT / 'FiscalOps_CFDI_READER_SSGT_V21_1_PRO.html'
    sha = hashlib.sha256(original.read_bytes()).hexdigest()
    expected = '33eeed2334a683b5360c2fc4f9cabc26885be66fef8714e4278f97235b8c373b'
    if sha != expected:
        raise SystemExit('PROTOTYPE_HASH_MISMATCH')
    directory = ROOT / 'tests/visual/baseline/manual'
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    name = f'{args.scene}_{args.viewport_width}x{args.viewport_height}_{stamp}'
    target = directory / f'{name}.png'
    with target.open('xb') as stream:
        stream.write(data)
    record = {'scene': args.scene, 'file': target.name, 'sha256': hashlib.sha256(data).hexdigest(),
              'prototype_sha256': sha, 'pixel_dimensions': [width, height],
              'viewport': [args.viewport_width, args.viewport_height], 'browser': args.browser,
              'windows_dpi_percent': args.windows_dpi_percent, 'zoom_percent': args.zoom_percent,
              'system': platform.platform(), 'provenance': 'operator-created screenshot; metadata reported by operator',
              'review_status': 'PENDING_REVIEW', 'captured_at_registration_utc': stamp, 'notes': args.notes}
    with (directory / f'{name}.json').open('x', encoding='utf-8') as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
    print(target)


if __name__ == '__main__':
    main()
