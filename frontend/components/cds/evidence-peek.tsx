"use client";

import { useEffect, useState } from "react";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import { getPageThumbnailUrl } from "@/lib/api";

export type EvidenceRef = {
  document_id?: string | null;
  page_number?: number | null;
  note?: string | null;
  snippet?: string | null;
};

type EvidencePeekProps = {
  open: boolean;
  onClose: () => void;
  title: string;
  severity?: string;
  refs: EvidenceRef[];
};

export function EvidencePeek({ open, onClose, title, severity, refs }: EvidencePeekProps) {
  const primary = refs[0];
  const [thumbnail, setThumbnail] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setThumbnail(null);
    if (!open || !primary?.document_id || !primary.page_number) {
      return;
    }
    void getPageThumbnailUrl(primary.document_id, primary.page_number)
      .then((result) => {
        if (!cancelled) {
          setThumbnail(result.url);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setThumbnail(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [open, primary?.document_id, primary?.page_number]);

  useEffect(() => {
    if (!open) {
      return;
    }
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  return (
    <div className="cds-evidence-peek fixed inset-y-0 right-0 z-40 flex w-[min(52vw,720px)] border-l border-border bg-background">
      <ResizablePanelGroup orientation="horizontal" className="h-full">
        <ResizablePanel defaultSize="42%" minSize="28%">
          <div className="flex h-full flex-col p-6">
            <p className="cds-meta">{severity ?? "Finding"}</p>
            <h2 className="mt-3 text-xl font-medium tracking-[-0.03em] text-foreground">{title}</h2>
            <p className="mt-6 cds-meta">Evidence {String(refs.length).padStart(2, "0")} refs</p>
            <ul className="mt-3 space-y-2 text-sm">
              {refs.length === 0 ? (
                <li className="text-muted-foreground">No evidence attached.</li>
              ) : (
                refs.map((ref, index) => (
                  <li key={`${ref.document_id}-${index}`} className="text-foreground">
                    {ref.document_id?.slice(0, 8) ?? "Document"}
                    {ref.page_number ? ` · p${ref.page_number}` : ""}
                    {ref.note ? ` · ${ref.note}` : ""}
                  </li>
                ))
              )}
            </ul>
            {primary?.snippet ? (
              <blockquote className="mt-6 border-l border-primary pl-3 text-sm text-muted-foreground">
                {primary.snippet}
              </blockquote>
            ) : null}
            <button
              type="button"
              className="cds-hit-target mt-auto self-start text-sm text-muted-foreground transition-colors duration-[180ms] hover:text-foreground"
              onClick={onClose}
            >
              Close
            </button>
          </div>
        </ResizablePanel>
        <ResizableHandle />
        <ResizablePanel defaultSize="58%" minSize="36%">
          <div className="flex h-full items-center justify-center bg-secondary p-4">
            {thumbnail ? (
              <img
                src={thumbnail}
                alt={`Evidence page ${primary?.page_number ?? ''} preview`}
                className="max-h-full max-w-full object-contain"
              />
            ) : (
              <p className="text-sm text-muted-foreground">No page image for this reference.</p>
            )}
          </div>
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  );
}
