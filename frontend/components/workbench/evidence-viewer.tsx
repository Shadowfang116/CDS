"use client";

import { useMemo, useState } from "react";
import { DocumentViewer } from "@/components/documents/DocumentViewer";
import { CdsPill, severityTone } from "@/components/ui/cds-pill";
import { CaseDocumentItem, DossierFieldItem } from "@/lib/api";
import { FindingRow, canonicalDocType } from "@/lib/workbench/findings";
import { urduTextProps } from "@/lib/text-script";

type EvidenceViewerProps = {
  caseId: string;
  matterTitle: string;
  status: string;
  documents: CaseDocumentItem[];
  fields: DossierFieldItem[];
  selectedFinding: FindingRow | null;
  selectedDocId?: string;
  selectedPage?: number;
  onBack: () => void;
  onAttachEvidence: (documentId: string, pageNumber: number) => void;
  onResolve?: (item: FindingRow) => void;
  onRequestDocument?: () => void;
};

type IntelligenceTab = "finding" | "facts" | "document";

export function EvidenceViewer({
  caseId,
  matterTitle,
  status,
  documents,
  fields,
  selectedFinding,
  selectedDocId,
  selectedPage,
  onBack,
  onAttachEvidence,
  onResolve,
  onRequestDocument,
}: EvidenceViewerProps) {
  const [tab, setTab] = useState<IntelligenceTab>("finding");
  const selected = documents.find((item) => item.id === selectedDocId) ?? documents[0] ?? null;
  const typeLabel = selected ? canonicalDocType(selected) : null;
  const confidence =
    typeof selected?.classification_confidence === "number"
      ? Math.round(Number(selected.classification_confidence) * (selected.classification_confidence <= 1 ? 100 : 1))
      : null;
  const related = useMemo(() => fields.slice(0, 4), [fields]);
  const compare = selectedFinding?.evidence_refs?.filter((entry) => entry.note || entry.document_id).slice(0, 2) ?? [];
  const highlight = selectedFinding?.evidence_refs?.find((entry) => entry.note)?.note ?? selectedFinding?.title ?? null;

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-background">
      <div className="flex h-[60px] shrink-0 items-center justify-between border-b border-border bg-[hsl(var(--header))] px-5">
        <div className="flex items-center gap-3.5">
          <p className="font-display text-[12px] font-medium tracking-[0.08em] text-foreground">CDS</p>
          <button type="button" className="text-[11px] font-medium text-muted-foreground" onClick={onBack}>
            ← Matter
          </button>
          <span className="h-[22px] w-px bg-border" />
          <p className="text-[12px] font-semibold text-foreground">{matterTitle}</p>
          <CdsPill>{status}</CdsPill>
        </div>
        <div className="flex items-center gap-2">
          {selectedFinding?.rule_id ? <CdsPill tone="high">{selectedFinding.rule_id}</CdsPill> : null}
          <button type="button" className="cds-btn cds-btn-ghost" onClick={onBack}>
            Back to finding
          </button>
        </div>
      </div>

      <div className="flex h-[92px] shrink-0 items-start justify-between border-b border-border bg-[hsl(var(--surface))] px-[18px] py-3.5">
        <div className="flex min-w-0 flex-col gap-1">
          <p className="cds-meta">Evidence document</p>
          <p className="truncate text-[17px] font-semibold leading-[25px] text-foreground">
            {selected?.original_filename ?? "No document selected"}
          </p>
          <div className="flex flex-wrap items-center gap-2">
            {typeLabel ? <CdsPill>{typeLabel}</CdsPill> : null}
            {selected ? (
              <CdsPill tone={(selected.status ?? "").toLowerCase().includes("fail") ? "missing" : "good"}>
                {(selected.status ?? "").toLowerCase() === "complete" || (selected.status ?? "").toLowerCase() === "done"
                  ? "OCR good"
                  : selected.status || "OCR"}
              </CdsPill>
            ) : null}
            {confidence !== null ? <CdsPill tone="good">Conf {confidence}%</CdsPill> : null}
          </div>
        </div>
        <div className="flex items-center gap-2 self-center">
          {selected ? (
            <button
              type="button"
              className="cds-btn cds-btn-primary"
              onClick={() => onAttachEvidence(selected.id, selectedPage || 1)}
            >
              Attach evidence
            </button>
          ) : null}
        </div>
      </div>

      <div className="flex min-h-0 flex-1">
        <div className="min-h-0 min-w-0 flex-1">
          <DocumentViewer
            caseId={caseId}
            documents={documents}
            initialDocId={selectedDocId}
            initialPage={selectedPage}
            variant="evidence"
            highlightLabel={selectedFinding?.title ?? null}
            highlightValue={highlight}
            onAttachEvidence={onAttachEvidence}
          />
        </div>
        <aside className="flex w-[568px] shrink-0 flex-col border-l border-border bg-[hsl(var(--surface))]">
          <div className="flex h-[52px] items-center gap-[22px] border-b border-border px-[18px] text-[11px]">
            {(["finding", "facts", "document"] as const).map((item) => (
              <button
                key={item}
                type="button"
                className={tab === item ? "font-semibold text-foreground" : "font-medium text-muted-foreground"}
                onClick={() => setTab(item)}
              >
                {item === "finding" ? "Finding" : item === "facts" ? "Facts" : "Document"}
              </button>
            ))}
          </div>

          {tab === "finding" && selectedFinding ? (
            <div className="min-h-0 flex-1 overflow-y-auto px-5 py-[18px]">
              <p className="cds-meta">
                {selectedFinding.rule_id ?? "Finding"}
                {selectedFinding.is_hard_stop || selectedFinding.severity === "High" ? " · Blocking" : ""}
              </p>
              <div className="mt-2.5 flex gap-2">
                <CdsPill tone={severityTone(selectedFinding.severity)}>{selectedFinding.severity}</CdsPill>
                <CdsPill>{selectedFinding.status}</CdsPill>
              </div>
              <h2 className="mt-2.5 text-[19px] font-semibold leading-7 text-foreground">{selectedFinding.title}</h2>
              {selectedFinding.description ? (
                <p className="mt-2 text-[12px] leading-[17px] text-muted-foreground">{selectedFinding.description}</p>
              ) : null}
              {compare.length > 0 ? (
                <>
                  <p className="cds-meta mt-4">Evidence comparison</p>
                  <div className="mt-2.5 flex flex-col gap-1.5">
                    {compare.map((entry, index) => {
                      const doc = documents.find((item) => item.id === entry.document_id);
                      return (
                        <div key={`${entry.document_id}-${index}`} className="flex items-center justify-between rounded border border-border bg-[hsl(var(--pill))] px-2.5 py-2">
                          <p className="w-[250px] font-display text-[9px] text-muted-foreground">
                            {(canonicalDocType(doc ?? {}) || "Evidence").toUpperCase()}
                            {entry.page_number ? ` · PAGE ${entry.page_number}` : ""}
                          </p>
                          <p className="text-[14px] font-semibold text-foreground">{entry.note || "Linked"}</p>
                        </div>
                      );
                    })}
                  </div>
                </>
              ) : null}
              {selectedFinding.status === "Open" ? (
                <div className="mt-4 flex gap-2">
                  <button type="button" className="cds-btn cds-btn-primary" onClick={onRequestDocument}>
                    Request corrected Fard
                  </button>
                  <button type="button" className="cds-btn cds-btn-ghost" onClick={() => onResolve?.(selectedFinding)}>
                    Resolve
                  </button>
                </div>
              ) : null}
            </div>
          ) : null}

          {tab === "facts" || (tab === "finding" && selectedFinding) ? (
            <div className="border-t border-border px-5 py-4">
              <p className="cds-meta">Related facts</p>
              <div className="mt-2 space-y-1">
                {related.map((field) => (
                  <div key={field.field_key} className="flex h-10 items-center gap-2">
                    <p className="w-[170px] truncate font-display text-[10px] text-muted-foreground">{field.field_key}</p>
                    <p className="min-w-0 flex-1 truncate text-[11px] font-medium text-foreground" {...urduTextProps(field.field_value)}>
                      {field.field_value || "—"}
                    </p>
                    <CdsPill tone={field.needs_confirmation ? "proposed" : "confirmed"}>
                      {field.needs_confirmation ? "Proposed" : "Confirmed"}
                    </CdsPill>
                  </div>
                ))}
                {related.length === 0 ? <p className="text-[11px] text-muted-foreground">No related facts yet.</p> : null}
              </div>
            </div>
          ) : null}

          <div className="mt-auto border-t border-border bg-[hsl(var(--header))] px-5 py-4">
            <p className="cds-meta">Document record</p>
            <p className="mt-1.5 text-[11px] font-medium text-foreground">Type: {typeLabel || "Unclassified"}</p>
            <p className="mt-1.5 text-[11px] text-muted-foreground">OCR: {selected?.status || "Pending"}{confidence !== null ? ` · confidence ${confidence}%` : ""}</p>
            <p className="mt-1.5 text-[11px] text-muted-foreground">Evidence ID: {selected?.id ?? "—"}</p>
            {selected?.created_at ? (
              <p className="mt-1.5 text-[11px] text-muted-foreground">
                Uploaded {new Date(selected.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })} · original immutable
              </p>
            ) : null}
          </div>
        </aside>
      </div>
    </div>
  );
}
