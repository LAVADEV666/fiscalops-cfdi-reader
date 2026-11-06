"""CFDI 3.3/4.0 structural reader. Prefix spelling has no semantic meaning."""
import hashlib
from lxml import etree
from . import PARSER_VERSION
from .models import Concept, Invoice, LocalTaxes, Nature, PreservedNode, Tax
from .numbers import number
from .security import Limits, XmlRejected, secure_bytes

CFDI = {'4.0': 'http://www.sat.gob.mx/cfd/4', '3.3': 'http://www.sat.gob.mx/cfd/3'}
LOCAL = 'http://www.sat.gob.mx/implocal'
TFD = 'http://www.sat.gob.mx/TimbreFiscalDigital'


def xml_parser():
    return etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False,
                           dtd_validation=False, huge_tree=False, recover=False,
                           remove_comments=False, strip_cdata=False)


def read_invoice(source, limits: Limits = Limits()) -> Invoice:
    original, encoding = secure_bytes(source, limits)
    try:
        root = etree.fromstring(original, parser=xml_parser())
    except etree.XMLSyntaxError as exc:
        raise XmlRejected('XML_MALFORMED', line=exc.lineno, column=exc.position[1]) from exc
    qname = etree.QName(root)
    version = root.get('Version')
    if qname.localname != 'Comprobante' or qname.namespace not in CFDI.values():
        raise XmlRejected('CFDI_ROOT_NAMESPACE_UNSUPPORTED')
    if version not in CFDI:
        raise XmlRejected('CFDI_VERSION_UNSUPPORTED')
    ns = CFDI[version]
    if qname.namespace != ns:
        raise XmlRejected('CFDI_NAMESPACE_VERSION_MISMATCH')
    tag = lambda name: f'{{{ns}}}{name}'
    issues = []

    def one(parent, name, path):
        nodes = parent.findall(tag(name))
        if len(nodes) > 1:
            issues.append({'code': 'CFDI_DUPLICATE_SINGLETON', 'path': path+'/'+name})
        return nodes[0] if nodes else None

    def numeric(node, names, path):
        return {name: number(node.get(name) if node is not None else None, path+'/@'+name) for name in names}

    def taxes(node, scope, path, concept_index=None):
        result = []
        if node is None:
            return ()
        for group, item, nature in [('Traslados', 'Traslado', Nature.TRANSFER),
                                    ('Retenciones', 'Retencion', Nature.RETENTION)]:
            container = one(node, group, path)
            if container is None:
                continue
            for index, tax in enumerate(container.findall(tag(item)), 1):
                p = f'{path}/{group}/{item}[{index}]'
                nums = numeric(tax, ('Base', 'TasaOCuota', 'Importe'), p)
                result.append(Tax(scope, nature, tax.get('Impuesto'), tax.get('TipoFactor'),
                                  nums['Base'], nums['TasaOCuota'], nums['Importe'], p, concept_index))
        return tuple(result)

    issuer, receiver = one(root, 'Emisor', '/Comprobante'), one(root, 'Receptor', '/Comprobante')
    concepts_node = one(root, 'Conceptos', '/Comprobante')
    concepts = []
    if concepts_node is not None:
        for index, node in enumerate(concepts_node.findall(tag('Concepto')), 1):
            path = f'/Comprobante/Conceptos/Concepto[{index}]'
            tax_node = one(node, 'Impuestos', path)
            concepts.append(Concept(index, path, dict(node.attrib),
                                    numeric(node, ('Cantidad', 'ValorUnitario', 'Importe', 'Descuento'), path),
                                    taxes(tax_node, 'concept', path+'/Impuestos', index)))
    global_node = one(root, 'Impuestos', '/Comprobante')
    complement_nodes = root.findall(tag('Complemento'))
    if version == '4.0' and len(complement_nodes) > 1:
        issues.append({'code': 'CFDI_DUPLICATE_SINGLETON', 'path': '/Comprobante/Complemento'})
    preserved, local_taxes, uuids = [], [], []
    for comp_index, complement_node in enumerate(complement_nodes, 1):
        for index, node in enumerate(complement_node, 1):
            if not isinstance(node.tag, str):
                continue
            q = etree.QName(node)
            p = f'/Comprobante/Complemento[{comp_index}]/*[{index}]'
            local_version = node.get('Version', node.get('version'))
            is_local = q.namespace == LOCAL and q.localname == 'ImpuestosLocales' and local_version == '1.0'
            is_tfd = q.namespace == TFD and q.localname == 'TimbreFiscalDigital' and local_version == '1.1'
            preserved.append(PreservedNode(p, q.namespace or '', q.localname, local_version,
                                           'interpreted-local-1.0' if is_local else 'identity-only' if is_tfd else 'not-interpreted',
                                           etree.tostring(node, encoding='unicode', with_tail=False)))
            if is_tfd:
                uuids.append(node.get('UUID'))
            if is_local:
                entries = []
                for child_index, child in enumerate(node, 1):
                    if child.tag not in (f'{{{LOCAL}}}TrasladosLocales', f'{{{LOCAL}}}RetencionesLocales'):
                        continue
                    transfer = child.tag == f'{{{LOCAL}}}TrasladosLocales'
                    cp = f'{p}/*[{child_index}]'
                    entries.append(Tax('local', Nature.TRANSFER if transfer else Nature.RETENTION, None, None,
                                       number(None, cp+'/@Base'),
                                       number(child.get('TasadeTraslado' if transfer else 'TasadeRetencion'), cp+'/@TasaPorcentaje'),
                                       number(child.get('Importe'), cp+'/@Importe'), cp,
                                       local_name=child.get('ImpLocTrasladado' if transfer else 'ImpLocRetenido')))
                local_taxes.append(LocalTaxes(p, local_version, number(node.get('TotaldeTraslados'), p+'/@TotaldeTraslados'),
                                              number(node.get('TotaldeRetenciones'), p+'/@TotaldeRetenciones'), tuple(entries)))
    if len(local_taxes) > 1 or len(uuids) > 1:
        issues.append({'code': 'CFDI_DUPLICATE_COMPLEMENT', 'path': '/Comprobante/Complemento'})
    # Retain concept complements and Addenda, without interpreting similarly named tax nodes within them.
    for node in root.iter():
        if not isinstance(node.tag, str):
            continue
        if node.tag in (tag('Addenda'), tag('ComplementoConcepto')):
            preserved.append(PreservedNode(root.getroottree().getpath(node), ns, etree.QName(node).localname,
                                           None, 'not-interpreted', etree.tostring(node, encoding='unicode', with_tail=False)))
    return Invoice(PARSER_VERSION, hashlib.sha256(original).hexdigest(), original, encoding, ns, version,
                   dict(root.attrib), dict(issuer.attrib) if issuer is not None else {},
                   dict(receiver.attrib) if receiver is not None else {},
                   numeric(root, ('SubTotal', 'Descuento', 'Total', 'TipoCambio'), '/Comprobante'), tuple(concepts),
                   global_node is not None, taxes(global_node, 'global', '/Comprobante/Impuestos'),
                   numeric(global_node, ('TotalImpuestosTrasladados', 'TotalImpuestosRetenidos'), '/Comprobante/Impuestos'),
                   tuple(local_taxes), tuple(preserved), uuids[0] if len(uuids) == 1 else None, tuple(issues))
