# Thin wrapper around Docker Compose. Usage: .\run.ps1 [up|down|test]
# Mirrors run.sh. Written for Windows PowerShell but not tested on Windows (see README).
param([string]$Command = "up")

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Ensure-Env {
    if (-not (Test-Path ".env")) {
        Copy-Item ".env.example" ".env"
        Write-Host "Created .env from .env.example"
    }
}

function Read-Env([string]$Name, [string]$Default) {
    $line = Get-Content ".env" | Where-Object { $_ -match "^$Name=" } | Select-Object -Last 1
    if ($line) { return $line.Substring($Name.Length + 1) }
    return $Default
}

switch ($Command) {
    "up" {
        Ensure-Env
        docker compose up --build -d --wait
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        $base = "http://localhost:" + (Read-Env "FRONTEND_PORT" "8080")
        Write-Host ""
        Write-Host "App:          $base/"
        Write-Host "API:          $base/api/v1/"
        Write-Host "Health:       $base/api/v1/health"
        Write-Host "Swagger UI:   $base/api/v1/docs"
        Write-Host "Django admin: $base/admin/"
        Write-Host "Demo logins:  README.md, section `"Demo credentials`" (demo only)"
    }
    "down" {
        docker compose down
        exit $LASTEXITCODE
    }
    "test" {
        Ensure-Env
        docker compose run --build --rm api pytest
        exit $LASTEXITCODE
    }
    default {
        Write-Host "Usage: .\run.ps1 [up|down|test]"
        exit 1
    }
}
