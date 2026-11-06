# Preparación desktop — prueba mínima de contenedor

**Resultado: BLOCKED_MISSING_PYSIDE6 para ejecución gráfica.** Se entrega código ejecutable de prueba en `app/desktop_smoke.py`; comprobación real en `tests/visual/evidence/desktop-check.json`. Python3.11 y el Python3.12 incluido no tienen PySide6. No se descargó Qt ni se produjo EXE. Compilar sintaxis Python no demuestra que la integración Qt funcione.

## Alcance implementado y límites

El contenedor comprueba hashes del original y legacy, inicia un servidor exclusivamente en127.0.0.1 con puerto libre y carga sus bytes originales en QWebEngineView. La ventana usa el frontend V21.1 sin nuevos componentes, sin reemplazo fiscal y sin rediseño. El perfil Qt es off-the-record para no leer credenciales/historial del navegador del usuario. Se bloquean navegaciones y peticiones HTTP ajenas al origen local; data/qrc/blob se permiten para recursos locales del documento. El servidor se cierra al salir.

Hay registro mínimo de QWebChannel con un objeto diagnóstico que sólo expone ping. El HTML original no carga qwebchannel.js: **handshake frontend/backend no conectado ni probado**. No se afirma que registrar un objeto sea tener un puente fiscal. No se exponen lectura de archivos arbitrarios, SQL, secretos ni métodos fiscales.

No se creó base de datos ni se migró IndexedDB. SQLite está disponible y su diseño modular propuesto en03 sigue vigente. La prueba deja que el JavaScript original exista en la página, pero no incorpora motor nuevo. Selección de carpeta, permisos, descargas, caché y persistencia requerirán adaptadores desktop y pruebas específicas; la compatibilidad de esas APIs no se infiere de Chromium externo.

## Componentes evaluados

| Componente | Decisión y evidencia |
|---|---|
| PySide6/QtWebEngine | Sigue como candidato preferido por conservar HTML/CSS. Ausente en entornos inspeccionados; no hay medida de tamaño/memoria o equivalencia Qt. |
| QWebChannel | Importación prevista y registro fuente mínimo; pendiente handshake restringido y contratos de03. |
| Backend Python | Motor nuevo aún no creado. Shell separado de lógica fiscal y servidor de referencia reutilizado. |
| SQLite | Runtime3.45.1 comprobado; futuro repositorio transaccional con migraciones y hash de contenido. |
| Frontend modular | Se preserva original. No se convirtió a React, widgets nativos ni otro sistema visual. Modularización pendiente de completar baseline. |
| Distribución | No se creó PyInstaller/spec ni ejecutable final. Licencias/lock de Qt se determinarán con versión realmente instalada/probada. |

No se inventó una versión de dependencia Qt instalada ni una licencia auditada. La siguiente integración debe seleccionar una versión compatible, obtenerla de fuente oficial permitida y fijarla con hashes/licencias; las pruebas de esta entrega no justifican instalar una versión arbitraria ni declarar portabilidad.

## Ejecución y diagnóstico

```powershell
python -m app.desktop_smoke --check
python -m app.desktop_smoke --width 1366 --height 768
```

El primer comando devolvió diagnóstico de dependencia ausente y salida no exitosa. No se intentó iniciar una ventana Qt inexistente. `scripts/visual/Test-DesktopContainer.ps1 -CheckOnly` ofrece el mismo diagnóstico; con un Python que tenga las dependencias, omitir CheckOnly abre el shell. Esta ruta todavía requiere ejecución real.

La prueba de contenedor debe medir viewport CSS interior, no confundir tamaño exterior de ventana Qt con1366×768. Registrar DPR del widget, pantalla/DPI real, versión Qt/Chromium, plataforma y fonts; capturar los mismos estados que la baseline. Los títulos del marco de ventana y controles del sistema se separan del contenido comparado. No se prometen capturas idénticas entre navegadores sin medir diferencias.

## Pruebas necesarias antes de aprobar

1. Instanciar imports Qt, ventana y cierre limpio del servidor; comprobar que no hay errores de recursos o carga.
2. Capturar inicio/carga/reportes/modales a las tres dimensiones CSS y registrar DPI Windows. Comparar con manifest de baseline, admitiendo sólo diferencias revisadas de renderizador/animación.
3. Navegar con ratón, Enter/Espacio, Tab/ShiftTab y Escape; reproducir y corregir de forma controlada foco/listeners ya identificados. No atribuir diferencias del legado al shell.
4. Verificar picker/descargas locales con fixtures; definir política de permisos y caché portable separada del perfil de navegador. No activar elevación ni conexiones externas.
5. Conectar un handshake diagnóstico aislado y validar contrato antes de exponer operaciones. El motor fiscal seguirá desconectado hasta sus pruebas versionadas.

La modificación de `app/desktop_smoke.py` no toca `parseCFDI`, impuestos, nómina ni pagos. La ausencia de Qt impide aprobar navegación, foco, tamaños y recursos del contenedor; esas tareas quedan explícitas en08 y en el reporte final.
