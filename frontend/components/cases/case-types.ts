import { CaseStatus } from "@/components/ui/case-status-pill";
import { Severity } from "@/components/ui/severity-badge";

export type CaseRow = {
  id: string;
  borrower_name: string;
  property_type: "Society Plot" | "Urban House";
  status: CaseStatus;
  highest_severity: Severity;
  open_exceptions: number;
  open_cps: number;
  updated_at: string; // ISO string
};
