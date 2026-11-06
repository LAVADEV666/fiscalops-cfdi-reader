# Inventario funcional del prototipo

Referencia: HTML original; líneas en formato Lxxx. **Estado** usa EC/RC/HP/NC definidos en 00. Una implementación presente no prueba que el control funcione en una sesión real. No había pruebas previas; Nxx son los diagnósticos incorporados en `tests/audit/run_node.cjs`.

| Función/experiencia | Ubicación y dependencia activa | Estado y prueba disponible | Riesgo y estrategia de conservación/migración |
|---|---|---|---|
| Inicio automático y botón Iniciar | #s1 L513, pg L539, timer1600 | NC visual | Conservar logo, animaciones, tiempo y transición; capturar antes de refactorizar. |
| Carga, archivos, drop | #s2 L514, addFiles L595, detect L1042 | NC de selección real | Extensión filtra antes de detección; migrar a servicio de identificación por contenido con conteos. |
| XML | process L1021, normalize L683, parseCFDI L986 | N02–08,N11,N12,N25 con DOM adaptado | Namespace, precisión, campos incompletos; reemplazo sólo después de contratos y fixtures. |
| ZIP y paquetes SAT | unzipFile L1041, inflateRaw L615 | N23,N24: stored; deflate NC | No CRC/cifrado/ZIP64 ni salida acotada real; biblioteca segura en worker. |
| TXT metadata | parseMeta L616, metaMap L667 | N10,N21 | Pérdida de campos/procedencia y último gana; tabla de fuentes y conflictos. |
| HTML/HTM XML escapado | normalize L683, detect L1042 | NC envoltorios reales | No ejecuta contenido HTML; sustituir extracción textual segura por contrato explícito. |
| Conectar/reconectar/actualizar carpeta | L584–589, botones #folder,#changeFolder,#refreshFolder | NC permisos navegador | File System Access API; preservar árbol/nombres; migrar diálogo Qt y servicio de escaneo sólo lectura. |
| RFC por nombre y entrada opcional | detectRFCFromFolder L569, empresaRFC L564, norm L683 | RC extracción por patrón | Sin comprobación de identidad oficial; separar RFC elegido, detectado y origen. |
| Procesar nuevos / siguiente | process L1021, nextScreen L632, bindings L595 | NC lote real | #reprocessAll llama nextScreen, NO process(forceAll=true); mantener intención y documentar nueva acción de reproceso. |
| Memoria local y olvidar | L568–592; IndexedDB kv | N09 sobre firmas; IDB NC | SHA-256, parser+reglas, transacción e historial SQLite; no copiar debilidades. |
| Emitidos/recibidos | docSide L565, clas L683, filtros L630 | RC | P/N tienen clasificación PAGO/NOMINA mientras origen usa RFC; documentar ambos campos. Prioridad emisor si mismo RFC. |
| Año/mes y búsqueda UUID/RFC/nombre/serie/folio | L563,L668,L1085; #year,#month,#q | NC interactiva | Mes existe inicialmente oculto por CSS; probar cascada antes de declarar control visible. Índices SQL y consulta única. |
| Tipo, estatus, PUE/PPD y origen | L1045,L1046,L1085; segmentos L515 | HP doble toggle; N20 alcance reportes | Evitar listeners superpuestos; conservar estados activos y filtros de pantalla/exportación. |
| Indicadores y totales por moneda | summaryCards L1066, renderTotals L1065 | NC visual; aritmética N08 | Separar monedas ya es intención activa; no sumar pagos a Total CFDI. Totales de summary pueden diferir del reporte derivado. |
| Tabla, paginación, orden, densidad | renderTable L1063, sortedRows L1062, compareValues L1061 | N13 fecha; NC teclas/scroll | Página sólo al pintar; SQL paginado, fechas ISO internas y presentación actual. |
| Editor y perfiles | registry L752–960, profileColumns L959, L1128–1131 | NC interacción; RC pérdida de selección | Conservar tarjetas V21; separar borrador de selección; búsqueda no debe descartar checks ocultos. |
| Preferencias de columnas | prefKey L1049, save/load L1050–1051 | NC persistencia | Guardar por empresa,tipo,reporte,perfil,versión; migraciones explícitas. |
| Orden/ancho/fijación de columnas heredados | L1072–1075 vs L1128–1129 | RC funcionalidad sustituida | Tarjetas V21 no ofrecen los controles V19; no prometerlos activos ni reintroducir rediseño automático. |
| Visor integral y cinco pestañas | openPreview L1136; helpers L693–708 | NC visual/teclado | Resumen, Impuestos, Conceptos, Todos los datos, XML visual. Preservar geometría y scroll con evidencia. |
| Árbol XML | xmlTree L705 | RC profundidad/textos | Preserva XMLRaw, pero vista truncada >8; lectura completa futura sin contenido activo. |
| Hallazgos locales | finding L977, L999–1017, renderAssistant L1069 | N19 reporte ausente; NC exposición | Datos existen; render final vacía asistente y visor omite hallazgos. Añadir acceso sin declarar validación SAT. |
| Exportación XLSX multipestaña | L1138–1167; #excel,#exportModal | N14–17; ZIP/XML verificado | OOXML artesanal verdadero; reemplazar por openpyxl conservando diálogo, primera hoja, opciones y tipos. |
| Hojas analíticas | V21_ANALYSES L1111–1119; L1151–1159 | NC reconciliación completa | Resumen, monedas, mensual, contrapartes, formas/métodos, impuestos, conceptos; usar universo explícito. |
| CSV | csvValue/dlCSV L1080–1081; binding L1094 | N17 protección común; NC archivo CSV completo | Cita/escape implementados; probar CRLF, Unicode y fórmula; conservar ceros. |
| TXT | buildLines L1082, saveTxt L678, binding L1098 | N18 pierde cero | Delimitador~ reemplazado por espacio; documentar pérdida; formato reversible o política declarada. |
| Exportaciones técnicas ocultas | #excelf,#exportPack,#cancel,#sinmeta L515; L1083,L1097,L684 | RC rutas heredadas | XLS con HTML; filtros por emoji obsoletos; decidir reemplazo sin presentarlas como XLSX principal. |
| Errores por archivo | readErrors L727, process L1030–1035, reporte L750 | RC caché pierde incidentes | Guardar incidentes e historial; métodos ZIP omitidos deben ser reportados. |
| Límites y seguridad XML | parseXmlDocument L973 | N12,N25; XXE real NC | Rechazo preámbulo original antes de normalizar; parser seguro con límites por bytes/nodos. |
| Catálogos | SATCAT_RAW L694, catalogEntry L961 | 18 familias extraídas; N01 | Vigencia no aplicada, arrays ignorados, catálogos especializados incompletos; fuentes oficiales versionadas después. |
| Privacidad | sensitive registry y formatCell L1060,L1063 | RC tooltip expone valor | Blur sólo visual; documentar almacenamiento local y accesos, evitar datos reales en fixtures/logs. |
| Rendimiento/cancelación | pause L683, process L1036, export L1165 | NC medición; sin cancelación efectiva | Workers y eventos; benchmark posterior con métricas reproducibles. |

## Reportes activos y trazabilidad

| ID | Filas y origen | Ubicación del lector |
|---|---|---|
| summary | Una por CFDI | L986–1020 |
| concepts / conceptTaxes | Concepto / impuesto asociado | L999–1001 |
| globalTaxes | Federal y LOCAL con nivel | L1003,L1006 |
| relations | Grupo y UUID relacionado | L1008 |
| payments / paymentDocs / paymentTaxes | Pago / documento / impuesto por nivel | L1009 |
| payrollPerceptions / payrollDeductions / payrollOtherPayments | Desgloses de nómina | L1010 |
| payrollIncapacities / payrollOvertime | Incapacidad / horas extra | L1010 |
| locations / goods / transportFigures | Carta Porte parcial | L1011 |
| complements | Nombre, namespace, versión | L997 |
| missingMetadata / canceled / duplicates | Derivados de resumen filtrado | L1047 |
| readErrors | Incidentes de toda la sesión | L1030–1035,L1047 |

`findings` está definido en DEFAULTS/registry pero ausente en REPORT_DEFS. No confundirlo con un reporte accesible. Los reportes readErrors no respetan filtros por documento porque no comparten entidad CFDI; la UI debe explicar su ámbito. Las claves de detalle mantienen relaciones uno-a-muchos, aunque varios datos globales siguen concatenados para compatibilidad.

## Dependencias y pruebas por capacidad

Runtime actual: navegador con DOMParser, IndexedDB, TextEncoder/Decoder, Blob/URL, Intl, File.text/arrayBuffer, File System Access y DecompressionStream('deflate-raw'). No hay imports de bibliotecas externas ni servidor backend. Compatibilidad de cada API y permisos no probados en Windows objetivo. Dependencias del diagnóstico: Python3.11 stdlib y Node24.21.0; no son dependencias entregadas de aplicación.

El contrato de migración es conservar primero los identificadores, eventos de negocio y formas de filas. Cada función de la tabla requiere aceptación visual (04), datos equivalentes y una prueba específica antes de sustituirse. Los diagnósticos Nxx fijan errores observados del legado; al migrar deben convertirse en expectativas corregidas, no conservar los errores porque sus tests actuales pasen.

<!-- FUNCTION_INDEX -->

## Índice completo de declaraciones nombradas

Índice léxico reproducible: incluye helpers anidados; no cubre funciones flecha/anónimas como símbolos propios ni sustituye un AST. Las resoluciones efectivas de funciones de producto están verificadas en00; las propiedades de eventos requieren considerar su elemento y API de registro.

| Nombre | Líneas del HTML original | Observación |
|---|---|---|
| `el` | 539 | Declaración única en índice |
| `pg` | 539 | Declaración única en índice |
| `num` | 539 | Declaración única en índice |
| `money` | 539 | Declaración única en índice |
| `int` | 539 | Declaración única en índice |
| `setStatus` | 539 | Declaración única en índice |
| `setupFilters` | 542, 1085 | Declaración repetida; última L1085 |
| `emisionParts` | 563 | Declaración única en índice |
| `empresaRFC` | 564 | Declaración única en índice |
| `docSide` | 565 | Declaración única en índice |
| `sideLabel` | 566 | Declaración única en índice |
| `detectRFCFromFolder` | 569 | Declaración única en índice |
| `memName` | 570 | Declaración única en índice |
| `fileKey` | 571 | Declaración única en índice |
| `fileSig` | 572 | Declaración única en índice |
| `sameSig` | 573 | Declaración única en índice |
| `updateFolderPanel` | 574 | Declaración única en índice |
| `updateMemoryPanel` | 575 | Declaración única en índice |
| `idbOpen` | 576 | Declaración única en índice |
| `kvGet` | 577 | Declaración única en índice |
| `kvPut` | 578 | Declaración única en índice |
| `kvDel` | 579 | Declaración única en índice |
| `saveFolderHandle` | 580 | Declaración única en índice |
| `getSavedFolderHandle` | 581 | Declaración única en índice |
| `saveMemory` | 582 | Declaración única en índice |
| `loadMemoryForRFC` | 583 | Declaración única en índice |
| `ensureFolderPermission` | 584 | Declaración única en índice |
| `connectFolder` | 585 | Declaración única en índice |
| `reconnectFolder` | 586 | Declaración única en índice |
| `refreshConnectedFolder` | 587 | Declaración única en índice |
| `scanFolderHandle` | 588 | Declaración única en índice |
| `walkFolder` | 589 | Declaración única en índice |
| `applyMemoryDiff` | 590 | Declaración única en índice |
| `cachedArrays` | 591 | Declaración única en índice |
| `forgetMemoryDbl` | 592 | Declaración única en índice |
| `fmtDate` | 594 | Declaración única en índice |
| `pad` | 594 | Declaración única en índice |
| `ymd` | 594 | Declaración única en índice |
| `addFiles` | 595 | Declaración única en índice |
| `renderFileList` | 595 | Declaración única en índice |
| `process` | 596, 1021 | Declaración repetida; última L1021 |
| `unzipFile` | 615, 1041 | Declaración repetida; última L1041 |
| `inflateRaw` | 615 | Declaración única en índice |
| `detect` | 616, 1042 | Declaración repetida; última L1042 |
| `parseMeta` | 616 | Declaración única en índice |
| `impName` | 618 | Declaración única en índice |
| `firstTaxAttr` | 619 | Declaración única en índice |
| `taxItemFromNode` | 620 | Declaración única en índice |
| `ratePct` | 621 | Declaración única en índice |
| `taxItemsFromNodes` | 622 | Declaración única en índice |
| `taxSum` | 623 | Declaración única en índice |
| `addTaxAnalysis` | 624 | Declaración única en índice |
| `parseDetailItem` | 625 | Declaración única en índice |
| `taxRowsFromRows` | 626 | Declaración única en índice |
| `excelTable` | 627, 1078 | Declaración repetida; última L1078 |
| `allowedColsForContext` | 628, 1052 | Declaración repetida; última L1052 |
| `smartExportCols` | 629, 1053 | Declaración repetida; última L1053 |
| `applyOriginFilter` | 630 | Declaración única en índice |
| `ensureSmartOrigin` | 631 | Declaración única en índice |
| `nextScreen` | 632 | Declaración única en índice |
| `parseCFDI` | 634, 986 | Declaración repetida; última L986 |
| `joinVals` | 637 | Declaración única en índice |
| `attrsStr` | 637 | Declaración única en índice |
| `hasNode` | 637 | Declaración única en índice |
| `sumNodes` | 650 | Declaración única en índice |
| `metaMap` | 667 | Declaración única en índice |
| `statusEmoji` | 667, 1043 | Declaración repetida; última L1043 |
| `allRows` | 667, 1044 | Declaración repetida; última L1044 |
| `reportRowsBase` | 668 | Declaración única en índice |
| `applyReportFilters` | 669, 1045 | Declaración repetida; última L1045 |
| `filtered` | 670, 1046 | Declaración repetida; última L1046 |
| `typeLabel` | 671, 1054 | Declaración repetida; última L1054 |
| `presetForType` | 672 | Declaración única en índice |
| `setActiveType` | 673, 1055 | Declaración repetida; última L1055 |
| `renderTabs` | 674, 1058 | Declaración repetida; última L1058 |
| `renderTotals` | 675, 1065 | Declaración repetida; última L1065 |
| `render` | 676, 1067 | Declaración repetida; última L1067 |
| `stat` | 676 | Declaración única en índice |
| `renderTable` | 677, 1063 | Declaración repetida; última L1063 |
| `header` | 678 | Declaración única en índice |
| `buildLines` | 678, 1082 | Declaración repetida; última L1082 |
| `saveTxt` | 678 | Declaración única en índice |
| `dl` | 678 | Declaración única en índice |
| `dlExcel` | 678, 1079 | Declaración repetida; última L1079 |
| `renderChecks` | 682, 1071 | Declaración repetida; última L1071; asignación final L1128 |
| `tag` | 683 | Declaración única en índice |
| `tags` | 683 | Declaración única en índice |
| `at` | 683 | Declaración única en índice |
| `find` | 683 | Declaración única en índice |
| `getiva` | 683 | Declaración única en índice |
| `getret` | 683 | Declaración única en índice |
| `normalize` | 683 | Declaración única en índice |
| `trimq` | 683 | Declaración única en índice |
| `clean` | 683 | Declaración única en índice |
| `out` | 683 | Declaración única en índice |
| `safe` | 683 | Declaración única en índice |
| `dec` | 683 | Declaración única en índice |
| `esc` | 683 | Declaración única en índice |
| `norm` | 683 | Declaración única en índice |
| `tipoDesc` | 683 | Declaración única en índice |
| `clas` | 683 | Declaración única en índice |
| `sum` | 683 | Declaración única en índice |
| `pause` | 683 | Declaración única en índice |
| `aItem` | 691 | Declaración única en índice |
| `renderAssistant` | 692, 1069 | Declaración repetida; última L1069 |
| `previewRow` | 693 | Declaración única en índice |
| `cat` | 695, 962 | Declaración repetida; última L962 |
| `catalogKindForField` | 696, 963 | Declaración repetida; última L963 |
| `catalogHintFor` | 697, 964 | Declaración repetida; última L964 |
| `findingsFor` | 698, 1086 | Declaración repetida; última L1086 |
| `block` | 699 | Declaración única en índice |
| `pairs` | 700 | Declaración única en índice |
| `taxMetric` | 701 | Declaración única en índice |
| `localTaxRows` | 702 | Declaración única en índice |
| `detailTaxRows` | 703 | Declaración única en índice |
| `conceptRows` | 704 | Declaración única en índice |
| `xmlTree` | 705 | Declaración única en índice |
| `node` | 705 | Declaración única en índice |
| `allFieldRows` | 706, 1087 | Declaración repetida; última L1087; asignación final L1135 |
| `tabBtn` | 707 | Declaración única en índice |
| `pane` | 708 | Declaración única en índice |
| `openPreview` | 709 | Declaración única en índice; asignación final L1136 |
| `cd` | 752 | Declaración única en índice |
| `reg` | 753 | Declaración única en índice |
| `profileColumns` | 959 | Declaración única en índice |
| `catalogEntry` | 961 | Declaración única en índice |
| `currencyDecimals` | 965 | Declaración única en índice |
| `localTolerance` | 966 | Declaración única en índice |
| `qname` | 967 | Declaración única en índice |
| `attrN` | 968 | Declaración única en índice |
| `directChildren` | 969 | Declaración única en índice |
| `firstChild` | 970 | Declaración única en índice |
| `descendants` | 971 | Declaración única en índice |
| `firstDesc` | 972 | Declaración única en índice |
| `parseXmlDocument` | 973 | Declaración única en índice |
| `nval` | 974 | Declaración única en índice |
| `approx` | 975 | Declaración única en índice |
| `baseDetail` | 976 | Declaración única en índice |
| `finding` | 977 | Declaración única en índice |
| `copyAttrs` | 978 | Declaración única en índice |
| `taxCodeFromNode` | 979 | Declaración única en índice |
| `taxBaseFromNode` | 980 | Declaración única en índice |
| `taxFactorFromNode` | 981 | Declaración única en índice |
| `taxRateFromNode` | 982 | Declaración única en índice |
| `taxAmountFromNode` | 983 | Declaración única en índice |
| `taxNature` | 984 | Declaración única en índice |
| `parseTaxNode` | 985 | Declaración única en índice |
| `currentReportRows` | 1047 | Declaración única en índice |
| `applicableColumns` | 1048 | Declaración única en índice |
| `prefKey` | 1049 | Declaración única en índice |
| `saveColumns` | 1050 | Declaración única en índice |
| `loadColumns` | 1051 | Declaración única en índice |
| `reportOptionsForType` | 1056 | Declaración única en índice |
| `refreshReportSelectors` | 1057 | Declaración única en índice |
| `statusClass` | 1059 | Declaración única en índice |
| `formatCell` | 1060 | Declaración única en índice |
| `compareValues` | 1061 | Declaración única en índice |
| `sortedRows` | 1062 | Declaración única en índice |
| `currencyGroups` | 1064 | Declaración única en índice |
| `summaryCards` | 1066 | Declaración única en índice |
| `findingLabel` | 1068 | Declaración única en índice |
| `updateColumnSelectionCount` | 1070, 1127 | Declaración repetida; última L1127 |
| `bindColumnRows` | 1072 | Declaración única en índice |
| `moveColumn` | 1073 | Declaración única en índice |
| `nudgeColumn` | 1074 | Declaración única en índice |
| `applyColumnEditor` | 1075 | Declaración única en índice; asignación final L1129 |
| `spreadsheetSafe` | 1076 | Declaración única en índice |
| `exportColumns` | 1077 | Declaración única en índice |
| `csvValue` | 1080 | Declaración única en índice |
| `dlCSV` | 1081 | Declaración única en índice |
| `exportPackage` | 1083 | Declaración única en índice |
| `next` | 1083 | Declaración única en índice |
| `currentReportRowsFor` | 1084 | Declaración única en índice |
| `initV19` | 1088 | Declaración única en índice |
| `openCols` | 1099 | Declaración única en índice |
| `v21Scale` | 1120 | Declaración única en índice |
| `v21Area` | 1123 | Declaración única en índice |
| `v21RowsForEditor` | 1124 | Declaración única en índice |
| `v21ColumnInfo` | 1125 | Declaración única en índice |
| `v21Short` | 1126 | Declaración única en índice |
| `v21Preset` | 1130 | Declaración única en índice |
| `v21FieldArea` | 1133 | Declaración única en índice |
| `v21GroupedFields` | 1134 | Declaración única en índice |
| `v21XmlEscape` | 1138 | Declaración única en índice |
| `v21ColName` | 1139 | Declaración única en índice |
| `v21SheetName` | 1140 | Declaración única en índice |
| `v21CellXml` | 1141 | Declaración única en índice |
| `v21SheetXml` | 1142 | Declaración única en índice |
| `v21U16` | 1143 | Declaración única en índice |
| `v21U32` | 1143 | Declaración única en índice |
| `v21Concat` | 1143 | Declaración única en índice |
| `v21Crc` | 1144 | Declaración única en índice |
| `v21Dos` | 1145 | Declaración única en índice |
| `v21Zip` | 1146 | Declaración única en índice |
| `v21BuildXlsx` | 1147 | Declaración única en índice |
| `v21Cols` | 1148 | Declaración única en índice |
| `v21CustomCols` | 1149 | Declaración única en índice |
| `v21Agg` | 1150 | Declaración única en índice |
| `v21Resumen` | 1151 | Declaración única en índice |
| `v21Monedas` | 1152 | Declaración única en índice |
| `v21MonthKey` | 1153 | Declaración única en índice |
| `v21Mensual` | 1154 | Declaración única en índice |
| `v21Contrapartes` | 1155 | Declaración única en índice |
| `v21Pagos` | 1156 | Declaración única en índice |
| `v21Impuestos` | 1157 | Declaración única en índice |
| `v21Conceptos` | 1158 | Declaración única en índice |
| `v21AnalysisSheet` | 1159 | Declaración única en índice |
| `v21SelectedAnalyses` | 1160 | Declaración única en índice |
| `v21UpdateExportSummary` | 1161 | Declaración única en índice |
| `v21RenderExport` | 1162 | Declaración única en índice |
| `v21OpenExport` | 1163 | Declaración única en índice |
| `v21CloseExport` | 1164 | Declaración única en índice |
| `v21DownloadWorkbook` | 1165 | Declaración única en índice |
| `applyV20Scale` | 1173 | Declaración única en índice |

## Asignaciones a funciones (incluye propiedades de eventos)

| Símbolo/propiedad | Línea |
|---|---|
| `onchange` | 551 |
| `oninput` | 552 |
| `onclick` | 553 |
| `onclick` | 554 |
| `onclick` | 555 |
| `onclick` | 556 |
| `onupgradeneeded` | 576 |
| `onsuccess` | 576 |
| `onerror` | 576 |
| `onsuccess` | 577 |
| `onerror` | 577 |
| `cnt` | 676 |
| `q` | 704 |
| `onclick` | 717 |
| `onclick` | 719 |
| `onclick` | 720 |
| `count` | 1066 |
| `ondragstart` | 1072 |
| `ondragend` | 1072 |
| `ondragover` | 1072 |
| `ondragleave` | 1072 |
| `ondrop` | 1072 |
| `onclick` | 1072 |
| `onchange` | 1072 |
| `onclick` | 1072 |
| `onclick` | 1072 |
| `onchange` | 1072 |
| `onchange` | 1085 |
| `oninput` | 1085 |
| `onclick` | 1085 |
| `onclick` | 1085 |
| `onclick` | 1085 |
| `onclick` | 1085 |
| `onchange` | 1091 |
| `onchange` | 1092 |
| `onclick` | 1093 |
| `onclick` | 1094 |
| `onclick` | 1096 |
| `onclick` | 1097 |
| `onclick` | 1098 |
| `onclick` | 1099 |
| `onclick` | 1099 |
| `onclick` | 1099 |
| `onclick` | 1099 |
| `onclick` | 1099 |
| `onclick` | 1099 |
| `onclick` | 1099 |
| `oninput` | 1099 |
| `onclick` | 1100 |
| `onclick` | 1101 |
| `onkeydown` | 1101 |
| `onscroll` | 1102 |
| `onclick` | 1104 |
| `renderChecks` | 1128 |
| `onchange` | 1128 |
| `applyColumnEditor` | 1129 |
| `onclick` | 1131 |
| `onclick` | 1131 |
| `onclick` | 1131 |
| `onclick` | 1131 |
| `onclick` | 1131 |
| `onclick` | 1131 |
| `allFieldRows` | 1135 |
| `openPreview` | 1136 |
| `onclick` | 1136 |
| `val` | 1151 |
| `onchange` | 1162 |
| `onclick` | 1166 |

## Elementos con ID para conservar y probar

| ID | Tag | Línea |
|---|---|---|
| `fiscalops-v20-ui` | style | 101 |
| `fiscalops-v21-style` | style | 111 |
| `fiscalops-v211-reader-legibility` | style | 214 |
| `s1` | section | 513 |
| `start` | button | 513 |
| `s2` | section | 514 |
| `rfc` | input | 514 |
| `drop` | div | 514 |
| `file` | input | 514 |
| `select` | button | 514 |
| `folder` | button | 514 |
| `changeFolder` | button | 514 |
| `refreshFolder` | button | 514 |
| `process` | button | 514 |
| `reprocessAll` | button | 514 |
| `forgetMemory` | button | 514 |
| `clear` | button | 514 |
| `folderPanel` | div | 514 |
| `memoryPanel` | div | 514 |
| `filelist` | div | 514 |
| `prog` | progress | 514 |
| `status` | div | 514 |
| `s3` | section | 515 |
| `sub` | p | 515 |
| `excel` | button | 515 |
| `excelf` | button | 515 |
| `txt` | button | 515 |
| `csv` | button | 515 |
| `exportPack` | button | 515 |
| `editcols` | button | 515 |
| `more` | button | 515 |
| `year` | select | 515 |
| `q` | input | 515 |
| `tipo` | select | 515 |
| `estatus` | select | 515 |
| `month` | select | 515 |
| `reportKind` | select | 515 |
| `profileSel` | select | 515 |
| `densityBtn` | button | 515 |
| `csvQuick` | button | 515 |
| `reportDescription` | div | 515 |
| `typeTabs` | div | 515 |
| `cards` | div | 515 |
| `assistantBox` | div | 515 |
| `ps` | select | 515 |
| `prev` | button | 515 |
| `page` | span | 515 |
| `next` | button | 515 |
| `thead` | thead | 515 |
| `tbody` | tbody | 515 |
| `foot` | p | 515 |
| `editcolsTop` | button | 515 |
| `totalsBox` | div | 515 |
| `cancel` | button | 515 |
| `sinmeta` | button | 515 |
| `modal` | div | 515 |
| `columnEditorTitle` | h2 | 515 |
| `closecols` | button | 515 |
| `colSearch` | input | 515 |
| `corecols` | button | 515 |
| `invoicecols` | button | 515 |
| `allcols` | button | 515 |
| `nocols` | button | 515 |
| `paycols` | button | 515 |
| `nomcols` | button | 515 |
| `auditcols` | button | 515 |
| `taxcols` | button | 515 |
| `columnSelectionCount` | div | 515 |
| `checks` | div | 515 |
| `applycols` | button | 515 |
| `previewModal` | div | 515 |
| `previewKicker` | div | 515 |
| `previewClose` | button | 515 |
| `previewBody` | div | 515 |
| `exportModal` | div | 516 |
| `exportTitle` | h2 | 521 |
| `exportClose` | button | 524 |
| `exportMainInfo` | div | 526 |
| `analysisChoices` | div | 527 |
| `exportSheetSummary` | div | 528 |
| `exportCancel` | button | 530 |
| `exportGenerate` | button | 531 |
| `fiscalops-v20-runtime` | script | 1171 |
