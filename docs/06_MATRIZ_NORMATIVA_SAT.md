# Matriz normativa SAT — motor fiscal independiente

Seguimiento de implementación: la [integración Qt/worker](17_INTEGRACION_QT_WORKERS_REPORT.md) ya consume estas reglas. La cobertura normativa I/E y sus pendientes fiscales permanecen como se documentan aquí; el estado antiguo de integración pendiente al final corresponde al hito independiente.

Instantánea `sat-2026-11-06`. Matriz de implementación y evidencia; no certificación SAT. Fuentes descargadas directamente de dominios SAT; bytes archivados en `resources/sat/`, URL final, fecha UTC, Last-Modified y SHA256 en `manifest.json`. No hay descargas durante la lectura.

## Versiones, vigencias y cobertura

| Ámbito | Versión / periodo de referencia | Implementado | Límite |
|---|---|---|---|
| CFDI | 4.0; portal SAT: desde2022-01-01; única versión de emisión desde2023-04-01 | Lectura namespace/versión; XSD núcleo; recálculo I/E | No determina validez de emisión ni estatus actual |
| CFDI histórico | 3.3; portal SAT:2017-07-01 a2023-03-31 | Lectura histórica; XSD; recálculo I/E | No aplicar como autorización para emitir3.3 hoy |
| Impuestos locales | Namespace implocal, versión1.0 | Atributos, detalle1:N, XSD, conciliación | Sin reconstruir bases legales locales no expresadas |
| Timbre | TFD1.1 | UUID, original y XSD | Sin verificar firma, certificado o cancelación |
| Monedas/tasas | Catálogos4.0 de2026-11-06 y3.3 de2023-03-31 | Filas de c_Moneda/c_TasaOCuota con inicio/fin de vigencia | No son un archivo completo de todas las revisiones históricas |
| REP/nómina/Carta Porte/otros | Cualquier namespace/versión no implementado | Preservación y estado NO INTERPRETADO | Sin reglas ni certificación de revisión E2026 u otra |

El periodo general de versión procede del [portal SAT](http://omawww.sat.gob.mx/tramitesyservicios/Paginas/anexo_20.htm). No se confunde vigencia con Last-Modified HTTP. Las fechas efectivas de cada moneda/tasa proceden de las columnas oficiales del XLS. Una fila fuera de fecha o sin historia suficiente produce validación pendiente; no se inventa la precisión.

## Reglas implementadas y pruebas

Ejecución actual: **59 pruebas**, 0 fallos y 0 errores. Los códigos SAT son referencias de soporte, no una afirmación de implementar todas sus condiciones.

| ID | Regla / estado | Códigos de referencia4.0 | Códigos de referencia3.3 | Pruebas |
|---|---|---|---|---|
| F01 | IMPLEMENTADO EN ALCANCE: IVA/IEPS por código; grupos separados por naturaleza/factor/tasa; niveles separados | CFDI40205, CFDI40211, CFDI40221 | CFDI33183, CFDI33189, CFDI33195 | test_F01_iva_ieps_not_aggregate; test_F01_F02_multiple_concepts_multiple_codes |
| F02 | IMPLEMENTADO EN ALCANCE: Retención como enum, resumen global por impuesto sin exigir factor/base global | CFDI40203, CFDI40211 | CFDI33181, CFDI33189 | test_F02_retention_isr_typed; test_F01_F02_multiple_concepts_multiple_codes |
| F03 | IMPLEMENTADO EN ALCANCE: Locales una sola vez; sumas reportadas y de detalle separadas | CFDI40119 | CFDI33118 | test_F03_local_counted_once; test_F03_local_retention_subtracted_once; test_F03_local_mismatch_not_silently_fixed |
| F04 | IMPLEMENTADO EN ALCANCE: Exento sin tasa/importe; base exenta distinta de tasa cero | CFDI40177, CFDI40178, CFDI40184 | CFDI33157, CFDI33158, CFDI33166 | test_F04_exempt_and_zero_bases_disjoint; test_historical_33_exempt_only |
| F05 | IMPLEMENTADO EN ALCANCE: Fuente de detalle única por naturaleza; ausencia explícita; fallback conceptual sólo diagnóstico | CFDI40209, CFDI40205, CFDI40211, CFDI40221 | CFDI33187, CFDI33183, CFDI33189, CFDI33195 | test_F05_missing_aggregate_does_not_double; test_F05_invalid_global_amount_not_fallback_to_concepts |
| F06 | IMPLEMENTADO EN ALCANCE: Decimal, nulidad, límites de producto y redondeo al agrupar; precisión monetaria por fecha | CFDI40107, CFDI40108, CFDI40111, CFDI40167, CFDI40180, CFDI40186 | CFDI33106, CFDI33107, CFDI33110, CFDI33149, CFDI33161, CFDI33169 | test_F06_round_after_grouping_not_each_concept; test_F06_product_bounds_use_reported_precision; test_F06_currency_precision_zero_two_three; test_F06_rate_six_digits_per_official_faq40 |
| CAT | IMPLEMENTADO EN ALCANCE: c_Moneda y c_TasaOCuota con fechas/filas; IVA crédito 50% mantiene código002 | CFDI40179, CFDI40185, CFDI40219 | CFDI33159, CFDI33167, CFDI33193 | test_catalog_rate_fixed_range_and_mismatch; test_IEPS_cuota_and_historical_catalog_gap |

| Control técnico | Estado | Prueba |
|---|---|---|
| X01 namespace/versión/prefijo | Implementado | test_namespace_prefix_variants_same_values; test_wrong_namespace_and_version_rejected |
| X02 DTD/XXE | Rechazo en bytes originales por callbacks; no se elimina DTD antes de revisar | test_dtd_internal_external_entities_rejected_before_expansion; test_utf16_dtd_not_hidden_by_zero_bytes |
| X03 codificación | UTF8/UTF16LE/BE/Latin1/ASCII; bytes originales conservados | test_encodings_preserve_names_and_original_bytes |
| X04 recursos XML | Límites por bytes, elementos, profundidad, texto/atributos/namespaces; presupuesto temporal cooperativo | test_depth_nodes_text_attributes_and_namespaces_limits; test_byte_limit_before_reading_whole_stream |
| X05 XSD | Esquemas locales fijados por hash, sin resolver schemaLocation del documento | test_offline_schema_location_and_xinclude_never_fetch; test_resource_tamper_and_missing_fail_closed |
| Integridad de contenido | SHA256 de bytes originales; identidad disponible al futuro repositorio | test_original_hash_distinguishes_same_size_content; caché/SQLite pendientes |

## Precisión y procedimientos

- `Decimal` desde cadena XML, contexto local de80 dígitos. No hay conversión monetaria por float ni tolerancia global tipo epsilon. Original del atributo parseado, valor Decimal, escala y estado missing/invalid/valid permanecen separados; los bytes conservan la forma lexical exacta.
- `t_Importe` y operandos generales hasta6 decimales; agregados según c_Moneda; locales según su XSD (2). TasaOCuota4.0 exige6 posiciones conforme FAQ40 pregunta40; la lectura3.3 usa el límite superior de su XSD y comparación numérica con catálogo.
- Sumas de conceptos antes de redondear SubTotal/Descuento; impuestos conceptuales antes de redondear grupos. Se usa ROUND_HALF_UP para redondeo aritmético no negativo, como política explícita del motor. FAQ40 preguntas37–39 sustenta redondear al final; los empates exactos se prueban y no dependen del contexto global de Python.
- Límites de Importe: fórmulas de precisión reportada del estándar4.0 PDF pp76–78 y3.3 pp68–70. Límite inferior truncado; superior hacia arriba, corrección10^-12 en el operando superior. Se devuelve producto exacto e intervalo, sin reemplazar el importe reportado por el producto.
- Retenciones globales por código. Traslados por código/factor/tasa; los conceptos y globales se comparan, no se unen. Para3.3 no se exige resumen global de Exento;4.0 sí conserva Base/TipoFactor de Exento.
- Totales separados: fórmula con agregados reportados, fórmula con detalles elegidos y fórmula diagnóstica desde conceptos. No hay conversión MXN implícita ni mezcla entre monedas.

## XSD y complementos desconocidos

Los XSD SAT contienen xs:any **strict**. El documento completo sólo recibe PASS si todos sus nodos están cubiertos por los esquemas locales. Si faltan esquemas de extensiones, una copia exclusivamente de validación excluye esos subárboles, valida el núcleo y reporta PENDING con la lista excluida. El XML original permanece intacto; un fallo del núcleo sigue siendo FAIL. No se modifica el XSD ni se etiqueta el XML completo como válido por validar una proyección.

## Registro de fuentes

| ID | Fuente oficial / archivo | Estado / bytes | Consulta UTC / Last-Modified | SHA256 |
|---|---|---|---|---|
| portal | [anexo_20.htm](http://omawww.sat.gob.mx/tramitesyservicios/Paginas/anexo_20.htm) | downloaded / 24771 | 2026-11-06T16:00:23.400038+00:00 / Fri, 06 Nov 2026 15:02:49 GMT | `0b68000b625616c42d5ce22daba5d5bdddc55f0419707bc6d0cfa3337f113fa7` |
| cfdi40 | [cfdv40.xsd](https://www.sat.gob.mx/sitio_internet/cfd/4/cfdv40.xsd) | downloaded / 50607 | 2026-11-06T16:00:23.401040+00:00 / Tue, 04 Jun 2024 17:12:17 GMT | `2489b5b535f5cbc6a6c2db6132620de1833f85372512d01deea62880e700e276` |
| cfdi33 | [cfdv33.xsd](https://www.sat.gob.mx/sitio_internet/cfd/3/cfdv33.xsd) | downloaded / 53146 | 2026-11-06T16:00:23.401040+00:00 / Sat, 08 Aug 2020 05:15:54 GMT | `9fab804ebd9c532ddd59a74b23a3fa2b5d0d1f9046360b05efcef72206f01fd0` |
| catalog_xsd | [catCFDI.xsd](https://www.sat.gob.mx/sitio_internet/cfd/catalogos/catCFDI.xsd) | downloaded / 5984046 | 2026-11-06T16:00:23.401040+00:00 / Fri, 13 Dec 2024 19:59:34 GMT | `6c58936cb77576f839a4d7915953ceaf252b9eb9319f9458fe5bb67ae2bb0bb1` |
| types | [tdCFDI.xsd](https://www.sat.gob.mx/sitio_internet/cfd/tipoDatos/tdCFDI/tdCFDI.xsd) | downloaded / 7315 | 2026-11-06T16:00:23.402442+00:00 / Tue, 04 Jun 2024 17:13:32 GMT | `b3b81fe4017b95d5477f23a32f47e8b0571683cfddfff1330508c75e02b504cd` |
| local10 | [implocal.xsd](https://www.sat.gob.mx/sitio_internet/cfd/implocal/implocal.xsd) | downloaded / 4175 | 2026-11-06T16:00:23.402442+00:00 / Sat, 08 Aug 2020 05:16:36 GMT | `c377fe22b3d96cc6f719cbc4264c6d5754be351339deb48cfe7c004fefe62d1b` |
| tfd11 | [TimbreFiscalDigitalv11.xsd](https://www.sat.gob.mx/sitio_internet/cfd/TimbreFiscalDigital/TimbreFiscalDigitalv11.xsd) | downloaded / 4732 | 2026-11-06T16:00:23.638413+00:00 / Sat, 08 Aug 2020 05:16:08 GMT | `fb3d061fe9914500bef8beb3ea2e8722ee8a8224fa3af63643877a64c0ea05f7` |
| matrix40 | [matrix40.xls](http://omawww.sat.gob.mx/tramitesyservicios/Paginas/documentos/MatrizDeErrores_CFDI_v40_20260325.xls) | downloaded / 454656 | 2026-11-06T16:00:23.685403+00:00 / Tue, 24 Mar 2026 21:07:18 GMT | `bdc350035c7ed720af5be15509e01d0bda7c12cec4ad9797b0c34f889c1140a7` |
| matrix33 | [matrix33.xls](http://omawww.sat.gob.mx/tramitesyservicios/Paginas/documentos/MatrizDeErrores_CFDI_v33.xls) | downloaded / 631296 | 2026-11-06T16:00:23.686406+00:00 / Sun, 25 Sep 2022 20:28:27 GMT | `6d10cde320a02df06ec61678afdf08b236ec2e08f76f88f06754955d5c341998` |
| catalog40 | [catalog40.xls](http://omawww.sat.gob.mx/tramitesyservicios/Paginas/documentos/catCFDI_V_4_20261106.xls) | downloaded / 48771072 | 2026-11-06T16:01:10.068324+00:00 / Fri, 06 Nov 2026 15:02:36 GMT | `6249e37275ce164a1c4ac44e726dcd60858dac5c5604ff6c9ab06005a9199e1a` |
| catalog33 | [catalog33.xls](http://omawww.sat.gob.mx/tramitesyservicios/Paginas/documentos/catCFDI_V_33_31032023.xls) | downloaded / 33281024 | 2026-11-06T16:00:23.756165+00:00 / Sat, 01 Apr 2023 04:01:09 GMT | `ef6cf4fbedcbc5a3db993b9495186762327a75cd4c826f39d7055ccf28f7a46b` |
| standard40 | [standard40.pdf](http://omawww.sat.gob.mx/tramitesyservicios/Paginas/documentos/Anexo20_2022.pdf) | downloaded / 6665523 | 2026-11-06T16:00:23.813067+00:00 / Sun, 25 Sep 2022 20:24:42 GMT | `b3b6d63a97c859a31d7aacf0fe17b2d58207280df6f06caff3ceaf79954cf4bd` |
| standard33 | [standard33.pdf](http://omawww.sat.gob.mx/tramitesyservicios/Paginas/documentos/cfdv33.pdf) | downloaded / 2498547 | 2026-11-06T16:00:24.134331+00:00 / Sun, 25 Sep 2022 20:28:04 GMT | `93e99135fa0f3217ba4a342c0f70a62b90b1d09e1ee703ec5ca1099d98d60818` |
| faq40 | [faq40.pdf](http://omawww.sat.gob.mx/tramitesyservicios/Paginas/documentos/PregFrecCFDIVer4_0.pdf) | downloaded / 328600 | 2026-11-06T16:00:24.375442+00:00 / Thu, 30 May 2024 15:00:02 GMT | `44267da00068c89cd3e8bc31a08b0f87862821b75f47ac05b08823e9fcdc4bcd` |
| chain40 | [cadenaoriginal_4_0.xslt](https://www.sat.gob.mx/sitio_internet/cfd/4/cadenaoriginal_4_0/cadenaoriginal_4_0.xslt) | downloaded / 21324 | 2026-11-06T16:00:24.477038+00:00 / Fri, 17 Apr 2026 00:30:45 GMT | `b0559b380e73b850ca8a3da53b077a6051a09d87068d8d98e82dfd4acfba7565` |
| chain33 | [cadenaoriginal_3_3.xslt](https://www.sat.gob.mx/sitio_internet/cfd/3/cadenaoriginal_3_3/cadenaoriginal_3_3.xslt) | downloaded / 18758 | 2026-11-06T16:00:24.658328+00:00 / Wed, 01 Dec 2021 15:13:17 GMT | `2cfd68ff167c88c9a0ce449c32b6fe1110e18c846d03812ca302d9defe672745` |

Las cadenas XSLT están archivadas sólo como **raíces de referencia**; sus includes no están todos incorporados y no se ejecutan. Firma/certificado/cadena original permanecen NO VALIDADOS. No se confunde descarga con implementación.

## Catálogos derivados y pendientes

- CFDI4.0: 183 monedas, 19 filas de tasas/cuotas y 129 referencias de códigos de la matriz. Fila y hoja oficiales retenidas en `catalogs.json`; hash del XLS de origen y del JSON derivado comprobados.
- CFDI3.3: 178 monedas, 19 filas de tasas/cuotas y 96 referencias de códigos de la matriz. Fila y hoja oficiales retenidas en `catalogs.json`; hash del XLS de origen y del JSON derivado comprobados.

Pendientes: historia completa de catálogos, todos los catálogos/condicionales SAT ajenos al alcance, datos de contribuyentes, firmas/estatus externo, REP/nómina/CP, ZIP seguro, SQLite/caché, integración Qt con worker y sustitución de cálculos/reportes heredados. Los P0 Z03/C01 y los P0 fiscales del flujo legado no se declaran cerrados por este módulo.
