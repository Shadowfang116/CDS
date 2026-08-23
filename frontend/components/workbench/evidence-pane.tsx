"use client";

import { DocumentViewer } from "@/components/documents/DocumentViewer";
import { CdsPill } from "@/components/ui/cds-pill";
import { CaseDocumentItem } from "@/lib/api";
import { FindingRow, canonicalDocType } from "@/lib/workbench/findings";

type EvidencePaneProps = {
  caseId: string;
  documents: CaseDocumentItem[];
  selectedDocId?: string;
  selectedPage?: number;
  selectedFinding?: FindingRow | null;
  onAttachEvidence: (documentId: string, pageNumber: number) => void;
  onOpenFullViewer: () => void;
};

function ocrTone(status?: string | null): "good" | "stale" | "missing" | "neutral" {
  const value = (status ?? "").replace(/\s+/g, "_").toLowerCase();
  if (value === "complete" || value === "done") return "good";
  if (value === "needs_review") return "stale";
  if (value === "failed") return "missing";
  return "neutral";
}

function ocrLabel(status?: string | null): string {
  const value = (status ?? "").replace(/\s+/g, "_").toLowerCase();
  if (value === "complete" || value === "done") return "OCR good";
  if (value === "needs_review") return "Needs review";
  if (value === "failed") return "OCR failed";
  if (value === "uploaded") return "Uploaded";
  return status || "OCR";
}

export function EvidencePane({
  caseId,
  documents,
  selectedDocId,
  selectedPage,
  selectedFinding,
  onAttachEvidence,
  onOpenFullViewer,
}: EvidencePaneProps) {
  const selected = documents.find((item) => item.id === selectedDocId) ?? documents[0] ?? null;
  const typeLabel = selected ? canonicalDocType(selected) : null;
  const pageCount = selected?.page_count || 0;
  const page = selectedPage || 1;
  const confidence =
    typeof selected?.classification_confidence === "number"
      ? Math.round(Number(selected.classification_confidence) * (selected.classification_confidence <= 1 ? 100 : 1))
      : null;
  const highlight = selectedFinding?.evidence_refs?.find((entry) => entry.note)?.note ?? selectedFinding?.title ?? null;

  return (
    <div className="flex h-full min-h-0 flex-col bg-background">
      <div className="flex shrink-0 flex-col gap-2 border-b border-border bg-[hsl(var(--surface))] px-4 pb-3 pt-3.5">
        <p className="cds-meta">Evidence</p>
        {selected ? (
          <>
            <div className="flex flex-wrap items-center gap-2.5">
              <p className="truncate text-[12px] font-semibold leading-[17px] text-foreground">{selected.original_filename}</p>
              {typeLabel ? <CdsPill>{typeLabel}</CdsPill> : null}
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-[11px] font-medium text-muted-foreground">
                Page {page} of {pageCount || "—"}
              </span>
              <CdsPill tone={ocrTone(selected.status)}>{ocrLabel(selected.status)}</CdsPill>
              {confidence !== null ? <span className="text-[10px] text-muted-foreground">{confidence}% confidence</span> : null}
              <button
                type="button"
                className="cds-btn cds-btn-ghost"
                onClick={() => onAttachEvidence(selected.id, page)}
              >
                Attach as evidence
              </button>
              <button type="button" className="cds-btn cds-btn-primary" onClick={onOpenFullViewer}>
                Open viewer
              </button>
            </div>
          </>
        ) : (
          <p className="text-[12px] text-muted-foreground">Add evidence to inspect the source page.</p>
        )}
      </div>
      <div className="min-h-0 flex-1">
        <DocumentViewer
          caseId={caseId}
          documents={documents}
          initialDocId={selectedDocId}
          initialPage={selectedPage}
          variant="workbench"
          highlightLabel={selectedFinding?.rule_id ? selectedFinding.title : highlight}
          highlightValue={highlight}
          onAttachEvidence={onAttachEvidence}
          onOpenFullViewer={onOpenFullViewer}
        />
      </div>
    </div>
  );
}
