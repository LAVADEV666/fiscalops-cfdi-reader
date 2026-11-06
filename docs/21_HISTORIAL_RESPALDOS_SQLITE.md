# Historial visual y respaldos/restauración SQLite

El botón **Sesiones y respaldos**, en la esquina superior derecha de Qt, abre un gestor nativo. La superficie del reporte conserva su tamaño: no se cambia HTML/CSS, editor, visor, cálculos ni exportaciones. El botón es la adición visible de esta fase.

## Historial

La tabla muestra fecha UTC, RFC, cantidad de CFDI, estado activa/guardada/incompatible e identificador. Buscar admite RFC, fecha o ID; Anteriores/Siguientes paginan de50 en50. Abrir valida la sesión, activa su ID en SQLite y recarga el reporte con su vista guardada. Sesiones de otro fingerprint fiscal se muestran pero no se pueden abrir. No se recalculan ni se convierten importes al abrirlas.

Entrar al gestor captura y guarda la vista actual. Se impiden importaciones, cálculos/exportaciones nuevos desde el puente web durante el mantenimiento; el worker serializa los mensajes pendientes. Si hay una operación activa, primero hay que finalizarla o cancelarla. Cerrar el gestor sin cambiar datos regresa al mismo reporte. Abrir/restaurar recarga la sesión desde SQLite, evitando reutilizar filas antiguas en memoria.

## Crear un respaldo

**Crear respaldo SQLite…** abre QFileDialog para elegir el destino. Cancelar el selector no crea archivos. Qt confirma las sobrescrituras normales de un archivo existente. El path queda en Python: no se acepta por WebChannel.

El worker utiliza `sqlite3.Connection.backup`, en páginas, sobre un temporal exclusivo junto al destino. Verifica esquema, `integrity_check`, claves foráneas, originales, resultados, hashes y conteos; cierra SQLite, fuerza el flush del archivo y publica con reemplazo atómico. Un fallo o cancelación anterior a la publicación conserva el respaldo previo y la base activa. Se muestra ubicación, sesiones/CFDI y SHA256 del respaldo final.

No se admite guardar sobre la base activa, sus auxiliares journal/WAL/SHM, un enlace duro a ella o un destino que sea enlace simbólico. No se copian por separado archivos de una base abierta. El resultado es un SQLite autónomo con historial, originales, metadata, resultados y vistas. No contiene carpetas con permisos persistentes ni archivos originales ajenos al contenido previamente importado.

## Restaurar con revisión

1. **Seleccionar respaldo para restaurar…** abre el selector nativo. Se admite un archivo existente de hasta2GiB.
2. El worker lo abre de sólo lectura, verifica el esquema exacto de FiscalOps v1 y su contenido, y crea una copia temporal consistente. La sesión activa debe ser compatible con el motor instalado. Las sesiones históricas incompatibles pueden conservarse como archivo, sin habilitar su apertura.
3. Se muestran nombre, sesiones/CFDI/originales, SHA256 y el alcance: sustituir el historial completo. La selección todavía no modifica la base. **Descartar selección** o cerrar elimina el candidato temporal.
4. **Confirmar restauración** crea primero un respaldo preventivo verificado en `FiscalOpsData/backups/before_restore_<UTC>_<id>.sqlite3`. Si falla esa copia, no cambia datos activos.
5. Una transacción `BEGIN IMMEDIATE` sustituye documentos, sesiones, procedencia y resultados en la base existente. Las claves foráneas siguen activas. Se publica la sesión activa y una revisión nueva al confirmar la transacción. No se reemplaza por fuera de SQLite un archivo usado por otras conexiones.
6. La pantalla de resultado muestra la ubicación de la copia preventiva. **Ver reporte restaurado** recarga Qt desde la sesión restaurada, incluyendo filtros/columnas. Si el respaldo no tiene sesión activa, se abre la pantalla vacía y el historial sigue disponible.

La restauración utiliza el candidato revisado, aunque el archivo seleccionado cambie después. Si cambia el candidato temporal, su SHA no coincide y se rechaza. Los cambios en otra ventana, incluida la vista, invalidan la revisión esperada. No se sobrescriben silenciosamente: se solicita reabrir la aplicación. Una interrupción o fallo antes de COMMIT revierte los cambios; después de COMMIT se informa el éxito y se recarga el reporte, aunque el usuario haya solicitado cerrar el diálogo al mismo tiempo.

**Cancelar operación** utiliza un Event comprobado en copias/verificación y un progress handler de SQLite para la transacción. Un cierre del gestor espera su final antes de reactivar el reporte. No se usa QThread.terminate. La copia preventiva ya publicada se conserva también si la restauración posterior falla; el error muestra su ubicación. Un proceso que muera puede dejar un candidato temporal huérfano, sin convertirlo en base activa.

## Integridad y frontera Qt

La validación rechaza versiones futuras, bases ajenas, tablas/índices fuera del esquema admitido, triggers/vistas, claves foráneas rotas, hashes/longitudes incorrectos y conteos inconsistentes. También comprueba los JSON y las identidades de las proyecciones. No ejecuta SQL proporcionado por el archivo, XML, pickle ni reglas fiscales del respaldo. Los importes permanecen en JSON como cadenas decimales exactas y NULL; no se convierten a REAL.

Los hashes detectan alteraciones accidentales; no autentican un respaldo frente a quien pueda cambiar tanto datos como hashes. No hay cifrado de aplicación ni se afirma certificación SAT o recálculo normativo al restaurar. La comprobación de estructura y contenido no constituye una auditoría exhaustiva contra todo archivo hostil.

Protocolo diagnóstico `fiscalops.desktop/4`. Los slots WebChannel propios continúan siendo sólo openJob/request/cancel. Las operaciones native.enter/history/open/backup/restore.prepare/restore.commit/restore.discard son privadas de Python, fuera de la allowlist web. Las rutas, resultados y progreso de estas operaciones se entregan únicamente al diálogo Qt. Las conexiones SQLite, verificaciones, temporales y transacciones pertenecen al worker fiscal; el GUI sólo administra controles y selectores.

Las revisiones también aumentan al guardar una vista, para detectar cambios entre revisión del respaldo y confirmación. El esquema SQLite sigue siendo v1; no hay cambio de tablas ni migración destructiva. El motor fiscal/adaptador y el manifiesto normativo no cambian, por lo que las sesiones del hito anterior conservan su compatibilidad.

Referencias primarias: [API de respaldos SQLite](https://sqlite.org/backup.html), [sqlite3 de Python3.11](https://docs.python.org/3.11/library/sqlite3.html), [ATTACH](https://sqlite.org/lang_attach.html), [transacciones](https://sqlite.org/lang_transaction.html).

## Límites

Los límites de carga/reportes/exportaciones de las fases anteriores siguen vigentes. Respaldos y copias preventivas pueden crecer y no se eliminan automáticamente. Las bases `.sqlite3`/`.db` y auxiliares están excluidas de Git, además de FiscalOpsData. No hay envío de información ni respaldos programados.

La base activa debe ser legible y pasar las verificaciones para crear el respaldo preventivo; esta fase no sobrescribe una base activa corrupta ni realiza reparación forense. Restaurar sobre una instalación nueva/base vacía sí está admitido. No se garantiza edición sobre una base compartida entre equipos, sincronización durante escritura, consistencia de copias externas del filesystem o recuperación de fallos físicos del almacenamiento. SQLite opera sobre el almacenamiento local; OneDrive no se trata como servicio de concurrencia.

Persisten pendientes cifrado/gestión de claves, caché incremental, grants de carpeta, pruebas de Windows limpio/DPI125/150, validación normativa integral de complementos y EXE final.

[Entrega y evidencia](22_HISTORIAL_RESPALDOS_REPORT.md) · [Reproducción](../scripts/history/README.md).
