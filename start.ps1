$ErrorActionPreference = 'Stop'
$runtimePython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $venvPython) {
    $appPython = $venvPython
} elseif (Test-Path -LiteralPath $runtimePython) {
    $appPython = $runtimePython
} else {
    $appPython = (Get-Command python -ErrorAction Stop).Source
}
& $appPython (Join-Path $PSScriptRoot 'backend\server.py') @args
