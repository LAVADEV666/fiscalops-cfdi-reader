# Plan de migración incremental y arquitectura propuesta

**Decisión de FASE 0:** conservar el HTML íntegro como referencia y proponer Python + PySide6/QtWebEngine + QWebChannel + SQLite + Decimal + lxml + openpyxl. Es una propuesta sustentada en la necesidad de reutilizar el renderizado web y aislar la lógica fiscal. No se han instalado, medido ni empaquetado esas dependencias; no se les asigna una versión inventada. La selección final, fijación y licencias corresponden a FASE 2.

## Justificación y alternativas

| Alternativa | Ajuste al proyecto | Riesgo que debe medirse |
|---|---|---|
| PySide6 + QtWebEngine | Reutiliza HTML/CSS, puente nativo, archivos locales, workers y ecosistema Decimal/XML/XLSX en Python; preferida | Tamaño Qt, memoria, APIs browser originales no disponibles, compatibilidad gráfica, distribución y licencias. |
| Electron + backend Python | También mantiene renderizado, pero añade Node y coordinación con segundo runtime | Tamaño, actualizaciones, seguridad del puente, dependencias duplicadas; sin evidencia de ventaja aquí. |
| WebView2 + backend Python | Podría reducir binario si runtime ya instalado | Dependencia WebView2 contradice portabilidad sin instalación si no se incluye runtime; validar modo fixed-runtime y licencias. |
| Widgets nativos o reescritura UI | Motor local viable | Alto coste para reproducir cascada, tablas y modales 1:1; no ofrece beneficio demostrado para esta referencia. |

No se promete mejor velocidad por cambiar de lenguaje. Medir procesamiento, memoria, tamaño y respuesta antes de cerrar la decisión. Ningún framework de rediseño es necesario para conservar V21.1.

## Separación y contratos

`app/ui` conserva DOM y CSS; presenta datos y genera intenciones de usuario. `app/bridge` expone un conjunto pequeño de comandos por QWebChannel con validación de argumentos. `app/services` coordina importación, consultas y exportación. `app/workers` ejecuta tareas con IDs y cancelación. `fiscal_engine` no conoce Qt ni DOM. `storage` implementa repositorios, migraciones y transacciones SQLite. `exports` usa el mismo criterio de selección que la consulta visible.

Flujo: seleccionar origen → registrar lote → identificar bytes y hash → deduplicar archivo → interpretar XML → guardar árbol/modelos/hallazgos → consultar reporte → paginar UI/exportar. El contenido importado nunca se carga como página ejecutable. Un complemento no interpretado permanece con sus bytes/árbol y estado explícito.

Mensajes de puente propuestos (todavía sin implementar):

| Operación | Entrada | Respuesta/eventos |
|---|---|---|
| `import_sources` | Identificadores de rutas elegidas y opciones/límites | jobId; discovered/accepted/rejected/duplicate/processed/incidents; progreso y finalización. |
| `cancel_job` | jobId | Cancelación solicitada/confirmada; unidades confirmadas e incompletas. |
| `query_report` | reportId, filtro tipado, columnas, orden, página/tamaño | filas, totalFilas, totales por moneda, selectionId/versionSnapshot. |
| `read_document` | documentId | originales, modelos por nivel, soporte por complemento y hallazgos. |
| `export_report` | selectionId, columnas, análisis opcionales, destino elegido | jobId; progreso, cancelación y manifiesto de filas/hojas/totales. |
| `scan_origin` / `rebuild_index` | originId/versiones | diferencias e historial; nunca borrado por desconexión. |
| `save_profile` | empresa/tipo/reporte/perfil/versión y borrador confirmado | perfil persistido o error explícito. |

Importes viajan como cadenas decimales + moneda, no float JSON. UUID/RFC/CP/cuentas se envían como texto. Fechas conservan valor original y representación ISO, con zona sólo cuando exista evidencia; no inventar offset de emisión. No se evalúa código recibido por el puente. Rechazar métodos/rutas arbitrarias fuera de orígenes y destinos seleccionados.

## Entidades y trazabilidad

| Dominio | Tablas/entidades propuestas y claves |
|---|---|
| Origen/importación | origins, source_files, source_versions(hash,size,bytes/ubicación), import_batches, import_items, incidents. Identificar raíz y ruta relativa; documento no depende de ruta. |
| Documento | cfdi_documents(documentId,uuid,namespace,version,hash,parserVersion,ruleVersion), parties, document_parties, global_information, document_attributes. UUID no es único absoluto: conservar XML distintos como conflicto. |
| Conceptos/impuestos | concepts(documentId,index), concept_taxes(conceptId,index), global_taxes(documentId,index), local_taxes(documentId,index). Nunca mismo impuesto en dos acumuladores por representación duplicada. |
| Relaciones | relation_groups(documentId,index,type), relations(groupId,index,relatedUuid). Resolver vínculos locales sin borrar UUID no localizado. |
| Pagos | payment_totals(documentId), payments(documentId,index), payment_documents(paymentId,index), dr_taxes(paymentDocumentId,index), payment_taxes(paymentId,index). Moneda de cada nivel y equivalencia explícitas. |
| Nómina | payroll(documentId,version,revisionContext), employer, employee, perceptions, deductions, other_payments, disabilities, overtime y subestructuras específicas. Separar identificadores personales del log operativo. |
| Carta Porte | carta_porte(documentId,version), locations, goods, transport_modes, transport_figures, domiciles y tablas de enlace. Lectores por namespace/versión. |
| Complementos | complements(documentId,index,namespace,version,supportState,originalNode). No perder desconocidos. |
| Metadata | metadata_sources(fileHash,sourceDate,importedAt), metadata_rows(sourceId,uuid,rawHeaders/rawValues), status_observations y conflictos. No reemplazar historia. |
| Validación | validation_runs(documentId,engineVersion,ruleSetVersion), findings(ruleId,severity,category,path,observed,expected,source,explanation). Validación oficial externa separada y sólo si se implementa explícitamente. |
| Reglas/catálogos | rule_sets, catalog_versions(sourceURL,downloadedAt,hash,validFrom,validTo), catalog_entries y vigencias por clave. |

Cada valor monetario conserva original, normalizado Decimal serializado, precisión, moneda, nivel y naturaleza. Preferir texto decimal exacto en SQLite, o enteros escalados únicamente cuando la escala del campo esté demostrada. No usar REAL para importes; no totalizar texto mediante cast float SQL. Cálculos y redondeos pertenecen a reglas versionadas del motor. Índices propuestos sobre UUID normalizado, RFC, fecha ISO, tipo, moneda, sourceHash y las claves foráneas de detalle; verificar con EXPLAIN y benchmarks.

## Caché y recuperación

Identidad física=SHA256 de bytes; identidad fiscal=UUID+contenido; versión de interpretación=parser+reglas+catálogo/contexto. Distinguir idéntico, modificado, conflicto UUID, ausente, inaccesible e incompleto. Una transacción confirma cada unidad documental con sus hijos e incidentes. El lote conserva checkpoints. Una carpeta inaccesible no implica archivos eliminados ni documentos cancelados. Reprocesar cambia interpretación con historial y conserva originales.

La UI no accede directamente a SQL ni modifica importes. Consultas parametrizadas y migraciones con versión. Ubicación portable `FiscalOpsData` junto al ejecutable cuando sea escribible; si falla, diagnóstico y elección explícita, sin cambiar silenciosamente a AppData. Definir exportación/backup antes de migrar datos de IndexedDB; no leer perfiles privados del navegador de forma implícita.

## Hitos y puertas de aceptación

| Fase | Trabajo acotado | Evidencia necesaria antes de avanzar |
|---|---|---|
| 0 actual | Preservación, auditoría, inventarios, riesgos y propuesta | Seis documentos, hashes, pruebas diagnósticas; pendientes visuales explícitos. Punto de control actual. |
| 1 | Congelar referencia visual y navegación del original | 1366×768,1600×900,1920×1080, DPI registrado; escenas y fixture identificados; sin rediseño. |
| 2 | Shell Qt/puente y módulos; separar recursos manteniendo vista | Mismos screenshots, navegación, offline, CSP/puente restringido, worker y datos de prueba. Dependencias fijadas tras comprobar instalación/licencias. |
| 3 | Motor XML seguro y matriz normativa SAT | Fuentes oficiales descargadas con URL/fecha/hash, versiones y vigencias; fixtures sintéticos revisados y distinción XML/XSD/reglas. |
| 4 | Decimal/impuestos y reglas aritméticas | F01–F06 cerrados con expectativas correctas y evidencia normativa por campo. |
| 5 | Complementos versionados | REP múltiple, nómina/revisión aplicable y CP con cobertura exacta declarada; desconocidos preservados. |
| 6 | Importación/caché/metadata SQLite | Corrupción/cancelación/reinicio, UUID+hash, conflictos y fuentes; no pérdida silenciosa. |
| 7 | Reportes/filtros/exportación | SelectionId común UI/export, tipos Excel, límites, fórmula, hojas vacías y apertura real. |
| 8 | Rendimiento/seguridad/calidad | Datos 100/1k/10k/50k, perfilado, memoria, latencia, seguridad XML/ZIP y logs privados. |
| 9 | Build Windows onedir+ZIP | Script PowerShell, lock/hash/licencias, EXE/ZIP reales con SHA, prueba máquina limpia y offline. |
| 10 | Revisión integral | AC01–18 con evidencia, cero P0; ningún DONE global si falta aceptación. |

Cada fase termina con reporte y revisión antes de avanzar. La autorización de esta primera ejecución no se interpreta como permiso de sustituir el motor en fase 0.

## Propuesta concreta para iniciar FASE 1

Antes de escribir código de aplicación: confirmar hashes del original y activos; leer 00/02/04; elegir una vía de navegador/escritorio local permitida (la actual política bloquea file://, no intentar rodearla con otro protocolo); registrar navegador/versión, Windows, resolución, zoom y DPI; definir matriz de escenas y criterios de diferencia; preparar fixture anónimo representativo que no afirme validez SAT sin comprobarse. Crear `tests/visual/baseline/` sólo con capturas verdaderas, junto con manifiesto de escena/resolución/DPI/fixture/hash. No llenar carpeta con placeholders.

Capturar splash antes de1600ms, carga vacía, carga seleccionada, progreso y finalización, reportes vacíos/con datos, dos monedas, cancelado por metadata, errores, editor con búsqueda/perfiles, constructor con selecciones y visor en sus cinco pestañas. Probar un clic por tipo, filtros combinados, orden, paginación, teclado/foco, cierre y scroll. Reproducir U01–U03 con observación real antes de corregirlos.

La fase 1 puede registrar defectos para corrección posterior y conservar una baseline defectuosa etiquetada; no «mejorar» diseño durante la captura. Sólo tras revisar la referencia se permite separar recursos o conectar el shell en fase 2. Preservar diferencias y decisiones en un changelog visual. La decisión de tecnología queda pendiente de la prueba QtWebEngine con esas mismas escenas.
