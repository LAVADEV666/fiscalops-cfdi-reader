# Backlog priorizado y criterios de aceptación

Este backlog es una secuencia de trabajo, no una lista de funciones ya implementadas. FASE 0 preserva el original y entrega evidencias; la siguiente puerta es revisar baseline visual. Severidades y pruebas en02. Todas las tareas de producto están pendientes salvo A00–A02.

| Tarea | Fase / prioridad | Cambio concreto | Dependencia | Criterio y evidencia para cerrar |
|---|---|---|---|---|
| A00 | 0/P0 | Preservar original/legacy y hashes | HTML disponible | Hecho: copia byte a byte y manifest; verify_audit. |
| A01 | 0/P1 | Inventario código/riesgos/contratos | A00 | Hecho: seis documentos, inventario funciones/recursos y propuesta justificada. |
| A02 | 0/P1 | Reproducir lógica sin modificar prototipo | A00 | Hecho con límites:26 diagnósticos Node+adaptador XML; no UI/SAT. |
| V10 | 1/P1 | Habilitar vía visual local permitida | Revisión fase0 | Resolver BLOCKED_VISUAL_BASELINE sin rodear la política del navegador. |
| V11 | 1/P1 | Fixtures anónimos y escenas originales | V10 | Capturas/manifiesto de3 resoluciones y DPI real registrado. |
| V12 | 1/P1 | Reproducir filtros/editor/teclado/scroll | V11 | Un clic por tipo; búsqueda conserva selección; identificar defectos reales antes de cambios. |
| D20 | 2/P1 | Spike QtWebEngine/puente mínimo | Baseline revisada | Render comparable y APIs sustitutas de archivos/IndexedDB; medir tamaño/memoria/licencias. |
| D21 | 2/P1 | Módulos/contratos tipados y jobs | D20 | UI sin lógica fiscal, worker con progreso/cancelación; dependencias fijadas y offline. |
| D22 | 2/P1 | Esquema SQLite/migraciones | D21 | Transacción documento+hijos, incidentes e historial; rutas de datos escribibles y diagnóstico. |
| N30 | 3/P0 | Matriz normativa SAT oficial | Versiones por implementar | URL/fecha/hash/vigencia/regla/caso/estado por fuente; declarar descarga fallida, no inventar. |
| N31 | 3/P0 | XML por namespace/versión y bytes seguros | N30 | X01–X05: DTD/XXE, límites, codificaciones y malformed; rechazo trazable sin UI congelada. |
| N32 | 3/P1 | Campos y originales/nulos | N31 | Cobertura por atributos y nodos incluyendo global, sello/certificado; original inmutable. |
| F40 | 4/P0 | Decimal y precisión por campo | N30,N32 | F06: no float monetario; cero/nulo/ausente diferenciados; redondeo/tolerancia documentados. |
| F41 | 4/P0 | Modelo de impuestos por nivel/código | F40 | F01–F05 corregidos: IVA/IEPS, retenciones, locales, tasa0/exento y fallback. |
| F42 | 4/P1 | Hallazgos con evidencia normativa | F41 | Separar reportado/recalculado; no acreditar IVA/deducibilidad con XML únicamente. |
| C50 | 5/P1 | REP completo y relaciones | F41 | Múltiples pagos/docs, DR/P, equivalencias, totales MXN, saldos, pruebas de ausencia y conflictos. |
| C51 | 5/P1 | Nómina/versiones/revisiones | N30 | Investigar revisión E2026 con fuente oficial; catálogo/claves/vigencia; subestructuras y privacidad. |
| C52 | 5/P1 | Carta Porte con cobertura declarada | N30 | Cuatro modos sólo cuando implementados/probados; relaciones completas; unknown no descartado. |
| C53 | 5/P2 | Plugins de complementos | N31 | Contrato versionado y estado NO INTERPRETADO con XML intacto para no soportados. |
| I60 | 6/P0 | ZIP seguro y entradas trazables | D21,N31 | Z01–Z03: CRC/tamaño real/ratio/rutas, métodos soportados, fallos parciales contabilizados. |
| I61 | 6/P0 | Hash/cache/parser/reglas | D22 | C01–C06: cambio igual tamaño/fecha, carpetas iguales, duplicados/conflictos, eliminados/desconectados, reindex. |
| I62 | 6/P1 | Metadata con historia/fuentes | D22 | M01–M03: UUID validado, encabezados preservados, fechas y conflictos, estado local explícito. |
| R70 | 7/P1 | Consultas paginadas y selección compartida | D22,I61 | UI/export comparten selección; totales por moneda/reporte reconciliados con filas. |
| R71 | 7/P1 | Editor/perfiles/fechas | V12,R70 | U01–U07 corregidos; no selección perdida ni listeners dobles; orden cronológico y preferencias. |
| R72 | 7/P1 | Hallazgos accesibles/visor | F42,R70 | U04/U08: reporte y acceso al detalle sin eliminar experiencia V21; datos de reglas legibles. |
| E73 | 7/P1 | XLSX probado vía biblioteca | R70 | E01–E07: tipos/fechas/ceros, límites, control XML, hojas vacías, fórmula, progreso/cancelación y apertura Excel real. |
| E74 | 7/P2 | CSV/TXT y rutas heredadas | E73 | E04/E08: roundtrip o pérdida explícita, sin ceros perdidos; reemplazos de XLS ocultos documentados. |
| Q80 | 8/P1 | Pruebas de integración/seguridad/recuperación | N31,I60,I61,E73 | Archivos corruptos, cancelación/reinicio y logs sin datos personales; operación offline observada. |
| Q81 | 8/P2 | Benchmarks reproducibles | Q80 | 100/1k/10k/50k y mixtos, tiempo/memoria/latencia/export; comparación legado donde ejecutable. |
| B90 | 9/P1 | Build portable reproducible | Fases2–8 | PowerShell/spec/lock/licencias; EXE+ZIP y SHA reales; no permisos administrador. |
| B91 | 9/P1 | Windows limpio/offline/DPI | B90 | Sin Python/Node, espacios/acentos, directorio no escribible, requisitos gráficos; registro verificable. |
| A100 | 10/P0 | Revisión final AC01–18 | Todo anterior | Evidencia completa, cero P0 y auditoría de diferencias; sólo entonces DONE global. |

## Criterios globales: situación al terminar FASE 0

| Criterio | Situación actual y evidencia faltante |
|---|---|
| AC01–02 visual/navegación | PENDIENTE/BLOCKED_VISUAL_BASELINE. No hay app reconstruida ni capturas comparativas. |
| AC03 XML estructurado/seguro | Parcial en legado: DOMParser/hijos; namespaces y seguridad completa pendientes. |
| AC04 fixtures oficiales/normativos | PENDIENTE. Diagnósticos actuales deliberadamente sintéticos, no certificados XSD. |
| AC05–06 precisión/no duplicación | Defectos reproducidos F01–F06; abiertos. |
| AC07 pagos múltiples | Comportamiento parcial observado N11; reglas integrales pendientes. |
| AC08 nómina | Lectura parcial por código; revisión y cobertura sin validar. |
| AC09–10 metadata/caché | Defectos/riesgos M01–03 y C01–06 abiertos. |
| AC11 reportes/filtros | Varias rutas presentes, alcance y navegación pendientes. |
| AC12 XLSX | ZIP/XML de ejemplo comprobados; límites/controles/fechas/apertura real pendientes. |
| AC13 importación responsiva | Sin worker ni benchmark; pendiente. |
| AC14 recuperación | Incidentes de sesión presentes; persistencia y reinicio pendientes. |
| AC15 privacidad/offline | Inspección estática; falta prueba en ejecución offline y política de datos. |
| AC16 portable probado | NO CONSTRUIDO por alcance de esta fase; no se declara BLOCKED_WINDOWS_BUILD sin intentar fase9. |
| AC17 reproducibilidad | Auditoría reproducible con stdlib/Node; producto desktop pendiente. |
| AC18 sin P0 | NO CUMPLE en legado; matriz02 registra P0 abiertos. |

## Punto de control

Revisar errores confirmados y límites de la evidencia, aprobar las escenas y el procedimiento de FASE 1 y resolver acceso visual permitido antes de escribir código de producto. No hace falta autorización adicional para las comprobaciones reversibles de esta auditoría ya solicitada; la pausa de alcance proviene de la instrucción expresa «Comienza ahora exclusivamente con FASE0» del megaprompt, no de una decisión técnica de detener una reconstrucción autorizada.
