import type { NeedsAttentionItem } from "@/lib/api";

const ACTIONABLE_STATUS = new Set([
  "Review",
  "Pending Docs",
  "Processing",
  "New",
  "Ready for Approval",
]);

function rank(item: NeedsAttentionItem, userEmail: string | null): number[] {
  const assignedToMe = Boolean(userEmail) && item.assigned_to_email === userEmail;
  const actionable = ACTIONABLE_STATUS.has(item.status);
  const ageMs = Date.now() - new Date(item.updated_at).getTime();
  return [
    assignedToMe ? 0 : 1,
    actionable ? 0 : 1,
    item.open_high > 0 ? 0 : 1,
    item.pending_verifications > 0 ? 0 : 1,
    -ageMs,
  ];
}

function compareRank(a: number[], b: number[]): number {
  for (let i = 0; i < a.length; i += 1) {
    if (a[i] !== b[i]) {
      return a[i] - b[i];
    }
  }
  return 0;
}

export function pickNextMatter(
  items: NeedsAttentionItem[],
  userEmail: string | null
): NeedsAttentionItem | null {
  if (items.length === 0) {
    return null;
  }

  return [...items].sort((left, right) => compareRank(rank(left, userEmail), rank(right, userEmail)))[0] ?? null;
}

export function nextMatterWhy(item: NeedsAttentionItem): string {
  if (item.open_high > 0) {
    return `${item.open_high} high-risk exception${item.open_high === 1 ? "" : "s"}`;
  }
  if (item.pending_verifications > 0) {
    return `${item.pending_verifications} check${item.pending_verifications === 1 ? "" : "s"} outstanding`;
  }
  if (item.open_medium + item.open_low > 0) {
    return `${item.open_medium + item.open_low} open exception${item.open_medium + item.open_low === 1 ? "" : "s"}`;
  }
  return item.status;
}

export function formatWait(dateString: string): string {
  const diffMs = Math.max(0, Date.now() - new Date(dateString).getTime());
  const hours = Math.floor(diffMs / (1000 * 60 * 60));
  const days = Math.floor(hours / 24);
  const remHours = hours % 24;
  if (days <= 0) {
    return `${String(hours).padStart(2, "0")}H`;
  }
  return `${String(days).padStart(2, "0")}D ${String(remHours).padStart(2, "0")}H`;
}
