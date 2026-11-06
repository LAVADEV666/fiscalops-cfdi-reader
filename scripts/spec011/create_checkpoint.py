"""Create a local complete Git bundle for SPEC011, without replacing old bundles."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT=Path(__file__).resolve().parents[2]


def git(*args):return subprocess.run(['git',*args],cwd=ROOT,check=True,capture_output=True)


def main():
    assert not git('remote').stdout.strip()
    commit=git('rev-parse','HEAD').stdout.decode().strip()
    previous=git('rev-parse','spec011-start-20261106').stdout.decode().strip()
    assert commit!=previous,'Commit SPEC011 before creating its bundle'
    directory=ROOT/'build/checkpoints'
    directory.mkdir(parents=True,exist_ok=True)
    bundle=directory/f'FiscalOps_SPEC011_{commit[:12]}.bundle'
    if bundle.exists():raise SystemExit('Refusing to replace a checkpoint bundle')
    git('bundle','create',str(bundle),'--all')
    checked=git('bundle','verify',str(bundle))
    result={'checkpoint':commit,'previous_checkpoint':previous,'bundle':bundle.name,
            'bytes':bundle.stat().st_size,'sha256':hashlib.sha256(bundle.read_bytes()).hexdigest(),
            'bundle_verified':True,'restore':'git clone PATH_TO_BUNDLE NEW_EMPTY_DIRECTORY',
            'venv_included':False,'exe_generated':False,'remote_count':0,
            'verification':(checked.stdout+checked.stderr).decode('utf-8',errors='replace')}
    (directory/'SPEC011_RESTORE_POINT.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
