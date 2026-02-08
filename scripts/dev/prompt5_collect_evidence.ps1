#!/usr/bin/env pwsh
# Prompt 5 Evidence Collection Script
# Re-runs autofill, collects debug logs, and runs SQL proof queries
# P19: Accepts parameters for Case ID, Sale Deed Doc ID, and Fard Doc ID

param(
    [Parameter(Mandatory=$false)]
    [string]$CaseId = "f14f2276-96c0-4f06-aea8-5a9c9eb9a9c8",
    
    [Parameter(Mandatory=$false)]
    [string]$SaleDeedDocId = "8fa48b2d-c169-450e-8b16-8855b6a83def",
    
    [Parameter(Mandatory=$false)]
    [string]$FardDocId = "a81b1693-63b4-4f94-b22e-21624d432c58"
)

# Set UTF-8 encoding for proper Urdu display
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Context IDs (from parameters or defaults)
$CASE_ID = $CaseId
$SALE_DEED_DOC_ID = $SaleDeedDocId
$FARD_DOC_ID = $FardDocId

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PROMPT 5 EVIDENCE COLLECTION" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step A: Check Docker engine (hard fail if not reachable)
Write-Host "[1/9] Checking Docker engine..." -ForegroundColor Yellow
try {
    docker --version | Out-Null
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[FAIL] Docker engine is not running. Please start Docker Desktop." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "[FAIL] Docker not found or engine not running. Please install/start Docker Desktop." -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Docker engine is reachable" -ForegroundColor Green

# Step B: Ensure containers are up
Write-Host ""
Write-Host "[2/9] Ensuring containers are up..." -ForegroundColor Yellow
try {
    $result = docker compose up -d 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) {
        if ($result -match "pipe|engine|connect") {
            Write-Host "[FAIL] Docker engine is not running. Please start Docker Desktop." -ForegroundColor Red
            exit 1
        }
        # Check if containers are already running (this is OK)
        $running = docker compose ps --format json 2>&1 | ConvertFrom-Json
        if ($running) {
            Write-Host "[OK] Containers already running" -ForegroundColor Green
        } else {
            Write-Host "[FAIL] Failed to start containers: $result" -ForegroundColor Red
            exit 1
        }
    } else {
        Start-Sleep -Seconds 3
    }
} catch {
    # Check if containers are running anyway
    try {
        $running = docker compose ps --format json 2>&1 | ConvertFrom-Json
        if ($running) {
            Write-Host "[OK] Containers are running" -ForegroundColor Green
        } else {
            Write-Host "[FAIL] Failed to start containers: $_" -ForegroundColor Red
            exit 1
        }
    } catch {
        Write-Host "[FAIL] Failed to start containers: $_" -ForegroundColor Red
        exit 1
    }
}
Write-Host "[OK] Containers up" -ForegroundColor Green

# Step C: Rebuild API and worker to pick up latest code
Write-Host ""
Write-Host "[3/9] Rebuilding API and worker containers..." -ForegroundColor Yellow
try {
    $result = docker compose up -d --build api worker 2>&1
    if ($LASTEXITCODE -ne 0) {
        if ($result -match "pipe|engine|connect") {
            Write-Host "[FAIL] Docker engine is not running. Please start Docker Desktop." -ForegroundColor Red
            exit 1
        }
        Write-Host "[WARN] API/worker rebuild failed, continuing: $result" -ForegroundColor Yellow
    } else {
        Start-Sleep -Seconds 5
    }
} catch {
    Write-Host "[WARN] API/worker rebuild failed, continuing: $_" -ForegroundColor Yellow
}
Write-Host "[OK] API and worker rebuilt" -ForegroundColor Green

# Step D: Dev-login (with retry)
Write-Host ""
Write-Host "[4/9] Authenticating..." -ForegroundColor Yellow
$loginBody = @{
    email = "admin@orga.com"
    org_name = "OrgA"
    role = "Admin"
} | ConvertTo-Json

$maxRetries = 5
$retryCount = 0
$token = $null

while ($retryCount -lt $maxRetries -and -not $token) {
    try {
        Start-Sleep -Seconds 2
        $loginResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/auth/dev-login" -Method POST -Body $loginBody -ContentType "application/json" -UseBasicParsing -ErrorAction Stop
        $loginData = $loginResponse.Content | ConvertFrom-Json
        $token = $loginData.access_token
        if (-not $token) {
            throw "No access token received"
        }
    } catch {
        $retryCount++
        if ($retryCount -ge $maxRetries) {
            Write-Host "[FAIL] Authentication failed after $maxRetries attempts: $_" -ForegroundColor Red
            exit 1
        }
        Write-Host "[RETRY] Waiting for API to be ready (attempt $retryCount/$maxRetries)..." -ForegroundColor Yellow
    }
}
Write-Host "[OK] Authenticated" -ForegroundColor Green

$headers = @{
    "Authorization" = "Bearer $token"
}

# Step E: Verify case and documents exist before running autofill
Write-Host ""
Write-Host "[5/10] Verifying case and documents exist..." -ForegroundColor Yellow
$caseExists = $false
$saleDeedExists = $false
$fardExists = $false
$caseTitle = ""
$saleDeedFilename = ""
$fardFilename = ""

try {
    # Check case exists
    $caseQuery = "SELECT id, title FROM cases WHERE id = '$CASE_ID';"
    $caseResult = $caseQuery | docker compose exec -T db psql -U bank_diligence -d bank_diligence -t -A 2>&1
    if ($caseResult -match "^\s*[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\s*\|\s*(.+)$") {
        $caseExists = $true
        $caseTitle = ($caseResult -split '\|')[1].Trim()
        Write-Host "[OK] Case exists: $caseTitle" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] Case ID $CASE_ID not found in database" -ForegroundColor Red
        Write-Host "To list available cases, run:" -ForegroundColor Yellow
        Write-Host "  docker compose exec -T db psql -U bank_diligence -d bank_diligence -c 'SELECT id, title FROM cases LIMIT 10;'" -ForegroundColor Gray
        exit 1
    }
    
    # Check sale deed document exists
    $saleDeedQuery = "SELECT id, original_filename FROM documents WHERE id = '$SALE_DEED_DOC_ID';"
    $saleDeedResult = $saleDeedQuery | docker compose exec -T db psql -U bank_diligence -d bank_diligence -t -A 2>&1
    if ($saleDeedResult -match "^\s*[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\s*\|\s*(.+)$") {
        $saleDeedExists = $true
        $saleDeedFilename = ($saleDeedResult -split '\|')[1].Trim()
        Write-Host "[OK] Sale deed document exists: $saleDeedFilename" -ForegroundColor Green
    } else {
        Write-Host "[WARN] Sale deed document ID $SALE_DEED_DOC_ID not found" -ForegroundColor Yellow
    }
    
    # Check fard document exists
    $fardQuery = "SELECT id, original_filename FROM documents WHERE id = '$FARD_DOC_ID';"
    $fardResult = $fardQuery | docker compose exec -T db psql -U bank_diligence -d bank_diligence -t -A 2>&1
    if ($fardResult -match "^\s*[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\s*\|\s*(.+)$") {
        $fardExists = $true
        $fardFilename = ($fardResult -split '\|')[1].Trim()
        Write-Host "[OK] Fard document exists: $fardFilename" -ForegroundColor Green
    } else {
        Write-Host "[WARN] Fard document ID $FARD_DOC_ID not found" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[FAIL] Failed to verify case/documents: $_" -ForegroundColor Red
    exit 1
}

# Step E.5: One-time cleanup of existing party role rows (P20)
Write-Host ""
Write-Host "[5.5/10] Cleaning up existing party role rows..." -ForegroundColor Yellow
try {
    $cleanupQuery = @"
DELETE FROM ocr_extraction_candidates
WHERE case_id='$CASE_ID' AND document_id='$SALE_DEED_DOC_ID'
  AND field_key IN ('party.seller.names','party.buyer.names','party.witness.names');
"@
    $cleanupResult = $cleanupQuery | docker compose exec -T db psql -U bank_diligence -d bank_diligence -t -A 2>&1
    Write-Host "[OK] Cleanup completed" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Cleanup failed (continuing): $_" -ForegroundColor Yellow
}

# Step F: Re-run Autofill with overwrite=true (query param) - ONCE ONLY
Write-Host ""
Write-Host "[6/10] Re-running Autofill (overwrite=true) - SINGLE CALL..." -ForegroundColor Yellow
$autofillCallCount = 0
$autofillResponseJson = ""
try {
    $autofillCallCount++
    $autofillUrl = "http://localhost:8000/api/v1/cases/$CASE_ID/dossier/autofill?overwrite=true"
    $autofillResponse = Invoke-WebRequest -Uri $autofillUrl -Method POST -Headers $headers -ContentType "application/json" -UseBasicParsing -ErrorAction Stop
    
    # P19: Only process if status code is 200 (not 401 or other errors)
    if ($autofillResponse.StatusCode -eq 200) {
        $autofillData = $autofillResponse.Content | ConvertFrom-Json
        $autofillResponseJson = $autofillResponse.Content
        Write-Host "[OK] Autofill completed (status 200)" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] Autofill returned status code $($autofillResponse.StatusCode)" -ForegroundColor Red
        Write-Host "Response: $($autofillResponse.Content)" -ForegroundColor Red
        exit 1
    }
} catch {
    # P19: Do NOT retry on 401 or other errors - fail immediately
    Write-Host "[FAIL] Autofill failed: $_" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response: $responseBody" -ForegroundColor Red
    }
    exit 1
}
Write-Host "[INFO] Autofill called exactly $autofillCallCount time(s)" -ForegroundColor Cyan

# Step G: Capture run_id from logs and collect debug logs
Write-Host ""
Write-Host "[7/10] Capturing run_id and collecting debug logs..." -ForegroundColor Yellow
$runId = ""
try {
    # P20: Get last 1000 lines and find most recent request_id from START autofill log
    $allLogs = docker compose logs api --tail=1000 2>&1
    $startLogs = $allLogs | Select-String "DOSSIER_AUTOFILL_DEBUG: \[.*\] START autofill" | Select-Object -Last 1
    if ($startLogs) {
        if ($startLogs -match '\[([a-f0-9]{8})\]') {
            $runId = $matches[1]
            Write-Host "[OK] Captured run_id: $runId" -ForegroundColor Green
        } else {
            Write-Host "[WARN] Could not parse run_id from logs" -ForegroundColor Yellow
        }
    } else {
        Write-Host "[WARN] No START autofill log found" -ForegroundColor Yellow
    }
    
    # P16: Get last 200 lines containing PARTY_ROLES_DEBUG and OCR_FALLBACK
    $debugLogs = $allLogs | Select-String "PARTY_ROLES_DEBUG|DOSSIER_AUTOFILL_DEBUG|OCR_FALLBACK|EXIT party roles|ENTER write loop|EXCEPTION|Traceback|SKIP role=" | Select-Object -Last 200
    Write-Host "[OK] Debug logs collected (last 200 lines with PARTY_ROLES_DEBUG/OCR_FALLBACK)" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Failed to collect debug logs: $_" -ForegroundColor Yellow
    $debugLogs = @()
}

# Step I: Run SQL proof queries A-D
Write-Host ""
Write-Host "[8/10] Running SQL proof queries (A-D)..." -ForegroundColor Yellow
try {
    $sqlContent = Get-Content "scripts/dev/prompt5_sql_queries.sql" -Raw -ErrorAction Stop
    $sqlContent = $sqlContent -replace '<CASE_ID>', $CASE_ID
    $sqlContent = $sqlContent -replace '<SALE_DEED_DOC_ID>', $SALE_DEED_DOC_ID
    $sqlContent = $sqlContent -replace '<FARD_DOC_ID>', $FARD_DOC_ID
    
    $sqlOutput = $sqlContent | docker compose exec -T db psql -U bank_diligence -d bank_diligence 2>&1
    Write-Host "[OK] SQL queries executed" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] SQL queries failed: $_" -ForegroundColor Red
    $sqlOutput = "SQL query execution failed: $_"
}

# Step J: Optional debug SQL
Write-Host ""
Write-Host "[9/10] Running optional debug SQL..." -ForegroundColor Yellow
$debugSqlOutput = ""
if (Test-Path "scripts/dev/prompt5_party_roles_debug.sql") {
    try {
        $debugSqlContent = Get-Content "scripts/dev/prompt5_party_roles_debug.sql" -Raw -ErrorAction Stop
        $debugSqlContent = $debugSqlContent -replace '<CASE_ID>', $CASE_ID
        $debugSqlContent = $debugSqlContent -replace '<SALE_DEED_DOC_ID>', $SALE_DEED_DOC_ID
        $debugSqlContent = $debugSqlContent -replace '<FARD_DOC_ID>', $FARD_DOC_ID
        
        $debugSqlOutput = $debugSqlContent | docker compose exec -T db psql -U bank_diligence -d bank_diligence 2>&1
        Write-Host "[OK] Debug SQL executed" -ForegroundColor Green
    } catch {
        Write-Host "[WARN] Debug SQL failed: $_" -ForegroundColor Yellow
        $debugSqlOutput = "Debug SQL execution failed: $_"
    }
} else {
    Write-Host "[SKIP] Debug SQL file not found, skipping" -ForegroundColor Gray
}

# Step K: Optional OCR text excerpt
Write-Host ""
Write-Host "[10/10] Collecting OCR text excerpt and final summary..." -ForegroundColor Yellow
$ocrExcerpt = ""
try {
    $ocrQuery = @"
SELECT 
    page_number,
    ocr_confidence,
    SUBSTRING(ocr_text, 1, 400) AS ocr_text_excerpt
FROM document_pages
WHERE document_id = '$SALE_DEED_DOC_ID'
  AND page_number <= 2
ORDER BY page_number;
"@
    $ocrExcerpt = $ocrQuery | docker compose exec -T db psql -U bank_diligence -d bank_diligence 2>&1
    Write-Host "[OK] OCR excerpt collected" -ForegroundColor Green
} catch {
    Write-Host "[WARN] OCR excerpt failed: $_" -ForegroundColor Yellow
    $ocrExcerpt = "OCR excerpt collection failed: $_"
}

# Parse SQL output into queries A-D
# SQL output format: each query result is separated by headers
$queryAOutput = ""
$queryBOutput = ""
$queryCOutput = ""
$queryDOutput = ""

if ($sqlOutput) {
    # Split by query headers
    $parts = $sqlOutput -split "(?=field_key\s+\|\s+document_id|document_id\s+\|\s+document_name\s+\|\s+field_key|id\s+\|\s+field_key\s+\|\s+confidence|document_id\s+\|\s+page_number\s+\|\s+ocr_confidence)"
    
    foreach ($part in $parts) {
        if ($part -match "field_key\s+\|\s+document_id.*document_name.*page_number") {
            $queryAOutput = $part.Trim()
        } elseif ($part -match "document_id\s+\|\s+document_name\s+\|\s+field_key\s+\|\s+row_count") {
            $queryBOutput = $part.Trim()
        } elseif ($part -match "id\s+\|\s+field_key\s+\|\s+confidence" -and $part -notmatch "page_number") {
            $queryCOutput = $part.Trim()
        } elseif ($part -match "document_id\s+\|\s+page_number\s+\|\s+ocr_confidence") {
            $queryDOutput = $part.Trim()
        }
    }
    
    # If parsing failed, use full output for all
    if (-not $queryAOutput -and $sqlOutput) {
        $queryAOutput = $sqlOutput
        $queryBOutput = $sqlOutput
        $queryCOutput = $sqlOutput
        $queryDOutput = $sqlOutput
    }
}

# Print PASTE BACK TO CHATGPT block
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PASTE BACK TO CHATGPT" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "CASE AND DOCUMENT EXISTENCE:" -ForegroundColor Yellow
Write-Host "Case ID: $CASE_ID"
Write-Host "Case exists: $caseExists"
if ($caseExists) {
    Write-Host "Case title: $caseTitle"
}
Write-Host ""
Write-Host "Sale Deed Doc ID: $SALE_DEED_DOC_ID"
Write-Host "Sale deed exists: $saleDeedExists"
if ($saleDeedExists) {
    Write-Host "Sale deed filename: $saleDeedFilename"
}
Write-Host ""
Write-Host "Fard Doc ID: $FARD_DOC_ID"
Write-Host "Fard exists: $fardExists"
if ($fardExists) {
    Write-Host "Fard filename: $fardFilename"
}
Write-Host ""
Write-Host "AUTOFILL CALL COUNT: $autofillCallCount" -ForegroundColor Cyan
Write-Host ""

Write-Host "AUTOFILL RESPONSE:" -ForegroundColor Yellow
Write-Host $autofillResponseJson
Write-Host ""

Write-Host "PARTY_ROLES_DEBUG LOGS:" -ForegroundColor Yellow
if ($debugLogs) {
    $debugLogs | ForEach-Object { Write-Host $_ }
} else {
    Write-Host "(No PARTY_ROLES_DEBUG logs found)"
}
Write-Host ""

Write-Host "SQL QUERY A OUTPUT (Party Role Candidates):" -ForegroundColor Yellow
Write-Host $queryAOutput
Write-Host ""

Write-Host "SQL QUERY B OUTPUT (Duplicate Detector):" -ForegroundColor Yellow
Write-Host $queryBOutput
Write-Host ""

Write-Host "SQL QUERY C OUTPUT (Candidate Confidence Range):" -ForegroundColor Yellow
Write-Host $queryCOutput
Write-Host ""

Write-Host "SQL QUERY D OUTPUT (Page Confidence Range):" -ForegroundColor Yellow
Write-Host $queryDOutput
Write-Host ""

Write-Host "SQL QUERY E OUTPUT (Any party candidates):" -ForegroundColor Yellow
$queryEOutput = ""
try {
    $queryE = @"
SELECT field_key, document_id, COUNT(*) 
FROM ocr_extraction_candidates
WHERE case_id = '$CASE_ID'
  AND field_key LIKE 'party.%'
GROUP BY field_key, document_id
ORDER BY field_key, document_id;
"@
    $queryEOutput = $queryE | docker compose exec -T db psql -U bank_diligence -d bank_diligence 2>&1
} catch {
    $queryEOutput = "Query E failed: $_"
}
Write-Host $queryEOutput
Write-Host ""

Write-Host "SQL QUERY F OUTPUT (Latest 30 candidates):" -ForegroundColor Yellow
$queryFOutput = ""
try {
    $queryF = @"
SELECT created_at, field_key, document_id, confidence, LEFT(proposed_value,120) AS v
FROM ocr_extraction_candidates
WHERE case_id = '$CASE_ID'
ORDER BY created_at DESC
LIMIT 30;
"@
    $queryFOutput = $queryF | docker compose exec -T db psql -U bank_diligence -d bank_diligence 2>&1
} catch {
    $queryFOutput = "Query F failed: $_"
}
Write-Host $queryFOutput
Write-Host ""

# P20: Query J - Party roles for THIS RUN ONLY
Write-Host "RUN_ID: $runId" -ForegroundColor Cyan
Write-Host ""
if ($runId) {
    Write-Host "[Query J] SQL QUERY J OUTPUT (Party Roles for THIS RUN ONLY):" -ForegroundColor Yellow
    $queryJOutput = ""
    try {
        $queryJ = @"
SELECT 
  field_key, 
  document_id, 
  page_number, 
  confidence, 
  proposed_value, 
  run_id
FROM ocr_extraction_candidates
WHERE case_id = '$CASE_ID'::uuid
  AND document_id = '$SALE_DEED_DOC_ID'::uuid
  AND field_key IN ('party.seller.names','party.buyer.names','party.witness.names')
  AND run_id = '$runId'
ORDER BY field_key;
"@
        $queryJOutput = $queryJ | docker compose exec -T db psql -U bank_diligence -d bank_diligence 2>&1
        Write-Host $queryJOutput
    } catch {
        $queryJOutput = "Query J failed: $_"
        Write-Host $queryJOutput
    }
    Write-Host ""
    
    # P20: Validation summary
    if ($queryJOutput -match "\((\d+) rows?\)") {
        $rowCount = [int]$matches[1]
        Write-Host "VALIDATION SUMMARY:" -ForegroundColor Cyan
        Write-Host "Query J row count: $rowCount" -ForegroundColor Cyan
        if ($rowCount -eq 3) {
            Write-Host "PASS: Query J returns exactly 3 rows" -ForegroundColor Green
        } else {
            Write-Host "FAIL: Query J returns $rowCount rows (expected 3)" -ForegroundColor Red
        }
        
        # Check logs for party_role_items_count, attempted_party, written_party
        $logText = $debugLogs -join "`n"
        $itemsCount = ""
        $attempted = ""
        $written = ""
        if ($logText -match "party_role_items_count=(\d+)") {
            $itemsCount = $matches[1]
            Write-Host "party_role_items_count: $itemsCount" -ForegroundColor Cyan
        }
        if ($logText -match "attempted_party=(\d+)") {
            $attempted = $matches[1]
            Write-Host "attempted_party: $attempted" -ForegroundColor Cyan
        }
        if ($logText -match "written_party=(\d+)") {
            $written = $matches[1]
            Write-Host "written_party: $written" -ForegroundColor Cyan
        }
        
        # Check for roles_present/roles_missing in logs
        if ($logText -match "roles_present=\[([^\]]+)\]") {
            $rolesPresent = $matches[1]
            Write-Host "roles_present: $rolesPresent" -ForegroundColor Cyan
        }
        if ($logText -match "roles_missing=\[([^\]]+)\]") {
            $rolesMissing = $matches[1]
            Write-Host "roles_missing: $rolesMissing" -ForegroundColor Cyan
        }
    }
    Write-Host ""
    
    # P23: Query K - Party names must not contain newlines or leading/trailing whitespace
    Write-Host "SQL QUERY K OUTPUT (Party names must be clean - regression check):" -ForegroundColor Yellow
    $queryKOutput = ""
    $queryKRowCount = 0
    try {
        $queryK = @"
SELECT field_key, proposed_value
FROM ocr_extraction_candidates
WHERE run_id = '$runId'
  AND field_key LIKE 'party.%'
  AND (
    proposed_value LIKE E'%\n%'
    OR proposed_value LIKE E'%\r%'
    OR proposed_value ~ '(^\\s|\\s$)'
  );
"@
        $queryKOutput = $queryK | docker compose exec -T db psql -U bank_diligence -d bank_diligence 2>&1
        Write-Host $queryKOutput
        
        # Extract row count
        if ($queryKOutput -match "\((\d+) rows?\)") {
            $queryKRowCount = [int]$matches[1]
        }
    } catch {
        $queryKOutput = "Query K failed: $_"
        Write-Host $queryKOutput
    }
    Write-Host ""
    
    # P23: Hard fail if Query K returns rows > 0
    if ($queryKRowCount -gt 0) {
        Write-Host "FAIL: Query K returned $queryKRowCount rows (expected 0) - party names contain newlines/whitespace!" -ForegroundColor Red
        exit 1
    } else {
        Write-Host "PASS: Query K returned 0 rows - all party names are clean" -ForegroundColor Green
    }
    
    # Add to PASTE BACK block (output already printed above)
    Write-Host ""
    Write-Host "SQL QUERY K OUTPUT (Party names must be clean - regression check):" -ForegroundColor Yellow
    Write-Host $queryKOutput
    Write-Host ""
    Write-Host "query_k_rows_count: $queryKRowCount" -ForegroundColor Cyan
    $partyNamesClean = if ($queryKRowCount -eq 0) { "PASS" } else { "FAIL" }
    Write-Host "party_names_clean: $partyNamesClean" -ForegroundColor $(if ($partyNamesClean -eq "PASS") { "Green" } else { "Red" })
    Write-Host ""
}

if ($debugSqlOutput) {
    Write-Host "DEBUG SQL OUTPUT:" -ForegroundColor Yellow
    Write-Host $debugSqlOutput
    Write-Host ""
}

if ($ocrExcerpt) {
    Write-Host "OCR TEXT EXCERPT (Sale Deed, Pages 1-2):" -ForegroundColor Yellow
    Write-Host $ocrExcerpt
    Write-Host ""
}

# Final summary: Check Query A results
Write-Host "FINAL SUMMARY:" -ForegroundColor Yellow
if ($queryAOutput) {
    # Count rows in Query A output
    $queryARowsArray = $queryAOutput -split "`n" | Where-Object { $_ -match "party\.(seller|buyer|witness)\.names" }
    $queryARows = if ($queryARowsArray) { $queryARowsArray.Count } else { 0 }
    Write-Host "Query A row count: $queryARows" -ForegroundColor $(if ($queryARows -eq 3) { "Green" } else { "Red" })
    
    # Check for plausibility (no blacklisted terms)
    $hasGarbage = $false
    $blacklistTerms = @("EXECUTED BY", "De eo re", "vendor", "vendee", "witness", "signature")
    foreach ($term in $blacklistTerms) {
        if ($queryAOutput -match $term) {
            $hasGarbage = $true
            Write-Host "WARNING: Query A contains blacklisted term: $term" -ForegroundColor Red
        }
    }
    
    if ($queryARows -eq 3 -and -not $hasGarbage) {
        Write-Host "PASS: Query A returns exactly 3 rows with plausible names" -ForegroundColor Green
    } else {
        Write-Host "FAIL: Query A does not meet requirements" -ForegroundColor Red
    }
} else {
    Write-Host "WARNING: Could not parse Query A output" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "END" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

