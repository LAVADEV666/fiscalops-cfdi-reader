# Motor fiscal — reproducción Windows

Runtime aislado, sin alterar Python global ni políticas de ejecución:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements/fiscal.txt
.\.venv\Scripts\python.exe -m app.fiscal tests/fiscal/fixtures/p0_iva_ieps_40.xml
```

`Setup-Motor.ps1` realiza la misma instalación acotada. Si la política local impide ejecutarlo, usar los comandos directos; no cambiar la política del equipo.

Pruebas/validación (xlrd sólo para verificar extracción de las tablas SAT):

```powershell
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements/fiscal-dev.txt
.\.venv\Scripts\python.exe scripts/fiscal/run_tests.py
.\.venv\Scripts\python.exe scripts/fiscal/render_matrix.py
.\.venv\Scripts\python.exe scripts/fiscal/verify.py
python scripts/spec011/verify.py
```

El runner sale con1 ante fallos; verificar `$LASTEXITCODE` si se usa un pipeline PowerShell. Escribe `tests/fiscal/evidence/tests.json` con casos, versiones y hashes. El verificador exige éxito y correspondencia entre el código probado y el actual. No se instalan dependencias ni se consulta red durante las pruebas.

La prueba de protección del original crea y elimina un enlace duro únicamente en un directorio temporal. Se ejecutó con éxito en Windows fuera del sandbox de comandos, que restringe esa operación; no requiere cambiar políticas de Windows. Un entorno que la bloquee debe reportar el fallo, no omitirla y declarar éxito.

Fixtures y fuentes se entregan ya materializados. Reproducción deliberada de fuentes derivadas:

```powershell
.\.venv\Scripts\python.exe scripts/fiscal/build_fixtures.py
.\.venv\Scripts\python.exe scripts/fiscal/extract_catalogs.py
```

`fetch_sources.py` es una herramienta **manual de mantenimiento**, no parte del importador. Hace solicitudes únicamente a URLs SAT explícitas, guarda fecha/hashes y limita cada descarga a64MiB. No sobrescribe snapshots diferentes: un cambio de fuentes requiere nueva versión, revisión de vigencias, regeneración y pruebas. Una respuesta no disponible queda registrada; no se inventan validaciones. No ejecutar este comando para abrir un XML.

Los XLS se leen con xlrd; se extraen únicamente monedas/tasas y ubicación de códigos de la matriz. Las celdas BIFF numéricas de tasas se convierten por `Decimal(str(value))` a seis posiciones, con procedencia retenida. Los importes de CFDI se leen exclusivamente desde sus cadenas XML mediante Decimal.

Documentos de aceptación: `docs/06_MATRIZ_NORMATIVA_SAT.md`, `docs/15_MOTOR_FISCAL_P0_REPORT.md` y `docs/16_CONTRATO_MOTOR_FISCAL.md`. El frontend Qt sigue en el hito SPEC011 hasta una integración transaccional en worker y adaptación de todos los reportes/exportaciones. No hay EXE final ni certificación SAT.
