[CmdletBinding()]
param(
    [ValidateSet("once", "worker")]
    [string]$Mode = "once",
    [string]$Provider = "mock"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $repoRoot ".venv\Scripts\python.exe"

if ($Mode -eq "once") {
    & $pythonPath -m predictionlab.runtime.collector_cli once --provider $Provider
}
else {
    & $pythonPath -m predictionlab.runtime.collector_cli worker
}

exit $LASTEXITCODE
