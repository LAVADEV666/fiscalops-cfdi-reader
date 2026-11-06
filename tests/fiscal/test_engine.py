from dataclasses import replace
from decimal import Decimal, ROUND_DOWN, getcontext, localcontext
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from lxml import etree as E

from app.fiscal.calculations import analyze, product_interval
from app.fiscal.models import Nature, to_data
from app.fiscal.numbers import number, quantize
from app.fiscal.reader import read_invoice
from app.fiscal.rules import RULES
from app.fiscal.security import Limits, XmlRejected, secure_bytes
from app.fiscal.service import inspect_invoice, json_data
from app.fiscal.sources import SatSources, SourceUnavailable, validate_xsd
from fixtures import concept, invoice, samples, tax

ROOT = Path(__file__).resolve().parents[2]
D = Decimal


class EngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = SatSources()
        cls.samples = samples()

    def inspect(self, data=None):
        return inspect_invoice(invoice() if data is None else data, sources=self.sources)

    def analysis(self, data=None):
        return self.inspect(data)['analysis']

    def codes(self, analysis):
        return {f['code'] for f in analysis['findings']}

    def mutate(self, data, change):
        root = E.fromstring(data)
        change(root)
        return E.tostring(root, encoding='UTF-8', xml_declaration=True)

    def test_reviewed_fixtures_xsd_and_arithmetic(self):
        manifest = json.loads((ROOT/'tests/fiscal/fixtures/manifest.json').read_text(encoding='utf-8'))
        for case in manifest['fixtures']:
            with self.subTest(file=case['file']):
                data = (ROOT/'tests/fiscal/fixtures'/case['file']).read_bytes()
                self.assertEqual(data, self.samples[case['file']])
                self.assertEqual(hashlib.sha256(data).hexdigest(), case['sha256'])
                result = self.inspect(data)
                self.assertEqual(result['validation']['xsd']['status'], case['xsd_expected'])
                self.assertEqual(result['analysis']['status'], case['arithmetic_expected'])

    def test_F01_iva_ieps_not_aggregate(self):
        a = self.analysis(self.samples['p0_iva_ieps_40.xml'])
        self.assertEqual(a['recalculated']['federal_by_code']['IVA_transfer'], D('16'))
        self.assertEqual(a['recalculated']['federal_by_code']['IEPS_transfer'], D('8'))
        self.assertEqual(a['reported']['federal']['TotalImpuestosTrasladados'].value, D('24'))
        self.assertEqual(a['recalculated']['total_from_tax_details'], D('124'))

    def test_F02_retention_isr_typed(self):
        r = self.inspect(self.samples['p0_isr_retention_40.xml'])
        self.assertIs(r['document'].global_taxes[0].nature, Nature.RETENTION)
        self.assertEqual(r['analysis']['recalculated']['federal_by_code']['ISR_retention'], D('10'))
        self.assertEqual(r['analysis']['recalculated']['total_from_concepts'], D('90'))

    def test_F03_local_counted_once(self):
        a = self.analysis(self.samples['p0_local_once_40.xml'])
        self.assertEqual(a['recalculated']['local_details']['transfer'], D('3'))
        self.assertEqual(a['recalculated']['total_from_reported_components'], D('119'))
        self.assertEqual(a['recalculated']['total_from_tax_details'], D('119'))
        self.assertEqual(a['recalculated']['difference_total_minus_details'], D('0'))

    def test_F03_local_retention_subtracted_once(self):
        a = self.analysis(self.samples['local_retention_40.xml'])
        self.assertEqual(a['recalculated']['local_details'], {'transfer': D('3'), 'retention': D('1')})
        self.assertEqual(a['recalculated']['total_from_concepts'], D('118'))

    def test_F03_local_mismatch_not_silently_fixed(self):
        data = invoice(locals={'transfer': '4', 'transfers': ['3']}, total='120')
        a = self.analysis(data)
        self.assertIn('LOCAL_AGGREGATE_VS_DETAILS', self.codes(a))
        self.assertEqual(a['reported']['local']['transfer'], D('4'))
        self.assertEqual(a['recalculated']['local_details']['transfer'], D('3'))
        self.assertEqual(a['recalculated']['total_from_reported_components'], D('120'))
        self.assertEqual(a['recalculated']['total_from_tax_details'], D('119'))

    def test_F04_exempt_and_zero_bases_disjoint(self):
        a = self.analysis(self.samples['p0_exempt_zero_40.xml'])
        bases = a['recalculated']['iva_bases']
        self.assertEqual(bases['exempt'], D('100'))
        self.assertEqual(bases['zero_rate'], D('100'))
        groups = a['recalculated']['federal_concept_groups']
        self.assertIsNone(next(g for g in groups if g['factor'] == 'Exento')['amount'])
        self.assertEqual(next(g for g in groups if g['factor'] == 'Tasa')['amount'], D('0'))

    def test_F04_exempt_only_aggregate_absent_is_not_zero_rate(self):
        t = tax(factor='Exento', rate=None, amount=None)
        a = self.analysis(invoice(concepts=[concept(taxes=[t])], globals=[t], aggregate_transfer=None, total='100'))
        self.assertEqual(a['status'], 'consistent-in-scope')
        self.assertEqual(a['recalculated']['iva_bases']['zero_rate'], D('0'))
        self.assertEqual(a['reported']['federal']['TotalImpuestosTrasladados'].state, 'missing')

    def test_F04_exempt_with_amount_or_rate_rejected(self):
        for field in ('rate', 'amount'):
            with self.subTest(field=field):
                t = tax(factor='Exento', rate=None, amount=None)
                t[field] = '0'
                a = self.analysis(invoice(concepts=[concept(taxes=[t])], globals=[t], aggregate_transfer=None, total='100'))
                self.assertIn('EXEMPT_FIELDS_ABSENT', self.codes(a))

    def test_F04_exempt_retention_not_valid(self):
        t = tax(code='001', factor='Exento', rate=None, amount=None, nature='retention')
        a = self.analysis(invoice(concepts=[concept(taxes=[t])], globals=[t], aggregate_transfer=None, total='100'))
        self.assertIn('EXEMPT_FIELDS_ABSENT', self.codes(a))

    def test_F05_missing_aggregate_does_not_double(self):
        a = self.analysis(self.samples['p0_missing_aggregate_40.xml'])
        selection = a['recalculated']['selected_federal']['transfer']
        self.assertEqual(selection['source'], 'global-detail')
        self.assertEqual(selection['total'], D('16'))
        self.assertEqual(a['recalculated']['federal_by_code']['IVA_transfer'], D('16'))
        self.assertIsNone(a['recalculated']['total_from_reported_components'])
        self.assertEqual(a['recalculated']['total_from_tax_details'], D('116'))
        self.assertIn('FEDERAL_AGGREGATE_MISSING', self.codes(a))

    def test_F05_missing_global_uses_traced_concept_fallback(self):
        a = self.analysis(invoice(globals=[], aggregate_transfer=None))
        self.assertEqual(a['recalculated']['selected_federal']['transfer']['source'], 'concept-fallback')
        self.assertEqual(a['recalculated']['selected_federal']['transfer']['total'], D('16.00'))
        self.assertIn('GLOBAL_GROUP_MISSING', self.codes(a))

    def test_F05_invalid_global_amount_not_fallback_to_concepts(self):
        t = tax(amount='INVALID')
        a = self.analysis(invoice(globals=[t]))
        self.assertEqual(a['recalculated']['selected_federal']['transfer']['source'], 'global-detail')
        self.assertIsNone(a['recalculated']['selected_federal']['transfer']['total'])
        self.assertIsNone(a['recalculated']['total_from_tax_details'])
        self.assertIn('NUMBER_FIELD', self.codes(a))

    def test_F05_incorrect_aggregate_is_preserved(self):
        a = self.analysis(invoice(aggregate_transfer='24'))
        self.assertEqual(a['reported']['federal']['TotalImpuestosTrasladados'].raw, '24')
        self.assertEqual(a['recalculated']['federal_by_code']['IVA_transfer'], D('16'))
        self.assertEqual(a['recalculated']['total_from_reported_components'], D('124'))
        self.assertIn('FEDERAL_AGGREGATE_VS_DETAILS', self.codes(a))

    def test_F06_missing_invalid_and_zero_distinct(self):
        fields = [number(value, '/x') for value in (None, '', 'BAD', '0', '0.000000')]
        self.assertEqual([f.state for f in fields], ['missing', 'invalid', 'invalid', 'valid', 'valid'])
        self.assertEqual([f.value for f in fields], [None, None, None, D('0'), D('0')])
        self.assertEqual(fields[-1].scale, 6)
        a = self.analysis(self.samples['p0_missing_subtotal_40.xml'])
        self.assertIsNone(a['reported']['subtotal'].value)
        self.assertIsNone(a['recalculated']['total_from_tax_details'])

    def test_F06_nondecimal_lexicals_never_coerced(self):
        for raw in ('NaN', 'Infinity', '-1', '1e2', '1,000.00', '1,25', '0x10', '１', '1'*65):
            with self.subTest(raw=raw):
                self.assertEqual(number(raw, '/x').state, 'invalid')

    def test_F06_exact_decimal_and_serialization(self):
        self.assertEqual(number('0.1', '/x').value+number('0.2', '/y').value, D('0.3'))
        self.assertEqual(quantize(D('1.005'), 2), D('1.01'))
        self.assertEqual(to_data(number('0.00', '/x')), {'raw': '0.00', 'value': '0.00', 'state': 'valid', 'scale': 2, 'path': '/x'})
        with self.assertRaises(TypeError):
            to_data({'amount': 0.1})

    def test_F06_round_after_grouping_not_each_concept(self):
        a = self.analysis(self.samples['round_groups_40.xml'])
        self.assertEqual(a['recalculated']['subtotal_from_concepts'], D('0.21'))
        self.assertEqual(a['recalculated']['federal_by_code']['IVA_transfer'], D('0.03'))
        self.assertEqual(a['recalculated']['total_from_concepts'], D('0.24'))

    def test_F06_ambient_decimal_context_cannot_change_results(self):
        with localcontext() as context:
            context.prec = 3
            context.rounding = ROUND_DOWN
            a = self.analysis(self.samples['round_groups_40.xml'])
        self.assertEqual(a['recalculated']['total_from_concepts'], D('0.24'))

    def test_F06_large_exact_amount(self):
        data = invoice(concepts=[concept(amount='999999999999999999.123456')], globals=[], aggregate_transfer=None,
                       subtotal='999999999999999999.12', total='999999999999999999.12')
        a = self.analysis(data)
        self.assertEqual(a['recalculated']['total_from_concepts'], D('999999999999999999.12'))
        self.assertEqual(a['status'], 'consistent-in-scope')

    def test_F06_currency_precision_zero_two_three(self):
        for code, raw, rounded, digits in [('JPY', '1.005', '2', 0), ('USD', '1.005', '2.01', 2), ('KWD', '1.005', '2.010', 3)]:
            with self.subTest(currency=code):
                a = self.analysis(invoice(concepts=[concept(amount=raw)]*2, globals=[], aggregate_transfer=None,
                                          currency=code, subtotal=rounded, total=rounded))
                self.assertEqual(a['currency_digits'], digits)
                self.assertEqual(a['recalculated']['total_from_concepts'], D(rounded))
                self.assertEqual(a['status'], 'consistent-in-scope')

    def test_F06_foreign_exchange_not_optional_or_invented(self):
        data = self.mutate(invoice(currency='USD'), lambda r: r.attrib.pop('TipoCambio'))
        a = self.analysis(data)
        self.assertIn('FOREIGN_EXCHANGE_REQUIRED', self.codes(a))
        self.assertEqual(a['reported']['total'].value, D('116'))  # Remains USD; no implicit MXN conversion.

    def test_F06_unknown_currency_never_assumes_two_decimals(self):
        a = self.analysis(invoice(currency='ZZZ'))
        self.assertIsNone(a['currency_digits'])
        self.assertIsNone(a['recalculated']['total_from_concepts'])
        self.assertIn('CURRENCY_PRECISION', self.codes(a))

    def test_F06_header_currency_scale_error(self):
        a = self.analysis(invoice(total='116.001'))
        self.assertTrue(any(f['code'] == 'NUMBER_FIELD' and f['path'].endswith('@Total') for f in a['findings']))

    def test_F06_rate_six_digits_per_official_faq40(self):
        t = tax(rate='0.16')
        r = self.inspect(invoice(concepts=[concept(taxes=[t])], globals=[t]))
        self.assertEqual(r['validation']['xsd']['status'], 'pass')  # XSD alone has only an upper precision bound.
        self.assertIn('FEDERAL_RATE_SIX_DECIMALS', self.codes(r['analysis']))

    def test_F06_discount_calculated_and_absence_enforced(self):
        data = invoice(concepts=[concept(amount='100', discount='10')], globals=[], aggregate_transfer=None,
                       subtotal='100', discount='10', total='90')
        self.assertEqual(self.analysis(data)['status'], 'consistent-in-scope')
        a = self.analysis(self.mutate(data, lambda r: r.attrib.pop('Descuento')))
        self.assertIn('HEADER_DISCOUNT_REQUIRED', self.codes(a))
        self.assertIsNone(a['recalculated']['total_from_tax_details'])
        a = self.analysis(invoice(discount='0'))
        self.assertIn('HEADER_DISCOUNT_MUST_BE_OMITTED', self.codes(a))

    def test_F06_product_bounds_use_reported_precision(self):
        first, second = number('100.000000', '/b'), number('0.160000', '/r')
        expected = {'lower': D('15.999999'), 'upper': D('16.000001'), 'exact_product': D('16.000000000000')}
        self.assertEqual(product_interval(first, second, number('16.000000', '/i'), tax=True), expected)
        for amount, expected_status in [('15.999999', 'pass'), ('16.000001', 'pass'), ('15.999998', 'error'), ('16.000002', 'error')]:
            with self.subTest(amount=amount):
                a = self.analysis(invoice(concepts=[concept(taxes=[tax(base='100.000000', amount=amount)])]))
                check = next(c for c in a['checks'] if c['code'] == 'TAX_PRODUCT_INTERVAL')
                self.assertEqual(check['status'], expected_status)

    def test_F06_concept_product_bad_amount(self):
        a = self.analysis(invoice(concepts=[concept(amount='100.000000', quantity='1.000000', unit='101.000000')]))
        self.assertIn('CONCEPT_PRODUCT_INTERVAL', self.codes(a))

    def test_namespace_prefix_variants_same_values(self):
        for prefix in ('cfdi', 'otra', None):
            with self.subTest(prefix=prefix):
                r = self.inspect(invoice(prefix=prefix))
                self.assertEqual(r['validation']['xsd']['status'], 'pass')
                self.assertEqual(r['analysis']['recalculated']['total_from_tax_details'], D('116'))

    def test_wrong_namespace_and_version_rejected(self):
        for data, code in [(invoice().replace(b'http://www.sat.gob.mx/cfd/4', b'urn:not-sat'), 'CFDI_ROOT_NAMESPACE_UNSUPPORTED'),
                           (invoice().replace(b'Version="4.0"', b'Version="3.3"'), 'CFDI_NAMESPACE_VERSION_MISMATCH'),
                           (invoice().replace(b'Version="4.0"', b'Version="9.0"'), 'CFDI_VERSION_UNSUPPORTED')]:
            with self.subTest(code=code), self.assertRaises(XmlRejected) as ctx:
                read_invoice(data)
            self.assertEqual(ctx.exception.code, code)

    def test_foreign_tax_namespace_is_not_read_as_cfdi(self):
        data = invoice().replace(b'<cfdi:Traslado ', b'<otra:Traslado xmlns:otra="urn:not-sat" ')
        r = self.inspect(data)
        self.assertEqual(r['document'].global_taxes, ())
        self.assertEqual(r['document'].concepts[0].taxes, ())
        self.assertEqual(r['validation']['xsd']['status'], 'fail')

    def test_encodings_preserve_names_and_original_bytes(self):
        for encoding in ('UTF-8', 'UTF-16', 'UTF-16LE', 'UTF-16BE', 'ISO-8859-1'):
            with self.subTest(encoding=encoding):
                data = invoice(encoding=encoding)
                doc = read_invoice(data)
                self.assertEqual(doc.original, data)
                self.assertEqual(doc.issuer['Nombre'], 'EMPRESA SINTÉTICA ÁRBOL')
                self.assertEqual(doc.sha256, hashlib.sha256(data).hexdigest())
                self.assertEqual(self.inspect(data)['validation']['xsd']['status'], 'pass')

    def test_original_hash_distinguishes_same_size_content(self):
        first = invoice()
        second = first.replace(b'12:34:56', b'12:34:57')
        self.assertEqual(len(first), len(second))
        self.assertNotEqual(read_invoice(first).sha256, read_invoice(second).sha256)
        doc = read_invoice(first)
        self.assertEqual(base64.b64decode(to_data(doc, include_original=True)['original']['base64']), first)

    def test_unknown_complement_preserved_and_not_taxed(self):
        data = self.samples['unknown_complement_40.xml']
        r = self.inspect(data)
        self.assertIn('999999', r['document'].complements[0].xml)
        self.assertEqual(r['document'].complements[0].status, 'not-interpreted')
        self.assertEqual(r['analysis']['recalculated']['federal_by_code']['IVA_transfer'], D('16'))
        self.assertEqual(r['validation']['xsd']['status'], 'pending')
        self.assertEqual(r['validation']['xsd']['core_projection_status'], 'pass')
        self.assertEqual(r['document'].original, data)

    def test_tfd_identity_is_not_signature_validation(self):
        data = invoice(extra='<t:TimbreFiscalDigital xmlns:t="http://www.sat.gob.mx/TimbreFiscalDigital" Version="1.1" UUID="11111111-1111-4111-8111-111111111111" FechaTimbrado="2026-11-06T12:34:57" RfcProvCertif="AAA010101AAA" SelloCFD="QUFB" NoCertificadoSAT="00001000000500000000" SelloSAT="QUFB"/>')
        r = self.inspect(data)
        self.assertEqual(r['document'].uuid, '11111111-1111-4111-8111-111111111111')
        self.assertEqual(r['validation']['xsd']['status'], 'pass')
        self.assertEqual(r['validation']['signature'], 'not-validated')
        self.assertEqual(r['validation']['official_sat'], 'not-queried')

    def test_multiple_complement_containers_33_preserved(self):
        data = invoice(version='3.3', extra='<x:A xmlns:x="urn:a"/>')
        def add(root):
            node = E.SubElement(root, '{http://www.sat.gob.mx/cfd/3}Complemento')
            E.SubElement(node, '{urn:b}B')
        r = self.inspect(self.mutate(data, add))
        self.assertEqual(len(r['document'].complements), 2)
        self.assertEqual(r['document'].structural_issues, ())
        self.assertEqual(r['validation']['xsd']['status'], 'pending')

    def test_unsupported_types_keep_xml_without_claiming_arithmetic(self):
        for kind in ('N', 'P', 'T'):
            with self.subTest(kind=kind):
                data = invoice(document_type=kind)
                r = self.inspect(data)
                self.assertEqual(r['document'].original, data)
                self.assertIn('DOCUMENT_ARITHMETIC_NOT_IMPLEMENTED', self.codes(r['analysis']))
                self.assertIsNone(r['analysis']['recalculated']['total_from_tax_details'])
        payment = invoice(document_type='P', currency='XXX', concepts=[concept(amount='0', unit='0')],
                          globals=[], aggregate_transfer=None, subtotal='0', total='0')
        a = self.analysis(payment)
        self.assertEqual(a['status'], 'partial')
        self.assertNotIn('POSITIVE_OPERAND', self.codes(a))
        self.assertTrue(all(value is None for value in a['recalculated']['federal_by_code'].values()))

    def test_duplicate_global_groups_diagnosed(self):
        a = self.analysis(invoice(globals=[tax(), tax()], aggregate_transfer='32', total='132'))
        self.assertIn('GLOBAL_GROUP_UNIQUE', self.codes(a))

    def test_duplicate_singleton_blocks_formula(self):
        data = self.mutate(invoice(), lambda r: r.append(E.fromstring(E.tostring(r.find('{*}Impuestos')))))
        a = self.analysis(data)
        self.assertIn('CFDI_DUPLICATE_SINGLETON', self.codes(a))
        self.assertIsNone(a['recalculated']['total_from_tax_details'])

    def test_unsupported_local_version_not_silently_zero(self):
        data = invoice(locals={'transfer': '3', 'transfers': ['3']}, total='119').replace(b'version="1.0" Totalde', b'version="2.0" Totalde')
        a = self.analysis(data)
        self.assertIn('COMPLEMENT_NOT_INTERPRETED', self.codes(a))
        self.assertIsNone(a['recalculated']['local_details']['transfer'])
        self.assertIsNone(a['recalculated']['total_from_tax_details'])

    def test_catalog_rate_fixed_range_and_mismatch(self):
        for t, valid in [(tax(), True), (tax(rate='0.080000', amount='8'), True), (tax(rate='0.150000', amount='15'), False),
                         (tax(code='001', nature='retention', rate='0.100000', amount='10'), True)]:
            with self.subTest(tax=t):
                a = self.analysis(invoice(concepts=[concept(taxes=[t])]))
                c = next(c for c in a['checks'] if c['code'] == 'RATE_CATALOG')
                self.assertEqual(c['status'], 'pass' if valid else 'error')

    def test_F01_F02_multiple_concepts_multiple_codes(self):
        specs = []
        for amount, iva, ieps, isr in [('100', '16', '8', '10'), ('50', '8', '4', '5')]:
            specs.append(concept(amount=amount, taxes=[tax(base=amount, amount=iva),
                           tax(code='003', base=amount, rate='0.080000', amount=ieps),
                           tax(code='001', base=amount, rate='0.100000', amount=isr, nature='retention')]))
        gl = [tax(base='150', amount='24'), tax(code='003', base='150', rate='0.080000', amount='12'),
              tax(code='001', base='150', rate='0.100000', amount='15', nature='retention')]
        for version in ('3.3', '4.0'):
            with self.subTest(version=version):
                r = self.inspect(invoice(version=version, concepts=specs, globals=gl, subtotal='150', total='171',
                                         aggregate_transfer='36', aggregate_retention='15'))
                self.assertEqual(r['validation']['xsd']['status'], 'pass')
                self.assertEqual(r['analysis']['status'], 'consistent-in-scope')
                summary = r['analysis']['recalculated']['federal_by_code']
                self.assertEqual((summary['IVA_transfer'], summary['IEPS_transfer'], summary['ISR_retention']), (D('24'), D('12'), D('15')))
                self.assertEqual(r['analysis']['recalculated']['total_from_concepts'], D('171'))

    def test_IEPS_cuota_and_historical_catalog_gap(self):
        t = tax(code='003', factor='Cuota', base='100.000000', rate='1.500000', amount='150.000000')
        data = invoice(concepts=[concept(taxes=[t])], globals=[dict(t, base='100', amount='150')],
                       aggregate_transfer='150', total='250')
        r = self.inspect(data)
        self.assertEqual(r['validation']['xsd']['status'], 'pass')
        self.assertEqual(r['analysis']['status'], 'consistent-in-scope')
        self.assertEqual(r['analysis']['recalculated']['federal_by_code']['IEPS_transfer'], D('150'))
        a = self.analysis(data.replace(b'2026-11-06', b'2025-11-06'))
        rates = [c['status'] for c in a['checks'] if c['code'] == 'RATE_CATALOG']
        self.assertEqual(rates, ['pending', 'pending'])
        self.assertEqual(a['status'], 'partial')

    def test_historical_33_exempt_only(self):
        t = tax(factor='Exento', rate=None, amount=None)
        r = self.inspect(invoice(version='3.3', concepts=[concept(taxes=[t])], globals=[], aggregate_transfer=None, total='100'))
        self.assertEqual(r['validation']['xsd']['status'], 'pass')
        self.assertEqual(r['analysis']['status'], 'consistent-in-scope')
        self.assertEqual(r['analysis']['recalculated']['iva_bases']['exempt'], D('100'))

    def test_catalog_mapping_retains_credit_label(self):
        for version in ('3.3', '4.0'):
            credit = next(r for r in self.sources.catalogs['versions'][version]['rates'] if r['maximum'] == '0.080000' and r['tax_code'] == '002')
            self.assertEqual(credit['tax'], 'IVA Crédito aplicado del 50%')

    def test_catalog_historical_dates_are_not_guessed(self):
        self.assertIsNone(self.sources.currency('4.0', 'MXN', '2021-12-31'))
        self.assertIsNone(self.sources.currency('4.0', 'MXN', 'invalid'))
        self.assertEqual(self.sources.currency('3.3', 'JPY', '2023-03-01')['digits'], 0)
        a = self.analysis(invoice(date='2021-12-31T12:34:56'))
        self.assertIsNone(a['currency_digits'])
        self.assertIn('CURRENCY_PRECISION', self.codes(a))

    def test_all_supporting_sat_codes_exist_in_downloaded_matrix(self):
        for version in ('3.3', '4.0'):
            codes = {r['code'] for r in self.sources.catalogs['versions'][version]['rules']}
            for rule, reference in RULES.items():
                with self.subTest(version=version, rule=rule):
                    self.assertTrue(set(reference['sat40' if version == '4.0' else 'sat33']) <= codes)

    def test_xsd_errors_exclude_taxpayer_content(self):
        r = self.inspect(invoice(subtotal=None))
        errors = json.dumps(r['validation']['xsd']['errors'])
        self.assertNotIn('AAA010101AAA', errors)
        self.assertNotIn('SINT', errors)
        self.assertNotIn('message', errors)

    def test_offline_schema_location_and_xinclude_never_fetch(self):
        data = self.mutate(invoice(), lambda r: r.set('{http://www.w3.org/2001/XMLSchema-instance}schemaLocation',
                                                     'http://www.sat.gob.mx/cfd/4 https://example.invalid/evil.xsd'))
        with patch.object(socket.socket, 'connect', side_effect=AssertionError('Network forbidden')):
            r = inspect_invoice(data, sources=SatSources())
        self.assertEqual(r['validation']['xsd']['status'], 'pass')
        extra = '<xi:include xmlns:xi="http://www.w3.org/2001/XInclude" href="file:///C:/DO_NOT_READ"/>'
        r = self.inspect(invoice(extra=extra))
        self.assertIn('DO_NOT_READ', r['document'].complements[0].xml)
        self.assertEqual(r['validation']['xsd']['status'], 'pending')

    def test_resource_tamper_and_missing_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            (dest/'manifest.json').write_bytes((ROOT/'resources/sat/manifest.json').read_bytes())
            (dest/'cfdv40.xsd').write_bytes(b'<not-the-sat-schema/>')
            sources = SatSources(dest)
            with self.assertRaises(SourceUnavailable):
                sources.resource('cfdi40')
            self.assertEqual(validate_xsd(read_invoice(invoice()), sources)['status'], 'pending')
            (dest/'cfdv40.xsd').unlink()
            with self.assertRaises(SourceUnavailable):
                sources.resource('cfdi40')

    def test_cli_exit_status_and_original_protection(self):
        cases = [('p0_iva_ieps_40.xml', 0), ('p0_missing_aggregate_40.xml', 1), ('unknown_complement_40.xml', 3)]
        for name, exit_code in cases:
            with self.subTest(file=name):
                result = subprocess.run([sys.executable, '-m', 'app.fiscal', str(ROOT/'tests/fiscal/fixtures'/name)],
                                        cwd=ROOT, capture_output=True)
                self.assertEqual(result.returncode, exit_code, result.stderr)
                payload = json.loads(result.stdout)
                self.assertEqual(payload['contract'], 'fiscalops.inspection/1')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'malformed.xml'
            path.write_bytes(b'<bad>')
            result = subprocess.run([sys.executable, '-m', 'app.fiscal', str(path)], cwd=ROOT, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)['rejected']['code'], 'XML_MALFORMED')
            result = subprocess.run([sys.executable, '-m', 'app.fiscal', str(path), '--output', str(path)], cwd=ROOT, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(path.read_bytes(), b'<bad>')
            alias = Path(tmp)/'hardlink.xml'
            os.link(path, alias)
            result = subprocess.run([sys.executable, '-m', 'app.fiscal', str(path), '--output', str(alias)], cwd=ROOT, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(path.read_bytes(), b'<bad>')
            output = Path(tmp)/'missing-directory'/'report.json'
            result = subprocess.run([sys.executable, '-m', 'app.fiscal', str(path), '--output', str(output)], cwd=ROOT, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn(b'Traceback', result.stderr)


class SecurityTests(unittest.TestCase):
    def rejected(self, data, code, **limits):
        with self.assertRaises(XmlRejected) as ctx:
            secure_bytes(data, Limits(**limits))
        self.assertEqual(ctx.exception.code, code)

    def test_dtd_internal_external_entities_rejected_before_expansion(self):
        payloads = [b'<!DOCTYPE a><a/>', b'<!DOCTYPE a [<!ENTITY x "secret">]><a>&x;</a>',
                    b'<!DOCTYPE a SYSTEM "https://example.invalid/a.dtd"><a/>',
                    b'<!DOCTYPE a [<!ENTITY x SYSTEM "file:///C:/DO_NOT_READ">]><a>&x;</a>',
                    b'<!DOCTYPE a [<!ENTITY % x SYSTEM "https://example.invalid/a.dtd">%x;]><a/>']
        for data in payloads:
            with self.subTest(data=data):
                self.rejected(data, 'XML_DTD_FORBIDDEN')

    def test_utf16_dtd_not_hidden_by_zero_bytes(self):
        data = '<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE a [<!ENTITY x "x">]><a>&x;</a>'.encode('utf-16')
        self.rejected(data, 'XML_DTD_FORBIDDEN')

    def test_escaped_or_commented_doctype_is_harmless_text(self):
        data = b'<a><!-- <!DOCTYPE a> --><![CDATA[<!DOCTYPE a>]]>&lt;!DOCTYPE a&gt;&amp;</a>'
        self.assertEqual(secure_bytes(data)[0], data)

    def test_xml_malformed_encoding_and_duplicate_attributes(self):
        for data in (b'<a>', b'<a x="1" x="2"/>', b'<a>\xff</a>', b'<a>&undefined;</a>'):
            with self.subTest(data=data):
                self.rejected(data, 'XML_MALFORMED')
        self.rejected(b'<?xml version="1.1"?><a/>', 'XML_VERSION_UNSUPPORTED')
        self.rejected(b'<?xml version="1.0" encoding="Windows-1252"?><a/>', 'XML_ENCODING_UNSUPPORTED')

    def test_byte_limit_before_reading_whole_stream(self):
        stream = io.BytesIO(b' '*1000)
        self.rejected(stream, 'XML_BYTE_LIMIT', max_bytes=100)
        self.assertEqual(stream.tell(), 101)
        self.rejected(b' '*101, 'XML_BYTE_LIMIT', max_bytes=100)

    def test_depth_nodes_text_attributes_and_namespaces_limits(self):
        cases = [(b'<a><b><c/></b></a>', 'XML_DEPTH_LIMIT', {'max_depth': 2}),
                 (b'<a><b/><c/></a>', 'XML_NODE_LIMIT', {'max_nodes': 2}),
                 (b'<a>123456</a>', 'XML_TEXT_LIMIT', {'max_text_chars': 5}),
                 (b'<a x="1" y="2"/>', 'XML_ATTRIBUTE_LIMIT', {'max_attributes_per_node': 1}),
                 (b'<a xmlns:a="urn:a" xmlns:b="urn:b"/>', 'XML_ATTRIBUTE_LIMIT', {'max_attributes_per_node': 1}),
                 (b'<a x="123456"/>', 'XML_ATTRIBUTE_SIZE_LIMIT', {'max_attribute_chars': 4})]
        for data, code, limits in cases:
            with self.subTest(code=code, limits=limits):
                self.rejected(data, code, **limits)

    def test_cooperative_time_budget(self):
        self.rejected(b'<a/>', 'XML_TIME_LIMIT', max_seconds=0)

    def test_text_input_rejected_without_lossy_reencoding(self):
        with self.assertRaises(TypeError):
            secure_bytes('<a/>')


if __name__ == '__main__':
    unittest.main()
