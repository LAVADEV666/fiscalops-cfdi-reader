# FASE 0.5 + FASE 1 — Referencia visual auténtica V21.1

Fecha: 2026-11-06. **FASE 0.5: DONE para recuperación del acceso visual y punto de restauración. FASE 1: PARTIAL.** Existe referencia visual auténtica, pero faltan carpeta/memoria reales, un fotograma de progreso estable, DPI real de Windows y la ejecución del contenedor Qt. No se aprueba globalmente la UI ni se certifica exactitud fiscal.

## Recuperación del navegador

No se repitió la auditoría. Se reutilizaron documentos00–05, el índice de242 declaraciones, riesgos y diagnósticos previos. La limitación se investigó con los componentes existentes:

| Opción | Disponibilidad comprobada | Resultado real |
|---|---|---|
| Python principal | 3.11.9 x64 | Servidor HTTP y herramientas stdlib disponibles; PySide6/PyQt6/Playwright Python ausentes. |
| Python incluido en runtime | 3.12.14 | PySide6/PyQt6/Playwright Python ausentes; no se instalaron paquetes. |
| Playwright Node incluido | 1.62.1 | Disponible en runtime de la aplicación. La búsqueda inicial sólo en Node global de FASE0 no lo detectaba. |
| Chromium instalado de Playwright | Revisión1234, navegador151.0.7922.34 | Ejecutó las capturas y navegación fuera del aislamiento de comandos. |
| Edge/Chrome | Ejecutables presentes | No se deduce funcionalidad por presencia; la vía final probada fue Chromium incluido e IAB. |
| Navegador integrado IAB | Disponible, versión exacta no obtenida | Seis tomas suplementarias reales; dos tomas de carga conservaron el tamaño anterior del override y están identificadas por sus dimensiones reales. |
| QtWebEngine/QWebChannel | Sin PySide6 en los dos Python inspeccionados | Contenedor fuente preparado; ejecución bloqueada, sin capturas Qt. |
| SQLite | Runtime3.45.1 en Python principal | Disponible; sin nueva base fiscal ni motor conectado. |

El servidor inicial dentro del aislamiento escuchaba, pero el navegador devolvió ERR_CONNECTION_TIMED_OUT; una conexión Python aislada produjo WinError10013. Al ejecutar el servidor fuera de ese aislamiento, autorizado para este trabajo, IAB abrió correctamente la página por `127.0.0.1`. Playwright también requirió ejecución fuera del aislamiento; el lanzamiento aislado terminó con código3221225506 y navegador cerrado.

No se cambió firewall, registro, políticas del navegador, certificados, permisos generales ni seguridad de Windows. No se usó file:// ni se levantó un servidor en0.0.0.0. `scripts/visual/serve.py` publica exclusivamente `/`, `/prototype.html` y `/health`; no publica carpetas, Git, documentos ni fixtures. Host y hash del prototipo se verifican. Seis pruebas HTTP reales comprobaron contenido íntegro, salud, rechazo de listados, traversal, archivos arbitrarios y Host ajeno. El contexto automatizado bloqueó peticiones fuera de ese origen.

## Evidencia y congelamiento

El HTML original y `legacy/` conservan SHA256 `33eeed2334a683b5360c2fc4f9cabc26885be66fef8714e4278f97235b8c373b`. No se sobrescribió legacy ni se corrigió el motor. El servidor devuelve los bytes originales. Los datos de pruebas son sintéticos, sin firmas válidas ni validación XSD; importes del legado nunca se utilizan como expectativas fiscales.

Se congelaron **60 imágenes** con hashes en `tests/visual/baseline/manifest.json`:54 PNG de Chromium (18 escenas×3 resoluciones) y6 JPEG nativos de IAB como corroboración de inicio/carga. Se conservaron los bytes JPEG recibidos, usando extensión correcta; no son PNG convertidos ni imágenes generadas. Tres capturas transitorias de progreso se excluyeron de la baseline aceptada y se conservaron en `tests/visual/evidence/transient/`.

Resoluciones CSS obligatorias:1366×768,1600×900,1920×1080. En las54 capturas principales, deviceScaleFactor=1, contexto nuevo con zoom predeterminado100%, viewport real y escala CSS V20/V21 registrados antes y después de cada toma. El navegador fue Chromium headless en Windows x64; versión/kernel del sistema y user-agent están en navigation.json. **DSF1 no prueba DPI real del escritorio de Windows**. Las seis tomas IAB usaron override de viewport, restablecido al terminar; su DPI/versión exacta no se infieren.

Dos tomas suplementarias IAB conservaron dimensiones anteriores al override: se obtuvieron1280×720 al solicitar1366×768 y1600×900 al solicitar1920×1080. Se corrigieron nombres y metadata según los bytes de imagen, sin modificarlos. No cuentan como evidencia de las dimensiones solicitadas. Las54 capturas principales verifican por separado las tres dimensiones requeridas.

Las animaciones originales siguen activas. El runner espera que terminen animaciones/transiciones finitas antes de capturar estados estables, sin modificar CSS, timers o estado fiscal. No se desactivó la animación orbital infinita. Diferencias futuras deben considerar ese ruido y las diferencias entre renderizadores; no se declara similitud100% ni se comparó una aplicación reconstruida inexistente.

| Escena congelada | Nombre base del PNG (se repite por resolución) | Qué demuestra |
|---|---|---|
| Inicio | 01_initial | Pantalla s1 auténtica antes del timer. |
| Carga vacía | 02_upload_empty | Distribución, botones, estados disabled y recursos originales. |
| Selección de archivos | 03_files_selected | Fixtures locales seleccionados y proceso habilitado. |
| Centro de reportes y tabla | 04_reports_table | Tabla original, indicadores, filtros y filas sintéticas. |
| Pestaña de tipo pulsada | 05_type_clicked | Defecto real: un clic en I no deja tipo activo. |
| Estado vacío por filtro | 06_empty_filter | Mensaje y tabla sin coincidencias. |
| Visor / resumen | 07_viewer_summary | Modal y pestaña inicial. |
| Visor / impuestos | 08_viewer_taxes | Pestaña real; valores fiscales NO aprobados. |
| Visor / conceptos | 09_viewer_concepts | Detalle expandible. |
| Visor / todos los datos | 10_viewer_fields | Agrupación de campos. |
| Visor / XML | 11_viewer_xml | Árbol XML real del fixture. |
| Editor | 12_column_editor | Tarjetas, perfiles y selección inicial. |
| Búsqueda del editor | 13_column_search | Campos filtrados sin rediseño. |
| Aplicación de búsqueda | 14_column_search_applied | Pérdida real de selección fuera de la búsqueda. |
| Constructor Excel | 15_excel_constructor | Hoja principal y opciones originales. |
| Selección de análisis | 16_excel_choices | Opciones elegidas antes de descargar. |
| Incidente real | 17_read_errors | XML deliberadamente mal formado registrado por el motor original. |
| Limpiar | 18_cleared | Vuelta real a carga y proceso deshabilitado. |

Los PNG principales fueron inspeccionados, incluyendo reportes a1920×1080 y editor/visor a1366×768. Se verifican automáticamente firma de imagen, dimensiones y hashes de las60 imágenes. No hay imágenes vacías de sustitución. `controls-trace.zip` contiene la traza real adicional con snapshots y capturas; puede abrirse con el visor de trazas de Playwright instalado.

## Navegación y diferencias confirmadas

`navigation.json`:48 comprobaciones,42 PASS y6 FAIL (dos defectos reproducidos en cada resolución). `controls.json`:30 comprobaciones,28 PASS y2 FAIL. Total: **78 comprobaciones,70 PASS y8 FAIL preexistentes**. Los procesos de diagnóstico terminan con0 si completan la recolección aunque registren FAIL; ese código no convierte los fallos en aprobaciones. La matriz08 cita cada prueba y distingue presencia de comprobación funcional.

- U02 queda reproducido en navegador: listeners de typeTabs procesan dos veces el mismo clic y el tipo activo termina vacío.
- U01 queda reproducido: buscar UUID y aplicar reduce el conjunto a los checks visibles, descartando otras columnas seleccionadas.
- Foco modal: Shift+Tab desde Cerrar escapa al documento de fondo; cerrar tampoco devuelve foco al botón invocador. Ambas comprobaciones fallan de forma auténtica.
- El primer intento detectó una carrera del timer inicial: una importación muy rápida llega a s3 antes de1600ms y el timer posterior la devuelve a s2. Evidencia en attempt-01-navigation.json y attempt-01-timer-returned-upload.png. El runner final espera que venza ese timer antes de importar, sin cancelarlo ni corregirlo.
- Una primera toma coincidió con el fade de entrada. Se ajustó únicamente el procedimiento de captura para esperar animaciones finitas. La evidencia transitoria y el primer intento no se usan como aprobación visual estable.

No son regresiones introducidas: el prototipo es idéntico. No se arreglaron UI ni cálculos en esta ejecución. La referencia conserva defectos documentados para que una futura corrección sea explícita y revisable.

## Casos pendientes y motivo exacto

| Caso | Estado | Motivo y siguiente acción |
|---|---|---|
| Carpeta conectada / memoria | PENDIENTE | showDirectoryPicker y su autorización nativa no se automatizaron en headless. No se inyectaron handles falsos. Usar carpeta sintética AAA010101AAA y procedimiento manual. |
| Progreso estable | NO ACEPTADO | Antes de las3 tomas el estado era s2/Procesados; al terminar screenshot ya era s3. Se conserva transición, sin afirmar captura estable de progreso. Capturar manualmente o en vídeo real del lote. |
| Permisos/errores nativos de carpeta | PENDIENTE | No se fabricaron ni aceptaron avisos de permisos. Sí se comprobó incidente XML real y alerta de selección vacía mediante evento dialog. |
| DPI real Windows | PENDIENTE | Viewports emulados no equivalen a cambiar/verificar100/125/150% del escritorio. Registrar valor real en captura manual. |
| QtWebEngine | BLOQUEADO | PySide6 ausente; no se atribuyen al contenedor las pruebas Chromium. |
| Modularización del frontend | DIFERIDA | La puerta de referencia completa sigue abierta por los casos anteriores; separar ahora impediría cerrar comparación íntegra. El shell carga el original sin modificarlo. |

## Reproducir en Windows

Usar `scripts/visual/README.md`. `Start-VisualReference.ps1` inicia servidor local y prepara fixtures. `Capture-VisualBaseline.ps1` usa Playwright/navegador existentes, sin descargar nada, y guarda nuevas capturas en una carpeta candidate con fecha. La baseline congelada no se sobrescribe. `record_manual.py` registra PNG auténticos aportados por el operador, con hash y metadatos declarados, pendientes de revisión. Un registro manual no es automáticamente una prueba aprobada.

Git: checkpoint de FASE0 `a8810bf05d9209a63c4508e23d39fc47bd315d47`; se verificó que el blob del HTML tiene exactamente el mismo SHA256. `.gitattributes` impide conversión de finales de línea al restaurar. El checkpoint final de esta etapa se identifica con `git log` y `build/checkpoints/RESTORE_POINT.json`, fuera del contenido versionado para evitar autorreferencia. No hay remotos configurados ni subidas.
