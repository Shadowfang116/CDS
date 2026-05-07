export type OnboardingStep = {
  id: string;
  target: string;
  title: string;
  description: string;
  actionHint: string;
};

export const ONBOARDING_STORAGE_KEY = 'bdp_onboarding_done';
export const ONBOARDING_OPEN_EVENT = 'bdp:start-onboarding-tour';

export const ONBOARDING_STEPS: OnboardingStep[] = [
  {
    id: 'dashboard',
    target: '[data-tour="dashboard"]',
    title: 'Dashboard — Command Centre',
    description: 'This screen shows matters requiring legal review, pending approvals, and files where title defects or document gaps still need attention. Use it as your daily starting point before opening individual case files.',
    actionHint: 'Check the queue each morning to identify matters under review pressure or awaiting escalation.',
  },
  {
    id: 'cases',
    target: '[data-tour="case-list"]',
    title: 'Matters Queue',
    description: 'Each entry in this list is a separate finance matter or collateral review file. The queue shows ownership status, pending exceptions, and days outstanding so the team can prioritise without opening every file.',
    actionHint: 'Assign ownership to stale matters before they exceed the review deadline.',
  },
  {
    id: 'demo-matter',
    target: '[data-tour="case-list"]',
    title: 'Opening a Matter',
    description: 'Click any matter to enter its file room. For this walkthrough, use the PILOT DEMO CASE — it contains pre-loaded title documents, extracted OCR text, and sample exceptions to review.',
    actionHint: 'Click the demo matter to continue the walkthrough inside the file.',
  },
  {
    id: 'matter-workspace',
    target: '[data-tour="dashboard"]',
    title: 'Matter Workspace',
    description: 'The matter workspace is the central file room for the transaction. From here, access the title documents, run OCR, raise Exceptions, check Conditions Precedent, prepare the dossier, and generate the Bank Pack.',
    actionHint: 'Use the tabs across the top to navigate between documents, exceptions, CPs, and output drafts.',
  },
  {
    id: 'documents',
    target: '[data-tour="ocr-review"]',
    title: 'Title Documents',
    description: 'Upload the principal title chain here — sale deed, mutation entries (fard, jamabandi), allotment or transfer papers, NOCs, and supporting annexures. Every document is linked to the matter record and available for evidence citation.',
    actionHint: 'Upload all title documents before commencing OCR or raising exceptions.',
  },
  {
    id: 'begin-ocr',
    target: '[data-tour="ocr-review"]',
    title: 'OCR — First-Pass Extraction',
    description: 'The system extracts key text from title documents to assist review. This is a reading aid, not a legal opinion. You must still compare extracted fields with the underlying deed, mutation, or transfer paper before confirming them.',
    actionHint: 'Click Begin OCR to queue documents for text extraction. Extraction runs in the background.',
  },
  {
    id: 'ocr-fields',
    target: '[data-tour="ocr-review"]',
    title: 'OCR Field Review',
    description: 'Extracted fields are listed page by page. Fields marked with low confidence require manual verification, particularly for Urdu text, handwritten entries, or scanned mutations. Confirm only what you have checked against the source document.',
    actionHint: 'Review low-confidence fields first. Do not confirm without cross-referencing the original paper.',
  },
  {
    id: 'exceptions',
    target: '[data-tour="exceptions"]',
    title: 'Exceptions — Title Defects and Gaps',
    description: 'Raise an Exception whenever you identify a defect in title, a gap in the chain of ownership, a missing NOC, an unresolved encumbrance, or any factual inconsistency in the documents. Every Exception must either be resolved with evidence or advanced through a documented Waiver.',
    actionHint: 'Clear all high-severity Exceptions before the matter moves to approval.',
  },
  {
    id: 'exception-waiver',
    target: '[data-tour="exceptions"]',
    title: 'Waivers and Resolution',
    description: 'Where an Exception cannot be resolved before closing, it may be waived with appropriate rationale and governance sign-off. The platform records the waiver basis, approving officer, and date so the audit trail is complete.',
    actionHint: 'Only an Approver or authorised officer should record a Waiver on a title exception.',
  },
  {
    id: 'cps',
    target: '[data-tour="exceptions"]',
    title: 'Conditions Precedent',
    description: 'Conditions Precedent are the requirements that must be fulfilled before disbursement or final approval. Track each CP here with its evidence reference, status, and any Waiver where a condition has been modified or deferred.',
    actionHint: 'No matter should move to final approval with unresolved, non-waived CPs outstanding.',
  },
  {
    id: 'dossier',
    target: '[data-tour="dashboard"]',
    title: 'Dossier — Structured Matter Record',
    description: 'The dossier consolidates the structured summary of the property, borrower, and transaction — property description, title position, encumbrances, and key parties. It feeds the Bank Pack and provides the legal team with a reliable working record.',
    actionHint: 'Complete the dossier fields before generating draft outputs.',
  },
  {
    id: 'approval',
    target: '[data-tour="dashboard"]',
    title: 'Approval Flow — Maker / Checker',
    description: 'The platform enforces reviewer/approver segregation. Reviewers prepare the matter and submit for decision. Approvers assess outstanding Exceptions, CP status, and Waiver rationale before recording the final approval or referral back.',
    actionHint: 'Confirm all Exceptions and CPs are addressed before submitting the matter for Approver review.',
  },
  {
    id: 'bank-pack',
    target: '[data-tour="export"]',
    title: 'Drafts and Bank Pack',
    description: 'Once the matter record is sufficiently developed, generate the Bank Pack PDF, Discrepancy Letter, Undertaking draft, or Legal Opinion skeleton. These outputs are structured for legal review and are clearly marked where further professional input is required.',
    actionHint: 'Run the Bank Pack export after Exceptions are cleared or waived and CPs are addressed.',
  },
  {
    id: 'completion',
    target: '[data-tour="dashboard"]',
    title: 'Matter Completion',
    description: 'A matter is ready for closure when all title Exceptions are resolved or waived with documented rationale, all Conditions Precedent are addressed, the dossier is complete, and the Bank Pack or Legal Opinion has been reviewed and signed off by the responsible officer.',
    actionHint: 'Mark the matter complete and archive the file once the final approval is recorded.',
  },
];
