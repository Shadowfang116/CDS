# CDS Security Hardening Backlog

This backlog tracks the next production-hardening controls required before real confidential matters are processed at scale.

| Priority | Backlog Item | Risk | Owner Suggestion | Acceptance Criteria |
| --- | --- | --- | --- | --- |
| P0 | Make GitHub repo private before real documents or bank-specific material are added | Real client or bank material could be exposed through source control | Repo owner / engineering lead | Repository visibility is private, access is limited to approved collaborators, and onboarding guidance explicitly prohibits uploading real material before privacy is enforced |
| P0 | Add database-level audit log immutability | Audit events could be altered without a durable control | Backend engineer + DBA | Audit log tables enforce append-only behavior through DB constraints, trigger policy, or segregated write path; destructive updates are blocked and tested |
| P1 | Add MinIO object storage backup automation | Bank Pack, document, and evidence objects may be lost after storage failure | Infrastructure owner | Automated scheduled backup job exists, retention policy is documented, and restore target location is defined |
| P1 | Add restore drill documentation | Backups are not reliable if restore procedures are untested | Infrastructure owner + technical operator | Step-by-step restore drill exists, includes validation steps, and is run successfully at least once on a non-production environment |
| P1 | Add route-level RBAC and tenant-scope audit | Cross-tenant access or unauthorized actions could go undetected | Backend engineer | Sensitive routes have explicit role checks, tenant-scope enforcement is covered, and audit entries capture actor, tenant, route, and action |
| P1 | Add object-key org isolation test | Object storage keys may leak or overlap across organizations | Backend engineer / QA | Automated test verifies object-key construction and retrieval remain organization-scoped across upload, download, and export paths |
| P1 | Add secret scanning with gitleaks or equivalent | Secrets may be committed without detection | DevOps / security owner | Secret scanning is wired into CI or pre-merge checks, baseline is reviewed, and failing findings block merge until triaged |
| P1 | Add production TLS/cert renewal verification | Pilot deployment may fail or become insecure due to expired certificates | Infrastructure owner | TLS renewal method is documented, renewal is test-verified, and an operator can confirm certificate validity before expiry |
| P2 | Add admin user bootstrap command/runbook | Initial environment setup may rely on ad hoc database changes | Backend engineer | Supported bootstrap command or documented runbook exists for first admin creation, with required audit and recovery notes |
| P2 | Add retention policy enforcement test | Closed-case retention controls may drift from policy | Backend engineer / QA | Automated test covers retention logic, confirms eligible records are handled correctly, and proves audit trace remains intact |

## Expected Output / Verification

This backlog is acceptable when:

- all 10 hardening items are documented
- each item includes priority, risk, owner suggestion, and acceptance criteria
- the list can be used directly for pilot hardening planning

Suggested verification:

```powershell
Get-Content docs\SECURITY_HARDENING_BACKLOG.md
```

Expected outcome:

- the file exists
- all requested hardening items appear with actionable acceptance criteria
