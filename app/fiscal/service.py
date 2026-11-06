"""Public synchronous API for the independent engine; future worker adapters can call this."""
from .calculations import analyze
from .models import to_data
from .reader import read_invoice
from .security import Limits
from .sources import SatSources, validate_xsd


def inspect_invoice(source, *, limits: Limits = Limits(), sources: SatSources | None = None):
    invoice = read_invoice(source, limits)
    sources = sources or SatSources()
    xsd = validate_xsd(invoice, sources)
    arithmetic = analyze(invoice, sources)
    return {'contract': 'fiscalops.inspection/1', 'document': invoice,
            'validation': {'xml': 'pass', 'xsd': xsd, 'arithmetic': arithmetic['status'],
                           'official_sat': 'not-queried', 'signature': 'not-validated'},
            'analysis': arithmetic, 'normative_snapshot': sources.manifest['snapshot']}


def json_data(result, *, include_original=False):
    return to_data(result, include_original=include_original)
