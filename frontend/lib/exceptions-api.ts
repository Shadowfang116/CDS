"use client";

import { ExceptionRow } from "@/components/exceptions/exception-types";

export async function fetchCaseExceptions(caseId: string): Promise<ExceptionRow[]> {
  const res = await fetch(`/api/cases/${caseId}/exceptions`, { cache: "no-store" });
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`Failed to fetch exceptions: ${res.status} ${txt}`);
  }
  return (await res.json()) as ExceptionRow[];
}

export async function resolveException(exceptionId: string, payload?: any): Promise<ExceptionRow> {
  const res = await fetch(`/api/exceptions/${exceptionId}/resolve`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload ?? {}),
  });
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`Resolve failed: ${res.status} ${txt}`);
  }
  return (await res.json()) as ExceptionRow;
}

export async function waiveException(exceptionId: string, payload: { waiver_reason: string }): Promise<ExceptionRow> {
  const res = await fetch(`/api/exceptions/${exceptionId}/waive`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`Waive failed: ${res.status} ${txt}`);
  }
  return (await res.json()) as ExceptionRow;
}
