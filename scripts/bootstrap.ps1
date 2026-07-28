[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $repoRoot ".venv"
$frontendPath = Join-Path $repoRoot "frontend"

if (-not (Test-Path -LiteralPath $venvPath)) {
    py -3.13 -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create the Python virtual environment."
    }
}

$pythonPath = Join-Path $venvPath "Scripts\python.exe"
& $pythonPath -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "Failed to upgrade pip."
}

& $pythonPath -m pip install -e "$repoRoot\backend[dev]"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install backend dependencies."
}

Push-Location $frontendPath
try {
    npm.cmd ci
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install frontend dependencies."
    }
}
finally {
    Pop-Location
}

Write-Output "AI-Polyphite development dependencies are installed."
