# Historial visual y respaldos SQLite — entrega

Implementados en Qt mediante **Sesiones y respaldos**, en la cabecera. El historial muestra fecha UTC, RFC, CFDI, estado e ID; permite buscar, paginar y abrir una sesión compatible con su vista guardada. Los reportes conservan el viewport y los22 tipos existentes. El respaldo y la restauración trabajan en el worker; ninguna ruta de esos flujos se entrega al WebChannel.

Crear respaldo usa la API de SQLite, valida una copia temporal y publica el archivo final. Restaurar abre el archivo de sólo lectura, verifica esquema/hashes/conteos y muestra un resumen que aún no modifica datos. Tras confirmar crea un respaldo preventivo, sustituye todo el contenido mediante una transacción y muestra la copia preventiva antes de volver al reporte. Cancelar, fallar o morir antes del COMMIT conserva la base anterior.

| Evidencia actual | Resultado |
|---|---|
| Contratos nuevos de historial/respaldo/restauración |20/20 PASS |
| Persistencia SQLite |20/20 PASS |
| Integración/reportes |28/28 PASS |
| Motor fiscal |59/59 PASS |
| Historial y restauración en dos procesos Qt reales |37/37 PASS |
| Ventana, visor y exportaciones Qt |34/34 PASS |
| Jobs Qt y cancelación/cierre |17/17 PASS |
| HTML sin Qt |Procesamiento/exportación bloqueados |
| Comparación nativa a tres tamaños |Máximo 0.671917% de píxeles distintos |
| Original, legacy, HTML/CSS/editor y baseline60 |Preservados |
| Fuentes oficiales fijadas |16 hashes verificados |

La prueba Qt crea dos sesiones sintéticas, busca y abre la primera, guarda un respaldo nativo, cancela un selector de archivo, rechaza un archivo inválido, revisa/descarta un candidato y confirma después una restauración. La copia preventiva conserva la segunda sesión activa; la base restaurada vuelve a la primera con su filtro HISTORY-1 y perfil fiscal. La pantalla de éxito muestra el path preventivo. Un segundo proceso Qt confirma persistencia tras reiniciar.

Después de restaurar se guardan CSV/TXT/XLSX reales de una fila: IVA16 y Total119. El XLSX mantiene ocho hojas y todas sus partes XML/CRC se verifican; las descargas llegan a DownloadCompleted. No se afirma validación visual en Microsoft Excel instalado. La prueba anterior Qt verifica las cinco pestañas del visor, foco del editor, tres tamaños y cálculos Decimal; no cambia el motor fiscal ni el manifiesto normativo.

Los contratos provocan una caída real con os._exit(24) durante la sustitución de tablas y comprueban rollback al abrir otra conexión. También verifican cancelación, fallo de publicación/INSERT, backup vacío, paths activos/auxiliares/enlaces duros, fuente cambiada después de revisar, candidato alterado, conflictos entre ventanas, tipos JSON dañados, esquema/versión/hash inválidos, búsqueda literal y paginación de56 sesiones sin omitir/duplicar IDs. El fallo de escritura se simula; no se llenó físicamente el disco.

Se inspeccionaron capturas reales del historial, revisión, confirmación y reporte restaurado. Frente al checkpoint SQLite anterior se observan el botón Qt añadido y pequeñas variaciones de rasterización en la captura inicial. No hay cambio de dimensiones del reporte, HTML/CSS/editor ni del baseline original. Los140 checks de navegador y las capturas anteriores permanecen como evidencia histórica, no se cuentan como ejecuciones nuevas de esta fase.

La base activa debe ser legible para producir el respaldo preventivo; no se sobrescribe una base activa corrupta ni se realiza reparación forense. Permanecen fuera cifrado, limpieza/retención automática de backups, programación de respaldos, edición compartida/sincronizada entre equipos, grants/caché incremental, Windows limpio/DPI125/150, validación integral de complementos y EXE final. Las comprobaciones de hashes no autentican un archivo frente a modificaciones deliberadas de datos y hashes.

[Contrato y límites](21_HISTORIAL_RESPALDOS_SQLITE.md) · [Reproducción](../scripts/history/README.md). Evidencia en `tests/history/evidence/verification.json`, contratos y `tests/history/qt/acceptance.json`; capturas y exportaciones usan únicamente datos sintéticos. La verificación vincula fuentes actuales con las ejecuciones. Commit/bundle nuevos locales, sin bases del usuario ni remotos.
