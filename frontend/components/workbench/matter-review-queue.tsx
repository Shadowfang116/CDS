"use client";

import { CdsPill, severityTone } from "@/components/ui/cds-pill";
import { CaseDocumentItem, DossierFieldItem } from "@/lib/api";
import { FindingRow, firstEvidenceRef } from "@/lib/workbench/findings";
import { buildFileCompleteness, legalStateLabel } from "@/lib/workbench/required-evidence";
import { getFieldLabelMeta } from "@/lib/field-labels";
import { cn } from "@/lib/utils";

type MatterReviewQueueProps = {
  documents: CaseDocumentItem[];
  findings: FindingRow[];
  fields: DossierFieldItem[];
  selectedFindingId: string | null;
  selectedFieldKey: string | null;
  onSelectFinding: (item: FindingRow) => void;
  onSelectField: (field: DossierFieldItem) => void;
  onOpenDocument: (documentId: string, page?: number) => void;
  onRequestDocument: (label: string) => void;
};

function QueueRow({
  selected,
  label,
  detail,
  status,
  onClick,
  children,
}: {
  selected: boolean;
  label: string;
  detail: string;
  status: string;
  onClick: () => void;
  children?: React.ReactNode;
}) {
  return (
    <li>
      <button
        type="button"
        aria-pressed={selected}
        onClick={onClick}
        className={cn(
          "w-full border-b border-border px-3.5 py-3 text-left transition-colors hover:bg-[hsl(var(--pill))] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
          selected && "bg-[hsl(var(--pill))]"
        )}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-[12px] font-semibold text-foreground">{label}</p>
            <p className="mt-1 text-[11px] leading-4 text-muted-foreground">{detail}</p>
          </div>
          <span className="shrink-0 text-[10px] font-medium text-muted-foreground">{status}</span>
        </div>
        {children}
      </button>
    </li>
  );
}

export function MatterReviewQueue({
  documents,
  findings,
  fields,
  selectedFindingId,
  selectedFieldKey,
  onSelectFinding,
  onSelectField,
  onOpenDocument,
  onRequestDocument,
}: MatterReviewQueueProps) {
  const completeness = buildFileCompleteness(documents, findings, fields);
  const missing = completeness.required.filter((item) => ["missing", "weak"].includes(item.legalState));
  const proposed = fields.filter((field) => field.needs_confirmation);
  const openFindings = findings.filter((item) => item.status === "Open");

  return (
    <div className="flex h-full min-h-0 flex-col bg-[hsl(var(--surface))]">
      <header className="shrink-0 border-b border-border px-3.5 py-3">
        <p className="cds-meta">Review</p>
        <h2 className="mt-1 text-[16px] font-semibold text-foreground">Items needing your attention</h2>
        <p className="mt-1 text-[11px] leading-4 text-muted-foreground">
          Open one item to review its source and next action.
        </p>
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {missing.length > 0 ? (
          <section aria-labelledby="missing-evidence-heading">
            <h3 id="missing-evidence-heading" className="cds-meta px-3.5 pb-1 pt-3">
              Missing evidence
            </h3>
            <ul>
              {missing.map((item) => (
                <QueueRow
                  key={`missing-${item.id}`}
                  selected={false}
                  label={item.label}
                  detail="Upload or replace this document before relying on the review."
                  status={legalStateLabel(item.legalState)}
                  onClick={() => item.preferred?.id ? onOpenDocument(item.preferred.id, 1) : onRequestDocument(item.label)}
                />
              ))}
            </ul>
          </section>
        ) : null}

        {openFindings.length > 0 ? (
          <section aria-labelledby="issues-heading">
            <h3 id="issues-heading" className="cds-meta px-3.5 pb-1 pt-3">
              Issues and approval requirements
            </h3>
            <ul>
              {openFindings.map((item) => {
                const evidence = firstEvidenceRef(item);
                return (
                  <QueueRow
                    key={`${item.kind}-${item.id}`}
                    selected={item.id === selectedFindingId}
                    label={item.title}
                    detail={item.kind === "cp" ? "Approval requirement" : item.description || "Review the source and choose the next action."}
                    status={item.status}
                    onClick={() => onSelectFinding(item)}
                  >
                    <div className="mt-2 flex items-center gap-2">
                      <CdsPill tone={severityTone(item.severity)}>{item.severity}</CdsPill>
                      {evidence ? <span className="text-[10px] text-muted-foreground">Source p.{evidence.page}</span> : null}
                    </div>
                  </QueueRow>
                );
              })}
            </ul>
          </section>
        ) : null}

        {proposed.length > 0 ? (
          <section aria-labelledby="facts-heading">
            <h3 id="facts-heading" className="cds-meta px-3.5 pb-1 pt-3">
              Facts to confirm
            </h3>
            <ul>
              {proposed.map((field) => (
                <QueueRow
                  key={field.field_key}
                  selected={field.field_key === selectedFieldKey}
                  label={getFieldLabelMeta(field.field_key).label}
                  detail={field.field_value || "A value was extracted and needs confirmation."}
                  status="Review required"
                  onClick={() => onSelectField(field)}
                />
              ))}
            </ul>
          </section>
        ) : null}

        {missing.length === 0 && openFindings.length === 0 && proposed.length === 0 ? (
          <div className="px-3.5 py-8">
            <p className="text-[14px] font-semibold text-foreground">Nothing needs review</p>
            <p className="mt-1 text-[12px] leading-5 text-muted-foreground">
              The matter can move to the decision step when readiness checks are complete.
            </p>
          </div>
        ) : null}
      </div>
    </div>
  );
}
