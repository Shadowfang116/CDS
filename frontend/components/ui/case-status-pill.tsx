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
  New: "border-[rgba(100,116,139,0.35)] bg-[rgba(100,116,139,0.14)] text-[rgb(214,222,234)]",
  Processing: "border-[rgba(59,130,246,0.35)] bg-[rgba(59,130,246,0.14)] text-[rgb(191,219,254)]",
  Review: "border-[rgba(234,179,8,0.35)] bg-[rgba(234,179,8,0.14)] text-[rgb(253,240,138)]",
  "Pending Docs":
    "border-[rgba(249,115,22,0.35)] bg-[rgba(249,115,22,0.14)] text-[rgb(254,215,170)]",
  "Ready for Approval":
    "border-[rgba(168,85,247,0.35)] bg-[rgba(168,85,247,0.14)] text-[rgb(233,213,255)]",
  Approved:
    "border-[rgba(34,197,94,0.35)] bg-[rgba(34,197,94,0.14)] text-[rgb(187,247,208)]",
  Rejected: "border-[rgba(239,68,68,0.35)] bg-[rgba(239,68,68,0.14)] text-[rgb(254,202,202)]",
  Closed: "border-[rgba(107,114,128,0.35)] bg-[rgba(107,114,128,0.14)] text-[rgb(209,213,219)]",
};

export function CaseStatusPill(props: {
  status: CaseStatus;
  className?: string;
}) {
  const { status, className } = props;

  return (
    <Badge
      variant="outline"
      className={cn("font-semibold", STATUS_CLASS[status], className)}
    >
      {status}
    </Badge>
  );
}
