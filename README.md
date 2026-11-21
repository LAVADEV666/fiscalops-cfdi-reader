# FiscalOps CFDI Reader — V21.1 / motor XML + Decimal

**Hito actual: historial visual y respaldos/restauración SQLite desde Qt.** El botón **Sesiones y respaldos** permite buscar/abrir sesiones, crear un respaldo verificado y restaurar tras revisar su contenido, con copia preventiva y transacción. Se conservan22 reportes, visor, filtros/columnas y exportaciones Decimal. [Entrega](docs/22_HISTORIAL_RESPALDOS_REPORT.md) · [Contrato](docs/21_HISTORIAL_RESPALDOS_SQLITE.md) · [Pruebas](scripts/history/README.md).

```powershell
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements/desktop.txt
.\.venv\Scripts\python.exe -m app.desktop.main
```

Original, legacy y60 referencias preservados. Limpiar cierra la sesión conservando historial; doble clic en Borrar memoria elimina los datos persistidos sin tocar originales seleccionados. La conexión SQLite pertenece al worker; importación/cálculos/exportación continúan fuera del GUI. Grants de carpeta, caché incremental, validaciones integrales de complementos y EXE final siguen pendientes. Sin Qt no se permite volver al motor legado.

El hito anterior de integración Qt se conserva en [17](docs/17_INTEGRACION_QT_WORKERS_REPORT.md) y [18](docs/18_CONTRATO_QT_WORKERS.md); su almacenamiento en memoria fue sustituido por la fase SQLite.

La persistencia SQLite del hito anterior se conserva en [19](docs/19_PERSISTENCIA_SQLITE.md) y [20](docs/20_PERSISTENCIA_SQLITE_REPORT.md). La base activa está en `FiscalOpsData/fiscalops.sqlite3`; las copias preventivas se conservan en `FiscalOpsData/backups`. No se incluyen bases ni respaldos del usuario en Git.

## Hito anterior — motor independiente

Motor fiscal independiente en `app/fiscal`, con lector seguro por namespaces CFDI3.3/4.0, matriz normativa SAT y reconciliación Decimal F01–F06 para ingresos/egresos. Su API y CLI continúan disponibles. La integración Qt posterior se describe arriba; el HTML original sigue como referencia inmutable.

```powershell
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements/fiscal.txt
.\.venv\Scripts\python.exe -m app.fiscal tests/fiscal/fixtures/p0_iva_ieps_40.xml --output resultado-fiscal.json
```

59 pruebas del motor;16 fuentes oficiales con hashes;13 fixtures sintéticos con validación XSD y reglas separadas. Leer [matriz normativa](docs/06_MATRIZ_NORMATIVA_SAT.md), [entrega fiscal](docs/15_MOTOR_FISCAL_P0_REPORT.md), [API/CLI](docs/16_CONTRATO_MOTOR_FISCAL.md) y [reproducción](scripts/fiscal/README.md).

## Arranque directo en Windows

Para equipos corporativos que no permitan distribuir un EXE, ejecuta [Iniciar-CFDI-Reader.bat](Iniciar-CFDI-Reader.bat) desde la carpeta del repositorio. El lanzador usa `.venv` si ya existe; en el primer arranque busca Python3.11, crea el entorno local e instala las dependencias fijadas de `requirements/desktop.txt`. No requiere permisos de administrador ni modifica una instalación global de Python.

La primera ejecución necesita acceso a PyPI para descargar las ruedas de Qt y el motor fiscal. Después, el arranque es local con:

```powershell
.\.venv\Scripts\python.exe -m app.desktop.main
```

El producto de escritorio no depende de un `.exe` de FiscalOps; sí requiere Python3.11 de64bits y las dependencias fijadas. `FiscalOpsData` permanece local y está excluido de Git.

## Hito preservado — SPEC011

**FASE 1.1 DONE / FASE 1.2 DONE en el alcance de SPEC011.** En ese hito se estabilizó la UI y se ejecutó Qt en Windows conservando el flujo fiscal legado. La integración actual, descrita arriba, ya lo sustituye en Qt. Original, legacy y60 referencias permanecen intactos.

Para abrir el contenedor:

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install --require-hashes -r requirements/desktop.txt
./.venv/Scripts/python.exe -m app.desktop.main
```

También se pueden usar [Setup-Desktop.ps1](scripts/spec011/Setup-Desktop.ps1) y [Start-Desktop.ps1](scripts/spec011/Start-Desktop.ps1). La UI de desarrollo está en `app/ui/index.html`; el HTML raíz continúa como referencia inmutable.

Resultados:48/48 navegación,30/30 controles,62/62 específicos y30/30 Qt. Comparaciones reales y diferencias de renderizador documentadas. Selector nativo de carpeta, memoria portable, progreso estable y DPI125/150% siguen sin certificación.

Leer [estabilización](docs/11_UI_STABILIZATION_REPORT.md), [desktop real](docs/12_DESKTOP_SMOKE_REPORT.md), [matriz de regresión](docs/13_UI_REGRESSION_MATRIX.md), [handoff fiscal](docs/14_HANDOFF_MOTOR_FISCAL.md) y [procedimiento reproducible](scripts/spec011/README.md). Checkpoint previo `spec011-start-20261106`; checkpoint final/bundle local en `build/checkpoints/SPEC011_RESTORE_POINT.json`. No hay remotos ni subidas.

## Historial — FASE 0

La primera entrega fue exclusivamente auditoría. Sus documentos y resultados se conservan como evidencia histórica.

Leer [reporte de fase](docs/FASE_0_REPORTE.md), [auditoría](docs/00_AUDITORIA_LEGACY.md), [inventario](docs/01_INVENTARIO_FUNCIONAL.md), [riesgos](docs/02_MATRIZ_DE_RIESGOS.md), [plan/arquitectura](docs/03_PLAN_DE_MIGRACION.md), [contratos visuales](docs/04_CONTRATOS_UI.md) y [backlog](docs/05_BACKLOG_PRIORIZADO.md).

## Reproducir diagnósticos

Requiere Python3.11+ y Node24 (versiones observadas en este entorno); usa sólo bibliotecas estándar, sin instalar paquetes ni subir documentos.

```powershell
python scripts/audit_legacy.py
node --check tests/audit/evidence/script-01.js
node --check tests/audit/evidence/script-02.js
node tests/audit/run_node.cjs
python scripts/render_function_inventory.py
python scripts/verify_audit.py
```

Las26 observaciones comprueban lógica del legado, incluidos errores esperados. XML usa un adaptador de nodos ElementTree; UI está simulada. No certifican reglas SAT, DOMParser real, navegación ni fidelidad visual. Evidencia en `tests/audit/evidence/`; XLSX de diagnóstico sintético, sin datos de clientes.

## Continuación FASE 0.5 + FASE 1

El acceso visual se recuperó mediante servidor HTTP sólo local en127.0.0.1. **FASE0.5: DONE (recuperación y checkpoint). FASE1: PARTIAL.** Hay60 imágenes auténticas congeladas en `tests/visual/baseline/`, con hashes y metadatos.78 comprobaciones de navegación:70 PASS y8 FAIL que documentan defectos preexistentes. No se corrigió el motor fiscal ni se rediseñó la interfaz.

Leer [baseline y resultados](docs/07_BASELINE_VISUAL.md), [matriz de55 controles](docs/08_MATRIZ_COMPATIBILIDAD_UI.md), [contenedor desktop](docs/09_ARQUITECTURA_DESKTOP.md), [siguiente etapa del motor](docs/10_PLAN_RECONSTRUCCION_MOTOR.md) y [reporte de entrega](docs/FASE_0_5_FASE_1_REPORTE.md).

Procedimiento Windows en [scripts/visual/README.md](scripts/visual/README.md). Quedan pendientes carpeta/memoria reales, progreso estable, DPI real Windows y ejecución Qt. `python -m app.desktop_smoke --check` informa PySide6 ausente: el código de shell entregado no es un contenedor probado ni un EXE.

Git conserva el checkpoint de FASE0 y el de esta etapa, sin remotos. `.gitattributes` protege los bytes contra conversión de finales de línea. El punto final de restauración y su bundle local se describen en `build/checkpoints/RESTORE_POINT.json` (archivos de entrega fuera del versionado para evitar incluir el propio bundle en su historia).
