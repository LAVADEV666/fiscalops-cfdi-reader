# Reproducir la fase SQLite

Desde la raíz, con la `.venv` y `requirements/desktop.txt` existentes:

```powershell
.\.venv\Scripts\python.exe -m app.desktop.main
.\.venv\Scripts\python.exe scripts/persistence/run_tests.py
.\.venv\Scripts\python.exe scripts/integration/run_tests.py
.\.venv\Scripts\python.exe scripts/fiscal/run_tests.py --output tests/persistence/evidence/fiscal-tests.json
.\.venv\Scripts\python.exe tests/persistence/qt_recovery.py
.\.venv\Scripts\python.exe tests/integration/qt_smoke.py
.\.venv\Scripts\python.exe tests/integration/qt_jobs.py
node scripts/persistence/compare_visual.cjs PATH_TO_NODE_MODULES
.\.venv\Scripts\python.exe scripts/persistence/verify.py
```

Ejecutar las pruebas Qt secuencialmente: usan ventanas Windows reales. Las históricas usan SQLite en memoria para no tocar datos del usuario. `qt_recovery.py` usa una base temporal real en `.work/` ignorado y tres procesos Qt separados: carga/guardado, recuperación/exportación/limpieza y comprobación de inicio vacío. Verifica que un cambio inmediatamente anterior al cierre se guarda, que la conexión pertenece al worker y que está cerrada al salir.

Los veinte contratos prueban rollback por cancelación, escritura fallida, bloqueo, conflicto entre ventanas y caída abrupta de un proceso dentro de una transacción; también hashes, identidad/versionado, metadata, nulos/ceros, original UTF16, duplicados, los22 reportes y exportaciones tras reabrir. No se llenó realmente el disco: se inyectó un fallo SQL de escritura.

La comparación visual toma los tres reportes Qt del commit anterior y los compara con las capturas actuales sin modificar el baseline. El texto de persistencia del panel de memoria cambia intencionalmente; el HTML/CSS/editor/branding originales permanecen byte a byte.

Para verificar el bloqueo sin Qt, usar el servidor loopback QA de `scripts/integration/serve.py` y `tests/integration/no_native.cjs`; detener el servidor después. Los suites de referencia140/140 y las36 capturas del hito anterior se conservan como evidencia histórica, no se presentan como ejecuciones nuevas de SQLite.

`create_checkpoint.py` crea un bundle nuevo después de un commit limpio. No incluye `.venv`, bases SQLite ni datos del usuario, y no utiliza remotos.
