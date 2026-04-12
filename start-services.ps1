#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = $PSScriptRoot
Set-Location $projectRoot

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Docker is not available on PATH. Install Docker Desktop / Docker Engine first." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example" -ForegroundColor Yellow
}

Write-Host "Starting the full local stack..." -ForegroundColor Green
docker compose up -d --build

Write-Host "Applying database migrations..." -ForegroundColor Green
docker compose exec -T api alembic upgrade head

Write-Host ""
Write-Host "Local stack is up." -ForegroundColor Green
Write-Host "Frontend:   http://localhost:3000/dashboard" -ForegroundColor Cyan
Write-Host "API Docs:   http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "Health:     http://localhost:8000/api/v1/health/deep" -ForegroundColor Cyan
Write-Host "MinIO:      http://localhost:9001" -ForegroundColor Cyan
Write-Host "MailHog:    http://localhost:8025" -ForegroundColor Cyan
Write-Host ""
Write-Host "Optional demo seed:" -ForegroundColor Yellow
Write-Host "  docker compose exec -T api python scripts/dev/seed_demo_data.py" -ForegroundColor White
