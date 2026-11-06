"""Exact Decimal P0 reconciliation for CFDI I/E. No legal eligibility or SAT status inference."""
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, ROUND_CEILING, ROUND_DOWN, localcontext
import re
from . import RULESET_VERSION
from .models import Invoice, Nature, Number
from .numbers import DECIMAL_CONTEXT, ZERO, complete_sum, quantize
from .rules import reference
from .sources import SatSources, SourceUnavailable, effective

TAX_NAMES = {'001': 'ISR', '002': 'IVA', '003': 'IEPS'}


def product_interval(first: Number, second: Number, result: Number, *, tax=False):
    """Anexo20 4.0 pp76–78 / 3.3 pp68–70 (PDF pages): bounds at the reported result scale.

    Tax rate is exact; quantity x unit value allows both reported operand precisions.
    The 10^-12 correction belongs only to the upper operand bound. No epsilon comparison.
    """
    if any(n.value is None or n.scale is None for n in (first, second, result)):
        return None
    with localcontext(DECIMAL_CONTEXT):
        half_first = Decimal(1).scaleb(-first.scale)/2
        half_second = ZERO if tax else Decimal(1).scaleb(-second.scale)/2
        correction = Decimal('0.000000000001')
        low = (first.value-half_first)*(second.value-half_second)
        high = (first.value+half_first-correction)*(second.value if tax else second.value+half_second-correction)
        unit = Decimal(1).scaleb(-result.scale)
        return {'lower': low.quantize(unit, rounding=ROUND_DOWN),
                'upper': high.quantize(unit, rounding=ROUND_CEILING),
                'exact_product': first.value*second.value}


def analyze(invoice: Invoice, sources: SatSources):
    with localcontext(DECIMAL_CONTEXT):
        return _analyze(invoice, sources)


def _analyze(invoice, sources):
    checks, findings = [], []
    version = invoice.version

    def record(rule, code, path, status, *, reported=None, expected=None, detail=None):
        entry = {'rule': rule, 'code': code, 'path': path, 'status': status,
                 'reported': reported, 'expected': expected, 'reference': reference(rule, version)}
        if detail is not None:
            entry['detail'] = detail
        checks.append(entry)
        if status != 'pass':
            findings.append(entry)

    def compare(rule, code, path, reported, expected):
        status = 'pending' if expected is None or reported is None else 'pass' if reported == expected else 'error'
        record(rule, code, path, status, reported=reported, expected=expected)

    def validate_number(field, *, required=False, scale=6):
        if field.state == 'missing' and not required:
            return
        good = field.state == 'valid' and field.scale <= scale
        record('F06', 'NUMBER_FIELD', field.path, 'pass' if good else 'error',
               reported=field.raw, detail={'state': field.state, 'maximum_scale': scale})

    issue_date = invoice.attributes.get('Fecha', '')[:10]
    try:
        # No parsing of locale dates or silently truncating malformed ISO dates.
        datetime.strptime(invoice.attributes.get('Fecha', ''), '%Y-%m-%dT%H:%M:%S')
        valid_date = True
    except ValueError:
        valid_date = False
    currency = invoice.attributes.get('Moneda')
    try:
        currency_row = sources.currency(version, currency, issue_date) if valid_date else None
        catalog = sources.catalogs['versions'][version]
    except (SourceUnavailable, OSError, ValueError):
        currency_row, catalog = None, None
    digits = currency_row['digits'] if currency_row is not None and currency != 'XXX' else None
    record('CAT', 'CURRENCY_PRECISION', '/Comprobante/@Moneda', 'pass' if digits is not None else 'pending',
           reported=currency, expected=digits, detail={'issue_date': issue_date, 'snapshot': sources.manifest['snapshot'],
                                                     'row': currency_row, 'complete_catalog_history': False})
    for issue in invoice.structural_issues:
        record('SCOPE', issue['code'], issue['path'], 'error')
    supported = invoice.attributes.get('TipoDeComprobante') in ('I', 'E')
    if not supported:
        record('SCOPE', 'DOCUMENT_ARITHMETIC_NOT_IMPLEMENTED', '/Comprobante/@TipoDeComprobante', 'pending',
               reported=invoice.attributes.get('TipoDeComprobante'))
    for node in invoice.complements:
        if node.status == 'not-interpreted' and node.local_name != 'Addenda':
            record('SCOPE', 'COMPLEMENT_NOT_INTERPRETED', node.path, 'pending',
                   detail={'namespace': node.namespace, 'version': node.version})
    if invoice.uuid is not None:
        record('SCOPE', 'UUID_FORMAT', '/Comprobante/Complemento/TimbreFiscalDigital/@UUID',
               'pass' if re.fullmatch(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}', invoice.uuid) else 'error')
    if not supported:
        # P/N/T have their own arithmetic and conditions. In particular, a valid payment
        # concept has zero unit value: applying the I/E positive-value check would be wrong.
        return {'ruleset': RULESET_VERSION, 'status': 'error' if any(f['status'] == 'error' for f in findings) else 'partial',
                'scope': 'read-only; arithmetic for this document type not implemented',
                'currency': currency, 'currency_digits': digits, 'issue_date': issue_date,
                'reported': {'subtotal': invoice.numbers['SubTotal'], 'discount': invoice.numbers['Descuento'],
                             'total': invoice.numbers['Total'], 'federal': invoice.global_totals,
                             'local': [{'path': loc.path, 'transfer': loc.transfers, 'retention': loc.retentions} for loc in invoice.locals]},
                'recalculated': {'subtotal_from_concepts': None, 'discount_from_concepts': None,
                                 'federal_concept_groups': [], 'federal_global_groups': [],
                                 'selected_federal': {n.value: {'source': 'not-implemented', 'groups': [], 'total': None} for n in Nature},
                                 'federal_by_code': {f'{name}_{n.value}': None for name in TAX_NAMES.values() for n in Nature},
                                 'local_details': {n.value: None for n in Nature},
                                 'iva_bases': {'exempt': None, 'zero_rate': None, 'scope': 'not-implemented'},
                                 'total_from_reported_components': None, 'total_from_tax_details': None,
                                 'total_from_concepts': None, 'difference_total_minus_details': None},
                'checks': checks, 'findings': findings,
                'not_validated': ['document-type arithmetic', 'complement rules', 'signature/certificate',
                                  'SAT status/cancellation', 'deductibility/accreditability']}
    for key, field in invoice.numbers.items():
        validate_number(field, required=key in ('SubTotal', 'Total'), scale=digits if digits is not None and key != 'TipoCambio' else 6)
    root = invoice.numbers
    if currency not in ('MXN', 'XXX', None):
        exchange = root['TipoCambio']
        record('F06', 'FOREIGN_EXCHANGE_REQUIRED', exchange.path,
               'pass' if exchange.value is not None and exchange.value > ZERO else 'error', reported=exchange.raw)
    if currency == 'MXN' and root['TipoCambio'].state != 'missing':
        compare('F06', 'MXN_EXCHANGE_ONE', root['TipoCambio'].path, root['TipoCambio'].value, Decimal('1'))

    concept_taxes = tuple(t for c in invoice.concepts for t in c.taxes)
    all_federal = concept_taxes+invoice.global_taxes

    def check_rate(tax):
        if catalog is None or tax.rate.value is None:
            record('CAT', 'RATE_CATALOG', tax.rate.path, 'pending')
            return
        candidates = [r for r in catalog['rates'] if r['tax_code'] == tax.code and
                      r['factor'] == tax.factor and r[tax.nature.value]]
        valid_rows = [r for r in candidates if effective(r, issue_date)]
        allowed = [r for r in valid_rows if (tax.rate.value == Decimal(r['maximum']) if r['kind'] == 'Fijo'
                   else Decimal(r['minimum']) <= tax.rate.value <= Decimal(r['maximum']))]
        record('CAT', 'RATE_CATALOG', tax.rate.path, 'pass' if allowed else 'error' if valid_rows else 'pending',
               reported=tax.rate.value, detail={'rows': [r['row'] for r in allowed], 'issue_date': issue_date,
                                               'catalog_source': catalog['source_id']})

    for concept in invoice.concepts:
        n = concept.numbers
        for key, field in n.items():
            validate_number(field, required=key != 'Descuento')
        for key in ('Cantidad', 'ValorUnitario'):
            record('F06', 'POSITIVE_OPERAND', n[key].path,
                   'pass' if n[key].value is not None and n[key].value > ZERO else 'error', reported=n[key].value)
        bounds = product_interval(n['Cantidad'], n['ValorUnitario'], n['Importe'])
        record('F06', 'CONCEPT_PRODUCT_INTERVAL', n['Importe'].path,
               'pending' if bounds is None else 'pass' if bounds['lower'] <= n['Importe'].value <= bounds['upper'] else 'error',
               reported=n['Importe'].value, expected=bounds)
        if n['Descuento'].state != 'missing':
            okay = (n['Descuento'].value is not None and n['Importe'].value is not None and
                    n['Descuento'].value <= n['Importe'].value and n['Descuento'].scale <= n['Importe'].scale)
            record('F06', 'CONCEPT_DISCOUNT', n['Descuento'].path, 'pass' if okay else 'error', reported=n['Descuento'].raw)

    for tax in all_federal:
        rule = 'F02' if tax.nature == Nature.RETENTION else 'F01'
        record(rule, 'FEDERAL_TAX_CODE', tax.path+'/@Impuesto', 'pass' if tax.code in TAX_NAMES else 'error', reported=tax.code)
        # Global retentions have neither factor, rate nor base in the official schema.
        global_retention = tax.scope == 'global' and tax.nature == Nature.RETENTION
        if global_retention:
            validate_number(tax.amount, required=True, scale=digits if digits is not None else 6)
            continue
        if tax.scope == 'concept' or version == '4.0':
            validate_number(tax.base, required=True, scale=6 if tax.scope == 'concept' or digits is None else digits)
            if tax.scope == 'concept':
                record('F06', 'POSITIVE_TAX_BASE', tax.base.path,
                       'pass' if tax.base.value is not None and tax.base.value > ZERO else 'error', reported=tax.base.value)
        if tax.factor == 'Exento':
            record('F04', 'EXEMPT_FIELDS_ABSENT', tax.path,
                   'pass' if tax.rate.state == tax.amount.state == 'missing' and tax.nature == Nature.TRANSFER else 'error',
                   detail={'rate': tax.rate.raw, 'amount': tax.amount.raw, 'nature': tax.nature.value})
        elif tax.factor in ('Tasa', 'Cuota'):
            validate_number(tax.rate, required=True)
            if version == '4.0':
                record('F06', 'FEDERAL_RATE_SIX_DECIMALS', tax.rate.path,
                       'pass' if tax.rate.state == 'valid' and tax.rate.scale == 6 else 'error',
                       reported=tax.rate.raw, detail={'source': 'faq40', 'question': 40})
            validate_number(tax.amount, required=True, scale=6 if tax.scope == 'concept' or digits is None else digits)
            check_rate(tax)
            if tax.scope == 'concept':
                bounds = product_interval(tax.base, tax.rate, tax.amount, tax=True)
                record('F06', 'TAX_PRODUCT_INTERVAL', tax.amount.path,
                       'pending' if bounds is None else 'pass' if bounds['lower'] <= tax.amount.value <= bounds['upper'] else 'error',
                       reported=tax.amount.value, expected=bounds)
        else:
            record('F04', 'TAX_FACTOR', tax.path+'/@TipoFactor', 'error', reported=tax.factor)

    def group_key(tax):
        if tax.nature == Nature.RETENTION:
            return (tax.nature.value, tax.code, None, None)
        return (tax.nature.value, tax.code, tax.factor, tax.rate.value)

    def groups(taxes, *, rounding):
        grouped = defaultdict(list)
        for tax in taxes:
            grouped[group_key(tax)].append(tax)
        result = []
        for key, entries in grouped.items():
            nature, code, factor, rate = key
            exempt = factor == 'Exento'
            amount = None if exempt else complete_sum(t.amount.value for t in entries)
            base = complete_sum(t.base.value for t in entries) if nature == Nature.TRANSFER.value else None
            if rounding and digits is not None:
                amount = quantize(amount, digits) if amount is not None else None
                base = quantize(base, digits) if base is not None else None
            result.append({'nature': nature, 'code': code, 'factor': factor, 'rate': rate,
                           'amount': amount, 'base': base, 'source_paths': [t.path for t in entries]})
        return result

    conceptual = groups(concept_taxes, rounding=True)
    global_groups = groups(invoice.global_taxes, rounding=False)
    concept_map = {(g['nature'], g['code'], g['factor'], g['rate']): g for g in conceptual}
    global_seen = set()
    for tax in invoice.global_taxes:
        key = group_key(tax)
        record('F01' if tax.nature == Nature.TRANSFER else 'F02', 'GLOBAL_GROUP_UNIQUE', tax.path,
               'error' if key in global_seen else 'pass')
        global_seen.add(key)
        expected = concept_map.get(key)
        rule = 'F02' if tax.nature == Nature.RETENTION else 'F01'
        if expected is None:
            record(rule, 'GLOBAL_GROUP_WITHOUT_CONCEPT', tax.path, 'error')
        else:
            if tax.factor != 'Exento':
                compare(rule, 'GLOBAL_AMOUNT_VS_CONCEPTS', tax.amount.path, tax.amount.value, expected['amount'] if digits is not None else None)
            if version == '4.0' and tax.nature == Nature.TRANSFER:
                compare(rule, 'GLOBAL_BASE_VS_CONCEPTS', tax.base.path, tax.base.value, expected['base'] if digits is not None else None)
    for key, group in concept_map.items():
        # CFDI3.3 has no global Exento representation; CFDI4.0 does.
        if group['factor'] == 'Exento' and version == '3.3':
            continue
        if key not in global_seen:
            record('F05', 'GLOBAL_GROUP_MISSING', '/Comprobante/Impuestos', 'error', expected=group)

    selected, federal_totals, concept_totals = {}, {}, {}
    for nature, name in [(Nature.TRANSFER, 'TotalImpuestosTrasladados'), (Nature.RETENTION, 'TotalImpuestosRetenidos')]:
        gl = [g for g in global_groups if g['nature'] == nature.value]
        co = [g for g in conceptual if g['nature'] == nature.value]
        active_gl = [g for g in gl if g['factor'] != 'Exento']
        active_co = [g for g in co if g['factor'] != 'Exento']
        chosen = gl if gl else co
        selected[nature.value] = {'source': 'global-detail' if gl else 'concept-fallback' if co else 'no-applicable-nodes',
                                  'groups': chosen, 'total': complete_sum(g['amount'] for g in chosen if g['factor'] != 'Exento')}
        field = invoice.global_totals[name]
        validate_number(field, scale=digits if digits is not None else 6)
        if active_gl or active_co:
            if field.state == 'missing':
                record('F05', 'FEDERAL_AGGREGATE_MISSING', field.path, 'error')
            compare('F01' if nature == Nature.TRANSFER else 'F02', 'FEDERAL_AGGREGATE_VS_DETAILS', field.path,
                    field.value, complete_sum(g['amount'] for g in active_gl) if active_gl else None)
            federal_totals[nature.value] = field.value
        else:
            # Semantically inapplicable tax is zero; the original field remains missing in the DTO.
            federal_totals[nature.value] = ZERO if field.state == 'missing' else field.value
            if field.state != 'missing':
                compare('F05', 'AGGREGATE_WITHOUT_TAXABLE_DETAILS', field.path, field.value, ZERO)
        concept_totals[nature.value] = complete_sum(g['amount'] for g in active_co) if digits is not None else None

    local_reported = {Nature.TRANSFER: [], Nature.RETENTION: []}
    local_recalculated = {Nature.TRANSFER: [], Nature.RETENTION: []}
    for local in invoice.locals:
        for tax in local.taxes:
            validate_number(tax.amount, required=True, scale=2)
            validate_number(tax.rate, required=True, scale=2)
        for nature, field in [(Nature.TRANSFER, local.transfers), (Nature.RETENTION, local.retentions)]:
            validate_number(field, required=True, scale=2)
            total = complete_sum(t.amount.value for t in local.taxes if t.nature == nature)
            compare('F03', 'LOCAL_AGGREGATE_VS_DETAILS', field.path, field.value, total)
            local_reported[nature].append(field.value)
            local_recalculated[nature].append(total)
    local_reported = {n.value: complete_sum(v) for n, v in local_reported.items()}
    local_recalculated = {n.value: complete_sum(v) for n, v in local_recalculated.items()}
    for node in invoice.complements:
        if node.namespace == 'http://www.sat.gob.mx/implocal' and node.status != 'interpreted-local-1.0':
            local_recalculated = {n.value: None for n in Nature}
            local_reported = {n.value: None for n in Nature}

    subtotal = complete_sum(c.numbers['Importe'].value for c in invoice.concepts) if invoice.concepts else None
    concept_discounts = [c.numbers['Descuento'] for c in invoice.concepts if c.numbers['Descuento'].state != 'missing']
    discount = complete_sum(f.value for f in concept_discounts)
    if digits is not None:
        subtotal = quantize(subtotal, digits) if subtotal is not None else None
        discount = quantize(discount, digits) if discount is not None else None
    else:
        subtotal = discount = None
    compare('F06', 'SUBTOTAL_VS_CONCEPTS', root['SubTotal'].path, root['SubTotal'].value, subtotal)
    if concept_discounts:
        compare('F06', 'DISCOUNT_VS_CONCEPTS', root['Descuento'].path, root['Descuento'].value, discount)
        if root['Descuento'].state == 'missing':
            record('F06', 'HEADER_DISCOUNT_REQUIRED', root['Descuento'].path, 'error')
    elif root['Descuento'].state != 'missing':
        record('F06', 'HEADER_DISCOUNT_MUST_BE_OMITTED', root['Descuento'].path, 'error', reported=root['Descuento'].raw)
    header_discount = ZERO if root['Descuento'].state == 'missing' and not concept_discounts else root['Descuento'].value
    if header_discount is not None and root['SubTotal'].value is not None:
        record('F06', 'HEADER_DISCOUNT_LIMIT', root['Descuento'].path,
               'pass' if header_discount <= root['SubTotal'].value else 'error', reported=header_discount, expected=root['SubTotal'].value)

    def formula(sub, disc, federal, local):
        args = (sub, disc, federal['transfer'], federal['retention'], local['transfer'], local['retention'])
        if any(n is None for n in args) or digits is None or not supported or invoice.structural_issues:
            return None
        return quantize(sub-disc+federal['transfer']-federal['retention']+local['transfer']-local['retention'], digits)

    reported_formula = formula(root['SubTotal'].value, header_discount, federal_totals, local_reported)
    detail_formula = formula(root['SubTotal'].value, header_discount, {n: selected[n]['total'] for n in selected}, local_recalculated)
    concept_formula = formula(subtotal, discount, concept_totals, local_recalculated)
    compare('F03', 'TOTAL_VS_REPORTED_COMPONENTS', root['Total'].path, root['Total'].value, reported_formula)
    compare('F03', 'TOTAL_VS_TAX_DETAILS', root['Total'].path, root['Total'].value, detail_formula)
    iva_bases = [t for t in concept_taxes if t.code == '002' and t.nature == Nature.TRANSFER]
    bases = {
        'exempt': complete_sum(t.base.value for t in iva_bases if t.factor == 'Exento'),
        'zero_rate': complete_sum(t.base.value for t in iva_bases if t.factor == 'Tasa' and t.rate.value == ZERO),
        'scope': 'concept IVA transfers only; no global/concept union',
    }
    summary = {}
    for nature, selection in selected.items():
        for code in TAX_NAMES:
            relevant = [g for g in selection['groups'] if g['code'] == code and g['factor'] != 'Exento']
            summary[f'{TAX_NAMES[code]}_{nature}'] = complete_sum(g['amount'] for g in relevant)
    status = 'error' if any(f['status'] == 'error' for f in findings) else 'partial' if findings else 'consistent-in-scope'
    return {'ruleset': RULESET_VERSION, 'status': status, 'scope': 'CFDI I/E P0 reconciliation; not full SAT validation',
            'currency': currency, 'currency_digits': digits, 'issue_date': issue_date,
            'reported': {'subtotal': root['SubTotal'], 'discount': root['Descuento'], 'total': root['Total'],
                         'federal': invoice.global_totals, 'local': local_reported},
            'recalculated': {'subtotal_from_concepts': subtotal, 'discount_from_concepts': discount,
                             'federal_concept_groups': conceptual, 'federal_global_groups': global_groups,
                             'selected_federal': selected, 'federal_by_code': summary, 'local_details': local_recalculated,
                             'iva_bases': bases, 'total_from_reported_components': reported_formula,
                             'total_from_tax_details': detail_formula, 'total_from_concepts': concept_formula,
                             'difference_total_minus_details': root['Total'].value-detail_formula
                             if root['Total'].value is not None and detail_formula is not None else None},
            'checks': checks, 'findings': findings,
            'not_validated': ['SAT status/cancellation', 'signature/certificate', 'deductibility/accreditability',
                              'complete catalog history', 'other SAT technical rules', 'unsupported complements']}
