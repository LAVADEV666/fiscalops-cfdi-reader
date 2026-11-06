# SPEC 011 — Contenedor desktop real

**FASE 1.2: DONE en el alcance de integración y smoke test.** Se abrió una ventana nativa Windows, se ejecutaron30 comprobaciones con Qt y se verificó cierre del proceso. Las capacidades de carpetas nativas y escalados no ensayados quedan pendientes, sin certificarlas.

## Entorno aislado y reproducible

Se creó `.venv` con CPython3.11.9 x64. El Python global conserva sus paquetes; PySide6 se instaló únicamente dentro del entorno del proyecto desde PyPI oficial. `pip-install.json` conserva URLs y hashes de ruedas; `requirements/desktop-spec011.txt` fija las seis dependencias y SHA256 para Windows x64:

| Paquete | Versión instalada |
|---|---|
| PySide6 |6.12.0 |
| PySide6_Essentials |6.12.0 |
| PySide6_Addons |6.12.0 |
| PySide6_WebEngine |6.12.0.140 |
| PySide6_Pdf |6.12.0.140 |
| shiboken6 |6.12.0 |

Qt runtime6.12.0, Chromium integrado140.0.7339.225, plataforma Qt`windows`, Windows build26200. Se registró el identificador de ventana nativo, visibilidad/exposición real, monitor, geometría1920×1080, DPI lógico96, DPR1 y DPI físico informado por Qt. No se usó plataforma offscreen, servidor remoto, flag para desactivar sandbox ni cambio de firewall o seguridad Windows.

El entorno y metadatos de licencias de paquetes están en `desktop-environment.json`; son metadatos observados, no una auditoría legal de distribución. No se incluye .venv en Git/bundle ni se distribuye EXE. PySide6_Pdf es dependencia del paquete instalado, no una función PDF incorporada al producto.

## Implementación final

`app/desktop/main.py` carga `app/ui/index.html` directamente desde disco en QWebEngineView. No inicia servidor HTTP en escritorio; loopback sólo se emplea en las pruebas de navegador. El perfil es off-the-record y no lee perfiles personales. La lista de recursos permitidos se limita a los archivos UI conocidos y la referencia protegida para QA; se rechazan peticiones remotas y navegación arbitraria.

La ventana tiene marco nativo, puede redimensionarse/maximizarse y usa el frontend preservado. La captura del contenido no incluye el marco del sistema. No se sustituyó el motor ni el lector de archivos existente. `app/desktop_smoke.py` queda como lanzador compatible del contenedor actual; `--check` escribe diagnóstico en SPEC011 y no sobrescribe el diagnóstico histórico de FASE0.5.

QWebChannel está conectado realmente. Qt entrega su biblioteca local y `desktop-bridge.js` publica un wrapper mínimo con ready/ping. Se registran sólo dos slots propios:

| Slot | Contrato ejecutado |
|---|---|
| describe() | JSON protocol=fiscalops.desktop/1, capabilities diagnóstico, motor legacy y flujo de archivos no sustituido. |
| ping(requestId) | Identificador acotado a128 caracteres y respuestaok; prueba ida/vuelta real. |

No se exponen SQL, lectura arbitraria de rutas, ejecución de comandos, importación fiscal o credenciales. Los contratos usan la API de [QWebEnginePage](https://doc.qt.io/qtforpython-6/PySide6/QtWebEngineCore/QWebEnginePage.html) y [QWebChannel](https://doc.qt.io/qtforpython-6/PySide6/QtWebChannel/QWebChannel.html); la evidencia de ejecución es local, no esas páginas de documentación.

## Smoke test real y medidas visuales

`tests/spec011/qt_smoke.py` ejecutó30 comprobaciones PASS: ventana expuesta/plataforma Windows, handshake/ping, recursos, tres viewports, maximizar, carga de50 fixtures por el file-input de Qt, tabla, clic de tipo, foco y teclado desde ambos invocadores, modales de Excel/visor, cinco pestañas, scroll horizontal, operación local, rechazo de red, lote2000 y cierre limpio.

La selección de archivos de QA usa chooseFiles con lista sintética inyectada desde Python, no desde QWebChannel. Después la lectura File.text y el motor original se ejecutan realmente en Qt. Esto no equivale a probar el selector nativo de carpetas ni permisos/reconexión. No se cargaron datos de clientes.

Las peticiones de la ejecución final son archivos UI locales. Un fetch externo de prueba fue rechazado por Qt antes de llegar al interceptor; además la allowlist nativa lo rechaza. No se debilitó la política de archivo local para fabricar un evento de interceptación. `offline_proof` documenta las dos condiciones y la ausencia de servidor HTTP. No se afirma haber desconectado físicamente la red del equipo.

El marco/área disponible de Windows ajustó inicialmente una solicitud1920×1080 a1920×1061. La prueba final usó un tamaño mínimo de cliente sólo durante QA para obtener los tres viewports interiores exactos; luego retiró la restricción y comprobó maximización/restauración. La aplicación normal no fija ese mínimo. No se alteró la resolución ni DPI de Windows.

Las36 capturas comparativas y18 diffs de Qt usan las mismas escenas/datos/tamaños en original y desarrollo. Máximo mismo Qt0.230%; editor/visor/Excel0%. La comparación directa con la baseline de Chromium151 muestra hasta6.846% en tabla por renderizador/scrollbars; se conserva el resultado y se considera una diferencia de plataforma aceptable en este smoke, sin afirmar coincidencia total. Se inspeccionaron las imágenes y no se detectaron nuevos recortes o superposiciones críticas.

## Sistema de archivos: contrato propuesto, todavía no expuesto

| Operación futura | Entrada | Resultado y restricciones propuestas |
|---|---|---|
| selectFolder | requestId | QFileDialog nativo elegido por usuario; grantId opaco, etiqueta de carpeta y alcance de lectura. No devolver acceso general al disco. |
| reconnectFolder | grantId | Revalidar existencia/permisos del origen; fallo explícito si está desconectado, sin borrar documentos. |
| readAuthorizedFiles | grantId,rutas relativas,jobId | Resolver cada ruta dentro del origen autorizado; bloquear escapes/symlinks fuera de alcance; lectura acotada, sin método de path absoluto arbitrario. |
| refreshFiles | grantId,jobId | Inventario/diferencias con identidades y hashes; aplicar sólo tras verificar el nuevo flujo. |
| getProgress | jobId | Estado, aceptados/rechazados/procesados/incidentes y total descubierto, sin importes sensibles en logs. |
| cancelOperation | jobId | Cancelación cooperativa, confirmación de unidades finalizadas e incompletas; no simular éxito si ya terminó. |

Estos métodos son una propuesta de contrato, no slots funcionales. El nuevo selector se implementará y probará por separado antes de reemplazar el flujo del navegador. No se mezclará con correcciones fiscales. La persistencia de grants/memoria requerirá diseño portable y almacenamiento transaccional posterior.

## Pendientes concretos

- Selector de carpeta real, permisos, reconexión, actualización y memoria portable: sin implementación/certificación nativa todavía.
- Captura estable de progreso: el lote2000 terminó, pero la toma cruzó de Preparando a Reporte listo; `accepted_stable_capture=false`. La imagen existe como intento, no como aprobación.
- DPI125/150%, otras versiones de Windows, máquina limpia y distribución portable: no ensayados en esta SPEC. Sí se registró el contexto nativo actual96/DPR1.
- Motor fiscal: sigue legacy con P0 abiertos; no hay certificación SAT.

## Ejecución Windows

```powershell
powershell -File scripts/spec011/Setup-Desktop.ps1
powershell -File scripts/spec011/Start-Desktop.ps1
```

No cambies políticas de ejecución si tu entorno bloquea .ps1. Alternativa directa documentada en `scripts/spec011/README.md`: crear .venv, instalar el lock con --require-hashes y ejecutar `.venv\Scripts\python.exe -m app.desktop.main`. El uso normal del contenedor no requiere administrador, servidor ni conexión después de preparar las dependencias.
