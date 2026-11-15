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
        $apiPort = Read-Env "API_PORT" "8000"
        $frontendPort = Read-Env "FRONTEND_PORT" "8080"
        Write-Host ""
        Write-Host "App:          http://localhost:$frontendPort/"
        Write-Host "API:          http://localhost:$apiPort/api/v1/"
        Write-Host "Health:       http://localhost:$apiPort/api/v1/health"
        Write-Host "Swagger UI:   http://localhost:$apiPort/api/v1/docs"
        Write-Host "Django admin: http://localhost:$apiPort/admin/"
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
