export type HeaderField = {
  field_key?: string | null;
  field_value?: string | null;
};

export type HeaderFinding = {
  status?: string | null;
  kind?: string | null;
  severity?: string | null;
  title?: string | null;
  is_hard_stop?: boolean;
};

function valueOf(fields: HeaderField[], keys: string[]): string | null {
  for (const key of keys) {
    const hit = fields.find((item) => item.field_key === key)?.field_value?.trim();
    if (hit) return hit;
  }
  return null;
}

export function matterBorrower(fields: HeaderField[]): string | null {
  return valueOf(fields, ["party.name.borrower", "party.buyer.names"]);
}

export function matterFacility(fields: HeaderField[]): string | null {
  return valueOf(fields, ["facility.amount", "facility.limit", "facility.finance_type"]);
}

export function matterRegime(fields: HeaderField[]): string | null {
  const scheme = valueOf(fields, ["property.scheme_name"]);
  const regime = valueOf(fields, ["property.regime", "property.authority"]);
  if (scheme && regime && scheme.toLowerCase() !== regime.toLowerCase()) {
    return `${scheme} · ${regime}`;
  }
  return scheme || regime;
}

export function openHighCount(findings: HeaderFinding[]): number {
  return findings.filter(
    (item) => item.kind !== "cp" && item.status === "Open" && item.severity === "High"
  ).length;
}

export function openHardStopCount(findings: HeaderFinding[]): number {
  return findings.filter((item) => item.status === "Open" && item.is_hard_stop).length;
}

export function openCpCount(findings: HeaderFinding[]): number {
  return findings.filter((item) => item.kind === "cp" && item.status === "Open").length;
}

export function primaryBlocker(
  findings: HeaderFinding[],
  readinessReasons: string[] = []
): string | null {
  const open = findings.filter((item) => item.status === "Open");
  const hard = open.find((item) => item.is_hard_stop);
  if (hard?.title) return hard.title;
  const high = open.find((item) => item.kind !== "cp" && item.severity === "High");
  if (high?.title) return high.title;
  const cp = open.find((item) => item.kind === "cp");
  if (cp?.title) return cp.title;
  return readinessReasons[0] ?? null;
}

export function readinessLabel(ready: boolean | undefined, status?: string | null): string {
  const normalized = (status ?? "").toLowerCase();
  if (normalized === "approved") return "Approved";
  if (normalized === "ready for approval" || normalized === "ready") return "Ready";
  if (ready) return "Ready";
  return "Not ready";
}
