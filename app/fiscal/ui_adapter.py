"""Adapt the offline inspection to the existing V21 report/preview column contract.

No Qt objects and no browser calculations. Complement projections preserve reports;
they do not expand the engine's normative validation coverage.
"""
from decimal import Decimal, localcontext
import re
from lxml import etree
from .models import Nature, to_data
from .numbers import DECIMAL_CONTEXT, ZERO, complete_sum, number
from .reader import xml_parser

DETAIL_KEYS = ('concepts conceptTaxes globalTaxes relations payments paymentDocs paymentTaxes '
               'payrollPerceptions payrollDeductions payrollOtherPayments payrollIncapacities payrollOvertime '
               'locations goods transportFigures complements findings').split()
NUMERIC_ATTRS = set(('Cantidad ValorUnitario Importe Descuento Base TasaOCuota TipoCambio Monto TipoCambioP '
                    'EquivalenciaDR ImpSaldoAnt ImpPagado ImpSaldoInsoluto NumDiasPagados TotalPercepciones '
                    'TotalDeducciones TotalOtrosPagos SalarioBaseCotApor SalarioDiarioIntegrado ImporteGravado '
                    'ImporteExento SubsidioCausado ImporteMonetario ImportePagado Dias HorasExtra '
                    'DistanciaRecorrida PesoEnKg ValorMercancia TotalDistRec').split())


def decimal_attr(value):
    return number(value, '/projection').value


def display_date(value):
    if not value:
        return ''
    match = re.match(r'^(\d{4})-(\d{2})-(\d{2})', value)
    return '/'.join((match[3], match[2], match[1])) if match else value


def adapt_inspection(inspection, document_id, filename):
    with localcontext(DECIMAL_CONTEXT):
        return to_data(_adapt(inspection, document_id, filename))


def _adapt(inspection, document_id, filename):
    doc, analysis = inspection['document'], inspection['analysis']
    attrs, calc = doc.attributes, analysis['recalculated']
    root = etree.fromstring(doc.original, parser=xml_parser())
    tag = lambda name: '{'+doc.namespace+'}'+name
    row = {'_docId': document_id, '_rowId': document_id, 'SHA256': doc.sha256,
           'ArchivoOrigen': filename, 'MotorFiscal': doc.parser_version, 'ReglasFiscales': analysis['ruleset'],
           'VersionCFDI': doc.version, 'UUID': doc.uuid or '', 'Fecha': display_date(attrs.get('Fecha')),
           'FechaEmisionISO': attrs.get('Fecha'), 'Año': attrs.get('Fecha', '')[:4], 'Mes': attrs.get('Fecha', '')[5:7],
           'XMLRaw': doc.original.decode(doc.encoding).lstrip('\ufeff'), 'EstatusSAT': 'SIN METADATA',
           'FechaCancelacionSAT': '', 'EstatusSATMetadata': 'SIN METADATA', 'FechaCancelacionMetadata': '',
           'ValidacionXSD': inspection['validation']['xsd']['status'], 'ValidacionFirma': 'NO VALIDADA',
           'ValidacionSATOficial': 'NO CONSULTADA'}
    row.update(attrs)
    row['Fecha'] = display_date(attrs.get('Fecha'))
    row['Subtotal'] = doc.numbers['SubTotal'].value
    row['Descuento'] = doc.numbers['Descuento'].value
    row['Total'] = doc.numbers['Total'].value
    row['TipoCambio'] = doc.numbers['TipoCambio'].value
    row.update({'RFCEmisor': doc.issuer.get('Rfc', ''), 'NombreEmisor': doc.issuer.get('Nombre', ''),
                'RegimenFiscalEmisor': doc.issuer.get('RegimenFiscal', ''), 'FacAtrAdquirente': doc.issuer.get('FacAtrAdquirente', ''),
                'RFCReceptor': doc.receiver.get('Rfc', ''), 'NombreReceptor': doc.receiver.get('Nombre', ''),
                'RegimenFiscalReceptor': doc.receiver.get('RegimenFiscalReceptor', ''),
                'DomicilioFiscalReceptor': doc.receiver.get('DomicilioFiscalReceptor', ''),
                'UsoCFDI': doc.receiver.get('UsoCFDI', ''), 'ResidenciaFiscalReceptor': doc.receiver.get('ResidenciaFiscal', ''),
                'NumRegIdTribReceptor': doc.receiver.get('NumRegIdTrib', '')})
    kind = attrs.get('TipoDeComprobante', '')
    row['TipoCFDIEspecial'] = {'I': 'INGRESO', 'E': 'EGRESO', 'P': 'COMPLEMENTO_PAGO', 'N': 'NOMINA', 'T': 'TRASLADO'}.get(kind, 'OTRO')
    row['EfectoDescripcion'] = {'I': 'Ingreso', 'E': 'Egreso', 'P': 'Pago', 'N': 'Nómina', 'T': 'Traslado'}.get(kind, '')
    details = {key: [] for key in DETAIL_KEYS}
    row['_details'] = details

    def add(key, values):
        item = {k: row.get(k, '') for k in ('UUID', 'Fecha', 'TipoDeComprobante', 'RFCEmisor', 'NombreEmisor', 'RFCReceptor', 'NombreReceptor', 'EstatusSAT')}
        item.update(values)
        item.update(_docId=document_id, _rowId=f'{document_id}:{key}:{len(details[key])+1}')
        details[key].append(item)
        return item

    def copied(node, names=None):
        return {k: decimal_attr(v) if k in NUMERIC_ATTRS else v for k, v in node.attrib.items() if names is None or k in names}

    def add_tax(key, tax):
        return add(key, {'ConceptoIndice': tax.concept_index, 'NivelImpuesto': {'concept': 'CONCEPTO', 'global': 'GLOBAL', 'local': 'LOCAL'}[tax.scope],
                         'Naturaleza': 'Retención' if tax.nature == Nature.RETENTION else 'Traslado',
                         'Base': tax.base.value, 'Impuesto': tax.code or tax.local_name, 'TipoFactor': tax.factor,
                         'TasaOCuota': tax.rate.value, 'Importe': tax.amount.value})

    checks = {c['path']: c for c in analysis['checks'] if c['code'] == 'CONCEPT_PRODUCT_INTERVAL'}
    for concept in doc.concepts:
        values = dict(concept.attributes)
        for key, field in concept.numbers.items():
            values[key] = field.value
        values['DescuentoConcepto'] = values.pop('Descuento', None)
        check = checks.get(concept.path+'/@Importe')
        values['ConceptoIndice'] = concept.index
        values['ValidacionImporte'] = {'pass': 'CORRECTO', 'error': 'REVISAR'}.get(check['status'], 'NO EVALUADO') if check else 'NO EVALUADO'
        exact = (check.get('expected') or {}).get('exact_product') if check else None
        values['DiferenciaCalculada'] = values['Importe']-exact if values['Importe'] is not None and exact is not None else None
        add('concepts', values)
        for tax in concept.taxes:
            add_tax('conceptTaxes', tax)
    for tax in doc.global_taxes:
        add_tax('globalTaxes', tax)
    for local in doc.locals:
        for tax in local.taxes:
            add_tax('globalTaxes', tax)
    row['CantidadConceptos'] = len(doc.concepts)
    for dest, source in [('Conceptos', 'Descripcion'), ('ConceptosClaveProdServ', 'ClaveProdServ'), ('ConceptosObjetoImp', 'ObjetoImp'), ('ConceptosImporte', 'Importe')]:
        row[dest] = '|'.join(str(c[source]) for c in details['concepts'] if c.get(source) is not None)
    codes = calc['federal_by_code']
    row['IVA'] = codes['IVA_transfer']
    row['Retenciones'] = calc['selected_federal']['retention']['total']
    row['TotalImpuestosTrasladadosReportado'] = doc.global_totals['TotalImpuestosTrasladados'].value
    row['TotalImpuestosRetenidosReportado'] = doc.global_totals['TotalImpuestosRetenidos'].value
    row['Total Traslados Detalle'] = calc['selected_federal']['transfer']['total']
    row['Total Retenciones Detalle'] = calc['selected_federal']['retention']['total']
    row['DiferenciaCalculada'] = calc['difference_total_minus_details']
    row['TotalRecalculado'] = calc['total_from_tax_details']
    row['TotalRecalculadoConceptos'] = calc['total_from_concepts']
    concept_iva = complete_sum(g['amount'] for g in calc['federal_concept_groups'] if g['nature'] == 'transfer' and g['code'] == '002' and g['factor'] != 'Exento') if kind in ('I', 'E') else None
    concept_ret = complete_sum(g['amount'] for g in calc['federal_concept_groups'] if g['nature'] == 'retention') if kind in ('I', 'E') else None
    row['Diferencia IVA vs Detalle'] = row['IVA']-concept_iva if row['IVA'] is not None and concept_iva is not None else None
    row['Diferencia Retenciones vs Detalle'] = row['Retenciones']-concept_ret if row['Retenciones'] is not None and concept_ret is not None else None
    for label, key in [('IEPS Trasladado Importe', 'IEPS_transfer'), ('ISR Retenido Importe', 'ISR_retention'),
                       ('IVA Retenido Importe', 'IVA_retention'), ('IEPS Retenido Importe', 'IEPS_retention')]:
        row[label] = codes[key]
    for percentage, rate in [('16', Decimal('.16')), ('8', Decimal('.08')), ('0', ZERO)]:
        groups = [g for g in calc['federal_concept_groups'] if g['nature'] == 'transfer' and g['code'] == '002' and g['factor'] == 'Tasa' and g['rate'] == rate]
        for suffix, key in [('Base', 'base'), ('Importe', 'amount')]:
            row[f'IVA Trasladado {percentage} {suffix}'] = complete_sum(g[key] for g in groups) if kind in ('I', 'E') else None
    row['IVA Exento Base'] = calc['iva_bases']['exempt']
    row['BaseTasa0'], row['BaseExenta'] = calc['iva_bases']['zero_rate'], calc['iva_bases']['exempt']
    row['BaseIVA16'], row['IVA16'] = row['IVA Trasladado 16 Base'], row['IVA Trasladado 16 Importe']
    row['BaseIVA8'], row['IVA8'] = row['IVA Trasladado 8 Base'], row['IVA Trasladado 8 Importe']
    row['ImpuestosLocalesTotalTraslados'] = complete_sum(loc.transfers.value for loc in doc.locals) if doc.locals else ZERO
    row['ImpuestosLocalesTotalRetenciones'] = complete_sum(loc.retentions.value for loc in doc.locals) if doc.locals else ZERO
    local_entries = [tax for loc in doc.locals for tax in loc.taxes]
    for field, regex in [('ISH', r'\bISH\b|HOSPEDAJE'), ('TUA', r'\bTUA\b|AEROPUER')]:
        entries = [t for t in local_entries if t.nature == Nature.TRANSFER and re.search(regex, t.local_name or '', re.I)]
        row[field+'Importe'] = complete_sum(t.amount.value for t in entries)
        row['ISHDetectado' if field == 'ISH' else 'TUADetectada'] = 'SÍ' if entries else 'NO'
        row[field+'Detalle'] = '|'.join(f'{t.local_name}:{t.amount.raw}' for t in entries)
        if field == 'ISH':
            row['ISHTasa'] = '|'.join(t.rate.raw or '' for t in entries)
    for nature, dest in [(Nature.TRANSFER, 'ImpuestosLocalesTrasladosDetalle'), (Nature.RETENTION, 'ImpuestosLocalesRetencionesDetalle')]:
        row[dest] = '|'.join(f'{t.local_name}:{t.amount.raw}' for t in local_entries if t.nature == nature)
    for nature, dest in [('Traslado', 'TrasladosDetalle'), ('Retención', 'RetencionesDetalle')]:
        row[dest] = '|'.join(','.join(f'{k}:{t.get(k)}' for k in ('Base', 'Impuesto', 'TipoFactor', 'TasaOCuota', 'Importe'))
                             for t in details['globalTaxes'] if t['NivelImpuesto'] == 'GLOBAL' and t['Naturaleza'] == nature)
    for gi, group in enumerate(root.findall(tag('CfdiRelacionados')), 1):
        for ri, relation in enumerate(group.findall(tag('CfdiRelacionado')), 1):
            add('relations', {'GrupoRelacionIndice': gi, 'RelacionIndice': ri, 'TipoRelacion': group.get('TipoRelacion'),
                              'UUIDRelacionado': relation.get('UUID'), 'EstadoRelacionadoLocal': 'NO DISPONIBLE'})
    row['TipoRelacion'] = '|'.join(dict.fromkeys(r.get('TipoRelacion', '') for r in details['relations']))
    row['UUIDRelacionado'] = '|'.join(r.get('UUIDRelacionado', '') for r in details['relations'])
    for node in doc.complements:
        add('complements', {'ComplementoIndice': len(details['complements'])+1, 'Complemento': node.local_name,
                            'NamespaceURI': node.namespace, 'VersionComplemento': node.version,
                            'EstadoInterpretacion': node.status})
        if node.namespace == 'http://www.sat.gob.mx/TimbreFiscalDigital' and node.local_name == 'TimbreFiscalDigital' and node.version == '1.1':
            timbre = etree.fromstring(node.xml.encode(), parser=xml_parser())
            row.update(FechaTimbrado=display_date(timbre.get('FechaTimbrado')), NoCertificadoSAT=timbre.get('NoCertificadoSAT'), RfcProvCertif=timbre.get('RfcProvCertif'))
        _project_complement(node, row, details, add, copied)
    row['ComplementosDetectados'] = ' | '.join(f'{n.local_name} {n.version or ""}'.strip() for n in doc.complements)
    for entry in analysis['findings']:
        add('findings', {'HallazgoIndice': len(details['findings'])+1, 'Severidad': 'ERROR' if entry['status'] == 'error' else 'INFORMACIÓN',
                         'CategoriaRegla': entry['rule'], 'CodigoHallazgo': entry['code'], 'MensajeHallazgo': entry['code']+' · '+entry['path'],
                         'ReferenciaRegla': ' | '.join(entry['reference']['supporting_sat_codes'] or entry['reference']['source_ids']),
                         'Diferencia': None, 'Reportado': entry['reported'], 'Esperado': entry['expected']})
    xsd = inspection['validation']['xsd']['status']
    if xsd != 'pass':
        add('findings', {'HallazgoIndice': len(details['findings'])+1, 'Severidad': 'ERROR' if xsd == 'fail' else 'INFORMACIÓN',
                         'CategoriaRegla': 'XSD LOCAL', 'CodigoHallazgo': 'XSD_'+xsd.upper(),
                         'MensajeHallazgo': 'Validación XSD '+xsd+'; no equivale a validación oficial SAT.', 'ReferenciaRegla': 'Anexo20 / instantánea local', 'Diferencia': None})
    row['ResultadoValidacion'] = 'ERROR' if analysis['status'] == 'error' or xsd == 'fail' else 'REVISAR' if analysis['status'] == 'partial' or xsd == 'pending' else 'SIN DIFERENCIAS'
    row['EstatusXML'] = row['ResultadoValidacion']
    row['HallazgosConteo'] = len(details['findings'])
    row['ObservacionesXML'] = '|'.join(f['CodigoHallazgo'] for f in details['findings'])
    row['ImpuestosAnalisis'] = row['ObservacionesXML']
    row['TarifasDetectadas'], row['TarifasDetalle'] = 'NO INTERPRETADO', ''
    # Explicit non-applicable discount contributes zero only to aggregates; the displayed source stays NULL.
    row['_aggregateValues'] = {'Descuento': calc['discount_from_concepts'] if row['Descuento'] is None and not any(c.numbers['Descuento'].state != 'missing' for c in doc.concepts) else row['Descuento']}
    return row


def _project_complement(preserved, row, details, add, copied):
    """Namespace/version allowlist for existing read-only complement report projections."""
    ns, version, name = preserved.namespace, preserved.version, preserved.local_name
    known = ((name == 'Pagos' and (ns, version) in (('http://www.sat.gob.mx/Pagos20', '2.0'), ('http://www.sat.gob.mx/Pagos', '1.0'))) or
             (name == 'Nomina' and ns == 'http://www.sat.gob.mx/nomina12' and version == '1.2') or
             (name == 'CartaPorte' and (ns, version) in (('http://www.sat.gob.mx/CartaPorte20', '2.0'), ('http://www.sat.gob.mx/CartaPorte30', '3.0'), ('http://www.sat.gob.mx/CartaPorte31', '3.1'))))
    if not known:
        return
    root = etree.fromstring(preserved.xml.encode(), parser=xml_parser())
    tag = lambda local: '{'+ns+'}'+local
    if name == 'Pagos':
        total_node = root.find(tag('Totales'))
        if total_node is not None:
            for key, val in total_node.attrib.items():
                row['Pago'+key] = decimal_attr(val)
        for pi, payment in enumerate(root.findall(tag('Pago')), 1):
            pay = add('payments', dict(copied(payment), PagoIndice=pi))
            documents = payment.findall(tag('DoctoRelacionado'))
            pay['NumDocumentosRelacionados'] = len(documents)
            for di, node in enumerate(documents, 1):
                item = add('paymentDocs', dict(copied(node), PagoIndice=pi, DocumentoIndice=di))
                values = [item.get(k) for k in ('ImpSaldoAnt', 'ImpPagado', 'ImpSaldoInsoluto')]
                item['DiferenciaSaldo'] = values[0]-values[1]-values[2] if all(v is not None for v in values) else None
                item['ValidacionSaldo'] = 'NO EVALUADO'  # REP normative rules are outside current engine coverage.
                _payment_taxes(node.find(tag('ImpuestosDR')), ns, 'DR', add, pi, di, item.get('IdDocumento'), pay.get('MonedaP'))
            _payment_taxes(payment.find(tag('ImpuestosP')), ns, 'P', add, pi, None, None, pay.get('MonedaP'))
        pays = details['payments']
        row['PagoNumeroPagos'], row['PagoNumeroDocumentos'] = len(pays), len(details['paymentDocs'])
        converted = []
        for p in pays:
            rate = Decimal('1') if p.get('MonedaP') == 'MXN' else p.get('TipoCambioP')
            converted.append(p.get('Monto')*rate if p.get('Monto') is not None and rate is not None else None)
        row['PagoMontoCalculadoMXN'] = complete_sum(converted)
        reported = row.get('PagoMontoTotalPagos')
        row['PagoDiferenciaTotal'] = reported-row['PagoMontoCalculadoMXN'] if reported is not None and row['PagoMontoCalculadoMXN'] is not None else None
        for field in ('FechaPago', 'FormaDePagoP', 'MonedaP', 'TipoCambioP', 'Monto', 'NumOperacion', 'CtaBeneficiario'):
            row['Pago'+field] = '|'.join(str(p.get(field, '')) for p in pays)
    elif name == 'Nomina':
        row.update(copied(root))
        row['FechaPagoNomina'] = row.pop('FechaPago', None)
        for part in ('Emisor', 'Receptor'):
            node = root.find(tag(part))
            if node is not None:
                row.update(copied(node))
        row['CURP'], row['Antiguedad'] = row.get('Curp', ''), row.get('Antigüedad', '')
        specs = [('Percepciones', 'Percepcion', 'payrollPerceptions'), ('Deducciones', 'Deduccion', 'payrollDeductions'),
                 ('OtrosPagos', 'OtroPago', 'payrollOtherPayments'), ('Incapacidades', 'Incapacidad', 'payrollIncapacities')]
        for parent, child, key in specs:
            for node in root.findall(tag(parent)+'/'+tag(child)):
                item = add(key, dict(copied(node), DetalleIndice=len(details[key])+1, NumEmpleado=row.get('NumEmpleado')))
                if key == 'payrollPerceptions':
                    item['Importe'] = complete_sum([item.get('ImporteGravado'), item.get('ImporteExento')])
                    for hour in node.findall(tag('HorasExtra')):
                        values = copied(hour)
                        add('payrollOvertime', dict(values, Importe=values.get('ImportePagado'), DetalleIndice=len(details['payrollOvertime'])+1, NumEmpleado=row.get('NumEmpleado')))
                if key == 'payrollOtherPayments':
                    subsidy = node.find(tag('SubsidioAlEmpleo'))
                    item['SubsidioCausado'] = decimal_attr(subsidy.get('SubsidioCausado')) if subsidy is not None else None
                if key == 'payrollIncapacities':
                    item['Importe'] = item.get('ImporteMonetario')
    else:
        row['CartaPorteDetectada'], row['CartaPorteVersion'] = 'SÍ', version
        for local, key, index in [('Ubicacion', 'locations', 'UbicacionIndice'), ('Mercancia', 'goods', 'MercanciaIndice'), ('TiposFigura', 'transportFigures', 'FiguraIndice')]:
            for node in root.iter(tag(local)):
                item = add(key, dict(copied(node), **{index: len(details[key])+1}))
                if key == 'goods':
                    item['CantidadMercancia'], item['ClaveUnidadMercancia'] = item.get('Cantidad'), item.get('ClaveUnidad')
        row['CartaPorteNumeroMercancias'], row['CartaPorteNumeroUbicaciones'] = len(details['goods']), len(details['locations'])
        row['CartaPorteDistanciaTotal'] = complete_sum(item.get('DistanciaRecorrida') for item in details['locations'])


def _payment_taxes(container, namespace, suffix, add, pi, di, document, currency):
    if container is None:
        return
    for nature, group, item in [('Traslado', 'Traslados', 'Traslado'), ('Retención', 'Retenciones', 'Retencion')]:
        for node in container.findall('{'+namespace+'}'+group+suffix+'/{'+namespace+'}'+item+suffix):
            values = {key: decimal_attr(node.get(key+suffix)) for key in ('Base', 'TasaOCuota', 'Importe')}
            values.update(Impuesto=node.get('Impuesto'+suffix), TipoFactor=node.get('TipoFactor'+suffix), Naturaleza=nature,
                          NivelImpuesto='DOCUMENTO' if suffix == 'DR' else 'PAGO', PagoIndice=pi, DocumentoIndice=di,
                          IdDocumento=document, MonedaP=currency)
            add('paymentTaxes', values)
