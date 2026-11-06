$ErrorActionPreference = 'Stop'
$FiscalRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$FiscalPython = Join-Path $FiscalRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $FiscalPython)) {
    python -m venv (Join-Path $FiscalRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear .venv' }
}
& $FiscalPython -m pip install --require-hashes -r (Join-Path $FiscalRoot 'requirements/fiscal.txt')
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias fiscales fijadas' }
& $FiscalPython -c 'import sys; from lxml import etree; assert sys.prefix != sys.base_prefix; print("Motor fiscal listo; lxml", etree.LXML_VERSION)'
if ($LASTEXITCODE -ne 0) { throw 'La comprobación del motor fiscal falló' }
