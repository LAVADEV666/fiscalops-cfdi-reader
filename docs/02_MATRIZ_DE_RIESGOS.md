# Matriz de riesgos y evidencia

Severidad: **P0** impide confiar en importes, integridad o seguridad fundamental; **P1** bloquea una capacidad crítica o puede perder datos; **P2** afecta operación/claridad con alternativa; **P3** mantenimiento o detalle. Clasificación EC/RC/HP/NC en 00. EC en lector significa reproducción con adaptador XML y UI simulada, no comprobación en navegador real. Ningún hallazgo se ha corregido en el producto durante FASE 0.

| ID | Sev. | Clase | Hallazgo y ubicación original | Evidencia / reproducción pendiente | Acción y aceptación futura |
|---|---|---|---|---|---|
| F01 | P0 | EC | TotalImpuestosTrasladados→IVA L1003 | N02: IVA24 vs nodo IVA16 | Separar total federal/IVA/IEPS; reconciliar por nivel y código. |
| F02 | P0 | EC | Retención/Retencion incompatibles L984,L624 | N03: ISR0 vs retenido10 | Enum de naturaleza; retenciones reconciliadas por código. |
| F03 | P0 | EC | Locales contados dos veces L1006,L1015 | N04: diferencia−3 con total119 | Una ruta de suma para cada nivel; total calculado119. |
| F04 | P0 | EC | Exento también en tasa0 L624 | N06: ambas bases100 | Separar factor/tasa, exento sólo en su tratamiento. |
| F05 | P1 | EC | Fallback suma concepto+global L1004 | N07 con XML incompleto:32 vs16 | Elegir fuente y reportar total ausente, nunca inventar sin trazabilidad. |
| F06 | P0 | EC | Number y nulidad→0 L539,L974 | N08 | Decimal, NULL explícito y tolerancias sustentadas por regla/campo. |
| X01 | P1 | EC | Namespace no verificado L967–988 | N05 acepta urn:not-sat | Namespaces/versiones explícitos; desconocido rechazado o conservado no interpretado. |
| X02 | P1 | EC/RC | normalize elimina DTD antes de chequeo L683,L1033 | N25 prueba eliminación; explotación no demostrada | Controlar bytes originales antes de transformación; prueba entidades/DTD. |
| X03 | P1 | RC | Decodificación forzada UTF8 L1030,L1041 | Fixture ISO-8859-1 pendiente | Detectar BOM/declaración, preservar bytes; comparar texto exacto. |
| X04 | P1 | RC | Límites XML en caracteres y tras lectura L973 | Casos máximos/nodos profundos pendientes | Límite por bytes/nodos/tiempo desde stream; rechazo trazable. |
| X05 | P1 | NC | Sin XSD/reglas/versiones históricas L986–1019 | No existen esquemas/pruebas oficiales locales | Paquete SAT verificado y modos de validación separados. |
| X06 | P1 | RC | Extracción parcial CFDI/Pagos/Nómina/CP L991–1011 | Matriz de cobertura en 00 | Campos por XSD y soporte declarado por versión; no certificar lectura parcial. |
| Z01 | P1 | EC | ZIP no verifica CRC L1041 | N23 acepta !x/> con CRC antiguo | ZIP probado, CRC/estructura y registro de entrada dañada. |
| Z02 | P1 | EC/RC | Método no soportado se omite, central truncada hace break | N24; truncado pendiente | Registro de rechazo por entrada y conciliación de conteos. |
| Z03 | P0 | RC | Descompresión limitada por usize declarada, no real | ZIP bomb controlada pendiente | Stream acotado, ratio, total real, cancelación, pruebas aisladas. No se ejecutó bomba. |
| C01 | P0 | EC/RC | Identidad por firma, sin hash L573 | N09 firmas iguales; cambio real pendiente | SHA256, original único, versiones parser/reglas. |
| C02 | P1 | RC | Caché sólo por RFC, carpetas colisionan L570,L583 | Dos carpetas mismo RFC/ruta pendientes | Identidad de raíz/origen además de documento. |
| C03 | P1 | RC | Fallos cached sin incidentes L1035 | Segunda importación con IDB pendiente | Persistir status/errores y reintentar incompletos. |
| C04 | P1 | RC | seen no incluye UUID cacheados L1022–1023 | Nuevo vs cacheado pendiente | Índice de UUID+hash, distinguir conflicto de duplicado idéntico. |
| C05 | P1 | RC | kvPut no espera transacción L578 | Cuota/abort/cierre pendiente | Confirmación tx completa, rollback y diagnóstico recuperable. |
| C06 | P2 | RC | Eliminados sólo contados, sin historial L590–591 | Borrar/restaurar/reconectar pendiente | Estado ausente por origen; no borrar documento fiscal ni historia. |
| M01 | P1 | EC | UUID metadata inválido aceptado L616 | N10 | Validar formato y guardar rechazo/procedencia. |
| M02 | P1 | EC | Conflicto metadata último gana L667 | N21 | Conservar fuentes, fechas y conflictos sin presumir vigencia actual. |
| M03 | P1 | RC | Estado SAT sin antigüedad de fuente en celda L1044 | Revisión de UX pendiente | Mostrar «informado por metadata» y fecha; oficial en línea separado. |
| U01 | P1 | RC | Editor filtra checks al guardar L1129 | Búsqueda UUID con Fecha seleccionada pendiente DOM real | Guardar modelo completo, búsqueda sólo presentación. |
| U02 | P1 | HP | Dos listeners alternan tipo L685,L1085 | Un clic real puede activar/desactivar; no ejecutado | Un despacho por acción; comprobar tipo seleccionado y exportación. |
| U03 | P2 | RC/HP | Búsqueda y preview con listeners dobles L684,L1085,L718,L1101 | Conteo de renders/preview pendiente | Consolidar handlers manteniendo efectos documentados. |
| U04 | P1 | EC/RC | findings no es reporte, asistente se vacía/oculta | N19; L1067,CSS03; visibilidad NC | Acceso a todos los hallazgos con referencia y evidencia. |
| U05 | P2 | EC | Orden léxico fechas dd/mm L1061 | N13 | Fecha interna ISO/datetime; orden cronológico correcto. |
| U06 | P2 | RC | Cerrar editor no revierte; aplicar borra widths/pinned | L1128–1129 | Borrador aislado, aplicar/cancelar; conservar preferencias compatibles. |
| U07 | P2 | EC | Reportes no acotados por tipo L1056 | N20 | Matriz de compatibilidad explícita; probar cambio de tipo. |
| U08 | P2 | RC | Árbol truncado y sin texto, visor parcial | L705,L1136 | Rótulos precisos, árbol completo lazy y sin ejecución HTML. |
| E01 | P1 | EC | XLSX recorta filas silenciosamente L1142 | N16 usa objeto sintético, no lote millón | Partir hojas o rechazar explícito; reconciliar filas y totales. |
| E02 | P1 | EC | XML XLSX inválido con controles L1138,L1141 | N15 + invalid-control-cell.xml | Política de control XML y biblioteca; archivo abrible sin reparación. |
| E03 | P2 | EC | Fechas exportadas como texto L1141 | N14 | Tipo fecha/hora y formato; RFC/UUID/texto de ceros intactos. |
| E04 | P1 | EC | Cero numérico desaparece TXT L1082 | N18 | Distinguir cero de vacío; roundtrip de filas. |
| E05 | P1 | RC | Hojas analíticas usan summary, principal reporte derivado | L1165,L1151–1159 | Misma selección o elección explícita con descripción del universo. |
| E06 | P2 | RC | Hojas vacías omitidas pese a contarlas | L1161,L1165 | Contador real y política de hoja vacía explícita. |
| E07 | P1 | RC | XLSX/ZIP todo en memoria y sin cancelación | L1142,L1146,L1165 | Worker, progreso/cancelación, escritura incremental y cleanup. |
| E08 | P3 | RC | Rutas ocultas generan XLS HTML y filtros obsoletos | L1079,L684 | Documentar sustitución; un exportador probado por formato. |
| T01 | P1 | RC | Catálogos no validan vigencia; TasaOCuota array ignorado | L961–966,L1013 | Fuente/hash/vigencia por clave; cobertura histórica. |
| T02 | P1 | RC | Periodicidad global usada para nómina | L963 y CAT Periodicidad | Comprobar catálogos oficiales distintos antes de interpretar claves. |
| P01 | P1 | RC | UI/hilo de cálculo compartido, sin cancelación/lote exclusivo | L1021,L1165 | Workers y máquina de estados; prueba UI responsiva y cancelación. |
| P02 | P2 | NC | Rendimiento masivo sin medición | No datasets/benchmarks existentes | 100/1k/10k/50k, memoria y latencia; no asumir mejora. |
| S01 | P2 | RC | Blur no oculta tooltip ni cifra caché | L1060,L1063,L576 | Política privacidad y logs; controles explícitos, pruebas de exposición. |
| V01 | P1 | NC | Navegación/fidelidad/DPI sin evidencia real | BLOCKED_VISUAL_BASELINE | Capturas permitidas y comparación a 3 resoluciones/DPI antes de refactor. |
| V02 | P2 | RC | Dos escritores de escala y CSS superpuesto | L1120,L1173 y 5 CSS | Medir cascada/render antes de consolidar. |

## Priorización y seguimiento

Los P0 son abiertos, no corregidos. La aplicación no puede certificarse hasta cerrar los P0 con pruebas de expectativas correctas, revisar namespaces/importación y completar aceptación. Los EC se convierten en casos de regresión del motor nuevo; los RC/HP requieren reproducciones independientes antes de alterar producción. No hay evidencia de explotación real ni de pérdida de documentos de clientes.

Conservación visual es requisito transversal: corregir un cálculo no autoriza rediseño; retener una apariencia tampoco obliga a conservar un importe erróneo. Documentar sustituciones de funciones ocultas/obsoletas, sin eliminaciones silenciosas.
