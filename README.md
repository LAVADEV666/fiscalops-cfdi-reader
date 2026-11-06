# FiscalOps CFDI Reader — auditoría V21.1

Esta entrega corresponde exclusivamente a **FASE 0** del megaprompt. El prototipo original está intacto y tiene copia verificable en `legacy/`. No se ha reconstruido la aplicación ni generado EXE.

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
