export type SubmitGateInput = {
  ready: boolean;
  blockedReasons: string[];
  decision: string | null;
};

export function submitEnabled(input: SubmitGateInput): boolean {
  if (!input.ready) return false;
  if (input.decision === "FAIL") return false;
  return input.blockedReasons.length === 0;
}

export function submitBlocker(input: SubmitGateInput): string | null {
  if (input.decision === "FAIL") return "Decision is FAIL — clear hard-stops and open High exceptions first";
  if (input.blockedReasons[0]) return input.blockedReasons[0];
  if (!input.ready) return "Readiness is not met";
  return null;
}

export function acknowledgementsComplete(requiredIds: string[], acknowledged: string[]): boolean {
  if (requiredIds.length === 0) return true;
  const set = new Set(acknowledged);
  return requiredIds.every((id) => set.has(id));
}

export function canSelfApprove(submittedBy: string | null, currentUserId: string | null): boolean {
  if (!submittedBy || !currentUserId) return false;
  return submittedBy === currentUserId;
}
