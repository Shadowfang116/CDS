export type NextActionInput = {
  hardStopTitle?: string | null;
  missingRequiredCausingHigh?: string | null;
  unconfirmedKeyField?: string | null;
  openHighTitle?: string | null;
  blockingCpText?: string | null;
  pendingVerification?: string | null;
  openMediumTitle?: string | null;
  openLowTitle?: string | null;
  status?: string | null;
};

export function clientNextAction(input: NextActionInput): string {
  const status = (input.status ?? "").trim().toLowerCase();
  if (input.hardStopTitle) return `Resolve blocking issue: ${input.hardStopTitle}`;
  if (input.missingRequiredCausingHigh) return `Add required proof: ${input.missingRequiredCausingHigh}`;
  if (input.unconfirmedKeyField) return `Confirm ${input.unconfirmedKeyField}`;
  if (input.openHighTitle) return `Review high-priority issue: ${input.openHighTitle}`;
  if (input.blockingCpText) return `Complete approval requirement: ${input.blockingCpText}`;
  if (input.pendingVerification) return `Complete verification: ${input.pendingVerification}`;
  if (input.openMediumTitle) return `Review issue: ${input.openMediumTitle}`;
  if (input.openLowTitle) return `Review issue: ${input.openLowTitle}`;
  if (status === "approved") return "Issue bank pack";
  if (status === "new") return "Review matter readiness";
  return "Submit for approval";
}
