# Father Demo Script - 15-20 Minute Walkthrough

This script provides a timed, step-by-step walkthrough for demonstrating the Bank Diligence Platform to stakeholders (e.g., your father).

## Pre-Demo Setup

1. **Run UAT:** `.\scripts\dev\pilot_uat.ps1` (ensures everything is ready)
2. **Open browser:** Navigate to `http://localhost:3000`
3. **Have ready:**
   - Demo case ID (from `uat_last_run.txt`)
   - Real-doc case ID (if real docs were tested)
   - Export URLs (from `uat_last_run.txt`)

## Demo Flow (15-20 minutes)

### 1. Login as OrgA Admin (1 min)

**Action:**
- Navigate to `http://localhost:3000`
- Click "Login"
- Enter: `admin@orga.com` / any password
- Select: OrgA / Admin

**Expected:**
- Dashboard loads with KPIs visible
- Active cases count > 0
- Risk summary visible

**Talk Track:**
> "This is the Bank Diligence Platform. I'm logged in as an admin for Organization A. The dashboard shows our active cases, risk summary, and pending verifications."

---

### 2. Dashboard Overview (2 min)

**Action:**
- Point to KPIs: Active Cases, Risk Summary, Pending Verifications
- Click on a case card or navigate to Cases page

**Expected:**
- KPIs show realistic numbers (from seed data)
- Cases list is populated
- Risk badges are visible (Green/Amber/Red)

**Talk Track:**
> "The dashboard gives us a high-level view of all cases. We can see active cases, risk levels, and what needs attention. Let me open a specific case to show you the detailed workflow."

---

### 3. Open "PILOT DEMO CASE" (1 min)

**Action:**
- Navigate to Cases page
- Find and click on "PILOT DEMO CASE" (or first case)
- Case detail page opens

**Expected:**
- Case detail page loads
- Tabs visible: Dossier, Documents, OCR Extractions, Controls, etc.
- Controls & Evidence Checklist card at top

**Talk Track:**
> "Here's a case we're working on. Notice the Controls & Evidence Checklist at the top - this shows us what evidence is required and what's missing."

---

### 4. Controls Checklist: Show Missing Evidence + Blockers (3 min)

**Action:**
- Point to Controls & Evidence Checklist card
- Show regime badge (e.g., "LDA", "DHA")
- Expand evidence checklist
- Point to "Missing" items (red badges)
- Point to "Provided" items (green badges)
- Show readiness status (Ready/Blocked)
- Click on readiness blockers if blocked

**Expected:**
- Regime is inferred (e.g., "LDA" with confidence %)
- Evidence checklist shows some "Missing" and some "Provided"
- Readiness shows "Blocked" with specific reasons (e.g., "1 hard-stop exception(s) open")
- Acceptable document types shown as badges for missing evidence

**Talk Track:**
> "The system automatically detects which regime applies - in this case, LDA. It shows us exactly what evidence is required. See these red badges? Those are missing documents. The green ones are already provided. The system won't let us mark this case as 'Ready for Approval' until all required evidence is attached. Here's why it's blocked: [read blockers]."

---

### 5. Documents: Open DocumentViewer, Show OCR Quality Banner, Show OCR Text (3 min)

**Action:**
- Click "Documents" tab
- Click on first document to open DocumentViewer
- Point to OCR status pill (Done/Processing/Failed)
- Point to OCR quality banner (if quality is Low/Critical)
- Expand OCR Text panel at bottom
- Scroll through OCR text
- Highlight some text to show selection

**Expected:**
- Document viewer loads with PDF preview
- OCR status shows "Done" with quality level
- If quality is Low/Critical, warning banner is visible
- OCR text panel shows extracted text
- Text is selectable

**Talk Track:**
> "Here's a document we uploaded. The system automatically runs OCR to extract text. Notice the OCR status - it's 'Done' and shows quality level. If quality is low, we get a warning. Let me show you the extracted text... [scroll through text]. This text is what the system uses to automatically fill in the dossier fields."

---

### 6. OCR Extractions: Edit Candidate, Demonstrate Force Confirm Modal on Low Quality (3 min)

**Action:**
- Navigate to "OCR Extractions" tab
- Show pending extractions list
- Point to extraction with `is_low_quality: true` (if any)
- Click "Edit" on an extraction
- Change the proposed value
- Try to "Confirm" a low-quality extraction
- Show force confirm modal (if quality is Low)
- Enter reason and confirm with force_confirm

**Expected:**
- Extractions list shows pending candidates
- Low-quality extractions are flagged (warning badge)
- Edit field is editable
- Confirming low-quality without force_confirm shows error/modal
- Force confirm modal requires reason
- After force confirm, extraction is confirmed

**Talk Track:**
> "When OCR quality is low, the system flags these extractions. We can still use them, but we need to explicitly confirm - this prevents accidental writes of bad data. Let me edit this value... [edit]. Now when I try to confirm, it requires force confirmation because the OCR quality was low. This is a safety gate."

---

### 7. OCR Text Correction: Correct OCR Text, Re-run Autofill (2 min)

**Action:**
- Go to Documents tab, open a document
- Scroll to OCR Text panel at bottom
- Point to "Edit OCR Text" button (Admin/Reviewer only)
- Click "Edit OCR Text"
- Show editable textarea: "I can fix OCR errors here"
- Change a value (e.g., if it says 'Plot No 12', change to 'Plot No 21')
- Enter note: "Correcting OCR error - verified against source"
- Click "Save Correction"
- Show "Corrected" badge appears
- Click "Re-run Autofill" button
- Navigate to OCR Extractions tab to show new candidates

**Expected:**
- Correction saved successfully
- "Corrected" badge visible
- Autofill button works
- New extractions reflect corrected text

**Talk Track:**
> "Sometimes OCR makes mistakes. We can correct the OCR text without losing the original. Notice the 'Corrected' badge - this means we're using corrected text. Now when I re-run autofill, it will use the corrected text, so extractions will be accurate."

---

### 8. Evidence: Attach OCR Snippet Evidence to an Exception/CP (2 min)

**Action:**
- Navigate to "Exceptions" or "CPs" tab
- Click on an exception or CP
- Click "Attach Evidence"
- Select "OCR Snippet" option
- Go back to Documents tab, select text in OCR panel
- Click "Attach Selected Text"
- Choose the exception/CP from dropdown
- Confirm attachment

**Expected:**
- Evidence attachment dialog opens
- OCR snippet option is available
- Text selection works in OCR panel
- Snippet is attached to exception/CP
- Evidence appears in exception/CP detail view

**Talk Track:**
> "We can attach evidence to exceptions or condition precedents. Here's a cool feature - we can select text directly from the OCR output and attach it as evidence. This links the evidence to the specific document and page. [attach snippet]. Now this exception has evidence attached."

---

### 9. Reports: Generate Bank Pack PDF + Discrepancy Letter DOCX (2 min)

**Action:**
- Navigate to "Reports" page (or case Reports tab)
- Select the case
- Click "Generate Bank Pack PDF"
- Wait for generation (5-10 seconds)
- Show presigned URL or download
- Click "Generate Discrepancy Letter DOCX"
- Wait for generation
- Show presigned URL or download

**Expected:**
- Bank Pack PDF generation starts
- Progress indicator or success message
- Presigned URL is provided
- PDF is downloadable
- Discrepancy Letter DOCX generation works similarly
- DOCX is downloadable

**Talk Track:**
> "The system can generate professional exports. The Bank Pack PDF includes the dossier summary, exceptions, CPs, and all evidence references. The Discrepancy Letter is a DOCX template that we can customize. Both are generated on-demand and include presigned URLs for download."

---

### 10. Approvals: Demonstrate Maker/Checker (Create Request, Approve with Different Role) (2 min)

**Action:**
- Navigate to "Approvals" page
- Show pending approval requests
- Create a new approval request (if possible)
- Logout
- Login as Reviewer: `reviewer@orga.com`
- Navigate to Approvals
- Show pending request
- Approve the request

**Expected:**
- Approval requests list is visible
- New request can be created
- Reviewer role can see pending requests
- Approval action is available
- Status changes after approval

**Talk Track:**
> "We have a maker/checker workflow. An admin creates an approval request, and a reviewer (different role) must approve it. This ensures proper oversight. [show workflow]."

---

### 11. Tenant Isolation: Logout, Login OrgB, Show Empty/No Access (1 min)

**Action:**
- Logout
- Login as OrgB Admin: `admin@orgb.com`
- Navigate to Dashboard
- Show OrgB's cases (different from OrgA)
- Try to access OrgA case URL (from earlier)
- Show 404/403 error

**Expected:**
- OrgB dashboard shows different cases
- OrgB cannot see OrgA cases
- Accessing OrgA case URL returns 404/403
- Tenant isolation is enforced

**Talk Track:**
> "Finally, tenant isolation. Each organization only sees its own data. I'm now logged in as Organization B. Notice the cases are completely different. If I try to access an Organization A case, I get an error. This ensures data security and compliance."

---

## Closing (1 min)

**Action:**
- Return to dashboard
- Summarize key features

**Talk Track:**
> "So to summarize: The platform automates document analysis, extracts structured data, identifies risks and requirements, tracks evidence, and generates professional exports - all with full audit logging and tenant isolation. It's ready for pilot testing with real bank documents."

---

## Demo Tips

1. **Pace yourself:** Don't rush. 15-20 minutes is plenty of time.
2. **Focus on value:** Emphasize automation, quality gates, and auditability.
3. **Handle errors gracefully:** If something doesn't work, explain it's a demo environment and move on.
4. **Use real examples:** Reference the actual case/document names from your UAT run.
5. **Show, don't tell:** Let the UI speak for itself when possible.

## Backup Plan

If something breaks during demo:
1. Have `uat_last_run.txt` open with case IDs
2. Have export URLs ready to show
3. Skip to Reports section to show exports
4. Emphasize the automation and quality gates

## Post-Demo

1. Answer questions
2. Show `uat_last_run.txt` for metrics
3. Offer to run a real-doc scenario if time permits
4. Provide access to documentation

