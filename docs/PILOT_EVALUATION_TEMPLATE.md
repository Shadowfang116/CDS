# CDS Pilot Evaluation Template

Use this template to score the first 10 internal pilot matters processed through Covenant Diligence Systems.

## Evaluation Table

| Case No. | Property Type | Regime | Document Set | Expected High-Risk Flags | Actual High-Risk Flags | Missed Flags | False Positives | OCR Confidence | Dossier Accuracy | Bank Pack Exported? | Processing Time | Reviewer Notes | Approver Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 3 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 4 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 5 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 6 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 7 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 8 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 9 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 10 |  |  |  |  |  |  |  |  |  |  |  |  |  |

## Scoring Targets

- High-risk recall target: `>= 80%`
- False positives: tracked and explainable
- Bank Pack export: must succeed for every pilot case
- Processing time: target under 5 minutes after processing

## Reviewer Guidance

- `Expected High-Risk Flags` should be defined before scoring the output.
- `Actual High-Risk Flags` should reflect what CDS surfaced in Exceptions and Conditions Precedent.
- `Missed Flags` should list material issues CDS failed to surface.
- `False Positives` should list issues CDS surfaced but the reviewer considers non-material or unsupported.
- `Dossier Accuracy` should reflect whether the reviewed dossier is decision-ready.

## Expected Output / Verification

The evaluation pass is usable when:

- all 10 rows can be completed without missing workflow data
- each case records whether the Bank Pack exported successfully
- reviewer and approver notes are captured for every case

Suggested verification:

```powershell
Get-ChildItem docs\PILOT_*.md
```

Expected outcome:

- `PILOT_EVALUATION_TEMPLATE.md` is present
- the template contains a 10-case scoring table and scoring targets
