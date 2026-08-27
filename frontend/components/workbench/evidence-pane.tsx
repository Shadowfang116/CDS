"use client";

import { useState } from "react";
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
  if (value === "complete" || value === "done") return "Text extracted";
  if (value === "needs_review") return "Review required";
  if (value === "failed") return "Text extraction failed";
  if (value === "uploaded") return "Uploaded";
  return status || "OCR";
}

function ocrReviewNotice(status?: string | null, confidence?: number | null): string | null {
  const value = (status ?? "").replace(/\s+/g, "_").toLowerCase();
  if (value === "failed") return "Text extraction failed. Use the source page and request a replacement or manual review.";
  if (value === "needs_review" || (confidence !== null && confidence !== undefined && confidence < 80)) {
    return "This text is provisional. Compare it with the source page before relying on it.";
  }
  return null;
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
  const [evidenceMode, setEvidenceMode] = useState<"source" | "text" | "split">("source");
  const selected = documents.find((item) => item.id === selectedDocId) ?? documents[0] ?? null;
  const typeLabel = selected ? canonicalDocType(selected) : null;
  const pageCount = selected?.page_count || 0;
  const page = selectedPage || 1;
  const confidence =
    typeof selected?.classification_confidence === "number"
      ? Math.round(Number(selected.classification_confidence) * (selected.classification_confidence <= 1 ? 100 : 1))
      : null;
  const highlight = selectedFinding?.evidence_refs?.find((entry) => entry.note)?.note ?? selectedFinding?.title ?? null;
  const reviewNotice = ocrReviewNotice(selected?.status, confidence);

  return (
    <div className="flex h-full min-h-0 flex-col bg-background">
      <div className="flex shrink-0 flex-col gap-2 border-b border-border bg-[hsl(var(--surface))] px-4 pb-3 pt-3.5">
        <p className="cds-meta">Evidence and source page</p>
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
              <div className="flex items-center gap-1 rounded border border-border p-0.5" role="tablist" aria-label="Evidence view">
                {([['source', 'Source page'], ['text', 'Extracted text'], ['split', 'Side by side']] as const).map(([mode, label]) => (
                  <button key={mode} type="button" role="tab" aria-selected={evidenceMode === mode} onClick={() => setEvidenceMode(mode)} className={evidenceMode === mode ? "bg-foreground px-2 py-1 text-[10px] font-semibold text-background" : "px-2 py-1 text-[10px] text-muted-foreground hover:bg-[hsl(var(--pill))]"}>{label}</button>
                ))}
              </div>
              <button
                type="button"
                className="cds-btn cds-btn-ghost"
                onClick={() => onAttachEvidence(selected.id, page)}
              >
                Link this page as proof
              </button>
              <button type="button" className="cds-btn cds-btn-primary" onClick={onOpenFullViewer}>
                Open full viewer
              </button>
            </div>
            {reviewNotice ? (
              <p className="text-[11px] leading-4 text-[hsl(var(--status-medium))]" role="status">
                {reviewNotice}
              </p>
            ) : null}
          </>
        ) : (
          <p className="text-[12px] text-muted-foreground">Upload a document to inspect its source page.</p>
        )}
      </div>
      <div className="min-h-0 flex-1">
        <DocumentViewer
          key={`${selectedDocId ?? "none"}:${selectedPage ?? 1}`}
          caseId={caseId}
          documents={documents}
          initialDocId={selectedDocId}
          initialPage={selectedPage}
          variant="workbench"
          evidenceMode={evidenceMode}
          showHighlightPanel={false}
          highlightLabel={selectedFinding?.rule_id ? selectedFinding.title : highlight}
          highlightValue={highlight}
          onAttachEvidence={onAttachEvidence}
          onOpenFullViewer={onOpenFullViewer}
        />
      </div>
    </div>
  );
}
