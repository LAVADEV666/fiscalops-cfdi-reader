# SPEC 011 — Estabilización UI V21.1

**FASE 1.1: DONE.** Se corrigieron los cinco defectos solicitados en una copia de desarrollo, con pruebas antes/después y comparación visual real. No se modificaron original, legacy ni las60 referencias congeladas. Checkpoint previo: etiqueta `spec011-start-20261106`, commit `6dec03fbbe5ce078eddbad9b8e3e7fd68929e767`, bundle previo verificado.

## Código y conservación

El frontend de desarrollo está en `app/ui/index.html`, con `legacy-runtime.js`, `v20-runtime.js` y el módulo fuente `column-editor.js`. `scripts/spec011/build_ui.py` lo reproduce desde el original de SHA256 `33eeed2334a683b5360c2fc4f9cabc26885be66fef8714e4278f97235b8c373b`. El constructor sólo permite cambios en líneas originales539,685,1103,1127–1131,1175–1177 y la separación de scripts. Conserva los cinco bloques CSS y los recursos embebidos. El puente diagnóstico adicional no introduce controles visuales.

`development-build.json` registra hashes de salida y comprueba que los bloques fiscales L618–626,L634–666,L973–1020,L1021–1044 permanecen idénticos dentro de la copia. Incluyen ambos lectores, análisis monetario, impuestos, nómina/pagos, proceso de importación y ZIP. No se corrigieron errores fiscales ni se cambió el modelo documental. La validación general comprueba además los60 hashes de imágenes y el hash del manifest original contra Git.

## Causas reales y correcciones

| Requisito | Causa reproducida | Corrección en el propietario | Evidencia |
|---|---|---|---|
| P0-A | L685 addEventListener coexistía con onclick de setupFilters L1085; setActiveType alternaba dos veces. | Eliminada la delegación duplicada en la copia; setupFilters es el único propietario del clic. Sin debounce ni bloqueo temporal. | El original termina sin tipo; desarrollo termina en I. PUE permanece activo.48/48 históricos. |
| P0-B | Guardar reconstruía selección desde checks renderizados tras filtrar; onchange modificaba visibleCols aplicado. | Borrador separado: available,selected,search,profile. visibleCols/activeProfile/preferencias sólo cambian al aplicar. La selección conserva orden. | Búsquedas sucesivas, clear, selección oculta, cancelar, perfiles, recarga y exportación;62/62 específicos. |
| P0-C | Modal era overlay visual sin contención de teclado ni fondo inerte. | Un controlador de diálogo administra focusables actuales, wrap de Tab/ShiftTab, focusin defensivo y atributos inert reversibles en ramas del fondo. | Navegador y teclado Qt real. Pasa contención con búsqueda, checks y botones, incluso después de redimensionar. |
| P0-D | Cierre sólo quitaba claseon, sin recordar invocador; coexistían descartes V19/V20. | Se guarda event.currentTarget en cada apertura y se restaura si está conectado, visible y habilitado. Se retiraron cierres de editor ajenos a su controlador. | Apertura repetida desde editcols y editcolsTop, aplicar/cerrar/Escape;30/30 históricos. |
| P1-E | Timeout inicial ejecutaba pg(2) incondicionalmente tras una navegación legítima rápida. | pg cancela el timer pendiente; la transición automática verifica que sigue en s1. Sin interacción, conserva1600ms y animaciones originales. | Mismo escenario temprano: original vuelveas2, desarrollo permaneceens3; splash automático sigue funcionando. |

El módulo no modifica el HTML/CSS del editor: conserva tarjetas, cuadrantes, textos, clases y rótulos. Abrir crea borrador; buscar sólo filtra la presentación; los presets reemplazan el borrador sin mezclarse; todas/ninguna no cambian el aplicado. Cerrar, fondo o Escape descartan. Aplicar valida no vacío, guarda el perfil correspondiente y actualiza pantalla/exportación desde visibleCols. Una búsqueda vacía no selecciona campos ni restablece todas las columnas.

El aislamiento de fondo respeta el valor inert anterior y recorre hermanos de los ancestros del modal, sin volver inerte el contenedor que lo aloja. No se fija siempre el foco a un botón concreto. El controlador usa el conjunto de controles visibles/habilitados del momento, evitando referencias a checkboxes eliminados por búsqueda. El cierre del editor no cierra accidentalmente otros diálogos.

## Pruebas y resultados

| Conjunto | Antes | Después | Archivo |
|---|---|---|---|
| Navegación histórica |42 PASS/6 FAIL |48 PASS/0 FAIL | tests/spec011/browser/evidence/navigation.json |
| Controles históricos |28 PASS/2 FAIL |30 PASS/0 FAIL | tests/spec011/controls/controls.json |
| Cinco defectos concretos |5 reproducciones FAIL en original |Mismos escenarios PASS | tests/spec011/targeted/results.json |
| Regresión ampliada |Escenarios nuevos además de los anteriores |62 PASS/0 FAIL | mismo results.json |
| Contenedor Windows |Antes ausente |30 PASS/0 FAIL | tests/spec011/qt/smoke.json |

La única adaptación de secuencia en los48 casos conserva la aserción de tipo: como el clic ahora activa I, después de fotografiarlo se desactiva explícitamente para que los casos siguientes conserven su ámbito histórico sin filtro. No se eliminó ni suavizó la comprobación fallida. Se añadió opción `--strict` a los runners históricos para salida no exitosa si un check falla; los datos históricos quedan intactos.

En controles se mantienen las30 expectativas, incluida restauración a editcolsTop y Shift+Tab. La suite ampliada prueba no escribir preferencias en borrador, cancelar selecciones, perfiles aislados, ninguna+clear, alerta de vacío, orden aplicado, encabezados exportados, ambos invocadores en tres ciclos y editor a las tres resoluciones. La exportación XLSX se abre estructuralmente para comparar encabezados con la tabla aplicada; no se comparan importes fiscales.

Los primeros intentos detectaron una declaración de v21Preset omitida durante la separación y un ajuste de viewport por el área disponible de Windows. Se corrigieron y repitieron las pruebas. JSON de intentos en `tests/spec011/attempts/`; no cuentan como aprobación. La compilación de sintaxis por sí sola no fue criterio de cierre.

## Comparación visual y aceptación

Se compararon54 PNG estables contra la baseline preservada, además de18 parejas original/desarrollo con el mismo Chromium151 y fases equivalentes de animación. En estas18 parejas la diferencia medida fue **0 píxeles** con pixelmatch threshold0.1 y exclusión de antialias. No se deduce identidad universal de renderizado a partir de esa medición.

Frente a la baseline histórica con animaciones en marcha, las escenas sin cambio funcional tuvieron diferencia máxima **0.273%**. Las escenas05 (tipo activo) y14 (selección conservada) presentan cambios de estado esperados y están etiquetadas; no se reemplazó la baseline para ocultarlos.

Se capturaron también36 imágenes nativas Qt (original/desarrollo, seis escenas×tres tamaños), con18 diffs. Máximo mismo Qt: **0.230%**, localizado en iconos/animaciones y rasterización; editor, visor y constructor permanecieron en0% en las tres resoluciones. Inspección visual y diffs en `qt-visual/`. Entre QtWebEngine140 y la baseline Chromium151 hay hasta **6.846%** de píxeles distintos en tablas, principalmente scrollbars nativos, métricas y rasterización. Se conserva y documenta esa diferencia; no se presenta como fidelidad100%. La identidad visual y disposición se consideran conservadas en el alcance probado: no hay nuevos paneles, controles ocultados o modales cortados introducidos por el cambio.

La conclusión usa capturas y medidas reales, además del contrato CSS preservado. No hubo revisión basada únicamente en CSS ni modificación de las imágenes originales.

## Límites

Los P0 fiscales de02 continúan abiertos. Carpetas nativas, reconexión, memoria portable y captura de progreso estable siguen sin certificación; el lote de2000 sí completó en Qt. El entorno nativo probado usa DPI lógico96 y DPR1;125/150% no se ensayaron. No hay EXE final, certificación SAT ni promesa de funcionamiento en todo Windows.
