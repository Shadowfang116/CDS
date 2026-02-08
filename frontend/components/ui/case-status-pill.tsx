import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export type CaseStatus =
  | "New"
  | "Processing"
  | "Review"
  | "Pending Docs"
  | "Ready for Approval"
  | "Approved"
  | "Rejected"
  | "Closed";

const STATUS_CLASS: Record<CaseStatus, string> = {
  New: "border-muted-foreground/30 text-foreground bg-background",
  Processing: "border-sky-500/30 text-sky-700 dark:text-sky-300 bg-sky-500/10",
  Review: "border-indigo-500/30 text-indigo-700 dark:text-indigo-300 bg-indigo-500/10",
  "Pending Docs":
    "border-amber-500/30 text-amber-700 dark:text-amber-300 bg-amber-500/10",
  "Ready for Approval":
    "border-emerald-500/30 text-emerald-700 dark:text-emerald-300 bg-emerald-500/10",
  Approved:
    "border-emerald-500/30 text-emerald-700 dark:text-emerald-300 bg-emerald-500/10",
  Rejected: "border-red-500/30 text-red-700 dark:text-red-300 bg-red-500/10",
  Closed: "border-muted-foreground/30 text-muted-foreground bg-muted",
};

export function CaseStatusPill(props: {
  status: CaseStatus;
  className?: string;
}) {
  const { status, className } = props;

  return (
    <Badge
      variant="outline"
      className={cn("font-medium", STATUS_CLASS[status], className)}
    >
      {status}
    </Badge>
  );
}
