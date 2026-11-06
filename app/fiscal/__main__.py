"""Offline command line: python -m app.fiscal invoice.xml [--output inspection.json]."""
import argparse
import json
from pathlib import Path
import sys
from .security import XmlRejected
from .service import inspect_invoice, json_data
from .sources import SourceUnavailable


def main(argv=None):
    parser = argparse.ArgumentParser(description='Lector fiscal offline CFDI 3.3/4.0; importes JSON como cadenas Decimal.')
    parser.add_argument('xml', type=Path)
    parser.add_argument('--output', type=Path, help='Guardar JSON; por defecto se escribe a stdout.')
    parser.add_argument('--include-original', action='store_true', help='Incluir bytes XML originales en base64 (contiene datos del documento).')
    args = parser.parse_args(argv)
    try:
        same_file = args.output and (args.output.resolve() == args.xml.resolve() or
                                    args.output.exists() and args.xml.exists() and args.output.samefile(args.xml))
        if same_file:
            parser.error('El archivo de salida debe ser distinto del XML original.')
        with args.xml.open('rb') as stream:
            result = inspect_invoice(stream)
        payload = json_data(result, include_original=args.include_original)
        xsd = payload['validation']['xsd']['status']
        state = payload['analysis']['status']
        exit_code = 1 if xsd == 'fail' or state == 'error' else 3 if xsd == 'pending' or state == 'partial' else 0
    except XmlRejected as exc:
        payload, exit_code = {'contract': 'fiscalops.inspection/1', 'rejected': exc.as_dict()}, 2
    except (OSError, SourceUnavailable) as exc:
        # Do not dump document content or full local paths into diagnostics.
        payload, exit_code = {'contract': 'fiscalops.inspection/1', 'error': type(exc).__name__}, 2
    text = json.dumps(payload, ensure_ascii=False, indent=2)+'\n'
    if args.output:
        try:
            args.output.write_text(text, encoding='utf-8')
        except OSError:
            sys.stderr.write('No se pudo escribir el reporte fiscal.\n')
            return 2
    else:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        sys.stdout.write(text)
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
