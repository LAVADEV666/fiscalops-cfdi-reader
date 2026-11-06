# Persistencia SQLite de documentos, resultados y sesiones

Hito histórico. El selector visual y los respaldos/restauración ya se implementan en la fase posterior: [contrato actual](21_HISTORIAL_RESPALDOS_SQLITE.md) y [entrega](22_HISTORIAL_RESPALDOS_REPORT.md).

La aplicación Qt guarda las cargas confirmadas en `FiscalOpsData/fiscalops.sqlite3`, junto al proyecto. Se crea al primer acceso del worker. El lanzador y el comando `.\.venv\Scripts\python.exe -m app.desktop.main` siguen siendo los mismos. No se añaden dependencias: se utiliza `sqlite3` de CPython3.11.

## Comportamiento visible

Al abrir Qt se recupera la última sesión activa: documentos, XML del visor, incidencias, resultados fiscales, RFC de procesamiento, tipo de reporte, perfil, columnas, anchos, columnas fijadas, orden, filtros y página. Los reportes y exportaciones se resuelven con las mismas identidades que antes de cerrar. No se ejecuta el parser/cálculos JavaScript ni se reinterpreta una cifra al leer SQLite.

La interfaz, sus22 reportes y cinco pestañas del visor se conservan. Se reutiliza el panel de memoria existente para indicar que la sesión está guardada. No se añade un gestor de historial a la interfaz. El protocolo permite listar y abrir sesiones anteriores; no implica permisos persistentes sobre carpetas.

- Procesar una carga nueva conserva la anterior hasta confirmar la transacción completa. Una cancelación, fallo de lectura o fallo SQL no publica una sesión parcial.
- **Limpiar** cierra la sesión activa y limpia la pantalla; conserva el historial local. El siguiente inicio permanece vacío.
- **Doble clic en Borrar memoria**, con una sesión activa, elimina las sesiones, documentos y resultados locales mediante una transacción. No borra los archivos originales seleccionados. Es borrado lógico; no se promete borrado seguro de sectores/copias.
- Los cambios de vista se guardan con180ms de debounce. Al cerrar se captura la vista final y se encola su guardado antes de cerrar SQLite y detener el worker. Si el renderizador no responde en1.5s, se conserva la última vista confirmada. Un fallo de guardado al cierre queda en `FiscalBridge.close_save_result`; los documentos ya confirmados permanecen guardados.
- Una carpeta se vuelve a seleccionar para actualizar/reprocesar. No se migra ni se confía en la caché IndexedDB del legado.

## Datos y precisión

| Tabla | Contenido |
|---|---|
| documents | SHA256, bytes originales BLOB y longitud; deduplicación por contenido, nunca por UUID |
| sessions | ID, fecha UTC, RFC, fingerprint del motor, cantidad de documentos, metadata local, incidencias y vista |
| inputs | Origen y orden de cada entrada XML/metadata aceptada para lectura, incluso entradas con XML rechazado; referencia al contenido original |
| fiscal_results | Resultado completo de inspección, validaciones y análisis; proyección de reportes; IDs y orden por sesión; hashes de ambos JSON |
| workspace | Sesión activa y revisión de concurrencia |

Los importes son cadenas decimales exactas en JSON TEXT y NULL permanece NULL. No se usa REAL ni SUM de SQLite para cálculos fiscales. Las sumatorias y análisis continúan en Python/Decimal. Se guardan originales XML y metadata, no el ZIP exterior ni bytes de entradas rechazadas por los límites del contenedor. Los duplicados conservan instancias y procedencia propias; únicamente comparten el BLOB cuando sus bytes coinciden.

Al recuperar se verifican longitud y SHA del XML y hashes de inspección/proyección, junto con identidades y conteos. Estos hashes detectan alteraciones accidentales; no son una firma ni autenticación contra alguien que controle la base. No se usa pickle ni se ejecuta contenido guardado. Una sesión cuyo fingerprint fiscal difiere del motor instalado se rechaza con `SESSION_ENGINE_MISMATCH`, sin eliminarla; se deben seleccionar y procesar de nuevo sus originales. El fingerprint abarca el código fiscal/adaptador y el manifiesto normativo fijado.

## Transacciones, versiones e hilos

La conexión se abre de forma diferida en el worker y conserva `check_same_thread=True`. Ninguna conexión, SQL o ruta de la base se expone por WebChannel. El shutdown cancela trabajos, encola la vista final, cierra la conexión en el worker y termina QThread. No usa terminate ni trabajo SQLite en el GUI.

Esquema inicial `user_version=1`, `application_id=0x464F5053`. Inicialización0→1 y publicación de sesiones usan `BEGIN IMMEDIATE`/COMMIT/ROLLBACK; se activan claves foráneas, `synchronous=FULL` y journal DELETE. No hay WAL pendiente que deba copiarse con el archivo. Bases ajenas, versiones futuras e integridad fallida se rechazan sin reemplazar el archivo. Una versión futura necesitará su migración explícita; no se simulan migraciones inexistentes.

Se comprueban `quick_check` y claves foráneas al abrir. El timeout de bloqueo es250ms y produce `DATABASE_BUSY` para reintentar. Una revisión compara la sesión activa esperada al confirmar, limpiar o guardar vista: otra ventana no puede sobrescribirla silenciosamente (`SESSION_CONFLICT_REOPEN`). Se usan consultas parametrizadas.

Estas decisiones se apoyan en la documentación primaria de [sqlite3 de Python3.11](https://docs.python.org/3.11/library/sqlite3.html), [transacciones SQLite](https://sqlite.org/lang_transaction.html), [claves foráneas](https://sqlite.org/foreignkeys.html) y [PRAGMA/user_version](https://sqlite.org/pragma.html#pragma_user_version).

## Protocolo de sesión

Diagnóstico `fiscalops.desktop/3`; los slots públicos siguen siendo solamente `openJob`, `request` y `cancel`. Operaciones nuevas del worker:

| Operación | Contrato |
|---|---|
| session.resume | Carga la sesión activa compatible o devuelve dataset_id:null |
| dataset.page | Página de filas/incidencias y formatos Decimal del snapshot recuperado; mismos límites de transporte |
| session.save | dataset_id y view JSON≤65536bytes; no puede modificar resultados fiscales |
| session.list | Hasta50 sesiones por página con offset, ordenadas por fecha descendente |
| session.open | Abre un ID histórico existente/compatible y lo activa; no acepta rutas |
| session.purge | Elimina historial y contenido de la base local y desactiva la sesión |

`import.commit` ahora confirma SQLite antes de publicar el snapshot en memoria. `dataset.clear` desactiva de forma persistente antes de limpiar la memoria. `report.aggregate` y `report.export` mantienen el contrato anterior y vuelven a resolver las identidades del snapshot del worker. El historial persiste completo; sólo los snapshots en uso permanecen en memoria. No existe reutilización automática de resultados para una importación nueva: se vuelve a inspeccionar con el motor actual.

## Límites y pendientes

Se mantienen los límites de carga, ZIP, paginación y exportación del [contrato de workers](18_CONTRATO_QT_WORKERS.md). El historial puede crecer en disco y no se elimina automáticamente. La ruta no la elige JavaScript y `FiscalOpsData/` está excluida de Git; no se incluye información real en evidencia o bundles.

La base es local, sin cifrado de aplicación. Copias de seguridad consistentes/restauración desde UI, traslado de la base, selector visual de historial, caché incremental, permisos persistentes de carpetas, varios equipos sobre una base compartida y sincronización de archivos mientras se escribe quedan fuera de esta fase. La carpeta del proyecto de este equipo está dentro de OneDrive; eso no convierte SQLite en un servicio de sincronización ni acredita edición concurrente entre equipos. No se amplía la cobertura normativa de complementos/SAT ni se genera el EXE final.

Pruebas y reproducción en [scripts/persistence/README.md](../scripts/persistence/README.md). Evidencia de aceptación en [20_PERSISTENCIA_SQLITE_REPORT.md](20_PERSISTENCIA_SQLITE_REPORT.md).
