param([string]$Python = 'python', [switch]$CheckOnly, [int]$Width = 1366, [int]$Height = 768)
$ErrorActionPreference = 'Stop'
$taskRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
Push-Location -LiteralPath $taskRoot
try {
    if ($CheckOnly) { & $Python -m app.desktop_smoke --check }
    else { & $Python -m app.desktop_smoke --width $Width --height $Height }
    if ($LASTEXITCODE -ne 0) { throw 'Contenedor no ejecutado. Consulta tests/visual/evidence/desktop-check.json.' }
} finally { Pop-Location }
