# Reproducir historial y respaldos Qt

Mismo entorno y lanzador; no hay paquetes adicionales:

```powershell
.\.venv\Scripts\python.exe -m app.desktop.main
.\.venv\Scripts\python.exe scripts/history/run_tests.py
.\.venv\Scripts\python.exe scripts/persistence/run_tests.py
.\.venv\Scripts\python.exe scripts/integration/run_tests.py
.\.venv\Scripts\python.exe scripts/fiscal/run_tests.py --output tests/history/evidence/fiscal-tests.json
.\.venv\Scripts\python.exe tests/history/qt_history.py
.\.venv\Scripts\python.exe tests/integration/qt_smoke.py
.\.venv\Scripts\python.exe tests/integration/qt_jobs.py
node scripts/history/compare_visual.cjs PATH_TO_NODE_MODULES
.\.venv\Scripts\python.exe scripts/history/verify.py
```

Ejecutar Qt secuencialmente, en Windows real. Las ventanas de prueba usan selectores Python QA para devolver las rutas temporales seleccionadas; esos hooks no están en WebChannel. La prueba nueva utiliza dos procesos Qt separados y una base temporal en `tests/history/.work/`, ignorada. Se crean dos sesiones sintéticas, se busca/abre la primera, se respalda, se rechaza un archivo inválido, se revisa/descarta y luego se confirma una restauración. Verifica respaldo preventivo visible, recuperación de la primera sesión, CSV/TXT/XLSX filtrados y permanencia después de reiniciar.

Los contratos incluyen interrupción real con os._exit dentro de una restauración, cancelación, fallo de publicación, fallo de INSERT, detección de enlaces duros, archivo fuente cambiado tras revisar, candidato alterado, conflictos entre ventanas, historial paginado e intentos de esquema/hash inválidos. El fallo de escritura se simula; no se llenó físicamente el disco.

El test de enlaces duros requiere permisos de Windows para crearlos en el temporal; ejecutarlo con permisos adecuados, no omitirlo y declarar PASS. Las pruebas originales Qt usan SQLite en memoria y no tocan FiscalOpsData. Los respaldos de prueba no se incluyen en Git; sí se guardan resultados, metadatos, capturas auténticas y exportaciones sintéticas.

La comparación visual toma los reportes nativos del checkpoint SQLite anterior. La adición prevista es el botón Qt en la cabecera; el viewport, HTML/CSS/editor y baseline60 se preservan. Para comprobar el bloqueo sin Qt usar el servidor loopback QA `scripts/integration/serve.py` y `tests/integration/no_native.cjs`, deteniéndolo después. Las suites140 del navegador y las capturas históricas anteriores no se presentan como ejecuciones nuevas.

`create_checkpoint.py`, tras commit limpio, crea un bundle local verificado nuevo. No incluye bases del usuario ni .venv/EXE y no usa remotos.
