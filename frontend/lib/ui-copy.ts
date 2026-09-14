/** Shared plain-language labels for rendered CDS UI. Internal API/domain names stay unchanged. */
export const UI_COPY = {
  case: "Case",
  cases: "Cases",
  issue: "Issue",
  issues: "Issues",
  approvalNeeded: "Approval needed",
  caseDetails: "Case details",
  scanDocuments: "Scan documents",
  startScan: "Start scan",
  blockingIssue: "Blocking issue",
  needsReview: "Needs your review",
  propertyAuthority: "Property authority",
} as const;

export function displayDecision(value?: string | null): string {
  switch ((value ?? "").toUpperCase()) {
    case "PASS":
      return "Passed";
    case "FAIL":
      return "Needs work";
    case "CONDITIONAL_PASS":
      return "Conditional";
    default:
      return value || "No decision yet";
  }
}

export function displayStatus(value?: string | null): string {
  switch ((value ?? "").toLowerCase()) {
    case "new":
      return "New";
    case "processing":
      return "Processing";
    case "review":
      return "In review";
    case "ready for approval":
      return "Ready for approval";
    case "approved":
      return "Approved";
    default:
      return value || "Unknown";
  }
}
