"""Private native-Qt history and verified SQLite backup/restore, executed on the fiscal worker."""
from contextlib import closing
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import uuid

from .imports import Cancelled, checkpoint
from .persistence import Repository, APPLICATION_ID, SCHEMA_VERSION, database_errors, digest
from app.fiscal.ui_adapter import DETAIL_KEYS

MAX_RESTORE = 2*1024**3
TABLES = ('documents', 'sessions', 'inputs', 'fiscal_results')


def file_hash(path, cancel):
    import hashlib
    value = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1024*1024):
            checkpoint(cancel)
            value.update(block)
    return value.hexdigest()


def strict_json(value):
    def no_float(value):
        raise ValueError('BACKUP_CONTENT_INVALID')
    try:
        return json.loads(value, parse_float=no_float, parse_constant=no_float)
    except (ValueError, RecursionError, TypeError):
        raise ValueError('BACKUP_CONTENT_INVALID') from None


def read_only(path):
    db = sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True, timeout=.25, isolation_level=None)
    db.execute('PRAGMA query_only=ON')
    db.execute('PRAGMA trusted_schema=OFF')
    db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 128*1024*1024)
    return db


def schema(db):
    return [(kind, name, ''.join(sql.split()).lower()) for kind, name, sql in db.execute(
        "SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name")]


def validate(db, cancel, progress=lambda value: None, engine=None):
    db.set_progress_handler(lambda: int(cancel.is_set()), 1000)
    try:
        return _validate(db, cancel, progress, engine)
    except sqlite3.Error:
        if cancel.is_set():
            raise Cancelled() from None
        raise
    finally:
        db.set_progress_handler(None, 0)


def _validate(db, cancel, progress, engine):
    """Validate the complete snapshot without running its schema, fiscal code or XML."""
    checkpoint(cancel)
    if db.execute('PRAGMA user_version').fetchone()[0] != SCHEMA_VERSION:
        raise ValueError('BACKUP_VERSION_UNSUPPORTED')
    if db.execute('PRAGMA application_id').fetchone()[0] != APPLICATION_ID:
        raise ValueError('BACKUP_IDENTITY_INVALID')
    expected = Repository()
    try:
        if schema(db) != schema(expected.db()):
            raise ValueError('BACKUP_SCHEMA_INVALID')
    finally:
        expected.close()
    if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)] or db.execute('PRAGMA foreign_key_check').fetchone():
        raise ValueError('BACKUP_INTEGRITY_FAILED')
    workspace = db.execute('SELECT singleton,active_session,revision FROM workspace').fetchall()
    if len(workspace) != 1 or workspace[0][0] != 1 or type(workspace[0][2]) is not int or workspace[0][2] < 0:
        raise ValueError('BACKUP_CONTENT_INVALID')
    active, revision = workspace[0][1:]
    sessions, results, originals = 0, 0, 0
    for sha, size, actual in db.execute('SELECT sha256,byte_count,length(original) FROM documents'):
        checkpoint(cancel)
        if type(size) is not int or not 0 <= size <= 32*1024*1024 or size != actual:
            raise ValueError('BACKUP_CONTENT_INVALID')
        raw = db.execute('SELECT original FROM documents WHERE sha256=?', (sha,)).fetchone()[0]
        if not isinstance(raw, bytes) or digest(raw) != sha:
            raise ValueError('DOCUMENT_INTEGRITY_FAILED')
        originals += 1
        progress({'label': 'Verificando originales', 'done': originals, 'total': 0})
    for sid, rfc, key, count, meta, errors, view in db.execute(
            'SELECT id,rfc,engine_key,document_count,metadata_json,errors_json,view_json FROM sessions'):
        checkpoint(cancel)
        if not isinstance(sid, str) or not sid or not isinstance(rfc, str) or len(rfc) > 13 or not isinstance(key, str):
            raise ValueError('BACKUP_CONTENT_INVALID')
        if type(count) is not int or not 0 <= count <= 10000:
            raise ValueError('BACKUP_CONTENT_INVALID')
        records, incidents, state = strict_json(meta), strict_json(errors), strict_json(view)
        if (not isinstance(records, list) or any(not isinstance(r, dict) for r in records)
                or not isinstance(incidents, list) or any(not isinstance(r, dict) or r.get('_rowId') != f'{sid}:error:{i+1}' for i, r in enumerate(incidents))
                or not isinstance(state, dict) or len(view.encode('utf-8')) > 65536):
            raise ValueError('BACKUP_CONTENT_INVALID')
        if db.execute('SELECT count(*) FROM fiscal_results WHERE session_id=?', (sid,)).fetchone()[0] != count:
            raise ValueError('SESSION_INTEGRITY_FAILED')
        size = db.execute('SELECT COALESCE(SUM(d.byte_count),0) FROM inputs i JOIN documents d ON d.sha256=i.sha256 WHERE i.session_id=?', (sid,)).fetchone()[0]
        if size > 64*1024*1024:
            raise ValueError('BACKUP_CONTENT_INVALID')
        if sid == active and engine is not None and key != engine:
            raise ValueError('SESSION_ENGINE_MISMATCH')
        sessions += 1
    for doc_id, sha, inspection, ihash, projection, phash in db.execute(
            'SELECT document_id,sha256,inspection_json,inspection_sha256,projection_json,projection_sha256 FROM fiscal_results'):
        checkpoint(cancel)
        if digest(inspection) != ihash or digest(projection) != phash:
            raise ValueError('DOCUMENT_INTEGRITY_FAILED')
        value, row = strict_json(inspection), strict_json(projection)
        if (not isinstance(value, dict) or not isinstance(row, dict) or value.get('contract') != 'fiscalops.inspection/1'
                or not isinstance(value.get('document'), dict) or value['document'].get('sha256') != sha or row.get('SHA256') != sha
                or row.get('_docId') != doc_id or row.get('_rowId') != doc_id or not isinstance(row.get('_details'), dict)
                or set(row['_details']) != set(DETAIL_KEYS)
                or any(row.get(k) is not None and not isinstance(row[k], str) for k in ('Subtotal', 'Descuento', 'IVA', 'Retenciones', 'Total'))):
            raise ValueError('BACKUP_CONTENT_INVALID')
        raw = db.execute('SELECT original FROM documents WHERE sha256=?', (sha,)).fetchone()[0]
        try:
            raw.decode(value['document']['encoding'])
        except (UnicodeError, LookupError, KeyError):
            raise ValueError('BACKUP_CONTENT_INVALID') from None
        for name, rows in row['_details'].items():
            if not isinstance(rows, list) or any(not isinstance(r, dict) or r.get('_docId') != doc_id or
                    r.get('_rowId') != f'{doc_id}:{name}:{index+1}' for index, r in enumerate(rows)):
                raise ValueError('BACKUP_CONTENT_INVALID')
        results += 1
        progress({'label': 'Verificando resultados', 'done': results, 'total': 0})
    checkpoint(cancel)
    return {'sessions': sessions, 'documents': results, 'originals': originals, 'active_session': active, 'revision': revision}


def copy_database(source, target, cancel, progress):
    busy_since = [None]
    def update(status, remaining, total):
        checkpoint(cancel)
        if status in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
            busy_since[0] = busy_since[0] or time.monotonic()
            if time.monotonic()-busy_since[0] > 5:
                raise ValueError('DATABASE_BUSY')
        else:
            busy_since[0] = None
        progress({'label': 'Copiando SQLite', 'done': total-remaining, 'total': total})
    source.backup(target, pages=128, progress=update, sleep=.05)
    checkpoint(cancel)


class Maintenance:
    def __init__(self, store):
        self.store = store
        self.plans = {}
        self.last_recovery = None

    @property
    def repository(self):
        return self.store.repository

    def safe_path(self, value):
        path = Path(value).absolute()
        if path.is_symlink():
            raise ValueError('BACKUP_PATH_INVALID')
        if self.repository.path != ':memory:':
            active = Path(self.repository.path).resolve()
            if path.resolve() == active or str(path.resolve()) in {str(active)+s for s in ('-journal', '-wal', '-shm')}:
                raise ValueError('BACKUP_PATH_IS_ACTIVE_DATABASE')
            if path.exists() and active.exists() and os.path.samefile(path, active):
                raise ValueError('BACKUP_PATH_IS_ACTIVE_DATABASE')
        return path

    def backup(self, destination, cancel, progress):
        path = self.safe_path(destination)
        if not path.parent.is_dir():
            raise ValueError('BACKUP_DIRECTORY_MISSING')
        with database_errors():
            fd, temp = tempfile.mkstemp(prefix='.fiscalops-backup-', suffix='.sqlite3', dir=path.parent)
            os.close(fd)
            temp = Path(temp)
            try:
                with closing(sqlite3.connect(temp, isolation_level=None)) as output:
                    copy_database(self.repository.db(), output, cancel, progress)
                    summary = validate(output, cancel, progress)
                with temp.open('r+b') as stream:
                    os.fsync(stream.fileno())
                sha = file_hash(temp, cancel)
                checkpoint(cancel)
                os.replace(temp, path)
                return dict(summary, path=str(path), sha256=sha, bytes=path.stat().st_size)
            finally:
                temp.unlink(missing_ok=True)

    def prepare(self, source_path, cancel, progress):
        path = self.safe_path(source_path)
        if not path.is_file() or path.stat().st_size > MAX_RESTORE:
            raise ValueError('RESTORE_FILE_LIMIT')
        root = Path(self.repository.path).absolute().parent if self.repository.path != ':memory:' else Path(tempfile.gettempdir())
        root.mkdir(parents=True, exist_ok=True)
        fd, temp = tempfile.mkstemp(prefix='.fiscalops-restore-', suffix='.sqlite3', dir=root)
        os.close(fd)
        staged = Path(temp)
        try:
            with database_errors(), closing(read_only(path)) as source:
                # Validate before backup so a foreign trigger/view is never trusted or executed.
                source.execute('BEGIN')
                validate(source, cancel, progress, self.repository.engine)
                with closing(sqlite3.connect(staged, isolation_level=None)) as target:
                    copy_database(source, target, cancel, progress)
                    summary = validate(target, cancel, progress, self.repository.engine)
                source.execute('ROLLBACK')
            token = uuid.uuid4().hex
            self.close()
            self.plans[token] = {'staged': staged, 'sha256': file_hash(staged, cancel), 'summary': summary,
                                 'expected_revision': self.repository.db().execute('SELECT revision FROM workspace WHERE singleton=1').fetchone()[0]}
            return dict(summary, token=token, name=path.name, sha256=self.plans[token]['sha256'])
        except BaseException:
            staged.unlink(missing_ok=True)
            raise

    def restore(self, token, cancel, progress):
        self.last_recovery = None
        plan = self.plans.get(token)
        if plan is None:
            raise ValueError('RESTORE_PLAN_UNKNOWN')
        if file_hash(plan['staged'], cancel) != plan['sha256']:
            raise ValueError('RESTORE_PLAN_CHANGED')
        repo = self.repository
        expected = plan['expected_revision']
        if repo.revision != expected:
            raise ValueError('SESSION_CONFLICT_REOPEN')
        if repo.path == ':memory:':
            raise ValueError('RESTORE_REQUIRES_PERSISTENT_DATABASE')
        folder = Path(repo.path).absolute().parent/'backups'
        folder.mkdir(exist_ok=True)
        recovery = folder/('before_restore_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'_'+uuid.uuid4().hex[:12]+'.sqlite3')
        before = self.backup(recovery, cancel, progress)
        self.last_recovery = str(recovery)
        if before['revision'] != expected:
            raise ValueError('SESSION_CONFLICT_REOPEN')
        db = repo.db()
        attached = False
        try:
            with database_errors():
                db.execute('ATTACH DATABASE ? AS restore_source', (str(plan['staged']),))
                attached = True
                # SQLite's rollback journal protects the entire replacement, including process death.
                with repo.transaction():
                    if db.execute('SELECT revision FROM workspace WHERE singleton=1').fetchone()[0] != expected:
                        raise ValueError('SESSION_CONFLICT_REOPEN')
                    db.set_progress_handler(lambda: int(cancel.is_set()), 1000)
                    db.execute('UPDATE workspace SET active_session=NULL WHERE singleton=1')
                    db.execute('DELETE FROM sessions')
                    db.execute('DELETE FROM documents')
                    for table in TABLES:
                        checkpoint(cancel)
                        label = ('originales', 'sesiones', 'procedencia', 'resultados fiscales')[TABLES.index(table)]
                        progress({'label': 'Restaurando '+label, 'done': TABLES.index(table), 'total': len(TABLES)})
                        db.execute(f'INSERT INTO main.{table} SELECT * FROM restore_source.{table}')
                    db.execute('UPDATE workspace SET active_session=?,revision=? WHERE singleton=1',
                               (plan['summary']['active_session'], expected+1))
                    checkpoint(cancel)
                    db.set_progress_handler(None, 0)
                    if db.execute('PRAGMA foreign_key_check').fetchone():
                        raise ValueError('BACKUP_INTEGRITY_FAILED')
        except ValueError:
            if cancel.is_set():
                raise Cancelled() from None
            raise
        finally:
            db.set_progress_handler(None, 0)
            if attached:
                db.execute('DETACH DATABASE restore_source')
        repo.revision = expected+1
        self.store.datasets.clear()
        self.store.staging.clear()
        self.store.active_dataset = None
        self.discard(token)
        return {'restored': True, 'recovery_path': str(recovery), 'sessions': plan['summary']['sessions'],
                'documents': plan['summary']['documents'], 'active_session': plan['summary']['active_session']}

    def discard(self, token):
        plan = self.plans.pop(token, None)
        if plan:
            plan['staged'].unlink(missing_ok=True)
        return {'discarded': True}

    def close(self):
        for token in list(self.plans):
            self.discard(token)

    def handle(self, operation, payload, cancel, progress):
        checkpoint(cancel)
        if operation == 'native.enter':
            snapshot = payload.get('snapshot')
            if snapshot:
                self.store.handle('session.save', snapshot, '', cancel, lambda value: None)
            return {'ready': True}
        if operation == 'native.history':
            offset, query = payload.get('offset', 0), str(payload.get('query', ''))[:128]
            if type(offset) is not int or offset < 0:
                raise ValueError('PAGE_OFFSET_INVALID')
            with database_errors():
                pattern = '%'+query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')+'%'
                sql = " FROM sessions WHERE rfc LIKE ? ESCAPE '\\' OR id LIKE ? ESCAPE '\\' OR created_at LIKE ? ESCAPE '\\'"
                db = self.repository.db()
                data = db.execute('SELECT id,created_at,rfc,document_count,engine_key'+sql+' ORDER BY created_at DESC,id LIMIT 51 OFFSET ?', (pattern, pattern, pattern, offset)).fetchall()
                active = db.execute('SELECT active_session FROM workspace').fetchone()[0]
            return {'sessions': [{'dataset_id': r[0], 'created_at': r[1], 'rfc': r[2], 'documents': r[3], 'compatible': r[4] == self.repository.engine, 'active': r[0] == active} for r in data[:50]],
                    'has_more': len(data) > 50, 'offset': offset}
        if operation == 'native.open':
            return self.store.handle('session.open', payload, '', cancel, lambda value: None)
        if operation == 'native.backup':
            return self.backup(payload['path'], cancel, progress)
        if operation == 'native.restore.prepare':
            return self.prepare(payload['path'], cancel, progress)
        if operation == 'native.restore.commit':
            return self.restore(payload['token'], cancel, progress)
        if operation == 'native.restore.discard':
            return self.discard(payload['token'])
        raise ValueError('OPERATION_UNKNOWN')
