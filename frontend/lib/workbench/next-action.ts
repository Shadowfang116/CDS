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
  if (input.hardStopTitle) return `Clear hard-stop: ${input.hardStopTitle}`;
  if (input.missingRequiredCausingHigh) return `Attach required evidence: ${input.missingRequiredCausingHigh}`;
  if (input.unconfirmedKeyField) return `Confirm ${input.unconfirmedKeyField}`;
  if (input.openHighTitle) return `Review high exception: ${input.openHighTitle}`;
  if (input.blockingCpText) return `Clear CP: ${input.blockingCpText}`;
  if (input.pendingVerification) return `Complete verification: ${input.pendingVerification}`;
  if (input.openMediumTitle) return `Review exception: ${input.openMediumTitle}`;
  if (input.openLowTitle) return `Review exception: ${input.openLowTitle}`;
  return input.status === "Approved" ? "Issue bank pack" : "Submit for approval";
}
