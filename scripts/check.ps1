[CmdletBinding()]
param(
    [switch]$E2E,
    [switch]$Integration
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $repoRoot ".venv\Scripts\python.exe"
$frontendPath = Join-Path $repoRoot "frontend"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Python environment not found. Run scripts/bootstrap.ps1 first."
}

if ($Integration) {
    & $pythonPath -m pytest "$repoRoot\backend\tests"
}
else {
    & $pythonPath -m pytest "$repoRoot\backend\tests" -m "not integration"
}
if ($LASTEXITCODE -ne 0) {
    throw "Backend tests failed."
}

if ($Integration) {
    & $pythonPath -m alembic -c "$repoRoot\backend\alembic.ini" check
    if ($LASTEXITCODE -ne 0) {
        throw "Alembic metadata drift check failed."
    }
}

& $pythonPath -m ruff check "$repoRoot\backend"
if ($LASTEXITCODE -ne 0) {
    throw "Backend lint failed."
}

& $pythonPath -m mypy --config-file "$repoRoot\backend\pyproject.toml" "$repoRoot\backend\src"
if ($LASTEXITCODE -ne 0) {
    throw "Backend type checking failed."
}

Push-Location $frontendPath
try {
    npm.cmd audit
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend dependency audit failed."
    }

    npm.cmd run lint
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend lint failed."
    }

    npm.cmd run typecheck
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend type checking failed."
    }

    npm.cmd run build
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend build failed."
    }

    if ($E2E) {
        npm.cmd run test:e2e
        if ($LASTEXITCODE -ne 0) {
            throw "Frontend E2E tests failed."
        }
    }
}
finally {
    Pop-Location
}

docker compose --file "$repoRoot\docker-compose.yml" config --quiet
if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose validation failed."
}

Write-Output "All scaffold checks passed."
