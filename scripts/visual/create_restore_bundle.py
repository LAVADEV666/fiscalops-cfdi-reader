"""Create a local, self-contained Git restore bundle; never publish or overwrite."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, check=True, capture_output=True)


def main():
    commit = git('rev-parse', 'HEAD').stdout.decode().strip()
    source = git('show', 'HEAD:FiscalOps_CFDI_READER_SSGT_V21_1_PRO.html').stdout
    expected = '33eeed2334a683b5360c2fc4f9cabc26885be66fef8714e4278f97235b8c373b'
    assert hashlib.sha256(source).hexdigest() == expected
    assert not git('remote').stdout.strip(), 'This workflow expects no configured remotes'
    directory = ROOT / 'build/checkpoints'
    directory.mkdir(parents=True, exist_ok=True)
    bundle = directory / f'FiscalOps_Fase0_5_Fase1_{commit[:12]}.bundle'
    if bundle.exists():
        raise SystemExit('Refusing to overwrite an existing restore bundle')
    git('bundle', 'create', str(bundle), '--all')
    verification = git('bundle', 'verify', str(bundle))
    report = {'commit': commit, 'bundle': bundle.name, 'bytes': bundle.stat().st_size,
              'sha256': hashlib.sha256(bundle.read_bytes()).hexdigest(),
              'prototype_sha256': expected, 'bundle_verified': True,
              'restore_method': 'git clone PATH_TO_BUNDLE NEW_EMPTY_DESTINATION',
              'remote_count': 0, 'exe_built': False,
              'verification': (verification.stdout + verification.stderr).decode('utf-8', errors='replace')}
    (directory / 'RESTORE_POINT.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
