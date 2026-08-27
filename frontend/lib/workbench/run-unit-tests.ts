import assert from "node:assert/strict";
import {
  canProposeWaiver,
  canWaiveFinding,
  firstEvidenceRef,
  groupFindings,
  isKycNoiseLabel,
  missingRequiredTypes,
  pendingWaiverExceptionIds,
  toExceptionFinding,
} from "./findings";
import { clientNextAction } from "./next-action";
import {
  matterBorrower,
  matterFacility,
  matterRegime,
  openHardStopCount,
  primaryBlocker,
  readinessLabel,
} from "./matter-header";
import { acknowledgementsComplete, canSelfApprove, submitEnabled } from "./submit-gate";
import {
  FileDocument,
  buildFileCompleteness,
  displayCanonicalLabel,
  isCompanyMortgage,
  isKycNoiseDocument,
  legalStateLabel,
  processState,
  processStateLabel,
} from "./required-evidence";
import {
  dashboardSectionFromPath,
  findingNextStep,
  findingRequestLabel,
  isDashboardNavActive,
  ocrReviewNotice,
  ocrStatusLabel,
  requirementNextStep,
  summarizeInboxItem,
} from "../cds-review-ui";
import { resolveApiBaseUrl } from "../runtime-config";
import { formatDocumentType, getQualityToneClass } from "../../components/documents/document-viewer-format";

assert.equal(
  resolveApiBaseUrl({ API_INTERNAL_BASE_URL: undefined, API_BASE_URL: undefined, NODE_ENV: "development" }),
  "http://localhost:8000"
);
assert.equal(dashboardSectionFromPath("/dashboard"), "dashboard");
assert.equal(dashboardSectionFromPath("/dashboard/documents"), "documents");
assert.equal(dashboardSectionFromPath("/dashboard/cp"), "cp");
assert.equal(isDashboardNavActive("/dashboard/cases/case-1", "/dashboard/cases"), true);
assert.equal(isDashboardNavActive("/dashboard", "/dashboard"), true);
assert.equal(ocrStatusLabel("complete"), "Text extracted");
assert.match(ocrReviewNotice("complete", 96) ?? "", /provisional/i);
assert.match(ocrReviewNotice("failed", null) ?? "", /manual review/i);
assert.equal(
  resolveApiBaseUrl({ API_INTERNAL_BASE_URL: "http://api:8000", API_BASE_URL: "http://localhost:8000", NODE_ENV: "production" }),
  "http://api:8000"
);
assert.equal(formatDocumentType("REGISTERED_SALE_DEED"), "REGISTERED SALE DEED".replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase()));
assert.equal(getQualityToneClass("good"), "cds-quality-good");

const grouped = groupFindings(
  [
    { id: "e1", kind: "exception", severity: "Low", status: "Open", title: "Low" },
    { id: "e2", kind: "exception", severity: "High", status: "Open", title: "High", is_hard_stop: true },
  ],
  [{ id: "c1", kind: "cp", severity: "High", status: "Open", title: "CP" }]
);

assert.equal(grouped[0].id, "e2");
assert.equal(canWaiveFinding(grouped[0]), false);
assert.equal(submitEnabled({ ready: true, blockedReasons: [], decision: "FAIL" }), false);
assert.equal(acknowledgementsComplete(["a", "b"], ["a", "b"]), true);
assert.equal(canSelfApprove("u1", "u1"), true);
assert.equal(canSelfApprove("u1", "u2"), false);
assert.equal(canWaiveFinding({ id: "e3", kind: "exception", severity: "High", status: "Open", title: "X", waivable: false }), false);
assert.equal(
  clientNextAction({ hardStopTitle: "Title chain", unconfirmedKeyField: "party.name.borrower" }).startsWith("Resolve blocking issue"),
  true
);

const goldTax = toExceptionFinding({
  id: "tax-1",
  severity: "Low",
  status: "Open",
  title: "Historical property tax",
  rule_id: "GOLD-TAX-01",
  waivable: true,
  is_hard_stop: false,
});
assert.equal(canWaiveFinding(goldTax), true);
assert.equal(canProposeWaiver(goldTax), true);
assert.equal(canProposeWaiver(goldTax, ["tax-1"]), false);
assert.deepEqual(pendingWaiverExceptionIds([{ request_type: "exception_waive", payload_json: { exception_id: "tax-1" } }]), ["tax-1"]);
assert.equal(
  clientNextAction({ openLowTitle: "Historical property tax" }),
  "Review issue: Historical property tax"
);
assert.equal(
  clientNextAction({
    openLowTitle: "Historical property tax",
    missingRequiredCausingHigh: isKycNoiseLabel("Salary slip") ? null : "Salary slip",
  }),
  "Review issue: Historical property tax"
);
assert.equal(clientNextAction({ status: "NEW" }), "Review matter readiness");
assert.equal(findingRequestLabel(goldTax), "Request Property Tax / PT-10");
assert.equal(isKycNoiseLabel("Salary slip"), true);
assert.equal(isKycNoiseLabel("Approved building plan"), false);
assert.equal(submitEnabled({ ready: true, blockedReasons: [], decision: "FAIL" }), false);
assert.equal(submitEnabled({ ready: false, blockedReasons: ["hard-stop"], decision: "PASS" }), false);

const dues = toExceptionFinding({
  id: "dues-1",
  severity: "High",
  status: "Open",
  title: "Outstanding development charges",
  rule_id: "GOLD-DUES-01",
  source_document_id: "doc-noc",
  source_page: 2,
});
assert.deepEqual(firstEvidenceRef(dues), { documentId: "doc-noc", page: 2 });
assert.deepEqual(missingRequiredTypes(dues, [{ doc_type: "Sale Deed" }]), ["Dues Clearance"]);
assert.deepEqual(missingRequiredTypes(dues, [{ doc_type: "Dues Clearance" }]), []);

assert.equal(
  matterBorrower([
    { field_key: "party.buyer.names", field_value: "اے بی سی ٹیکسٹائلز (پرائیویٹ) لمیٹڈ" },
  ]),
  "اے بی سی ٹیکسٹائلز (پرائیویٹ) لمیٹڈ"
);
assert.equal(matterFacility([{ field_key: "facility.finance_type", field_value: "Term finance" }]), "Term finance");
assert.equal(
  matterRegime([
    { field_key: "property.scheme_name", field_value: "Punjab Urban" },
    { field_key: "property.regime", field_value: "LDA" },
  ]),
  "Punjab Urban · LDA"
);
assert.equal(openHardStopCount(grouped), 1);
assert.equal(
  primaryBlocker([
    { status: "Open", kind: "exception", severity: "High", title: "Property area mismatch" },
    { status: "Open", kind: "cp", title: "Obtain current Fard" },
  ]),
  "Property area mismatch"
);
assert.equal(readinessLabel(false, "Review"), "Not ready");
assert.equal(readinessLabel(true, "Review"), "Ready");
assert.equal(readinessLabel(false, "Approved"), "Approved");
assert.notEqual(readinessLabel(true, "Review"), "PASS");

const companyFields = [
  { field_key: "case.borrower_type", field_value: "company" },
  { field_key: "party.buyer.names", field_value: "ABC Textiles Limited" },
];

function fileDoc(overrides: Partial<FileDocument> & Pick<FileDocument, "id" | "original_filename">): FileDocument {
  return {
    page_count: 2,
    status: "complete",
    needs_review: false,
    created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

assert.equal(displayCanonicalLabel("REGISTERED_SALE_DEED"), "Registered Sale Deed");
assert.equal(displayCanonicalLabel("MUTATION"), "Mutation / Intiqal");
assert.equal(displayCanonicalLabel("FARD"), "Fard / Revenue Record");
assert.equal(displayCanonicalLabel("AUTHORITY_NOC"), "Authority / Society NOC");
assert.equal(displayCanonicalLabel("SEARCH_REPORT"), "Title / Encumbrance Search");
assert.equal(displayCanonicalLabel("BUILDING_PLAN"), "Approved Building Plan");
assert.equal(displayCanonicalLabel("POSSESSION_LETTER"), "Possession Evidence");
assert.equal(displayCanonicalLabel("PROPERTY_TAX"), "Property Tax / PT-10");
assert.equal(displayCanonicalLabel("DUES_CLEARANCE"), "Development Dues Clearance");
assert.equal(displayCanonicalLabel("CHARGE_RELEASE"), "Charge Release / Satisfaction");
assert.equal(displayCanonicalLabel("IDENTITY_CONFIRMATION"), "Identity Confirmation");
assert.equal(displayCanonicalLabel("CNIC"), "Identity / CNIC");

const staleFardFinding = toExceptionFinding({
  id: "fard-1",
  rule_id: "GOLD-FARD-01",
  status: "Open",
  title: "Stale Fard",
});
const planFinding = toExceptionFinding({
  id: "plan-1",
  rule_id: "GOLD-PLAN-01",
  status: "Open",
  title: "Approved building plan missing",
});

const oldFard = fileDoc({
  id: "doc-fard-old",
  original_filename: "03_Fard_Old.pdf",
  doc_type: "Fard",
  created_at: "2026-01-15T00:00:00Z",
});
assert.match(
  requirementNextStep({
    id: "sale_deed",
    label: "Registered Sale Deed",
    legalState: "missing",
    preferred: null,
    prior: [],
    requiredByFinding: false,
    section: "required",
  }),
  /Upload Registered Sale Deed/i
);
assert.match(
  requirementNextStep({
    id: "current_fard",
    label: "Current Fard",
    legalState: "weak",
    preferred: oldFard,
    prior: [],
    requiredByFinding: true,
    section: "required",
  }),
  /Replace or confirm/i
);
assert.match(
  findingNextStep(
    toExceptionFinding({
      id: "plan-1",
      rule_id: "GOLD-PLAN-01",
      status: "Open",
      title: "Approved building plan missing",
      resolution_conditions: "Approved building plan is required before submission",
    })
  ),
  /approved building plan/i
);
const staleView = buildFileCompleteness([oldFard], [staleFardFinding], companyFields);
const staleFardRow = staleView.required.find((row) => row.id === "current_fard");
assert.equal(staleFardRow?.legalState, "weak");
assert.equal(legalStateLabel(staleFardRow!.legalState), "WEAK / STALE");
assert.equal(processState(oldFard), "ocr_complete");
assert.notEqual(staleFardRow?.legalState, "provided");

const missingPlanView = buildFileCompleteness([], [planFinding], companyFields);
assert.equal(missingPlanView.required.find((row) => row.id === "building_plan")?.legalState, "missing");
assert.equal(legalStateLabel("missing"), "MISSING");

const buildingPlan = fileDoc({
  id: "doc-plan",
  original_filename: "12_Approved_Building_Plan.pdf",
  doc_type: "Building Plan",
  created_at: "2026-03-01T00:00:00Z",
});
const providedPlanView = buildFileCompleteness([buildingPlan], [planFinding], companyFields);
assert.equal(providedPlanView.required.find((row) => row.id === "building_plan")?.legalState, "provided");
assert.equal(providedPlanView.required.find((row) => row.id === "building_plan")?.preferred?.original_filename, "12_Approved_Building_Plan.pdf");

const correctedFard = fileDoc({
  id: "doc-fard-new",
  original_filename: "13_Corrected_Fard.pdf",
  doc_type: "Fard",
  created_at: "2026-03-02T00:00:00Z",
});
const correctedView = buildFileCompleteness([oldFard, correctedFard], [staleFardFinding], companyFields);
const currentFard = correctedView.required.find((row) => row.id === "current_fard");
assert.equal(currentFard?.preferred?.original_filename, "13_Corrected_Fard.pdf");
assert.equal(currentFard?.legalState, "provided");
assert.equal(currentFard?.prior.some((doc) => doc.original_filename === "03_Fard_Old.pdf"), true);
assert.equal(
  correctedView.leftover.some((doc) => doc.original_filename === "03_Fard_Old.pdf"),
  false
);

const kycNoise = [
  fileDoc({ id: "doc-salary", original_filename: "salary_slip.pdf", doc_type: "Salary Slip" }),
  fileDoc({ id: "doc-photo", original_filename: "photograph.jpg", doc_type: "Photograph" }),
  fileDoc({ id: "doc-coapp", original_filename: "co-applicant-cnic.pdf", doc_type: "Co-applicant CNIC" }),
];
assert.equal(kycNoise.every(isKycNoiseDocument), true);
assert.equal(isCompanyMortgage(companyFields), true);
const companyView = buildFileCompleteness(kycNoise, [], companyFields);
assert.equal(companyView.required.some((row) => /salary|photograph|co-applicant/i.test(row.label)), false);
assert.equal(companyView.supporting.some((row) => /salary|photograph|co-applicant/i.test(row.label)), false);
assert.equal(companyView.leftover.length, 0);

const processingDoc = fileDoc({
  id: "doc-processing",
  original_filename: "17_New_NOC.pdf",
  predicted_doc_type: "Society/Authority NOC",
  status: "processing",
});
const processingView = buildFileCompleteness([processingDoc], [], companyFields);
assert.equal(processState(processingDoc), "processing");
assert.equal(processStateLabel(processingDoc), "Processing");
assert.equal(processingView.required.find((row) => row.id === "noc")?.legalState, "processing");
assert.notEqual(processingView.required.find((row) => row.id === "noc")?.legalState, "provided");

const classifiedPlan = fileDoc({
  id: "doc-plan-review",
  original_filename: "12_Approved_Building_Plan.pdf",
  doc_type: "Building Plan",
  needs_review: true,
  status: "complete",
});
const classifiedPlanView = buildFileCompleteness([classifiedPlan], [], companyFields);
assert.equal(processState(classifiedPlan), "ocr_complete");
assert.equal(classifiedPlanView.required.find((row) => row.id === "building_plan")?.legalState, "provided");

const selectedPlanView = buildFileCompleteness([], [planFinding], companyFields, "plan-1");
assert.equal(selectedPlanView.required.find((row) => row.id === "building_plan")?.requiredByFinding, true);
assert.equal(selectedPlanView.required.find((row) => row.id === "current_fard")?.requiredByFinding, false);

const hardStopSummary = summarizeInboxItem({
  open_hard_stop: 1,
  open_high: 1,
  open_medium: 0,
  open_cps: 0,
  next_action: "Clear hard-stop: Title chain",
});
assert.equal(hardStopSummary.label, "Hard-stop open");
assert.match(hardStopSummary.action, /Clear hard-stop/i);

const missingInfoSummary = summarizeInboxItem({
  open_hard_stop: 0,
  open_high: 1,
  open_medium: 0,
  open_cps: 0,
  next_action: "Attach required evidence: Dues Clearance",
});
assert.equal(missingInfoSummary.label, "Missing information");
assert.match(missingInfoSummary.action, /Dues Clearance/i);

console.log("workbench unit tests passed");
