# Reporte de entrega — FASE 0

**FASE:** 0 — Auditoría integral del HTML V21.1.

**ESTADO:** PARTIAL. Se entregan los seis documentos requeridos, la matriz de conservación, el inventario de funciones y la propuesta de arquitectura. La revisión visual y navegación real no se ejecutaron por `BLOCKED_VISUAL_BASELINE`; las hipótesis de UI quedan abiertas. No es una certificación del producto.

**ALCANCE:** exclusivamente auditoría, preservación, extracción de referencias, diagnósticos de lógica y plan por fases, conforme al apartado16 del adjunto. No se reemplazó motor, rediseñó interfaz ni generó EXE.

**ARCHIVOS:** original preservado; copia en `legacy/`; recursos en `assets/legacy/`; docs00–05; scripts de inventario/verificación; pruebas y evidencia en `tests/audit/`. No había Git en el directorio; no se creó historial ficticio.

**CAMBIOS:** 242 declaraciones nombradas inventariadas, 28 nombres repetidos, 68 asignaciones de función y 83 elementos con ID. Extraídos cinco CSS, un logo repetido cuatro veces y 18 familias de catálogos. Identificadas implementaciones efectivas DOM V19/V20 y asignaciones V21. No se asumió que la primera función encontrada fuera la activa.

**PRUEBAS:**

| Comando/acción | Resultado | Evidencia |
|---|---|---|
| `python scripts/audit_legacy.py` | Hash original=legacy, extracción | inventory.json |
| `node --check tests/audit/evidence/script-01.js` | Sintaxis válida | Comando ejecutado sin errores. |
| `node --check tests/audit/evidence/script-02.js` | Sintaxis válida | Comando ejecutado sin errores. |
| `node tests/audit/run_node.cjs` |26 observaciones reproducidas, incluidas fallas esperadas del legado | node-results.json |
| `python scripts/render_function_inventory.py` | Índice léxico completo en documento01 | Documento01 y inventory.json |
| `python scripts/verify_audit.py` | Hashes/documentos, ZIP CRC y9 partes XML, tipos y hoja vacía; control inválido reproducido | verification.json, synthetic-export.xlsx, invalid-control-cell.xml |
| Edge headless / navegador integrado | Sin DOM / file:// rechazado por política | execution-limitations.json |

Los diagnósticos ejecutan código original en VM Node con UI simulada y XML adaptado desde ElementTree. No son pruebas E2E, XSD ni validación SAT. El XLSX sintético fue inspeccionado como ZIP/XML; no se abrió en Excel. Los probes de navegador preparados no llegaron a ejecutarse y se retiraron para no confundirlos con evidencia.

**RIESGOS:** importes IVA/IEPS mezclados, retenciones ignoradas en análisis, locales duplicados, exento contado como tasa0 y float monetario reproducidos. Abiertos riesgos de caché por firma, persistencia de incidentes, ZIP y bloqueo UI. No hay soporte integral demostrado de Nómina/revisiónE ni Carta Porte3.1.

**REGRESIONES:** ninguna modificación en el HTML original, verificada por SHA256. No hay nueva versión de aplicación que comparar. No se afirma que el prototipo esté libre de errores visuales o funcionales.

**SIGUIENTE PASO:** revisión de este punto de control; iniciar FASE1 con vía visual local permitida, fixtures anónimos y capturas a1366×768,1600×900,1920×1080 con DPI/zoom registrados; verificar navegación, filtros/editor/visor antes de separar archivos o conectar backend. Detalle en03 y04.

## Trazabilidad de requisitos de la primera ejecución

| Requisito | Entregable | Evidencia/prueba |
|---|---|---|
| P0 original intacto/hash | legacy/,00 | inventory.json,verify_audit |
| Extraer visuales | assets/legacy/,04 | Hashes CSS/PNG, manifest |
| Inventario funcional/funciones | 01 | 242 declaraciones, asignaciones y21 reportes |
| Hallazgo A superposiciones | 00 secciónA | N01,N26 y mapa de resolución |
| Hallazgos B/C dinero/impuestos | 00 seccionesB/C,02 | N02–N08 |
| Hallazgo D caché | 00 secciónE,02 C01–06 | N09; riesgos de IDB explícitamente no reproducidos |
| Hallazgo E exportaciones | 00 secciónF,02 E01–08 | N14–18,ZIP/XML y control inválido |
| Hallazgo F integridad | 00 seccionesD/E/F | N10,N21,N23–25, revisión process/readErrors |
| Matriz de riesgos P0–P3 | 02 | Cada fila distingue EC/RC/HP/NC |
| Arquitectura justificada/plan | 03 | Alternativas, contratos, entidades y puertas |
| Conservación visual | 04 | Matriz de escenas; bloqueo declarado sin imágenes inventadas |
| Backlog priorizado | 05 | Tareas/aceptación y estado AC01–18 |
| Checkpoint sin EXE/rediseño | Este reporte y README | Original idéntico; no app nueva ni binario |

FASE 0: PARTIAL
