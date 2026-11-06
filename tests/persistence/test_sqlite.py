"""SQLite phase: recovery, precision, transactional failure and historical report contracts."""
import base64
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'tests/fiscal')]
from fixtures import invoice
from app.desktop.fiscal_worker import FiscalStore
from app.desktop.imports import Cancelled
from app.desktop.persistence import Repository, APPLICATION_ID, dumps
from app.desktop.reports import REPORTS, report_rows


class SQLiteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/'data'/'fiscalops.sqlite3'
        self.stores = []
        self.event = threading.Event()
        self.store = self.new()

    def tearDown(self):
        for store in self.stores:
            store.repository.close()
        self.temp.cleanup()

    def new(self):
        store = FiscalStore(self.path)
        self.stores.append(store)
        return store

    def call(self, op, data=None, store=None):
        return (store or self.store).handle(op, data or {}, 'job', self.event, lambda value: None)

    def prepare(self, files=None):
        self.call('import.begin', {'rfc': 'AAA010101AAA'})
        for name, raw in files or [('one.xml', invoice())]:
            self.call('import.file', {'name': name, 'base64': base64.b64encode(raw).decode()})
        return self.call('import.prepare')['dataset_id']

    def imported(self, files=None):
        identity = self.prepare(files)
        self.call('import.commit')
        return identity

    def reopen(self):
        self.store.repository.close()
        self.store = self.new()
        return self.call('session.resume')

    def sql(self, query):
        return self.store.repository.db().execute(query).fetchall()

    def test_connection_is_lazy_and_initializes_versioned_schema(self):
        self.assertFalse(self.path.exists())
        self.assertIsNone(self.store.repository.connection)
        self.assertIsNone(self.call('session.resume')['dataset_id'])
        self.assertEqual(self.sql('PRAGMA user_version'), [(1,)])
        self.assertEqual(self.sql('PRAGMA application_id'), [(APPLICATION_ID,)])
        self.assertEqual(self.sql('PRAGMA foreign_keys'), [(1,)])
        self.assertEqual(self.sql('PRAGMA synchronous'), [(2,)])
        self.assertEqual(self.sql('PRAGMA journal_mode'), [('delete',)])
        self.assertIsNone(self.reopen()['dataset_id'])

    def test_reopen_preserves_original_utf16_and_all_report_identities(self):
        raw = invoice().decode().replace('encoding="UTF-8"', 'encoding="UTF-16"').encode('utf-16')
        identity = self.imported([("quote'; DROP TABLE documents;--.xml", raw)])
        before = self.store.datasets[identity]
        expected = {report: report_rows(before, report, before['rows']) for report in REPORTS}
        self.assertEqual(self.reopen()['dataset_id'], identity)
        after = self.store.datasets[identity]
        self.assertEqual(expected, {report: report_rows(after, report, after['rows']) for report in REPORTS})
        self.assertEqual(self.sql('SELECT original FROM documents'), [(raw,)])
        self.assertEqual(self.sql('PRAGMA foreign_key_check'), [])

    def test_decimal_null_zero_and_analyses_survive_reopen(self):
        names = ['p0_iva_ieps_40.xml', 'p0_local_once_40.xml', 'p0_isr_retention_40.xml', 'p0_missing_subtotal_40.xml']
        identity = self.imported([(n, (ROOT/'tests/fiscal/fixtures'/n).read_bytes()) for n in names])
        ids = [r['_docId'] for r in self.store.datasets[identity]['rows']]
        payload = {'dataset_id': identity, 'document_ids': ids[:3]}
        expected = self.call('report.aggregate', payload)
        self.reopen()
        self.assertEqual(expected, self.call('report.aggregate', payload))
        rows = self.store.datasets[identity]['rows']
        self.assertEqual([r['Total'] for r in rows[:3]], ['124', '119', '90'])
        self.assertEqual(rows[2]['IVA'], '0')
        self.assertIsNone(rows[3]['Subtotal'])
        stored = json.loads(self.sql('SELECT inspection_json FROM fiscal_results ORDER BY position')[2][0])
        self.assertEqual(stored['document']['numbers']['Total']['value'], '90')
        with self.assertRaises(TypeError):
            dumps({'Total': 0.1})

    def test_exact_csv_txt_xlsx_selected_order_after_reopen(self):
        identity = self.imported([('one.xml', invoice()), ('two.xml', invoice(total='117'))])
        ids = [r['_docId'] for r in self.store.datasets[identity]['rows']][::-1]
        payload = {'dataset_id': identity, 'document_ids': ids, 'row_ids': ids, 'report': 'summary',
                   'columns': [{'id': 'Total', 'label': 'Total', 'dataType': 'currency'}, {'id': 'Descuento', 'label': 'Descuento'}],
                   'analyses': ['resumen', 'monedas', 'mensual', 'contrapartes', 'pagos', 'impuestos', 'conceptos']}
        expected = {kind: self.call('report.export', dict(payload, format=kind)) for kind in ('csv', 'txt', 'xlsx')}
        self.reopen()
        for kind in expected:
            actual = self.call('report.export', dict(payload, format=kind))
            self.assertEqual(actual['row_ids'], ids)
            if kind != 'xlsx':
                self.assertEqual(actual, expected[kind])
            else:
                with zipfile.ZipFile(io.BytesIO(base64.b64decode(actual['base64']))) as archive:
                    self.assertIsNone(archive.testzip())
                    self.assertEqual(len([n for n in archive.namelist() if n.startswith('xl/worksheets/')]), 8)
                    self.assertIn(b'<v>117</v>', archive.read('xl/worksheets/sheet1.xml'))

    def test_duplicates_keep_instances_deduplicate_only_source_bytes(self):
        raw = (ROOT/'tests/fiscal/fixtures/p0_iva_ieps_40.xml').read_bytes()
        # The fixture has no stamp; give this duplicate test an explicit local UUID.
        raw = raw.replace(b'</cfdi:Comprobante>', b'<cfdi:Complemento><t:TimbreFiscalDigital xmlns:t="http://www.sat.gob.mx/TimbreFiscalDigital" Version="1.1" UUID="11111111-1111-4111-8111-111111111111"/></cfdi:Complemento></cfdi:Comprobante>')
        first = self.imported([('a.xml', raw), ('b.xml', raw)])
        second = self.imported([('c.xml', raw)])
        self.assertNotEqual(first, second)
        self.assertEqual(self.sql('SELECT count(*) FROM documents'), [(1,)])
        self.assertEqual(self.sql('SELECT count(*) FROM inputs'), [(3,)])
        self.assertEqual(self.sql('SELECT count(*) FROM fiscal_results'), [(3,)])
        self.reopen()
        self.call('session.open', {'dataset_id': first})
        self.assertEqual(len(self.store.datasets[first]['rows']), 2)
        self.assertIn('UUID_DUPLICADO', self.store.datasets[first]['rows'][1]['ObservacionesXML'])

    def test_incidents_and_local_metadata_recover_without_reinterpretation(self):
        meta = ('Uuid~EstadoComprobante~FechaCancelacion\n11111111-1111-4111-8111-111111111111~0~2026-11-06\n').encode()
        identity = self.imported([('ok.xml', invoice()), ('bad.xml', b'<bad'), ('metadata.txt', meta)])
        before = self.store.datasets[identity]
        self.assertTrue(before['errors'])
        self.reopen()
        self.assertEqual(before, self.store.datasets[identity])
        self.assertEqual(self.sql('SELECT count(*) FROM inputs'), [(3,)])
        self.assertTrue(self.sql('SELECT metadata_json FROM sessions')[0][0])

    def test_view_state_and_rfc_survive_reopen(self):
        identity = self.imported()
        view = {'report': 'concepts', 'columns': ['Descripcion', 'Importe'], 'filters': {'q': 'ÁRBOL', 'ps': '30'}, 'page': 1}
        self.call('session.save', {'dataset_id': identity, 'view': view})
        actual = self.reopen()
        self.assertEqual(actual['view'], view)
        self.assertEqual(actual['rfc'], 'AAA010101AAA')
        self.assertEqual(actual['documents'], 1)

    def test_oversized_view_and_stale_session_cannot_overwrite(self):
        identity = self.imported()
        with self.assertRaisesRegex(ValueError, 'SESSION_VIEW_INVALID'):
            self.call('session.save', {'dataset_id': identity, 'view': {'q': 'x'*65536}})
        with self.assertRaisesRegex(ValueError, 'DATASET_STALE'):
            self.call('session.save', {'dataset_id': 'forged', 'view': {}})
        self.assertEqual(self.reopen()['view'], {})

    def test_prepared_uncommitted_load_never_replaces_previous_session(self):
        first = self.imported()
        self.prepare([('new.xml', invoice(total='999'))])
        self.assertEqual(self.reopen()['dataset_id'], first)
        self.assertEqual(self.sql('SELECT count(*) FROM sessions'), [(1,)])
        self.assertEqual(self.sql('SELECT count(*) FROM documents'), [(1,)])

    def test_cancel_during_sql_transaction_rolls_back_all_rows_and_active_pointer(self):
        first = self.imported()
        self.prepare([('new.xml', invoice(total='999'))])
        original = __import__('app.desktop.persistence', fromlist=['checkpoint']).checkpoint
        count = [0]
        def cancel_inside(event):
            count[0] += 1
            if count[0] == 3:
                event.set()
            original(event)
        with patch('app.desktop.persistence.checkpoint', cancel_inside):
            with self.assertRaises(Cancelled):
                self.call('import.commit')
        self.event.clear()
        self.assertEqual(self.reopen()['dataset_id'], first)
        self.assertEqual(self.sql('SELECT count(*) FROM documents'), [(1,)])
        self.assertEqual(self.sql('SELECT count(*) FROM fiscal_results'), [(1,)])

    def test_injected_sql_write_failure_rolls_back_without_publishing(self):
        first = self.imported()
        self.prepare([('new.xml', invoice(total='999'))])
        self.store.repository.db().execute("CREATE TEMP TRIGGER fail_result BEFORE INSERT ON fiscal_results BEGIN SELECT RAISE(ABORT,'simulated write failure'); END")
        with self.assertRaisesRegex(ValueError, 'DATABASE_UNAVAILABLE'):
            self.call('import.commit')
        self.assertEqual(self.store.active_dataset, first)
        self.assertEqual(self.reopen()['dataset_id'], first)
        self.assertEqual(self.sql('SELECT count(*) FROM sessions'), [(1,)])

    def test_process_crash_mid_transaction_recovers_previous_commit(self):
        first = self.imported()
        self.store.repository.close()
        code = '''import os,base64,threading,sys
from app.desktop.fiscal_worker import FiscalStore
s=FiscalStore(sys.argv[1]); e=threading.Event()
def call(op,p=None): return s.handle(op,p or {},'crash',e,lambda v:None)
call('import.begin'); call('import.file',{'name':'new.xml','base64':sys.argv[2]});call('import.prepare')
s.repository._activate=lambda db,identity:os._exit(23)
call('import.commit')
'''
        result = subprocess.run([sys.executable, '-c', code, str(self.path), base64.b64encode(invoice(total='999')).decode()], cwd=ROOT, timeout=30, capture_output=True)
        self.assertEqual(result.returncode, 23, result.stderr.decode(errors='replace'))
        self.assertEqual(self.reopen()['dataset_id'], first)
        self.assertEqual(self.sql('PRAGMA integrity_check'), [('ok',)])
        self.assertEqual(self.sql('SELECT count(*) FROM sessions'), [(1,)])

    def test_busy_database_fails_bounded_and_preserves_report(self):
        first = self.imported()
        self.prepare([('new.xml', invoice(total='999'))])
        lock = sqlite3.connect(self.path, isolation_level=None)
        try:
            lock.execute('BEGIN IMMEDIATE')
            with self.assertRaisesRegex(ValueError, 'DATABASE_BUSY'):
                self.call('import.commit')
            self.assertEqual(self.store.active_dataset, first)
        finally:
            lock.close()
        self.assertEqual(self.reopen()['dataset_id'], first)

    def test_concurrent_windows_cannot_silently_replace_active_session(self):
        first = self.imported()
        second = self.new()
        self.call('session.resume', store=second)
        latest = self.imported([('new.xml', invoice(total='999'))])
        with self.assertRaisesRegex(ValueError, 'SESSION_CONFLICT_REOPEN'):
            self.call('session.save', {'dataset_id': first, 'view': {'report': 'concepts'}}, second)
        with self.assertRaisesRegex(ValueError, 'SESSION_CONFLICT_REOPEN'):
            self.call('dataset.clear', store=second)
        self.assertEqual(self.reopen()['dataset_id'], latest)

    def test_clear_deactivates_but_history_can_be_opened_and_purge_removes_all(self):
        first = self.imported()
        self.call('dataset.clear')
        self.assertIsNone(self.reopen()['dataset_id'])
        self.assertEqual(self.call('session.list')['sessions'][0]['dataset_id'], first)
        self.call('session.open', {'dataset_id': first})
        self.assertEqual(self.reopen()['dataset_id'], first)
        self.call('session.purge')
        self.assertIsNone(self.reopen()['dataset_id'])
        self.assertEqual(self.call('session.list')['sessions'], [])
        for table in ('sessions', 'documents', 'inputs', 'fiscal_results'):
            self.assertEqual(self.sql('SELECT count(*) FROM '+table), [(0,)])

    def test_tampered_original_and_projection_are_rejected(self):
        self.imported()
        db = self.store.repository.db()
        db.execute("UPDATE documents SET original=x'00'")
        with self.assertRaisesRegex(ValueError, 'DOCUMENT_INTEGRITY_FAILED'):
            self.reopen()
        db = self.store.repository.db()
        db.execute('UPDATE documents SET original=?', (invoice(),))
        db.execute("UPDATE fiscal_results SET projection_json='{}'")
        with self.assertRaisesRegex(ValueError, 'DOCUMENT_INTEGRITY_FAILED'):
            self.reopen()

    def test_engine_mismatch_blocks_reuse_without_deleting_history(self):
        identity = self.imported()
        self.store.repository._engine = 'different-version'
        with self.assertRaisesRegex(ValueError, 'SESSION_ENGINE_MISMATCH'):
            self.call('session.resume')
        self.assertEqual(self.sql('SELECT id FROM sessions'), [(identity,)])

    def test_newer_schema_is_never_downgraded(self):
        self.imported()
        self.store.repository.db().execute('PRAGMA user_version=99')
        self.store.repository.close()
        before = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'DATABASE_SCHEMA_NEWER'):
            self.reopen()
        self.assertEqual(self.path.read_bytes(), before)

    def test_foreign_or_corrupt_database_is_not_replaced(self):
        self.path.parent.mkdir()
        self.path.write_bytes(b'not a sqlite database')
        before = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'DATABASE_UNAVAILABLE'):
            self.call('session.resume')
        self.assertEqual(self.path.read_bytes(), before)
        self.path.unlink()
        db = sqlite3.connect(self.path)
        db.execute('CREATE TABLE unrelated(id)')
        db.commit()
        db.close()
        before = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'DATABASE_IDENTITY_INVALID'):
            self.call('session.resume')
        self.assertEqual(self.path.read_bytes(), before)

    def test_connection_cannot_be_used_from_another_thread(self):
        self.call('session.resume')
        observed = []
        def other():
            try:
                self.store.repository.db()
            except ValueError as exc:
                observed.append(str(exc))
        worker = threading.Thread(target=other)
        worker.start()
        worker.join()
        self.assertEqual(observed, ['DATABASE_THREAD_VIOLATION'])


if __name__ == '__main__':
    unittest.main()
