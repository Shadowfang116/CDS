import { CaseDocumentItem } from "@/lib/api";
import { FindingRow, canonicalDocType, documentMatchesType, requiredDocTypes } from "@/lib/workbench/findings";

export type LegalState = "provided" | "missing" | "weak" | "needs_review" | "processing" | "failed";
export type EvidenceRequirementStatus = "provided" | "stale" | "missing";

export type FileDocument = Pick<
  CaseDocumentItem,
  | "id"
  | "original_filename"
  | "page_count"
  | "status"
  | "doc_type"
  | "predicted_doc_type"
  | "corrected_doc_type"
  | "needs_review"
  | "created_at"
>;

export type RequirementSpec = {
  id: string;
  label: string;
  types: string[];
};

export type FileRequirementRow = {
  id: string;
  label: string;
  legalState: LegalState;
  preferred: FileDocument | null;
  prior: FileDocument[];
  requiredByFinding: boolean;
  section: "required" | "supporting";
};

export type FileCompletenessView = {
  required: FileRequirementRow[];
  supporting: FileRequirementRow[];
  leftover: FileDocument[];
};

const LABEL_BY_KEY: Record<string, string> = {
  sale_deed: "Registered Sale Deed",
  mutation: "Mutation / Intiqal",
  fard: "Fard / Revenue Record",
  cnic: "Identity / CNIC",
  noc: "Authority / Society NOC",
  search_report: "Title / Encumbrance Search",
  valuation: "Valuation Report",
  facility_approval: "Facility Approval",
  possession: "Possession Evidence",
  property_tax: "Property Tax / PT-10",
  board_resolution: "Board Resolution",
  building_plan: "Approved Building Plan",
  dues_clearance: "Development Dues Clearance",
  charge_release: "Charge Release / Satisfaction",
  identity_confirmation: "Identity Confirmation",
};

const ALIAS_TO_KEY: Array<[RegExp, string]> = [
  [/identity confirmation|name confirmation/, "identity_confirmation"],
  [/charge release|satisfaction/, "charge_release"],
  [/dues clearance|development dues/, "dues_clearance"],
  [/building plan|approved plan/, "building_plan"],
  [/board resolution/, "board_resolution"],
  [/facility approval/, "facility_approval"],
  [/search report|title search|encumbrance search/, "search_report"],
  [/possession/, "possession"],
  [/property tax|pt-?10/, "property_tax"],
  [/society\/authority noc|authority noc|society noc|\bnoc\b/, "noc"],
  [/registered sale|sale deed|registry/, "sale_deed"],
  [/mutation|intiqal/, "mutation"],
  [/\bfard\b|jamabandi|revenue record/, "fard"],
  [/\bcnic\b|national id/, "cnic"],
  [/valuation/, "valuation"],
];

export const CORE_REQUIREMENTS: RequirementSpec[] = [
  { id: "sale_deed", label: "Registered Sale Deed", types: ["Sale Deed", "Registered Sale Deed"] },
  { id: "mutation", label: "Mutation / Intiqal", types: ["Mutation", "Intiqal"] },
  { id: "current_fard", label: "Current Fard", types: ["Fard", "Current Fard"] },
  { id: "noc", label: "Authority / Society NOC", types: ["Society/Authority NOC", "NOC", "Authority NOC"] },
  { id: "building_plan", label: "Approved Building Plan", types: ["Building Plan", "Approved Plan", "Approved Building Plan"] },
  { id: "search_report", label: "Title / Encumbrance Search", types: ["Search Report"] },
  { id: "possession", label: "Possession Evidence", types: ["Possession Letter", "Possession"] },
];

export const SUPPORTING_REQUIREMENTS: RequirementSpec[] = [
  { id: "valuation", label: "Valuation Report", types: ["Valuation", "Valuation Report"] },
  { id: "facility_approval", label: "Facility Approval", types: ["Facility Approval"] },
  { id: "board_resolution", label: "Board Resolution", types: ["Board Resolution"] },
  { id: "property_tax", label: "Property Tax / PT-10", types: ["Property Tax/PT-10", "Property Tax", "PT-10"] },
  { id: "dues_clearance", label: "Development Dues Clearance", types: ["Dues Clearance"] },
  { id: "charge_release", label: "Charge Release / Satisfaction", types: ["Charge Release"] },
  { id: "identity_confirmation", label: "Identity Confirmation", types: ["Identity Confirmation"] },
];

export const GOLD_EVIDENCE_PACK: Array<{ label: string; types: string[] }> = CORE_REQUIREMENTS.map((item) => ({
  label: item.label,
  types: item.types,
}));

const KYC_NOISE_TYPE = /salary|photograph|\bphoto\b|utility|co-applicant|payslip/i;
const COMPANY_MARKER = /company|corporate|limited|pvt|private|لمیٹڈ/i;

function normalize(value: string): string {
  return value.toLowerCase().replace(/[_/]+/g, " ").replace(/\s+/g, " ").trim();
}

export function canonicalTypeKey(value?: string | null): string | null {
  if (!value) return null;
  const text = normalize(value);
  for (const [pattern, key] of ALIAS_TO_KEY) {
    if (pattern.test(text)) return key;
  }
  return null;
}

export function displayCanonicalLabel(value?: string | null): string {
  const key = canonicalTypeKey(value);
  if (key && LABEL_BY_KEY[key]) return LABEL_BY_KEY[key];
  if (!value) return "Unclassified";
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function isKycNoiseDocument(doc: FileDocument): boolean {
  const type = canonicalDocType(doc) ?? "";
  const name = doc.original_filename ?? "";
  return KYC_NOISE_TYPE.test(type) || KYC_NOISE_TYPE.test(name);
}

export function isCompanyMortgage(
  fields: Array<{ field_key?: string | null; field_value?: string | null }> = []
): boolean {
  const borrowerType = fields.find((item) => item.field_key === "case.borrower_type")?.field_value ?? "";
  if (/individual|person|retail/i.test(borrowerType)) return false;
  if (COMPANY_MARKER.test(borrowerType)) return true;
  const buyer =
    fields.find((item) => item.field_key === "party.name.borrower")?.field_value ??
    fields.find((item) => item.field_key === "party.buyer.names")?.field_value ??
    "";
  return COMPANY_MARKER.test(buyer);
}

export function processState(doc?: FileDocument | null): "uploaded" | "processing" | "ocr_complete" | "failed" | "ready" {
  const status = (doc?.status ?? "").replace(/\s+/g, "_").toLowerCase();
  if (status === "failed") return "failed";
  if (["uploaded", "queued", "split"].includes(status)) return "uploaded";
  if (["processing", "ocr_in_progress", "running"].includes(status)) return "processing";
  if (["complete", "done", "processed"].includes(status)) return "ocr_complete";
  if (status === "needs_review") return "ready";
  return doc ? "ready" : "uploaded";
}

export function processStateLabel(doc?: FileDocument | null): string | null {
  if (!doc) return null;
  const state = processState(doc);
  if (state === "failed") return "Failed";
  if (state === "processing") return "Processing";
  if (state === "uploaded") return "Uploaded";
  if (state === "ocr_complete") return "OCR complete";
  return "Ready";
}

function matchesSpec(doc: FileDocument, spec: RequirementSpec): boolean {
  return spec.types.some((type) => documentMatchesType(doc, type));
}

function sortNewest(docs: FileDocument[]): FileDocument[] {
  return [...docs].sort((left, right) => {
    const leftTime = Date.parse(left.created_at ?? "") || 0;
    const rightTime = Date.parse(right.created_at ?? "") || 0;
    return rightTime - leftTime;
  });
}

function findingTargetsSpec(item: FindingRow, spec: RequirementSpec): boolean {
  if (item.rule_id === "GOLD-FARD-01" && spec.id === "current_fard") return true;
  if (item.rule_id === "GOLD-AREA-01" && spec.id === "current_fard") return true;
  if (item.rule_id === "GOLD-PLAN-01" && spec.id === "building_plan") return true;
  if (item.rule_id === "GOLD-DUES-01" && spec.id === "dues_clearance") return true;
  if (item.rule_id === "GOLD-ENCUMB-01" && spec.id === "charge_release") return true;
  if (item.rule_id === "GOLD-NAME-01" && spec.id === "identity_confirmation") return true;
  if (item.rule_id === "GOLD-TAX-01" && spec.id === "property_tax") return true;
  return requiredDocTypes(item).some((type) => spec.types.some((candidate) => normalize(candidate) === normalize(type) || documentMatchesType({ doc_type: type }, candidate)));
}

function legalStateFor(
  spec: RequirementSpec,
  preferred: FileDocument | null,
  prior: FileDocument[],
  findings: FindingRow[]
): LegalState {
  if (!preferred) return "missing";
  const state = processState(preferred);
  if (state === "failed") return "failed";
  if (state === "processing" || state === "uploaded") return "processing";
  const staleFard = findings.some(
    (item) => item.status === "Open" && (item.rule_id === "GOLD-FARD-01" || /stale fard/i.test(item.title ?? ""))
  );
  // A newer Fard supersedes the stale instrument even if evaluate has not yet cleared GOLD-FARD-01.
  // Classification needs_review is a technical flag, not legal insufficiency.
  if (staleFard && spec.id === "current_fard" && prior.length === 0) return "weak";
  return "provided";
}

export function legalStateLabel(state: LegalState): string {
  if (state === "provided") return "PROVIDED";
  if (state === "weak") return "WEAK / STALE";
  if (state === "needs_review") return "NEEDS REVIEW";
  if (state === "processing") return "PROCESSING";
  if (state === "failed") return "FAILED";
  return "MISSING";
}

export function requirementMark(status: LegalState | EvidenceRequirementStatus): string {
  if (status === "provided") return "✓";
  if (status === "weak" || status === "stale" || status === "needs_review") return "!";
  if (status === "processing" || status === "failed") return "…";
  return "○";
}

export function requirementTone(
  status: LegalState | EvidenceRequirementStatus
): "good" | "stale" | "missing" | "proposed" {
  if (status === "provided") return "good";
  if (status === "weak" || status === "stale" || status === "needs_review") return "stale";
  if (status === "processing") return "proposed";
  return "missing";
}

export function requirementLabel(status: LegalState | EvidenceRequirementStatus): string {
  if (status === "stale") return "Weak / Stale";
  return legalStateLabel(status as LegalState);
}

function buildRow(
  spec: RequirementSpec,
  documents: FileDocument[],
  findings: FindingRow[],
  selectedFinding: FindingRow | null,
  section: "required" | "supporting"
): FileRequirementRow {
  const matches = sortNewest(documents.filter((doc) => matchesSpec(doc, spec) && !isKycNoiseDocument(doc)));
  const preferred = matches[0] ?? null;
  const prior = matches.slice(1);
  return {
    id: spec.id,
    label: spec.label,
    legalState: legalStateFor(spec, preferred, prior, findings),
    preferred,
    prior,
    requiredByFinding: Boolean(selectedFinding && findingTargetsSpec(selectedFinding, spec)),
    section,
  };
}

export function buildFileCompleteness(
  documents: FileDocument[],
  findings: FindingRow[] = [],
  _fields: Array<{ field_key?: string | null; field_value?: string | null }> = [],
  selectedFindingId: string | null = null
): FileCompletenessView {
  const selectedFinding = findings.find((item) => item.id === selectedFindingId) ?? null;
  const usable = documents.filter((doc) => !isKycNoiseDocument(doc));

  const required = CORE_REQUIREMENTS.map((spec) => buildRow(spec, usable, findings, selectedFinding, "required"));
  const claimed = new Set(
    required.flatMap((row) => [row.preferred?.id, ...row.prior.map((doc) => doc.id)].filter(Boolean) as string[])
  );

  const supporting = SUPPORTING_REQUIREMENTS.map((spec) => buildRow(spec, usable, findings, selectedFinding, "supporting")).filter(
    (row) => row.preferred || row.requiredByFinding || findings.some((item) => findingTargetsSpec(item, specById(row.id)))
  );

  supporting.forEach((row) => {
    if (row.preferred) claimed.add(row.preferred.id);
    row.prior.forEach((doc) => claimed.add(doc.id));
  });

  const leftover = sortNewest(usable.filter((doc) => !claimed.has(doc.id)));

  return { required, supporting, leftover };
}

function specById(id: string): RequirementSpec {
  return (
    CORE_REQUIREMENTS.find((item) => item.id === id) ??
    SUPPORTING_REQUIREMENTS.find((item) => item.id === id) ?? { id, label: id, types: [] }
  );
}

export function requiredEvidencePack(
  documents: CaseDocumentItem[],
  findings: FindingRow[] = [],
  fields: Array<{ field_key?: string | null; field_value?: string | null }> = []
): Array<{ label: string; types: string[]; status: EvidenceRequirementStatus }> {
  return buildFileCompleteness(documents, findings, fields).required.map((row) => ({
    label: row.label,
    types: specById(row.id).types,
    status: row.legalState === "weak" ? "stale" : row.legalState === "provided" ? "provided" : "missing",
  }));
}

export function formatDocType(value?: string | null): string {
  return displayCanonicalLabel(value);
}

export function secondaryMeta(doc: FileDocument | null): string | null {
  if (!doc) return null;
  const parts: string[] = [];
  if (doc.page_count) parts.push(`${doc.page_count} page${doc.page_count === 1 ? "" : "s"}`);
  const process = processStateLabel(doc);
  if (process) parts.push(process);
  return parts.length ? parts.join(" · ") : null;
}

export function preferredFilename(row: FileRequirementRow): string | null {
  return row.preferred?.original_filename ?? null;
}

export function missingRequirementLabel(
  view: FileCompletenessView,
  selectedFinding: FindingRow | null
): string | null {
  const marked = [...view.required, ...view.supporting].find((row) => row.requiredByFinding && row.legalState === "missing");
  if (marked) return marked.label;
  const missing = view.required.find((row) => row.legalState === "missing");
  if (missing) return missing.label;
  if (selectedFinding) {
    const types = requiredDocTypes(selectedFinding);
    if (types[0]) return displayCanonicalLabel(types[0]);
  }
  return null;
}
