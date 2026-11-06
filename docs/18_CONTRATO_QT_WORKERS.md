# Contrato Qt / workers / reportes

Contrato del hito de integración. La fase SQLite actual amplía el protocolo a desktop/3 y sustituye los snapshots sólo en memoria: [contrato vigente de persistencia](19_PERSISTENCIA_SQLITE.md). Los límites de carga y exportación descritos aquí se mantienen.

## Frontera del puente

`desktop.describe()` informa protocolo `fiscalops.desktop/2` y motor `python-decimal-worker`. Se conserva `desktop.ping()`. El objeto `fiscal` tiene solamente tres slots propios:

| Método | Entrada | Respuesta inmediata |
|---|---|---|
| openJob | import o export | job_id opaco o rechazo |
| request | request_id,job_id,operación,payload JSON | ACK; el resultado llega por señal response |
| cancel | job_id | Cancelación cooperativa o trabajo ya terminado |

Señales públicas: response(JSON), progress(job_id,JSON), downloadStatus(saved/cancelled/failed). El receptor interno de resultados y la cola Python están en un QObject privado no registrado. La prueba de metaobjeto comprueba que `_received` y `dispatch` no están expuestos. No hay slots de lectura de rutas, SQL, comandos, red o escritura arbitraria.

El GUI crea QThread y un QObject trabajador que se mueve a ese hilo. Las conexiones son queued. El worker posee los documentos, interpreta XML, valida XSD, ejecuta Decimal, prepara proyecciones/agrupaciones y genera las exportaciones. El hilo GUI sólo atiende mensajes, permisos de selección/guardado y eventos de ventana. Referencias técnicas: [QThread](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html) y [señales Qt](https://doc.qt.io/qtforpython-6/PySide6/QtCore/Signal.html); las pruebas locales acreditan la ejecución, no estas páginas.

## Ciclo de importación

1. Selección con el file-input existente, arrastrar archivos o selector de directorio de Chromium en Qt. Sólo después de esa selección se envían los bytes como base64; no se entrega al backend una ruta de disco para leer.
2. import.begin crea un staging independiente. import.file recibe un archivo cada vez, con contrapresión por ACK/resultado. XML no pasa por File.text, normalizador, DOMParser ni descompresor del legado. import.reject registra un archivo excesivo sin leerlo completo en el navegador.
3. El worker interpreta bytes mediante el lector seguro y proyecta filas a las columnas existentes. También lee metadata y ZIP mediante rutas acotadas. Cada archivo/entrada rechazada tiene incidente propio.
4. import.prepare concilia metadata, duplicados y relaciones. Conflictos de metadata se conservan como DESCONOCIDO/hallazgo; no se sustituye vigencia oficial por metadata. Cada ocurrencia tiene doc_id/row_id propios, y SHA256 de contenido.
5. import.page entrega hasta50 posiciones y aproximadamente2MiB por página, permitiendo una fila individual mayor dentro del límite XML. Filas e incidentes comparten cursor sin omisiones ni duplicaciones.
6. import.commit publica el conjunto completo. Hasta entonces, cancelar/fallar mantiene el reporte anterior. El frontend arma sus filas provisionalmente y sólo las sustituye tras la confirmación. Se retienen hasta dos snapshots en memoria para tolerar respuestas pendientes; no es almacenamiento persistente.

La cancelación usa threading.Event y se comprueba entre documentos, páginas y bloques ZIP. No interrumpe por fuerza una validación XML/XSD ya en curso. No se usa QThread.terminate. Al cerrar durante un trabajo se cancela, se espera asíncronamente al fin de la unidad y se destruye la ventana con el hilo detenido. Las descargas aceptadas terminan antes de destruir su perfil Qt.

## Límites implementados

| Unidad | Límite |
|---|---|
| Archivo seleccionado |32MiB; XML individual sigue limitado a8MiB por el lector |
| Sesión de carga |64MiB de bytes de documentos/metadata y10000 documentos; exceso aborta el staging, conservando el reporte anterior |
| ZIP |20000 entradas,128MiB reales descomprimidos por contenedor,8MiB por entrada, ratio200; sólo stored/deflate |
| Puente |16 solicitudes pendientes /16 jobs; payload máximo46MiB de caracteres antes del parseo en worker |
| Exportación |64MiB de salida; presupuesto de67108864 caracteres de XML por hoja;32 hojas; máximo1048575 filas de datos por hoja, más encabezado |

ZIP verifica CRC al leer; no extrae entradas al disco. Rechaza rutas absolutas, `..`, ADS, symlinks, cifrado, métodos no admitidos, ZIP anidado y tipos desconocidos, registrando el motivo. Son controles ensayados en el alcance de integración, no una certificación exhaustiva contra todo archivo adversarial o cargas masivas.

## Selección y precisión compartidas

La UI conserva filtros, perfiles, ordenación, paginación, controles y visor. El frontend selecciona identidades, no envía importes para que el backend los acepte como autoridad. report.aggregate agrupa los doc_id seleccionados por moneda usando Decimal. report.export vuelve a resolver esos mismos IDs y verifica la lista/orden exactos de row_id del reporte; IDs desconocidos, duplicados o de otro snapshot se rechazan.

No se unen moneda nacional y extranjera. NULL no se transforma en cero para aparentar un agregado completo. Sólo una ausencia estructuralmente no aplicable aporta cero explícito, por ejemplo descuento inexistente sin descuentos conceptuales. El valor mostrado conserva NULL y el agregado utiliza el valor no aplicable documentado.

La presentación monetaria mantiene dos decimales como V21, redondeados/formateados por Decimal en el worker. Ordenar cifras en la UI usa comparación de cadenas decimales exactas, sin Number/parseFloat. Eso no cambia la precisión original de los importes exportados.

## Reportes y exportaciones

Se conservan los22 tipos de reporte: resumen, conceptos, impuestos conceptuales/globales, relaciones, pagos/documentos/impuestos, las cinco tablas de nómina, tres de Carta Porte, complementos, hallazgos, sin metadata, cancelados, duplicados e incidentes. El visor utiliza esas mismas filas para conceptos/impuestos y conserva las cinco pestañas. XML visual es representación del original conservado, sin ejecutar su contenido.

REP/Pagos1.0/2.0, Nómina1.2 y Carta Porte2.0/3.0/3.1 se proyectan por namespace/versión para conservar lectura y reportes. Estas proyecciones no amplían la cobertura normativa del motor. Las comprobaciones no implementadas permanecen NO EVALUADO/PENDING; no se llama soporte fiscal integral a una extracción estructural. Las sumas auxiliares de percepciones, distancias o pagos utilizan Decimal y conservan datos faltantes.

Excel se genera en el worker como OOXML real, con encabezado morado, autofiltro, primera fila congelada, anchos y columnas elegidas. Reporte es la primera hoja; las siete analíticas opcionales utilizan la misma selección de documentos. Valores de más de15 cifras significativas se conservan como texto exacto para evitar pérdida en Excel. CSV/TXT conservan ceros y dejan nulos vacíos; se mantiene protección contra fórmulas. No se recortan filas silenciosamente. Controles XML no válidos rechazan la exportación.

El guardado usa QFileDialog nativo; el path proviene del usuario, no de un slot web. Se prueba DownloadCompleted y se inspeccionan los archivos finales, no sólo la existencia temporal de una descarga parcial. Se verifican CRC y XML del XLSX; esta entrega no afirma una revisión visual mediante Microsoft Excel instalado.

Los botones ocultos heredados de Excel filtrado/paquete/cancelados/sin metadata también se enrutan al worker. Las antiguas salidas HTML disfrazadas de XLS se sustituyen por XLSX real; paquete conserva un archivo por reporte no vacío. No se eliminan rutas silenciosamente.

## Ejecución y modos

```powershell
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements/desktop.txt
.\.venv\Scripts\python.exe -m app.desktop.main
```

`scripts/spec011/Setup-Desktop.ps1` instala el lock actual y el lanzador existente abre el contenedor integrado. Sin Qt/puente, el HTML distribuido bloquea procesamiento y exportación; no cae al motor viejo. Sólo el servidor QA de `scripts/integration/serve.py` habilita explícitamente la referencia visual para ejecutar los tests históricos. `/without-native/` sirve el HTML sin esa marca y prueba el bloqueo.

El HTML original, legacy y60 referencias permanecen inmutables. `scripts/integration/build_ui.py` construye el runtime desde el commit anterior añadiendo el adaptador nativo; comprueba HTML/CSS/editor/escala sin cambios. El constructor SPEC011 queda protegido contra sobrescribir esta integración accidentalmente.

Pendientes: SQLite/caché/memoria portable, permisos persistentes de carpeta, actualización sin reselección, validaciones normativas integrales de complementos, firmas/estatus SAT, máquinas limpias, DPI125/150 y EXE final. Reabrir/actualizar una carpeta vuelve a pedir selección; no promete un permiso persistente que no se haya implementado.
