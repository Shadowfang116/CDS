export const PRODUCT_WALKTHROUGH_STORAGE_KEY = 'bdp_tutorial_completed';
export const PRODUCT_WALKTHROUGH_OPEN_EVENT = 'bdp:start-product-walkthrough';

export type ProductWalkthroughStep = {
  title: string;
  description: string;
};

export const PRODUCT_WALKTHROUGH_STEPS: ReadonlyArray<ProductWalkthroughStep> = [
  {
    title: 'Dashboard — Command Centre',
    description:
      'This screen provides a real-time view of matters requiring legal review, pending approvals, and files where title defects or document gaps still need attention. Use it each morning to identify which matters are under review pressure, approaching deadlines, or awaiting escalation before a financing decision can proceed.',
  },
  {
    title: 'Matters Queue',
    description:
      'Each entry in the queue is a separate finance matter or collateral review file. The queue shows ownership status, outstanding exceptions, and days elapsed so the team can prioritise their review workload without opening every individual file.',
  },
  {
    title: 'Opening a Matter',
    description:
      'Click any matter to enter its working file. The PILOT DEMO CASE contains pre-loaded title documents, extracted OCR text, and sample exceptions — use it to follow the remainder of this walkthrough through a realistic property-backed finance review.',
  },
  {
    title: 'Matter Workspace',
    description:
      'The matter workspace is the central file room for the transaction. From here the team manages title documents, OCR review, Exceptions, Conditions Precedent, dossier preparation, and final output generation from a single controlled record.',
  },
  {
    title: 'Title Documents',
    description:
      'Upload the principal title chain here — sale deed, mutation entries (including fard and jamabandi), allotment or transfer papers, NOCs from relevant authorities, and any supporting annexures. Every document remains linked to the matter so the Bank and instructing solicitors can trace the full evidentiary basis of the file.',
  },
  {
    title: 'OCR — First-Pass Extraction',
    description:
      'The system extracts key text from title documents to assist review. This is a reading aid, not a legal conclusion. You must still compare extracted fields with the underlying deed, mutation, or transfer paper before confirming them, and should not treat extracted text as verified without independent cross-referencing.',
  },
  {
    title: 'OCR Field Review',
    description:
      'Extracted fields are displayed page by page with a confidence indicator. Fields marked with low confidence require manual verification — particularly for Urdu text, handwritten entries, registered deed numbers, and scanned mutation orders. Confirm only fields you have independently verified against the source document.',
  },
  {
    title: 'Exceptions — Title Defects and Gaps',
    description:
      'Raise an Exception whenever you identify a defect in title, a gap in the chain of ownership, a missing NOC, an unresolved encumbrance, or any factual inconsistency in the submitted documents. Each Exception must either be resolved with supporting evidence before the matter advances, or moved through a formally documented Waiver with appropriate rationale and governance sign-off.',
  },
  {
    title: 'Waivers and Resolution',
    description:
      'Where an Exception cannot be resolved prior to closing, it may be waived subject to appropriate rationale and authorisation. The platform records the Waiver basis, approving officer, and date so the matter audit trail remains complete. Waivers should not substitute for genuine title resolution where resolution is achievable.',
  },
  {
    title: 'Conditions Precedent',
    description:
      'Conditions Precedent capture the requirements that must be fulfilled before disbursement or final approval. Each CP is tracked with its evidence reference, current status, and any Waiver where a condition has been modified or deferred. No matter should advance to final approval with unresolved, non-waived CPs outstanding.',
  },
  {
    title: 'Dossier — Structured Matter Record',
    description:
      'The dossier consolidates the structured summary of the property, borrower, and transaction — property description, title position, encumbrances identified, and key transacting parties. It provides a reliable working record for legal review, credit decisioning, and downstream draft generation, and should be completed before the Bank Pack is produced.',
  },
  {
    title: 'Approval Flow — Maker / Checker',
    description:
      'The platform enforces reviewer and approver segregation consistent with standard maker-checker governance. Reviewers prepare the matter record and submit it for decision. Approvers independently assess outstanding Exceptions, CP completion, and Waiver rationale before recording the final approval, referral, or rejection.',
  },
  {
    title: 'Drafts and Bank Pack',
    description:
      'Once the matter record is sufficiently complete, the platform prepares formal outputs including the Bank Pack PDF, Discrepancy Letter, Undertaking draft, and Legal Opinion skeleton. These outputs are structured for legal review and clearly marked where further professional input is required before they may be relied upon.',
  },
  {
    title: 'Matter Completion',
    description:
      'A matter is ready for closure when all title Exceptions are resolved or formally waived, all Conditions Precedent are addressed or waived with documented rationale, the dossier is complete, and the Bank Pack or Legal Opinion has been reviewed and signed off by the responsible officer. Archive the matter record once final approval is recorded.',
  },
] as const;
