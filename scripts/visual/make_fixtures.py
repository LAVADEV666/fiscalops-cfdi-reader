"""Generate anonymous UI fixtures, not certified fiscal documents."""
from pathlib import Path
import hashlib
import json
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / 'tests/visual/fixtures/AAA010101AAA'
NS = uuid.UUID('3f56736b-8126-4857-82c7-71a05adf4340')


def document(index, kind='I', currency='MXN', received=False):
    uid = str(uuid.uuid5(NS, f'visual-{index}')).upper()
    emitter, receiver = ('BBB010101BBB', 'AAA010101AAA') if received else ('AAA010101AAA', 'BBB010101BBB')
    total = '0' if kind in ('P', 'T') else '116.00'
    comp = ''
    if kind == 'P':
        comp = '<pago20:Pagos Version="2.0"><pago20:Totales MontoTotalPagos="100.00"/><pago20:Pago FechaPago="2026-10-20T12:00:00" FormaDePagoP="03" MonedaP="MXN" Monto="100.00"><pago20:DoctoRelacionado IdDocumento="11111111-1111-4111-8111-111111111111" MonedaDR="MXN" NumParcialidad="1" ImpSaldoAnt="116.00" ImpPagado="100.00" ImpSaldoInsoluto="16.00" ObjetoImpDR="01"/></pago20:Pago></pago20:Pagos>'
    elif kind == 'N':
        comp = '<nomina12:Nomina Version="1.2" TipoNomina="O" FechaPago="2026-10-31" FechaInicialPago="2026-10-16" FechaFinalPago="2026-10-31" NumDiasPagados="15" TotalPercepciones="116.00"><nomina12:Emisor RegistroPatronal="SINTETICO"/><nomina12:Receptor Curp="DATO-SINTETICO" NumSeguridadSocial="00000000000" NumEmpleado="001" TipoContrato="01" TipoRegimen="02" PeriodicidadPago="04"/><nomina12:Percepciones TotalGravado="100.00" TotalExento="16.00"><nomina12:Percepcion TipoPercepcion="001" Clave="001" Concepto="PERCEPCION SINTETICA" ImporteGravado="100.00" ImporteExento="16.00"/></nomina12:Percepciones></nomina12:Nomina>'
    elif kind == 'T':
        comp = '<cartaporte31:CartaPorte Version="3.1" TranspInternac="No" TotalDistRec="10"><cartaporte31:Ubicaciones><cartaporte31:Ubicacion TipoUbicacion="Origen" IDUbicacion="OR000001" RFCRemitenteDestinatario="AAA010101AAA" FechaHoraSalidaLlegada="2026-10-20T12:00:00"/><cartaporte31:Ubicacion TipoUbicacion="Destino" IDUbicacion="DE000001" RFCRemitenteDestinatario="BBB010101BBB" FechaHoraSalidaLlegada="2026-10-20T13:00:00" DistanciaRecorrida="10"/></cartaporte31:Ubicaciones><cartaporte31:Mercancias PesoBrutoTotal="1" UnidadPeso="KGM" NumTotalMercancias="1"><cartaporte31:Mercancia BienesTransp="10101500" Descripcion="MERCANCIA SINTETICA" Cantidad="1" ClaveUnidad="H87" PesoEnKg="1"/></cartaporte31:Mercancias></cartaporte31:CartaPorte>'
    taxes = '' if kind in ('P', 'T', 'N') else '<cfdi:Impuestos TotalImpuestosTrasladados="16.00"><cfdi:Traslados><cfdi:Traslado Base="100.00" Impuesto="002" TipoFactor="Tasa" TasaOCuota="0.160000" Importe="16.00"/></cfdi:Traslados></cfdi:Impuestos>'
    text = f'''<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital" xmlns:pago20="http://www.sat.gob.mx/Pagos20" xmlns:nomina12="http://www.sat.gob.mx/nomina12" xmlns:cartaporte31="http://www.sat.gob.mx/CartaPorte31" Version="4.0" Serie="DEMO" Folio="{index:04}" Fecha="2026-10-20T12:34:56" TipoDeComprobante="{kind}" Moneda="{currency}" SubTotal="100.00" Total="{total}" MetodoPago="{'PPD' if index%2 else 'PUE'}" FormaPago="03" Exportacion="01" LugarExpedicion="01000">
<cfdi:Emisor Rfc="{emitter}" Nombre="EMISOR SINTETICO SIN DATOS REALES" RegimenFiscal="601"/>
<cfdi:Receptor Rfc="{receiver}" Nombre="RECEPTOR SINTETICO DE PRUEBAS" RegimenFiscalReceptor="601" DomicilioFiscalReceptor="01000" UsoCFDI="G03"/>
<cfdi:Conceptos><cfdi:Concepto ClaveProdServ="81112100" Cantidad="1" ClaveUnidad="E48" Descripcion="SERVICIO SINTETICO PARA REFERENCIA VISUAL {index}" ValorUnitario="100.00" Importe="100.00" ObjetoImp="02"/></cfdi:Conceptos>{taxes}
<cfdi:Complemento><tfd:TimbreFiscalDigital Version="1.1" UUID="{uid}" FechaTimbrado="2026-10-20T12:35:00" RfcProvCertif="AAA010101AAA"/>{comp}</cfdi:Complemento></cfdi:Comprobante>'''
    return uid, text


def main():
    FIXTURES.mkdir(parents=True, exist_ok=True)
    rows = []
    manifest = []
    for index in range(1, 49):
        kind = {2: 'E', 3: 'P', 4: 'N', 5: 'T'}.get(index, 'I')
        uid, xml = document(index, kind, 'USD' if index == 6 else 'MXN', received=index > 40)
        path = FIXTURES / f'demo-{index:02}-{kind}.xml'
        path.write_text(xml, encoding='utf-8')
        manifest.append({'file': path.name, 'uuid': uid, 'kind': kind, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        if index != 8:
            rows.append(f'{uid}~AAA010101AAA~EMISOR SINTETICO~BBB010101BBB~RECEPTOR SINTETICO~{0 if index==2 else 1}~{ "2026-10-31" if index==2 else ""}')
    (FIXTURES / 'metadata-demo.txt').write_text('Uuid~RfcEmisor~NombreEmisor~RfcReceptor~NombreReceptor~Estatus~FechaCancelacion\n'+'\n'.join(rows), encoding='utf-8')
    (FIXTURES / 'error-deliberado.xml').write_text('<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4">', encoding='utf-8')
    (FIXTURES.parent / 'manifest.json').write_text(json.dumps({'purpose': 'Anonymous visual UI fixtures; not signed, not XSD-validated, not fiscal references', 'files': manifest}, indent=2), encoding='utf-8')
    work = ROOT / 'tests/visual/.work'
    work.mkdir(exist_ok=True)
    with zipfile.ZipFile(work / 'progress-synthetic.zip', 'w', compression=zipfile.ZIP_STORED) as archive:
        for index in range(1000, 3000):
            _uid, xml = document(index)
            archive.writestr(f'synthetic-{index}.xml', xml)
    print(json.dumps({'documents': len(manifest), 'folder': str(FIXTURES), 'progress_entries': 2000}))


if __name__ == '__main__':
    main()
