$ErrorActionPreference = "Stop"

$scriptText = Get-Content -Raw (Join-Path $PSScriptRoot "..\..\start-services.ps1")

if ($scriptText -notmatch '\$LASTEXITCODE -ne 0') {
    throw "start-services.ps1 must check the exit code of Docker commands."
}

if ($scriptText -notmatch 'Local stack is up\.') {
    throw "start-services.ps1 must retain its readiness message."
}

Write-Host "start-services.ps1 failure handling contract passed."
