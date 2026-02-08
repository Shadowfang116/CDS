# Script to start the dashboard and backend services
# Make sure Docker Desktop is running before executing this script

Write-Host "Starting Bank Diligence Platform services..." -ForegroundColor Green

# Navigate to project directory
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

# Check if Docker is available
$dockerPath = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
if (-not (Test-Path $dockerPath)) {
    Write-Host "Error: Docker not found at $dockerPath" -ForegroundColor Red
    Write-Host "Please make sure Docker Desktop is installed and running." -ForegroundColor Yellow
    exit 1
}

# Wait for Docker daemon to be ready
Write-Host "Waiting for Docker daemon to be ready..." -ForegroundColor Yellow
$maxAttempts = 24
$attempt = 0
$dockerReady = $false

while ($attempt -lt $maxAttempts) {
    Start-Sleep -Seconds 5
    $attempt++
    try {
        & $dockerPath ps 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $dockerReady = $true
            Write-Host "Docker is ready!" -ForegroundColor Green
            break
        }
    } catch {
        # Continue waiting
    }
    Write-Host "." -NoNewline
}

if (-not $dockerReady) {
    Write-Host ""
    Write-Host "Docker daemon is not ready yet. Please wait a bit longer and try again." -ForegroundColor Red
    Write-Host "You can also manually start Docker Desktop and wait for it to fully load." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Starting services (api and frontend)..." -ForegroundColor Green

# Start the services
$dockerComposePath = "C:\Program Files\Docker\Docker\resources\bin\docker-compose.exe"
& $dockerComposePath up -d --build api frontend

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Services started successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Dashboard: http://localhost:3000" -ForegroundColor Cyan
    Write-Host "Backend API: http://localhost:8000" -ForegroundColor Cyan
    Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "To view logs, run: docker compose logs -f api frontend" -ForegroundColor Yellow
    Write-Host "To stop services, run: docker compose down" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "Failed to start services. Check the error messages above." -ForegroundColor Red
    exit 1
}
