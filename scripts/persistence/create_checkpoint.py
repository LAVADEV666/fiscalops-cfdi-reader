"""Verified local restore point for the SQLite phase, without replacing prior bundles."""
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
    previous = '0b19884ea75875eb7c0208d18c18d62d86d89093'
    assert head != previous
    folder = ROOT/'build/checkpoints'
    folder.mkdir(parents=True, exist_ok=True)
    bundle = folder/f'FiscalOps_SQLite_{head[:12]}.bundle'
    assert not bundle.exists(), 'Refusing to replace a checkpoint'
    git('bundle', 'create', str(bundle), '--all')
    verified = git('bundle', 'verify', str(bundle))
    result = {'checkpoint': head, 'previous_checkpoint': previous, 'bundle': bundle.name,
              'bytes': bundle.stat().st_size, 'sha256': hashlib.sha256(bundle.read_bytes()).hexdigest(),
              'verified': True, 'user_database_included': False, 'remote_count': 0, 'exe_generated': False,
              'restore': 'git clone PATH_TO_BUNDLE NEW_EMPTY_DIRECTORY',
              'verification': (verified.stdout+verified.stderr).decode('utf-8', errors='replace')}
    (folder/'SQLITE_RESTORE_POINT.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
