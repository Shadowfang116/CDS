#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Push-Location "$PSScriptRoot\..\..\backend"
try {
  $env:PYTHONPATH = "."
  python tests\run_mvp_tests.py
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
  Pop-Location
}
