# Integración Qt con motor fiscal y workers — entrega

**Implementada y probada en Windows dentro de este alcance.** El flujo Qt deja de ejecutar el parser y cálculos monetarios JavaScript. Los reportes, visor y exportaciones reciben las filas y sumas del motor Python/Decimal. No se declara el proyecto fiscal completo ni certificación SAT.

## Cambio concreto

Antes: Qt alojaba la interfaz, pero File.text/DOMParser, impuestos, sumatorias y Excel seguían en el hilo del navegador con Number y caché antigua. Ahora: bytes seleccionados pasan por un puente acotado a un QObject en QThread; XML/XSD/Decimal, ZIP, metadata, reportes y generación de archivos se ejecutan allí. La UI sólo filtra/ordena identidades y presenta datos. Los puntos de entrada fiscales heredados están bloqueados en Qt; si falta Qt no se permite volver al legado.

F01–F06 llegan a la aplicación: IVA16/IEPS8 separados del agregado24; retención ISR10; total119 con local3 sin duplicación; exento y tasa0 separados; ausencia/invalidación conservadas y fallback conceptual trazable; cero y NULL distintos. Se mantienen valores reportados y recalculados. Los campos de motor, hash, XSD y recálculos pueden consultarse en Todos los datos y columnas opcionales.

## Experiencia preservada

Original, legacy y las60 referencias quedan intactos. HTML/CSS/branding, escalado y código del editor de columnas son byte a byte los del hito anterior. Se conservan22 reportes, cinco pestañas del visor, filtros, perfiles, ordenación, paginación, búsquedas y foco. Las descripciones de impuestos permanecen; nuevas columnas de procedencia/validación son opcionales. Los botones actuales muestran progreso/cancelación sin añadir una pantalla distinta.

La selección de carpeta se realiza con directory-input nativo de Chromium en Qt. Reabrir/actualizar pide nueva selección; no se promete permiso persistente. No se reutilizan cifras de IndexedDB/Number anteriores. La memoria del worker es de sesión y la carga nueva se publica completa al finalizar; cancelación/fallo conserva el reporte previo.

## Evidencia ejecutada

| Suite | Resultado | Qué acredita |
|---|---|---|
| Fiscal anterior |59/59 PASS | Regresión del lector y reglas Decimal I/E3.3/4.0; salida nueva separada de la evidencia histórica |
| Contratos de integración |28/28 PASS | Selección,22 reportes, complementos proyectados, nulos, monedas, ZIP/CRC, límites, Excel y puente mínimo |
| Ventana Qt real |34/34 PASS | Hilo distinto al GUI, heartbeat, importación, foco, visor, tres tamaños y descargas completadas |
| Jobs Qt reales |17/17 PASS | Carpeta, ZIP1000, progreso, cancelación, reintento, doble inicio y cierre activo |
| Navegación de referencia |48/48 PASS | Controles y escenas históricas a tres resoluciones |
| Controles de referencia |30/30 PASS | Ordenación, perfiles, reportes y exportaciones del frontend preservado |
| Regresiones UI de referencia |62/62 PASS | Editor, búsqueda, borrador, foco, timer y preferencias |
| Sin Qt |PASS | HTML de producción bloquea procesamiento/exportación; no descarga ni ejecuta fallback |

Qt6.12.0, plataforma windows, ventana nativa expuesta, DPI lógico96.0, DPR1.0. Los IDs reales del GUI y worker son diferentes y se registran en smoke.json. Cancelación observada: 0.063s; cierre con operación activa: 0.063s. Son mediciones de este lote sintético, no garantías para cualquier XML o máquina. No se usó modo offscreen, firewall modificado ni flags de desactivación de seguridad.

El progreso se capturó durante el ZIP: antes/después permanecían s2 y busy=true. La captura se acepta como pantalla de procesamiento real; los contadores dinámicos no se congelaron. Reintento terminó con1001 CFDI y total MXN124124.00. Cancelar no publicó staging ni generó una descarga.

Los tests de navegador se ejecutan en una referencia visual explícita del servidor QA, usando el flujo legado sólo para los contratos históricos. No acreditan cálculos del backend. Esas cifras se prueban por contratos y en la ventana Qt. `/without-native/` comprueba el bloqueo del HTML sin esa marca. El escritorio normal carga exclusivamente archivos locales, sin servidor HTTP.

## Excel, CSV y TXT reales

Se guardaron y reabrieron archivos a través del flujo nativo de descargas. Excel tiene8 hojas: Reporte, Resumen, Totales por moneda, Análisis mensual, Contrapartes, Formas y métodos, Análisis impuestos y Conceptos. Se revisan CRC y XML de todas las partes, columnas/tipos/estilos y valores: IVA16/16/0, retenciones0/0/10 y totales124/119/90. Un filtro CASE-1 exporta exactamente una fila, Total119. Los IDs y el orden coinciden con la selección mostrada.

Se conservan ceros, nulos, cifras exactas y protección de fórmulas. Más de15 cifras significativas se guardan como texto exacto para Excel. No se recortan filas en silencio. La apariencia conserva formato monetario de dos decimales de V21; los valores fuente/exportados conservan su precisión completa. No se afirma haber abierto el archivo mediante Microsoft Excel instalado.

## Comparación visual

36 capturas auténticas,18 parejas del mismo Qt con datos compatibles, a1366×768,1600×900 y1920×1080. Diferencia máxima0.005815% (pixelmatch umbral0.1, antialias excluido). Las diferencias de importes corregidos se prueban aparte, sin exigir conservar cifras defectuosas. Se inspeccionaron reporte, editor, visor e imágenes de diferencia; no se acepta una captura vacía como fidelidad.

| Escena |1366×768 |1600×900 |1920×1080 |
|---|---|---|---|
| upload | 0.000000% | 0.000000% | 0.005305% |
| report | 0.000000% | 0.000000% | 0.000000% |
| editor | 0.005815% | 0.005069% | 0.004823% |
| visor | 0.000000% | 0.000000% | 0.000000% |
| taxes | 0.000000% | 0.000000% | 0.000000% |
| excel | 0.000000% | 0.000000% | 0.000000% |

Se esperan pequeñas diferencias por campos opcionales añadidos en el contador del editor, elementos animados de carga y la variante Ingreso/Ingresos heredada entre original y copia estabilizada. Las animaciones finitas terminan naturalmente antes de capturar; sólo las infinitas se pausan en QA. Ningún PNG del baseline anterior se modifica.

## Fronteras y pendientes

Las reglas normativas siguen siendo las del motor independiente: I/E3.3/4.0 en su alcance P0. REP, nómina y Carta Porte conservan tablas/atributos y cálculos auxiliares Decimal, con reglas no cubiertas NO EVALUADO/PENDING. No se declara validación integral, firma, certificado, cancelación oficial ni derecho a deducción/acreditamiento.

Continúan pendientes SQLite/caché persistente, memoria portable, grants persistentes y actualización sin reselección, historia completa de catálogos, pruebas de Windows limpio/DPI125/150, rendimiento de50k y EXE final. Los límites de sesión/ZIP/exportación se describen en18 y se muestran como rechazo explícito; no certifican seguridad exhaustiva contra todo archivo adversarial.

La instalación actual usa requirements/desktop.txt (Qt y lxml fijados por hash en .venv). Procedimiento en scripts/integration/README.md; contrato en docs/18_CONTRATO_QT_WORKERS.md. La verificación final vincula hashes de aplicación con pruebas/capturas y comprueba las fuentes SAT originales. Se conserva un commit y bundle local nuevos, sin remotos ni subidas.
