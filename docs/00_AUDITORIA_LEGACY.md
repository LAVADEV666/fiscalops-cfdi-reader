# FASE 0 — Auditoría integral del HTML V21.1

**Fecha:** 2026-11-06 (America/Mexico_City). **ESTADO: PARTIAL**: entregables estáticos y diagnósticos de funciones completados; navegación real y capturas pendientes por `BLOCKED_VISUAL_BASELINE`. Este estado no certifica el producto. El alcance de esta ejecución termina en la auditoría, conforme al apartado 16 del megaprompt; no incluye reconstrucción ni EXE.

## Fuente y conservación

El único archivo inicial del directorio era `FiscalOps_CFDI_READER_SSGT_V21_1_PRO.html`: 905,818 bytes, 1,181 líneas. No hay repositorio Git, AGENTS.md local, dependencias declaradas ni pruebas previas en el directorio inspeccionado. La copia íntegra está en `legacy/`, sin alterar el original.

SHA-256 de ambos archivos: `33eeed2334a683b5360c2fc4f9cabc26885be66fef8714e4278f97235b8c373b`.

Se extrajeron cinco bloques CSS en orden de cascada, un PNG único repetido cuatro veces y los catálogos originales en `assets/legacy/`. Los iconos restantes son texto/emoji del HTML y de los generadores JavaScript: deben conservarse con su contexto, no sustituirse por otra biblioteca. `tests/audit/evidence/inventory.json` contiene hashes, ubicaciones, elementos, funciones y familias de catálogos. Las referencias Lxxx de estos documentos siempre apuntan al HTML ORIGINAL, no al JavaScript extraído.

## Método y límites de evidencia

- **EC — Error confirmado:** salida reproducida con funciones reales del archivo; se identifica el diagnóstico Nxx. Para el lector XML se usó un adaptador de nodos de Python ElementTree y UI simulada. Confirma lógica y recorridos sobre esos nodos, no comportamiento de DOMParser de navegador ni cumplimiento XSD.
- **RC — Riesgo por lectura de código:** ruta identificada y razonada, sin reproducción integral.
- **HP — Hipótesis pendiente:** requiere un disparador y una sesión real; no se presenta como error confirmado.
- **NC — Funcionalidad no comprobada:** existe código, pero falta probar el comportamiento correspondiente.

Se inspeccionaron markup, los cinco CSS, los dos scripts completos, catálogo estructurado y sus metadatos, lectores, almacenamiento, reportes, visor y exportadores. El índice de funciones es léxico, no un AST ni una cobertura de ejecución. La suite Node inicializa el primer script completo con dobles de UI y expone funciones desde su cierre; no corrige ni reemplaza las funciones que audita. No se ejecutó el segundo script visual en un navegador real.

La ejecución headless de Edge devolvió código 0 sin DOM ni salida diagnóstica, incluso en un intento con escalación. No demuestra que el HTML funcione o falle. La apertura `file://` con el navegador integrado fue rechazada por su política de URL. No se intentó sortear esa restricción. npm no resolvió `registry.npmjs.org` (`ENOTFOUND`); no se instalaron paquetes. El mecanismo alternativo es ejecución de funciones en Node, sin navegador. No hay capturas, métricas DPI ni comparación visual: **BLOCKED_VISUAL_BASELINE**. La fase 1 debe habilitar una vía de prueba local permitida, o recibir capturas y una ejecución del responsable en el entorno objetivo.

## A. Implementaciones superpuestas: qué se ejecuta

El primer `<script>` abre un único IIFE estricto en L535 y termina en L1170. Las declaraciones de función se elevan dentro de ese cierre: las últimas declaraciones de mismo nombre sustituyen las anteriores incluso para las llamadas que aparecen antes de ellas. Las asignaciones posteriores `nombre=function` se aplican al llegar a esa línea. Los manejadores `onclick` sustituyen propiedades anteriores, pero NO quitan escuchas `addEventListener`.

| Símbolo/ruta | Versiones localizadas | Resolución y consecuencias |
|---|---|---|
| `parseCFDI` | L634 y L986 | Activa L986, estructurada con DOMParser; NO el lector regex L634. N01 y N26 lo verifican en VM. |
| `process` | L596 y L1021 | Activa L1021: conserva `readErrors` durante la sesión. No es correcto atribuirle únicamente los `console.warn` de L608. |
| `unzipFile` | L615 y L1041 | Activa L1041: límites nominales 300 MB ZIP / 500 MB declarados / 35 MB por entrada / 20,000 entradas. |
| `getiva`, `getret` | L683 | Permanecen definidos, pero el parser activo no los invoca (N26). El error de IVA sigue presente por otra asignación, L1003. |
| `addTaxAnalysis` | L624 | Única definición, compartida con el nuevo lector L1005; conserva contratos textuales antiguos incompatibles. |
| `render`, `renderTable`, `allRows`, filtros | L676→1067, L677→1063, L667→1044, L542→1085 | Se usan las declaraciones V19 finales; caché de filas incluye versión del parser, pero sólo longitud de arrays. |
| `renderChecks` | L682, L1071; asignación L1128 | Activa asignación V21 de tarjetas; ya no llama `bindColumnRows`: orden, ancho y fijado de V19 carecen de controles en ese editor. |
| `applyColumnEditor` | L1075; asignación L1129 | Activa V21; reconstruye selección sólo desde checks actualmente renderizados y borra widths/pinned. |
| `allFieldRows`, `openPreview` | L706/1087→1135; L709→1136 | Activas asignaciones V21; el visor final no incluye un panel explícito de hallazgos. |
| Excel visible | L684, L1096, L1166 | `#excel.onclick=v21OpenExport`; genera XLSX verdadero con `v21BuildXlsx`. `dlExcel` L1079 queda en rutas técnicas ocultas y produce HTML con extensión XLS. |
| `PARSER_VERSION` | L541→L726 | Valor activo `SSGT_V20_DOM_REPORTS_20260729`; `APP_SCHEMA_VERSION=19.0.0`. No coincide con el título visual 21.1 y no hay versión separada de reglas. |
| Escalado | `v21Scale` L1120 y `applyV20Scale` L1173 | Dos escuchas resize modifican `--v20-scale`; el segundo script vuelve a escribirla. Fidelidad y DPI requieren medición real. |

Hay 242 declaraciones nombradas (incluidos helpers anidados), 28 nombres con declaraciones repetidas y 68 asignaciones léxicas a funciones (incluyen propiedades de eventos). Inventario completo y ubicaciones en documento 01 y JSON. No deben eliminarse capas por su etiqueta de versión sin analizar sus rutas activas.

## B. Importes y precisión

`num` L539 usa parseFloat y convierte ausencia/NaN en cero. `nval` L974 usa Number y convierte ausencias, texto inválido y no finitos en cero. `sum` L683, `taxSum` L623, cálculos L999–1015 y agregaciones L1150–1157 usan números binarios. N08 reproduce `0.1+0.2=0.30000000000000004` y `(1.005).toFixed(2)='1.00'`. No es una comprobación de una regla SAT de redondeo; demuestra la representación elegida.

`addTaxAnalysis` redondea indiscriminadamente a dos decimales y compara con tolerancia fija .02; el parser usa `localTolerance` L966 según catálogo de moneda sin documentar límites oficiales por campo. `currencyDecimals` no utiliza vigencia histórica. La ausencia de importes se pierde en cálculos, exportación TXT y valores por defecto. N18 demuestra que cero numérico pasa a vacío en TXT. Deben preservarse original, nulo, moneda, precisión y calculado por separado.

## C. Impuestos: hallazgos reproducidos

| ID de riesgo | Evidencia | Resultado |
|---|---|---|
| F01 | L1003 / N02 | XML diagnóstico con IVA16=16 e IEPS=8: columna IVA=24. La suma federal se presenta como IVA. |
| F02 | L984, L624 / N03 | `parseTaxNode` produce `Retención`; taxSum espera `Retencion`. ISR retenido=0.00 pese a nodo y total=10. |
| F03 | L1006, L1015 / N04 | Local de 3 añadido a `globalTaxes` y nuevamente como `localTras`: total reportado119 produce diferencia−3. |
| F04 | L624 / N06 | Exento sin tasa se incluye tanto en BaseTasa0=100 como en BaseExenta=100. Falta filtrar TipoFactor para tasa cero. |
| F05 | L1004 / N07 | Si falta el total global (caso deliberadamente incompleto), fallback suma concepto16+global16 y escribe IVA32. No es una prueba con CFDI válido. |

No se confirmó duplicación general de todos los impuestos: `addTaxAnalysis` elige globales o conceptuales, no ambos, y los impuestos REP están en `paymentTaxes`. Los problemas están en rutas concretas anteriores. Los impuestos locales se agregan después del análisis de impuestos y se mezclan con los federales en la colección `globalTaxes`, aunque conservan `NivelImpuesto=LOCAL`. La inferencia ISH/TUA por descripción de conceptos de L648–653 fue sustituida: el parser activo sólo detecta nombres de impuestos locales L1006. El visor conserva campos antiguos que pueden quedar vacíos.

## D. XML, complementos e integridad

El lector activo usa jerarquía de hijos y localName, pero `directChildren` y `descendants` no verifican namespaceURI (L967–972). N05 acepta un Comprobante con namespace `urn:not-sat`. VersionCFDI se conserva, pero no selecciona lector/XSD por versión. No se implementan XSD, cadena original, validación criptográfica, matrices SAT ni consulta oficial. Los hallazgos son controles locales con referencia textual genérica, no prueba normativa.

L973 rechaza DTD/ENTITY y limita texto a 30×1024² caracteres, no bytes; N12 prueba el rechazo antes del adaptador XML. L683 `normalize`, utilizado antes del parser, elimina todo lo que preceda a Comprobante; N25 demuestra que puede eliminar el DOCTYPE. No se ha demostrado explotación XXE: el riesgo es que el control se aplica después de modificar el documento. `f.text()` y TextDecoder UTF-8 del ZIP no respetan de manera explícita XML con otra codificación. HTML importado se trata como texto y no se navega ni inserta como HTML activo; normalización de envoltorios es limitada y puede dejar sufijos inválidos.

**Pagos:** L1009 sí recorre TODOS los Pago y DoctoRelacionado, separa niveles DOCUMENTO/PAGO y mantiene Total del CFDI aparte del complemento. N11 conserva 2 pagos, 2 documentos, totalpagos100 y CFDI0. No se debe diagnosticar que usa sólo el primer Pago por leer L661. Sigue faltando interpretación completa de Totales (sólo MontoTotalPagos), reglas oficiales, relación moneda DR en filas tributarias y consistencia de equivalencias y agregaciones.

**Nómina:** L1010 extrae atributos laborales, percepciones, deducciones, otros pagos, subsidio, incapacidades y horas extra; conserva filas. No modela íntegramente jubilación/separación, acciones, compensación de saldos y demás subestructuras. No contiene selector por revisión E 2026 ni fuente que permita afirmarla soportada. La investigación normativa corresponde a fase 3; este informe no afirma vigencia de una revisión sin consultar sus documentos.

**Carta Porte:** L1011 extrae ubicaciones, mercancías y figuras por nombre local; no es soporte integral 3.1 ni de los cuatro medios de transporte. Faltan domicilios, conexiones mercancía-ubicación, autotransporte, marítimo, aéreo, ferroviario y subestructuras. Los complementos desconocidos se inventarían L997 y quedan en XMLRaw; falta estado explícito NO INTERPRETADO.

No se exportan como columnas estructuradas Sello, Certificado o InformaciónGlobal, entre otros campos; sí permanece el XMLRaw. Es preservación del origen, no extracción integral. Fecha y FechaTimbrado pierden hora al pasar por fmtDate (N22). El árbol XML L705 se corta a profundidad>8 y no muestra todos los textos/CDATA: su rótulo «completo» excede la implementación.

## E. Memoria y metadata

IndexedDB `FiscalOpsSSGT`, objectStore `kv` L576; caché por RFC `memory_<RFC>` L570, no por carpeta. Identidad `path,size,lastModified` L571–573: N09 demuestra firmas iguales, no identidad de contenidos. Misma ruta/tamaño/fecha puede ocultar cambios. Carpetas diferentes bajo el mismo RFC y rutas relativas iguales pueden reutilizar documentos incorrectos. Versionar parser invalida la caché completa L583, pero no hay versión de reglas ni SHA-256 del contenido.

Los archivos eliminados se cuentan L590 y dejan de incluirse en `cachedArrays(files)` L591; permanecen en memory.files, sin historial de desaparición/restauración. No hay borrado indiscriminado de DB por desconectar carpeta; tampoco hay índice/historial transaccional separado. `kvPut` resuelve sin esperar `tx.oncomplete`, no registra fallos de transacción y no cierra conexiones. Los errores no se guardan en cada record L1035: una entrada fallida puede quedar cached con arrays vacíos y su incidente desaparecer en la siguiente sesión (RC, pendiente de reproducción IDB real). `seen` se vacía y no se precarga con UUID de cfd cacheado L1022–1023: duplicados entre documentos nuevos y caché pueden no marcarse.

`parseMeta` L616 retiene sólo UUID, estatus y fecha de cancelación, sin procedencia ni los demás encabezados. N10 acepta UUID inválido. `metaMap` L667 aplica último archivo gana; N21 demuestra que un conflicto se convierte silenciosamente en CANCELADO. No compara fecha de fuente ni registra conflicto. Las etiquetas Estado SAT/Vigentes se basan en metadata local; la nota «no sustituye validación oficial» existe, pero no presenta antigüedad de la metadata junto al estado.

## F. Reportes, controles y exportaciones

Hay 21 tipos de reporte y 182 entradas en COLUMN_REGISTRY en ejecución VM (N01). `findings` tiene DEFAULTS y columnas, pero no REPORT_DEFS: N19 confirma que no aparece como reporte. L1067 vacía assistantBox; CSS V20 lo oculta y el visor V21 no llama findingsFor. RC: hallazgos calculados con visibilidad insuficiente. N20 muestra que `reportOptionsForType('I')` incluye pagos porque todas las definiciones incluyen tipo vacío; no se restringen efectivamente reportes por tipo.

N13 prueba orden léxico erróneo de fechas dd/mm/yyyy: 31/01 se ordena después de 01/02. Tablas paginan al renderizar (30/50/100/200) pero calculan, filtran, clonan y ordenan en memoria, con setupFilters en cada render. El listener de búsqueda inmediato de L684 coexiste con debounce L1085; hay trabajo duplicado (RC). `typeTabs` tiene addEventListener L685 y onclick L1085: posible doble toggle (HP, necesita DOM real). `tbody` tiene dos manejadores de apertura L718 y L1101 (HP).

Editor final L1129 toma sólo checks visibles tras búsqueda y borra estado de anchos/fijado: RC de pérdida de selección. Cerrar no revierte `visibleCols` modificado en onchange L1128 (RC). Los antiguos controles de orden/ancho no están activos; su ausencia debe registrarse en la migración.

XLSX principal V21 **sí es un ZIP OOXML**, no HTML renombrado. Se generó `synthetic-export.xlsx`, verificando CRC, nueve partes XML, dos hojas incluida vacía, UUID inline text y celda numérica116.25. No se abrió en Excel real ni se certificó interoperabilidad general. N14: fechas como inlineStr. N15 + verify_audit: U+0001 se conserva y hace XML inválido. N16: el límite corta silenciosamente rows.slice(0,1048575); se usó un objeto diagnóstico para no asignar un millón de filas, no se hizo benchmark masivo. Construcción map/join/concatenación copia el libro entero en memoria; setTimeout40 no traslada trabajo a worker ni permite cancelar mientras genera.

`spreadsheetSafe` L1076 protege valores de texto que comienzan con =,+,-,@; N17 verifica =1+1. XLSX numérico convierte Number; RFC/UUID se conservan como texto según columna. CSV entrecomilla y duplica comillas; TXT sustituye separadores y saltos, lo que pierde contenido, además del cero numérico N18. Hoja principal usa filtered/currentReportRows/sortedRows/exportColumns, común con pantalla; hojas analíticas usan summary filtrado y no necesariamente el subconjunto del reporte derivado (canceled, duplicates, etc.): riesgo de universos diferentes. Hojas analíticas vacías se omiten L1165 aunque el diálogo cuenta selecciones. Exportación técnica oculta conserva XLS HTML y rutas heredadas de estatus emoji que ya no coinciden.

ZIP L1041: N23 acepta contenido alterado con CRC inválido y N24 omite método no soportado sin incidente. Los tamaños límites se basan en central directory antes de descomprimir; no se contrasta salida real ni ratio ni CRC ni cifrado/ZIP64/discos. Una firma central incorrecta hace break, entregando resultado parcial sin error. No escribe nombres ZIP en disco: ZIP Slip con escritura NO está demostrado; validar rutas será requisito cuando exista extracción real.

## Catálogos, privacidad y rendimiento

18 familias: FormaPago22, Moneda183, TipoDeComprobante5, Exportacion4, MetodoPago2, Periodicidad5, Meses18, TipoRelacion7, RegimenFiscal19, Pais250, UsoCFDI24, ClaveUnidad2418, ObjetoImp8, Impuesto3, TipoFactor3, TasaOCuota19, Aduana50, Estado95. `TasaOCuota` es array y `catalogEntry` lo descarta L961. Hay fechas start/end y meta locales; no se aplican vigencias. Periodicidad es la de CFDI global; se usa para PeriodicidadPago de nómina L963: verificar catálogo específico. No se encontraron paquetes XSD/XSLT ni catálogos completos de nómina/Carta Porte ni evidencia de origen/hashes normativos.

Las entradas sensibles se difuminan en algunas celdas L1060, pero el title del td L1063 contiene el valor sin máscara y XLSX/CSV lo exportan. IndexedDB almacena XMLRaw y datos laborales en claro bajo la seguridad del perfil del navegador, no cifrado de aplicación. No hay telemetría ni cliente SAT implementado identificado en los dos scripts; la comprobación offline real no se ejecutó. Nunca equivaler blur a control de acceso o cifrado.

Proceso y exportador corren en el hilo JavaScript. `pause()` cada 25 archivos cede entre bloques, pero un XML grande, ZIP o render puede bloquear. Los límites sólo se evalúan tras cargar archivos/bytes. No hay cancelación de importación, exclusión de dos procesos simultáneos, recuperación de lote ni historial transaccional. No se midieron 100/1k/10k/50k XML: corresponde a fase 8.

## Pruebas ejecutadas y trazabilidad

| Comando | Resultado/evidencia |
|---|---|
| `python scripts/audit_legacy.py` | Preservación y extracción; inventory.json. |
| `node --check tests/audit/evidence/script-01.js` y `script-02.js` | Ambos aceptados sintácticamente; no implica ejecución en navegador. |
| `node tests/audit/run_node.cjs` | 26 observaciones reproducidas; node-results.json. Incluyen comportamientos correctos y defectos esperados; NO 26 criterios de producto aprobados. |
| `python scripts/verify_audit.py` | Hashes, seis documentos, ZIP/XML y reproducciones; verification.json. |
| `python scripts/run_audit_browser.py` (intento histórico; runner retirado) | Edge salida vacía, sin resultados; no se usa como prueba aprobada. |
| Navegador integrado `file://` | Política bloquea protocolo; sin capturas. |

Requisitos A–F se relacionan respectivamente con tabla de resolución, sección B, sección C, sección E, sección F y secciones D/E/F. Inventario detallado: 01; riesgos con prueba/acción: 02; arquitectura y fases: 03; conservación: 04; tareas y aceptación: 05. El reporte de fase está en `FASE_0_REPORTE.md`.

**Regresiones introducidas:** ninguna modificación al prototipo; identidad verificada por hash. No se afirma ausencia de defectos preexistentes ni equivalencia visual de una aplicación futura. **Siguiente paso:** revisión del punto de control y ejecución de FASE 1 según documento 03, empezando por acceso visual local permitido y fixtures anónimos.
