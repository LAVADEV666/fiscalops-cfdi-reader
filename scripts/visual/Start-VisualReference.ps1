param([int]$Port = 0, [string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$taskRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
Push-Location -LiteralPath $taskRoot
try {
    & $Python scripts/visual/make_fixtures.py
    if ($LASTEXITCODE -ne 0) { throw 'No se pudieron generar los fixtures sintéticos.' }
    Write-Host 'Servidor sólo local. Abre la URL que se imprimirá. Ctrl+C lo detiene.'
    & $Python scripts/visual/serve.py --port $Port
} finally { Pop-Location }
