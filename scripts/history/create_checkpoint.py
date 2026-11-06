"""Create a new verified local bundle for the history/backup milestone."""
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
    previous = 'ec95bbbb05c4eed81856b034c01e02b8ac5e7b4e'
    assert head != previous
    folder = ROOT/'build/checkpoints'
    folder.mkdir(parents=True, exist_ok=True)
    bundle = folder/f'FiscalOps_HistoryBackups_{head[:12]}.bundle'
    assert not bundle.exists()
    git('bundle', 'create', str(bundle), '--all')
    checked = git('bundle', 'verify', str(bundle))
    record = {'checkpoint': head, 'previous_checkpoint': previous, 'bundle': bundle.name,
              'bytes': bundle.stat().st_size, 'sha256': hashlib.sha256(bundle.read_bytes()).hexdigest(),
              'verified': True, 'user_database_included': False, 'remote_count': 0, 'exe_generated': False,
              'restore': 'git clone PATH_TO_BUNDLE NEW_EMPTY_DIRECTORY',
              'verification': (checked.stdout+checked.stderr).decode('utf-8', errors='replace')}
    (folder/'HISTORY_BACKUPS_RESTORE_POINT.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
