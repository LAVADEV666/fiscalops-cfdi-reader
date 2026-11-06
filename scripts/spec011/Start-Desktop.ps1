$ErrorActionPreference='Stop'
$taskRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
Push-Location -LiteralPath $taskRoot
try {
    if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) { throw 'Ejecuta primero scripts/spec011/Setup-Desktop.ps1.' }
    & ./.venv/Scripts/python.exe -m app.desktop.main
    if ($LASTEXITCODE -ne 0) { throw 'FiscalOps terminó con un error; revisar diagnóstico de Qt.' }
} finally { Pop-Location }
