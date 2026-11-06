"""Complete, local Git restore bundle for the fiscal milestone; never replaces earlier checkpoints."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, check=True, capture_output=True)


def main():
    assert not git('status', '--porcelain').stdout, 'Commit the complete milestone before bundling'
    assert not git('remote').stdout.strip(), 'Local checkpoint only'
    commit = git('rev-parse', 'HEAD').stdout.decode().strip()
    previous = 'ec63d840231d64fc872552f9db3fb67c8d9b3485'
    assert commit != previous
    directory = ROOT/'build/checkpoints'
    directory.mkdir(parents=True, exist_ok=True)
    path = directory/f'FiscalOps_XML_Decimal_{commit[:12]}.bundle'
    if path.exists():
        raise SystemExit('Checkpoint already exists; refusing overwrite')
    git('bundle', 'create', str(path), '--all')
    verification = git('bundle', 'verify', str(path))
    record = {'checkpoint': commit, 'previous_checkpoint': previous, 'bundle': path.name,
              'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size,
              'verified': True, 'remote_count': 0, 'venv_included': False, 'exe_generated': False,
              'restore': 'git clone PATH_TO_BUNDLE NEW_EMPTY_DIRECTORY',
              'verification': (verification.stdout+verification.stderr).decode('utf-8', errors='replace')}
    (directory/'FISCAL_ENGINE_RESTORE_POINT.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
