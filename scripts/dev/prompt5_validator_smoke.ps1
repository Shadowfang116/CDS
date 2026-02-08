#!/usr/bin/env pwsh
# Prompt 5 Validator Smoke Test
# Tests validator functions directly in the API container

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PROMPT 5 VALIDATOR SMOKE TEST" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Docker
Write-Host "[1/2] Checking Docker..." -ForegroundColor Yellow
try {
    docker info | Out-Null
    Write-Host "[OK] Docker engine is reachable" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] Docker engine is not running" -ForegroundColor Red
    exit 1
}

# Step 2: Run validator tests
Write-Host ""
Write-Host "[2/2] Running validator tests..." -ForegroundColor Yellow

$pythonScript = @'
from app.services.extractors.validators import is_probably_name_line

def compute_letter_ratio(text: str) -> float:
    """Compute letter ratio using Unicode-aware isalpha()."""
    s2 = "".join(ch for ch in text if not ch.isspace())
    if not s2:
        return 0.0
    letters = sum(1 for ch in s2 if ch.isalpha())
    return letters / len(s2)

tests = [
    "کاشف زابد",
    "EXECUTED BY",
    "De eo re; wal Sch",
    "THE BANK OF PUNJAB",
    "Muhammad Ali",
    "IN WITNESS WHEREOF"
]

print("Test Name", "=>", "Result", "Letter Ratio", sep="\t")
print("-" * 80)

for test_name in tests:
    try:
        is_valid, warning = is_probably_name_line(test_name)
        ratio = compute_letter_ratio(test_name)
        result_str = f"PASS" if is_valid else f"FAIL: {warning}"
        print(f"{test_name[:40]:40} => {result_str:30} ratio={ratio:.2f}")
    except Exception as e:
        print(f"{test_name[:40]:40} => EXCEPTION: {e}")

print("-" * 80)
print("")
print("Expected:")
print("  - 'کاشف زابد' should PASS")
print("  - 'EXECUTED BY' should FAIL")
print("  - 'De eo re; wal Sch' should FAIL")
print("  - 'IN WITNESS WHEREOF' should FAIL")
'@

$output = $pythonScript | docker compose exec -T api python 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] Validator test failed:" -ForegroundColor Red
    Write-Host $output
    exit 1
}

Write-Host "[OK] Validator test completed" -ForegroundColor Green
Write-Host ""
Write-Host $output
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "END" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

