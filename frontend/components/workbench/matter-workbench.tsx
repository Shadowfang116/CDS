"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { DecisionStrip } from "@/components/workbench/decision-strip";
import { EvidencePane } from "@/components/workbench/evidence-pane";
import { EvidenceViewer } from "@/components/workbench/evidence-viewer";
import { FilePane } from "@/components/workbench/file-pane";
import { MatterReviewQueue } from "@/components/workbench/matter-review-queue";
import { WorkPane, WorkbenchExport } from "@/components/workbench/work-pane";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { useToast } from "@/components/ui/toast";
import { getCaseWorkbenchPath } from "@/lib/routes";
import { getFieldLabelMeta } from "@/lib/field-labels";
import { WorkflowStepper, workflowStepForMatter, type WorkflowStepId } from "@/components/workbench/workflow-stepper";
import { clientNextAction } from "@/lib/workbench/next-action";
import {
  matterBorrower,
  matterFacility,
  matterRegime,
  openCpCount,
  openHardStopCount,
  openHighCount,
  primaryBlocker,
  readinessLabel,
} from "@/lib/workbench/matter-header";
import {
  FindingRow,
  firstEvidenceRef,
  groupFindings,
  isKycNoiseLabel,
  pendingWaiverExceptionIds,
  toCpFinding,
  toExceptionFinding,
} from "@/lib/workbench/findings";
import {
  approveRequest,
  generateBankPack,
  generateDiscrepancyLetter,
  getCaseWorkbench,
  getExportDownloadUrl,
  listDocuments,
  listExports,
  rejectRequest,
  resolveException,
  updateCP,
  uploadDocument,
  workbenchEvaluate,
  workbenchExtract,
  workbenchRequestWaiver,
  workbenchSubmit,
  ApprovalRequest,
  CaseDocumentItem,
  CaseReadiness,
} from "@/lib/api";

type MatterWorkbenchProps = {
  caseId: string;
};

export function MatterWorkbench({ caseId }: MatterWorkbenchProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const user = useCurrentUser();
  const { toast } = useToast();

  const findingId = searchParams.get("finding");
  const fieldKey = searchParams.get("field");
  const editField = searchParams.get("edit");
  const docId = searchParams.get("doc");
  const page = searchParams.get("page") ? Number(searchParams.get("page")) : undefined;
  const view = searchParams.get("view");
  const requestedSurface = searchParams.get("surface") ?? "documents";
  const surface = requestedSurface === "files" || requestedSurface === "evidence"
    ? "documents"
    : requestedSurface === "issues" || requestedSurface === "facts"
      ? "review"
      : requestedSurface === "decision"
        ? "decision"
        : requestedSurface;
  const panelOpen = searchParams.get("panel") === "inspector" || searchParams.get("work") === "1" || Boolean(editField);

  const [matter, setMatter] = useState<any>(null);
  const [documents, setDocuments] = useState<CaseDocumentItem[]>([]);
  const [findingsState, setFindingsState] = useState<FindingRow[]>([]);
  const [readiness, setReadiness] = useState<CaseReadiness | null>(null);
  const [blockedReasons, setBlockedReasons] = useState<string[]>([]);
  const [pendingApprovals, setPendingApprovals] = useState<ApprovalRequest[]>([]);
  const [exports, setExports] = useState<WorkbenchExport[]>([]);
  const [fields, setFields] = useState<any[]>([]);
  const [verifications, setVerifications] = useState<any[]>([]);
  const [serverNextAction, setServerNextAction] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [matterRailCollapsed, setMatterRailCollapsed] = useState(false);

  const setQuery = useCallback(
    (next: Record<string, string | number | undefined | null>) => {
      router.replace(getCaseWorkbenchPath(caseId, { finding: findingId, field: fieldKey, edit: editField, doc: docId, page, view, work: panelOpen ? "1" : null, panel: panelOpen ? "inspector" : null, surface, ...next }));
    },
    [caseId, docId, editField, fieldKey, findingId, page, panelOpen, router, surface, view]
  );

  const load = useCallback(async () => {
    const data = await getCaseWorkbench(caseId);
    setMatter(data.matter);
    setDocuments(Array.isArray(data.documents) ? data.documents : []);
    setFindingsState(Array.isArray(data.findings) ? data.findings : []);
    const ready = data.readiness
      ? {
          case_id: data.readiness.case_id ?? caseId,
          ready: Boolean(data.readiness.ready),
          reasons: data.readiness.reasons ?? [],
          metrics: data.readiness.metrics ?? {
            open_high_exceptions: 0,
            pending_verifications: 0,
            cp_completion_pct: 0,
            cp_threshold_pct: 80,
          },
        }
      : null;
    setReadiness(ready);
    setBlockedReasons(ready?.ready ? [] : ready?.reasons ?? []);
    setPendingApprovals(Array.isArray(data.pending_approvals) ? data.pending_approvals : []);
    setFields(Array.isArray(data.fields) ? data.fields : []);
    setVerifications(Array.isArray(data.verifications) ? data.verifications : []);
    setServerNextAction(typeof data.next_action === "string" ? data.next_action : null);
    setExports(
      (data.exports ?? []).map((item: any) => ({
        id: item.id,
        filename: item.filename,
        status: item.status,
        export_type: item.export_type,
      }))
    );
  }, [caseId]);

  useEffect(() => {
    void load().catch((error) => {
      toast({ title: "Matter failed to load", description: error instanceof Error ? error.message : "Error", variant: "error" });
    });
  }, [load, toast]);

  useEffect(() => {
    const pending = documents.some((doc) => {
      const status = (doc.status ?? "").toLowerCase();
      return status && !["complete", "needs_review", "failed", "uploaded"].includes(status.replace(/\s+/g, "_"));
    });
    if (!pending) return;
    const timer = window.setInterval(() => {
      void listDocuments(caseId).then((docs) => setDocuments(Array.isArray(docs) ? docs : []));
    }, 4000);
    return () => window.clearInterval(timer);
  }, [caseId, documents]);

  useEffect(() => {
    const pendingPack = exports.some((item) => ["pending", "running"].includes((item.status ?? "").toLowerCase()));
    if (!pendingPack) return;
    const timer = window.setInterval(() => {
      void listExports(caseId).then((exportList) => {
        setExports(
          (exportList?.exports ?? []).map((item: any) => ({
            id: item.id,
            filename: item.filename,
            status: item.status,
            export_type: item.export_type,
          }))
        );
      });
    }, 4000);
    return () => window.clearInterval(timer);
  }, [caseId, exports]);

  const findings: FindingRow[] = useMemo(() => {
    const exceptions = findingsState.filter((item) => item.kind !== "cp").map(toExceptionFinding);
    const cps = findingsState.filter((item) => item.kind === "cp").map(toCpFinding);
    return groupFindings(exceptions, cps);
  }, [findingsState]);

  const selectedFinding = findingId ? findings.find((item) => item.id === findingId) ?? null : null;
  const waiverIds = useMemo(() => pendingWaiverExceptionIds(pendingApprovals), [pendingApprovals]);

  const nextAction = useMemo(() => {
    const hard = findings.find((item) => item.is_hard_stop && item.status === "Open");
    const high = findings.find((item) => item.kind === "exception" && item.severity === "High" && item.status === "Open");
    const cp = findings.find((item) => item.kind === "cp" && item.status === "Open");
    const medium = findings.find((item) => item.severity === "Medium" && item.status === "Open");
    const low = findings.find((item) => item.severity === "Low" && item.status === "Open");
    const unconfirmed = fields.find((item) => item.needs_confirmation);
    const pendingVer = verifications.find((item) => item.status === "Pending");
    const missingLegal = high && !isKycNoiseLabel(`${high.title} ${high.rule_id ?? ""}`)
      ? high.resolution_conditions
      : null;
    const computedNextAction = clientNextAction({
      hardStopTitle: hard?.title,
      missingRequiredCausingHigh: missingLegal ?? null,
      unconfirmedKeyField: unconfirmed ? getFieldLabelMeta(unconfirmed.field_key).label : null,
      openHighTitle: high?.title,
      blockingCpText: cp?.title,
      pendingVerification: pendingVer?.verification_type ?? pendingVer?.type,
      openMediumTitle: medium?.title,
      openLowTitle: low?.title,
      status: matter?.status,
    });
    const serverSuggestsSubmission = (serverNextAction ?? "").trim().toLowerCase() === "submit for approval";
    if (matter?.status?.trim().toLowerCase() === "new" && serverSuggestsSubmission) return computedNextAction;
    return serverNextAction || computedNextAction;
  }, [fields, findings, matter?.status, serverNextAction, verifications]);

  const selectedEvidence = selectedFinding ? firstEvidenceRef(selectedFinding) : null;
  const evidenceDocId = docId || selectedEvidence?.documentId || documents[0]?.id || undefined;
  const evidencePage = page || selectedEvidence?.page || 1;
  const isProcessing = documents.some((document) => {
    const status = (document.status ?? "").toLowerCase().replace(/\s+/g, "_");
    return ["processing", "queued", "ocr_in_progress", "analyzing", "uploading"].includes(status);
  });
  const activeWorkflow = workflowStepForMatter({
    documentCount: documents.length,
    processing: isProcessing || extracting || evaluating,
    issueCount: findings.filter((item) => item.status === "Open").length,
    unconfirmedCount: fields.filter((item) => item.needs_confirmation).length,
    ready: Boolean(readiness?.ready),
  });

  const run = async (fn: () => Promise<void>, ok: string) => {
    setBusy(true);
    try {
      await fn();
      toast({ title: ok });
      await load();
    } catch (error) {
      toast({ title: "Action failed", description: error instanceof Error ? error.message : "Error", variant: "error" });
    } finally {
      setBusy(false);
    }
  };

  const selectFinding = (item: FindingRow) => {
    const ref = firstEvidenceRef(item);
    setQuery({ finding: item.id, doc: ref?.documentId, page: ref?.page ?? 1, panel: "inspector", work: "1", surface: "review" });
  };

  const selectField = (field: { field_key: string; source_document_id?: string | null; source_page_number?: number | null }) => {
    setQuery({ field: field.field_key, doc: field.source_document_id, page: field.source_page_number, panel: "inspector", work: "1", surface: "review" });
  };

  const requestDocument = (instrument?: string | null) =>
    void run(async () => {
      await generateDiscrepancyLetter(caseId);
    }, instrument ? `Draft discrepancy letter generated — ${instrument}` : "Draft discrepancy letter generated — review before anything leaves CDS");

  if (!matter) {
    return <p className="p-6 text-sm text-muted-foreground">Loading matter…</p>;
  }

  if (view === "evidence") {
    return (
      <EvidenceViewer
        caseId={caseId}
        matterTitle={matter.title}
        status={matter.status}
        documents={documents}
        fields={fields}
        selectedFinding={selectedFinding}
        selectedDocId={evidenceDocId}
        selectedPage={evidencePage}
        onBack={() => setQuery({ view: null })}
        onAttachEvidence={(documentId, pageNumber) => setQuery({ doc: documentId, page: pageNumber, view: "evidence" })}
        onResolve={(item) => void run(async () => { await resolveException(item.id, "Resolved from workbench"); }, "Issue resolved")}
        onRequestDocument={requestDocument}
      />
    );
  }

  const jurisdiction = matterRegime(fields);
  const borrower = matterBorrower(fields);
  const facility = matterFacility(fields);
  const highCount = openHighCount(findings);
  const hardStopCount = openHardStopCount(findings);
  const cpCount = openCpCount(findings);
  const blocker = primaryBlocker(findings, blockedReasons);
  const readyLabel = readinessLabel(readiness?.ready, matter.status);

  const workPane = (
    <WorkPane
      caseId={caseId}
      documents={documents}
      findings={findings}
      selectedFindingId={selectedFinding?.id ?? null}
      focusField={editField}
      initialMode={fieldKey ? "dossier" : surface === "decision" ? "decide" : "findings"}
      openEditor={Boolean(editField)}
      pendingWaiverIds={waiverIds}
      nextAction={nextAction}
      onSelectFinding={selectFinding}
      onResolve={(item) => void run(async () => { await resolveException(item.id, "Resolved from workbench"); }, "Issue resolved")}
      onWaive={(item, reason) => void run(async () => { await workbenchRequestWaiver(caseId, item.id, reason); }, "Waiver requested — another reviewer must decide")}
      onSatisfyCp={(item) => void run(async () => { await updateCP(item.id, "Met"); }, "Approval requirement marked complete")}
      onJumpToEvidence={(documentId, pageNumber) => setQuery({ doc: documentId, page: pageNumber, surface: "evidence" })}
      onRequestDocument={requestDocument}
      onOpenEvidence={() => setQuery({ view: "evidence" })}
      readiness={readiness}
      controlsBlocked={blockedReasons}
      decision={matter.decision ?? null}
      status={matter.status}
      pendingApprovals={pendingApprovals}
      exports={exports}
      showDecisionDock={surface === "decision"}
      currentUserId={user?.id ?? null}
      role={user?.role ?? null}
      busy={busy}
      onSubmit={() => void run(async () => {
        await workbenchEvaluate(caseId).catch(() => undefined);
        await workbenchSubmit(caseId, {
          decision: matter.decision === "FAIL" ? "FAIL" : matter.decision || "CONDITIONAL_PASS",
          rationale: `Submitted from workbench. Next action: ${nextAction}`,
        });
      }, "Submitted for approval")}
      onApprove={(request) => void run(async () => {
        await approveRequest(request.id, request.request_type === "exception_waive" ? "Waiver approved from workbench" : "Acknowledged high findings and waivers");
        if (request.request_type === "exception_waive") await workbenchEvaluate(caseId).catch(() => undefined);
      }, request.request_type === "exception_waive" ? "Waiver approved" : "Approved")}
      onReject={(request) => void run(async () => { await rejectRequest(request.id, "Rejected from workbench"); }, "Request rejected")}
      onDraftPack={() => void run(async () => { await generateBankPack(caseId); }, "Approval pack draft queued")}
      onIssuePack={() => void run(async () => { await generateBankPack(caseId); }, "Bank pack issued")}
      onDownloadExport={(exportId) => void run(async () => {
        const result = await getExportDownloadUrl(exportId);
        if (result?.url) window.open(result.url, "_blank");
        else throw new Error("Approval pack is not ready to download");
      }, "Download opened")}
    />
  );

  return (
    <div className="flex h-[calc(100vh-58px)] min-h-0 flex-col bg-background" data-page="matter" data-surface="operational" data-tour="matter-workspace">
      <DecisionStrip
        title={matter.title}
        status={matter.status}
        decision={matter.decision ?? null}
        highExceptions={highCount}
        hardStops={hardStopCount}
        openCps={cpCount}
        documents={documents.length}
        nextAction={nextAction}
        jurisdiction={jurisdiction}
        borrower={borrower}
        facility={facility}
        blocker={blocker}
        readiness={readyLabel}
      />
      <WorkflowStepper
        active={activeWorkflow}
        onSelect={(step: WorkflowStepId) => {
          if (step === "upload" || step === "analyze") setQuery({ surface: "files", work: null });
          if (step === "review") setQuery({ surface: "evidence", work: null });
          if (step === "issues") setQuery({ surface: "issues", work: "1" });
          if (step === "facts") setQuery({ surface: "facts", work: "1" });
          if (step === "submit") setQuery({ surface: "decision", work: "1" });
        }}
      />
      <div className="relative min-h-0 flex-1">
        <div className="hidden h-full min-h-0 md:flex">
          <aside className={matterRailCollapsed ? "w-12 shrink-0 border-r border-border" : "w-[min(22rem,30vw)] shrink-0 border-r border-border"}>
            {matterRailCollapsed ? (
              <button type="button" className="flex h-full w-full items-start justify-center pt-4 text-xs text-muted-foreground" onClick={() => setMatterRailCollapsed(false)} aria-label="Show Matter workspace rail">
                <span style={{ writingMode: "vertical-rl" }}>Show workspace</span>
              </button>
            ) : (
              <div className="flex h-full min-h-0 flex-col">
                <div className="flex shrink-0 items-center justify-between border-b border-border px-3.5 py-2.5">
                  <p className="cds-meta">Matter workspace</p>
                  <button type="button" className="cds-meta text-muted-foreground" onClick={() => setMatterRailCollapsed(true)} aria-label="Hide Matter workspace rail">Hide</button>
                </div>
                <nav className="grid shrink-0 grid-cols-3 border-b border-border p-1" aria-label="Matter workspace">
                  {([["documents", "Documents"], ["review", "Review"], ["decision", "Decision"]] as const).map(([item, label]) => (
                    <button key={item} type="button" aria-current={surface === item ? "page" : undefined} onClick={() => setQuery({ surface: item, panel: null, work: null })} className={surface === item ? "bg-foreground px-2 py-2 text-xs font-semibold text-background" : "px-2 py-2 text-xs text-muted-foreground hover:bg-[hsl(var(--pill))]"}>{label}</button>
                  ))}
                </nav>
                <div className="min-h-0 flex-1 overflow-hidden">
                  {surface === "documents" ? (
                    <FilePane
                      documents={documents}
                      findings={findings}
                      fields={fields}
                      selectedFindingId={selectedFinding?.id ?? null}
                      onSelectFinding={selectFinding}
                      onOpenDocument={(documentId, pageNumber) => setQuery({ doc: documentId, page: pageNumber, surface: "documents" })}
                      uploading={uploading}
                      extracting={extracting}
                      evaluating={evaluating}
                      busy={busy}
                      requesting={busy}
                      showReviewSummary={false}
                      onUpload={async (files) => {
                        setUploading(true);
                        try {
                          for (const file of Array.from(files)) await uploadDocument(caseId, file);
                          await load();
                        } finally {
                          setUploading(false);
                        }
                      }}
                      onExtract={() => void (async () => {
                        setExtracting(true);
                        try {
                          await workbenchExtract(caseId);
                          setEvaluating(true);
                          await workbenchEvaluate(caseId);
                          toast({ title: "Documents analyzed" });
                          await load();
                        } catch (error) {
                          toast({ title: "Analysis failed", description: error instanceof Error ? error.message : "Error", variant: "error" });
                        } finally {
                          setExtracting(false);
                          setEvaluating(false);
                        }
                      })()}
                      onRequestDocument={requestDocument}
                    />
                  ) : surface === "review" ? (
                    <MatterReviewQueue
                      documents={documents}
                      findings={findings}
                      fields={fields}
                      selectedFindingId={selectedFinding?.id ?? null}
                      selectedFieldKey={fieldKey}
                      onSelectFinding={selectFinding}
                      onSelectField={selectField}
                      onOpenDocument={(documentId, pageNumber) => setQuery({ doc: documentId, page: pageNumber, surface: "documents" })}
                      onRequestDocument={(label) => requestDocument(label)}
                    />
                  ) : (
                    <div className="px-3.5 py-4">
                      <p className="cds-meta">Decision</p>
                      <p className="mt-2 text-sm font-semibold text-foreground">Review readiness and approval</p>
                      <p className="mt-1 text-xs leading-5 text-muted-foreground">The decision workspace is open in the main panel.</p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </aside>
          <main className="min-w-0 flex-1">
            {surface === "decision" ? <div className="h-full overflow-hidden">{workPane}</div> : <EvidencePane caseId={caseId} documents={documents} selectedDocId={evidenceDocId} selectedPage={evidencePage} selectedFinding={selectedFinding} onAttachEvidence={(documentId, pageNumber) => setQuery({ doc: documentId, page: pageNumber, view: "evidence" })} onOpenFullViewer={() => setQuery({ view: "evidence" })} />}
          </main>
        </div>
        <div className="absolute inset-0 flex min-h-0 flex-col md:hidden">
          <nav className="grid shrink-0 grid-cols-3 border-b border-border bg-[hsl(var(--surface))] p-1" role="tablist" aria-label="Matter workspace">
            {([["documents", "Documents"], ["review", "Review"], ["decision", "Decision"]] as const).map(([item, label]) => (
              <button key={item} type="button" role="tab" aria-selected={surface === item} onClick={() => setQuery({ surface: item, panel: null, work: null })} className={surface === item ? "bg-foreground px-2 py-2 text-xs font-semibold text-background" : "px-2 py-2 text-xs text-muted-foreground"}>{label}</button>
            ))}
          </nav>
          <div className="min-h-0 flex-1 overflow-hidden">
            {surface === "documents" && docId ? (
              <div className="flex h-full min-h-0 flex-col">
                <button type="button" className="shrink-0 border-b border-border px-4 py-2 text-left text-xs font-semibold text-foreground" onClick={() => setQuery({ doc: null, page: null })}>← Back to documents</button>
                <div className="min-h-0 flex-1"><EvidencePane caseId={caseId} documents={documents} selectedDocId={evidenceDocId} selectedPage={evidencePage} selectedFinding={selectedFinding} onAttachEvidence={(documentId, pageNumber) => setQuery({ doc: documentId, page: pageNumber, view: "evidence" })} onOpenFullViewer={() => setQuery({ view: "evidence" })} /></div>
              </div>
            ) : surface === "documents" ? (
              <FilePane documents={documents} findings={findings} fields={fields} selectedFindingId={selectedFinding?.id ?? null} onSelectFinding={selectFinding} onOpenDocument={(documentId, pageNumber) => setQuery({ doc: documentId, page: pageNumber, surface: "documents" })} uploading={uploading} extracting={extracting} evaluating={evaluating} busy={busy} requesting={busy} showReviewSummary={false} onUpload={async (files) => { setUploading(true); try { for (const file of Array.from(files)) await uploadDocument(caseId, file); await load(); } finally { setUploading(false); } }} onExtract={() => void (async () => { setExtracting(true); try { await workbenchExtract(caseId); setEvaluating(true); await workbenchEvaluate(caseId); toast({ title: "Documents analyzed" }); await load(); } catch (error) { toast({ title: "Analysis failed", description: error instanceof Error ? error.message : "Error", variant: "error" }); } finally { setExtracting(false); setEvaluating(false); } })()} onRequestDocument={requestDocument} />
            ) : surface === "review" && panelOpen ? (
              <div className="h-full overflow-hidden">{workPane}</div>
            ) : surface === "review" ? (
              <MatterReviewQueue documents={documents} findings={findings} fields={fields} selectedFindingId={selectedFinding?.id ?? null} selectedFieldKey={fieldKey} onSelectFinding={selectFinding} onSelectField={selectField} onOpenDocument={(documentId, pageNumber) => setQuery({ doc: documentId, page: pageNumber, surface: "documents" })} onRequestDocument={(label) => requestDocument(label)} />
            ) : (
              <div className="h-full overflow-hidden">{workPane}</div>
            )}
          </div>
        </div>
        {panelOpen && surface !== "decision" ? (
          <div className="absolute inset-0 z-20 hidden bg-black/35 md:block" onClick={() => setQuery({ panel: null, work: null, edit: null })}>
            <aside className="absolute inset-y-0 right-0 w-[min(28rem,92%)] border-l border-border bg-[hsl(var(--surface))] shadow-2xl" onClick={(event) => event.stopPropagation()}>
              <div className="flex h-12 items-center justify-between border-b border-border px-4">
                <p className="text-sm font-semibold text-foreground">Review item</p>
                <button type="button" className="cds-btn cds-btn-ghost" onClick={() => setQuery({ panel: null, work: null, edit: null })}>Close</button>
              </div>
              <div className="h-[calc(100%-3rem)]">{workPane}</div>
            </aside>
          </div>
        ) : null}
      </div>
    </div>
  );
}
