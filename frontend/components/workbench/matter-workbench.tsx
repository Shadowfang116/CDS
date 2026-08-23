"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { usePanelRef } from "react-resizable-panels";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import { DecisionStrip } from "@/components/workbench/decision-strip";
import { EvidencePane } from "@/components/workbench/evidence-pane";
import { EvidenceViewer } from "@/components/workbench/evidence-viewer";
import { FilePane } from "@/components/workbench/file-pane";
import { WorkPane, WorkbenchExport } from "@/components/workbench/work-pane";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { useToast } from "@/components/ui/toast";
import { getCaseWorkbenchPath } from "@/lib/routes";
import { getFieldLabelMeta } from "@/lib/field-labels";
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
  const docId = searchParams.get("doc");
  const page = searchParams.get("page") ? Number(searchParams.get("page")) : undefined;
  const view = searchParams.get("view");

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
  const filePanelRef = usePanelRef();
  const workPanelRef = usePanelRef();
  const [fileCollapsed, setFileCollapsed] = useState(false);
  const [workCollapsed, setWorkCollapsed] = useState(false);

  const setQuery = useCallback(
    (next: Record<string, string | number | undefined | null>) => {
      router.replace(getCaseWorkbenchPath(caseId, { finding: findingId, field: fieldKey, doc: docId, page, view, ...next }));
    },
    [caseId, docId, fieldKey, findingId, page, router, view]
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

  const selectedFinding = findings.find((item) => item.id === findingId) ?? findings[0] ?? null;
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
    return serverNextAction || clientNextAction({
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
  }, [fields, findings, matter?.status, serverNextAction, verifications]);

  const selectedEvidence = selectedFinding ? firstEvidenceRef(selectedFinding) : null;
  const evidenceDocId = docId || selectedEvidence?.documentId || documents[0]?.id || undefined;
  const evidencePage = page || selectedEvidence?.page || 1;

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
    setQuery({ finding: item.id, doc: ref?.documentId, page: ref?.page ?? 1 });
  };

  if (!matter) {
    return <p className="p-6 text-sm text-muted-foreground">Loading matter…</p>;
  }

  const jurisdiction = matterRegime(fields);
  const borrower = matterBorrower(fields);
  const facility = matterFacility(fields);
  const highCount = openHighCount(findings);
  const hardStopCount = openHardStopCount(findings);
  const cpCount = openCpCount(findings);
  const blocker = primaryBlocker(findings, blockedReasons);
  const readyLabel = readinessLabel(readiness?.ready, matter.status);

  const requestDocument = (instrument?: string | null) =>
    void run(async () => {
      await generateDiscrepancyLetter(caseId);
    }, instrument ? `Draft discrepancy letter generated — ${instrument}` : "Draft discrepancy letter generated — review before anything leaves CDS");

  return (
    <div className="flex h-[calc(100vh-58px)] min-h-0 flex-col bg-background" data-page="matter" data-surface="operational">
      {view === "evidence" ? (
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
          onResolve={(item) => void run(async () => { await resolveException(item.id, "Resolved from workbench"); }, "Finding resolved")}
          onRequestDocument={requestDocument}
        />
      ) : null}
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
      <ResizablePanelGroup orientation="horizontal" className="min-h-0 flex-1">
        <ResizablePanel
          id="file"
          panelRef={filePanelRef}
          collapsible
          collapsedSize={4}
          minSize={18}
          defaultSize={23}
          onResize={() => setFileCollapsed(Boolean(filePanelRef.current?.isCollapsed()))}
        >
          <FilePane
            documents={documents}
            findings={findings}
            fields={fields}
            selectedFindingId={selectedFinding?.id ?? null}
            onSelectFinding={selectFinding}
            uploading={uploading}
            extracting={extracting}
            evaluating={evaluating}
            busy={busy}
            requesting={busy}
            collapsed={fileCollapsed}
            onToggleCollapse={() => {
              if (filePanelRef.current?.isCollapsed()) filePanelRef.current.expand();
              else filePanelRef.current?.collapse();
            }}
            onUpload={async (files) => {
              setUploading(true);
              try {
                for (const file of Array.from(files)) {
                  await uploadDocument(caseId, file);
                }
                await load();
              } finally {
                setUploading(false);
              }
            }}
            onExtract={() =>
              void (async () => {
                setExtracting(true);
                try {
                  await workbenchExtract(caseId);
                  setEvaluating(true);
                  await workbenchEvaluate(caseId);
                  toast({ title: "Evidence processed" });
                  await load();
                } catch (error) {
                  toast({ title: "Process failed", description: error instanceof Error ? error.message : "Error", variant: "error" });
                } finally {
                  setExtracting(false);
                  setEvaluating(false);
                }
              })()
            }
            onRequestDocument={requestDocument}
          />
        </ResizablePanel>
        <ResizableHandle />
        <ResizablePanel defaultSize={45} minSize={36} id="evidence">
          <EvidencePane
            caseId={caseId}
            documents={documents}
            selectedDocId={evidenceDocId}
            selectedPage={evidencePage}
            selectedFinding={selectedFinding}
            onAttachEvidence={(documentId, pageNumber) => setQuery({ doc: documentId, page: pageNumber, view: "evidence" })}
            onOpenFullViewer={() => setQuery({ view: "evidence" })}
          />
        </ResizablePanel>
        <ResizableHandle />
        <ResizablePanel
          id="work"
          panelRef={workPanelRef}
          collapsible
          collapsedSize={4}
          minSize={22}
          defaultSize={32}
          onResize={() => setWorkCollapsed(Boolean(workPanelRef.current?.isCollapsed()))}
        >
          <WorkPane
            caseId={caseId}
            documents={documents}
            findings={findings}
            selectedFindingId={selectedFinding?.id ?? null}
            focusField={fieldKey}
            pendingWaiverIds={waiverIds}
            nextAction={nextAction}
            onSelectFinding={selectFinding}
            onResolve={(item) => void run(async () => { await resolveException(item.id, "Resolved from workbench"); }, "Finding resolved")}
            onWaive={(item, reason) =>
              void run(async () => {
                await workbenchRequestWaiver(caseId, item.id, reason);
              }, "Waiver proposed — waiting for checker")
            }
            onSatisfyCp={(item) => void run(async () => { await updateCP(item.id, "Met"); }, "CP marked met")}
            onJumpToEvidence={(documentId, pageNumber) => setQuery({ doc: documentId, page: pageNumber })}
            onRequestDocument={requestDocument}
            onOpenEvidence={() => setQuery({ view: "evidence" })}
            readiness={readiness}
            controlsBlocked={blockedReasons}
            decision={matter.decision ?? null}
            status={matter.status}
            pendingApprovals={pendingApprovals}
            exports={exports}
            currentUserId={user?.id ?? null}
            role={user?.role ?? null}
            busy={busy}
            onSubmit={() =>
              void run(async () => {
                await workbenchEvaluate(caseId).catch(() => undefined);
                await workbenchSubmit(caseId, {
                  decision: matter.decision === "FAIL" ? "FAIL" : matter.decision || "CONDITIONAL_PASS",
                  rationale: `Submitted from workbench. Next action: ${nextAction}`,
                });
              }, "Submitted for approval")
            }
            onApprove={(request) =>
              void run(async () => {
                await approveRequest(
                  request.id,
                  request.request_type === "exception_waive"
                    ? "Waiver approved from workbench"
                    : "Acknowledged high findings and waivers"
                );
                if (request.request_type === "exception_waive") {
                  await workbenchEvaluate(caseId).catch(() => undefined);
                }
              }, request.request_type === "exception_waive" ? "Waiver approved" : "Approved")
            }
            onReject={(request) =>
              void run(async () => {
                await rejectRequest(request.id, "Rejected from workbench");
              }, "Rejected")
            }
            onDraftPack={() => void run(async () => { await generateBankPack(caseId); }, "Draft pack queued")}
            onIssuePack={() => void run(async () => { await generateBankPack(caseId); }, "Bank pack issued")}
            onDownloadExport={(exportId) =>
              void run(async () => {
                const result = await getExportDownloadUrl(exportId);
                if (result?.url) {
                  window.open(result.url, "_blank");
                } else {
                  throw new Error("Export is not ready to download");
                }
              }, "Download opened")
            }
            collapsed={workCollapsed}
            onToggleCollapse={() => {
              if (workPanelRef.current?.isCollapsed()) workPanelRef.current.expand();
              else workPanelRef.current?.collapse();
            }}
          />
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  );
}
