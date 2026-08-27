"use client";

import { CdsPill } from "@/components/ui/cds-pill";
import { urduTextProps } from "@/lib/text-script";

type DecisionStripProps = {
  title: string;
  status: string;
  decision: string | null;
  highExceptions: number;
  hardStops?: number;
  openCps: number;
  documents: number;
  nextAction?: string | null;
  jurisdiction?: string | null;
  borrower?: string | null;
  facility?: string | null;
  blocker?: string | null;
  readiness?: string | null;
};

export function DecisionStrip({
  title,
  status,
  decision,
  highExceptions,
  hardStops = 0,
  openCps,
  documents,
  nextAction,
  jurisdiction,
  borrower,
  facility,
  blocker,
  readiness,
}: DecisionStripProps) {
  const fail = (decision ?? "").toUpperCase() === "FAIL";
  const ready = (readiness ?? "").toLowerCase() === "ready" || (readiness ?? "").toLowerCase() === "approved";
  const statusLabel = readiness ?? status;

  return (
    <header className="shrink-0 border-b border-border bg-background px-5 pb-3 pt-3">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="max-w-[48ch] truncate text-[20px] font-semibold leading-[28px] text-foreground">{title}</h1>
            <CdsPill tone={fail ? "fail" : ready ? "good" : "stale"}>{statusLabel}</CdsPill>
          </div>
          {borrower ? (
            <p className="cds-extract-text mt-0.5 truncate text-[12px] text-muted-foreground" {...urduTextProps(borrower)}>
              {borrower}
            </p>
          ) : null}
          {facility ? <p className="truncate text-[11px] text-muted-foreground">{facility}</p> : null}
        </div>
        <div className="shrink-0 pt-1 text-right text-[11px] text-muted-foreground">
          <p>Stage: <span className="font-medium text-foreground">{status}</span></p>
          <p className="mt-1">{decision ? `Decision: ${decision}` : "No decision yet"}</p>
        </div>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-muted-foreground">
        <span>{documents} document{documents === 1 ? "" : "s"}</span>
        <span>{highExceptions} high-priority issue{highExceptions === 1 ? "" : "s"}</span>
        {hardStops > 0 ? <span>{hardStops} blocking issue{hardStops === 1 ? "" : "s"}</span> : null}
        <span>{openCps} approval requirement{openCps === 1 ? "" : "s"} outstanding</span>
        {jurisdiction ? <span>{jurisdiction}</span> : null}
      </div>
      <div className="mt-2 grid gap-1 text-[12px] font-medium text-foreground sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] sm:gap-x-6">
        {blocker ? (
          <p className="min-w-0">
            <span className="cds-meta mr-2">What is stopping approval</span>{" "}
            <span>{blocker}</span>
          </p>
        ) : null}
        {nextAction ? (
          <p className="min-w-0">
            <span className="cds-meta mr-2">Next step</span>{" "}
            <span>{nextAction}</span>
          </p>
        ) : null}
      </div>
    </header>
  );
}
