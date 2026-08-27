import { requiredDocTypes, requiredEvidenceLabel, type FindingRow } from "./workbench/findings";
import { displayCanonicalLabel, type FileRequirementRow, type LegalState } from "./workbench/required-evidence";

export type DashboardSectionId =
  | "dashboard"
  | "matters"
  | "documents"
  | "exceptions"
  | "cp"
  | "approvals"
  | "audit"
  | "settings";

type InboxSummary = {
  label: string;
  action: string;
  tone: "high" | "medium" | "neutral" | "good";
};

type InboxSummaryInput = {
  open_hard_stop?: number | null;
  open_high?: number | null;
  open_medium?: number | null;
  open_cps?: number | null;
  next_action?: string | null;
};

function normalizeStatus(value?: string | null): string {
  return (value ?? "").trim().toLowerCase().replace(/\s+/g, "_");
}

function normalizedRequirementList(item: FindingRow): string[] {
  const values = requiredDocTypes(item)
    .map((value) => displayCanonicalLabel(value))
    .filter(Boolean);

  return [...new Set(values)];
}

function missingInformationAction(nextAction: string): boolean {
  return /attach required evidence|missing|upload|required document|request evidence|request document/i.test(nextAction);
}

export function dashboardSectionFromPath(pathname: string): DashboardSectionId {
  if (pathname.startsWith("/dashboard/settings")) return "settings";
  if (pathname.startsWith("/dashboard/audit") || pathname.startsWith("/governance") || pathname.startsWith("/integrations")) {
    return "audit";
  }
  if (pathname.startsWith("/approvals")) return "approvals";
  if (pathname.startsWith("/dashboard/exceptions")) return "exceptions";
  if (pathname.startsWith("/dashboard/cp")) return "cp";
  if (pathname.startsWith("/dashboard/documents")) return "documents";
  if (pathname.startsWith("/dashboard/cases") || pathname.startsWith("/matters")) return "matters";
  return "dashboard";
}

export function isDashboardNavActive(pathname: string, href: string): boolean {
  if (href === "/dashboard") return pathname === href;
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function ocrStatusLabel(status?: string | null): string {
  const value = normalizeStatus(status);
  if (value === "complete" || value === "done" || value === "completed") return "Text extracted";
  if (value === "needs_review") return "Review required";
  if (value === "failed") return "Text extraction failed";
  if (value === "uploaded") return "Uploaded";
  return status || "OCR";
}

export function ocrReviewNotice(status?: string | null, confidence?: number | null): string | null {
  const value = normalizeStatus(status);

  if (value === "failed") {
    return "OCR failed. Review the source page and use manual review or a replacement upload before relying on this page.";
  }

  if (value === "processing" || value === "queued" || value === "uploaded" || value === "ocr_in_progress") {
    return "OCR is still running. Keep the source page in view and confirm the field after extraction finishes.";
  }

  if (value === "needs_review" || (confidence !== null && confidence !== undefined && confidence < 80)) {
    return "This text is provisional. Compare it with the source page, then confirm or correct the field in Work.";
  }

  if (value === "complete" || value === "done" || value === "completed") {
    return "OCR is complete, but the extracted text stays provisional until a reviewer confirms it against the source page.";
  }

  return null;
}

export function summarizeInboxItem(item: InboxSummaryInput): InboxSummary {
  const nextAction = (item.next_action ?? "").trim();

  if ((item.open_hard_stop ?? 0) > 0) {
    return {
      label: "Hard-stop open",
      action: nextAction || "Open the matter, compare the cited source page, and clear the hard-stop before submission.",
      tone: "high",
    };
  }

  if (missingInformationAction(nextAction)) {
    return {
      label: "Missing information",
      action: nextAction || "Open the matter, request or upload the missing evidence, then rerun review.",
      tone: "high",
    };
  }

  if ((item.open_high ?? 0) > 0) {
    return {
      label: "High-risk findings open",
      action: nextAction || "Open the matter, compare the source page, and resolve or waive the finding with evidence.",
      tone: "high",
    };
  }

  if ((item.open_medium ?? 0) > 0) {
    return {
      label: "Review needed",
      action: nextAction || "Open the matter, confirm the cited page, and record the result before deciding.",
      tone: "medium",
    };
  }

  if ((item.open_cps ?? 0) > 0) {
    return {
      label: "CP outstanding",
      action: nextAction || "Open the matter, attach the supporting page, and mark the condition met when complete.",
      tone: "neutral",
    };
  }

  return {
    label: "Ready",
    action: nextAction || "Open the matter and prepare the approval package.",
    tone: "good",
  };
}

function resolutionRequirement(item: FindingRow): string | null {
  const resolution = requiredEvidenceLabel(item);
  if (resolution && resolution !== item.resolution_conditions) {
    return resolution;
  }

  const labels = normalizedRequirementList(item);
  return labels.length > 0 ? labels.join(" or ") : null;
}

function requirementActionByState(state: LegalState, label: string, filename: string | null, requiredByFinding: boolean): string {
  if (state === "missing") {
    return `Upload ${label} or request it from counsel before rerunning review.`;
  }

  if (state === "weak") {
    return `Replace or confirm ${filename || label} so ${label} is current enough for submission.`;
  }

  if (state === "needs_review") {
    return `Review ${filename || label}, compare it to the source page, and confirm the usable value before submission.`;
  }

  if (state === "processing") {
    return `Wait for processing to finish, then compare ${label} against the source page.`;
  }

  if (state === "failed") {
    return `Re-upload ${label} or review the original page manually before using it.`;
  }

  if (requiredByFinding) {
    return `Open ${filename || label} and confirm it against the current finding.`;
  }

  return `Open ${filename || label} and keep it ready as source evidence.`;
}

export function requirementNextStep(row: FileRequirementRow): string {
  return requirementActionByState(
    row.legalState,
    row.label,
    row.preferred?.original_filename ?? null,
    row.requiredByFinding
  );
}

export function findingRequestLabel(item: FindingRow): string {
  const labels = normalizedRequirementList(item);
  if (labels.length > 0) {
    return `Request ${labels.join(" or ")}`;
  }

  return item.kind === "cp" ? "Request supporting evidence" : "Request document";
}

export function findingNextStep(item: FindingRow): string {
  const resolution = item.resolution_conditions?.trim();
  const required = resolutionRequirement(item);

  if (item.status !== "Open") {
    if (item.status === "Waived") {
      return "Keep the waiver reason and linked evidence together for checker review and audit.";
    }

    return "Keep the resolving evidence linked so the audit trail still shows how this item was cleared.";
  }

  if (resolution) {
    return `${resolution}. Keep the source page open while you verify it.`;
  }

  if (required) {
    return `Attach ${required} and compare it with the cited source page before resolving this ${item.kind === "cp" ? "condition" : "finding"}.`;
  }

  if (item.kind === "cp") {
    return "Attach the supporting page, then mark the condition met when the evidence is on file.";
  }

  if (item.is_hard_stop || item.severity === "High") {
    return "Open the cited page, compare the source text, and either resolve the finding or record a waiver request with evidence.";
  }

  return "Review the cited page, confirm the source text, and resolve the finding with a short recorded rationale.";
}
