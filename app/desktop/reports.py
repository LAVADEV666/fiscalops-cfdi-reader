"""One authoritative report/selection contract shared by the UI totals and all exports."""
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, localcontext
from app.fiscal.numbers import DECIMAL_CONTEXT, complete_sum, number
from app.fiscal.models import to_data

DETAIL_REPORTS = set(('concepts conceptTaxes globalTaxes relations payments paymentDocs paymentTaxes '
                      'payrollPerceptions payrollDeductions payrollOtherPayments payrollIncapacities payrollOvertime '
                      'locations goods transportFigures complements findings').split())
REPORTS = DETAIL_REPORTS | {'summary', 'missingMetadata', 'canceled', 'duplicates', 'readErrors'}
METRICS = ('Subtotal', 'Descuento', 'IVA', 'Retenciones', 'Total')
ANALYSES = ('resumen', 'monedas', 'mensual', 'contrapartes', 'pagos', 'impuestos', 'conceptos')


def decimal_value(value):
    if isinstance(value, (int, Decimal)):
        return Decimal(value)
    return number(value, '/report').value if isinstance(value, str) else None


def total(rows, key):
    with localcontext(DECIMAL_CONTEXT):
        return complete_sum(decimal_value(r.get('_aggregateValues', {}).get(key, r.get(key))) for r in rows)


def selected_documents(dataset, ids):
    if not isinstance(ids, list) or len(ids) != len(set(ids)):
        raise ValueError('SELECTION_IDS_INVALID')
    index = {row['_docId']: row for row in dataset['rows']}
    if any(identity not in index for identity in ids):
        raise ValueError('SELECTION_STALE_OR_UNKNOWN')
    return [index[identity] for identity in ids]


def report_rows(dataset, report, documents, row_ids=None):
    if report not in REPORTS:
        raise ValueError('REPORT_UNKNOWN')
    if report == 'readErrors':
        rows = dataset['errors']
    elif report == 'summary':
        rows = documents
    elif report in ('missingMetadata', 'canceled', 'duplicates'):
        rows = [r for r in documents if (r['EstatusSAT'] == 'SIN METADATA' if report == 'missingMetadata' else
                r['EstatusSAT'] == 'CANCELADO' if report == 'canceled' else 'UUID_DUPLICADO' in r.get('ObservacionesXML', ''))]
    else:
        rows = [item for row in documents for item in row['_details'][report]]
    if row_ids is not None:
        index = {r['_rowId']: r for r in rows}
        if not isinstance(row_ids, list) or len(row_ids) != len(set(row_ids)) or set(row_ids) != set(index):
            raise ValueError('REPORT_ROW_SELECTION_MISMATCH')
        rows = [index[key] for key in row_ids]
    return rows


def grouped(rows, key):
    groups = defaultdict(list)
    for row in rows:
        groups[key(row)].append(row)
    return groups


def aggregate(rows):
    return to_data([dict(Moneda=code, CFDI=len(items), **{key: total(items, key) for key in METRICS})
                    for code, items in sorted(grouped(rows, lambda r: r.get('Moneda') or 'SIN MONEDA').items())])


def money_formats(value):
    """Display rounding belongs to Decimal in the worker, not Number/Intl in the browser."""
    result = {}
    def visit(item):
        if isinstance(item, dict):
            for key, child in item.items():
                if key not in ('XMLRaw', '_XMLRaw'):
                    visit(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                visit(child)
        elif isinstance(item, (str, int, Decimal)):
            dec = decimal_value(item)
            if dec is not None:
                with localcontext(DECIMAL_CONTEXT):
                    result[str(item)] = '$'+format(dec.quantize(Decimal('.01')), ',.2f')
    visit(value)
    return result


def columns(specs):
    return [{'id': spec[0], 'label': spec[1], 'dataType': spec[2] if len(spec) > 2 else 'text',
             'width': spec[3] if len(spec) > 3 else 160} for spec in specs]


METRIC_COLUMNS = columns([(key, key, 'currency') for key in METRICS])


def analysis_sheets(documents, report_rows_, analyses, rfc, context, concept_columns):
    with localcontext(DECIMAL_CONTEXT):
        return _sheets(documents, report_rows_, analyses, rfc.upper(), context, concept_columns)


def _sheets(docs, main_rows, analyses, rfc, context, concept_columns):
    if any(key not in ANALYSES for key in analyses) or len(analyses) != len(set(analyses)):
        raise ValueError('ANALYSIS_UNKNOWN_OR_DUPLICATE')
    sheets = []
    for key in analyses:
        rows, cols = [], []
        if key == 'resumen':
            indicators = [('Tipo de reporte', context.get('report_label', '')), ('Tipo de CFDI', context.get('type_label', 'Todos')),
                          ('CFDI filtrados', len(docs)), ('Filas de la hoja Reporte', len(main_rows)),
                          ('Columnas seleccionadas', context.get('column_count', 0)),
                          ('Emitidos', sum(r.get('RFCEmisor', '').upper() == rfc for r in docs) if rfc else 0),
                          ('Recibidos', sum(r.get('RFCReceptor', '').upper() == rfc for r in docs) if rfc else 0)]
            indicators += [(label, sum(r['EstatusSAT'] == status for r in docs)) for label, status in
                           [('Vigentes', 'VIGENTE'), ('Cancelados', 'CANCELADO'), ('Sin metadata', 'SIN METADATA')]]
            indicators.append(('Generado', datetime.now().astimezone().isoformat(timespec='seconds')))
            rows = [{'Indicador': label, 'Valor': value, 'Detalle': ''} for label, value in indicators]
            cols = columns([('Indicador', 'Indicador'), ('Valor', 'Valor'), ('Detalle', 'Detalle')])
        elif key in ('monedas', 'mensual'):
            groups = grouped(docs, lambda r: (r.get('FechaEmisionISO', '')[:7], r.get('Moneda') or 'SIN MONEDA') if key == 'mensual' else (r.get('Moneda') or 'SIN MONEDA',))
            for identity, items in sorted(groups.items()):
                item = {'Moneda': identity[-1], 'CFDI': len(items), **{metric: total(items, metric) for metric in METRICS}}
                if key == 'mensual':
                    item['Periodo'] = identity[0]
                else:
                    item['Descripcion'] = context.get('currency_labels', {}).get(identity[0], '')
                rows.append(item)
            cols = columns(([('Periodo', 'Periodo')] if key == 'mensual' else [])+[('Moneda', 'Moneda')]+([] if key == 'mensual' else [('Descripcion', 'Descripción')])+[('CFDI', 'CFDI', 'number')])+METRIC_COLUMNS
        elif key == 'contrapartes':
            def counterparty(r):
                side = 'EMITIDOS' if rfc and r.get('RFCEmisor', '').upper() == rfc else 'RECIBIDOS' if rfc and r.get('RFCReceptor', '').upper() == rfc else 'OTROS'
                suffix = 'Receptor' if side == 'EMITIDOS' else 'Emisor'
                return side, r.get('RFC'+suffix, ''), r.get('Nombre'+suffix, ''), r.get('Moneda') or 'SIN MONEDA'
            for identity, items in grouped(docs, counterparty).items():
                rows.append(dict(zip(('Origen', 'RFC', 'Nombre', 'Moneda'), identity), CFDI=len(items),
                                 **{metric: total(items, metric) for metric in ('Subtotal', 'IVA', 'Retenciones', 'Total')}))
            cols = columns([('Origen', 'Origen'), ('RFC', 'RFC'), ('Nombre', 'Nombre'), ('Moneda', 'Moneda'), ('CFDI', 'CFDI', 'number')])+[c for c in METRIC_COLUMNS if c['id'] != 'Descuento']
        elif key == 'pagos':
            for identity, items in grouped(docs, lambda r: (r.get('FormaPago') or 'SIN DATO', r.get('MetodoPago') or 'SIN DATO', r.get('Moneda') or 'SIN MONEDA')).items():
                fp, mp, mon = identity
                rows.append({'FormaPago': fp, 'FormaPagoDescripcion': context.get('form_labels', {}).get(fp, ''),
                             'MetodoPago': mp, 'MetodoPagoDescripcion': context.get('method_labels', {}).get(mp, ''),
                             'Moneda': mon, 'CFDI': len(items), 'Total': total(items, 'Total')})
            cols = columns([('FormaPago', 'Forma de pago'), ('FormaPagoDescripcion', 'Descripción forma'), ('MetodoPago', 'Método de pago'),
                            ('MetodoPagoDescripcion', 'Descripción método'), ('Moneda', 'Moneda'), ('CFDI', 'CFDI', 'number'), ('Total', 'Total', 'currency')])
        elif key == 'impuestos':
            metrics = {'BaseIVA16': 'IVA Trasladado 16 Base', 'IVA16': 'IVA Trasladado 16 Importe', 'BaseIVA8': 'IVA Trasladado 8 Base',
                       'IVA8': 'IVA Trasladado 8 Importe', 'BaseIVA0': 'IVA Trasladado 0 Base', 'BaseExenta': 'IVA Exento Base',
                       'IEPS': 'IEPS Trasladado Importe', 'ISRRetenido': 'ISR Retenido Importe', 'IVARetenido': 'IVA Retenido Importe',
                       'ISH': 'ISHImporte', 'TUA': 'TUAImporte'}
            for code, items in sorted(grouped(docs, lambda r: r.get('Moneda') or 'SIN MONEDA').items()):
                loc = complete_sum([total(items, 'ImpuestosLocalesTotalTraslados'), total(items, 'ImpuestosLocalesTotalRetenciones')])
                rows.append({'Moneda': code, 'CFDI': len(items), **{field: total(items, source) for field, source in metrics.items()}, 'Locales': loc})
            labels = {'BaseIVA16': 'Base IVA 16%', 'IVA16': 'IVA 16%', 'BaseIVA8': 'Base IVA 8%', 'IVA8': 'IVA 8%',
                      'BaseIVA0': 'Base tasa 0', 'BaseExenta': 'Base exenta', 'IEPS': 'IEPS trasladado',
                      'ISRRetenido': 'ISR retenido', 'IVARetenido': 'IVA retenido', 'Locales': 'Impuestos locales'}
            cols = columns([('Moneda', 'Moneda'), ('CFDI', 'CFDI', 'number')]+[(field, labels.get(field, field), 'currency') for field in (*list(metrics)[:-2], 'Locales', 'ISH', 'TUA')])
        else:
            rows = [item for row in docs for item in row['_details']['concepts']]
            cols = concept_columns
        sheets.append({'name': {'resumen': 'Resumen', 'monedas': 'Totales por moneda', 'mensual': 'Análisis mensual',
                               'contrapartes': 'Contrapartes', 'pagos': 'Formas y métodos', 'impuestos': 'Análisis impuestos', 'conceptos': 'Conceptos'}[key],
                       'rows': rows, 'cols': cols})
    return sheets
