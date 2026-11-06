"""Render the normative matrix from pinned sources, implemented references and actual tests."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from app.fiscal.rules import RULES

DESCRIPTIONS = {
    'F01': ('IVA/IEPS por código; grupos separados por naturaleza/factor/tasa; niveles separados', 'test_F01_iva_ieps_not_aggregate; test_F01_F02_multiple_concepts_multiple_codes'),
    'F02': ('Retención como enum, resumen global por impuesto sin exigir factor/base global', 'test_F02_retention_isr_typed; test_F01_F02_multiple_concepts_multiple_codes'),
    'F03': ('Locales una sola vez; sumas reportadas y de detalle separadas', 'test_F03_local_counted_once; test_F03_local_retention_subtracted_once; test_F03_local_mismatch_not_silently_fixed'),
    'F04': ('Exento sin tasa/importe; base exenta distinta de tasa cero', 'test_F04_exempt_and_zero_bases_disjoint; test_historical_33_exempt_only'),
    'F05': ('Fuente de detalle única por naturaleza; ausencia explícita; fallback conceptual sólo diagnóstico', 'test_F05_missing_aggregate_does_not_double; test_F05_invalid_global_amount_not_fallback_to_concepts'),
    'F06': ('Decimal, nulidad, límites de producto y redondeo al agrupar; precisión monetaria por fecha', 'test_F06_round_after_grouping_not_each_concept; test_F06_product_bounds_use_reported_precision; test_F06_currency_precision_zero_two_three; test_F06_rate_six_digits_per_official_faq40'),
    'CAT': ('c_Moneda y c_TasaOCuota con fechas/filas; IVA crédito 50% mantiene código002', 'test_catalog_rate_fixed_range_and_mismatch; test_IEPS_cuota_and_historical_catalog_gap'),
}


def render():
    manifest = json.loads((ROOT/'resources/sat/manifest.json').read_text(encoding='utf-8'))
    evidence = json.loads((ROOT/'tests/fiscal/evidence/tests.json').read_text(encoding='utf-8'))
    catalogs = json.loads((ROOT/'resources/sat/catalogs.json').read_text(encoding='utf-8'))
    lines = ['# Matriz normativa SAT — motor fiscal independiente', '',
             'Instantánea `sat-2026-11-06`. Matriz de implementación y evidencia; no certificación SAT. '
             'Fuentes descargadas directamente de dominios SAT; bytes archivados en `resources/sat/`, '
             'URL final, fecha UTC, Last-Modified y SHA256 en `manifest.json`. No hay descargas durante la lectura.', '',
             '## Versiones, vigencias y cobertura', '',
             '| Ámbito | Versión / periodo de referencia | Implementado | Límite |',
             '|---|---|---|---|',
             '| CFDI | 4.0; portal SAT: desde2022-01-01; única versión de emisión desde2023-04-01 | Lectura namespace/versión; XSD núcleo; recálculo I/E | No determina validez de emisión ni estatus actual |',
             '| CFDI histórico | 3.3; portal SAT:2017-07-01 a2023-03-31 | Lectura histórica; XSD; recálculo I/E | No aplicar como autorización para emitir3.3 hoy |',
             '| Impuestos locales | Namespace implocal, versión1.0 | Atributos, detalle1:N, XSD, conciliación | Sin reconstruir bases legales locales no expresadas |',
             '| Timbre | TFD1.1 | UUID, original y XSD | Sin verificar firma, certificado o cancelación |',
             '| Monedas/tasas | Catálogos4.0 de2026-11-06 y3.3 de2023-03-31 | Filas de c_Moneda/c_TasaOCuota con inicio/fin de vigencia | No son un archivo completo de todas las revisiones históricas |',
             '| REP/nómina/Carta Porte/otros | Cualquier namespace/versión no implementado | Preservación y estado NO INTERPRETADO | Sin reglas ni certificación de revisión E2026 u otra |', '',
             'El periodo general de versión procede del [portal SAT]('+next(r['url'] for r in manifest['sources'] if r['id']=='portal')+'). '
             'No se confunde vigencia con Last-Modified HTTP. Las fechas efectivas de cada moneda/tasa proceden de las columnas oficiales del XLS. '
             'Una fila fuera de fecha o sin historia suficiente produce validación pendiente; no se inventa la precisión.', '',
             '## Reglas implementadas y pruebas', '',
             f'Ejecución actual: **{evidence["tests_run"]} pruebas**, {evidence["failures"]} fallos y {evidence["errors"]} errores. '
             'Los códigos SAT son referencias de soporte, no una afirmación de implementar todas sus condiciones.', '',
             '| ID | Regla / estado | Códigos de referencia4.0 | Códigos de referencia3.3 | Pruebas |',
             '|---|---|---|---|---|']
    tests = {r['id'].split('.')[-1] for r in evidence['cases'] if '(' not in r['id']}
    for key, (description, names) in DESCRIPTIONS.items():
        assert all(name.strip() in tests for name in names.split(';'))
        entry = RULES[key]
        lines.append(f'| {key} | IMPLEMENTADO EN ALCANCE: {description} | '+', '.join(entry['sat40'])+' | '+', '.join(entry['sat33'])+' | '+names+' |')
    lines += ['', '| Control técnico | Estado | Prueba |', '|---|---|---|',
              '| X01 namespace/versión/prefijo | Implementado | test_namespace_prefix_variants_same_values; test_wrong_namespace_and_version_rejected |',
              '| X02 DTD/XXE | Rechazo en bytes originales por callbacks; no se elimina DTD antes de revisar | test_dtd_internal_external_entities_rejected_before_expansion; test_utf16_dtd_not_hidden_by_zero_bytes |',
              '| X03 codificación | UTF8/UTF16LE/BE/Latin1/ASCII; bytes originales conservados | test_encodings_preserve_names_and_original_bytes |',
              '| X04 recursos XML | Límites por bytes, elementos, profundidad, texto/atributos/namespaces; presupuesto temporal cooperativo | test_depth_nodes_text_attributes_and_namespaces_limits; test_byte_limit_before_reading_whole_stream |',
              '| X05 XSD | Esquemas locales fijados por hash, sin resolver schemaLocation del documento | test_offline_schema_location_and_xinclude_never_fetch; test_resource_tamper_and_missing_fail_closed |',
              '| Integridad de contenido | SHA256 de bytes originales; identidad disponible al futuro repositorio | test_original_hash_distinguishes_same_size_content; caché/SQLite pendientes |', '',
              '## Precisión y procedimientos', '',
              '- `Decimal` desde cadena XML, contexto local de80 dígitos. No hay conversión monetaria por float ni tolerancia global tipo epsilon. '
              'Original del atributo parseado, valor Decimal, escala y estado missing/invalid/valid permanecen separados; los bytes conservan la forma lexical exacta.',
              '- `t_Importe` y operandos generales hasta6 decimales; agregados según c_Moneda; locales según su XSD (2). '
              'TasaOCuota4.0 exige6 posiciones conforme FAQ40 pregunta40; la lectura3.3 usa el límite superior de su XSD y comparación numérica con catálogo.',
              '- Sumas de conceptos antes de redondear SubTotal/Descuento; impuestos conceptuales antes de redondear grupos. '
              'Se usa ROUND_HALF_UP para redondeo aritmético no negativo, como política explícita del motor. '
              'FAQ40 preguntas37–39 sustenta redondear al final; los empates exactos se prueban y no dependen del contexto global de Python.',
              '- Límites de Importe: fórmulas de precisión reportada del estándar4.0 PDF pp76–78 y3.3 pp68–70. '
              'Límite inferior truncado; superior hacia arriba, corrección10^-12 en el operando superior. '
              'Se devuelve producto exacto e intervalo, sin reemplazar el importe reportado por el producto.',
              '- Retenciones globales por código. Traslados por código/factor/tasa; los conceptos y globales se comparan, no se unen. '
              'Para3.3 no se exige resumen global de Exento;4.0 sí conserva Base/TipoFactor de Exento.',
              '- Totales separados: fórmula con agregados reportados, fórmula con detalles elegidos y fórmula diagnóstica desde conceptos. '
              'No hay conversión MXN implícita ni mezcla entre monedas.', '',
              '## XSD y complementos desconocidos', '',
              'Los XSD SAT contienen xs:any **strict**. El documento completo sólo recibe PASS si todos sus nodos están cubiertos por los esquemas locales. '
              'Si faltan esquemas de extensiones, una copia exclusivamente de validación excluye esos subárboles, valida el núcleo y reporta PENDING con la lista excluida. '
              'El XML original permanece intacto; un fallo del núcleo sigue siendo FAIL. No se modifica el XSD ni se etiqueta el XML completo como válido por validar una proyección.', '',
              '## Registro de fuentes', '',
              '| ID | Fuente oficial / archivo | Estado / bytes | Consulta UTC / Last-Modified | SHA256 |',
              '|---|---|---|---|---|']
    for r in manifest['sources']:
        path = ROOT/'resources/sat'/r['file']
        assert r['status'] == 'downloaded' and hashlib.sha256(path.read_bytes()).hexdigest() == r['sha256']
        lines.append(f'| {r["id"]} | [{r["file"]}]({r["url"]}) | {r["status"]} / {r["bytes"]} | {r["acquired_at"]} / {r.get("last_modified")} | `{r["sha256"]}` |')
    lines += ['', 'Las cadenas XSLT están archivadas sólo como **raíces de referencia**; sus includes no están todos incorporados y no se ejecutan. '
              'Firma/certificado/cadena original permanecen NO VALIDADOS. No se confunde descarga con implementación.', '',
              '## Catálogos derivados y pendientes', '']
    for version, data in catalogs['versions'].items():
        lines.append(f'- CFDI{version}: {len(data["currencies"])} monedas, {len(data["rates"])} filas de tasas/cuotas y {len(data["rules"])} referencias de códigos de la matriz. '
                     'Fila y hoja oficiales retenidas en `catalogs.json`; hash del XLS de origen y del JSON derivado comprobados.')
    lines += ['', 'La integración Qt con worker y sustitución del flujo nativo se entrega en docs/17_INTEGRACION_QT_WORKERS_REPORT.md; no amplía la cobertura normativa de estas reglas.', '',
              'Pendientes: historia completa de catálogos, todos los catálogos/condicionales SAT ajenos al alcance, datos de contribuyentes, '
              'firmas/estatus externo, REP/nómina/CP y SQLite/caché. ZIP tiene controles de integración documentados en18, sin certificación exhaustiva. '
              'Los P0 Z03/C01 y los P0 fiscales del flujo legado no se declaran cerrados por este módulo.', '']
    (ROOT/'docs/06_MATRIZ_NORMATIVA_SAT.md').write_text('\n'.join(lines), encoding='utf-8')
    print('Normative matrix rendered from 16 verified sources and actual tests')


if __name__ == '__main__':
    render()
