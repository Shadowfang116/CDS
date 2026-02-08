#!/usr/bin/env pwsh
# Pilot Reset Script - One-command setup for demo environment
# Usage: ./scripts/dev/pilot_reset.ps1 [-KeepVolumes]

param(
    [switch]$KeepVolumes = $false
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Invoke-CmdCapture {
  param(
    [Parameter(Mandatory=$true)][string]$Command,
    [string]$FailMessage = "Command failed"
  )
  # Use cmd.exe so PowerShell does not treat stderr as error records.
  $outputLines = & cmd.exe /c "$Command 2>&1"
  $exit = $LASTEXITCODE
  $output = ($outputLines -join "`n").Trim()
  return [pscustomobject]@{ ExitCode = $exit; Output = $output; Command = $Command; FailMessage = $FailMessage }
}

function Assert-Ok {
  param([Parameter(Mandatory=$true)]$Result)
  if ($Result.ExitCode -ne 0) {
    Write-Host "[FAIL] $($Result.FailMessage)" -ForegroundColor Red
    Write-Host "Command: $($Result.Command)" -ForegroundColor Red
    if ($Result.Output) { Write-Host $Result.Output -ForegroundColor Red }
    exit $Result.ExitCode
  }
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PILOT RESET - Bank Diligence Platform" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "IMPORTANT: Run scripts using .\scripts\dev\pilot_reset.ps1" -ForegroundColor Yellow
Write-Host "          (do not type notes into terminal)" -ForegroundColor Yellow
Write-Host ""
Write-Host "IMPORTANT: Run scripts using .\scripts\dev\pilot_reset.ps1" -ForegroundColor Yellow
Write-Host "          (do not type notes into terminal)" -ForegroundColor Yellow
Write-Host ""

# Step 1: Clean up (optional)
if (-not $KeepVolumes) {
    Write-Host "[1/6] Cleaning up existing containers and volumes..." -ForegroundColor Yellow
    $down = Invoke-CmdCapture -Command "docker compose down -v" -FailMessage "Failed to clean up containers"
    Assert-Ok $down
    Write-Host "[OK] Cleanup complete" -ForegroundColor Green
} else {
    Write-Host "[1/6] Keeping volumes (containers only)..." -ForegroundColor Yellow
    $down = Invoke-CmdCapture -Command "docker compose down" -FailMessage "Failed to stop containers"
    Assert-Ok $down
    Write-Host "[OK] Containers stopped" -ForegroundColor Green
}

# Step 2: Build and start services
Write-Host ""
Write-Host "[2/6] Building and starting services..." -ForegroundColor Yellow
$up = Invoke-CmdCapture -Command "docker compose up -d --build" -FailMessage "Failed to start services"
Assert-Ok $up
Write-Host "[OK] Services started" -ForegroundColor Green

# Step 3: Wait for services to be healthy
Write-Host ""
Write-Host "[3/6] Waiting for services to be healthy..." -ForegroundColor Yellow
$maxAttempts = 60
$attempt = 0
$healthy = $false

while ($attempt -lt $maxAttempts) {
    Start-Sleep -Seconds 2
    $attempt++
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/health/deep" -Method GET -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $healthData = $response.Content | ConvertFrom-Json
            if ($healthData.status -eq "ok" -and $healthData.checks.database.status -eq "ok" -and $healthData.checks.redis.status -eq "ok") {
                $healthy = $true
                break
            }
        }
    } catch {
        # Continue waiting
    }
    
    if ($attempt % 10 -eq 0) {
        Write-Host "  Waiting... (attempt $attempt/$maxAttempts)" -ForegroundColor Gray
    }
}

if (-not $healthy) {
    Write-Host "[FAIL] Services did not become healthy within timeout" -ForegroundColor Red
    Write-Host "Checking container status..." -ForegroundColor Yellow
    $ps = Invoke-CmdCapture -Command "docker compose ps" -FailMessage "Failed to check container status"
    if ($ps.Output) { Write-Host $ps.Output }
    Write-Host ""
    Write-Host "API container logs (last 200 lines):" -ForegroundColor Yellow
    $logs = Invoke-CmdCapture -Command "docker compose logs --tail=200 api" -FailMessage "Failed to get logs"
    if ($logs.Output) { Write-Host $logs.Output }
    exit 1
}
Write-Host "[OK] Services are healthy" -ForegroundColor Green

# Verify API container is actually running (not just created)
$apiStatus = Invoke-CmdCapture -Command "docker compose ps api --format `"{{.Status}}`"" -FailMessage "Failed to check API status"
if ($apiStatus.Output -notmatch "Up") {
    Write-Host "[FAIL] API container is not running. Status: $($apiStatus.Output)" -ForegroundColor Red
    Write-Host "API container logs:" -ForegroundColor Yellow
    $logs = Invoke-CmdCapture -Command "docker compose logs --tail=200 api" -FailMessage "Failed to get logs"
    if ($logs.Output) { Write-Host $logs.Output }
    exit 1
}

# Step 4: Run migrations
Write-Host ""
Write-Host "[4/6] Running database migrations..." -ForegroundColor Yellow
$m = Invoke-CmdCapture -Command "docker compose exec -T api alembic upgrade head" -FailMessage "Alembic upgrade head failed"
if ($m.ExitCode -ne 0) {
    # Check if error is about missing revision (database stamped to non-existent revision)
    if ($m.Output -match "Can't locate revision") {
        Write-Host "[WARN] Migration revision not found in codebase (database may be from different version)" -ForegroundColor Yellow
        Write-Host "Auto-recovering by resetting database..." -ForegroundColor Yellow
        
        if ($KeepVolumes) {
            Write-Host "[FAIL] Cannot auto-recover with -KeepVolumes flag. Please run without -KeepVolumes or manually reset DB." -ForegroundColor Red
            Write-Host "Manual recovery: docker compose down -v && docker compose up -d --build" -ForegroundColor Yellow
            exit 1
        }
        
        # Reset database
        Write-Host "  Stopping containers and removing volumes..." -ForegroundColor Gray
        $down = Invoke-CmdCapture -Command "docker compose down -v" -FailMessage "Failed to reset database"
        Assert-Ok $down
        
        Write-Host "  Rebuilding and starting services..." -ForegroundColor Gray
        $up = Invoke-CmdCapture -Command "docker compose up -d --build" -FailMessage "Failed to restart services"
        Assert-Ok $up
        
        # Wait for services to be healthy again
        Write-Host "  Waiting for services to be healthy..." -ForegroundColor Gray
        $maxAttempts = 60
        $attempt = 0
        $healthy = $false
        while ($attempt -lt $maxAttempts) {
            Start-Sleep -Seconds 2
            $attempt++
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/health/deep" -Method GET -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
                if ($response.StatusCode -eq 200) {
                    $healthData = $response.Content | ConvertFrom-Json
                    if ($healthData.status -eq "ok" -and $healthData.checks.database.status -eq "ok") {
                        $healthy = $true
                        break
                    }
                }
            } catch {
                # Continue waiting
            }
        }
        
        if (-not $healthy) {
            Write-Host "[FAIL] Services did not become healthy after reset" -ForegroundColor Red
            exit 1
        }
        
        # Retry migrations
        Write-Host "  Retrying migrations..." -ForegroundColor Gray
        $m = Invoke-CmdCapture -Command "docker compose exec -T api alembic upgrade head" -FailMessage "Alembic upgrade head failed after reset"
        Assert-Ok $m
        if ($m.Output) { Write-Host $m.Output }
        Write-Host "[OK] Migrations complete after auto-recovery" -ForegroundColor Green
    } else {
        Assert-Ok $m
    }
} else {
    if ($m.Output) { Write-Host $m.Output }
    Write-Host "[OK] Migrations complete" -ForegroundColor Green
}

# Verify current revision
$cur = Invoke-CmdCapture -Command "docker compose exec -T api alembic current" -FailMessage "Alembic current failed"
Assert-Ok $cur
if ($cur.Output) { Write-Host $cur.Output }

# Verify critical tables exist
Write-Host "Verifying database schema..." -ForegroundColor Yellow
$schemaCheck = Invoke-CmdCapture -Command "docker compose exec -T db psql -U bank_diligence -d bank_diligence -t -A -X -c `"SELECT to_regclass('public.audit_log'), to_regclass('public.verifications'), to_regclass('public.verification_evidence_refs'), to_regclass('public.cps');`"" -FailMessage "Database schema check failed"
Assert-Ok $schemaCheck
$schemaResult = $schemaCheck.Output.Trim()
$tables = $schemaResult -split '\|'
$requiredTables = @('audit_log', 'verifications', 'verification_evidence_refs', 'cps')
$missingTables = @()
foreach ($table in $requiredTables) {
    if ($schemaResult -notmatch $table -or $tables -notcontains $table) {
        $missingTables += $table
    }
}
if ($missingTables.Count -gt 0) {
    Write-Host "[FAIL] Required tables missing: $($missingTables -join ', ')" -ForegroundColor Red
    Write-Host "Schema check result: $schemaResult" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Database schema verified (required tables exist)" -ForegroundColor Green

# Step 5: Seed demo data
Write-Host ""
Write-Host "[5/6] Seeding demo data..." -ForegroundColor Yellow
$seed = Invoke-CmdCapture -Command "docker compose exec -T api python scripts/dev/seed_demo_data.py" -FailMessage "Failed to seed demo data"
Assert-Ok $seed
if ($seed.Output) { Write-Host $seed.Output }
Write-Host "[OK] Demo data seeded" -ForegroundColor Green

# Post-seed verification: Ensure required documents exist
Write-Host "Verifying required documents are attached..." -ForegroundColor Yellow
$verifyQuery = @"
SELECT 
    c.id as case_id,
    c.title as case_title,
    d.id as doc_id,
    d.original_filename,
    COUNT(dp.id) as page_count
FROM cases c
LEFT JOIN documents d ON d.case_id = c.id AND d.org_id = c.org_id
LEFT JOIN document_pages dp ON dp.document_id = d.id AND dp.org_id = d.org_id
WHERE c.org_id = (SELECT id FROM orgs WHERE name = 'OrgA' LIMIT 1)
    AND c.title IN ('PILOT DEMO CASE', 'PILOT LDA REVISED PLAN CASE', 'PILOT REVENUE KHASRA MISMATCH CASE', 'PILOT DHA SOCIETY CASE')
GROUP BY c.id, c.title, d.id, d.original_filename
ORDER BY c.title, d.original_filename;
"@
$verifyResult = Invoke-CmdCapture -Command "docker compose exec -T db psql -U bank_diligence -d bank_diligence -t -A -X -c `"$verifyQuery`"" -FailMessage "Failed to verify documents"
if ($verifyResult.ExitCode -eq 0) {
    $verifyLines = $verifyResult.Output -split "`n" | Where-Object { $_.Trim() -ne "" }
    $requiredDocs = @{
        "PILOT DEMO CASE" = @("PILOT_DEMO_DOCUMENT.pdf")
        "PILOT LDA REVISED PLAN CASE" = @("LDA_REVISED_PLAN_DOCUMENT.pdf")
        "PILOT REVENUE KHASRA MISMATCH CASE" = @("FARD_123_4.pdf", "JAMABANDI_999_1.pdf")
        "PILOT DHA SOCIETY CASE" = @("DHA_TRANSFER_DOCUMENT.pdf")
    }
    $missingDocs = @()
    foreach ($line in $verifyLines) {
        $fields = $line -split '\|'
        if ($fields.Count -ge 5) {
            $caseTitle = $fields[1].Trim()
            $docFilename = $fields[3].Trim()
            $pageCount = [int]($fields[4].Trim())
            if ($requiredDocs.ContainsKey($caseTitle)) {
                $required = $requiredDocs[$caseTitle]
                if ($required -contains $docFilename) {
                    if ($pageCount -eq 0) {
                        $missingDocs += ("{0}: {1} (exists but has 0 pages)" -f $caseTitle, $docFilename)
                    }
                }
            }
        }
    }
    # Check for missing documents
    foreach ($caseTitle in $requiredDocs.Keys) {
        $required = $requiredDocs[$caseTitle]
        foreach ($reqDoc in $required) {
            $found = $false
            foreach ($line in $verifyLines) {
                $fields = $line -split '\|'
                if ($fields.Count -ge 5 -and $fields[1].Trim() -eq $caseTitle -and $fields[3].Trim() -eq $reqDoc) {
                    $found = $true
                    break
                }
            }
            if (-not $found) {
                $missingDocs += ("{0}: {1} (not found)" -f $caseTitle, $reqDoc)
            }
        }
    }
    if ($missingDocs.Count -gt 0) {
        Write-Host "[WARN] Some required documents are missing or incomplete:" -ForegroundColor Yellow
        foreach ($missing in $missingDocs) {
            Write-Host "  - $missing" -ForegroundColor Yellow
        }
        Write-Host "[WARN] Tests may fail. Re-run seed if needed." -ForegroundColor Yellow
    } else {
        Write-Host "[OK] All required documents verified" -ForegroundColor Green
    }
} else {
    Write-Host "[WARN] Could not verify documents: $($verifyResult.Output)" -ForegroundColor Yellow
}

# Step 6: Extract demo IDs from seed output
$demoCaseId = ""
$demoDocId = ""
if ($seed.Output) {
    $seedLines = $seed.Output -split "`n"
    foreach ($line in $seedLines) {
        if ($line -match "DEMO_CASE_ID=(.+)") {
            $demoCaseId = $matches[1]
        }
        if ($line -match "DEMO_DOC_ID=(.+)") {
            $demoDocId = $matches[1]
        }
    }
}

# Final summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "[OK] PILOT RESET COMPLETE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Access URLs:" -ForegroundColor Yellow
Write-Host "  Frontend:     http://localhost:3000/dashboard" -ForegroundColor White
Write-Host "  API Docs:     http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Health Check: http://localhost:8000/api/v1/health/deep" -ForegroundColor White
Write-Host "  MinIO:        http://localhost:9001 (minioadmin / change_me)" -ForegroundColor White
Write-Host "  MailHog:      http://localhost:8025" -ForegroundColor White
Write-Host ""
Write-Host "Demo Credentials:" -ForegroundColor Yellow
Write-Host "  OrgA Admin:    admin@orga.com (any password)" -ForegroundColor White
Write-Host "  OrgA Reviewer: reviewer@orga.com" -ForegroundColor White
Write-Host "  OrgB Admin:   admin@orgb.com" -ForegroundColor White
Write-Host ""
if ($demoCaseId) {
    Write-Host "Demo IDs (for smoke tests):" -ForegroundColor Yellow
    Write-Host "  DEMO_CASE_ID=$demoCaseId" -ForegroundColor White
    if ($demoDocId) {
        Write-Host "  DEMO_DOC_ID=$demoDocId" -ForegroundColor White
    }
}
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Run smoke tests: ./scripts/dev/smoke_test.ps1" -ForegroundColor White
Write-Host "  2. Open dashboard and login as admin@orga.com" -ForegroundColor White
Write-Host "  3. Navigate through cases, documents, and exports" -ForegroundColor White
Write-Host ""

