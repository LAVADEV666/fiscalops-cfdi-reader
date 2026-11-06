# Entrega — lector XML y motor Decimal independiente

Seguimiento: el siguiente hito ya integra este motor con Qt mediante workers; leer [17_INTEGRACION_QT_WORKERS_REPORT](17_INTEGRACION_QT_WORKERS_REPORT.md). Este documento conserva el alcance de la entrega independiente y sus59 pruebas. El estado «Qt continúa legado» del apartado final es histórico y queda sustituido por esa integración.

Implementado el siguiente hito del handoff14: lector seguro, matriz normativa real y reconciliación F01–F06 para CFDI de ingreso/egreso3.3 y4.0. Se entrega como módulo Python/API y CLI reproducible, antes de migrar servicios al puente Qt. No es una reconstrucción integral del producto ni validación oficial SAT.

## Resultado por riesgo

| Riesgo | Resultado en el motor nuevo | Evidencia correcta |
|---|---|---|
| F01 IVA/IEPS | Separación por código001/002/003, naturaleza y nivel | IVA16, IEPS8, agregado24; total124 |
| F02 retenciones | Enum `retention`; resumen por impuesto; no depende de acentos de etiquetas | ISR retenido10, total90 |
| F03 locales | Complemento1.0 separado; agregado y detalle se comparan; una sola inclusión | IVA16 + local3 sobre100 =119; con local retenido1 =118 |
| F04 exento/tasa0 | Exento no tiene tasa/importe; bases clasificadas por factor | Dos conceptos100: base exenta100 y base tasa0 de100, sin duplicarlas |
| F05 fallback | Selección por naturaleza: global si existe, conceptual sólo si falta; ausencia/incidencia conservada | Total agregado ausente: IVA diagnóstico16, nunca32; fórmula reportada nula |
| F06 float/nulos | Decimal desde cadena,80 dígitos de contexto local, escala/ausencia explícitas | 0.1+0.2 exacto; agrupación0.0336→0.03; MXN/USD2, JPY0, KWD3 |

Estos riesgos se resuelven **en el alcance del nuevo motor**, sin modificar ni declarar corregido el JavaScript heredado. Z03 (ZIP), la persistencia/caché de C01 y el resto del backlog continúan abiertos.

## Lectura y trazabilidad

- Entrada binaria o stream, antes de decodificar/normalizar. SHA256 sobre todos los bytes originales, que quedan disponibles en el DTO. RFC, sello, certificado, campos desconocidos y estructuras no tipadas siguen presentes en el original.
- Namespace y versión exactos: `http://www.sat.gob.mx/cfd/3` con3.3 o `/cfd/4` con4.0. Prefijos arbitrarios y namespace por defecto equivalentes. Hijos se leen sólo desde el padre y namespace apropiados; no se buscan impuestos por nombre local en todo el árbol.
- Conceptos e impuestos1:N; globals y locales separados. CFDI3.3 admite múltiples contenedores Complemento. Versiones no implementadas no se interpretan por coincidencia de nombre.
- UTF8, UTF16LE/BE, Latin1 y ASCII; BOM/declaración respetados por el parser. DTD y entidades externas/paramétricas rechazados en callbacks, incluso UTF16. XInclude, stylesheet y schemaLocation aportados por el XML nunca se ejecutan/resuelven.
- Límites predeterminados:8MiB de XML,64 niveles,100000 elementos,128 atributos/declaraciones namespace por elemento,1M caracteres por atributo,4M de texto. Lectura en64KiB y presupuesto cooperativo de5s. Este presupuesto no es un watchdog de proceso ni un benchmark masivo; la futura integración Qt debe usar worker.

## Validación normativa

16 fuentes oficiales descargadas y verificadas por hash: esquemas3.3/4.0, tipos, catálogos XSD/XLS, matrices de errores, locales1.0, TFD1.1, estándares y FAQ. Las raíces XSLT se archivan sin ejecutar ni presumir sus dependencias completas. Los catálogos derivados incluyen fecha efectiva, hoja y fila. La extracción preserva el rótulo especial del IVA8% y su código002; no decide si existe derecho al beneficio.

Los XSD se compilan con imports fijados localmente. El atributo schemaLocation del documento no selecciona esquema. Los `xs:any` del SAT son strict: para extensiones sin XSD local se informa PENDING y se valida por separado una proyección del núcleo. El original no cambia. Un núcleo inválido sigue dando FAIL. Nunca se presenta esa proyección como validación completa del CFDI.

La [matriz06](06_MATRIZ_NORMATIVA_SAT.md) relaciona fuentes, versiones, reglas, casos, hashes y pendientes. Fecha de descarga/Last-Modified no es fecha de vigencia legal; los snapshots no cubren todas las revisiones históricas. REP, nómina (incluida una revisiónE2026), Carta Porte, firmas, certificados, estatus SAT y todos los demás catálogos/condicionales quedan expresamente fuera del alcance.

## Pruebas realizadas

`tests/fiscal/evidence/tests.json` registra59 pruebas unittest, sus subcasos y versiones reales de Python/lxml/libxml2/Expat. Se comprueban13 fixtures sintéticos materializados:11 pasan XSD completo, uno carece de SubTotal y falla XSD, y uno con complemento desconocido queda PENDING. El fixture con agregado federal ausente pasa XSD pero falla reglas técnicas, mostrando por qué ambos niveles son distintos. Los fixtures no son CFDI emitidos por el SAT ni están firmados realmente.

Casos adicionales: CFDI3.3 histórico, varios impuestos/conceptos, IEPS cuota, límites de producto por precisión reportada, impuestos locales retenidos, descuentos, moneda desconocida, brecha histórica de cuotas, alteración/ausencia de esquema, namespace falso, límite por bytes antes de lectura completa, XML malformado, DTD/XXE y CLI con códigos0/1/2/3. Se prueba un schemaLocation externo sin acceso de red y se impide sobrescribir el XML de entrada con el reporte.

El verificador de entrega comprueba nuevamente fuentes/derivados, vínculo entre hashes de código y pruebas, original/legacy, recursos UI y las60 referencias congeladas. Las pruebas visuales de SPEC011 se conservan como evidencia histórica; no se repiten ni se presentan como nuevas capturas porque esta fase no modifica UI, desktop ni JavaScript.

## Dependencias y operación

Runtime: lxml6.1.3, wheel Windows x64/CPython3.11 fijado por hash en `requirements/fiscal.txt`, dentro de `.venv`. xlrd2.0.2 es exclusivo de mantenimiento de catálogos (`fiscal-dev.txt`). Las versiones reales y metadatos de licencia observados están en `tests/fiscal/evidence/environment.json`; no se certifica todavía la distribución portable de esas licencias.

Comandos y contrato en [16_CONTRATO_MOTOR_FISCAL](16_CONTRATO_MOTOR_FISCAL.md) y [scripts/fiscal/README](../scripts/fiscal/README.md). No se ha generado EXE, conectado al SAT ni subido XML de clientes.

## Siguiente integración

El contenedor Qt continúa con el puente de diagnóstico de SPEC011 y el flujo fiscal legado. La siguiente migración debe introducir un job/worker cancelable, acceso nativo autorizado por selección del usuario, adapter de filas que conserve Decimal como cadena, hallazgos y selección común con exportación. Debe sustituir de forma conjunta importación, resúmenes y visor/exportación que hoy dependen de fórmulas JavaScript, conservando los controles y comparaciones visuales. No basta con exponer un slot que deje cifras viejas en los demás reportes.
