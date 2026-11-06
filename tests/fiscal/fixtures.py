"""Synthetic arithmetical fixtures. XSD conformity does not make these signed/issued CFDIs."""
from lxml import etree as E

NS = {'4.0': 'http://www.sat.gob.mx/cfd/4', '3.3': 'http://www.sat.gob.mx/cfd/3'}
LOCAL = 'http://www.sat.gob.mx/implocal'


def tax(code='002', base='100', rate='0.160000', amount='16', factor='Tasa', nature='transfer'):
    return dict(code=code, base=base, rate=rate, amount=amount, factor=factor, nature=nature)


def concept(amount='100', taxes=None, discount=None, quantity='1', unit=None):
    return dict(amount=amount, taxes=[] if taxes is None else taxes, discount=discount,
                quantity=quantity, unit=amount if unit is None else unit)


def invoice(*, version='4.0', concepts=None, globals=None, subtotal='100', total='116', discount=None,
            aggregate_transfer='16', aggregate_retention=None, currency='MXN', locals=None,
            prefix='cfdi', encoding='UTF-8', extra=None, date=None, document_type='I'):
    ns = NS[version]
    tag = lambda name: '{'+ns+'}'+name
    root = E.Element(tag('Comprobante'), nsmap={prefix: ns, 'implocal': LOCAL})
    attrs = dict(Version=version, Fecha=date or ('2026-11-06T12:34:56' if version == '4.0' else '2023-03-01T12:34:56'),
                 Sello='QUFB', NoCertificado='00001000000500000000', Certificado='QUFB',
                 Moneda=currency, TipoDeComprobante=document_type, LugarExpedicion='06000', MetodoPago='PUE', FormaPago='03')
    if version == '4.0':
        attrs['Exportacion'] = '01'
    if currency not in ('MXN', 'XXX'):
        attrs['TipoCambio'] = '20.000000'
    for name, value in [('SubTotal', subtotal), ('Total', total), ('Descuento', discount)]:
        if value is not None:
            attrs[name] = value
    root.attrib.update(attrs)
    E.SubElement(root, tag('Emisor'), Rfc='AAA010101AAA', Nombre='EMPRESA SINTÉTICA ÁRBOL', RegimenFiscal='601')
    recipient = E.SubElement(root, tag('Receptor'), Rfc='BBB010101BB1', Nombre='RECEPTOR SINTÉTICO', UsoCFDI='G03')
    if version == '4.0':
        recipient.attrib.update({'DomicilioFiscalReceptor': '06000', 'RegimenFiscalReceptor': '601'})

    def taxes(parent, specs, *, global_scope=False):
        node = E.SubElement(parent, tag('Impuestos'))
        # Schema order is concept: Traslados, Retenciones; global: Retenciones, Traslados.
        order = ['retention', 'transfer'] if global_scope else ['transfer', 'retention']
        for nature in order:
            entries = [s for s in specs if s['nature'] == nature]
            if not entries:
                continue
            group = E.SubElement(node, tag('Traslados' if nature == 'transfer' else 'Retenciones'))
            for spec in entries:
                child = E.SubElement(group, tag('Traslado' if nature == 'transfer' else 'Retencion'), Impuesto=spec['code'])
                if not (global_scope and nature == 'retention'):
                    child.set('TipoFactor', spec['factor'])
                    if not global_scope or version == '4.0':
                        if spec['base'] is not None:
                            child.set('Base', spec['base'])
                    if spec['rate'] is not None:
                        child.set('TasaOCuota', spec['rate'])
                if spec['amount'] is not None:
                    child.set('Importe', spec['amount'])
        return node

    container = E.SubElement(root, tag('Conceptos'))
    for spec in concepts if concepts is not None else [concept(taxes=[tax()])]:
        node = E.SubElement(container, tag('Concepto'), ClaveProdServ='01010101', ClaveUnidad='H87',
                            Descripcion='CASO SINTÉTICO SIN VALIDEZ FISCAL', Cantidad=spec['quantity'],
                            ValorUnitario=spec['unit'], Importe=spec['amount'])
        if version == '4.0':
            node.set('ObjetoImp', '02' if spec['taxes'] else '01')
        if spec['discount'] is not None:
            node.set('Descuento', spec['discount'])
        if spec['taxes']:
            taxes(node, spec['taxes'])
    if globals is None:
        globals = [tax()]
    if globals or aggregate_transfer is not None or aggregate_retention is not None:
        node = taxes(root, globals, global_scope=True)
        if aggregate_transfer is not None:
            node.set('TotalImpuestosTrasladados', aggregate_transfer)
        if aggregate_retention is not None:
            node.set('TotalImpuestosRetenidos', aggregate_retention)
    if locals or extra:
        comp = E.SubElement(root, tag('Complemento'))
        if locals:
            loc = E.SubElement(comp, '{'+LOCAL+'}ImpuestosLocales', version='1.0',
                               TotaldeTraslados=locals.get('transfer', '0'), TotaldeRetenciones=locals.get('retention', '0'))
            for value in locals.get('retentions', []):
                E.SubElement(loc, '{'+LOCAL+'}RetencionesLocales', ImpLocRetenido='RET LOCAL', TasadeRetencion='1', Importe=value)
            for value in locals.get('transfers', []):
                E.SubElement(loc, '{'+LOCAL+'}TrasladosLocales', ImpLocTrasladado='ISH', TasadeTraslado='3', Importe=value)
        if extra:
            comp.append(E.fromstring(extra.encode('utf-8')))
    return E.tostring(root, xml_declaration=True, encoding=encoding)


def samples():
    mixed = [tax(), tax(code='003', rate='0.080000', amount='8')]
    exempt = tax(factor='Exento', rate=None, amount=None)
    zero = tax(rate='0.000000', amount='0')
    retention = tax(code='001', rate='0.100000', amount='10', nature='retention')
    return {
        'p0_iva_ieps_40.xml': invoice(concepts=[concept(taxes=mixed)], globals=mixed, aggregate_transfer='24', total='124'),
        'p0_isr_retention_40.xml': invoice(concepts=[concept(taxes=[retention])], globals=[retention],
                                          aggregate_transfer=None, aggregate_retention='10', total='90'),
        'p0_local_once_40.xml': invoice(locals={'transfer': '3', 'transfers': ['3']}, total='119'),
        'local_retention_40.xml': invoice(locals={'transfer': '3', 'transfers': ['3'], 'retention': '1', 'retentions': ['1']}, total='118'),
        'p0_exempt_zero_40.xml': invoice(concepts=[concept(taxes=[exempt]), concept(taxes=[zero])], globals=[exempt, zero],
                                        subtotal='200', total='200', aggregate_transfer='0'),
        'p0_missing_aggregate_40.xml': invoice(aggregate_transfer=None),
        'p0_missing_subtotal_40.xml': invoice(subtotal=None),
        'round_groups_40.xml': invoice(concepts=[concept(amount='0.105', taxes=[tax(base='0.105', amount='0.016800')])]*2,
                                      globals=[tax(base='0.21', amount='0.03')], subtotal='0.21', total='0.24', aggregate_transfer='0.03'),
        'historical_iva_ieps_33.xml': invoice(version='3.3', concepts=[concept(taxes=mixed)], globals=mixed, aggregate_transfer='24', total='124'),
        'latin1_40.xml': invoice(encoding='ISO-8859-1'),
        'utf16_40.xml': invoice(encoding='UTF-16'),
        'alternate_prefix_40.xml': invoice(prefix='factura'),
        'unknown_complement_40.xml': invoice(extra='<otro:Datos xmlns:otro="urn:example:uninterpreted" Version="7"><otro:Traslado Importe="999999"/></otro:Datos>'),
    }
