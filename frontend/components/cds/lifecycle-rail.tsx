"use client";

import { cn } from "@/lib/utils";

const STEPS = [
  "New",
  "Processing",
  "Review",
  "Pending Docs",
  "Ready for Approval",
  "Approved",
] as const;

function stepLabel(step: (typeof STEPS)[number]) {
  if (step === "Ready for Approval") return "Ready";
  if (step === "Pending Docs") return "Pending docs";
  return step;
}

export function LifecycleRail({ status }: { status: string }) {
  const normalized = status.toLowerCase();

  return (
    <ol className="flex flex-wrap items-center gap-x-[18px] gap-y-2 font-display text-[10px] font-medium uppercase tracking-[0.04em] text-muted-foreground">
      {STEPS.map((step) => {
        const current =
          step.toLowerCase() === normalized ||
          (normalized === "ready" && step === "Ready for Approval") ||
          (normalized === "review" && step === "Review");
        return (
          <li key={step} className="flex items-center gap-[18px]">
            <span className={cn(current ? "text-foreground" : undefined)}>{stepLabel(step)}</span>
            {current ? <span className="h-0.5 w-[55px] bg-[hsl(var(--crimson-border))]" /> : null}
          </li>
        );
      })}
    </ol>
  );
}
