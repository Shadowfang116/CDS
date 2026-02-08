#!/usr/bin/env pwsh
# Generate example DOCX file using python-docx in docker container
param(
    [string]$OutputPath = "docs\pilot_samples_real_example\PILOT_DEMO_OPINION.docx"
)

$ErrorActionPreference = "Stop"

# Ensure output directory exists
$outputDir = Split-Path -Parent $OutputPath
if ($outputDir -and -not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

# Generate DOCX using python-docx in the api container
$pythonScript = @'
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import os

doc = Document()

# Title
title = doc.add_heading('LEGAL OPINION', level=0)
title.alignment = WD_ALIGN_PARAGRAPH.CENTER

doc.add_paragraph('')

# Subtitle
subtitle = doc.add_paragraph('Property Transfer Analysis Report')
subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER

doc.add_paragraph('')

# Property Details Section
doc.add_heading('Property Details', level=1)
table = doc.add_table(rows=5, cols=2)
table.style = 'Table Grid'

data = [
    ('Plot Number:', '21'),
    ('Block:', 'G'),
    ('Society:', 'DHA Phase 5'),
    ('City:', 'Lahore'),
    ('Area:', '10 Marla'),
]

for i, (label, value) in enumerate(data):
    row = table.rows[i]
    row.cells[0].text = label
    row.cells[1].text = value

doc.add_paragraph('')

# Opinion Section
doc.add_heading('Legal Opinion', level=1)
doc.add_paragraph(
    'This document confirms that the property located at Plot No. 21, Block G, '
    'DHA Phase 5, Lahore is legally valid for transfer. All documentation has been '
    'verified and found to be in order.'
)

doc.add_paragraph(
    'The title is clear and free from any encumbrances. The property can be safely '
    'mortgaged or transferred.'
)

# Save
doc.save('/tmp/example.docx')
print('DOCX created successfully')
'@

# Run python script in container
$tempScriptPath = "/tmp/gen_docx.py"
$pythonScript | docker compose exec -T api sh -c "cat > $tempScriptPath"

$result = docker compose exec -T api python $tempScriptPath 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to generate DOCX: $result"
    exit 1
}

# Copy from container to host
$containerId = docker compose ps -q api 2>&1 | Out-String
$containerId = $containerId.Trim()

docker cp "${containerId}:/tmp/example.docx" $OutputPath 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to copy DOCX from container"
    exit 1
}

if (Test-Path $OutputPath) {
    Write-Host "DOCX created: $OutputPath" -ForegroundColor Green
    exit 0
} else {
    Write-Error "DOCX was not created at $OutputPath"
    exit 1
}
