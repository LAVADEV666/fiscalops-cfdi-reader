# Plan de reconstrucción del motor — siguiente etapa técnica

Este documento prepara el trabajo siguiente; **no implementa ni corrige el motor fiscal**. El HTML original, su JavaScript y legacy permanecen intactos. Las capturas nuevas congelan apariencia, no importes fiscales. Siguen abiertos los P0 de02: IVA/IEPS mezclados, retenciones por etiqueta incompatible, locales duplicados, tasa0/exento y float/nulidad.

## Puerta de inicio de FASE 2

Completar carpeta/memoria, progreso estable y DPI real en la referencia; ejecutar el shell Qt con dependencias verificadas; aceptar contratos de UI y la matriz08. Después separar recursos en `app/ui` conservando orden CSS, identidad de funciones activas y renderizado. Comparar capturas por escena antes de sustituir servicios. Una suite que espere errores del legado no debe perpetuarlos como expectativas del motor nuevo.

Las tareas fiscales siguientes se ejecutarán por módulos y revisión, no en una reescritura monolítica. Las fases del megaprompt original siguen aplicando: arquitectura en2, XML/normativa en3, impuestos en4, complementos en5 y almacenamiento/importación en6. Llamar a la siguiente etapa «FASE2» no autoriza saltarse sus puertas de exactitud fiscal.

## Orden técnico y aceptación

| Orden | Módulo | Trabajo acotado | Prueba que autoriza avanzar |
|---|---|---|---|
| 1 | Contratos/datos | DTOs tipados, importe original/normalizado/calculado, moneda, precisión, NULL y niveles separados | Serialización sin float, cero y ausencia diferentes; filas1:N trazables. |
| 2 | Fuentes y reglas | Crear06_MATRIZ_NORMATIVA_SAT con regla, fuente oficial, versión, vigencia, URL/hash, prueba y estado | XSD/XSLT/catálogos descargados realmente; si faltan, validación pendiente explícita. |
| 3 | XML seguro | Lectura desde bytes con namespaces/versiones, codificación y límites; rechazo antes de normalizar | Malformado, DTD/entidades, profundidad/tamaño, namespaces falsos, UTF8/otras codificaciones, unknown complement preservado. |
| 4 | Cálculo Decimal | Aritmética por campo y tolerancia/escala respaldada por fuente versionada | Casos de redondeo, importes ausentes y moneda; valor original nunca alterado. |
| 5 | Impuestos | Separar conceptual/global/local, impuesto/factor/tasa y reportado/recalculado | Casos F01–F06 con expectativas CORREGIDAS, sin doble suma y sin declarar acreditamiento/deducibilidad. |
| 6 | REP | Pago/DoctoRelacionado/DR/P y totales por moneda | Múltiples pagos/docs, saldos, equivalencias y totalCFDI0 separado de importes de pagos. |
| 7 | Nómina | Lector por revisión/fecha con subestructuras y catálogos aplicables | Investigar revisiónE2026 con documentación técnica oficial; no asumirla soportada ni vigente por el nombre del complemento. |
| 8 | Carta Porte | Esquemas/versiones y relaciones por transporte | Declarar cobertura exacta, preservar nodos sin interpretar; no llamar soporte integral a extracción parcial. |
| 9 | Importación/caché | SHA256, UUID+contenido, versión parser/reglas, SQLite transaccional, fuentes metadata e incidentes | Cambio de mismo tamaño/fecha, carpetas homónimas, UUID conflictivo, fallos/reinicio y desconexión sin borrado. |
| 10 | Reportes/exportación | Una selección consultable para UI y export; biblioteca XLSX probada | Filas/totales reconciliados, fechas/texto/números, ceros, controles XML, límites, fórmulas y apertura real Excel. |
| 11 | Workers/recuperación | Progreso, cancelación, exclusión de trabajos y checkpoints | UI responde durante lote/export, cancelación segura y retomado sin pérdida. |

## Casos de regresión que deben convertirse

N02 debe producir IVA16 e IEPS8 separados, no IVA24. N03 debe clasificar retención ISR10. N04 debe reconciliar total119 sin sumar dos veces el local3. N06 debe mantener base exenta100 y no añadirla a tasa0. N07 debe señalar total global ausente y escoger una fuente trazable, no sumar concepto+global. N08 debe usar representación decimal exacta y preservar ausencia. Son ejemplos de diagnóstico sintético; la aceptación fiscal requiere además su correspondencia con esquema/reglas oficiales.

El motor local distinguirá XML bien formado, XSD, reglas técnicas, catálogo/vigencia, aritmética, consistencia, alertas preventivas y verificación oficial externa. No se conectará al SAT de forma implícita ni se simulará vigencia actual con metadata histórica. Reglas y catálogos deben versionarse para lectura histórica.

## Protección de la experiencia

Los servicios nuevos entregarán el mismo contrato de filas y eventos a una UI preservada. Corregir cálculos o foco/listeners no autoriza sustituir paneles, tipografía, paleta o modales. Toda funcionalidad oculta/heredada tendrá una decisión de conservación/sustitución, sin eliminarla por comodidad. El inventario de50 botones originales y5 pestañas dinámicas finales se usará como lista de regresión.

Antes de dar DONE al producto deberán aprobarse AC01–18 del megaprompt: esta etapa no los certifica. Quedan prohibidas afirmaciones de soporte fiscal integral, rendimiento masivo o portabilidad Windows basadas sólo en capturas y navegación del legado.
