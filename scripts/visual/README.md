# Captura reproducible en Windows

Estos scripts conservan el HTML original y sólo usan datos sintéticos. No instalan navegadores o paquetes, no cambian firewall/seguridad y no producen EXE. La baseline existente está congelada; las ejecuciones nuevas se guardan en carpetas candidate.

## Captura automática

Desde la raíz del proyecto, en una terminal Windows iniciada por el operador:

```powershell
powershell -File scripts/visual/Start-VisualReference.ps1
```

No cambies la política de ejecución para lanzar los scripts: si tu entorno los bloquea, utiliza directamente `python scripts/visual/make_fixtures.py` y `python scripts/visual/serve.py`. El servidor imprime la URL con puerto libre y escribe server.json. Mantén esa terminal abierta y ciérralo con Ctrl+C al terminar. Sólo escucha127.0.0.1 y publica el HTML original y health, sin listado de archivos.

En otra terminal:

```powershell
powershell -File scripts/visual/Capture-VisualBaseline.ps1
```

El wrapper busca Playwright del runtime incluido y Chromium ya instalado. Puede recibir `-Modules`, `-Browser`, `-Node`, `-Url` y `-Output` explícitos si están en otra ruta. Si faltan dependencias, informa el error; no las descarga. La versión del navegador realmente usada queda en navigation.json. Para una pasada visible del runner principal se admite `-Headed`; las comprobaciones adicionales de controles siguen headless y se registran como tales.

Los comandos Node equivalentes son:

```powershell
node scripts/visual/capture.cjs --modules RUTA_NODE_MODULES --browser RUTA_CHROME_EXE --url http://127.0.0.1:PUERTO --output tests/visual/candidate-NOMBRE
node scripts/visual/check_controls.cjs --modules RUTA_NODE_MODULES --browser RUTA_CHROME_EXE --url http://127.0.0.1:PUERTO --evidence tests/visual/candidate-NOMBRE/evidence
```

Las rutas con espacios deben ir entre comillas. Los runners sólo aceptan origen literal127.0.0.1 y salidas dentro del proyecto. No se cargan perfiles personales. Se permite sólo tráfico al origen local. Un código de salida0 significa recolección completada: revisar los FAIL del JSON. No se debe publicar como PASS una reproducción correcta de un defecto del legado.

El timer inicial de1600ms puede devolver una importación rápida a la pantalla de carga. El runner conserva el timer y espera su vencimiento antes de importar. Espera animaciones finitas antes de screenshots estables, manteniendo las animaciones originales. Progreso se registra antes/después: si cambió de pantalla durante la toma, no se acepta como baseline estable.

## Carpeta/memoria y progreso manuales

1. Abre la URL local en Edge/Chrome del equipo objetivo. Anota navegador/versión, Windows, zoom y escala real de pantalla. Ajusta el viewport CSS de contenido a1366×768; repite1600×900 y1920×1080. No confundas tamaño exterior de ventana con viewport. El valor de DPI debe observarse en Windows, no inferirse de deviceScaleFactor.
2. Conecta exclusivamente `tests/visual/fixtures/AAA010101AAA` con Cambiar carpeta. Acepta personalmente sólo el permiso de lectura de esa carpeta sintética. No selecciones carpetas fiscales reales. Captura panel conectado y memoria, ejecuta Procesar nuevos, vuelve a carga y Actualizar; comprueba el conteo de caché. Registra selección/reconexión y cualquier error real. No fabriques paneles con DevTools.
3. Para progreso, importa `tests/visual/.work/progress-synthetic.zip` generado por make_fixtures. Captura con la herramienta de recortes de Windows o un vídeo real mientras la barra y texto muestran procesamiento. Si el lote termina antes, indícalo; no alteres timers o contenido de la UI para simular trabajo.
4. Captura modales y sus cinco pestañas; usa Tab, Shift+Tab y Escape. Los defectos de foco actuales están documentados y no equivalen a diferencias introducidas por el shell.
5. Guarda un PNG auténtico del contenido, sin datos ajenos a la prueba. Regístralo con metadatos observados, por ejemplo:

```powershell
python scripts/visual/record_manual.py --png "C:\ruta\captura.png" --scene folder_connected --viewport-width 1366 --viewport-height 768 --browser "Edge VERSION_OBSERVADA" --windows-dpi-percent 100 --zoom-percent 100 --notes "Carpeta sintética elegida; sólo lectura"
```

El script verifica firma/dimensiones de PNG, original y hash; agrega imagen/JSON con nombre único en baseline/manual sin sobrescribir nada. La metadata del operador queda marcada como declarada y PENDING_REVIEW. Registrar una imagen no aprueba automáticamente escena ni exactitud fiscal. Para otros estados: memory_cached, processing_progress, native_error o qt_container.

## Contenedor Qt

```powershell
python -m app.desktop_smoke --check
python -m app.desktop_smoke --width 1366 --height 768
```

La primera ejecución real de esta entrega informó PySide6 ausente. Usar un intérprete con QtWebEngine y QWebChannel verificados antes del segundo comando. No confundir una compilación de sintaxis con prueba de ventana. La dimensión del argumento es exterior de ventana; medir y registrar el viewport interior para comparar. El shell no conecta el motor nuevo ni persiste datos personales.

## Verificación y revisión

`python scripts/visual/verify_visual.py` verifica hashes de fuente/capturas, dimensiones, manifiesto, resultados de controles y archivos exportados como ZIP/XML. No valida XSD ni reglas SAT. `python scripts/visual/test_server.py` ejecuta seis comprobaciones HTTP sólo locales y necesita que el entorno permita loopback.

Abrir la traza existente con el Playwright instalado: `node RUTA_NODE_MODULES/playwright/cli.js show-trace tests/visual/evidence/controls-trace.zip`. Es una acción manual opcional, no una descarga. Comparar candidatos con la baseline por escena, tamaño, renderizador, fuentes y animaciones. Aún no hay una aplicación reconstruida ni un porcentaje de similitud calculado.
