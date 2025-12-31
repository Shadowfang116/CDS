#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Verify key backend route configurations inside the api container.

.DESCRIPTION
    This script uses PowerShell-safe grep patterns (multiple -e flags, no regex pipes)
    to verify that required backend configurations are present. It uses direct grep
    (no pipes) which is robust in PowerShell:
    
    - Grep's exit code is preserved (0 = matches, 1 = no matches, 2+ = error)
    - No shell quoting/escaping issues
    - Output is captured directly in PowerShell for display
    
    For manual verification with the robust sh wrapper pattern (handles pipes),
    see the one-liners in README.md.

.EXAMPLE
    .\scripts\dev\verify_backend_routes.ps1
#>

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$script:exitCode = 0
$script:checksRun = 0
$script:checksPassed = 0

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host $Title -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
}

function Test-ApiContainerRunning {
    Write-Host "Checking if api container is running..." -ForegroundColor Gray
    $containerId = docker compose ps -q api 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to query container status: $containerId" -ForegroundColor Red
        return $false
    }
    
    if ([string]::IsNullOrWhiteSpace($containerId)) {
        Write-Host "[ERROR] API container is not running. Start with: docker compose up -d" -ForegroundColor Red
        return $false
    }
    
    Write-Host "[OK] API container is running (ID: $($containerId.Trim()))" -ForegroundColor Green
    return $true
}

function Invoke-Grep {
    <#
    .SYNOPSIS
        Run grep with a single pattern inside the api container and return results.
    
    .DESCRIPTION
        Uses direct grep via sh -lc (no pipes) to avoid shell quoting issues.
        Captures output and exit code in PowerShell for reliable checking.
    
    .PARAMETER File
        Path to file inside container (relative to /app)
    
    .PARAMETER Pattern
        Single pattern to search for
    
    .PARAMETER PreviewLines
        Number of matching lines to preview (default 5)
    
    .OUTPUTS
        PSCustomObject with:
        - Success: bool (pattern found)
        - ExitCode: int (grep exit code)
        - Output: string[] (matching lines)
        - Error: string (error message if any)
    #>
    param(
        [Parameter(Mandatory)]
        [string]$File,
        
        [Parameter(Mandatory)]
        [string]$Pattern,
        
        [int]$PreviewLines = 5
    )
    
    # Build grep command - use sh -lc with direct grep (no pipes)
    # Escape single quotes in pattern and file path by replacing ' with '\''
    $escapedPattern = $Pattern -replace "'", "'\''"
    $escapedFile = $File -replace "'", "'\''"
    # Use single quotes for the entire sh command to avoid PowerShell interpolation
    $grepCmd = "grep -n -e '$escapedPattern' '$escapedFile'"
    
    try {
        # Run grep via sh -lc - capture both stdout and stderr
        # Pass the command as a single-quoted string to sh -lc
        $output = docker compose exec -T api sh -lc $grepCmd 2>&1
        $cmdExitCode = $LASTEXITCODE
        
        # Parse output - ensure we always have an array
        $outputStr = if ($output -is [array]) { $output -join "`n" } else { "$output" }
        $lines = @(($outputStr -split "`n") | Where-Object { $_.Trim() -ne "" })
        
        return [PSCustomObject]@{
            Success = ($cmdExitCode -eq 0 -and $lines.Count -gt 0)
            ExitCode = $cmdExitCode
            Output = $lines
            PreviewLines = @($lines | Select-Object -First $PreviewLines)
            Error = if ($cmdExitCode -ge 2) { $outputStr } else { $null }
        }
    } catch {
        return [PSCustomObject]@{
            Success = $false
            ExitCode = -1
            Output = @()
            PreviewLines = @()
            Error = $_.Exception.Message
        }
    }
}

function Assert-Pattern {
    <#
    .SYNOPSIS
        Check if a pattern exists in a file and report PASS/FAIL.
    
    .PARAMETER File
        Path to file inside container (relative to /app)
    
    .PARAMETER Pattern
        Pattern to search for
    
    .PARAMETER Description
        Human-readable description of what is being checked
    #>
    param(
        [Parameter(Mandatory)]
        [string]$File,
        
        [Parameter(Mandatory)]
        [string]$Pattern,
        
        [Parameter(Mandatory)]
        [string]$Description
    )
    
    $script:checksRun++
    
    Write-Host "  Checking: $Description" -ForegroundColor Yellow -NoNewline
    Write-Host " (pattern: '$Pattern')" -ForegroundColor Gray
    
    $result = Invoke-Grep -File $File -Pattern $Pattern -PreviewLines 3
    
    if ($result.Success) {
        Write-Host "    [PASS] Pattern found" -ForegroundColor Green
        $previewArray = @($result.PreviewLines)
        $outputArray = @($result.Output)
        if ($previewArray.Count -gt 0) {
            foreach ($line in $previewArray) {
                Write-Host "      $line" -ForegroundColor DarkGreen
            }
            if ($outputArray.Count -gt $previewArray.Count) {
                Write-Host "      ... ($($outputArray.Count - $previewArray.Count) more lines)" -ForegroundColor Gray
            }
        }
        $script:checksPassed++
        return $true
    } elseif ($result.ExitCode -eq 1) {
        Write-Host "    [FAIL] Pattern not found (exit code: 1)" -ForegroundColor Red
        $script:exitCode = 1
        return $false
    } else {
        Write-Host "    [FAIL] Grep error (exit code: $($result.ExitCode))" -ForegroundColor Red
        if ($result.Error) {
            $preview = ($result.Error -split "`n" | Select-Object -First 2) -join " "
            Write-Host "      Error: $preview" -ForegroundColor DarkRed
        }
        $script:exitCode = 1
        return $false
    }
}

# =============================================================================
# MAIN
# =============================================================================

Write-Section "Backend Route Verification"
Write-Host "Verifying key backend configurations are present in the api container..."

# Check container is running
if (-not (Test-ApiContainerRunning)) {
    Write-Host ""
    Write-Host "[FATAL] Cannot proceed without running api container." -ForegroundColor Red
    exit 1
}

# -----------------------------------------------------------------------------
# A) verification.py - Evidence gate and request body parsing
# -----------------------------------------------------------------------------
Write-Section "A) Verification Endpoint Evidence Gate"
Write-Host "File: app/api/routes/verification.py" -ForegroundColor Gray
Write-Host ""

$fileA = "app/api/routes/verification.py"
Assert-Pattern -File $fileA -Pattern "MarkVerifiedRequest" -Description "MarkVerifiedRequest class" | Out-Null
Assert-Pattern -File $fileA -Pattern "force" -Description "force field" | Out-Null
Assert-Pattern -File $fileA -Pattern "evidence" -Description "evidence references" | Out-Null
Assert-Pattern -File $fileA -Pattern "Body" -Description "Body import/usage" | Out-Null

# -----------------------------------------------------------------------------
# B) OCR Text Corrections - api_route with PUT+POST methods
# -----------------------------------------------------------------------------
Write-Section "B) OCR Correction Route (PUT+POST)"
Write-Host "File: app/api/routes/ocr_text_corrections.py" -ForegroundColor Gray
Write-Host ""

$fileB = "app/api/routes/ocr_text_corrections.py"
Assert-Pattern -File $fileB -Pattern "api_route" -Description "api_route decorator" | Out-Null
Assert-Pattern -File $fileB -Pattern "ocr-text/correction" -Description "ocr-text/correction endpoint" | Out-Null
Assert-Pattern -File $fileB -Pattern "PUT" -Description "PUT method" | Out-Null
Assert-Pattern -File $fileB -Pattern "POST" -Description "POST method" | Out-Null

# -----------------------------------------------------------------------------
# C) Document Conversion - LibreOffice flags and profile config
# -----------------------------------------------------------------------------
Write-Section "C) LibreOffice Conversion Configuration"
Write-Host "File: app/services/doc_convert.py" -ForegroundColor Gray
Write-Host ""

$fileC = "app/services/doc_convert.py"
Assert-Pattern -File $fileC -Pattern "UserInstallation" -Description "UserInstallation flag" | Out-Null
Assert-Pattern -File $fileC -Pattern "lo-profile" -Description "lo-profile directory" | Out-Null
Assert-Pattern -File $fileC -Pattern "nolockcheck" -Description "nolockcheck flag" | Out-Null
Assert-Pattern -File $fileC -Pattern "nodefault" -Description "nodefault flag" | Out-Null
Assert-Pattern -File $fileC -Pattern "norestore" -Description "norestore flag" | Out-Null
Assert-Pattern -File $fileC -Pattern "HOME" -Description "HOME environment variable" | Out-Null

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
Write-Section "Summary"

Write-Host "Checks run: $script:checksRun" -ForegroundColor Gray
Write-Host "Checks passed: $script:checksPassed" -ForegroundColor $(if ($script:checksPassed -eq $script:checksRun) { "Green" } else { "Yellow" })

if ($script:exitCode -eq 0) {
    Write-Host ""
    Write-Host "[OK] All backend route verifications passed!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "[FAIL] Some verifications failed. Check output above." -ForegroundColor Red
}

# Print one-liner commands for manual verification
Write-Host ""
Write-Host "Manual verification one-liners (PowerShell-safe):" -ForegroundColor Cyan
Write-Host "Simple direct grep (exit code 0 = found, 1 = not found):" -ForegroundColor Gray
Write-Host ""

Write-Host "# A) Verification endpoint (evidence gate + Body parsing):" -ForegroundColor DarkGray
Write-Host 'docker compose exec -T api grep -n -e MarkVerifiedRequest -e force -e evidence -e Body app/api/routes/verification.py' -ForegroundColor White
Write-Host ""

Write-Host "# B) OCR correction route (api_route with PUT+POST):" -ForegroundColor DarkGray
Write-Host 'docker compose exec -T api grep -n -e api_route -e ocr-text/correction -e PUT -e POST app/api/routes/ocr_text_corrections.py' -ForegroundColor White
Write-Host ""

Write-Host "# C) LibreOffice configuration:" -ForegroundColor DarkGray
Write-Host 'docker compose exec -T api grep -n -e UserInstallation -e lo-profile -e nolockcheck -e nodefault -e norestore -e HOME app/services/doc_convert.py' -ForegroundColor White
Write-Host ""

Write-Host "Robust sh wrapper pattern (handles grep exit codes with head pipe):" -ForegroundColor Gray
Write-Host "See README.md for the full commands with the sh wrapper pattern." -ForegroundColor Gray
Write-Host ""

exit $script:exitCode
