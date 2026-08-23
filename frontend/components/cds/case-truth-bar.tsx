"use client";

type CaseTruthBarProps = {
  title: string;
  status: string;
  highExceptions: number;
  openCps: number;
  documents: number;
  blockedBy?: string | null;
  nextAction?: string | null;
};

export function CaseTruthBar({
  title,
  status,
  highExceptions,
  openCps,
  documents,
  blockedBy,
  nextAction,
}: CaseTruthBarProps) {
  return (
    <header className="border-b border-border pb-5">
      <div className="flex flex-wrap items-baseline justify-between gap-4">
        <h1 className="max-w-[28ch] text-[clamp(1.75rem,2.4vw,2.25rem)] font-medium leading-tight tracking-[-0.03em] text-foreground">
          {title}
        </h1>
        <p className="cds-meta">{status}</p>
      </div>
      <div className="mt-4 flex flex-wrap gap-x-8 gap-y-2 text-sm tabular">
        <span className={highExceptions > 0 ? "text-primary" : "text-muted-foreground"}>
          {String(highExceptions).padStart(2, "0")} high-risk exception{highExceptions === 1 ? "" : "s"}
        </span>
        <span className="text-muted-foreground">
          {String(openCps).padStart(2, "0")} open CP{openCps === 1 ? "" : "s"}
        </span>
        <span className="text-muted-foreground">
          {String(documents).padStart(2, "0")} document{documents === 1 ? "" : "s"}
        </span>
      </div>
      {blockedBy ? <p className="mt-3 text-sm text-foreground">Blocked by {blockedBy}</p> : null}
      {nextAction ? <p className="mt-1 text-sm text-muted-foreground">Next action: {nextAction}</p> : null}
    </header>
  );
}
