"""Native history/backup contracts, crash rollback, cancellation and untrusted input."""
import base64
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'tests/fiscal')]
from fixtures import invoice
from app.desktop.fiscal_worker import FiscalStore, FiscalBridge
from app.desktop.maintenance import Maintenance, validate, read_only, file_hash
from app.desktop.persistence import digest
from app.desktop.imports import Cancelled


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.path = self.root/'active.sqlite3'
        self.backup = self.root/'respaldo ÁRBOL.sqlite3'
        self.event = threading.Event()
        self.store = FiscalStore(self.path)
        self.service = Maintenance(self.store)
        self.first = self.imported('116')

    def tearDown(self):
        self.service.close()
        self.store.repository.close()
        self.tmp.cleanup()

    def call(self, op, payload=None):
        return self.store.handle(op, payload or {}, 'job', self.event, lambda v: None)

    def imported(self, total):
        self.call('import.begin')
        self.call('import.file', {'name': 'synthetic.xml', 'base64': base64.b64encode(invoice(total=total)).decode()})
        self.call('import.prepare')
        return self.call('import.commit')['dataset_id']

    def snapshot(self):
        db = self.store.repository.db()
        return {table: db.execute('SELECT * FROM '+table+' ORDER BY 1,2').fetchall()
                for table in ('documents', 'sessions', 'inputs', 'fiscal_results', 'workspace')}

    def saved(self):
        return self.service.backup(self.backup, self.event, lambda v: None)

    def prepared(self):
        return self.service.prepare(self.backup, self.event, lambda v: None)

    def test_backup_is_verified_complete_and_independent(self):
        summary = self.saved()
        self.assertEqual((summary['sessions'], summary['documents'], summary['originals']), (1, 1, 1))
        self.assertEqual(summary['sha256'], file_hash(self.backup, self.event))
        self.imported('999')
        with closing(read_only(self.backup)) as db:
            self.assertEqual(validate(db, self.event)['documents'], 1)
            projection = json.loads(db.execute('SELECT projection_json FROM fiscal_results').fetchone()[0])
            self.assertEqual(projection['Total'], '116')

    def test_same_active_path_sidecars_and_hardlink_are_rejected(self):
        paths = [self.path, Path(str(self.path)+'-journal'), Path(str(self.path)+'-wal'), Path(str(self.path)+'-shm')]
        link = self.root/'alias.sqlite3'
        os.link(self.path, link)
        paths.append(link)
        for path in paths:
            with self.assertRaisesRegex(ValueError, 'BACKUP_PATH_IS_ACTIVE_DATABASE'):
                self.service.backup(path, self.event, lambda v: None)

    def test_failed_publish_preserves_existing_backup_and_live_database(self):
        self.backup.write_bytes(b'previous destination')
        before = self.snapshot()
        with patch('app.desktop.maintenance.os.replace', side_effect=PermissionError('simulated full/denied destination')):
            with self.assertRaisesRegex(ValueError, 'DATABASE_UNAVAILABLE'):
                self.saved()
        self.assertEqual(self.backup.read_bytes(), b'previous destination')
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(list(self.root.glob('.fiscalops-backup-*')))

    def test_cancel_backup_keeps_existing_destination(self):
        self.backup.write_bytes(b'previous')
        def cancel(value):
            self.event.set()
        with self.assertRaises(Cancelled):
            self.service.backup(self.backup, self.event, cancel)
        self.event.clear()
        self.assertEqual(self.backup.read_bytes(), b'previous')

    def test_restore_preview_and_discard_never_mutate_live_database(self):
        self.saved()
        self.imported('999')
        before = self.snapshot()
        plan = self.prepared()
        self.assertEqual((plan['sessions'], plan['documents']), (1, 1))
        self.assertEqual(self.snapshot(), before)
        self.service.discard(plan['token'])
        self.assertFalse(list(self.root.glob('.fiscalops-restore-*')))
        with self.assertRaisesRegex(ValueError, 'RESTORE_PLAN_UNKNOWN'):
            self.service.restore(plan['token'], self.event, lambda v: None)

    def test_restore_preserves_exact_rows_views_and_makes_preventive_backup(self):
        view = {'filters': {'q': 'ÁRBOL'}, 'columns': ['IVA', 'Total']}
        self.call('session.save', {'dataset_id': self.first, 'view': view})
        expected = self.snapshot()
        self.saved()
        second = self.imported('999')
        before = self.snapshot()
        plan = self.prepared()
        restored = self.service.restore(plan['token'], self.event, lambda v: None)
        after = self.snapshot()
        for table in ('documents', 'sessions', 'inputs', 'fiscal_results'):
            self.assertEqual(after[table], expected[table])
        self.assertGreater(after['workspace'][0][2], before['workspace'][0][2])
        self.assertEqual(self.call('session.resume')['dataset_id'], self.first)
        self.assertEqual(self.call('session.resume')['view'], view)
        with closing(read_only(Path(restored['recovery_path']))) as db:
            self.assertEqual(validate(db, self.event)['active_session'], second)
            self.assertEqual(db.execute('SELECT * FROM sessions ORDER BY 1,2').fetchall(), before['sessions'])

    def test_selected_source_may_change_but_reviewed_staging_is_used(self):
        self.saved()
        self.imported('999')
        plan = self.prepared()
        self.backup.write_bytes(b'source replaced after preview')
        self.service.restore(plan['token'], self.event, lambda v: None)
        self.assertEqual(self.call('session.resume')['dataset_id'], self.first)

    def test_changed_staging_is_rejected_without_replacement(self):
        self.saved()
        self.imported('999')
        plan = self.prepared()
        before = self.snapshot()
        self.service.plans[plan['token']]['staged'].write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'RESTORE_PLAN_CHANGED'):
            self.service.restore(plan['token'], self.event, lambda v: None)
        self.assertEqual(self.snapshot(), before)

    def test_cancel_inside_restore_rolls_back_every_table(self):
        self.saved()
        self.imported('999')
        plan = self.prepared()
        before = self.snapshot()
        def cancel(value):
            if value['label'] == 'Restaurando procedencia':
                self.event.set()
        with self.assertRaises(Cancelled):
            self.service.restore(plan['token'], self.event, cancel)
        self.event.clear()
        self.assertEqual(self.snapshot(), before)
        self.assertTrue(Path(self.service.last_recovery).exists())

    def test_failed_insert_restore_rolls_back_prior_deletes(self):
        self.saved()
        self.imported('999')
        plan = self.prepared()
        before = self.snapshot()
        # TEMP trigger is not in the source snapshot; inject only after preventive backup verification.
        backup = self.service.backup
        def inject(*args):
            result = backup(*args)
            self.store.repository.db().execute("CREATE TEMP TRIGGER fail_result BEFORE INSERT ON fiscal_results BEGIN SELECT RAISE(ABORT,'test write failure'); END")
            return result
        with patch.object(self.service, 'backup', inject):
            with self.assertRaisesRegex(ValueError, 'DATABASE_UNAVAILABLE'):
                self.service.restore(plan['token'], self.event, lambda v: None)
        self.assertEqual(self.snapshot(), before)

    def test_crash_during_restore_recovers_previous_database(self):
        self.saved()
        second = self.imported('999')
        before = self.snapshot()
        self.store.repository.close()
        script = '''import os,sys,threading
from app.desktop.fiscal_worker import FiscalStore
from app.desktop.maintenance import Maintenance
s=FiscalStore(sys.argv[1]);m=Maintenance(s);e=threading.Event();s.repository.db()
p=m.prepare(sys.argv[2],e,lambda v:None)
def progress(v):
 if v['label']=='Restaurando procedencia':os._exit(24)
m.restore(p['token'],e,progress)
'''
        result = subprocess.run([sys.executable, '-c', script, str(self.path), str(self.backup)], cwd=ROOT, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 24, result.stderr.decode(errors='replace'))
        self.assertEqual(self.call('session.resume')['dataset_id'], second)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.store.repository.db().execute('PRAGMA integrity_check').fetchone(), ('ok',))
        # This subprocess deliberately died before its normal staging cleanup.
        for path in self.root.glob('.fiscalops-restore-*'):
            path.unlink()

    def test_concurrent_change_invalidates_reviewed_plan(self):
        self.saved()
        plan = self.prepared()
        identity = self.imported('999')
        with self.assertRaisesRegex(ValueError, 'SESSION_CONFLICT_REOPEN'):
            self.service.restore(plan['token'], self.event, lambda v: None)
        self.assertEqual(self.call('session.resume')['dataset_id'], identity)

    def test_other_window_view_save_invalidates_plan(self):
        self.saved()
        plan = self.prepared()
        other = FiscalStore(self.path)
        try:
            other.handle('session.resume', {}, '', self.event, lambda v: None)
            other.handle('session.save', {'dataset_id': self.first, 'view': {'filters': {'q': 'latest'}}}, '', self.event, lambda v: None)
            with self.assertRaisesRegex(ValueError, 'SESSION_CONFLICT_REOPEN'):
                self.service.restore(plan['token'], self.event, lambda v: None)
        finally:
            other.repository.close()

    def test_empty_backup_restores_without_inventing_active_session(self):
        self.call('session.purge')
        self.saved()
        self.imported('999')
        plan = self.prepared()
        self.service.restore(plan['token'], self.event, lambda v: None)
        self.assertIsNone(self.call('session.resume')['dataset_id'])
        self.assertEqual(self.call('session.list')['sessions'], [])

    def test_untrusted_trigger_and_hash_tampering_are_rejected(self):
        self.saved()
        with closing(sqlite3.connect(self.backup)) as db:
            db.execute('CREATE TRIGGER foreign_trigger AFTER INSERT ON sessions BEGIN DELETE FROM documents; END')
            db.commit()
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'BACKUP_SCHEMA_INVALID'):
            self.prepared()
        self.assertEqual(self.snapshot(), before)
        self.saved()
        with closing(sqlite3.connect(self.backup)) as db:
            db.execute("UPDATE fiscal_results SET projection_json='{}'")
            db.commit()
        with self.assertRaisesRegex(ValueError, 'DOCUMENT_INTEGRITY_FAILED'):
            self.prepared()
        self.assertEqual(self.snapshot(), before)

    def test_foreign_corrupt_and_future_backups_leave_live_database_intact(self):
        before = self.snapshot()
        self.backup.write_bytes(b'not sqlite')
        with self.assertRaisesRegex(ValueError, 'DATABASE_UNAVAILABLE'):
            self.prepared()
        self.saved()
        with closing(sqlite3.connect(self.backup)) as db:
            db.execute('PRAGMA user_version=99')
        with self.assertRaisesRegex(ValueError, 'BACKUP_VERSION_UNSUPPORTED'):
            self.prepared()
        self.saved()
        with closing(sqlite3.connect(self.backup)) as db:
            db.execute('PRAGMA application_id=1')
        with self.assertRaisesRegex(ValueError, 'BACKUP_IDENTITY_INVALID'):
            self.prepared()
        self.assertEqual(self.snapshot(), before)

    def test_history_paginates_searches_and_marks_compatibility(self):
        db = self.store.repository.db()
        for index in range(55):
            db.execute("INSERT INTO sessions(id,created_at,rfc,engine_key,document_count,metadata_json,errors_json) VALUES(?,?,?,?,0,'[]','[]')",
                       ('test-'+str(index), f'2026-11-06T12:00:{index:02}Z', 'RFC_%' if index == 3 else 'TEST', 'old-version'))
        page1 = self.service.handle('native.history', {}, self.event, lambda v: None)
        page2 = self.service.handle('native.history', {'offset': 50}, self.event, lambda v: None)
        self.assertEqual((len(page1['sessions']), len(page2['sessions'])), (50, 6))
        self.assertTrue(page1['has_more'])
        self.assertFalse(page2['has_more'])
        ids = [r['dataset_id'] for p in (page1, page2) for r in p['sessions']]
        self.assertEqual(len(set(ids)), 56)
        result = self.service.handle('native.history', {'query': 'RFC_%'}, self.event, lambda v: None)['sessions']
        self.assertEqual(len(result), 1)
        self.assertFalse(result[0]['compatible'])
        self.assertTrue(any(r['active'] for r in page1['sessions']))

    def test_private_path_operations_are_not_webchannel_operations_or_slots(self):
        from PySide6.QtCore import QMetaMethod
        self.assertFalse(any(op.startswith('native.') for op in FiscalBridge.OPERATIONS))
        meta = FiscalBridge.staticMetaObject
        slots = {bytes(meta.method(i).name()).decode() for i in range(meta.methodOffset(), meta.methodCount())
                 if meta.method(i).methodType() == QMetaMethod.MethodType.Slot}
        self.assertEqual(slots, {'openJob', 'request', 'cancel'})

    def test_invalid_result_shapes_rejected_even_when_json_hash_is_recomputed(self):
        self.saved()
        before = self.snapshot()
        with closing(sqlite3.connect(self.backup)) as db:
            raw = db.execute('SELECT inspection_json FROM fiscal_results').fetchone()[0]
            result = json.loads(raw)
            result['document'] = []
            text = json.dumps(result)
            db.execute('UPDATE fiscal_results SET inspection_json=?,inspection_sha256=?', (text, digest(text)))
            db.commit()
        with self.assertRaisesRegex(ValueError, 'BACKUP_CONTENT_INVALID'):
            self.prepared()
        self.assertEqual(self.snapshot(), before)

    def test_invalid_incident_shape_rejected_without_mutating_database(self):
        self.saved()
        before = self.snapshot()
        with closing(sqlite3.connect(self.backup)) as db:
            db.execute("UPDATE sessions SET errors_json='[123]'")
            db.commit()
        with self.assertRaisesRegex(ValueError, 'BACKUP_CONTENT_INVALID'):
            self.prepared()
        self.assertEqual(self.snapshot(), before)


if __name__ == '__main__':
    unittest.main()
