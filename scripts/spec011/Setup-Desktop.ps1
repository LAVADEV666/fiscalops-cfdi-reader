param([string]$Python='python')
$ErrorActionPreference='Stop'
$taskRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
Push-Location -LiteralPath $taskRoot
try {
    if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
        & $Python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno aislado.' }
    }
    & ./.venv/Scripts/python.exe -m pip install --disable-pip-version-check --require-hashes -r requirements/desktop.txt
    if ($LASTEXITCODE -ne 0) { throw 'No se instalaron las dependencias verificadas; revisar conexión a PyPI.' }
    & ./.venv/Scripts/python.exe -c "import PySide6; from PySide6.QtWebEngineCore import qWebEngineChromiumVersion; print('PySide6',PySide6.__version__,'Chromium',qWebEngineChromiumVersion())"
    if ($LASTEXITCODE -ne 0) { throw 'La comprobación de Qt falló.' }
} finally { Pop-Location }
