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
  New: "border-border bg-muted text-muted-foreground",
  Processing: "border-[hsl(var(--info)/0.35)] bg-[hsl(var(--info)/0.12)] text-[hsl(var(--info))]",
  Review: "border-[hsl(var(--gold)/0.35)] bg-[hsl(var(--gold)/0.12)] text-[hsl(var(--gold))]",
  "Pending Docs": "border-[hsl(var(--gold)/0.35)] bg-[hsl(var(--gold)/0.12)] text-[hsl(var(--gold))]",
  "Ready for Approval": "border-[hsl(var(--sage)/0.35)] bg-[hsl(var(--sage)/0.12)] text-[hsl(var(--sage))]",
  Approved: "border-[hsl(var(--sage)/0.35)] bg-[hsl(var(--sage)/0.12)] text-[hsl(var(--sage))]",
  Rejected: "border-[hsl(var(--status-high)/0.35)] bg-[hsl(var(--status-high)/0.12)] text-[hsl(var(--status-high))]",
  Closed: "border-border bg-muted text-muted-foreground",
};

export function CaseStatusPill(props: {
  status: CaseStatus;
  className?: string;
}) {
  const { status, className } = props;
  const displayStatus = status
    .trim()
    .toLowerCase()
    .split(" ")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ") as CaseStatus;

  return (
    <Badge
      variant="outline"
      className={cn("font-semibold", STATUS_CLASS[displayStatus] ?? STATUS_CLASS.New, className)}
    >
      {displayStatus}
    </Badge>
  );
}
