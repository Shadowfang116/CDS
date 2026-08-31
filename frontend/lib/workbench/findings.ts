export type FindingKind = "exception" | "cp";

export type FindingEvidenceRef = {
  id?: string;
  document_id?: string | null;
  page_number?: number | null;
  note?: string | null;
  is_closing?: boolean;
  isClosing?: boolean;
};

export type FindingRow = {
  id: string;
  kind: FindingKind;
  severity: string;
  status: string;
  title: string;
  is_hard_stop?: boolean;
  waivable?: boolean;
  rule_id?: string | null;
  module?: string | null;
  description?: string | null;
  cp_text?: string | null;
  resolution_conditions?: string | null;
  evidence_refs?: FindingEvidenceRef[];
  waiver_reason?: string | null;
  source_document_id?: string | null;
  source_page?: number | null;
};

export const GOLD_REQUIRED_DOC_TYPES: Record<string, string[]> = {
  "GOLD-AREA-01": ["Fard"],
  "GOLD-PLAN-01": ["Building Plan", "Approved Plan"],
  "GOLD-DUES-01": ["Dues Clearance"],
  "GOLD-ENCUMB-01": ["Charge Release"],
  "GOLD-FARD-01": ["Fard"],
  "GOLD-NAME-01": ["Identity Confirmation"],
  "GOLD-TAX-01": ["Property Tax/PT-10", "Property Tax"],
};

const KYC_NOISE = /salary|photograph|\bphoto\b|utility|co-applicant/i;

export function groupFindings(exceptions: FindingRow[], cps: FindingRow[]): FindingRow[] {
  const rows = [
    ...exceptions.map((item) => ({ ...item, kind: "exception" as const })),
    ...cps.map((item) => ({ ...item, kind: "cp" as const })),
  ];
  const rank = (item: FindingRow) => {
    if (item.status !== "Open") return 50;
    if (item.is_hard_stop) return 0;
    if (item.severity === "High") return 1;
    if (item.kind === "cp") return 2;
    if (item.severity === "Medium") return 3;
    if (item.severity === "Low") return 4;
    return 10;
  };
  return rows.sort((left, right) => rank(left) - rank(right));
}

export function canWaiveFinding(item: FindingRow): boolean {
  return item.kind === "exception" && item.waivable !== false && !item.is_hard_stop && item.status === "Open";
}

export function pendingWaiverExceptionIds(
  approvals: Array<{ request_type?: string; payload_json?: Record<string, unknown> | null }>
): string[] {
  return approvals
    .filter((item) => item.request_type === "exception_waive")
    .map((item) => String(item.payload_json?.exception_id ?? ""))
    .filter(Boolean);
}

export function hasPendingWaiver(item: FindingRow, pendingIds: Iterable<string> = []): boolean {
  const set = pendingIds instanceof Set ? pendingIds : new Set(pendingIds);
  return set.has(item.id);
}

export function canProposeWaiver(item: FindingRow, pendingIds: Iterable<string> = []): boolean {
  return canWaiveFinding(item) && !hasPendingWaiver(item, pendingIds);
}

export function firstEvidenceRef(item: FindingRow): { documentId: string; page?: number } | null {
  const fromSource = item.source_document_id;
  if (fromSource) {
    return { documentId: fromSource, page: item.source_page ?? undefined };
  }
  const ref = item.evidence_refs?.find((entry) => entry.document_id);
  if (!ref?.document_id) return null;
  return { documentId: ref.document_id, page: ref.page_number ?? undefined };
}

export function requiredDocTypes(item: FindingRow): string[] {
  if (item.rule_id && GOLD_REQUIRED_DOC_TYPES[item.rule_id]) {
    return GOLD_REQUIRED_DOC_TYPES[item.rule_id];
  }
  return [];
}

export function requiredEvidenceLabel(item: FindingRow): string | null {
  if (item.resolution_conditions) return item.resolution_conditions;
  const types = requiredDocTypes(item);
  return types.length ? types.join(" or ") : null;
}

export function canonicalDocType(doc: {
  doc_type?: string | null;
  predicted_doc_type?: string | null;
  corrected_doc_type?: string | null;
}): string | null {
  return doc.corrected_doc_type || doc.doc_type || doc.predicted_doc_type || null;
}

function normalizeType(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

export function documentMatchesType(
  doc: { doc_type?: string | null; predicted_doc_type?: string | null; corrected_doc_type?: string | null },
  requiredType: string
): boolean {
  const actual = canonicalDocType(doc);
  if (!actual) return false;
  const left = normalizeType(actual);
  const right = normalizeType(requiredType);
  return left === right || left.includes(right) || right.includes(left);
}

export function missingRequiredTypes(
  item: FindingRow,
  documents: Array<{ doc_type?: string | null; predicted_doc_type?: string | null; corrected_doc_type?: string | null }>
): string[] {
  return requiredDocTypes(item).filter((type) => !documents.some((doc) => documentMatchesType(doc, type)));
}

export function isKycNoiseLabel(label: string): boolean {
  return KYC_NOISE.test(label);
}

export function toExceptionFinding(item: {
  id: string;
  severity?: string;
  status?: string;
  title?: string;
  is_hard_stop?: boolean;
  waivable?: boolean;
  rule_id?: string | null;
  module?: string | null;
  description?: string | null;
  cp_text?: string | null;
  resolution_conditions?: string | null;
  evidence_refs?: FindingEvidenceRef[];
  waiver_reason?: string | null;
  source_document_id?: string | null;
  source_page?: number | null;
}): FindingRow {
  return {
    id: item.id,
    kind: "exception",
    severity: item.severity ?? "Medium",
    status: item.status ?? "Open",
    title: item.title ?? "Exception",
    is_hard_stop: item.is_hard_stop,
    waivable: item.waivable,
    rule_id: item.rule_id,
    module: item.module,
    description: item.description,
    cp_text: item.cp_text,
    resolution_conditions: item.resolution_conditions,
    evidence_refs: item.evidence_refs,
    waiver_reason: item.waiver_reason,
    source_document_id: item.source_document_id,
    source_page: item.source_page,
  };
}

export function toCpFinding(item: {
  id: string;
  severity?: string;
  status?: string;
  text?: string;
  title?: string;
  evidence_required?: string | null;
  resolution_conditions?: string | null;
  evidence_refs?: FindingEvidenceRef[];
  rule_id?: string | null;
  description?: string | null;
  cp_text?: string | null;
  waiver_reason?: string | null;
}): FindingRow {
  return {
    id: item.id,
    kind: "cp",
    severity: item.severity ?? "High",
    status: item.status ?? "Open",
    title: item.text ?? item.title ?? "Condition precedent",
    rule_id: item.rule_id,
    description: item.description,
    cp_text: item.cp_text ?? item.text,
    resolution_conditions: item.resolution_conditions ?? item.evidence_required,
    evidence_refs: item.evidence_refs,
    waiver_reason: item.waiver_reason,
  };
}
