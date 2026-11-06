# SPEC 011 — Matriz de regresión UI

Resultados reales. PASS de navegación no certifica cálculos fiscales. Original/legacy/baseline preservados. Los cinco FAIL previos se reproducen por separado; los intentos de implementación fallidos no se confunden con resultados finales.

## Casos históricos conservados

Las48 expectativas de navegación y las30 de controles se mantienen. El único ajuste de secuencia restablece el tipo después de comprobar su clic corregido, para conservar el ámbito sin filtro de los siguientes casos.

### Navegación

| Caso | Antes | Después | Expectativa conservada |
|---|---|---|---|
| start-1366 | PASS | PASS | Sí |
| empty-process-disabled-1366 | PASS | PASS | Sí |
| selected-process-enabled-1366 | PASS | PASS | Sí |
| table-has-rows-1366 | PASS | PASS | Sí |
| report-filter-single-click-1366 | FAIL | PASS | Sí |
| empty-filter-1366 | PASS | PASS | Sí |
| viewer-tab-impuestos-1366 | PASS | PASS | Sí |
| viewer-tab-conceptos-1366 | PASS | PASS | Sí |
| viewer-tab-datos-1366 | PASS | PASS | Sí |
| viewer-tab-xml-1366 | PASS | PASS | Sí |
| viewer-escape-1366 | PASS | PASS | Sí |
| column-search-preserves-selection-1366 | FAIL | PASS | Sí |
| xlsx-download-1366 | PASS | PASS | Sí |
| corrupt-xml-visible-1366 | PASS | PASS | Sí |
| clear-disables-process-1366 | PASS | PASS | Sí |
| progress-completes-1366 | PASS | PASS | Sí |
| start-1600 | PASS | PASS | Sí |
| empty-process-disabled-1600 | PASS | PASS | Sí |
| selected-process-enabled-1600 | PASS | PASS | Sí |
| table-has-rows-1600 | PASS | PASS | Sí |
| report-filter-single-click-1600 | FAIL | PASS | Sí |
| empty-filter-1600 | PASS | PASS | Sí |
| viewer-tab-impuestos-1600 | PASS | PASS | Sí |
| viewer-tab-conceptos-1600 | PASS | PASS | Sí |
| viewer-tab-datos-1600 | PASS | PASS | Sí |
| viewer-tab-xml-1600 | PASS | PASS | Sí |
| viewer-escape-1600 | PASS | PASS | Sí |
| column-search-preserves-selection-1600 | FAIL | PASS | Sí |
| xlsx-download-1600 | PASS | PASS | Sí |
| corrupt-xml-visible-1600 | PASS | PASS | Sí |
| clear-disables-process-1600 | PASS | PASS | Sí |
| progress-completes-1600 | PASS | PASS | Sí |
| start-1920 | PASS | PASS | Sí |
| empty-process-disabled-1920 | PASS | PASS | Sí |
| selected-process-enabled-1920 | PASS | PASS | Sí |
| table-has-rows-1920 | PASS | PASS | Sí |
| report-filter-single-click-1920 | FAIL | PASS | Sí |
| empty-filter-1920 | PASS | PASS | Sí |
| viewer-tab-impuestos-1920 | PASS | PASS | Sí |
| viewer-tab-conceptos-1920 | PASS | PASS | Sí |
| viewer-tab-datos-1920 | PASS | PASS | Sí |
| viewer-tab-xml-1920 | PASS | PASS | Sí |
| viewer-escape-1920 | PASS | PASS | Sí |
| column-search-preserves-selection-1920 | FAIL | PASS | Sí |
| xlsx-download-1920 | PASS | PASS | Sí |
| corrupt-xml-visible-1920 | PASS | PASS | Sí |
| clear-disables-process-1920 | PASS | PASS | Sí |
| progress-completes-1920 | PASS | PASS | Sí |

### Controles

| Caso | Antes | Después | Expectativa conservada |
|---|---|---|---|
| filechooser | PASS | PASS | Sí |
| next-page | PASS | PASS | Sí |
| previous-page | PASS | PASS | Sí |
| density | PASS | PASS | Sí |
| received-origin | PASS | PASS | Sí |
| cancelled-status | PASS | PASS | Sí |
| vigente-status | PASS | PASS | Sí |
| method-PUE | PASS | PASS | Sí |
| method-PPD | PASS | PASS | Sí |
| page-size | PASS | PASS | Sí |
| year-month | PASS | PASS | Sí |
| sort-header | PASS | PASS | Sí |
| row-enter | PASS | PASS | Sí |
| preview-close | PASS | PASS | Sí |
| column-initial-focus | PASS | PASS | Sí |
| modal-keyboard-containment | FAIL | PASS | Sí |
| preset-recommended | PASS | PASS | Sí |
| preset-fiscal | PASS | PASS | Sí |
| preset-audit | PASS | PASS | Sí |
| preset-taxes | PASS | PASS | Sí |
| preset-all | PASS | PASS | Sí |
| preset-none | PASS | PASS | Sí |
| empty-columns-alert | PASS | PASS | Sí |
| columns-close | PASS | PASS | Sí |
| columns-focus-restored | FAIL | PASS | Sí |
| export-close | PASS | PASS | Sí |
| export-cancel | PASS | PASS | Sí |
| export-escape | PASS | PASS | Sí |
| download-csv | PASS | PASS | Sí |
| download-txt | PASS | PASS | Sí |

## Reproducciones antes/después

| Defecto | Original | Desarrollo |
|---|---|---|
| P1-E-no-late-navigation | FAIL: s2 | PASS |
| P0-A-single-transition | FAIL: None | PASS |
| P0-B-search-apply-keeps-selection | FAIL: False | PASS |
| P0-C-focus-contained | FAIL: False | PASS |
| P0-D-invoker-restored | FAIL: colSearch | PASS |

## Regresión ampliada

| Caso | Resultado | Evidencia |
|---|---|---|
| initial-race-precondition | PASS | tests/spec011/targeted/results.json |
| P1-E-no-late-navigation | PASS | tests/spec011/targeted/results.json |
| automatic-splash-preserved | PASS | tests/spec011/targeted/results.json |
| P0-A-single-transition | PASS | tests/spec011/targeted/results.json |
| other-filter-preserved | PASS | tests/spec011/targeted/results.json |
| P0-B-search-apply-keeps-selection | PASS | tests/spec011/targeted/results.json |
| P0-C-focus-contained | PASS | tests/spec011/targeted/results.json |
| P0-D-invoker-restored | PASS | tests/spec011/targeted/results.json |
| apply-without-reordering | PASS | tests/spec011/targeted/results.json |
| draft-does-not-change-applied | PASS | tests/spec011/targeted/results.json |
| draft-does-not-save-preferences | PASS | tests/spec011/targeted/results.json |
| draft-does-not-change-profile | PASS | tests/spec011/targeted/results.json |
| successive-search-UUID | PASS | tests/spec011/targeted/results.json |
| successive-search-RFC | PASS | tests/spec011/targeted/results.json |
| successive-search-NOT-A-COLUMN | PASS | tests/spec011/targeted/results.json |
| successive-search-empty | PASS | tests/spec011/targeted/results.json |
| clearing-search-restores-selected-option | PASS | tests/spec011/targeted/results.json |
| cancel-keeps-applied | PASS | tests/spec011/targeted/results.json |
| cancel-keeps-preferences | PASS | tests/spec011/targeted/results.json |
| cancel-discards-uncommitted-option | PASS | tests/spec011/targeted/results.json |
| apply-keeps-hidden-new-option | PASS | tests/spec011/targeted/results.json |
| manual-selection-is-custom | PASS | tests/spec011/targeted/results.json |
| saved-profile-survives-reload | PASS | tests/spec011/targeted/results.json |
| profile-replaces-not-merges | PASS | tests/spec011/targeted/results.json |
| profile-draft-is-not-applied | PASS | tests/spec011/targeted/results.json |
| profile-applied-explicitly | PASS | tests/spec011/targeted/results.json |
| profile-preferences-isolated | PASS | tests/spec011/targeted/results.json |
| empty-search-does-not-select-all | PASS | tests/spec011/targeted/results.json |
| empty-apply-does-not-commit | PASS | tests/spec011/targeted/results.json |
| initial-focus-editcols-0 | PASS | tests/spec011/targeted/results.json |
| tab-wrap-editcols-0 | PASS | tests/spec011/targeted/results.json |
| shift-tab-wrap-editcols-0 | PASS | tests/spec011/targeted/results.json |
| background-inert-editcols-0 | PASS | tests/spec011/targeted/results.json |
| restore-editcols-0 | PASS | tests/spec011/targeted/results.json |
| initial-focus-editcols-1 | PASS | tests/spec011/targeted/results.json |
| tab-wrap-editcols-1 | PASS | tests/spec011/targeted/results.json |
| shift-tab-wrap-editcols-1 | PASS | tests/spec011/targeted/results.json |
| background-inert-editcols-1 | PASS | tests/spec011/targeted/results.json |
| restore-editcols-1 | PASS | tests/spec011/targeted/results.json |
| initial-focus-editcols-2 | PASS | tests/spec011/targeted/results.json |
| tab-wrap-editcols-2 | PASS | tests/spec011/targeted/results.json |
| shift-tab-wrap-editcols-2 | PASS | tests/spec011/targeted/results.json |
| background-inert-editcols-2 | PASS | tests/spec011/targeted/results.json |
| restore-editcols-2 | PASS | tests/spec011/targeted/results.json |
| initial-focus-editcolsTop-0 | PASS | tests/spec011/targeted/results.json |
| tab-wrap-editcolsTop-0 | PASS | tests/spec011/targeted/results.json |
| shift-tab-wrap-editcolsTop-0 | PASS | tests/spec011/targeted/results.json |
| background-inert-editcolsTop-0 | PASS | tests/spec011/targeted/results.json |
| restore-editcolsTop-0 | PASS | tests/spec011/targeted/results.json |
| initial-focus-editcolsTop-1 | PASS | tests/spec011/targeted/results.json |
| tab-wrap-editcolsTop-1 | PASS | tests/spec011/targeted/results.json |
| shift-tab-wrap-editcolsTop-1 | PASS | tests/spec011/targeted/results.json |
| background-inert-editcolsTop-1 | PASS | tests/spec011/targeted/results.json |
| restore-editcolsTop-1 | PASS | tests/spec011/targeted/results.json |
| initial-focus-editcolsTop-2 | PASS | tests/spec011/targeted/results.json |
| tab-wrap-editcolsTop-2 | PASS | tests/spec011/targeted/results.json |
| shift-tab-wrap-editcolsTop-2 | PASS | tests/spec011/targeted/results.json |
| background-inert-editcolsTop-2 | PASS | tests/spec011/targeted/results.json |
| restore-editcolsTop-2 | PASS | tests/spec011/targeted/results.json |
| resize-editor-1366 | PASS | tests/spec011/targeted/results.json |
| resize-editor-1600 | PASS | tests/spec011/targeted/results.json |
| resize-editor-1920 | PASS | tests/spec011/targeted/results.json |

## Escritorio Windows real

| Caso | Resultado | Evidencia |
|---|---|---|
| real-windows-platform | PASS | tests/spec011/qt/smoke.json |
| real-window-exposed | PASS | tests/spec011/qt/smoke.json |
| channel-handshake | PASS | tests/spec011/qt/smoke.json |
| channel-ping | PASS | tests/spec011/qt/smoke.json |
| resources-loaded | PASS | tests/spec011/qt/smoke.json |
| viewport-1366 | PASS | tests/spec011/qt/smoke.json |
| viewport-1600 | PASS | tests/spec011/qt/smoke.json |
| viewport-1920 | PASS | tests/spec011/qt/smoke.json |
| maximize | PASS | tests/spec011/qt/smoke.json |
| file-input-via-qt | PASS | tests/spec011/qt/smoke.json |
| table-rendered | PASS | tests/spec011/qt/smoke.json |
| single-type-click | PASS | tests/spec011/qt/smoke.json |
| initial-focus-editcols | PASS | tests/spec011/qt/smoke.json |
| shift-tab-editcols | PASS | tests/spec011/qt/smoke.json |
| escape-restores-editcols | PASS | tests/spec011/qt/smoke.json |
| initial-focus-editcolsTop | PASS | tests/spec011/qt/smoke.json |
| shift-tab-editcolsTop | PASS | tests/spec011/qt/smoke.json |
| escape-restores-editcolsTop | PASS | tests/spec011/qt/smoke.json |
| export-modal | PASS | tests/spec011/qt/smoke.json |
| viewer-modal | PASS | tests/spec011/qt/smoke.json |
| viewer-tab-impuestos | PASS | tests/spec011/qt/smoke.json |
| viewer-tab-conceptos | PASS | tests/spec011/qt/smoke.json |
| viewer-tab-datos | PASS | tests/spec011/qt/smoke.json |
| viewer-tab-xml | PASS | tests/spec011/qt/smoke.json |
| viewer-escape | PASS | tests/spec011/qt/smoke.json |
| horizontal-scroll-available | PASS | tests/spec011/qt/smoke.json |
| local-requests-only | PASS | tests/spec011/qt/smoke.json |
| external-network-blocked | PASS | tests/spec011/qt/smoke.json |
| qt-batch-completes | PASS | tests/spec011/qt/smoke.json |
| clean-close-window | PASS | tests/spec011/qt/smoke.json |

## Comparaciones visuales medidas

| Grupo | Comparaciones | Máximo de píxeles distintos | Observación |
|---|---:|---:|---|
| Original/desarrollo, mismo Chromium151 | 18 | 0.000000% | Mismas escenas, datos, viewport, fases de animación; no CSS de producto modificado |
| Baseline histórica/captura posterior | 54 | 0.272522% sin estados intencionales | Escenas05/14 etiquetadas; baseline no sobrescrita |
| Original/desarrollo, mismo Qt | 18 | 0.229861% | Editor/visor/Excel0%; ruido restante en animaciones/raster |
| Baseline Chromium151 / QtWebEngine140 | 18 | 6.845556% | Diferencia real de renderizador y scrollbar; no llamarla fidelidad100% |

Se usó pixelmatch threshold0.1 y exclusión de antialias; los porcentajes cuentan píxeles, no una certificación perceptual global. Diffs y capturas originales/candidatas permanecen disponibles.

## Capacidades pendientes, sin aprobación implícita

| Capacidad | Resultado | Motivo / acción |
|---|---|---|
| Carpeta/permisos/reconexión nativos | PENDIENTE | Contrato propuesto en12; no sustituir flujo sin implementarlo y probarlo |
| Progreso estable | NO APROBADO | Lote2000 completó; screenshot cruzó a reporte final. Ver progress_capture |
| DPI125/150% | NO PROBADO | Entorno nativo actual96/DPR1 observado; no modificar seguridad/pantalla para fingir cobertura |
| Persistencia portable tras cerrar Qt | PENDIENTE | Perfil Qt de smoke off-the-record; preferencias probadas en recarga, no almacenamiento portable de producción |
| Fiscal / SAT / EXE portable | FUERA DE SPEC011 | RiesgosP0 continúan en02 y14; sin nuevo motor ni empaquetado |

Resumen posterior: 48/48 navegación, 30/30 controles, 62/62 específicos y 30/30 Qt si todos los registros muestranPASS. Los JSON son la autoridad si se repite una ejecución.
