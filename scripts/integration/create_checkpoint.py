"""Local restore bundle for the Qt worker milestone, preserving all earlier checkpoints."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, check=True)


def main():
    assert not git('status', '--porcelain').stdout
    assert not git('remote').stdout.strip()
    head = git('rev-parse', 'HEAD').stdout.decode().strip()
    previous = '7846ebe98f0a09cecf83915c8102a6d46ce0ca1d'
    assert head != previous
    directory = ROOT/'build/checkpoints'
    directory.mkdir(parents=True, exist_ok=True)
    bundle = directory/f'FiscalOps_QtWorkers_{head[:12]}.bundle'
    if bundle.exists():
        raise SystemExit('Refusing to replace a checkpoint')
    git('bundle', 'create', str(bundle), '--all')
    checked = git('bundle', 'verify', str(bundle))
    record = {'checkpoint': head, 'previous_checkpoint': previous, 'bundle': bundle.name,
              'bytes': bundle.stat().st_size, 'sha256': hashlib.sha256(bundle.read_bytes()).hexdigest(),
              'verified': True, 'remote_count': 0, 'venv_included': False, 'exe_generated': False,
              'restore': 'git clone PATH_TO_BUNDLE NEW_EMPTY_DIRECTORY',
              'verification': (checked.stdout+checked.stderr).decode('utf-8', errors='replace')}
    (directory/'QT_WORKERS_RESTORE_POINT.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
