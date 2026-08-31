"use client";

import { useEffect, useMemo, useState } from "react";
import { DossierFieldsEditor } from "@/components/case/DossierFieldsEditor";
import { FindingsList } from "@/components/workbench/findings-list";
import { CdsPill, severityTone } from "@/components/ui/cds-pill";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ApprovalRequest, CaseReadiness } from "@/lib/api";
import { FindingRow, pendingWaiverExceptionIds, canonicalDocType } from "@/lib/workbench/findings";
import { acknowledgementsComplete, canSelfApprove, submitBlocker, submitEnabled } from "@/lib/workbench/submit-gate";

type WorkMode = "findings" | "dossier" | "decide";

export type WorkbenchExport = {
  id: string;
  filename: string;
  status: string;
  export_type: string;
};

type WorkPaneProps = {
  caseId: string;
  documents: any[];
  findings: FindingRow[];
  selectedFindingId: string | null;
  focusField: string | null;
  openEditor?: boolean;
  initialMode?: WorkMode;
  pendingWaiverIds?: Iterable<string>;
  nextAction?: string | null;
  onSelectFinding: (item: FindingRow) => void;
  onResolve: (item: FindingRow, reason: string, closingEvidenceRefIds: string[]) => void;
  onWaive: (item: FindingRow, reason: string) => void;
  onSatisfyCp: (item: FindingRow) => void;
  onJumpToEvidence: (documentId: string, page?: number) => void;
  onRequestDocument?: () => void;
  onAttachEvidence?: () => void;
  onOpenEvidence?: () => void;
  readiness: CaseReadiness | null;
  controlsBlocked: string[];
  decision: string | null;
  status: string;
  pendingApprovals: ApprovalRequest[];
  exports?: WorkbenchExport[];
  currentUserId: string | null;
  role: string | null;
  onSubmit: () => void;
  onApprove: (request: ApprovalRequest) => void;
  onReject: (request: ApprovalRequest) => void;
  onDraftPack: () => void;
  onIssuePack: () => void;
  onDownloadExport?: (exportId: string) => void;
  busy?: boolean;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
  showDecisionDock?: boolean;
};

function compareCards(item: FindingRow, documents: any[]) {
  const refs = item.evidence_refs?.filter((entry) => entry.document_id || entry.note) ?? [];
  if (refs.length > 0) {
    return refs.slice(0, 2).map((ref) => {
      const doc = documents.find((entry) => entry.id === ref.document_id);
      const type = doc ? canonicalDocType(doc) : null;
      return {
        label: `${(type || "Evidence").toUpperCase()}${ref.page_number ? ` · P.${ref.page_number}` : ""}`,
        value: ref.note || (ref.page_number ? `Page ${ref.page_number}` : "Linked evidence"),
        documentId: ref.document_id,
        page: ref.page_number ?? undefined,
      };
    });
  }
  if (item.source_document_id) {
    const doc = documents.find((entry) => entry.id === item.source_document_id);
    return [
      {
        label: `${(canonicalDocType(doc ?? {}) || "Source").toUpperCase()}${item.source_page ? ` · P.${item.source_page}` : ""}`,
        value: item.description || item.title,
        documentId: item.source_document_id,
        page: item.source_page ?? undefined,
      },
    ];
  }
  return [];
}

export function WorkPane({
  caseId,
  documents,
  findings,
  selectedFindingId,
  focusField,
  openEditor = false,
  initialMode,
  pendingWaiverIds,
  nextAction,
  onSelectFinding,
  onResolve,
  onWaive,
  onSatisfyCp,
  onJumpToEvidence,
  onRequestDocument,
  onAttachEvidence,
  onOpenEvidence,
  readiness,
  controlsBlocked,
  decision,
  status,
  pendingApprovals,
  exports = [],
  currentUserId,
  role,
  onSubmit,
  onApprove,
  onReject,
  onDraftPack,
  onIssuePack,
  onDownloadExport,
  busy,
  collapsed,
  onToggleCollapse,
  showDecisionDock = false,
}: WorkPaneProps) {
  const [mode, setMode] = useState<WorkMode>(initialMode ?? (focusField ? "dossier" : "findings"));
  const [acked, setAcked] = useState<string[]>([]);
  const [resolveTarget, setResolveTarget] = useState<FindingRow | null>(null);
  const [resolveReason, setResolveReason] = useState("");

  useEffect(() => {
    if (initialMode) setMode(initialMode);
  }, [initialMode]);

  const gate = {
    ready: Boolean(readiness?.ready),
    blockedReasons: [...(readiness?.reasons ?? []), ...controlsBlocked],
    decision,
  };
  const blocker = submitBlocker(gate);
  const canSubmit = submitEnabled(gate) && status !== "Ready for Approval" && status !== "Approved";
  const waiverIds = pendingWaiverIds ?? pendingWaiverExceptionIds(pendingApprovals);
  const selected = findings.find((item) => item.id === selectedFindingId) ?? findings[0] ?? null;
  const cards = selected ? compareCards(selected, documents) : [];
  const highOpen = findings.filter((item) => item.kind === "exception" && item.severity === "High" && item.status === "Open").length;
  const openCps = findings.filter((item) => item.kind === "cp" && item.status === "Open").length;

  const requiredAcks = useMemo(() => {
    const highs = findings.filter((item) => item.kind === "exception" && item.severity === "High");
    const waived = findings.filter((item) => item.status === "Waived");
    return [...highs, ...waived].map((item) => item.id);
  }, [findings]);

  const waiverRequests = pendingApprovals.filter((item) => item.request_type === "exception_waive");
  const caseDecision = pendingApprovals.find((item) => item.request_type === "case_decision") ?? null;
  const canCheck = role === "Approver" || role === "Admin";

  const canDecideCase =
    Boolean(caseDecision) &&
    canCheck &&
    !canSelfApprove(caseDecision?.requested_by_user_id ?? null, currentUserId) &&
    acknowledgementsComplete(requiredAcks, acked);

  const readinessPct = readiness?.ready
    ? 100
    : Math.max(8, Math.min(90, 100 - highOpen * 22 - openCps * 10));

  if (collapsed) {
    return (
      <button
        type="button"
        className="flex h-full w-full items-start justify-center bg-[hsl(var(--surface))] pt-4"
        onClick={onToggleCollapse}
        aria-label="Expand work pane"
      >
        <span className="cds-meta" style={{ writingMode: "vertical-rl" }}>
          Work
        </span>
      </button>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col bg-[hsl(var(--surface))]">
      {onToggleCollapse ? (
        <div className="flex h-[52px] items-center justify-end border-b border-border px-4 text-[11px]">
          <button type="button" className="cds-meta text-muted-foreground" onClick={onToggleCollapse} aria-label="Close review panel">
            Close
          </button>
        </div>
      ) : null}

      {mode === "findings" ? (
        <div className="min-h-0 flex-1 overflow-y-auto px-[18px] py-4">
          {selected ? (
            <div className="flex flex-col gap-2.5">
              <p className="cds-meta">
                {selected.rule_id ?? (selected.kind === "cp" ? "Approval requirement" : "Issue")}
                {selected.module ? ` · ${selected.module}` : selected.kind === "exception" ? " · Title / Property" : ""}
              </p>
              <div className="flex flex-wrap items-center gap-2">
                <CdsPill tone={severityTone(selected.severity)}>{selected.severity}</CdsPill>
                <CdsPill>{selected.status}</CdsPill>
                {selected.is_hard_stop || selected.severity === "High" ? <CdsPill tone="blocking">Blocking</CdsPill> : null}
              </div>
              <h2 className="text-[18px] font-semibold leading-[26px] text-foreground">{selected.title}</h2>
              {selected.description ? (
                <p className="text-[12px] leading-[17px] text-muted-foreground">{selected.description}</p>
              ) : null}
              {cards.length > 0 ? (
                <>
                  <div className="mt-1 h-px bg-border" />
                  <p className="cds-meta">Compared evidence</p>
                  <div className="grid grid-cols-2 gap-2.5">
                    {cards.map((card, index) => (
                      <button
                        key={`${card.label}-${index}`}
                        type="button"
                        className="rounded border border-border bg-[hsl(var(--pill))] px-2.5 py-2.5 text-left"
                        onClick={() => card.documentId && onJumpToEvidence(card.documentId, card.page)}
                      >
                        <p className="font-display text-[9px] leading-[13px] text-muted-foreground">{card.label}</p>
                        <p className="mt-1 text-[17px] font-semibold leading-[25px] text-foreground">{card.value}</p>
                      </button>
                    ))}
                  </div>
                </>
              ) : null}
              {selected.resolution_conditions ? (
                <>
                  <p className="cds-meta mt-1">Required resolution</p>
                  <p className="text-[12px] font-medium leading-[17px] text-foreground">{selected.resolution_conditions}</p>
                </>
              ) : null}
              {selected.cp_text ? (
                <>
                  <p className="cds-meta">Proposed approval requirement</p>
                  <p className="text-[11px] leading-4 text-muted-foreground">{selected.cp_text}</p>
                </>
              ) : null}
              {selected.status === "Open" ? (
                <div className="mt-1 flex flex-wrap gap-2">
                  <button type="button" className="cds-btn cds-btn-primary" onClick={onRequestDocument} disabled={busy}>
                    Request document
                  </button>
                  <button
                    type="button"
                    className="cds-btn cds-btn-ghost"
                    onClick={onOpenEvidence ?? onAttachEvidence}
                    disabled={busy}
                  >
                    Link source page as proof
                  </button>
                  {selected.kind === "exception" ? (
                    <button type="button" className="cds-btn cds-btn-ghost" onClick={() => { setResolveTarget(selected); setResolveReason(""); }} disabled={busy}>
                      Mark issue resolved
                    </button>
                  ) : (
                    <button type="button" className="cds-btn cds-btn-ghost" onClick={() => onSatisfyCp(selected)} disabled={busy}>
                      Resolve
                    </button>
                  )}
                </div>
              ) : null}
            </div>
          ) : (
            <p className="text-[12px] text-muted-foreground">Select a finding from the file pane.</p>
          )}
        </div>
      ) : null}

      {mode === "dossier" ? (
        <div className="min-h-0 flex-1 overflow-y-auto p-3">
          <DossierFieldsEditor
            caseId={caseId}
            documents={documents}
            focusField={focusField}
            openEditor={openEditor}
            oneAtATime
            onJumpToEvidence={onJumpToEvidence}
          />
        </div>
      ) : null}

      {mode === "decide" ? (
        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4 text-sm">
          <FindingsList
            items={findings}
            filter="all"
            selectedId={selectedFindingId}
            pendingWaiverIds={waiverIds}
            onSelect={onSelectFinding}
            onResolve={(item) => { setResolveTarget(item); setResolveReason(""); }}
            onWaive={onWaive}
            onSatisfyCp={onSatisfyCp}
            onJumpToEvidence={onJumpToEvidence}
          />

          {waiverRequests.map((request) => {
            const exceptionId = String(request.payload_json?.exception_id ?? "");
            const finding = findings.find((item) => item.id === exceptionId);
            const selfMade = canSelfApprove(request.requested_by_user_id, currentUserId);
            return (
              <div key={request.id} className="space-y-2 border-t border-border pt-4">
                <p className="cds-meta">Waiver request</p>
                <p>
                  {finding?.rule_id ? `${finding.rule_id} — ` : ""}
                  {finding?.title ?? exceptionId}
                </p>
                {request.payload_json?.waiver_reason ? (
                  <p className="text-muted-foreground">{String(request.payload_json.waiver_reason)}</p>
                ) : null}
                {selfMade ? (
                  <p>You proposed this waiver. Another person must decide it.</p>
                ) : (
                  <div className="flex gap-2">
                    <Button type="button" size="compact" disabled={!canCheck || busy} onClick={() => onApprove(request)}>
                      Approve waiver
                    </Button>
                    <Button type="button" size="compact" variant="outline" disabled={!canCheck || busy} onClick={() => onReject(request)}>
                      Reject
                    </Button>
                  </div>
                )}
              </div>
            );
          })}

          {caseDecision ? (
            <div className="space-y-2 border-t border-border pt-4">
              <p className="cds-meta">Case decision</p>
              {canSelfApprove(caseDecision.requested_by_user_id, currentUserId) ? (
                <p>You submitted this request. Another person must decide it.</p>
              ) : (
                requiredAcks.map((id) => {
                  const row = findings.find((item) => item.id === id);
                  return (
                    <label key={id} className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={acked.includes(id)}
                        onChange={(event) => {
                          setAcked((prev) =>
                            event.target.checked ? [...prev, id] : prev.filter((value) => value !== id)
                          );
                        }}
                      />
                      {row?.status === "Waived" ? "WAIVE" : "EX"} reviewed · {row?.title ?? id}
                    </label>
                  );
                })
              )}
              <div className="flex gap-2">
                <Button type="button" size="compact" disabled={!canDecideCase || busy} onClick={() => onApprove(caseDecision)}>
                  Approve
                </Button>
                <Button
                  type="button"
                  size="compact"
                  variant="outline"
                  disabled={canSelfApprove(caseDecision.requested_by_user_id, currentUserId) || busy}
                  onClick={() => onReject(caseDecision)}
                >
                  Reject
                </Button>
              </div>
            </div>
          ) : null}

          <div className="border-t border-border pt-4">
            {status === "Approved" ? (
              <>
                <p className="cds-meta">Issue Bank Pack</p>
                <p className="mb-2 text-muted-foreground">Versioned artefact. Treat issued packs as immutable.</p>
                <Button type="button" size="compact" disabled={busy} onClick={onIssuePack}>
                  Issue Bank Pack
                </Button>
              </>
            ) : decision === "FAIL" ? (
              <>
                <p className="cds-meta">FAIL review pack — not a clearance</p>
                <Button type="button" size="compact" variant="outline" disabled={busy} onClick={onDraftPack}>
                  Generate FAIL review pack
                </Button>
              </>
            ) : (
              <>
                <p className="cds-meta">Draft pack preview — not approved</p>
                <Button type="button" size="compact" variant="outline" disabled={busy} onClick={onDraftPack}>
                  Preview draft pack
                </Button>
              </>
            )}
            {exports.length > 0 ? (
              <ul className="mt-3 space-y-2">
                {exports.map((item) => (
                  <li key={item.id} className="flex items-center justify-between gap-2 text-xs">
                    <span className="min-w-0 truncate">
                      {item.filename} · {item.status}
                    </span>
                    {item.status === "succeeded" || item.status === "complete" ? (
                      <Button type="button" size="compact" variant="ghost" disabled={busy} onClick={() => onDownloadExport?.(item.id)}>
                        Download
                      </Button>
                    ) : (
                      <span className="text-muted-foreground">{item.status}</span>
                    )}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        </div>
      ) : null}

      {showDecisionDock ? (
        <div className="shrink-0 border-t border-border bg-[hsl(var(--header))] px-[18px] py-4">
          <p className="cds-meta">Ready to submit?</p>
          <p className="mt-2 text-[16px] font-semibold leading-[23px] text-foreground">
            {readiness?.ready ? "Ready for approval" : "Not ready for approval"}
          </p>
          <p className="mt-1.5 text-[11px] leading-4 text-muted-foreground">
            {highOpen} high-priority issues · {openCps} approval requirements open
          </p>
          <div className="relative mt-2.5 h-1.5 w-full rounded-[3px] bg-border">
            <div
              className="absolute inset-y-0 left-0 rounded-[3px] bg-[hsl(var(--crimson-border))]"
              style={{ width: `${readinessPct}%` }}
            />
          </div>
          {nextAction ? (
            <p className="mt-2 font-display text-[11px] text-foreground">
              NEXT  {nextAction}
            </p>
          ) : null}
          <button type="button" className="cds-btn cds-btn-primary mt-2" disabled={!canSubmit || busy} onClick={onSubmit}>
            Submit for approval
          </button>
          <p className="mt-2 text-[10px] leading-[15px] text-muted-foreground">
            {blocker || "Submission unlocks when CDS computes readiness."}
          </p>
        </div>
      ) : null}
      <Dialog open={Boolean(resolveTarget)} onOpenChange={(open) => !open && setResolveTarget(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>Resolve exception</DialogTitle><DialogDescription>Rationale and a linked source page marked as closing proof are required.</DialogDescription></DialogHeader>
          <Textarea value={resolveReason} onChange={(event) => setResolveReason(event.target.value)} placeholder="Why is this issue resolved?" />
          <p className="text-xs text-muted-foreground">Closing proof: {resolveTarget?.evidence_refs?.filter((ref) => ref.is_closing || ref.isClosing).length ?? 0} linked page(s)</p>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setResolveTarget(null)}>Cancel</Button>
            <Button type="button" disabled={busy || !resolveReason.trim() || !(resolveTarget?.evidence_refs ?? []).some((ref) => ref.is_closing || ref.isClosing)} onClick={() => {
              if (!resolveTarget) return;
              const refs = (resolveTarget.evidence_refs ?? []).filter((ref) => ref.is_closing || ref.isClosing).map((ref) => ref.id).filter((id): id is string => Boolean(id));
              onResolve(resolveTarget, resolveReason.trim(), refs);
              setResolveTarget(null);
            }}>Resolve</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
