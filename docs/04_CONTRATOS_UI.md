# Contratos UI y matriz de conservación visual

**Referencia:** HTML V21.1 original, hash en 00. **Estado visual: BLOCKED_VISUAL_BASELINE**. Esta matriz deriva de código, no de capturas ni medición de píxeles. No se afirma fidelidad100%. El navegador integrado rechazó file:// y Edge headless no devolvió DOM. Las capturas de referencia se harán en una vía local permitida en FASE 1; no se crearon imágenes falsas.

## Orden de recursos que define la apariencia

| Orden | Origen | Copia de auditoría | Contrato |
|---|---|---|---|
| 1 | `<style>` L2 | assets/legacy/style-01.css | Base y capas anteriores, identidad púrpura/naranja, animaciones y componentes. |
| 2 | `<style>` L80 | style-02.css | V19: columnas, tablas, enfoque, validación y editor anterior. |
| 3 | #fiscalops-v20-ui L101 | style-03.css | Pantalla 100vw/100vh, escalado V20, scroll y densidad. |
| 4 | #fiscalops-v21-style L111 | style-04.css | Tarjetas de columnas, agrupación del visor, Excel multipestaña. |
| 5 | #fiscalops-v211-reader-legibility L214 | style-05.css | Legibilidad final del lector y breakpoints específicos; no reemplazar por reglas base antiguas. |
| Imagen | Cuatro data URI L512–514 | embedded-01.png | Un PNG original, 180×180 según cabecera; preservar hash y usos header/splash/drop/orb. |
| Iconografía | Emoji y caracteres dentro de HTML/JS | Original y scripts inventariados | Apariencia depende de Segoe UI/Arial/fallback emoji y Windows; registrar fuentes/DPI. |

Los estilos extraídos son copias de referencia, no están conectados a una nueva app. Los inline style también forman parte del contrato y permanecen en el HTML. No reordenar CSS ni eliminar !important hasta obtener comparación visual. v21Scale y runtime V20 escriben escala: capturar el valor efectivo, no inferirlo de una sola función.

## Matriz de conservación

| Elemento | Referencia/selector y características de código | Estado/escenas a congelar | Evidencia de aceptación requerida |
|---|---|---|---|
| Paleta y fondo | :root --p #4F2D7F, --o #FF7D1E, --soft #f3e9ff, --line #e6dcf3, --mut #667085; capas posteriores añaden azul/gris | Todas | Colores computados y screenshots; no inventar un branding nuevo. |
| Tipografía | Segoe UI,Arial,sans-serif; V20/V21 calc y clamp; tamaños lector finales | Títulos, labels, números, árbol | Fuentes presentes, zoom100%, DPI anotado; legibilidad y saltos de línea. |
| Marco y encabezado | .app,.top,.logo; capa V20 ocupa viewport, header mínimo54px | Tres resoluciones | Geometría real, sin bordes/espacios tomados de capa inicial de1280px por error. |
| Inicio | #s1 .center,.splash-logo,.loader,#start | Antes del timer1600ms y después | Captura a tiempo fijo; float/load controladas para comparación y prueba normal de animación. |
| Carga | #s2 .upload-grid,.upload-card,.drop,.upload-aside | Vacío, drag hover, lista, lote seleccionado | Panel principal/lateral, drop border, botones y estado disabled. |
| Orb y ornamentos | .orb,.halo-dot,.flow-steps,.mini-cards | Carga normal | Mantener spin/breathe/drift/pulseRing; medir coste antes de optimizar. |
| Carpetas y memoria | #folderPanel,#memoryPanel,#filelist | Conectado, permiso denegado, caché/nuevo/modificado | Textos, badges, contadores, wrapping y scroll; no ocultar incidentes. |
| Progreso | #prog,#status aria-live | Escaneo, procesado, error y final | Porcentaje coherente y estado textual; foco y respuesta durante trabajo. |
| Centro reportes | #s3 .report-shell,.report-head,.top-origin,.report-actions | Vacío y con datos | Proporciones, acciones y orden del original, sin componentes de otro framework. |
| Filtros | .toolbar,#year,#month,#q,.status-seg,.method-seg,#tipo,#estatus | Combinados y reset | Capturar visibilidad final de controles inicialmente hidden-select; un evento efectivo por acción. |
| Tipo/perfil | #reportKind,#profileSel,#densityBtn | Todos los perfiles/tipos principales | Selección reflejada en reporte y columnas, rótulos conservados. |
| Pestañas tipo | #typeTabs button[data-type] | I/E/T/N/P y disabled sin datos | Estado activo tras un clic, conteos y navegación sin doble toggle. |
| Estadísticas | #cards .stat | Emitidos/recibidos/vigentes/cancelados/sinmetadata | Colores, alineación y datos del mismo ámbito; metadata nunca equivale a consulta actual SAT. |
| Tabla | .tablebox,#thead,#tbody,.pinned,.compact | Texto largo, números, vacío, cancelado, duplicado | Headers sticky, columnas y orden, scroll independiente, filas30/50/100/200, foco Enter/Espacio. |
| Totales | #totalsBox .currency-groups | Una y dos monedas, reporte derivado | Monedas separadas y universo reconciliado; mismo diseño antes de ajustar motor. |
| Hallazgos | #assistantBox, columnas ResultadoValidacion | Errores y advertencias | Registrar que CSS/renderer actual los ocultan; cualquier nueva visibilidad requiere decisión explícita, no afirmarla existente. |
| Editor V21 | #modal .column-editor,.v21-col-quadrant,.v21-column-card | Buscar, marcar, perfiles, todas/ninguna, aplicar/cerrar | Cuadrantes/tarjetas, muestras hasta2000 filas; búsqueda sin perder selección; conservar anchos sólo si contrato aprobado. |
| Visor | #previewModal .preview-box,#previewBody | Resumen/Impuestos/Conceptos/Todos los datos/XML visual | Grid, jerarquía, scroll y tamaño final; no usar visor antiguo como referencia. |
| Legibilidad visor | CSS05: --reader-text clamp15..16.5px; small13.5..15; heading16..18.5; ancho min1580/97.5vw, alto min96vh/1060 | 1366/1600/1920 y DPI | Medición efectiva tras cascada; modales sin recortes y etiquetas legibles. |
| Pestañas visor | .pv-tabs,.pv-pane,.concept-card,.xml-node | Cada tab y elementos expandibles | Estado activo, tab horizontal/vertical, texto escapado y navegación de teclado. |
| Constructor Excel | #exportModal,#analysisChoices,#exportMainInfo,#exportSheetSummary | Sin extras, varios, vacíos, generando/error | Hoja1 obligatoria, mismas columnas/filtros, contador de hojas real y botones. |
| Modales/cierre | #modal,#previewModal,#exportModal | Escape, fondo, botón cerrar, Tab/ShiftTab | Capturar foco inicial/restauración; focus trap actual no comprobado. Mantener overlay/z-index. |
| Responsive | @media en5 CSS, lector1450/1100/760 | Resoluciones y ventana estrecha/alta/baja | No superposición ni controles inaccesibles; registrar defectos comprobados, no arreglar por preferencia. |

## Contrato de datos e interacción

La UI solicita selección y presenta importes originales, hallazgos y estados. El motor es responsable de precisión/reglas; una advertencia no autoriza modificar el XML. `Moneda`, moneda P y moneda DR pertenecen a niveles distintos. `Estado SAT` debe conservar procedencia local/fecha al migrar, sin apariencia de verificación en línea.

El filtro de consulta y la selección exportada deben compartir snapshot. Columnas visibles, orden de filas y filtros se conservan en primera hoja; las analíticas sólo amplían el ámbito mediante elección explícita. Paginación es sólo presentación; exportar actual significa todas las filas filtradas salvo elección expresa de página. Reportes de errores sin CFDI tienen ámbito de lote y requieren rótulo claro.

El editor debe operar un borrador hasta Aplicar; Cerrar/Escape no confirma cambios. Buscar no modifica la selección completa. Esto identifica el contrato deseado que corrige U01/U06; no se afirma que el prototipo lo cumpla. Respetar el diseño de tarjetas V21, documentando que el editor anterior de ancho/orden fue sustituido por el parche.

## Protocolo de evidencia visual para FASE 1

Capturar a1366×768,1600×900,1920×1080; registrar DPI Windows100/125/150% al menos en los escenarios disponibles, escala de navegador y viewport CSS real. No cambiar configuración de Windows sin una vía autorizada; un emulador de deviceScaleFactor no demuestra DPI real de Windows. Registrar OS, navegador/renderizador/versión, fuentes, fecha, hash HTML y fixture.

Nombre recomendado: `escena__1366x768__dpi100__zoom100.png` y JSON de contexto. Animaciones: comparar a instante fijo o desactivadas exclusivamente por harness, y probarlas además en ejecución normal; ninguna desactivación se incorpora a producción sin decisión. Conservar baseline original y capturas candidatas separadas. Medir diff de píxeles/áreas y revisar diferencias, sin afirmar «100%» por observación casual. El umbral debe fijarse tras medir ruido de fuente/animaciones, no aprobar diferencias arbitrarias.

**Puerta:** no separar HTML/CSS/JS de producción hasta tener capturas verificadas y revisión de navegación. No existe nueva UI en esta fase; AC01/02 están pendientes, no fallados por una implementación nueva.
