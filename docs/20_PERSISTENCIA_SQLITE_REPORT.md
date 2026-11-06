# Persistencia SQLite — entrega y evidencia

Hito histórico. La fase siguiente implementa selector de historial y respaldo/restauración desde Qt: [entrega actual](22_HISTORIAL_RESPALDOS_REPORT.md).

Implementada en Qt: originales y metadata, resultados fiscales, proyecciones de los22 reportes y sesiones se guardan en `FiscalOpsData/fiscalops.sqlite3`. La última sesión activa se recupera sin releer los archivos ni volver al parser JavaScript. Los filtros, perfil, columnas y XML del visor sobreviven al cierre.

La conexión es exclusiva del worker; se abre y se cierra en ese hilo. Una transacción confirma toda la carga y la sesión activa antes de publicar el reporte. Cancelación, bloqueo, escritura fallida o caída a mitad de transacción conservan la sesión confirmada anterior. Los importes usan cadenas decimales y nulos, sin REAL/float ni cálculos SQL.

| Verificación actual | Resultado |
|---|---|
| Contratos SQLite |20/20 PASS |
| Contratos de integración/reportes |28/28 PASS |
| Motor fiscal |59/59 PASS |
| Ventana Qt y exportaciones |34/34 PASS |
| Jobs Qt, cancelación/reintento/cierre |17/17 PASS |
| Recuperación en tres procesos Qt Windows |34/34 PASS |
| HTML distribuido sin Qt |Bloquea procesamiento/exportación; sin fallback |
| Comparación de reportes a tres tamaños |Máximo 0.008484% de píxeles distintos |
| HTML/CSS/editor y baseline60 |Preservados |
| Fuentes oficiales fijadas |16 hashes verificados |

La prueba de recuperación crea una base temporal real, carga tres CFDI sintéticos, guarda un filtro/columnas, cierra inmediatamente después de cambiar el filtro y abre otro proceso Qt. El segundo recupera las mismas identidades, perfil fiscal, columnas y búsqueda, muestra las cinco pestañas del visor y exporta XLSX, CSV y TXT de una sola fila: IVA16 y Total119. XLSX contiene8 hojas y todas sus partes XML/CRC se verifican. Se comprueba DownloadCompleted; no se presenta la existencia de un archivo parcial como guardado exitoso.

El segundo proceso limpia la sesión activa; el tercero permanece vacío. SQLite conserva el historial anterior y sus tres resultados, con integridad correcta. Los tests de contrato prueban además apertura de historial y purga completa, originales UTF16, metadata/incidencias, las22 familias de reporte, cero/NULL, deduplicación de bytes conservando instancias, identidades/orden de exportación, versiones futuras, hashes alterados y conflicto entre ventanas.

La caída se provoca con `os._exit(23)` en un subproceso dentro de la transacción, antes de activar la nueva sesión. La recuperación vuelve al commit anterior. El fallo de escritura se inyecta con un trigger temporal de prueba: no se llenó físicamente el disco. Se mantiene la protección de hilo de sqlite3 y se prueba su rechazo desde otro hilo.

La comparación visual usa capturas reales de los reportes Qt actuales contra el commit anterior a1366×768,1600×900 y1920×1080. Se inspeccionaron el reporte recuperado y la diferencia: las variaciones pequeñas provienen del logotipo animado, sin cambio del diseño. No se modificó el baseline. Las140 comprobaciones de navegador y las36 capturas del hito anterior permanecen como evidencia histórica; no se cuentan como una nueva ejecución SQLite.

Limpiar desactiva la sesión sin destruir historial. Doble clic en Borrar memoria elimina el contenido persistido, sin tocar originales seleccionados. El guardado de vista tiene debounce y captura final al cerrar; si el renderizador no responde o falla ese último guardado, permanece la última vista confirmada. No se afirma cifrado, borrado seguro, certificación SAT o validación visual mediante Microsoft Excel instalado.

Persisten los límites de carga del hito anterior. Historial sin borrado automático, selector visual de historial, backup/restauración desde UI, caché incremental, grants permanentes, base compartida entre equipos/sincronización, Windows limpio/DPI125/150 y EXE siguen fuera de esta fase. La cobertura normativa del motor permanece igual.

Evidencia: `tests/persistence/evidence/verification.json`, `contracts.json`, `fiscal-tests.json`, `tests/persistence/qt/recovery.json`, descargas reales y comparación visual. El verificador vincula los resultados a hashes actuales de aplicación. [Contrato y límites](19_PERSISTENCIA_SQLITE.md) · [Reproducción](../scripts/persistence/README.md).

Abrir desde la raíz con `.\.venv\Scripts\python.exe -m app.desktop.main`. No cambia el lanzador ni se requiere instalar una dependencia adicional. Se guarda commit/bundle local nuevo sin remotos ni datos del usuario.
