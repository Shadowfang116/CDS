# CI smoke: ensure API starts and /api/v1/health/deep returns 200.
# Usage: run from repo root. Expects docker compose available.
$ErrorActionPreference = "Stop"

$RepoRoot = if ($PSScriptRoot) {
    Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
} else {
    (Get-Location).Path
}
Set-Location $RepoRoot

Write-Host "[ci] Bringing up api, db, redis, minio..."
docker compose up -d api db redis minio

$exitCode = 1
try {
    $url = "http://localhost:8000/api/v1/health/deep"
    $deadline = (Get-Date).AddSeconds(60)
    Write-Host "[ci] Waiting for $url (up to 60s)..."

    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-Host "[ci] Health OK (HTTP 200)"
                $exitCode = 0
                break
            }
        } catch {
            # ignore, retry
        }
        Start-Sleep -Seconds 2
    }

    if ($exitCode -ne 0) {
        Write-Host "[ci] Health check failed: $url did not return 200 within 60s"
        Write-Host "[ci] API logs:"
        docker compose logs api
    }
} finally {
    Write-Host "[ci] Tearing down..."
    docker compose logs api 2>$null
    docker compose down -v
}
exit $exitCode
