# Verify production readiness checks for deployment. Run from repo root.
$ErrorActionPreference = "Stop"
$failed = $false
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..\..")
$composeFile = Join-Path $repoRoot "docker-compose.prod.yml"
$envPath = Join-Path $repoRoot ".env.production"
$caddyFile = Join-Path $repoRoot "Caddyfile"

function Write-Check {
    param(
        [Parameter(Mandatory = $true)][string]$Message,
        [Parameter(Mandatory = $true)][string]$Level
    )

    switch ($Level) {
        "OK" { Write-Host "[OK] $Message" -ForegroundColor Green }
        "FAIL" { Write-Host "[FAIL] $Message" -ForegroundColor Red }
        "WARN" { Write-Host "[WARN] $Message" -ForegroundColor Yellow }
        default { Write-Host $Message }
    }
}

function Mark-Failed {
    param([Parameter(Mandatory = $true)][string]$Message)

    Write-Check -Message $Message -Level "FAIL"
    $script:failed = $true
}

function Get-EnvValues {
    param([Parameter(Mandatory = $true)][string]$Path)

    $values = @{}
    foreach ($line in Get-Content -LiteralPath $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#")) {
            continue
        }

        if ($trimmed -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') {
            $name = $matches[1]
            $value = $matches[2].Trim()
            if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
                $value = $value.Substring(1, $value.Length - 2)
            }

            $values[$name] = $value
        }
    }

    return $values
}

function Get-EnvValue {
    param(
        [Parameter(Mandatory = $true)][hashtable]$Values,
        [Parameter(Mandatory = $true)][string[]]$Names
    )

    foreach ($name in $Names) {
        if ($Values.ContainsKey($name)) {
            return $Values[$name]
        }
    }

    return $null
}

function Test-PlaceholderValue {
    param([Parameter(Mandatory = $true)][string]$Value)

    $normalized = $Value.Trim().Trim('"').Trim("'")
    if ([string]::IsNullOrWhiteSpace($normalized)) {
        return $true
    }

    $patterns = @(
        '^(?i)change_me.*$',
        '^(?i)changeme.*$',
        '^(?i)replace[-_ ]?me.*$',
        '^(?i)replace[-_ ]?with.*$',
        '^(?i)your-domain\.com$',
        '^(?i)your-public-hostname$',
        '^(?i)example\.com$',
        '^(?i)localhost$',
        '^(?i)dummy.*$',
        '^(?i)test.*$'
    )

    foreach ($pattern in $patterns) {
        if ($normalized -match $pattern) {
            return $true
        }
    }

    return $false
}

Write-Host "=== Production readiness ===" -ForegroundColor Cyan

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Mark-Failed "Docker not found."
} else {
    Write-Check -Message "Docker present" -Level "OK"
}

$null = docker compose version 2>&1
if ($LASTEXITCODE -ne 0) {
    Mark-Failed "docker compose not available."
} else {
    Write-Check -Message "docker compose present" -Level "OK"
}

if (-not (Test-Path -LiteralPath $envPath)) {
    Mark-Failed ".env.production not found. Copy .env.production.example and set production values."
} else {
    Write-Check -Message ".env.production exists" -Level "OK"
}

if (-not (Test-Path -LiteralPath $composeFile)) {
    Mark-Failed "docker-compose.prod.yml not found."
}

if (-not (Test-Path -LiteralPath $caddyFile)) {
    Mark-Failed "Caddyfile not found."
}

$envVars = @{}
if (Test-Path -LiteralPath $envPath) {
    $envVars = Get-EnvValues -Path $envPath
}

$appEnv = Get-EnvValue -Values $envVars -Names @("APP_ENV", "ENVIRONMENT")
if ($appEnv -ne "production") {
    Mark-Failed "APP_ENV must be production for a production deployment (found '$appEnv')."
} else {
    Write-Check -Message "APP_ENV=production" -Level "OK"
}

$requiredSecrets = @(
    @{ Names = @("POSTGRES_PASSWORD"); MinLength = 12; Label = "POSTGRES_PASSWORD" },
    @{ Names = @("APP_SECRET_KEY", "SECRET_KEY"); MinLength = 32; Label = "APP_SECRET_KEY" },
    @{ Names = @("MINIO_ROOT_PASSWORD"); MinLength = 12; Label = "MINIO_ROOT_PASSWORD" }
)

foreach ($item in $requiredSecrets) {
    $value = Get-EnvValue -Values $envVars -Names $item.Names
    $label = $item.Label

    if ($null -eq $value) {
        Mark-Failed "$label is missing."
        continue
    }

    if (Test-PlaceholderValue -Value $value) {
        Mark-Failed "$label looks like a placeholder."
        continue
    }

    if ($value.Length -lt $item.MinLength) {
        Mark-Failed "$label is shorter than $($item.MinLength) characters."
        continue
    }

    Write-Check -Message "$label is set and meets the minimum length" -Level "OK"
}

Write-Host ""
Write-Host "Checking docker compose config render..." -ForegroundColor Cyan
$null = docker compose -f $composeFile config | Out-Null
if ($LASTEXITCODE -ne 0) {
    Mark-Failed "docker compose config did not render successfully."
} else {
    Write-Check -Message "docker compose config renders" -Level "OK"
}

Write-Host ""
if ($failed) {
    Write-Host "Production readiness FAILED." -ForegroundColor Red
    exit 1
}

Write-Host "Production readiness checks passed." -ForegroundColor Green
exit 0
