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

// Keep styles conservative (bank-grade). No neon.
const SEVERITY_CLASS: Record<Severity, string> = {
  info: "border-muted-foreground/30 text-foreground bg-muted",
  low: "border-muted-foreground/30 text-foreground bg-background",
  medium: "border-amber-500/30 text-amber-700 dark:text-amber-300 bg-amber-500/10",
  high: "border-orange-500/30 text-orange-700 dark:text-orange-300 bg-orange-500/10",
  critical: "border-red-500/30 text-red-700 dark:text-red-300 bg-red-500/10",
};

export function SeverityBadge(props: {
  severity: Severity;
  className?: string;
}) {
  const { severity, className } = props;

  return (
    <Badge
      variant="outline"
      className={cn("font-medium", SEVERITY_CLASS[severity], className)}
    >
      {SEVERITY_LABEL[severity]}
    </Badge>
  );
}
