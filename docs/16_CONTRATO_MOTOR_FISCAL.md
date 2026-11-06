# Contrato del motor fiscal independiente

La API/CLI de este documento se mantiene. El adaptador nativo Qt posterior y sus jobs/reportes/exportaciones se documentan en [18_CONTRATO_QT_WORKERS](18_CONTRATO_QT_WORKERS.md); la ausencia de integración descrita al final corresponde al hito independiente anterior.

## Uso inmediato

Desde la raíz del proyecto, con CPython3.11 x64 y `.venv`:

```powershell
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements/fiscal.txt
.\.venv\Scripts\python.exe -m app.fiscal tests/fiscal/fixtures/p0_iva_ieps_40.xml --output resultado-fiscal.json
```

Para un documento propio, sustituir la ruta del XML. Si se omite `--output`, el JSON va a stdout. No se hacen consultas SAT ni descargas en la lectura. El reporte contiene datos del documento; no es un log anónimo. El XML de entrada se abre sólo para lectura y no puede ser destino del reporte. `--include-original` agrega base64 con los bytes originales; por defecto sólo se serializan su tamaño y hash.

| Salida del proceso | Significado |
|---|---|
| 0 | XSD completo PASS y consistencia en las reglas implementadas; no certificación SAT |
| 1 | XSD FAIL o reglas implementadas con errores |
| 2 | XML rechazado, entrada/salida inaccesible o recurso indispensable no disponible |
| 3 | Lectura posible con validación pendiente/parcial |

## API Python

```python
from app.fiscal.service import inspect_invoice, json_data
from app.fiscal.security import XmlRejected

with open("factura.xml", "rb") as stream:
    inspection = inspect_invoice(stream)

dto = json_data(inspection)
# dto['analysis']['recalculated']['federal_by_code']['IVA_transfer'] es str o None.
```

`read_invoice(bytes_or_stream, Limits(...))` produce un `Invoice` sin necesitar Qt ni SQLite. `inspect_invoice` añade validación XSD y reconciliación. `XmlRejected` expone código, línea y columna sin incluir el contenido fiscal ni rutas locales. No se realiza deduplicación, escritura de caché o resolución de UUID contra fuentes externas.

Contrato JSON: `fiscalops.inspection/1`. Versiones parser y reglas están incluidas. Cada importe es una cadena decimal o NULL, junto con:

- `raw`: valor de atributo que entrega el parser XML (no la secuencia byte a byte de comillas/escapes); los bytes exactos permanecen en `document.original`.
- `value`: Decimal en Python, cadena decimal en JSON; no `float`.
- `state`: missing, invalid o valid. Un valor léxicamente válido puede fallar después la regla de escala o el XSD.
- `scale`: decimales reportados, incluidos ceros finales.
- `path`: ubicación del campo.

La ausencia opcional sólo aporta cero a una fórmula cuando esa ausencia representa un componente no aplicable según su estructura: por ejemplo, no hay impuestos de esa naturaleza o no hay descuentos conceptuales. El DTO sigue conservando missing. Un impuesto existente con Importe inválido/ausente no se convierte en cero ni activa un fallback que oculte el error.

## Importes reportados y diagnósticos

`analysis.reported` conserva encabezado, agregados federales y locales. `recalculated` contiene grupos conceptuales/globales, fuente seleccionada por naturaleza, impuestos por código, bases IVA separadas y tres totales:

| Campo | Componentes |
|---|---|
| total_from_reported_components | SubTotal/Descuento reportados y agregados reportados; NULL si falta un agregado aplicable |
| total_from_tax_details | SubTotal/Descuento reportados, detalle global elegido (o fallback conceptual explícito) y detalle local una vez |
| total_from_concepts | Sumas conceptuales redondeadas por moneda y detalle local; diagnóstico independiente |

`difference_total_minus_details` resta el total de detalle al Total reportado. No altera el XML ni asegura que un total diagnóstico sea emitible. No se convierte moneda: los importes conservan `Moneda`. P/N/T se leen/preservan, con aritmética no implementada y totales diagnósticos nulos.

Los hallazgos incluyen ID interno, categoría de regla, código, ubicación, estado y reportado/esperado; las referencias listan fuentes y códigos SAT de apoyo. PASS de una comprobación no significa implementación completa de ese código SAT. `consistent-in-scope`, `error` y `partial` describen sólo el alcance declarado.

## Frontera de validación

`validation.xml`, `validation.xsd`, `validation.arithmetic`, `signature` y `official_sat` son capas distintas. `xsd.core_projection_status` y `excluded_unvalidated_nodes` explican las validaciones parciales. Nunca se elimina un complemento del original para conseguir PASS.

No hay adaptador a QWebChannel, transformaciones fiscales JavaScript, selector nativo nuevo, SQLite, ZIP, cancelación de jobs o actualización automática de fuentes. Éstos pertenecen a la siguiente integración; el CLI ya permite usar el motor de esta entrega.
