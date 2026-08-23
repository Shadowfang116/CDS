# CDS-GOLD-001 — RUN 2 Explanation, Remaining Gaps, and Next Steps

## Executive Summary

RUN 2 is a **major improvement** over RUN 1, but it does **not yet mean CDS-GOLD-001 is fully passed**.

It means the architecture is now behaving correctly enough that the remaining failures are specific extraction gaps rather than broad system defects.

The simplest way to understand the change is:

```text
RUN 1
Documents were there
        ↓
CDS misunderstood some of them
        ↓
Wrong names
Wrong missing-document findings
25 noisy exceptions
        ↓
FAIL for the wrong reasons


RUN 2
Documents were there
        ↓
CDS correctly identifies them
        ↓
Correct names preserved
Correct document types
Relevant rules only
5 meaningful findings
        ↓
Additional evidence clears those findings
        ↓
PASS
```

That is a very substantial step forward.

---

# 1. What Happened to the Seller / Buyer Problem

RUN 1 initially found:

```text
Seller
محمد اکرم

Buyer
اے بی سی ٹیکسٹائلز (پرائیویٹ) لمیٹڈ
```

Those were correct.

But when the Mutation was processed later, CDS replaced them with meaningless form labels:

```text
رجسٹریشن حوالہ
/ منتقل الیہ
```

That was a serious problem because a weaker later extraction was allowed to overwrite a better earlier one.

RUN 2 fixes that.

Now CDS effectively does:

```text
SALE DEED

محمد اکرم
Source: Sale Deed
Method: clause_urdu
Strong candidate
        ↓
KEEP


MUTATION

/ منتقل الیہ
Looks like a form label
        ↓
REJECT
```

More importantly, if two **genuine plausible names** disagree, CDS now preserves both rather than destroying one.

For example:

```text
Sale Deed
ABC Textiles (Pvt.) Limited

Mutation
ABC Textile Pvt Ltd
```

should become:

```text
CONFLICT / REVIEW REQUIRED
```

rather than:

```text
latest value wins
```

That is exactly what a bank-grade system should do.

---

# 2. The Document-Classification Problem Is Basically Fixed

This was another major RUN 1 defect.

RUN 1 physically contained:

```text
Registered Sale Deed
Possession Letter
Building Plan
etc.
```

but the rules sometimes behaved as though those documents did not exist.

RUN 2 now has a canonical understanding of all 16 documents.

So CDS can distinguish:

```text
Registered Sale Deed
Mutation
Fard
CNIC
NOC
Search Report
Valuation Report
Facility Approval
Possession Letter
Property Tax
Board Resolution
Building Plan
Dues Clearance
Charge Release
Identity Confirmation
```

That matters enormously.

Before:

```text
PDF exists
but CDS does not understand what it is
        ↓
"Missing Registered Title"
```

Now:

```text
PDF exists
        ↓
classified as Registered Sale Deed
        ↓
rule sees title instrument present
        ↓
no false exception
```

This is why many of the 25 garbage findings disappeared.

---

# 3. Why RUN 2 Had Only Five Findings

Because the rules are now being applied in a more sensible context.

RUN 1 was effectively asking generic questions such as:

```text
Where is the salary slip?
Where is the photograph?
Where is the utility bill?
Where is the co-applicant CNIC?
```

Those make little sense for:

> ABC Textiles (Pvt.) Limited → corporate borrower → property mortgage.

RUN 2 now understands applicability better.

So instead of 25 generic findings, the initial batch produced five relevant ones:

```text
1. Approved Building Plan missing

2. Development dues outstanding

3. Prior encumbrance exists

4. Name variation exists

5. Fard is stale
```

That is exactly the type of output we want CDS to produce.

A lawyer looking at those five findings can understand why each matters.

---

# 4. The Additional-Evidence Loop Also Worked

This is probably the most important product success in RUN 2.

Initial file:

```text
BUILDING PLAN
Missing

DEVELOPMENT DUES
Outstanding

PRIOR CHARGE
Unresolved

NAME VARIATION
Unresolved

FARD
Stale
```

Then you upload:

```text
12 Approved Building Plan

13 New / Corrected Fard

14 Development Charges Clearance

15 Charge Release

16 Identity Confirmation
```

and CDS reacts to the new evidence.

Conceptually:

```text
Finding
OPEN
   ↓
additional evidence
   ↓
classify
   ↓
extract facts
   ↓
re-run affected rule
   ↓
RESOLVED
```

So:

```text
Missing Building Plan
        ↓
Approved Plan uploaded
        ↓
CLEARED
```

```text
Outstanding Development Charges
        ↓
Clearance uploaded
        ↓
CLEARED
```

```text
Prior Encumbrance
        ↓
Release Letter uploaded
        ↓
CLEARED
```

```text
Name Variation
        ↓
Identity Confirmation uploaded
        ↓
CLEARED
```

and the newer Fard caused the stale-Fard condition to clear.

That is the CDS workflow we wanted from the beginning.

---

# 5. Why the Final Result Is PASS

After the additional evidence, none of the findings that the current engine could reliably establish remained open.

Therefore the evaluator produced:

```text
PASS
```

That is technically correct **according to the facts CDS currently knows how to extract**.

But this distinction is critical:

> **RUN 2 passed the rules it was capable of evaluating. It has not yet proven every gold-standard defect.**

There are still two important blind spots.

---

# 6. Gap 1 — Property Area Mismatch

The intended gold defect was:

```text
SALE DEED
4 Kanal

vs

OLD FARD
3 Kanal 18 Marla
```

CDS should have produced:

```text
AREA MISMATCH
```

But it did not.

## Why

The problem happened earlier than the rule engine.

Tesseract failed to give CDS a sufficiently reliable Sale Deed area fact.

So the rule engine essentially had:

```text
Sale Deed area
UNKNOWN

Fard area
3 Kanal 18 Marla
```

You cannot honestly calculate:

```text
UNKNOWN != 3 Kanal 18 Marla
```

and call it a legal discrepancy.

Therefore **not firing the exception was actually safer behavior**.

It avoided inventing a finding.

However, the upstream extraction still needs to be fixed.

## Target Behaviour

```text
Sale Deed
        ↓
property area extracted
4 Kanal
Evidence: p.X

Fard
        ↓
property area extracted
3 Kanal 18 Marla
Evidence: p.X

        ↓

NORMALIZE

4 Kanal = 80 Marla

3 Kanal 18 Marla = 78 Marla

        ↓

DIFFERENCE = 2 Marla

        ↓

EXCEPTION
Area mismatch
```

This is the next important extraction improvement.

---

# 7. Gap 2 — Historical Property-Tax Waiver

The gold scenario deliberately included a tax issue that should remain open for a waiver.

The intended workflow was:

```text
Historical tax evidence unavailable

BUT

Current clearance shows
nothing outstanding
```

Then:

```text
EXCEPTION
Historical tax evidence missing
        ↓
Reviewer proposes waiver
        ↓
Approver approves waiver
        ↓
WAIVED
```

RUN 2 never created this issue because CDS did not extract anything useful into:

```text
fact.tax_history
```

and did not identify appropriate historic-tax wording.

So CDS had no factual basis for opening the finding.

Again, this is safer than manufacturing an exception.

But it means the waiver workflow still has not been properly tested by CDS-GOLD-001.

---

# 8. The Fard-Date Fallback Also Needs Tightening

There is a third, smaller issue.

The corrected Fard did not produce a parseable:

```text
issue_date
```

So CDS used:

```text
document upload time
```

as a freshness fallback.

That is acceptable as a temporary engineering fallback for this synthetic test.

It is **not sufficient for production legal diligence**.

A Fard uploaded today could actually have been issued:

```text
8 months ago
```

Therefore:

```text
uploaded today
```

must not eventually equal:

```text
current Fard
```

Production logic should ideally be:

```text
1. Extract explicit Fard issue date
        ↓
2. validate date
        ↓
3. calculate age
```

If no date can be established:

```text
FARD DATE UNCONFIRMED
```

should probably be shown rather than assuming today's upload makes it current.

---

# 9. Where CDS Is Now

CDS has moved from:

```text
PIPELINE WORKS
but semantics are unreliable
```

to:

```text
PIPELINE WORKS

DOCUMENT UNDERSTANDING WORKS

CANDIDATE ARBITRATION WORKS

RULE APPLICABILITY WORKS

EVIDENCE REMEDIATION WORKS

but

SOME KEY LEGAL FACT EXTRACTION
still needs improvement
```

That is a much healthier stage.

---

# 10. What the 194 Backend Tests Mean

The test results matter.

Current reported results:

```text
Targeted
171 passed

Full backend
194 passed
```

This means the fixes were not made by manually hacking the live Matter until it looked good.

There are automated checks protecting them.

The tests now cover behaviour such as:

```text
mutation label cannot replace a real seller name

company case does not receive irrelevant individual-borrower rules

canonical document classification works

area/stale evaluators behave correctly
```

That is exactly what should happen before further product expansion.

The one skipped `test_exception_waivable.py` because host Python lacks PyJWT should be fixed eventually, but it does not invalidate RUN 2.

---

# 11. Recommended Next Sequence

The next sequence should be:

```text
RUN 2 semantics
        ✓

        ↓

Fix remaining GOLD fact extraction
        │
        ├── Sale Deed area
        ├── Fard issue date
        └── Historical tax evidence
        │
        ↓

RUN 3
        ↓

Gold scenario fully exercised
        │
        ├── mismatch generated
        ├── mismatch resolved
        ├── tax issue generated
        └── waiver completed
        ↓

THEN

Frontend Workbench
```

Do **not** make Surya the next priority.

The current Tesseract pipeline already extracted enough to successfully prove:

```text
names
plot
block
document classification
dues
encumbrance
identity
building-plan presence
```

The biggest immediate product value comes from improving the remaining structured legal facts.

Surya remains later, once a benchmark shows whether it materially improves the failure pages.

---

# 12. What RUN 3 Should Prove

RUN 3 should be almost identical to RUN 2 except the remaining gaps must be exercised.

## Initial Batch

Initial batch should ideally produce:

```text
DECISION
FAIL

FINDINGS

HIGH
Property area mismatch
Sale Deed: 4 Kanal
Fard: 3 Kanal 18 Marla

HIGH/MEDIUM
Approved Building Plan missing

MEDIUM
Outstanding Development Charges

MEDIUM/HIGH
Prior Encumbrance

MEDIUM
Stale Fard

MEDIUM
Name Variation

LOW/MEDIUM
Historical tax evidence unavailable
```

## Additional Evidence Batch

Then the additional evidence should cause:

```text
Area mismatch
→ RESOLVED

Building Plan
→ RESOLVED

Development Dues
→ RESOLVED

Prior Encumbrance
→ RESOLVED

Stale Fard
→ RESOLVED

Name Variation
→ RESOLVED

Historical Tax
→ REMAINS OPEN
```

Then:

```text
Reviewer
PROPOSE WAIVER

Approver
APPROVE WAIVER

        ↓

WAIVED
```

Only then has CDS-GOLD-001 exercised virtually the complete product lifecycle.

---

# 13. Why the Frontend Should Use RUN 2 Now

The workbench Findings UX should be designed against RUN 2's five legal findings, not RUN 1's 25 generic cards.

RUN 1 was useful as a failure record.

But it is not representative product data.

Use RUN 2 for visual development because its findings are meaningful:

```text
Missing Building Plan

Development Dues

Prior Encumbrance

Name Variation

Stale Fard
```

Imagine the new three-pane workbench:

```text
┌───────────────────┬──────────────────────────┬────────────────────────┐
│ FILE              │ EVIDENCE                 │ WORK                   │
│                   │                          │                        │
│ ✓ Sale Deed       │ Society NOC              │ EX-003                 │
│ ✓ Mutation        │ Page 2                   │                        │
│ ✓ Fard            │                          │ DEVELOPMENT DUES       │
│ ✓ NOC             │ "...بقایا واجبات..."     │                        │
│ ○ Building Plan   │                          │ Medium                 │
│                   │                          │                        │
│ FINDINGS          │                          │ PKR 1,850,000 due      │
│                   │                          │                        │
│ ● Building Plan   │                          │ Required evidence:     │
│ ● Dues            │                          │ Clearance certificate  │
│ ● Encumbrance     │                          │                        │
│ ● Name variation  │                          │ [REQUEST DOCUMENT]     │
│ ● Stale Fard      │                          │                        │
└───────────────────┴──────────────────────────┴────────────────────────┘
```

Now the frontend is being designed against **actual legal work**, not false-positive noise.

---

# 14. Overall CDS Status After RUN 2

Current practical status:

```text
Document upload             ✓

OCR pipeline                ✓ functional
                            △ accuracy still unbenchmarked

Document classification     ✓ major milestone

Party extraction            ✓ substantially improved

Candidate arbitration       ✓ fixed

Dossier candidate model     ✓

Rule regime/applicability   ✓ substantially improved

Generic rule execution      ✓

Gold legal findings         △ 5/7 currently demonstrable

Additional evidence loop    ✓

Automatic re-evaluation     ✓

Exception resolution        ✓ demonstrated

Waiver workflow             ○ not yet gold-tested

Approval                    available / needs flagship workflow test

Bank Pack                   available / needs final workflow test

Frontend workbench          NEXT major UX phase

Surya                       intentionally deferred
```

So **RUN 2 is a successful engineering milestone**, not the end of CDS-GOLD-001.

The two things that should be finished before declaring this gold case complete are:

1. reliable **cross-document property-area extraction/comparison**;
2. reliable **historical-tax evidence detection**, so the waiver path can genuinely be exercised.

Then run a clean **RUN 3**.

After that, the majority of product attention should move to the new:

```text
Inbox
+
Three-Pane Matter Workbench
+
Approver Flow
+
Bank Pack
```

---

# 15. RUN 3 Acceptance Criteria

The immediate target is:

```text
RUN 3

✓ Correct seller/buyer retained
✓ All 16 document types correct
✓ Area mismatch actually fires
✓ Stale Fard actually fires from document date
✓ Historic tax issue actually fires
✓ Additional Fard resolves area + freshness
✓ Plan resolves missing-plan finding
✓ Dues clearance resolves dues
✓ Release resolves prior charge
✓ Identity confirmation resolves name variation
✓ Historic tax remains open
✓ Reviewer proposes waiver
✓ Approver grants waiver
✓ Final decision becomes PASS / CONDITIONAL PASS according to the final decision policy
✓ Bank Pack reflects exactly those findings, evidence, resolutions and waiver
```

Once that happens, **CDS-GOLD-001 becomes the first genuinely complete regression case**.

---

# 16. Final Product Interpretation

RUN 2 proves that CDS is no longer merely demonstrating that documents can be uploaded and OCR'd.

It is beginning to demonstrate the more important proposition:

```text
DOCUMENT
    ↓
UNDERSTAND WHAT IT IS
    ↓
EXTRACT LEGAL FACTS
    ↓
COMPARE EVIDENCE
    ↓
IDENTIFY MATERIAL FINDINGS
    ↓
RECEIVE ADDITIONAL EVIDENCE
    ↓
RE-EVALUATE
    ↓
RESOLVE / WAIVE
    ↓
DECIDE
    ↓
ISSUE BANK PACK
```

That is the path from a document-processing system to a bank-ready diligence platform.
