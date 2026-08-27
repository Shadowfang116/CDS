import { cn } from "@/lib/utils";

export type WorkflowStepId = "upload" | "analyze" | "review" | "issues" | "facts" | "submit";

const STEPS: Array<{ id: WorkflowStepId; label: string }> = [
  { id: "upload", label: "Upload documents" },
  { id: "analyze", label: "Analyze documents" },
  { id: "review", label: "Review evidence" },
  { id: "issues", label: "Resolve issues" },
  { id: "facts", label: "Confirm facts" },
  { id: "submit", label: "Submit for approval" },
];

export function workflowStepForMatter(input: {
  documentCount: number;
  processing: boolean;
  issueCount: number;
  unconfirmedCount: number;
  ready: boolean;
}): WorkflowStepId {
  if (input.documentCount === 0) return "upload";
  if (input.processing) return "analyze";
  if (input.issueCount > 0) return "issues";
  if (input.unconfirmedCount > 0) return "facts";
  if (!input.ready) return "review";
  return "submit";
}

export function WorkflowStepper({
  active,
  onSelect,
}: {
  active: WorkflowStepId;
  onSelect: (step: WorkflowStepId) => void;
}) {
  const activeIndex = STEPS.findIndex((step) => step.id === active);
  return (
    <nav aria-label="Matter workflow" className="border-b border-border bg-[hsl(var(--surface))] px-4 py-3 sm:px-5">
      <ol className="flex min-w-max items-center gap-1 sm:min-w-0 sm:justify-between sm:gap-2">
        {STEPS.map((step, index) => {
          const complete = index < activeIndex;
          const current = step.id === active;
          return (
            <li key={step.id} className="flex items-center gap-1 sm:min-w-0 sm:flex-1">
              <button
                type="button"
                onClick={() => onSelect(step.id)}
                aria-current={current ? "step" : undefined}
                className={cn(
                  "flex items-center gap-2 rounded-md px-2 py-1.5 text-left text-[11px] transition-colors hover:bg-[hsl(var(--pill))]",
                  current ? "font-semibold text-foreground" : "text-muted-foreground"
                )}
              >
                <span className={cn(
                  "flex size-5 shrink-0 items-center justify-center rounded-full border text-[10px] font-semibold",
                  current && "border-foreground bg-foreground text-background",
                  complete && "border-[hsl(var(--status-good))] text-[hsl(var(--status-good))]",
                  !current && !complete && "border-border"
                )}>
                  {complete ? "✓" : index + 1}
                </span>
                <span className="hidden truncate sm:inline">{step.label}</span>
              </button>
              {index < STEPS.length - 1 ? <span className="h-px min-w-3 flex-1 bg-border" aria-hidden="true" /> : null}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

export const WORKFLOW_STEPS = STEPS;
