# Integración nativa — reproducción

Desde la raíz, con CPython3.11 x64 y `.venv`:

```powershell
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements/desktop.txt
.\.venv\Scripts\python.exe -m app.desktop.main
```

No cambiar políticas de Windows si un `.ps1` está bloqueado; usar los comandos directos. No hay servidor HTTP en el escritorio ni consultas SAT implícitas. Se reutilizan Qt/lxml ya fijados; no hay dependencias nuevas sin hashes.

Construir/comprobar:

```powershell
.\.venv\Scripts\python.exe scripts/integration/build_ui.py
.\.venv\Scripts\python.exe scripts/integration/run_tests.py
.\.venv\Scripts\python.exe scripts/fiscal/run_tests.py --output tests/integration/evidence/fiscal-tests.json
.\.venv\Scripts\python.exe tests/integration/qt_smoke.py
.\.venv\Scripts\python.exe tests/integration/qt_jobs.py
.\.venv\Scripts\python.exe tests/integration/qt_visual.py
node scripts/integration/compare_visual.cjs PATH_TO_NODE_MODULES
.\.venv\Scripts\python.exe scripts/integration/verify.py
```

Las pruebas Qt abren ventanas Windows reales, usan archivos sintéticos e inyectan selecciones de archivo/guardado sólo desde Python QA. No exponen paths por QWebChannel. Ejecutarlas secuencialmente. El test fiscal de enlaces duros requiere un entorno Windows que permita esa operación en el directorio temporal; no omitirlo y declarar PASS si un sandbox la bloquea.

Evidencia actual en `tests/integration/`: contracts, fiscal-tests, qt/smoke, jobs/jobs, visual/captures y comparison. Los intentos fallidos anteriores se distinguen de los resultados finales. Los screenshots son capturas reales; las pruebas visuales esperan el pintado y sólo pausan animaciones infinitas para comparar. Nunca se sobrescribe `tests/visual/baseline`.

Regresiones históricas del frontend:

```powershell
.\.venv\Scripts\python.exe scripts/integration/serve.py
node scripts/visual/capture.cjs --url URL_LOCAL --modules PATH_TO_NODE_MODULES --browser PATH_TO_CHROMIUM --target development --output tests/integration/browser --strict
node scripts/visual/check_controls.cjs --url URL_LOCAL --modules PATH_TO_NODE_MODULES --browser PATH_TO_CHROMIUM --evidence tests/integration/controls --strict
node tests/spec011/ui_regression.cjs --url URL_LOCAL --modules PATH_TO_NODE_MODULES --browser PATH_TO_CHROMIUM --output tests/integration/targeted
node tests/integration/no_native.cjs PATH_TO_NODE_MODULES URL_LOCAL
```

URL_LOCAL es exclusivamente el127.0.0.1 publicado por ese servidor. Este servidor habilita una referencia visual explícita del legado para los tests48/30/62; no es un motor fiscal de producción ni evidencia Decimal. El test sin Qt usa `/without-native/` sin esa marca y debe bloquear la carga/exportación. Las pruebas nativas y de contratos prueban los importes del motor real. Detener el servidor al terminar.

`create_checkpoint.py`, después del commit y con Git limpio, crea un bundle local nuevo y verifica su restaurabilidad. Conserva checkpoints anteriores y excluye .venv/EXE. No sube cambios ni XML a remotos.
