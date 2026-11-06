param(
    [string]$Node = 'node',
    [string]$Modules = $env:FISCALOPS_NODE_MODULES,
    [string]$Browser = '',
    [string]$Url = '',
    [switch]$Headed,
    [string]$Output = ('tests/visual/candidate-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
)
$ErrorActionPreference = 'Stop'
$taskRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
if (-not $Modules) {
    $taskBundled = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules'
    if (Test-Path -LiteralPath (Join-Path $taskBundled 'playwright/package.json')) { $Modules = $taskBundled }
}
if (-not $Browser) {
    $taskChromiumRoot = Join-Path $env:LOCALAPPDATA 'ms-playwright'
    $taskCandidates = @(Get-ChildItem -LiteralPath $taskChromiumRoot -Directory -Filter 'chromium-*' -ErrorAction SilentlyContinue |
        Sort-Object { [int]($_.Name -replace '^chromium-', '') } -Descending)
    foreach ($taskCandidate in $taskCandidates) {
        $taskExecutable = Join-Path $taskCandidate.FullName 'chrome-win64/chrome.exe'
        if (Test-Path -LiteralPath $taskExecutable) { $Browser = $taskExecutable; break }
    }
}
$taskArguments = @('scripts/visual/capture.cjs')
if ($Modules) { $taskArguments += @('--modules', $Modules) }
if ($Browser) { $taskArguments += @('--browser', $Browser) }
if ($Url) { $taskArguments += @('--url', $Url) }
if ($Headed) { $taskArguments += '--headed' }
$taskArguments += @('--output', $Output)
Push-Location -LiteralPath $taskRoot
try {
    & $Node @taskArguments
    if ($LASTEXITCODE -ne 0) { throw 'La captura no terminó; revisar navigation.json, no declarar DONE.' }
    $taskArguments[0] = 'scripts/visual/check_controls.cjs'
    $taskArguments = @($taskArguments | Where-Object { $_ -ne '--headed' })
    $taskOutputIndex = [Array]::IndexOf($taskArguments, '--output')
    $taskArguments[$taskOutputIndex] = '--evidence'
    $taskArguments[$taskOutputIndex + 1] = Join-Path $Output 'evidence'
    & $Node @taskArguments
    if ($LASTEXITCODE -ne 0) { throw 'La navegación no terminó; revisar controls.json.' }
    Write-Host 'Revisa resultados FAIL y bloqueos. Capturar no equivale a aprobar el prototipo.'
} finally { Pop-Location }
