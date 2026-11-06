"""Worker-owned SQLite repository. No SQL, paths or connection crosses WebChannel."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import threading

from app.fiscal.models import to_data
from .imports import checkpoint

SCHEMA_VERSION = 1
APPLICATION_ID = 0x464F5053
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE = ROOT/'FiscalOpsData'/'fiscalops.sqlite3'


def dumps(value):
    return json.dumps(to_data(value), ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode('utf-8')).hexdigest()


def engine_key():
    """Version both arithmetic and projections, including the pinned normative manifest."""
    paths = sorted((ROOT/'app/fiscal').glob('*.py'))+[ROOT/'resources/sat/manifest.json']
    return digest(b''.join(p.name.encode()+b'\0'+p.read_bytes()+b'\0' for p in paths))


@contextmanager
def database_errors():
    try:
        yield
    except sqlite3.Error as exc:
        code = getattr(exc, 'sqlite_errorcode', 0) & 0xFF
        name = 'DATABASE_BUSY' if code in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED) else 'DATABASE_UNAVAILABLE'
        raise ValueError(name) from None
    except OSError:
        raise ValueError('DATABASE_UNAVAILABLE') from None


class Repository:
    def __init__(self, path=':memory:'):
        self.path = str(path)
        self.connection = None
        self.owner_thread = None
        self.revision = None
        self._engine = None

    @property
    def engine(self):
        if self._engine is None:
            self._engine = engine_key()
        return self._engine

    def db(self):
        if self.connection is not None:
            if self.owner_thread != threading.get_ident():
                raise ValueError('DATABASE_THREAD_VIOLATION')
            return self.connection
        with database_errors():
            if self.path != ':memory:':
                Path(self.path).parent.mkdir(parents=True, exist_ok=True)
            db = sqlite3.connect(self.path, timeout=.25, isolation_level=None)
            try:
                db.execute('PRAGMA foreign_keys=ON')
                db.execute('PRAGMA trusted_schema=OFF')
                version = db.execute('PRAGMA user_version').fetchone()[0]
                identity = db.execute('PRAGMA application_id').fetchone()[0]
                tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                if version > SCHEMA_VERSION:
                    raise ValueError('DATABASE_SCHEMA_NEWER')
                if version < 0:
                    raise ValueError('DATABASE_IDENTITY_INVALID')
                if (version == 0 and (identity or tables)) or (version and identity != APPLICATION_ID):
                    raise ValueError('DATABASE_IDENTITY_INVALID')
                # A local rollback journal avoids depending on a long-lived WAL beside portable data.
                db.execute('PRAGMA journal_mode=DELETE')
                db.execute('PRAGMA synchronous=FULL')
                if version == 0:
                    db.execute('BEGIN IMMEDIATE')
                    for sql in (
                        '''CREATE TABLE documents(sha256 TEXT PRIMARY KEY, original BLOB NOT NULL,
                           byte_count INTEGER NOT NULL CHECK(byte_count>=0))''',
                        '''CREATE TABLE sessions(id TEXT PRIMARY KEY, created_at TEXT NOT NULL,
                           rfc TEXT NOT NULL, engine_key TEXT NOT NULL, document_count INTEGER NOT NULL,
                           metadata_json TEXT NOT NULL, errors_json TEXT NOT NULL, view_json TEXT NOT NULL DEFAULT '{}')''',
                        '''CREATE TABLE inputs(session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                           position INTEGER NOT NULL, sha256 TEXT NOT NULL REFERENCES documents(sha256),
                           filename TEXT NOT NULL, entry_name TEXT NOT NULL, PRIMARY KEY(session_id,position))''',
                        '''CREATE TABLE fiscal_results(document_id TEXT PRIMARY KEY,
                           session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                           position INTEGER NOT NULL, sha256 TEXT NOT NULL REFERENCES documents(sha256),
                           inspection_json TEXT NOT NULL, inspection_sha256 TEXT NOT NULL,
                           projection_json TEXT NOT NULL, projection_sha256 TEXT NOT NULL,
                           UNIQUE(session_id,position))''',
                        'CREATE INDEX results_session ON fiscal_results(session_id,position)',
                        '''CREATE TABLE workspace(singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                           active_session TEXT REFERENCES sessions(id), revision INTEGER NOT NULL)''',
                        'INSERT INTO workspace VALUES(1,NULL,0)',
                    ):
                        db.execute(sql)
                    db.execute(f'PRAGMA application_id={APPLICATION_ID}')
                    db.execute(f'PRAGMA user_version={SCHEMA_VERSION}')
                    db.execute('COMMIT')
                if db.execute('PRAGMA quick_check').fetchone() != ('ok',) or db.execute('PRAGMA foreign_key_check').fetchone():
                    raise ValueError('DATABASE_INTEGRITY_FAILED')
                self.revision = db.execute('SELECT revision FROM workspace WHERE singleton=1').fetchone()[0]
            except BaseException:
                db.close()
                raise
        self.connection, self.owner_thread = db, threading.get_ident()
        return db

    @contextmanager
    def transaction(self):
        with database_errors():
            db = self.db()
            db.execute('BEGIN IMMEDIATE')
            try:
                yield db
                db.execute('COMMIT')
            except BaseException:
                db.execute('ROLLBACK')
                raise

    def _activate(self, db, identity):
        updated = db.execute('UPDATE workspace SET active_session=?,revision=revision+1 WHERE singleton=1 AND revision=?',
                             (identity, self.revision)).rowcount
        if updated != 1:
            raise ValueError('SESSION_CONFLICT_REOPEN')

    def commit(self, stage, cancel):
        with self.transaction() as db:
            checkpoint(cancel)
            db.execute('INSERT INTO sessions(id,created_at,rfc,engine_key,document_count,metadata_json,errors_json) VALUES(?,?,?,?,?,?,?)',
                       (stage['id'], datetime.now(timezone.utc).isoformat(), stage['rfc'], self.engine,
                        len(stage['rows']), dumps(stage['metadata']), dumps(stage['errors'])))
            for index, item in enumerate(stage['inputs']):
                checkpoint(cancel)
                sha = digest(item['raw'])
                db.execute('INSERT OR IGNORE INTO documents VALUES(?,?,?)', (sha, item['raw'], len(item['raw'])))
                # Never trust a same-hash record blindly (e.g. damaged existing storage).
                existing = db.execute('SELECT original,byte_count FROM documents WHERE sha256=?', (sha,)).fetchone()
                if existing != (item['raw'], len(item['raw'])):
                    raise ValueError('DOCUMENT_INTEGRITY_FAILED')
                db.execute('INSERT INTO inputs VALUES(?,?,?,?,?)', (stage['id'], index, sha, item['filename'], item['entry']))
            for index, row in enumerate(stage['rows']):
                checkpoint(cancel)
                projection = dumps({k: v for k, v in row.items() if k not in ('XMLRaw', '_XMLRaw')})
                inspection = dumps(stage['inspections'][row['_docId']])
                db.execute('INSERT INTO fiscal_results VALUES(?,?,?,?,?,?,?,?)',
                           (row['_docId'], stage['id'], index, row['SHA256'], inspection, digest(inspection), projection, digest(projection)))
            self._activate(db, stage['id'])
            checkpoint(cancel)
        self.revision += 1

    def active(self):
        with database_errors():
            row = self.db().execute('SELECT active_session,revision FROM workspace WHERE singleton=1').fetchone()
            self.revision = row[1]
            return row[0]

    def load(self, identity, cancel):
        with database_errors():
            db = self.db()
            # A read transaction keeps originals/results/view coherent if another window writes.
            db.execute('BEGIN')
            try:
                session = db.execute('SELECT rfc,engine_key,document_count,errors_json,view_json FROM sessions WHERE id=?', (identity,)).fetchone()
                if not session:
                    raise ValueError('SESSION_UNKNOWN')
                if session[1] != self.engine:
                    raise ValueError('SESSION_ENGINE_MISMATCH')
                rows = []
                for doc_id, sha, inspection, i_hash, projection, p_hash, raw, size in db.execute(
                    '''SELECT r.document_id,r.sha256,r.inspection_json,r.inspection_sha256,r.projection_json,
                       r.projection_sha256,d.original,d.byte_count FROM fiscal_results r JOIN documents d
                       ON d.sha256=r.sha256 WHERE r.session_id=? ORDER BY r.position''', (identity,)):
                    checkpoint(cancel)
                    if digest(raw) != sha or len(raw) != size or digest(inspection) != i_hash or digest(projection) != p_hash:
                        raise ValueError('DOCUMENT_INTEGRITY_FAILED')
                    row, result = json.loads(projection), json.loads(inspection)
                    if row['_docId'] != doc_id or row['SHA256'] != sha or result['document']['sha256'] != sha:
                        raise ValueError('DOCUMENT_INTEGRITY_FAILED')
                    row['XMLRaw'] = raw.decode(result['document']['encoding']).lstrip('\ufeff')
                    rows.append(row)
                if len(rows) != session[2]:
                    raise ValueError('SESSION_INTEGRITY_FAILED')
                dataset = {'id': identity, 'rows': rows, 'errors': json.loads(session[3]), 'rfc': session[0], 'view': json.loads(session[4])}
                checkpoint(cancel)
            finally:
                db.execute('ROLLBACK')
            return dataset

    def list_sessions(self, offset=0):
        if type(offset) is not int or offset < 0:
            raise ValueError('PAGE_OFFSET_INVALID')
        with database_errors():
            rows = self.db().execute('SELECT id,created_at,rfc,document_count FROM sessions ORDER BY created_at DESC,id LIMIT 50 OFFSET ?', (offset,)).fetchall()
        return [{'dataset_id': r[0], 'created_at': r[1], 'rfc': r[2], 'documents': r[3]} for r in rows]

    def activate(self, identity):
        with self.transaction() as db:
            self._activate(db, identity)
        self.revision += 1

    def save_view(self, identity, value):
        if not isinstance(value, dict) or len(dumps(value).encode('utf-8')) > 65536:
            raise ValueError('SESSION_VIEW_INVALID')
        # Session UI state is never merged into fiscal rows or used as SQL.
        with self.transaction() as db:
            active = db.execute('SELECT active_session,revision FROM workspace WHERE singleton=1').fetchone()
            if active != (identity, self.revision):
                raise ValueError('SESSION_CONFLICT_REOPEN')
            db.execute('UPDATE sessions SET view_json=? WHERE id=?', (dumps(value), identity))

    def clear(self, purge=False):
        with self.transaction() as db:
            self._activate(db, None)
            if purge:
                db.execute('DELETE FROM sessions')
                db.execute('DELETE FROM documents')
        self.revision += 1

    def close(self):
        if self.connection is not None:
            self.db().close()
            self.connection = None
