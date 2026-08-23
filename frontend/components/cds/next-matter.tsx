"use client";

import { Button } from "@/components/ui/button";
import { formatWait } from "@/lib/next-matter";
import { cn } from "@/lib/utils";

type NextMatterProps = {
  title: string | null;
  status?: string;
  reason?: string;
  updatedAt?: string;
  highCount?: number;
  checkCount?: number;
  blockedBy?: string;
  loading?: boolean;
  onOpen?: () => void;
};

const OVERVIEW_BUTTON_CLASS =
  "h-11 rounded-[2px] bg-primary px-5 text-primary-foreground shadow-none transition-[filter] duration-[180ms] ease-out hover:bg-primary hover:brightness-[1.06] hover:shadow-none hover:translate-y-0 active:translate-y-0 focus-visible:ring-0";

export function NextMatter({
  title,
  status,
  reason,
  updatedAt,
  highCount,
  checkCount,
  blockedBy,
  loading,
  onOpen,
}: NextMatterProps) {
  if (loading) {
    return (
      <div className="space-y-5" aria-busy="true">
        <div className="h-3 w-24 bg-muted" />
        <div className="h-20 w-4/5 max-w-4xl bg-muted" />
        <div className="h-3 w-48 bg-muted" />
      </div>
    );
  }

  if (!title) {
    return (
      <div className="flex flex-col gap-5">
        <p className="cds-meta">Next matter</p>
        <h1 className="cds-overview-display">Review queue is clear</h1>
        <p className="max-w-md text-sm leading-6 text-muted-foreground">
          No matter currently requires intervention in this window.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6" data-dashboard-reveal>
      <div className="flex items-baseline justify-between gap-6">
        <p className="cds-meta">{status ?? "Review"}</p>
        <p className="cds-meta tabular">
          {new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </p>
      </div>
      <h1 className="cds-overview-display max-w-[16ch]">{title}</h1>
      <div className="flex flex-wrap gap-x-8 gap-y-2 text-sm">
        {typeof highCount === "number" ? (
          <p className={cn("tabular", highCount > 0 ? "text-primary" : "text-muted-foreground")}>
            {String(highCount).padStart(2, "0")} high-risk
          </p>
        ) : null}
        {typeof checkCount === "number" ? (
          <p className="tabular text-muted-foreground">
            {String(checkCount).padStart(2, "0")} checks
          </p>
        ) : null}
      </div>
      <div className="max-w-xl space-y-1 text-sm text-muted-foreground">
        {reason ? <p>{reason}</p> : null}
        {updatedAt ? <p className="tabular">Waiting {formatWait(updatedAt)}</p> : null}
        {blockedBy ? <p>Blocked by {blockedBy}</p> : null}
      </div>
      <div>
        <Button variant="primary" className={OVERVIEW_BUTTON_CLASS} onClick={onOpen}>
          Open next matter
        </Button>
      </div>
    </div>
  );
}
