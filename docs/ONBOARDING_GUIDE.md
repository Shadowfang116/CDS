# CDS First-Day Onboarding Guide

Covenant Diligence Systems helps a bank or legal team move from title documents to a documented review decision. It is a review aid and workflow system; it does not replace professional legal judgment.

## The simplest way to start

1. Sign in and open **Dashboard**.
2. Start with **Needs me**. Each matter explains what is blocking progress and what to do next.
3. Create a matter with a borrower or file name and property type. Attach the documents you already have; more can be added later.
4. Open the matter workspace. Keep the source document visible while reviewing extracted fields and findings.
5. Resolve missing evidence and risks, or record a properly approved waiver where the bank permits one.
6. Submit the prepared matter for checker approval. Generate the Bank Pack only after the reviewer and checker gates are satisfied.

## What each role does

| Role | Main responsibility |
| --- | --- |
| Admin | Set up the organization, users, roles, and operational configuration. |
| Reviewer | Upload and review evidence, verify provisional OCR values, resolve findings, complete the dossier, and submit the matter. |
| Approver / checker | Review the prepared matter, decide eligible waivers or approvals, and preserve maker-checker separation. |
| Viewer | Inspect matters, documents, findings, and audit history without changing review state. |

## How to read a matter

- **File** shows whether required documents are present.
- **Evidence** shows the source page that supports a fact or finding.
- **Work** shows risks, missing information, conditions precedent, and the next action.
- **Provisional** means the system extracted a value that still needs human confirmation.
- **Incomplete** means the matter cannot safely proceed until the stated document, field, or review action is addressed.
- **High risk** or **hard stop** means the issue needs resolution or an authorized governance decision before approval.

## Review rules to remember

- Always compare important OCR values with the source document and page.
- A finding is not resolved merely because a note was added; it needs supporting evidence or an approved waiver.
- Exceptions and Conditions Precedent are separate controls and should be handled separately.
- The person who prepares or requests a decision must not approve their own request.
- Every material change is recorded in the audit trail.

## If you get stuck

- Follow the **Next action** shown on the Dashboard or Matter header.
- Use **Required evidence** to see exactly what is missing.
- Use **Help** for the evidence, waiver, and keyboard walkthroughs.
- Select **Restart tour** in Help to replay the first-run tour.
- Ask the responsible legal reviewer or bank officer when the source documents do not support a conclusion.

## Pilot setup checklist

- [ ] Choose the bank-controlled private host and release owner.
- [ ] Create Admin, Reviewer, Approver/checker, and Viewer accounts as needed.
- [ ] Configure the organization's email login or approved SSO details.
- [ ] Seed a non-production pilot matter and confirm the review path.
- [ ] Run the authenticated browser smoke checklist in `docs/ops/RELEASE_CHECKLIST.md`.
- [ ] Test backups, restore, audit visibility, and export downloads before using real files.
