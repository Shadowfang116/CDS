import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export type Severity =
  | "info"
  | "low"
  | "medium"
  | "high"
  | "critical";

const SEVERITY_LABEL: Record<Severity, string> = {
  info: "Info",
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

const SEVERITY_CLASS: Record<Severity, string> = {
  info: "border-[rgba(82,90,99,0.45)] bg-[rgba(34,39,45,0.9)] text-stone-200",
  low: "border-[rgba(148,163,184,0.34)] bg-[rgba(96,165,250,0.12)] text-[rgb(191,219,254)]",
  medium: "border-[rgba(234,179,8,0.38)] bg-[rgba(234,179,8,0.16)] text-[rgb(254,240,138)]",
  high: "border-[rgba(245,158,11,0.4)] bg-[rgba(245,158,11,0.16)] text-[rgb(253,230,138)]",
  critical: "border-[rgba(239,68,68,0.38)] bg-[rgba(239,68,68,0.16)] text-[rgb(254,202,202)]",
};

function normalizeSeverity(value: string | null | undefined): Severity {
  const normalized = (value ?? '').trim().toLowerCase();
  if (normalized === 'critical') return 'critical';
  if (normalized === 'high') return 'high';
  if (normalized === 'medium') return 'medium';
  if (normalized === 'low') return 'low';
  return 'info';
}

export function SeverityBadge(props: {
  severity: Severity | string | null | undefined;
  className?: string;
}) {
  const { severity, className } = props;
  const normalizedSeverity = normalizeSeverity(severity);

  return (
    <Badge
      variant="outline"
      className={cn("font-medium", SEVERITY_CLASS[normalizedSeverity], className)}
    >
      {SEVERITY_LABEL[normalizedSeverity]}
    </Badge>
  );
}
