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

**Estado: FASE0 PARTIAL / BLOCKED_VISUAL_BASELINE.** Falta probar el prototipo visualmente mediante una vía local permitida; el navegador integrado bloqueó file://. Siguiente fase: congelamiento visual en tres resoluciones y DPI registrado, con revisión antes de cambiar código de producto.
