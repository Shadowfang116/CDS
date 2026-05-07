"use client";

import { ExceptionRow } from "@/components/exceptions/exception-types";

function normalizeExceptionRow(raw: any): ExceptionRow {
  return {
    id: String(raw?.id ?? ""),
    severity: String(raw?.severity ?? "low").toLowerCase() as ExceptionRow["severity"],
    module: String(raw?.module ?? ""),
    title: String(raw?.title ?? ""),
    description: String(raw?.description ?? ""),
    status: String(raw?.status ?? "open").toLowerCase() as ExceptionRow["status"],
    cp_text: raw?.cp_text ?? undefined,
    waiver_reason: raw?.waiver_reason ?? null,
    evidence_refs: Array.isArray(raw?.evidence_refs)
      ? raw.evidence_refs.map((ref: any) => ({
          doc_id: String(ref?.doc_id ?? ref?.document_id ?? ""),
          page: Number(ref?.page ?? ref?.page_number ?? 0),
          snippet: ref?.snippet ?? ref?.note ?? undefined,
        }))
      : [],
  };
}

function extractExceptionRows(raw: any): ExceptionRow[] {
  const rows = Array.isArray(raw)
    ? raw
    : Array.isArray(raw?.exceptions)
      ? raw.exceptions
      : [];

  return rows.map(normalizeExceptionRow);
}

export async function fetchCaseExceptions(caseId: string): Promise<ExceptionRow[]> {
  const res = await fetch(`/api/cases/${caseId}/exceptions`, {
    cache: "no-store",
    credentials: "include",
  });
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`Failed to fetch exceptions: ${res.status} ${txt}`);
  }
  return extractExceptionRows(await res.json());
}

export async function resolveException(exceptionId: string, payload?: any): Promise<ExceptionRow> {
  const res = await fetch(`/api/exceptions/${exceptionId}/resolve`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
    },
    credentials: "include",
    body: JSON.stringify(payload ?? {}),
  });
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`Resolve failed: ${res.status} ${txt}`);
  }
  return normalizeExceptionRow(await res.json());
}

export async function waiveException(exceptionId: string, payload: { waiver_reason: string }): Promise<ExceptionRow> {
  const res = await fetch(`/api/exceptions/${exceptionId}/waive`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
    },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`Waive failed: ${res.status} ${txt}`);
  }
  return normalizeExceptionRow(await res.json());
}
