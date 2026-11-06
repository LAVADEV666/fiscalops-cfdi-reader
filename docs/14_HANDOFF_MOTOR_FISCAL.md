# Handoff después de SPEC 011

La estabilización UI y el smoke desktop quedan implementados. El motor fiscal **no se reconstruyó**. Original, legacy y baseline permanecen intactos; el constructor de la copia de desarrollo comprueba regiones fiscales idénticas. La interfaz de desarrollo está en app/ui y el contenedor real en app/desktop/main.py.

## Riesgos que siguen abiertos

| Riesgo de02 | Situación al entregar |
|---|---|
| F01 IVA/IEPS | TotalImpuestosTrasladados sigue tratado como IVA en el legado. No corregido. |
| F02 retenciones | Etiquetas Retención/Retencion siguen incompatibles en análisis legado. No corregido. |
| F03 impuestos locales | Comprobación del total sigue pudiendo duplicarlos. No corregido. |
| F04 exento/tasa0 | Clasificación sigue pudiendo mezclar bases. No corregido. |
| F05 fallback | Suma conceptual/global defectuosa en documentos incompletos sigue en legado. |
| F06 Number/nulidad | Continúa cálculo monetario binario y conversión de ausencias a cero. |
| XML/caché/complementos | Namespaces, XSD, versiones, UUID/hash, metadata, seguridad y cobertura siguen sujetos al plan03/10. |

Los totales de capturas y fixtures sintéticos sólo sirven para UI. No son expectativas fiscales aceptadas. Los tests históricos que reproducen errores del motor deben convertirse en expectativas corregidas con fuentes, no perpetuarse para mantener porcentajes PASS.

## Propuesta concreta de siguiente fase

1. **Contrato XML/modelo de datos.** Acordar DTOs tipados con original, normalizado, moneda, precisión, nivel y NULL separados. Mantener CFDI/conceptos/impuestos/REP/nómina en relaciones1:N. El frontend continuará presentando los mismos controles, sin nuevas fórmulas fiscales en JavaScript.
2. **Anexo20 y fuentes.** Crear06_MATRIZ_NORMATIVA_SAT con XSD/XSLT/catálogos/matrices/guías oficiales, versiones, vigencias, URL/fecha/hash, caso y estado. Investigar revisión de nómina aplicable al periodo sin inferir soporte por etiqueta1.2. Si falta una descarga, dejar esa validación pendiente.
3. **Lector seguro por bytes y namespaces.** Parser estructurado con entidades externas deshabilitadas, límites, codificaciones, errores trazables y conservación de complementos no interpretados. Separar lectura/XML bien formado/XSD/reglas técnicas/estatus oficial.
4. **Decimal e impuestos.** Introducir Decimal en cálculos y contratos de importes. Separar reportado/recalculado y conceptual/global/local. Cerrar F01–F06 con pruebas normativamente sustentadas de tasas, exento, retenciones, monedas y redondeos. Nunca sumar representaciones del mismo impuesto dos veces.
5. **Conectar por hitos.** Probar el motor nuevo fuera de Qt, comparar datos y hallazgos, después exponer servicios mínimos por QWebChannel en workers. El puente actual sólo ofrece diagnóstico; no es una API fiscal ni de archivos nativos.

Antes de sustituir selección de carpeta o memoria, completar los contratos de12 con autorización nativa real, límites de acceso, progreso/cancelación y recuperación. Esa migración será independiente de reglas tributarias.

## Restricciones y aceptación siguiente

No cambiar branding, CSS o estructura visual para acomodar el backend. Reutilizar las60 referencias y las comparaciones de SPEC011; conservar pruebas de búsquedas, perfiles, foco, timer y los78 casos históricos ya corregidos. Ninguna lectura local prueba vigencia actual, deducibilidad o acreditamiento fiscal.

La siguiente fase debe terminar con fixtures verificados, diferencias explicables, matriz normativa y cero errores fiscales críticos en su alcance antes de ampliar soporte. No generar todavía EXE final ni declarar certificación SAT. El empaquetado Windows limpio/offline, otros DPI y licencias de distribución siguen correspondiendo a sus hitos posteriores.
