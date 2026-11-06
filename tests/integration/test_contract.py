"""Independent expectations for native adapters, selections, cancellation and export bytes."""
import base64
from decimal import Decimal, localcontext, ROUND_DOWN
import io
import json
from pathlib import Path
import struct
import sys
import threading
import unittest
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'tests/fiscal')]
from fixtures import invoice, concept, tax
from app.desktop.fiscal_worker import FiscalStore
from app.desktop.imports import entries, Cancelled
from app.desktop.reports import report_rows, aggregate
from app.desktop.exports import build_workbook, build_delimited


class NativeContractTests(unittest.TestCase):
    def setUp(self):
        self.store = FiscalStore()
        self.event = threading.Event()
        self.job = 'test-job'

    def tearDown(self):
        self.store.repository.close()

    def call(self, op, payload=None):
        return self.store.handle(op, payload or {}, self.job, self.event, lambda value: None)

    def imported(self, files):
        self.call('import.begin')
        for name, data in files:
            self.call('import.file', {'name': name, 'base64': base64.b64encode(data).decode()})
        self.call('import.prepare')
        rows = self.call('import.page')['rows']
        identity = self.call('import.commit')['dataset_id']
        return {'dataset_id': identity, 'document_ids': [r['_docId'] for r in rows]}, rows

    def sample(self, name):
        return (ROOT/'tests/fiscal/fixtures'/name).read_bytes()

    def test_p0_summary_details_and_single_source(self):
        selected, rows = self.imported([(name, self.sample(name)) for name in ('p0_iva_ieps_40.xml', 'p0_local_once_40.xml', 'p0_isr_retention_40.xml')])
        self.assertEqual([r['IVA'] for r in rows], ['16', '16', '0'])
        self.assertEqual([r['Retenciones'] for r in rows], ['0', '0', '10'])
        self.assertEqual([r['DiferenciaCalculada'] for r in rows], ['0.00']*3)
        result = self.call('report.aggregate', selected)['groups'][0]
        self.assertEqual((result['IVA'], result['Retenciones'], result['Total']), ('32', '10', '333'))
        self.assertEqual(rows[0]['_details']['conceptTaxes'][0]['Importe'], '16')
        self.assertEqual(rows[1]['_details']['globalTaxes'][-1]['NivelImpuesto'], 'LOCAL')

    def test_absent_and_invalid_not_zero_in_ui_or_aggregate(self):
        selected, rows = self.imported([('missing.xml', self.sample('p0_missing_subtotal_40.xml'))])
        self.assertIsNone(rows[0]['Subtotal'])
        self.assertIsNone(rows[0]['TotalRecalculado'])
        self.assertIsNone(self.call('report.aggregate', selected)['groups'][0]['Subtotal'])

    def test_exempt_zero_distinct_in_all_columns(self):
        _, rows = self.imported([('exempt.xml', self.sample('p0_exempt_zero_40.xml'))])
        self.assertEqual((rows[0]['IVA Exento Base'], rows[0]['IVA Trasladado 0 Base']), ('100', '100.00'))
        self.assertIsNone(rows[0]['_details']['conceptTaxes'][0]['Importe'])
        self.assertEqual(rows[0]['_details']['conceptTaxes'][1]['Importe'], '0')

    def test_group_rounding_exact_after_native_projection(self):
        selected, rows = self.imported([('round.xml', self.sample('round_groups_40.xml'))])
        self.assertEqual(rows[0]['IVA'], '0.03')
        self.assertEqual(self.call('report.aggregate', selected)['groups'][0]['Total'], '0.24')

    def test_multiple_currencies_not_combined(self):
        selected, _ = self.imported([('mxn.xml', invoice()), ('usd.xml', invoice(currency='USD'))])
        groups = self.call('report.aggregate', selected)['groups']
        self.assertEqual([(r['Moneda'], r['Total']) for r in groups], [('MXN', '116'), ('USD', '116')])

    def test_report_export_cannot_accept_forged_or_stale_rows(self):
        selected, _ = self.imported([('one.xml', invoice())])
        with self.assertRaisesRegex(ValueError, 'SELECTION_STALE'):
            self.call('report.aggregate', dict(selected, document_ids=['forged']))
        with self.assertRaisesRegex(ValueError, 'REPORT_ROW_SELECTION'):
            self.call('report.export', dict(selected, report='summary', row_ids=['forged'], columns=[{'id': 'Total'}]))
        with self.assertRaisesRegex(ValueError, 'DATASET_STALE'):
            self.call('report.aggregate', dict(selected, dataset_id='wrong'))

    def test_export_order_and_columns_share_selection(self):
        selected, rows = self.imported([('one.xml', invoice()), ('two.xml', invoice(total='117'))])
        chosen = dict(selected, document_ids=[rows[1]['_docId'], rows[0]['_docId']], row_ids=[rows[1]['_rowId'], rows[0]['_rowId']],
                      format='csv', report='summary', columns=[{'id': 'Total', 'label': 'Total'}, {'id': 'IVA', 'label': 'IVA'}])
        result = self.call('report.export', chosen)
        text = base64.b64decode(result['base64']).decode('utf-8-sig')
        self.assertEqual(text, '"Total","IVA"\r\n"117","16"\r\n"116","16"\r\n')
        self.assertEqual(result['row_ids'], chosen['row_ids'])

    def test_all_seven_analysis_sheets_use_exact_decimals(self):
        selected, _ = self.imported([('one.xml', self.sample('p0_iva_ieps_40.xml'))])
        result = self.call('report.export', dict(selected, report='summary', columns=[{'id': 'IVA', 'label': 'IVA', 'dataType': 'currency'}],
                    analyses=['resumen', 'monedas', 'mensual', 'contrapartes', 'pagos', 'impuestos', 'conceptos']))
        self.assertEqual(result['sheets'], 8)
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(result['base64']))) as archive:
            self.assertIsNone(archive.testzip())
            for filename in archive.namelist():
                if filename.endswith('.xml') or filename.endswith('.rels'):
                    ET.fromstring(archive.read(filename))
            self.assertIn(b'<v>16</v>', archive.read('xl/worksheets/sheet1.xml'))
            self.assertIn(b'<v>8</v>', archive.read('xl/worksheets/sheet7.xml'))  # IEPS in tax analysis
            self.assertIn(b'Generado', archive.read('xl/worksheets/sheet2.xml'))
            self.assertIn(b'FiscalOps V21', archive.read('docProps/core.xml'))
            self.assertIn(b'FiscalOps V21', archive.read('docProps/app.xml'))

    def test_csv_txt_zero_null_and_formula_safety(self):
        selected, rows = self.imported([('one.xml', self.sample('p0_isr_retention_40.xml'))])
        for kind in ('csv', 'txt'):
            result = self.call('report.export', dict(selected, format=kind, report='summary', columns=[{'id': 'IVA', 'label': 'IVA'}, {'id': 'Descuento', 'label': 'Descuento'}]))
            text = base64.b64decode(result['base64']).decode('utf-8-sig')
            self.assertIn('"0",""' if kind == 'csv' else '0~', text)
        data = build_delimited([{'x': '=1+1'}], [{'id': 'x'}], 'csv', self.event)
        self.assertIn(b"'=1+1", data)

    def test_large_excel_amount_remains_exact_text(self):
        data = build_workbook([{'name': 'Reporte', 'rows': [{'x': '999999999999999999.12'}],
                                'cols': [{'id': 'x', 'dataType': 'currency'}]}], self.event)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            sheet = archive.read('xl/worksheets/sheet1.xml')
            self.assertIn(b'999999999999999999.12', sheet)
            self.assertIn(b't="inlineStr"', sheet)
            self.assertNotIn(b'<v>999999', sheet)

    def test_export_rejects_xml_controls_instead_of_corrupting_xlsx(self):
        with self.assertRaisesRegex(ValueError, 'EXPORT_XML_CONTROL_CHARACTER'):
            build_workbook([{'name': 'Reporte', 'rows': [{'x': 'a\x01b'}], 'cols': [{'id': 'x'}]}], self.event)

    def test_cancel_preserves_committed_dataset(self):
        selected, _ = self.imported([('one.xml', invoice())])
        previous = self.store.active_dataset
        self.job = 'second'
        self.call('import.begin')
        self.call('import.file', {'name': 'other.xml', 'base64': base64.b64encode(invoice(total='999')).decode()})
        self.event.set()
        with self.assertRaises(Cancelled):
            self.call('import.prepare')
        self.assertEqual(self.store.active_dataset, previous)
        self.event.clear()
        self.assertEqual(self.call('report.aggregate', selected)['groups'][0]['Total'], '116')

    def test_prepared_rows_not_activated_until_commit(self):
        self.call('import.begin')
        self.call('import.file', {'name': 'one.xml', 'base64': base64.b64encode(invoice()).decode()})
        self.call('import.prepare')
        self.assertIsNone(self.store.active_dataset)
        self.assertEqual(len(self.call('import.page')['rows']), 1)
        self.call('import.commit')
        self.assertIsNotNone(self.store.active_dataset)

    def test_xml_dtd_failure_is_incident_and_next_file_still_imports(self):
        selected, rows = self.imported([('bad.xml', b'<!DOCTYPE a><a/>'), ('good.xml', invoice())])
        errors = self.store.datasets[selected['dataset_id']]['errors']
        self.assertEqual(len(rows), 1)
        self.assertEqual(errors[0]['MensajeError'], 'XML_DTD_FORBIDDEN')

    def test_zip_crc_rejected_and_valid_entries_accounted(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED) as archive:
            archive.writestr('bad.xml', b'<x/>')
            archive.writestr('good.xml', invoice())
        data = bytearray(stream.getvalue())
        length, extra = struct.unpack_from('<HH', data, 26)
        data[30+length+extra] ^= 1
        selected, rows = self.imported([('inputs.zip', bytes(data))])
        self.assertEqual(len(rows), 1)
        self.assertEqual(self.store.datasets[selected['dataset_id']]['errors'][0]['MensajeError'], 'ZIP_CRC_OR_STREAM_REJECTED')

    def test_zip_limits_paths_methods_and_no_extraction(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as archive:
            archive.writestr('../escape.xml', invoice())
            archive.writestr('nested.zip', b'not-a-zip')
            archive.writestr('method.xml', invoice(), compress_type=zipfile.ZIP_BZIP2)
            archive.writestr('highratio.xml', b'x'*100000, compress_type=zipfile.ZIP_DEFLATED)
        codes = [code for _, _, code in entries(stream.getvalue(), 'test.zip', self.event)]
        self.assertEqual(codes, ['ZIP_UNSAFE_PATH', 'ZIP_ENTRY_TYPE_UNSUPPORTED', 'ZIP_METHOD_UNSUPPORTED', 'ZIP_ENTRY_SIZE_OR_RATIO_LIMIT'])

    def test_namespace_safe_unknown_complement_not_mistaken_for_tax(self):
        _, rows = self.imported([('unknown.xml', self.sample('unknown_complement_40.xml'))])
        self.assertEqual(rows[0]['IVA'], '16')
        self.assertEqual(rows[0]['ResultadoValidacion'], 'REVISAR')
        self.assertIn('999999', rows[0]['XMLRaw'])
        self.assertEqual(rows[0]['_details']['complements'][0]['EstadoInterpretacion'], 'not-interpreted')

    def test_utf16_and_latin1_preserve_names_and_bytes(self):
        _, rows = self.imported([('a.xml', self.sample('utf16_40.xml')), ('b.xml', self.sample('latin1_40.xml'))])
        self.assertEqual([r['NombreEmisor'] for r in rows], ['EMPRESA SINTÉTICA ÁRBOL']*2)
        self.assertTrue(all('ÁRBOL' in r['XMLRaw'] for r in rows))

    def test_display_rounding_does_not_depend_on_global_context(self):
        with localcontext() as context:
            context.prec, context.rounding = 5, ROUND_DOWN
            selected, rows = self.imported([('one.xml', invoice(concepts=[concept(amount='1.005')], globals=[], aggregate_transfer=None, subtotal='1.01', total='1.01'))])
            formats = self.call('report.aggregate', selected)['money_formats']
        self.assertEqual(formats['1.01'], '$1.01')

    def test_metadata_conflict_and_duplicate_rows_are_not_lost(self):
        timbre = '<t:TimbreFiscalDigital xmlns:t="http://www.sat.gob.mx/TimbreFiscalDigital" Version="1.1" UUID="11111111-1111-4111-8111-111111111111" FechaTimbrado="2026-11-06T12:34:57" RfcProvCertif="AAA010101AAA" SelloCFD="QUFB" NoCertificadoSAT="00001000000500000000" SelloSAT="QUFB"/>'
        xml = invoice(extra=timbre)
        metadata = ('Uuid~RfcEmisor~NombreEmisor~RfcReceptor~NombreReceptor~Estatus~FechaCancelacion\n'
                    '11111111-1111-4111-8111-111111111111~AAA010101AAA~A~BBB010101BB1~B~1~\n'
                    '11111111-1111-4111-8111-111111111111~AAA010101AAA~A~BBB010101BB1~B~0~2026-11-07\n').encode()
        selected, rows = self.imported([('one.xml', xml), ('two.xml', xml), ('metadata.txt', metadata)])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['EstatusSAT'], 'DESCONOCIDO')
        self.assertIn('METADATA_CONFLICTO', rows[0]['ObservacionesXML'])
        self.assertIn('UUID_DUPLICADO', rows[1]['ObservacionesXML'])
        duplicates = report_rows(self.store.datasets[selected['dataset_id']], 'duplicates', rows)
        self.assertEqual(len(duplicates), 1)

    def test_rep_multiple_payment_document_and_tax_reports_preserved(self):
        complement = '''<p:Pagos xmlns:p="http://www.sat.gob.mx/Pagos20" Version="2.0"><p:Totales MontoTotalPagos="100"/>
        <p:Pago MonedaP="MXN" Monto="40" FormaDePagoP="03"><p:DoctoRelacionado IdDocumento="A" ImpSaldoAnt="100" ImpPagado="40" ImpSaldoInsoluto="60" MonedaDR="MXN"><p:ImpuestosDR><p:TrasladosDR><p:TrasladoDR BaseDR="100" ImpuestoDR="002" TipoFactorDR="Tasa" TasaOCuotaDR="0.160000" ImporteDR="16"/></p:TrasladosDR></p:ImpuestosDR></p:DoctoRelacionado></p:Pago>
        <p:Pago MonedaP="MXN" Monto="60" FormaDePagoP="03"><p:DoctoRelacionado IdDocumento="B" ImpSaldoAnt="60" ImpPagado="60" ImpSaldoInsoluto="0" MonedaDR="MXN"/></p:Pago></p:Pagos>'''
        _, rows = self.imported([('p.xml', invoice(document_type='P', currency='XXX', total='0', subtotal='0', concepts=[concept(amount='0')], globals=[], aggregate_transfer=None, extra=complement))])
        row = rows[0]
        self.assertEqual((len(row['_details']['payments']), len(row['_details']['paymentDocs']), len(row['_details']['paymentTaxes'])), (2, 2, 1))
        self.assertEqual((row['Total'], row['PagoMontoTotalPagos'], row['PagoMontoCalculadoMXN']), ('0', '100', '100'))
        self.assertEqual(row['_details']['paymentDocs'][0]['ValidacionSaldo'], 'NO EVALUADO')
        self.assertEqual(row['_details']['paymentDocs'][0]['DiferenciaSaldo'], '0')
        self.assertEqual(row['_details']['paymentTaxes'][0]['Importe'], '16')
        self.assertEqual(row['ResultadoValidacion'], 'REVISAR')

    def test_payroll_all_five_reports_and_decimal_perception(self):
        complement = '''<n:Nomina xmlns:n="http://www.sat.gob.mx/nomina12" Version="1.2" TipoNomina="O" FechaPago="2026-11-06" TotalPercepciones="0.3"><n:Receptor NumEmpleado="0001" Curp="SYNTHETIC"/>
        <n:Percepciones><n:Percepcion TipoPercepcion="001" Clave="01" Concepto="Sueldo" ImporteGravado="0.1" ImporteExento="0.2"><n:HorasExtra Dias="1" TipoHoras="01" HorasExtra="2" ImportePagado="0.1"/></n:Percepcion></n:Percepciones>
        <n:Deducciones><n:Deduccion TipoDeduccion="002" Importe="0.1"/></n:Deducciones><n:OtrosPagos><n:OtroPago TipoOtroPago="002" Importe="0.2"><n:SubsidioAlEmpleo SubsidioCausado="0.2"/></n:OtroPago></n:OtrosPagos><n:Incapacidades><n:Incapacidad DiasIncapacidad="1" TipoIncapacidad="01" ImporteMonetario="0.1"/></n:Incapacidades></n:Nomina>'''
        _, rows = self.imported([('n.xml', invoice(document_type='N', extra=complement))])
        details = rows[0]['_details']
        for report in ('payrollPerceptions', 'payrollDeductions', 'payrollOtherPayments', 'payrollOvertime', 'payrollIncapacities'):
            self.assertEqual(len(details[report]), 1)
        self.assertEqual(details['payrollPerceptions'][0]['Importe'], '0.3')
        self.assertEqual(rows[0]['NumEmpleado'], '0001')
        self.assertEqual(rows[0]['ResultadoValidacion'], 'REVISAR')

    def test_carta_porte_reports_preserved_without_certifying_rules(self):
        complement = '''<cp:CartaPorte xmlns:cp="http://www.sat.gob.mx/CartaPorte31" Version="3.1"><cp:Ubicaciones><cp:Ubicacion TipoUbicacion="Origen" IDUbicacion="OR000001" DistanciaRecorrida="0.1"/><cp:Ubicacion TipoUbicacion="Destino" IDUbicacion="DE000001" DistanciaRecorrida="0.2"/></cp:Ubicaciones><cp:Mercancias><cp:Mercancia BienesTransp="01010101" Descripcion="Sintético" Cantidad="1" ClaveUnidad="H87" PesoEnKg="0.3"/></cp:Mercancias><cp:FiguraTransporte><cp:TiposFigura TipoFigura="01" NombreFigura="PRUEBA"/></cp:FiguraTransporte></cp:CartaPorte>'''
        _, rows = self.imported([('t.xml', invoice(document_type='T', extra=complement))])
        self.assertEqual(len(rows[0]['_details']['locations']), 2)
        self.assertEqual(len(rows[0]['_details']['goods']), 1)
        self.assertEqual(len(rows[0]['_details']['transportFigures']), 1)
        self.assertEqual(rows[0]['CartaPorteDistanciaTotal'], '0.3')
        self.assertEqual(rows[0]['ResultadoValidacion'], 'REVISAR')

    def test_unknown_namespace_cannot_impersonate_payments(self):
        extra = '<p:Pagos xmlns:p="urn:fake" Version="2.0"><p:Pago Monto="999"/></p:Pagos>'
        _, rows = self.imported([('fake.xml', invoice(extra=extra))])
        self.assertEqual(rows[0]['_details']['payments'], [])
        self.assertEqual(rows[0]['_details']['complements'][0]['NamespaceURI'], 'urn:fake')

    def test_all_report_keys_are_usable_and_identity_stable(self):
        from app.desktop.reports import REPORTS
        selected, docs = self.imported([('a.xml', invoice())])
        dataset = self.store.datasets[selected['dataset_id']]
        for report in REPORTS:
            with self.subTest(report=report):
                rows = report_rows(dataset, report, docs)
                self.assertTrue(all('_rowId' in r for r in rows))
                self.assertEqual(report_rows(dataset, report, docs, [r['_rowId'] for r in rows]), rows)

    def test_import_session_limits_fail_without_replacing_previous_report(self):
        selected, rows = self.imported([('a.xml', invoice())])
        previous = self.store.active_dataset
        self.job = 'limited'
        self.call('import.begin')
        self.store.staging[self.job]['source_bytes'] = 64*1024*1024
        with self.assertRaisesRegex(ValueError, 'IMPORT_SESSION_BYTE_LIMIT'):
            self.call('import.file', {'name': 'one.xml', 'base64': base64.b64encode(invoice()).decode()})
        self.assertEqual(self.store.active_dataset, previous)
        self.assertEqual(self.call('report.aggregate', selected)['groups'][0]['Total'], '116')

    def test_large_transport_pages_keep_all_rows_and_incidents_once(self):
        self.call('import.begin')
        stage = self.store.staging[self.job]
        stage['rows'] = [{'_docId': str(i), '_rowId': str(i), 'XMLRaw': 'x'*(1024*1024+1)} for i in range(3)]
        stage['errors'] = [{'_rowId': 'error'+str(i), 'MensajeError': 'SYNTHETIC'} for i in range(5)]
        stage['prepared'] = True
        identities, errors, offset = [], [], 0
        for _ in range(6):
            result = self.call('import.page', {'offset': offset})
            identities.extend(r['_rowId'] for r in result['rows'])
            errors.extend(r['_rowId'] for r in result['errors'])
            if result['done']:
                break
            self.assertGreater(result['next'], offset)
            offset = result['next']
        self.assertEqual(identities, ['0', '1', '2'])
        self.assertEqual(errors, ['error'+str(i) for i in range(5)])

    def test_webchannel_exports_only_the_three_intended_slots(self):
        from app.desktop.fiscal_worker import FiscalBridge
        from PySide6.QtCore import QMetaMethod
        meta = FiscalBridge.staticMetaObject
        slots = {bytes(meta.method(i).name()).decode() for i in range(meta.methodOffset(), meta.methodCount())
                 if meta.method(i).methodType() == QMetaMethod.MethodType.Slot}
        self.assertEqual(slots, {'openJob', 'request', 'cancel'})
        names = {bytes(meta.method(i).name()).decode() for i in range(meta.methodOffset(), meta.methodCount())}
        self.assertNotIn('_received', names)
        self.assertNotIn('dispatch', names)


if __name__ == '__main__':
    unittest.main()
