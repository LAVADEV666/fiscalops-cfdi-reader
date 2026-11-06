"""Bind evidence to the exact current application sources, without including customer data."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def source_hashes():
    paths = [p for folder in ('app/desktop', 'app/fiscal', 'app/ui') for p in (ROOT/folder).glob('*')
             if p.is_file() and p.suffix in ('.py', '.js', '.html')]
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
