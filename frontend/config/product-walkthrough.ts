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
      'This screen provides a real-time view of cases requiring legal review, pending approvals, and files where title defects or document gaps still need attention. Use it each morning to identify which cases are under review pressure, approaching deadlines, or awaiting escalation before a financing decision can proceed.',
  },
  {
    title: 'Case queue',
    description:
      'Each entry in the queue is a separate finance case or collateral review file. The queue shows ownership status, outstanding issues, and days elapsed so the team can prioritise their review workload without opening every individual file.',
  },
  {
    title: 'Opening a case',
    description:
      'Click any case to enter its working file. The PILOT DEMO CASE contains pre-loaded title documents, scanned text, and sample issues — use it to follow the remainder of this walkthrough through a realistic property-backed finance review.',
  },
  {
    title: 'Case workspace',
    description:
      'The case workspace is the central file room for the transaction. From here the team manages title documents, scan review, issues, approval needs, case details, and final output generation from a single controlled record.',
  },
  {
    title: 'Title Documents',
    description:
      'Upload the principal title chain here — sale deed, mutation entries (including fard and jamabandi), allotment or transfer papers, NOCs from relevant authorities, and any supporting annexures. Every document remains linked to the case so the Bank and instructing solicitors can trace the full evidentiary basis of the file.',
  },
  {
    title: 'Scan documents — first pass',
    description:
      'The system extracts key text from title documents to assist review. This is a reading aid, not a legal conclusion. You must still compare extracted fields with the underlying deed, mutation, or transfer paper before confirming them, and should not treat extracted text as verified without independent cross-referencing.',
  },
  {
    title: 'Review scanned text',
    description:
      'Extracted fields are displayed page by page with a confidence indicator. Fields marked with low confidence require manual verification — particularly for Urdu text, handwritten entries, registered deed numbers, and scanned mutation orders. Confirm only fields you have independently verified against the source document.',
  },
  {
    title: 'Issues — title defects and gaps',
    description:
      'Raise an Issue whenever you identify a defect in title, a gap in the chain of ownership, a missing NOC, an unresolved encumbrance, or any factual inconsistency in the submitted documents. Each Issue must either be resolved with supporting evidence before the case advances, or moved through a formally documented Waiver with appropriate rationale and governance sign-off.',
  },
  {
    title: 'Waivers and Resolution',
    description:
      'Where an Issue cannot be resolved prior to closing, it may be waived subject to appropriate rationale and authorisation. The platform records the Waiver basis, approving officer, and date so the case activity history remains complete. Waivers should not substitute for genuine title resolution where resolution is achievable.',
  },
  {
    title: 'Approval needed',
    description:
      'Approval needed items capture the requirements that must be fulfilled before disbursement or final approval. Each item is tracked with its evidence reference, current status, and any Waiver where a requirement has been modified or deferred. No case should advance to final approval with unresolved, non-waived approval needs outstanding.',
  },
  {
    title: 'Case details',
    description:
      'Case details consolidate the structured summary of the property, borrower, and transaction — property description, title position, encumbrances identified, and key transacting parties. They provide a reliable working record for legal review, credit decisioning, and downstream draft generation, and should be completed before the Bank Pack is produced.',
  },
  {
    title: 'Approval Flow — Maker / Checker',
    description:
      'The platform enforces reviewer and approver separation consistent with standard maker-checker governance. Reviewers prepare the case record and submit it for decision. Approvers independently assess outstanding Issues, approval-needed items, and Waiver rationale before recording the final approval, referral, or rejection.',
  },
  {
    title: 'Drafts and Bank Pack',
    description:
      'Once the case record is sufficiently complete, the platform prepares formal outputs including the Bank Pack PDF, Discrepancy Letter, Undertaking draft, and Legal Opinion skeleton. These outputs are structured for legal review and clearly marked where further professional input is required before they may be relied upon.',
  },
  {
    title: 'Case completion',
    description:
      'A case is ready for closure when all title Issues are resolved or formally waived, all approval-needed items are addressed or waived with documented rationale, the case details are complete, and the Bank Pack or Legal Opinion has been reviewed and signed off by the responsible officer. Archive the case record once final approval is recorded.',
  },
] as const;
