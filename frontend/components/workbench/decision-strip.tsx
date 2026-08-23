"use client";

import { CdsPill } from "@/components/ui/cds-pill";
import { LifecycleRail } from "@/components/cds/lifecycle-rail";
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

  return (
    <header className="shrink-0 border-b border-border bg-background px-4 pb-3.5 pt-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="max-w-[48ch] truncate text-[18px] font-semibold leading-[26px] text-foreground">{title}</h1>
          {borrower ? (
            <p className="cds-extract-text mt-0.5 truncate text-[12px] text-muted-foreground" {...urduTextProps(borrower)}>
              {borrower}
            </p>
          ) : null}
          {facility ? <p className="truncate text-[11px] text-muted-foreground">{facility}</p> : null}
        </div>
        <div className="flex shrink-0 items-center gap-3 pt-1">
          <span className="cds-meta">Status {status}</span>
          <CdsPill tone={fail ? "fail" : "neutral"}>Decision {decision ?? "—"}</CdsPill>
          {readiness ? <CdsPill tone={ready ? "good" : "stale"}>{readiness}</CdsPill> : null}
        </div>
      </div>
      <div className="mt-2">
        <LifecycleRail status={status} />
      </div>
      <div className="mt-2.5 flex flex-wrap items-center gap-x-[22px] gap-y-1 text-[11px] font-medium text-foreground">
        <span>{highExceptions} HIGH</span>
        {hardStops > 0 ? <span>{hardStops} HARD-STOP</span> : null}
        <span>{openCps} OPEN CPs</span>
        <span>{documents} DOCUMENTS</span>
        {jurisdiction ? <CdsPill>{jurisdiction}</CdsPill> : null}
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-x-6 gap-y-1 text-[12px] font-medium text-foreground">
        {blocker ? (
          <p className="flex min-w-0 items-center gap-2">
            <span className="cds-meta">Blocked by</span>
            <span className="truncate">{blocker}</span>
          </p>
        ) : null}
        {nextAction ? (
          <p className="flex min-w-0 items-center gap-2">
            <span className="cds-meta">Next</span>
            <span className="truncate">{nextAction}</span>
          </p>
        ) : null}
      </div>
    </header>
  );
}
