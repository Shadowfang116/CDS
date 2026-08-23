# CDS-GOLD-001 end-to-end against the Urdu PDF corpus.
param(
    [string]$CorpusRoot = "C:\Users\fahad\Downloads\CDS_GOLD_001_URDU_PDF_CORPUS",
    [string]$ApiBase = "http://localhost:8000"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Get-ContentType([string]$ext) {
    switch ($ext.ToLower()) {
        ".pdf" { "application/pdf" }
        default { "application/octet-stream" }
    }
}

function Invoke-Login {
    $session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    $body = @{ email = "admin@orga.com"; password = "ChangeMe123!" } | ConvertTo-Json
    $resp = Invoke-WebRequest -Uri "$ApiBase/api/v1/auth/login" -Method POST -Body $body -ContentType "application/json" -WebSession $session -UseBasicParsing
    if ($resp.StatusCode -ne 200) { throw "Login failed: $($resp.StatusCode)" }
    $cookie = $session.Cookies.GetCookies($ApiBase) | Where-Object { $_.Name -eq "access_token" }
    if (-not $cookie) { throw "No access_token cookie after login" }
    return @{ Session = $session; CookieHeader = "access_token=$($cookie.Value)" }
}

function Upload-Docs($session, $cookieHeader, $caseId, $paths) {
    $ids = @()
    $uploadUrl = "$ApiBase/api/v1/cases/$caseId/documents"
    foreach ($path in $paths) {
        $name = [IO.Path]::GetFileName($path)
        Write-Host "  Uploading $name" -ForegroundColor Gray
        $curl = curl.exe -s -X POST -H "Cookie: $cookieHeader" -F "file=@$path" $uploadUrl
        $data = $curl | ConvertFrom-Json
        if (-not $data.id) { throw "Upload failed for $name : $curl" }
        $ids += $data.id
        Write-Host "    $($data.id)" -ForegroundColor Green
    }
    return $ids
}

function Wait-Ocr($session, $docIds, [int]$timeoutSec = 240) {
    foreach ($docId in $docIds) {
        Write-Host "  OCR wait $docId" -ForegroundColor Gray
        $deadline = (Get-Date).AddSeconds($timeoutSec)
        $done = $false
        while ((Get-Date) -lt $deadline) {
            Start-Sleep -Seconds 3
            try {
                $status = Invoke-RestMethod -Uri "$ApiBase/api/v1/documents/$docId/ocr-status" -WebSession $session
                $total = [int]$status.total_pages
                $doneCount = [int]$status.done_count
                $failedCount = [int]$status.failed_count
                if ($total -gt 0 -and $doneCount -eq $total -and $failedCount -eq 0) {
                    $done = $true
                    break
                }
                if ($failedCount -gt 0) { throw "OCR failed for $docId ($failedCount pages)" }
            } catch {
                if ($_.Exception.Message -like "OCR failed*") { throw }
            }
        }
        if (-not $done) { throw "OCR timeout for $docId" }
        Write-Host "    OCR done" -ForegroundColor Green
    }
}

function Enqueue-Ocr($session, $docIds) {
    foreach ($docId in $docIds) {
        try {
            Invoke-WebRequest -Uri "$ApiBase/api/v1/documents/$docId/ocr?force=false" -Method POST -WebSession $session -UseBasicParsing | Out-Null
            Write-Host "  OCR queued $docId" -ForegroundColor Gray
        } catch {
            Write-Host "  OCR enqueue warn $docId : $_" -ForegroundColor Yellow
        }
    }
}

Write-Host "=== CDS-GOLD-001 / RUN 3 E2E ===" -ForegroundColor Cyan
$init = @(Get-ChildItem "$CorpusRoot\01_INITIAL_EVIDENCE\*.pdf" | Sort-Object Name | ForEach-Object { $_.FullName })
$extra = @(Get-ChildItem "$CorpusRoot\02_ADDITIONAL_EVIDENCE\*.pdf" | Sort-Object Name | ForEach-Object { $_.FullName })
if ($init.Count -lt 11) { throw "Expected 11 initial PDFs, got $($init.Count)" }
if ($extra.Count -lt 5) { throw "Expected 5 additional PDFs, got $($extra.Count)" }

function Invoke-LoginAs([string]$email) {
    $session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    $body = @{ email = $email; password = "ChangeMe123!" } | ConvertTo-Json
    $resp = Invoke-WebRequest -Uri "$ApiBase/api/v1/auth/login" -Method POST -Body $body -ContentType "application/json" -WebSession $session -UseBasicParsing
    if ($resp.StatusCode -ne 200) { throw "Login failed for $email : $($resp.StatusCode)" }
    $cookie = $session.Cookies.GetCookies($ApiBase) | Where-Object { $_.Name -eq "access_token" }
    if (-not $cookie) { throw "No access_token cookie after login as $email" }
    return @{ Session = $session; CookieHeader = "access_token=$($cookie.Value)"; Email = $email }
}

function Write-Exceptions($label, $payload) {
    Write-Host "`n  $label" -ForegroundColor DarkCyan
    $items = @($payload.exceptions)
    if (-not $items -or $items.Count -eq 0) {
        Write-Host "    (none)" -ForegroundColor Gray
        return
    }
    foreach ($item in $items) {
        Write-Host ("    [{0}] {1}  {2}  {3}" -f $item.status, $item.severity, $item.rule_id, $item.title)
    }
}

$auth = Invoke-LoginAs "admin@orga.com"
$session = $auth.Session
$cookieHeader = $auth.CookieHeader
Write-Host "[OK] Logged in as admin@orga.com" -ForegroundColor Green

$caseBody = @{ title = "CDS-GOLD-001 / RUN 3" } | ConvertTo-Json
$case = Invoke-RestMethod -Uri "$ApiBase/api/v1/cases" -Method POST -Body $caseBody -ContentType "application/json" -WebSession $session
$caseId = $case.id
Write-Host "[OK] Case $caseId" -ForegroundColor Green
Write-Host "CASE_ID=$caseId"

Write-Host "`n[1] Initial evidence ($($init.Count) PDFs)" -ForegroundColor Yellow
$initIds = Upload-Docs $session $cookieHeader $caseId $init
Enqueue-Ocr $session $initIds
Wait-Ocr $session $initIds 300

Write-Host "`n[2] Autofill overwrite=true" -ForegroundColor Yellow
$autofill = Invoke-RestMethod -Uri "$ApiBase/api/v1/cases/$caseId/dossier/autofill?overwrite=true" -Method POST -WebSession $session
Write-Host ("  extracted={0} updated={1} skipped={2} errors={3}" -f $autofill.extracted.Count, $autofill.updated_fields.Count, $autofill.skipped_fields.Count, ($autofill.errors -join "; "))

Write-Host "`n[3] Evaluate rules (initial)" -ForegroundColor Yellow
$eval1 = Invoke-RestMethod -Uri "$ApiBase/api/v1/cases/$caseId/evaluate" -Method POST -WebSession $session
Write-Host ("  exceptions total={0} high={1} medium={2} low={3} cps={4} decision={5}" -f $eval1.total, $eval1.high, $eval1.medium, $eval1.low, $eval1.cps_total, $eval1.decision)
$ex1 = Invoke-RestMethod -Uri "$ApiBase/api/v1/cases/$caseId/exceptions" -WebSession $session
$cps1 = Invoke-RestMethod -Uri "$ApiBase/api/v1/cases/$caseId/cps" -WebSession $session
$cands = Invoke-RestMethod -Uri "$ApiBase/api/v1/cases/$caseId/ocr-extractions" -WebSession $session
Write-Exceptions "Initial findings" $ex1

Write-Host "`n[4] Additional evidence ($($extra.Count) PDFs)" -ForegroundColor Yellow
$extraIds = Upload-Docs $session $cookieHeader $caseId $extra
Enqueue-Ocr $session $extraIds
Wait-Ocr $session $extraIds 300

Write-Host "`n[5] Autofill + evaluate (after additional evidence)" -ForegroundColor Yellow
$autofill2 = Invoke-RestMethod -Uri "$ApiBase/api/v1/cases/$caseId/dossier/autofill?overwrite=true" -Method POST -WebSession $session
$eval2 = Invoke-RestMethod -Uri "$ApiBase/api/v1/cases/$caseId/evaluate" -Method POST -WebSession $session
$ex2 = Invoke-RestMethod -Uri "$ApiBase/api/v1/cases/$caseId/exceptions" -WebSession $session
$cps2 = Invoke-RestMethod -Uri "$ApiBase/api/v1/cases/$caseId/cps" -WebSession $session
$cands2 = Invoke-RestMethod -Uri "$ApiBase/api/v1/cases/$caseId/ocr-extractions" -WebSession $session
Write-Host ("  exceptions total={0} high={1} medium={2} low={3} cps={4} decision={5}" -f $eval2.total, $eval2.high, $eval2.medium, $eval2.low, $eval2.cps_total, $eval2.decision)
Write-Exceptions "After additional evidence" $ex2

$waiver = $null
$approval = $null
$eval3 = $null
$ex3 = $null
$cps3 = $null
$pack = $null

Write-Host "`n[6] Historic-tax waiver (reviewer propose, admin approve)" -ForegroundColor Yellow
$openItems = @($ex2.exceptions) | Where-Object { $_.status -eq "Open" }
$tax = @($openItems) | Where-Object { $_.rule_id -eq "GOLD-TAX-01" } | Select-Object -First 1
if (-not $tax) {
    Write-Host "  GOLD-TAX-01 is not open after additional evidence - waiver path skipped" -ForegroundColor Yellow
} else {
    $reviewer = Invoke-LoginAs "reviewer@orga.com"
    $waiverReason = "Current-year PT-10 shows paid. Historic 2019-20 paper receipt is unavailable; residual historic-tax finding waived with recorded reason."
    $waiverBody = @{
        case_id = $caseId
        request_type = "exception_waive"
        payload = @{
            exception_id = [string]$tax.id
            waiver_reason = $waiverReason
        }
    } | ConvertTo-Json -Depth 6
    $waiver = Invoke-RestMethod -Uri "$ApiBase/api/v1/approvals" -Method POST -Body $waiverBody -ContentType "application/json" -WebSession $reviewer.Session
    Write-Host ("  Proposed waiver {0} for {1}" -f $waiver.id, $tax.id) -ForegroundColor Green

    $approveBody = @{ reason = "Historic tax residual accepted. Current-year tax position is paid." } | ConvertTo-Json
    $approval = Invoke-RestMethod -Uri "$ApiBase/api/v1/approvals/$($waiver.id)/approve" -Method POST -Body $approveBody -ContentType "application/json" -WebSession $session
    Write-Host ("  Approved waiver status={0}" -f $approval.status) -ForegroundColor Green

    Write-Host "`n[7] Re-evaluate after waiver" -ForegroundColor Yellow
    $eval3 = Invoke-RestMethod -Uri "$ApiBase/api/v1/cases/$caseId/evaluate" -Method POST -WebSession $session
    $ex3 = Invoke-RestMethod -Uri "$ApiBase/api/v1/cases/$caseId/exceptions" -WebSession $session
    $cps3 = Invoke-RestMethod -Uri "$ApiBase/api/v1/cases/$caseId/cps" -WebSession $session
    Write-Host ("  exceptions total={0} high={1} medium={2} low={3} cps={4} decision={5}" -f $eval3.total, $eval3.high, $eval3.medium, $eval3.low, $eval3.cps_total, $eval3.decision)
    Write-Exceptions "After waiver re-eval" $ex3
}

Write-Host "`n[8] Bank pack" -ForegroundColor Yellow
try {
    $pack = Invoke-RestMethod -Uri "$ApiBase/api/v1/cases/$caseId/exports/bank-pack" -Method POST -WebSession $session
    Write-Host ("  export id={0} status={1} type={2}" -f $pack.export_id, $pack.status, $pack.export_type) -ForegroundColor Green
} catch {
    Write-Host "  Bank pack request failed: $_" -ForegroundColor Yellow
}

$outDir = Join-Path $PSScriptRoot "..\..\AI_context\execution_reports"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$jsonPath = Join-Path $outDir "cds_gold_001_e2e_$stamp.json"
$result = [ordered]@{
    case_id = $caseId
    run = "RUN 3"
    url = "http://localhost:3000/dashboard/cases/$caseId"
    initial_doc_ids = $initIds
    additional_doc_ids = $extraIds
    autofill_initial = $autofill
    eval_initial = $eval1
    exceptions_initial = $ex1
    cps_initial = $cps1
    candidates_initial = $cands
    autofill_after_additional = $autofill2
    eval_after_additional = $eval2
    exceptions_after_additional = $ex2
    cps_after_additional = $cps2
    candidates_after_additional = $cands2
    waiver_request = $waiver
    waiver_approval = $approval
    eval_after_waiver = $eval3
    exceptions_after_waiver = $ex3
    cps_after_waiver = $cps3
    bank_pack = $pack
}
$result | ConvertTo-Json -Depth 12 | Set-Content -Encoding utf8 $jsonPath
Write-Host "`nWrote $jsonPath" -ForegroundColor Cyan
Write-Host "Open http://localhost:3000/dashboard/cases/$caseId"
Write-Host "CASE_ID=$caseId"
