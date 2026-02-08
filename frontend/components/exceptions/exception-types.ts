import { Severity } from "@/components/ui/severity-badge";

export type ExceptionStatus = "open" | "resolved" | "waived";

export type ExceptionEvidenceRef = {
  doc_id: string;
  page: number;
  snippet?: string;
};

export type ExceptionRow = {
  id: string;
  severity: Severity;
  module: string;
  title: string;
  description: string;
  status: ExceptionStatus;
  cp_text?: string;
  waiver_reason?: string | null;
  evidence_refs: ExceptionEvidenceRef[];
};
