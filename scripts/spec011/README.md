# SPEC 011 — Ejecución y pruebas

La aplicación actual usa la copia de desarrollo `app/ui/index.html`. Original y legacy no se editan; la baseline de60 imágenes tampoco. No hay motor nuevo ni EXE final.

## Preparar y abrir en Windows

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install --require-hashes -r requirements/desktop-spec011.txt
./.venv/Scripts/python.exe -m app.desktop.main
```

Alternativa: `Setup-Desktop.ps1` y después `Start-Desktop.ps1` de esta carpeta. No cambian Python global ni políticas de seguridad. Si Windows impide .ps1, usa los comandos directos anteriores sin cambiar la política del sistema. Se requiere red sólo para preparar dependencias desde PyPI oficial; la ventana usa archivos locales y diagnóstico QWebChannel sin servidor remoto/HTTP.

`./.venv/Scripts/python.exe -m app.desktop_smoke --check` informa versiones/entorno y no abre ventana. `python scripts/spec011/build_ui.py` reconstruye la copia si se modifica el módulo fuente del editor. No ejecutar el extractor de auditoría para sobrescribir legacy.

## Regresión en navegador

Generar fixtures si es un checkout nuevo: `python scripts/visual/make_fixtures.py`. Iniciar `python scripts/spec011/serve.py`; imprime URL en127.0.0.1 y la guarda en tests/spec011/evidence/server.json. Este servidor es sólo de QA, no forma parte del contenedor. Ctrl+C lo detiene.

Usar Playwright y Chromium ya disponibles. En este equipo el paquete está en `$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules` y Chromium en `$env:LOCALAPPDATA/ms-playwright/chromium-1234/chrome-win64/chrome.exe`. Ajustar a rutas realmente instaladas; no asumirlas en otro equipo.

```powershell
node scripts/visual/capture.cjs --modules RUTA_NODE_MODULES --browser RUTA_CHROMIUM --url URL_LOCAL --target development --output tests/spec011/browser --strict
node scripts/visual/check_controls.cjs --modules RUTA_NODE_MODULES --browser RUTA_CHROMIUM --url URL_LOCAL --evidence tests/spec011/controls --strict
node tests/spec011/ui_regression.cjs --modules RUTA_NODE_MODULES --browser RUTA_CHROMIUM --url URL_LOCAL
node tests/spec011/paired_visual.cjs --modules RUTA_NODE_MODULES --browser RUTA_CHROMIUM --url URL_LOCAL
```

Entrecomillar rutas con espacios. Las pruebas escriben solamente resultados posteriores en tests/spec011; nunca la baseline. La suite específica visita original/desarrollo en contextos distintos, registra los cinco FAIL originales esperados y exige PASS en desarrollo. Los78 casos históricos se conservan; después de verificar que I queda activo se desactiva para preservar el ámbito de los siguientes casos.

Las comparaciones emparejadas esperan animaciones finitas y pausan únicamente las infinitas a tiempo0 en ambos lados dentro del harness. No modifican CSS del producto ni timers de navegación. Además se comparan54 capturas históricas, conservando los cambios intencionales05/14 y las diferencias de animación. Con `--compare-existing-only` se recalculan esos54 diffs sin repetir capturas emparejadas existentes.

## Smoke y capturas Qt reales

```powershell
./.venv/Scripts/python.exe tests/spec011/qt_smoke.py
./.venv/Scripts/python.exe tests/spec011/qt_visual.py
node scripts/spec011/compare_qt.cjs --modules RUTA_NODE_MODULES
```

Ejecutar las dos pruebas Qt secuencialmente para que sus eventos de teclado/ratón no compitan. Abren una ventana real con plataforma windows y datos sintéticos. No se usa offscreen ni depuración remota. La prueba fija un mínimo de cliente sólo para capturar1920×1080 si el marco excede el área disponible del monitor; no cambia DPI/resolución y lo retira antes de probar maximización.

El picker de archivos de QA retorna únicamente fixtures a la API chooseFiles; File.text y procesamiento original sí se ejecutan. No certifica el picker nativo de carpeta. El intento de progreso sólo se aprueba si antes y después sigue procesando; el resultado actual está marcado no estable. Se registra DPI96/DPR1 real; no se infieren125/150%.

`python scripts/spec011/verify.py` comprueba conservación, resultados, encabezados XLSX y comparaciones. `python scripts/spec011/render_matrix.py` reproduce el documento13 desde los resultados. Las rutas de salida existentes de SPEC011 son candidatos posteriores, no baseline: si se necesita conservar una ejecución posterior, copiarla a otra carpeta identificada antes de repetir.

La tabla de versiones/ruedas está en requirements y pip-install.json. No se versiona .venv ni se incorporan bibliotecas Qt a un EXE en esta etapa. Checkpoint anterior y final se describen en los reportes y en build/checkpoints/SPEC011_RESTORE_POINT.json.
