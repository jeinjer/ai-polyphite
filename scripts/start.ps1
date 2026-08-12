[CmdletBinding()]
param(
    [switch]$SkipBuild,
    [ValidateRange(30, 600)]
    [int]$TimeoutSeconds = 240
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $PSScriptRoot
$dockerDesktopCandidates = @(
    (Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"),
    (Join-Path $env:LOCALAPPDATA "Docker\Docker Desktop.exe")
)

function Test-DockerEngine {
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    try {
        & docker info --format "{{.ServerVersion}}" 2>&1 | Out-Null
        return $LASTEXITCODE -eq 0
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
}

function Wait-Until {
    param(
        [Parameter(Mandatory)]
        [scriptblock]$Condition,
        [Parameter(Mandatory)]
        [string]$Description
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (& $Condition) {
            return
        }
        Start-Sleep -Seconds 3
    }

    throw "Timeout waiting for $Description after $TimeoutSeconds seconds."
}

function Test-ComposeServiceHealthy {
    param(
        [Parameter(Mandatory)]
        [string]$Service
    )

    $containerId = & docker compose ps --quiet $Service 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $containerId) {
        return $false
    }

    $status = & docker inspect `
        --format "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}" `
        $containerId 2>$null
    return $LASTEXITCODE -eq 0 -and $status -in @("healthy", "running")
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker is not installed or is not available in PATH."
}

if (-not (Test-DockerEngine)) {
    $dockerDesktop = $dockerDesktopCandidates |
        Where-Object { Test-Path -LiteralPath $_ } |
        Select-Object -First 1

    if (-not $dockerDesktop) {
        throw "Docker Desktop is not running and its executable could not be found."
    }

    Write-Output "Starting Docker Desktop..."
    Start-Process -FilePath $dockerDesktop -WindowStyle Hidden
    Wait-Until -Description "Docker Desktop" -Condition { Test-DockerEngine }
}

Push-Location $repoRoot
try {
    $composeArguments = @("compose", "up", "--detach")
    if (-not $SkipBuild) {
        $composeArguments += "--build"
    }

    Write-Output "Starting AI-Polyphite..."
    & docker @composeArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose could not start AI-Polyphite."
    }

    Wait-Until -Description "the backend readiness check" -Condition {
        try {
            $response = Invoke-WebRequest `
                -UseBasicParsing `
                -Uri "http://127.0.0.1:8000/health/ready" `
                -TimeoutSec 3
            return $response.StatusCode -eq 200
        }
        catch {
            return $false
        }
    }

    Wait-Until -Description "the dashboard" -Condition {
        try {
            $response = Invoke-WebRequest `
                -UseBasicParsing `
                -Uri "http://127.0.0.1:3000" `
                -TimeoutSec 3
            return $response.StatusCode -eq 200
        }
        catch {
            return $false
        }
    }

    foreach ($service in @("postgres", "redis", "ollama", "backend", "frontend")) {
        Wait-Until -Description "the $service health check" -Condition {
            Test-ComposeServiceHealthy -Service $service
        }
    }

    $requiredServices = @(
        "postgres",
        "redis",
        "ollama",
        "backend",
        "worker",
        "paper-validator",
        "frontend",
        "backup"
    )
    $runningServices = @(& docker compose ps --status running --services)
    $missingServices = @($requiredServices | Where-Object { $_ -notin $runningServices })
    if ($missingServices.Count -gt 0) {
        & docker compose ps
        throw "Services not running: $($missingServices -join ', ')."
    }

    Write-Output ""
    Write-Output "AI-Polyphite is running."
    Write-Output "Dashboard: http://127.0.0.1:3000"
    Write-Output "API docs:  http://127.0.0.1:8000/docs"
    Write-Output "Mode:      public real data, simulated decisions and capital"
    Write-Output ""
    & docker compose ps
}
finally {
    Pop-Location
}
