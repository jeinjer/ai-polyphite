[CmdletBinding()]
param(
    [ValidateSet("once", "worker")]
    [string]$Mode = "once",
    [string]$ScheduledFor = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $repoRoot ".venv\Scripts\python.exe"

if ($Mode -eq "once") {
    $arguments = @(
        "-m",
        "predictionlab.runtime.paper_validation_cli",
        "once"
    )
    if ($ScheduledFor) {
        $arguments += @("--scheduled-for", $ScheduledFor)
    }
    & $pythonPath @arguments
}
else {
    & $pythonPath -m predictionlab.runtime.paper_validation_cli worker
}

exit $LASTEXITCODE
