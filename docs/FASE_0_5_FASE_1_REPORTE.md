# Entrega — FASE 0.5 + FASE 1

**FASE 0.5: DONE en recuperación de acceso visual y restauración reproducible.** Servidor local permitido, navegador real, dependencias inspeccionadas y Git inicializado, sin modificar seguridad general del sistema.

**FASE 1: PARTIAL.** Se congeló referencia auténtica con60 imágenes; faltan escenas nativas y prueba Qt. No se declara DONE de la etapa completa ni del producto.

## Alcance y archivos

La auditoría previa no se rehízo. Se consultaron00–05 y su checkpoint y se conservaron original/legacy sin escribirlos. Ningún módulo fiscal fue corregido o reemplazado; no hay EXE definitivo.

| Entregable | Archivos creados/modificados | Resultado |
|---|---|---|
| Baseline | docs/07_BASELINE_VISUAL.md; tests/visual/baseline/manifest.json;54 PNG+6 JPEG | Referencia auténtica con hashes, viewport y contexto. |
| Compatibilidad | docs/08_MATRIZ_COMPATIBILIDAD_UI.md; evidence/buttons.json |50 botones originales+5 pestañas dinámicas, con presencia y pruebas separadas. |
| Arquitectura | docs/09_ARQUITECTURA_DESKTOP.md; app/desktop_smoke.py | Shell mínimo fuente, sin motor nuevo; ejecución Qt bloqueada. |
| Siguiente motor | docs/10_PLAN_RECONSTRUCCION_MOTOR.md | Plan incremental, P0 abiertos, validación normativa posterior. |
| Captura local | scripts/visual/serve.py,make_fixtures.py,capture.cjs,check_controls.cjs | Servidor sólo127.0.0.1, fixtures anónimos y automatización real. |
| Procedimiento Windows | scripts/visual/README.md y3 scripts PowerShell | Ejecución/capturas/candidato y diagnóstico desktop, sin instalaciones automáticas. |
| Evidencia manual | scripts/visual/record_manual.py | Registro de PNG real con metadata del operador y revisión pendiente; sin fabricar estados. |
| Verificación | scripts/visual/test_server.py,verify_visual.py,probe_environment.py,inventory_ui.py,freeze_manifest.py | Hashes, dimensiones, rutas HTTP, descargas y cobertura de controles. |
| Versionado | .gitignore,.gitattributes,Git local | Checkpoints sin remotos ni conversión de bytes al restaurar. |
| Índice principal | README.md | Estado actualizado y enlaces a entregables; FASE0 queda como informe histórico. |

`tests/visual/.work/` contiene únicamente material generado temporalmente, excluido de Git. Los archivos y metadatos del servidor son locales. Los fixtures incluidos no tienen firmas válidas ni se presentan como XML fiscal certificado.

## Pruebas ejecutadas y evidencia

| Comando/acción | Resultado real | Evidencia |
|---|---|---|
| Servidor HTTP desde entorno aislado | Navegador timeout; cliente Python WinError10013 | Diagnóstico documentado en07. |
| Servidor loopback fuera del aislamiento | IAB y Chromium abrieron el HTML original | Capturas; navigation.json. No se modificó firewall ni políticas. |
| Playwright capture.cjs |57 capturas tomadas:54 estables aceptadas y3 transitorias excluidas | navigation.json; baseline; evidence/transient. |
| Captura IAB |6 JPEG suplementarios auténticos | Manifest; dos tamaños de carga conservaban override anterior y se registraron por dimensiones reales. |
| Navegación principal |48 comprobaciones:42 PASS,6 FAIL | navigation.json. |
| check_controls.cjs |30 comprobaciones:28 PASS,2 FAIL | controls.json,controls-trace.zip,controls-final.png. |
| test_server.py |6 pruebas HTTP PASS | server-tests.json. |
| verify_visual.py |60 hashes/dimensiones, fuente/legacy/Git idénticos;3 XLSX descargados verificados ZIP/XML | verification-stage1.json. No apertura Excel real ni validación fiscal. |
| Desktop --check |PySide6 ausente; GUI no ejecutada | desktop-check.json. |
| Sintaxis Python/Node/PowerShell |Compilación/parsing completados | syntax-checks.json. No equivale a prueba Qt. |
| Git restauración |Blob del original idéntico al fichero y SHA preservado | checkpoint inicial a8810bf; punto final/bundle en build/checkpoints. |

Un exit0 del runner de captura indica que terminó de recolectar; no transforma FAIL en PASS. El primer intento fallido de automatización se conserva en attempt-01-navigation.json: una carrera del timer inicial devolvió la pantalla al estado de carga. El runner final espera el timer original sin modificarlo.

## Diferencias y regresiones

No hubo cambios al HTML original ni a legacy; SHA256 de ambos: `33eeed2334a683b5360c2fc4f9cabc26885be66fef8714e4278f97235b8c373b`.

Se confirmaron defectos preexistentes de UI: doble procesamiento del clic de tipo en3 resoluciones, pérdida de columnas al aplicar búsqueda en3 resoluciones, fuga de foco con Shift+Tab y falta de retorno del foco al cerrar editor. Son8 comprobaciones FAIL, no8 cambios introducidos. También se observó la carrera del timer inicial en el primer intento. No se corrigieron durante la congelación.

Las capturas de progreso cruzaron de s2 a s3 y se separaron de la baseline estable. Las capturas IAB son JPEG nativos y dos tuvieron dimensiones previas al override; se corrigieron nombres/metadatos, no píxeles. Las54 capturas principales sí verifican las tres resoluciones CSS obligatorias.

## Bloqueos y recomendación FASE 2

Carpeta/memoria requieren selección y autorización nativa sobre la carpeta sintética. Progreso necesita captura estable manual o vídeo real. DPI Windows debe observarse en el equipo, no deducirse de emulación. QtWebEngine/QWebChannel requieren PySide6 realmente disponible para ejecutar el shell y comparar recursos, teclado, foco y tamaños. Se entrega procedimiento para cada pendiente; no se declara probado lo que sólo existe como código.

Iniciar FASE2 completando esas verificaciones y aceptando la matriz de conservación. Después modularizar HTML/CSS/JS y conectar únicamente contratos/servicios de escritorio comprobados. Mantener los riesgos fiscales P0 abiertos para su fase técnica con Decimal, fuentes oficiales y pruebas versionadas; no utilizar importes de estas capturas como valores fiscales de referencia.

**Estado global de esta entrega: PARTIAL.** Recuperación visual completada; cierre íntegro de FASE1 pendiente.
