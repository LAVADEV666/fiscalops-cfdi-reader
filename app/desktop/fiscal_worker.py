"""Worker-owned fiscal datasets; queued Qt transport never performs parsing on the GUI thread."""
import base64
import binascii
import json
from pathlib import Path
import threading
import time
import uuid
from PySide6.QtCore import QObject, QThread, Signal, Slot, Qt
from app.fiscal.service import inspect_invoice
from app.fiscal.sources import SatSources
from app.fiscal.security import XmlRejected
from app.fiscal.ui_adapter import adapt_inspection
from app.fiscal.models import to_data
from .imports import MAX_FILE, Cancelled, checkpoint, entries, metadata
from .reports import aggregate, analysis_sheets, report_rows, selected_documents, columns, money_formats
from .exports import build_delimited, build_workbook
from .persistence import Repository, DEFAULT_DATABASE


class FiscalStore:
    """Selected source bytes and persistent snapshots, owned exclusively by the worker."""
    def __init__(self, database_path=':memory:'):
        self.repository = Repository(database_path)
        self.sources = None
        self.staging = {}
        self.datasets = {}
        self.active_dataset = None

    def error(self, stage, filename, entry, code):
        stage['errors'].append({'_rowId': stage['id']+':error:'+str(len(stage['errors'])+1),
                                'ErrorIndice': len(stage['errors'])+1, 'Archivo': filename,
                                'Entrada': entry, 'Etapa': 'LECTURA NATIVA', 'MensajeError': code})

    def handle(self, operation, payload, job_id, cancel, progress):
        checkpoint(cancel)
        if operation == 'session.resume':
            identity = self.repository.active()
            if identity is None:
                return {'dataset_id': None, 'persistent': self.repository.path != ':memory:'}
            dataset = self.repository.load(identity, cancel)
            self.datasets[identity] = dataset
            self.active_dataset = identity
            return self._session_info(dataset)
        if operation == 'session.list':
            return {'sessions': self.repository.list_sessions(payload.get('offset', 0))}
        if operation == 'session.open':
            identity = payload.get('dataset_id')
            if not isinstance(identity, str):
                raise ValueError('SESSION_UNKNOWN')
            dataset = self.repository.load(identity, cancel)
            checkpoint(cancel)
            self.repository.activate(identity)
            self.datasets = {identity: dataset}
            self.active_dataset = identity
            return self._session_info(dataset)
        if operation == 'session.save':
            identity = payload.get('dataset_id')
            if identity != self.active_dataset or identity is None:
                raise ValueError('DATASET_STALE_OR_UNKNOWN')
            self.repository.save_view(identity, payload.get('view'))
            return {'saved': True, 'dataset_id': identity}
        if operation == 'session.purge':
            self.repository.clear(purge=True)
            self.datasets.clear()
            self.staging.clear()
            self.active_dataset = None
            return {'purged': True}
        if operation == 'dataset.page':
            dataset = self.datasets.get(payload.get('dataset_id'))
            if dataset is None:
                raise ValueError('DATASET_STALE_OR_UNKNOWN')
            return self._page(dataset, payload, cancel)
        if operation == 'import.begin':
            self.repository.db()  # Fail explicitly before reading inputs when persistence is unavailable.
            # An unfinished import is never reusable as a cached or committed dataset.
            self.staging = {key: value for key, value in self.staging.items() if not value['cancel'].is_set()}
            if self.staging:
                raise ValueError('IMPORT_ALREADY_ACTIVE')
            self.staging[job_id] = {'id': uuid.uuid4().hex, 'rows': [], 'metadata': [], 'errors': [], 'files': 0, 'source_bytes': 0, 'rfc': str(payload.get('rfc', '')).upper()[:13],
                                    'cancel': cancel, 'prepared': False, 'inputs': [], 'inspections': {}}
            return {'job_id': job_id}
        if operation.startswith('import.'):
            if job_id not in self.staging:
                raise ValueError('IMPORT_JOB_UNKNOWN')
            stage = self.staging[job_id]
            if operation == 'import.reject':
                self.error(stage, str(payload.get('name', ''))[:1024], '', 'FILE_BYTE_LIMIT')
                stage['files'] += 1
                return {'processed': stage['files'], 'documents': len(stage['rows']), 'metadata': len(stage['metadata']), 'errors': len(stage['errors'])}
            if operation == 'import.file':
                if stage['prepared']:
                    raise ValueError('IMPORT_ALREADY_PREPARED')
                name, encoded = payload.get('name'), payload.get('base64')
                if not isinstance(name, str) or len(name) > 1024 or not isinstance(encoded, str) or len(encoded) > (MAX_FILE+2)//3*4:
                    raise ValueError('IMPORT_FILE_LIMIT')
                try:
                    data = base64.b64decode(encoded, validate=True)
                except (ValueError, binascii.Error):
                    raise ValueError('IMPORT_BASE64_INVALID') from None
                if len(data) > MAX_FILE:
                    raise ValueError('IMPORT_FILE_LIMIT')
                for entry, raw, error in entries(data, name, cancel):
                    checkpoint(cancel)
                    if error:
                        self.error(stage, name, entry, error)
                        continue
                    stage['source_bytes'] += len(raw)
                    if stage['source_bytes'] > 64*1024*1024:
                        raise ValueError('IMPORT_SESSION_BYTE_LIMIT')
                    stage['inputs'].append({'raw': raw, 'filename': name, 'entry': entry})
                    try:
                        parsed_meta = None if entry.lower().endswith('.xml') else metadata(raw)
                        if parsed_meta is not None:
                            records, incidents = parsed_meta
                            for item in records:
                                item['filename'] = name
                            stage['metadata'].extend(records)
                            for code in incidents:
                                self.error(stage, name, entry, code)
                        else:
                            self.sources = self.sources or SatSources()  # lazy, on the worker thread
                            inspection = inspect_invoice(raw, sources=self.sources)
                            checkpoint(cancel)
                            row = adapt_inspection(inspection, uuid.uuid4().hex, name+(' / '+entry if entry != name else ''))
                            stage['rows'].append(row)
                            stage['inspections'][row['_docId']] = to_data(inspection)
                            if len(stage['rows']) > 10_000:
                                raise ValueError('IMPORT_DOCUMENT_LIMIT')
                    except XmlRejected as exc:
                        self.error(stage, name, entry, exc.code)
                    except (ValueError, OSError, UnicodeError) as exc:
                        if str(exc) == 'IMPORT_DOCUMENT_LIMIT':
                            raise
                        self.error(stage, name, entry, 'IMPORT_'+type(exc).__name__.upper())
                    progress({'processed': stage['files'], 'documents': len(stage['rows']), 'errors': len(stage['errors'])})
                stage['files'] += 1
                result = {'processed': stage['files'], 'documents': len(stage['rows']), 'metadata': len(stage['metadata']), 'errors': len(stage['errors'])}
                progress(result)
                return result
            if operation == 'import.prepare':
                self._prepare(stage, cancel)
                return {'dataset_id': stage['id'], 'documents': len(stage['rows']), 'errors': len(stage['errors']), 'metadata': len(stage['metadata'])}
            if operation == 'import.page':
                if not stage['prepared']:
                    raise ValueError('IMPORT_NOT_PREPARED')
                return self._page(stage, payload, cancel)
            if operation == 'import.commit':
                if not stage['prepared']:
                    raise ValueError('IMPORT_NOT_PREPARED')
                checkpoint(cancel)
                self.repository.commit(stage, cancel)
                dataset = {'id': stage['id'], 'rows': stage['rows'], 'errors': stage['errors'], 'rfc': stage['rfc'], 'view': {}}
                self.datasets[stage['id']] = dataset
                self.active_dataset = stage['id']
                while len(self.datasets) > 2:
                    self.datasets.pop(next(iter(self.datasets)))
                self.staging.pop(job_id)
                return {'dataset_id': dataset['id'], 'committed': True}
            raise ValueError('IMPORT_OPERATION_UNKNOWN')
        if operation == 'dataset.clear':
            self.repository.clear()
            self.datasets.clear()
            self.staging.clear()
            self.active_dataset = None
            return {'cleared': True}
        identity = payload.get('dataset_id')
        if identity not in self.datasets:
            raise ValueError('DATASET_STALE_OR_UNKNOWN')
        dataset = self.datasets[identity]
        docs = selected_documents(dataset, payload.get('document_ids', []))
        if operation == 'report.aggregate':
            groups = aggregate(docs)
            return {'dataset_id': identity, 'groups': groups, 'money_formats': money_formats(groups)}
        if operation == 'report.export':
            report = payload.get('report', 'summary')
            rows = report_rows(dataset, report, docs, payload.get('row_ids'))
            cols = payload.get('columns', [])
            kind = payload.get('format', 'xlsx')
            if kind in ('txt', 'csv'):
                data = build_delimited(rows, cols, kind, cancel)
                mime = 'text/csv;charset=utf-8' if kind == 'csv' else 'text/plain;charset=utf-8'
                sheet_count = 1
            elif kind == 'xlsx':
                context = payload.get('context', {})
                context['column_count'] = len(cols)
                sheets = [{'name': 'Reporte', 'rows': rows, 'cols': cols}]
                sheets.extend(analysis_sheets(docs, rows, payload.get('analyses', []), payload.get('rfc', ''), context,
                                              payload.get('concept_columns') or columns([('UUID', 'UUID'), ('ConceptoIndice', 'Concepto'), ('Descripcion', 'Descripción'), ('Importe', 'Importe', 'currency')])))
                data = build_workbook(sheets, cancel)
                mime, sheet_count = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', len(sheets)
            else:
                raise ValueError('EXPORT_FORMAT_UNKNOWN')
            checkpoint(cancel)
            return {'base64': base64.b64encode(data).decode('ascii'), 'mime': mime,
                    'name': 'FiscalOps_'+report+'.'+kind, 'rows': len(rows), 'sheets': sheet_count,
                    'document_ids': payload['document_ids'], 'row_ids': [r['_rowId'] for r in rows]}
        raise ValueError('OPERATION_UNKNOWN')

    def _session_info(self, dataset):
        return {'dataset_id': dataset['id'], 'documents': len(dataset['rows']), 'errors': len(dataset['errors']),
                'rfc': dataset['rfc'], 'view': dataset['view'], 'persistent': self.repository.path != ':memory:'}

    def _page(self, dataset, payload, cancel):
        offset = payload.get('offset', 0)
        if type(offset) is not int or offset < 0:
            raise ValueError('PAGE_OFFSET_INVALID')
        count, size = 0, 0
        length = max(len(dataset['rows']), len(dataset['errors']))
        for index in range(offset, min(offset+50, length)):
            checkpoint(cancel)
            pair = [items[index] for items in (dataset['rows'], dataset['errors']) if index < len(items)]
            estimate = len(json.dumps(pair, ensure_ascii=False).encode('utf-8'))
            if count and size+estimate > 2*1024*1024:
                break
            count += 1
            size += estimate
        rows = dataset['rows'][offset:offset+count]
        return {'rows': rows, 'errors': dataset['errors'][offset:offset+count], 'money_formats': money_formats(rows),
                'next': offset+count, 'done': offset+count >= length}

    def _prepare(self, stage, cancel):
        if stage['prepared']:
            return
        by_uuid, seen = {}, {}
        for record in stage['metadata']:
            by_uuid.setdefault(record['Uuid'], []).append(record)
        for row in stage['rows']:
            checkpoint(cancel)
            identifier = row.get('UUID', '').upper()
            rfc = stage['rfc']
            row['Clasificacion'] = ('PAGO' if row.get('TipoDeComprobante') == 'P' else 'NOMINA' if row.get('TipoDeComprobante') == 'N'
                                    else 'SIN_RFC_EMPRESA' if not rfc else 'INGRESO' if row.get('RFCEmisor', '').upper() == rfc
                                    else 'EGRESO' if row.get('RFCReceptor', '').upper() == rfc else 'NO_RELACIONADO')
            records = by_uuid.get(identifier, [])
            states = {(r['EstatusTexto'], r['FechaCancelacion']) for r in records}
            row['EstatusSAT'] = next(iter(states))[0] if len(states) == 1 else 'DESCONOCIDO' if states else 'SIN METADATA'
            row['FechaCancelacionSAT'] = next(iter(states))[1] if len(states) == 1 else ''
            row['EstatusSATMetadata'], row['FechaCancelacionMetadata'] = row['EstatusSAT'], row['FechaCancelacionSAT']
            row['FuenteEstatusSAT'] = 'METADATA LOCAL; NO CONSULTA SAT' if records else 'SIN METADATA'
            for values in row['_details'].values():
                for item in values:
                    item['EstatusSAT'], item['FechaCancelacionSAT'] = row['EstatusSAT'], row['FechaCancelacionSAT']
            for code, condition in [('METADATA_CONFLICTO', len(states) > 1), ('UUID_DUPLICADO', identifier and identifier in seen)]:
                if condition:
                    findings = row['_details']['findings']
                    findings.append({'_docId': row['_docId'], '_rowId': row['_docId']+':findings:'+str(len(findings)+1),
                                     'UUID': row['UUID'], 'Fecha': row['Fecha'], 'TipoDeComprobante': row.get('TipoDeComprobante'),
                                     'HallazgoIndice': len(findings)+1, 'Severidad': 'ADVERTENCIA', 'CategoriaRegla': 'CONSISTENCIA LOCAL',
                                     'CodigoHallazgo': code, 'MensajeHallazgo': code, 'ReferenciaRegla': 'Identidad/contenido y fuentes locales; no consulta SAT', 'Diferencia': None})
                    row['ObservacionesXML'] += ('|' if row['ObservacionesXML'] else '')+code
                    if row['ResultadoValidacion'] != 'ERROR':
                        row['ResultadoValidacion'] = row['EstatusXML'] = 'REVISAR'
            row['HallazgosConteo'] = len(row['_details']['findings'])
            if identifier:
                seen[identifier] = row['SHA256']
        status = {r['UUID'].upper(): r['EstatusSAT'] for r in stage['rows'] if r['UUID']}
        for row in stage['rows']:
            for relation in row['_details']['relations']:
                relation['EstadoRelacionadoLocal'] = status.get((relation.get('UUIDRelacionado') or '').upper(), 'NO DISPONIBLE')
        stage['prepared'] = True


class FiscalWorker(QObject):
    result = Signal(str, str, str)
    progress = Signal(str, str)

    def __init__(self, database_path=DEFAULT_DATABASE):
        super().__init__()
        self.store = FiscalStore(database_path)
        self.thread_ids = set()

    @Slot(object)
    def handle(self, packet):
        request_id, job_id, operation, raw, cancel = packet
        self.thread_ids.add(threading.get_ident())
        try:
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError('PAYLOAD_OBJECT_REQUIRED')
            last_progress = [0.0, -1]
            def progress(value):
                now = time.monotonic()
                if now-last_progress[0] >= .1 or value['processed'] != last_progress[1]:
                    last_progress[:] = [now, value['processed']]
                    self.progress.emit(job_id, json.dumps(value))
            result = self.store.handle(operation, payload, job_id, cancel, progress)
            response = {'request_id': request_id, 'ok': True, 'result': to_data(result)}
        except Cancelled:
            self.store.staging.pop(job_id, None)
            response = {'request_id': request_id, 'ok': False, 'code': 'CANCELLED'}
        except (ValueError, TypeError, KeyError, OSError) as exc:
            code = str(exc) if isinstance(exc, ValueError) and str(exc).isupper() and len(str(exc)) < 100 else 'FISCAL_OPERATION_REJECTED'
            response = {'request_id': request_id, 'ok': False, 'code': code}
        except Exception:
            response = {'request_id': request_id, 'ok': False, 'code': 'FISCAL_WORKER_FAILED'}
        self.result.emit(request_id, operation, json.dumps(response, ensure_ascii=False))

    @Slot()
    def stop(self):
        try:
            self.store.repository.close()
        finally:
            QThread.currentThread().quit()


class _DeliveryQueue(QObject):
    """Private GUI-thread receiver/dispatcher, never registered with QWebChannel."""
    send = Signal(object)
    stop = Signal()

    def __init__(self, receiver, parent):
        super().__init__(parent)
        self.receiver = receiver

    @Slot(str, str, str)
    def receive(self, request_id, operation, response):
        self.receiver(request_id, operation, response)


class FiscalBridge(QObject):
    response = Signal(str)
    progress = Signal(str, str)
    downloadStatus = Signal(str)
    OPERATIONS = {'import.begin', 'import.file', 'import.reject', 'import.prepare', 'import.page', 'import.commit', 'dataset.clear', 'dataset.page',
                  'session.resume', 'session.list', 'session.open', 'session.save', 'session.purge', 'report.aggregate', 'report.export'}

    def __init__(self, parent=None, database_path=DEFAULT_DATABASE):
        super().__init__(parent)
        self.thread = QThread(self)
        self.thread.setObjectName('FiscalOps-Decimal-Worker')
        self.worker = FiscalWorker(database_path)
        self.worker.moveToThread(self.thread)
        self._delivery = _DeliveryQueue(self._received, self)
        self._delivery.send.connect(self.worker.handle, Qt.ConnectionType.QueuedConnection)
        self._delivery.stop.connect(self.worker.stop, Qt.ConnectionType.QueuedConnection)
        self.worker.result.connect(self._delivery.receive, Qt.ConnectionType.QueuedConnection)
        self.worker.progress.connect(self.progress, Qt.ConnectionType.QueuedConnection)
        self.thread.finished.connect(self.worker.deleteLater)
        self.jobs, self.pending = {}, {}
        self.closing = False
        self.gui_thread_id = threading.get_ident()
        self.thread.start()

    @Slot(str, result=str)
    def openJob(self, kind):
        if self.closing or kind not in ('import', 'export') or len(self.jobs) >= 16:
            return json.dumps({'ok': False, 'code': 'JOB_REJECTED'})
        identity = uuid.uuid4().hex
        self.jobs[identity] = {'event': threading.Event(), 'kind': kind, 'state': 'open'}
        return json.dumps({'ok': True, 'job_id': identity})

    @Slot(str, str, str, str, result=str)
    def request(self, request_id, job_id, operation, payload):
        if (self.closing or operation not in self.OPERATIONS or len(request_id) > 96 or not request_id or
                request_id in self.pending or len(self.pending) >= 16 or len(payload) > 46*1024*1024):
            return json.dumps({'ok': False, 'code': 'REQUEST_REJECTED'})
        job = self.jobs.get(job_id) if job_id else None
        if operation.startswith('import.') or operation == 'report.export':
            if not job or job['kind'] != ('import' if operation.startswith('import.') else 'export') or job['state'] != 'open':
                return json.dumps({'ok': False, 'code': 'JOB_UNKNOWN_OR_CLOSED'})
        event = job['event'] if job else threading.Event()
        self.pending[request_id] = (job_id, operation, event)
        self._delivery.send.emit((request_id, job_id, operation, payload, event))
        return json.dumps({'ok': True})

    @Slot(str, result=str)
    def cancel(self, job_id):
        job = self.jobs.get(job_id)
        if not job or job['state'] != 'open':
            return json.dumps({'ok': False, 'code': 'JOB_ALREADY_FINISHED'})
        job['event'].set()
        job['state'] = 'cancelled'
        self.jobs.pop(job_id, None)
        return json.dumps({'ok': True, 'cancelled': True})

    def _received(self, request_id, operation, response):
        if request_id == 'close-session-view':
            self.close_save_result = json.loads(response)
        packet = self.pending.pop(request_id, None)
        if packet:
            job_id = packet[0]
            if operation in ('import.commit', 'report.export') or self.jobs.get(job_id, {}).get('state') == 'cancelled':
                self.jobs.pop(job_id, None)
        self.response.emit(response)

    def shutdown(self, snapshot=None):
        self.closing = True
        for job in self.jobs.values():
            job['event'].set()
        for _, _, event in self.pending.values():
            event.set()
        self.thread.requestInterruption()
        if snapshot is not None:
            # Queued after cancellation of in-flight jobs and before connection closure.
            self._delivery.send.emit(('close-session-view', '', 'session.save', json.dumps(snapshot), threading.Event()))
        self._delivery.stop.emit()
