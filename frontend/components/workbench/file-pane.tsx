"use client";

import { useRef, useState } from "react";
import { CdsPill, severityTone } from "@/components/ui/cds-pill";
import { CaseDocumentItem, DossierFieldItem } from "@/lib/api";
import { FindingRow } from "@/lib/workbench/findings";
import {
  FileRequirementRow,
  buildFileCompleteness,
  displayCanonicalLabel,
  legalStateLabel,
  missingRequirementLabel,
  processStateLabel,
  requirementMark,
  requirementTone,
  secondaryMeta,
} from "@/lib/workbench/required-evidence";
import { cn } from "@/lib/utils";

type FilePaneProps = {
  documents: CaseDocumentItem[];
  findings: FindingRow[];
  fields?: DossierFieldItem[];
  selectedFindingId: string | null;
  onSelectFinding: (item: FindingRow) => void;
  onOpenDocument: (documentId: string, page?: number) => void;
  onUpload: (files: FileList) => void;
  onRequestDocument: (instrument?: string | null) => void;
  onExtract?: () => void;
  onEvaluate?: () => void;
  requesting?: boolean;
  uploading?: boolean;
  extracting?: boolean;
  evaluating?: boolean;
  busy?: boolean;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
  showReviewSummary?: boolean;
};

function RequirementRow({
  row,
  onFocus,
  onOpenDocument,
}: {
  row: FileRequirementRow;
  onFocus?: () => void;
  onOpenDocument?: (documentId: string, page?: number) => void;
}) {
  const preferredDocumentId = row.preferred?.id;
  return (
    <button
      type="button"
      onClick={() => {
        onFocus?.();
        if (preferredDocumentId) onOpenDocument?.(preferredDocumentId, 1);
      }}
      aria-label={preferredDocumentId ? `Open ${row.preferred?.original_filename || row.label}` : row.label}
      className={cn(
        "group flex w-full flex-col gap-0.5 rounded border border-transparent px-2 py-2 text-left outline-none transition-colors hover:border-border hover:bg-[hsl(var(--pill))] focus-visible:ring-1 focus-visible:ring-ring",
        row.requiredByFinding && "bg-[hsl(var(--pill))]"
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="min-w-0 truncate text-[11px] font-medium text-foreground">
          {requirementMark(row.legalState)} {row.label}
        </p>
        <CdsPill tone={requirementTone(row.legalState)}>{legalStateLabel(row.legalState)}</CdsPill>
      </div>
      {row.preferred ? (
        <>
          <p className="truncate pl-3 text-[10px] text-muted-foreground">{row.preferred.original_filename}</p>
          {secondaryMeta(row.preferred) ? (
            <p className="truncate pl-3 text-[10px] text-muted-foreground">{secondaryMeta(row.preferred)}</p>
          ) : null}
        </>
      ) : null}
      {row.prior.map((doc) => (
        <p key={doc.id} className="truncate pl-3 text-[10px] text-muted-foreground">
          Also on file · {doc.original_filename}
        </p>
      ))}
      {row.requiredByFinding ? (
        <p className="pl-3 text-[10px] text-muted-foreground">Required by this finding</p>
      ) : null}
    </button>
  );
}

export function FilePane({
  documents,
  findings,
  fields = [],
  selectedFindingId,
  onSelectFinding,
  onOpenDocument,
  onUpload,
  onRequestDocument,
  onExtract,
  onEvaluate,
  requesting,
  uploading,
  extracting,
  evaluating,
  busy,
  collapsed,
  onToggleCollapse,
  showReviewSummary = true,
}: FilePaneProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [focusedRequirement, setFocusedRequirement] = useState<string | null>(null);
  const view = buildFileCompleteness(documents, findings, fields, selectedFindingId);
  const selectedFinding = findings.find((item) => item.id === selectedFindingId) ?? null;
  const confirmed = fields.filter((item) => !item.needs_confirmation).length;
  const proposed = fields.filter((item) => item.needs_confirmation).length;
  const total = fields.length;
  const processBusy = extracting || evaluating || busy;
  const requestTarget =
    view.required.find((row) => row.id === focusedRequirement)?.label ??
    missingRequirementLabel(view, selectedFinding);

  if (collapsed) {
    return (
      <button
        type="button"
        className="flex h-full w-full items-start justify-center bg-[hsl(var(--surface))] pt-4"
        onClick={onToggleCollapse}
        aria-label="Expand file pane"
      >
        <span className="cds-meta" style={{ writingMode: "vertical-rl" }}>
          Documents
        </span>
      </button>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col bg-[hsl(var(--surface))]">
      <div className="flex shrink-0 flex-col gap-2.5 border-b border-border p-3.5">
        <div className="flex items-center justify-between gap-2">
          <p className="cds-meta">Documents</p>
          {onToggleCollapse ? (
            <button type="button" className="cds-meta text-muted-foreground" onClick={onToggleCollapse} aria-label="Collapse file pane">
              Collapse
            </button>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            className="cds-btn cds-btn-primary"
            onClick={() => inputRef.current?.click()}
            disabled={uploading || busy}
            aria-label="Upload documents"
          >
            {uploading ? "Uploading…" : "Upload documents"}
          </button>
          <button
            type="button"
            className="cds-btn cds-btn-ghost"
            onClick={onExtract ?? onEvaluate}
            disabled={!onExtract && !onEvaluate || processBusy}
            aria-label="Analyze uploaded documents"
          >
            {extracting || evaluating ? "Analyzing…" : "Analyze uploaded documents"}
          </button>
          <button
            type="button"
            className="cds-btn cds-btn-ghost"
            onClick={() => onRequestDocument(requestTarget)}
            disabled={requesting || busy}
            aria-label={requestTarget ? `Request ${requestTarget}` : "Request document"}
          >
            Request missing document
          </button>
          <input
            ref={inputRef}
            type="file"
            multiple
            className="hidden"
            accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff,.docx"
            onChange={(event) => {
              if (event.target.files?.length) onUpload(event.target.files);
              event.target.value = "";
            }}
          />
        </div>
      </div>

      <div
        className="min-h-0 flex-1 overflow-y-auto"
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault();
          if (event.dataTransfer.files.length) onUpload(event.dataTransfer.files);
        }}
      >
        <section className="border-b border-border px-3.5 py-3">
          <p className="cds-meta mb-1.5">Required documents</p>
          <div className="flex flex-col">
            {view.required.map((row) => (
              <RequirementRow key={row.id} row={row} onFocus={() => setFocusedRequirement(row.id)} onOpenDocument={onOpenDocument} />
            ))}
          </div>
        </section>

        {view.supporting.length > 0 || view.leftover.length > 0 ? (
          <section className="border-b border-border px-3.5 py-3">
            <p className="cds-meta mb-1.5">Supporting documents</p>
            <div className="flex flex-col">
                {view.supporting.map((row) => (
                  <RequirementRow key={row.id} row={row} onFocus={() => setFocusedRequirement(row.id)} onOpenDocument={onOpenDocument} />
                ))}
              {view.leftover.map((doc) => (
                <div key={doc.id} className="flex flex-col gap-0.5 px-1 py-1.5">
                  <div className="flex items-start justify-between gap-2">
                    <p className="min-w-0 truncate text-[11px] font-medium text-foreground">
                      {displayCanonicalLabel(doc.doc_type || doc.predicted_doc_type || doc.corrected_doc_type)}
                    </p>
                    <span className="text-[10px] uppercase tracking-[0.06em] text-muted-foreground">
                      {processStateLabel(doc)}
                    </span>
                  </div>
                  <p className="truncate pl-3 text-[10px] text-muted-foreground">{doc.original_filename}</p>
                  {doc.page_count ? (
                    <p className="truncate pl-3 text-[10px] text-muted-foreground">
                      {doc.page_count} page{doc.page_count === 1 ? "" : "s"}
                    </p>
                  ) : null}
                </div>
              ))}
            </div>
          </section>
        ) : null}

        {showReviewSummary ? (
          <section className="border-b border-border px-3.5 py-3">
            <p className="cds-meta mb-1.5">Issues</p>
            <ul className="space-y-1">
              {findings.map((item) => {
                const selected = item.id === selectedFindingId;
                return (
                  <li key={`${item.kind}-${item.id}`}>
                    <button
                      type="button"
                      onClick={() => onSelectFinding(item)}
                      aria-pressed={selected}
                      className={cn(
                        "flex w-full items-center gap-2 rounded px-1 py-1.5 text-left outline-none focus-visible:ring-1 focus-visible:ring-ring",
                        selected && "bg-[hsl(var(--pill))]"
                      )}
                    >
                      <span className="w-[92px] shrink-0 truncate font-display text-[9px] text-muted-foreground">
                        {item.rule_id ?? (item.kind === "cp" ? "CP" : "EX")}
                      </span>
                      <CdsPill tone={severityTone(item.severity)}>{item.severity}</CdsPill>
                      <span className="min-w-0 flex-1 truncate text-[11px] text-foreground">{item.title}</span>
                      <span className="shrink-0 text-[10px] uppercase tracking-[0.06em] text-muted-foreground">
                        {item.status}
                      </span>
                    </button>
                  </li>
                );
              })}
              {findings.length === 0 ? (
                <li className="py-3 text-[11px] text-muted-foreground">No findings yet.</li>
              ) : null}
            </ul>
          </section>
        ) : null}
      </div>

      {showReviewSummary ? (
        <div className="shrink-0 px-3.5 py-3">
          <p className="cds-meta">Confirmed facts</p>
          <p className="mt-1.5 text-[14px] font-semibold leading-5 text-foreground">
            {total ? `${confirmed} / ${total} confirmed` : "No facts extracted"}
          </p>
          <p className="mt-1.5 text-[10px] leading-[15px] text-muted-foreground">
            {proposed
              ? `${proposed} proposed values require reviewer confirmation`
              : "All extracted values are confirmed"}
          </p>
        </div>
      ) : null}
    </div>
  );
}
