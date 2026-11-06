"""Pinned local SAT resources. No runtime HTTP, XML schemaLocation discovery or XSLT execution."""
from datetime import date
import hashlib
import json
from pathlib import Path
from lxml import etree
from .reader import CFDI, LOCAL, TFD, xml_parser

RESOURCE_ROOT = Path(__file__).resolve().parents[2]/'resources/sat'


class SourceUnavailable(ValueError):
    pass


class SatSources:
    def __init__(self, directory: Path = RESOURCE_ROOT):
        self.directory = directory
        self.manifest = json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
        self.records = {r['id']: r for r in self.manifest['sources']}
        self._schemas = {}
        self._catalogs = None

    def resource(self, source_id):
        record = self.records[source_id]
        if record['status'] != 'downloaded':
            raise SourceUnavailable('SAT_SOURCE_UNAVAILABLE:'+source_id)
        path = self.directory/record['file']
        if path.parent.resolve() != self.directory.resolve():
            raise SourceUnavailable('SAT_SOURCE_PATH_REJECTED')
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise SourceUnavailable('SAT_SOURCE_UNAVAILABLE:'+source_id) from exc
        if hashlib.sha256(data).hexdigest() != record['sha256']:
            raise SourceUnavailable('SAT_SOURCE_HASH_MISMATCH:'+source_id)
        return data

    @property
    def catalogs(self):
        if self._catalogs is None:
            derived = json.loads((self.directory/'derived.json').read_text(encoding='utf-8'))
            data = (self.directory/'catalogs.json').read_bytes()
            if hashlib.sha256(data).hexdigest() != derived['sha256']:
                raise SourceUnavailable('SAT_DERIVED_HASH_MISMATCH')
            self._catalogs = json.loads(data)
            for record in self._catalogs['versions'].values():
                for name, key in [('source_id', 'source_sha256'), ('matrix_source_id', 'matrix_sha256')]:
                    if self.records[record[name]]['sha256'] != record[key]:
                        raise SourceUnavailable('SAT_DERIVED_PROVENANCE_MISMATCH')
        return self._catalogs

    def currency(self, version, code, issue_date):
        rows = self.catalogs['versions'][version]['currencies']
        return next((r for r in rows if r['code'] == code and effective(r, issue_date)), None)

    def schema(self, version):
        if version not in self._schemas:
            ids = ('cfdi40' if version == '4.0' else 'cfdi33', 'catalog_xsd', 'types', 'local10', 'tfd11')
            resources = {}
            for source_id in ids:
                data = self.resource(source_id)
                record = self.records[source_id]
                for url in (record['url'], record['url'].replace('https://', 'http://'),
                            (self.directory/record['file']).resolve().as_uri()):
                    resources[url] = data

            class LocalResolver(etree.Resolver):
                def resolve(self, url, public_id, context):
                    if url not in resources:
                        raise OSError('Unpinned schema import refused')
                    return self.resolve_string(resources[url], context, base_url=url)

            parser = xml_parser()
            parser.resolvers.add(LocalResolver())
            imports = [(CFDI[version], ids[0]), (LOCAL, 'local10'), (TFD, 'tfd11')]
            wrapper = '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">'+''.join(
                f'<xs:import namespace="{namespace}" schemaLocation="{self.records[key]["url"]}"/>'
                for namespace, key in imports)+'</xs:schema>'
            self._schemas[version] = etree.XMLSchema(etree.fromstring(wrapper.encode(), parser=parser))
        return self._schemas[version]


def effective(row, issue_date):
    try:
        day = date.fromisoformat(issue_date)
    except (ValueError, TypeError):
        return False
    return ((not row['valid_from'] or day >= date.fromisoformat(row['valid_from'])) and
            (not row['valid_to'] or day <= date.fromisoformat(row['valid_to'])))


def validate_xsd(invoice, sources: SatSources):
    try:
        schema = sources.schema(invoice.version)
        root = etree.fromstring(invoice.original, parser=xml_parser())
        # SAT xs:any is strict (not lax). Unavailable complement schemas mean pending,
        # not a false declaration that the complete document passed or is invalid.
        removed = []
        cfdi_tag = lambda name: '{'+invoice.namespace+'}'+name
        for container in root.findall(cfdi_tag('Complemento')):
            for child in list(container):
                if not isinstance(child.tag, str):
                    continue
                q = etree.QName(child)
                known = ((q.namespace, q.localname) in ((LOCAL, 'ImpuestosLocales'), (TFD, 'TimbreFiscalDigital')))
                if not known:
                    removed.append({'namespace': q.namespace, 'name': q.localname})
                    container.remove(child)
        for node in list(root.iter()):
            if node.tag in (cfdi_tag('Addenda'), cfdi_tag('ComplementoConcepto')):
                removed.append({'namespace': invoice.namespace, 'name': etree.QName(node).localname})
                node.getparent().remove(node)
        valid = schema.validate(root)
        errors = [{'line': e.line, 'domain': e.domain_name, 'type': e.type_name, 'path': e.path}
                  for e in schema.error_log]  # Avoid logging RFC/names/attribute values from libxml messages.
        return {'status': ('pending' if removed else 'pass') if valid else 'fail', 'errors': errors,
                'core_projection_status': 'pass' if valid else 'fail', 'excluded_unvalidated_nodes': removed,
                'scope': 'CFDI core + local 1.0 + TFD 1.1; strict unknown extensions excluded only from validation copy',
                'catalog_history': 'snapshot only; not complete historical catalog validation'}
    except (SourceUnavailable, OSError, etree.XMLSchemaParseError) as exc:
        return {'status': 'pending', 'reason': type(exc).__name__}
