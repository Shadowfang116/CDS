'use client';

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  getMe,
  getCase,
  listDocuments,
  getDocumentDownloadUrl,
  getDossier,
  autofillDossier,
  evaluateCase,
  listExceptions,
  listCPs,
  generateDiscrepancyLetter,
  generateUndertakingIndemnity,
  generateInternalOpinion,
  generateBankPack,
  listExports,
  listVerifications,
  updateVerificationKeys,
  openVerificationPortal,
  attachVerificationEvidence,
  markVerificationVerified,
  markVerificationFailed,
  getCaseInsights,
  CaseInsightsResponse,
  ApiError,
  getCaseControls,
  CaseControlsResponse,
} from '@/lib/api';
import { OCRExtractionsPanel } from '@/components/ocr/OCRExtractionsPanel';
import { CaseControlsCard } from '@/components/case/CaseControlsCard';
import { DossierFieldsEditor } from '@/components/case/DossierFieldsEditor';
import { AuditPanel } from '@/components/cases/AuditPanel';
import { DocumentsPanel } from '@/components/cases/DocumentsPanel';
import { ExceptionsPanel } from '@/components/cases/ExceptionsPanel';
import { SetPageChrome } from '@/components/layout/set-page-chrome';
import { EmptyState } from '@/components/ui/empty-state';
import { Button } from '@/components/ui/button';
import { CaseStatusPill, type CaseStatus } from '@/components/ui/case-status-pill';
import { SeverityBadge } from '@/components/ui/severity-badge';
import { getRuleEvidenceDefinition, isEvidenceSatisfied } from '@/config/rules_evidence';
import { getFieldLabelMeta } from '@/lib/field-labels';
import {
  CASE_TABS,
  type CaseTabKey,
  getCaseTabPath,
  getCaseDocumentFocusPath,
  normalizeCaseTab,
} from '@/lib/routes';
import {
  CaseNotFoundState,
  CaseTabSkeleton,
  CaseWorkspaceSkeleton,
} from '@/components/cases/case-workspace-state';

function normalizeCaseStatus(status?: string | null): CaseStatus {
  const allowed: CaseStatus[] = [
    'New',
    'Processing',
    'Review',
    'Pending Docs',
    'Ready for Approval',
    'Approved',
    'Rejected',
    'Closed',
  ];

  return allowed.includes((status ?? '') as CaseStatus)
    ? ((status ?? 'New') as CaseStatus)
    : 'New';
}

function getBorrowerLabel(dossier: any): string | null {
  const fields = Array.isArray(dossier?.fields) ? dossier.fields : [];
  const borrower =
    fields.find((field: any) => field.field_key === 'party.name.borrower')?.field_value ??
    fields.find((field: any) => field.field_key === 'party.buyer.names')?.field_value ??
    null;

  return typeof borrower === 'string' && borrower.trim() ? borrower.trim() : null;
}

function getSeverityRank(severity?: string | null): number {
  switch (severity) {
    case 'Critical':
      return 0;
    case 'High':
      return 1;
    case 'Medium':
      return 2;
    case 'Low':
      return 3;
    default:
      return 4;
  }
}

function getSeverityAccent(severity?: string | null): string {
  switch (severity) {
    case 'Critical':
      return 'border-[rgba(239,68,68,0.38)] bg-[rgba(239,68,68,0.1)]';
    case 'High':
      return 'border-[rgba(245,158,11,0.35)] bg-[rgba(245,158,11,0.1)]';
    case 'Medium':
      return 'border-[rgba(234,179,8,0.35)] bg-[rgba(234,179,8,0.1)]';
    case 'Low':
      return 'border-[rgba(96,165,250,0.3)] bg-[rgba(96,165,250,0.08)]';
    default:
      return 'border-[rgba(82,90,99,0.35)] bg-[rgba(34,39,45,0.75)]';
  }
}

function getSeverityBadgeClass(severity?: string | null): string {
  switch (severity) {
    case 'Critical':
      return 'badge-error';
    case 'High':
      return 'badge-warning';
    case 'Medium':
      return 'badge-warning';
    case 'Low':
      return 'badge-info';
    default:
      return 'badge-neutral';
  }
}

function getStatusBadgeClass(status?: string | null): string {
  switch (status) {
    case 'Resolved':
    case 'Satisfied':
    case 'Verified':
      return 'badge-success';
    case 'Waived':
    case 'Failed':
      return 'badge-warning';
    case 'Open':
    case 'Pending':
      return 'badge-neutral';
    default:
      return 'badge-neutral';
  }
}

function getCpStatusLabel(status?: string | null): string {
  switch (status) {
    case 'Satisfied':
      return 'Fulfilled';
    case 'Waived':
      return 'Waived';
    default:
      return 'Pending';
  }
}

function truncateText(value?: string | null, maxLength: number = 140): string {
  const normalized = typeof value === 'string' ? value.trim() : '';
  if (!normalized) {
    return '';
  }
  if (normalized.length <= maxLength) {
    return normalized;
  }
  return `${normalized.slice(0, maxLength).trimEnd()}...`;
}

function getDecisionIndicator(params: {
  caseStatus?: string | null;
  openHigh: number;
  openMedium: number;
  openLow: number;
  openCps: number;
}) {
  const { caseStatus, openHigh, openMedium, openLow, openCps } = params;

  if (caseStatus === 'Rejected' || openHigh >= 2) {
    return {
      label: 'Reject',
      tone: 'text-[rgb(219,156,153)]',
      surface: 'border-[rgba(189,90,86,0.38)] bg-[rgba(189,90,86,0.1)]',
      rationale: 'Multiple unresolved high-severity exceptions remain open.',
    };
  }

  if (openHigh >= 1) {
    return {
      label: 'Hold',
      tone: 'text-[rgb(219,194,137)]',
      surface: 'border-[rgba(184,151,95,0.35)] bg-[rgba(184,151,95,0.1)]',
      rationale: 'A high-severity exception remains unresolved and requires reviewer action.',
    };
  }

  if (openCps > 0 || openMedium > 0 || openLow > 0) {
    return {
      label: 'Proceed with Conditions',
      tone: 'text-[rgb(219,194,137)]',
      surface: 'border-[rgba(184,151,95,0.35)] bg-[rgba(184,151,95,0.1)]',
      rationale: 'No unresolved high-severity exceptions remain, but open Conditions Precedent or residual issues still require closure.',
    };
  }

  return {
    label: 'Proceed',
    tone: 'text-[rgb(157,201,169)]',
    surface: 'border-[rgba(88,140,102,0.35)] bg-[rgba(88,140,102,0.12)]',
    rationale: 'No unresolved high-severity exceptions or open Conditions Precedent remain.',
  };
}

export function CaseWorkspace(props: { caseId: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { caseId } = props;

  const [caseData, setCaseData] = useState<any>(null);
  const [documents, setDocuments] = useState<any[]>([]);
  const [controls, setControls] = useState<CaseControlsResponse | null>(null);
  const [dossier, setDossier] = useState<any>(null);
  const [exceptions, setExceptions] = useState<any>(null);
  const [cps, setCps] = useState<any>(null);
  const [exports, setExports] = useState<any>(null);
  const [verifications, setVerifications] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<CaseTabKey>('summary');
  const [loading, setLoading] = useState(true);
  const [missingCase, setMissingCase] = useState(false);
  const [error, setError] = useState('');
  const [evaluating, setEvaluating] = useState(false);
  const [generating, setGenerating] = useState<string | null>(null);
  const [autofillOverwrite, setAutofillOverwrite] = useState(false);
  const [autofilling, setAutofilling] = useState(false);
  const [autofillResult, setAutofillResult] = useState<any>(null);
  const [generatedDrafts, setGeneratedDrafts] = useState<any[]>([]);
  const [insights, setInsights] = useState<CaseInsightsResponse | null>(null);
  const [insightsDays, setInsightsDays] = useState(30);
  const [insightsLoading, setInsightsLoading] = useState(false);
  const [dossierLoading, setDossierLoading] = useState(false);
  const [exceptionsLoading, setExceptionsLoading] = useState(false);
  const [exportsLoading, setExportsLoading] = useState(false);
  const [verificationsLoading, setVerificationsLoading] = useState(false);
  const [initialLoadComplete, setInitialLoadComplete] = useState(false);
  const [docNavTarget, setDocNavTarget] = useState<{ docId: string; page?: number } | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const loadedTabsRef = useRef<Set<string>>(new Set());
  const checkAuthAndLoadRef = useRef<null | (() => void | Promise<void>)>(null);

  const initialDocId = searchParams.get('docId') || searchParams.get('focusDocId') || undefined;
  const initialPageParam = searchParams.get('page') || searchParams.get('focusPage');
  const initialPage = initialPageParam ? parseInt(initialPageParam, 10) : undefined;

  // Memoize caseId to prevent unnecessary re-renders
  const memoizedCaseId = useMemo(() => caseId, [caseId]);

  const loadCase = useCallback(async () => {
    // Check if request was aborted
    if (abortControllerRef.current?.signal.aborted) {
      return;
    }
    
    setLoading(true);
    setError(''); // Clear previous errors
    setMissingCase(false);
    try {
      // Load case, documents, and controls in parallel (single source of truth)
      const [c, docs, ctrls, dossierResult, exceptionsResult, cpsResult] = await Promise.allSettled([
        getCase(memoizedCaseId),
        listDocuments(memoizedCaseId),
        getCaseControls(memoizedCaseId),
        getDossier(memoizedCaseId),
        listExceptions(memoizedCaseId),
        listCPs(memoizedCaseId),
      ]);

      if (
        c.status !== 'fulfilled' ||
        docs.status !== 'fulfilled' ||
        ctrls.status !== 'fulfilled'
      ) {
        throw (
          (c.status === 'rejected' && c.reason) ||
          (docs.status === 'rejected' && docs.reason) ||
          (ctrls.status === 'rejected' && ctrls.reason) ||
          new Error('Failed to load case')
        );
      }
      
      // Check if request was aborted before setting state
      if (abortControllerRef.current?.signal.aborted) {
        return;
      }
      
      setCaseData(c.value);
      setDocuments(docs.value);
      setControls(ctrls.value);
      if (dossierResult.status === 'fulfilled') {
        setDossier(dossierResult.value);
      }
      if (exceptionsResult.status === 'fulfilled') {
        setExceptions(exceptionsResult.value);
        loadedTabsRef.current.add(`${memoizedCaseId}:exceptions`);
      }
      if (cpsResult.status === 'fulfilled') {
        setCps(cpsResult.value);
        loadedTabsRef.current.add(`${memoizedCaseId}:cps`);
      }
      if (dossierResult.status === 'fulfilled') {
        loadedTabsRef.current.add(`${memoizedCaseId}:dossier`);
      }
      setInitialLoadComplete(true); // Mark initial load as complete
    } catch (e: any) {
      // Ignore abort errors
      if (e.name === 'AbortError') {
        return;
      }
      
      // Handle ApiError with structured details
      if (e instanceof ApiError) {
        if (e.status === 404) {
          setMissingCase(true);
          setError('');
        } else {
          setError(e.detail || `Failed to load case: ${e.message}`);
        }
      } else {
        setError(e.message || 'Failed to load case');
      }
      setInitialLoadComplete(true); // Mark as complete even on error
    } finally {
      if (!abortControllerRef.current?.signal.aborted) {
        setLoading(false);
      }
    }
  }, [memoizedCaseId]); // Only recreate if caseId changes

  // Define checkAuthAndLoad after loadCase (depends on loadCase)
  const checkAuthAndLoad = useCallback(async () => {
    try {
      await getMe();
    } catch {
      router.push('/');
      return;
    }
    await loadCase();
  }, [router, loadCase]);

  // Keep ref in sync with latest checkAuthAndLoad callback
  useEffect(() => {
    checkAuthAndLoadRef.current = checkAuthAndLoad;
  }, [checkAuthAndLoad]);

  // Separate effect for initial load (only runs when caseId changes)
  useEffect(() => {
    // Abort previous request if still in flight
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    
    // Create new AbortController for this case load
    const abortController = new AbortController();
    abortControllerRef.current = abortController;
    
    setInitialLoadComplete(false);
    loadedTabsRef.current.clear(); // Reset loaded tabs when caseId changes
    
    void checkAuthAndLoadRef.current?.();
    
    // Cleanup: abort in-flight request on unmount or caseId change
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [memoizedCaseId]);

  // Keep the visible tab aligned with URL query params.
  useEffect(() => {
    if (!initialLoadComplete) return;

    if (searchParams.get('focusDocId') || searchParams.get('docId')) {
      setActiveTab('documents');
      return;
    }
    setActiveTab(normalizeCaseTab(searchParams.get('tab')));
  }, [searchParams, initialLoadComplete]);

  const loadDossier = useCallback(async () => {
    setDossierLoading(true);
    try {
      const d = await getDossier(memoizedCaseId);
      setDossier(d);
    } catch (e: any) {
      setError(e.message || 'Failed to load dossier');
    } finally {
      setDossierLoading(false);
    }
  }, [memoizedCaseId]);

  const loadExceptionsAndCPs = useCallback(async () => {
    setExceptionsLoading(true);
    try {
      const [exc, cp] = await Promise.all([
        listExceptions(memoizedCaseId),
        listCPs(memoizedCaseId),
      ]);
      setExceptions(exc);
      setCps(cp);
    } catch (e: any) {
      setError(e.message || 'Failed to load exceptions or conditions precedent');
    } finally {
      setExceptionsLoading(false);
    }
  }, [memoizedCaseId]);

  const loadExports = useCallback(async () => {
    setExportsLoading(true);
    try {
      const exp = await listExports(memoizedCaseId);
      setExports(exp);
    } catch (e: any) {
      setError(e.message || 'Failed to load export history');
    } finally {
      setExportsLoading(false);
    }
  }, [memoizedCaseId]);

  const loadVerifications = useCallback(async () => {
    setVerificationsLoading(true);
    try {
      const v = await listVerifications(memoizedCaseId);
      setVerifications(v);
    } catch (e: any) {
      setError(e.message || 'Failed to load verification checks');
    } finally {
      setVerificationsLoading(false);
    }
  }, [memoizedCaseId]);

  const loadInsights = useCallback(async (days: number) => {
    setInsightsLoading(true);
    try {
      const data = await getCaseInsights(memoizedCaseId, days);
      setInsights(data);
    } catch (e: any) {
      setError(e.message || 'Failed to load case summary');
    } finally {
      setInsightsLoading(false);
    }
  }, [memoizedCaseId]);

  // Tab-based loading: only load data when tab becomes active (and caseId is stable)
  // Use loadedTabsRef to prevent repeated loads for the same tab
  useEffect(() => {
    if (!initialLoadComplete) return; // Wait for initial case load
    
    const tabKey = `${memoizedCaseId}:${activeTab}`;
    
    // Skip if this tab was already loaded for this case
    if (loadedTabsRef.current.has(tabKey)) {
      return;
    }
    
    if (activeTab === 'dossier') {
      loadDossier();
      loadedTabsRef.current.add(tabKey);
    } else if (activeTab === 'verification') {
      loadVerifications();
      loadedTabsRef.current.add(tabKey);
    } else if (activeTab === 'exceptions' || activeTab === 'cps') {
      loadExceptionsAndCPs();
      loadedTabsRef.current.add(`${memoizedCaseId}:exceptions`);
      loadedTabsRef.current.add(`${memoizedCaseId}:cps`);
    } else if (activeTab === 'drafts' || activeTab === 'exports') {
      loadExports();
      loadedTabsRef.current.add(tabKey);
    } else if (activeTab === 'summary') {
      loadInsights(insightsDays);
      loadedTabsRef.current.add(tabKey);
    }
  }, [activeTab, memoizedCaseId, insightsDays, initialLoadComplete, loadDossier, loadVerifications, loadExceptionsAndCPs, loadExports, loadInsights]);

  const focusEvidence = useCallback((docId: string, pageNum?: number, candidateId?: string) => {
    setActiveTab('documents');
    router.push(getCaseDocumentFocusPath(caseId, docId, pageNum, candidateId));
  }, [router, caseId]);

  const handleNavigateToDocument = useCallback((docId: string, page?: number) => {
    setDocNavTarget({ docId, page });
    setActiveTab('documents');
    router.replace(getCaseDocumentFocusPath(caseId, docId, page), { scroll: false });
  }, [router, caseId]);

  const navigateToDocuments = useCallback(() => {
    setActiveTab('documents');
    router.replace(getCaseTabPath(caseId, 'documents'), { scroll: false });
  }, [router, caseId]);

  const handleAutofill = async () => {
    setAutofilling(true);
    setAutofillResult(null);
    try {
      const result = await autofillDossier(caseId, autofillOverwrite);
      setAutofillResult(result);
      await loadDossier(); // Reload dossier to show updated fields
      router.replace(getCaseTabPath(caseId, 'ocr-extractions'), { scroll: false });
    } catch (e: any) {
      setAutofillResult({
        extracted: [],
        updated_fields: [],
        skipped_fields: [],
        errors: [e.message || 'Autofill failed'],
      });
    } finally {
      setAutofilling(false);
    }
  };

  const handleEvaluate = async () => {
    setEvaluating(true);
    setError('');
    try {
      await evaluateCase(caseId);
      await loadExceptionsAndCPs();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setEvaluating(false);
    }
  };

  const handleGenerateDraft = async (type: string) => {
    setGenerating(type);
    setError('');
    try {
      let result;
      switch (type) {
        case 'discrepancy':
          result = await generateDiscrepancyLetter(caseId);
          break;
        case 'undertaking':
          result = await generateUndertakingIndemnity(caseId);
          break;
        case 'opinion':
          result = await generateInternalOpinion(caseId);
          break;
        default:
          throw new Error('Unknown draft type');
      }
      setGeneratedDrafts(prev => [result, ...prev]);
      await loadExports();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setGenerating(null);
    }
  };

  const handleGenerateBankPack = async () => {
    setGenerating('bankpack');
    setError('');
    try {
      const result = await generateBankPack(caseId);
      setGeneratedDrafts(prev => [result, ...prev]);
      await loadExports();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setGenerating(null);
    }
  };

  const caseStatus = normalizeCaseStatus(caseData?.status);
  const borrowerLabel = getBorrowerLabel(dossier);
  const exceptionItems: any[] = useMemo(
    () => (Array.isArray(exceptions?.exceptions) ? exceptions.exceptions : []),
    [exceptions]
  );
  const cpItems: any[] = useMemo(
    () => (Array.isArray(cps?.cps) ? cps.cps : []),
    [cps]
  );
  const enrichedCpItems = useMemo(
    () =>
      cpItems.map((cp: any) => ({
        ...cp,
        evidenceDefinition: getRuleEvidenceDefinition(cp.rule_id, cp.evidence_required),
        linkedEvidence: Array.isArray(cp.evidence_refs) ? cp.evidence_refs : [],
        evidenceSatisfied: isEvidenceSatisfied(cp.evidence_refs),
      })),
    [cpItems]
  );
  const documentLookup = useMemo(() => {
    const lookup = new Map<string, any>();
    documents.forEach((doc) => {
      if (typeof doc?.id === 'string' && doc.id) {
        lookup.set(doc.id, doc);
      }
    });
    return lookup;
  }, [documents]);
  const openExceptionCounts = useMemo(() => {
    return exceptionItems.reduce(
      (acc: { high: number; medium: number; low: number }, exc: any) => {
        if (exc.status !== 'Open') {
          return acc;
        }
        if (exc.severity === 'High') acc.high += 1;
        else if (exc.severity === 'Medium') acc.medium += 1;
        else if (exc.severity === 'Low') acc.low += 1;
        return acc;
      },
      { high: 0, medium: 0, low: 0 }
    );
  }, [exceptionItems]);
  const openCpCount = useMemo(
    () => enrichedCpItems.filter((cp: any) => cp.status === 'Open').length,
    [enrichedCpItems]
  );
  const satisfiedCpCount = useMemo(
    () => enrichedCpItems.filter((cp: any) => cp.status === 'Satisfied').length,
    [enrichedCpItems]
  );
  const waivedExceptionCount = useMemo(
    () => exceptionItems.filter((exc: any) => exc.status === 'Waived').length,
    [exceptionItems]
  );
  const openExceptionTotal = useMemo(
    () => openExceptionCounts.high + openExceptionCounts.medium + openExceptionCounts.low,
    [openExceptionCounts]
  );
  const decisionIndicator = useMemo(
    () =>
      getDecisionIndicator({
        caseStatus,
        openHigh: openExceptionCounts.high,
        openMedium: openExceptionCounts.medium,
        openLow: openExceptionCounts.low,
        openCps: openCpCount,
      }),
    [caseStatus, openExceptionCounts, openCpCount]
  );
  const keyIssues = useMemo(() => {
    const prioritized = exceptionItems
      .filter((exc) => exc.status === 'Open')
      .sort((a, b) => getSeverityRank(a.severity) - getSeverityRank(b.severity));

    return prioritized.slice(0, 5);
  }, [exceptionItems]);
  const cpsBySeverity = useMemo(
    () =>
      ['High', 'Medium', 'Low']
        .map((severity) => ({
          severity,
          items: enrichedCpItems.filter((cp) => cp.severity === severity),
        }))
        .filter((group) => group.items.length > 0),
    [enrichedCpItems]
  );
  const approvalReadiness = useMemo(() => {
    const notReady = openExceptionCounts.high > 0 || openCpCount > 0;
    return {
      label: notReady ? 'NOT READY' : 'READY',
      tone: notReady ? 'text-[rgb(240,205,202)]' : 'text-[rgb(187,205,189)]',
      surface: notReady
        ? 'border-[rgba(189,90,86,0.38)] bg-[rgba(189,90,86,0.1)]'
        : 'border-[rgba(88,140,102,0.35)] bg-[rgba(88,140,102,0.12)]',
      rationale: notReady
        ? 'Open high-severity exceptions or required Conditions Precedent still block approval readiness.'
        : 'No open high-severity exceptions or required Conditions Precedent currently block approval readiness.',
    };
  }, [openCpCount, openExceptionCounts.high]);
  const getDocumentLabel = useCallback(
    (documentId?: string | null) => {
      if (!documentId) return 'Annexure reference pending';
      const doc = documentLookup.get(documentId);
      return doc?.original_filename || doc?.filename || `${documentId.slice(0, 8)}…`;
    },
    [documentLookup]
  );
  const formatEvidenceLabel = useCallback(
    (ref?: { document_id?: string | null; page_number?: number | null; note?: string | null } | null) => {
      if (!ref) {
        return 'Annexure reference pending';
      }

      const segments = [getDocumentLabel(ref.document_id)];
      if (ref.page_number) {
        segments.push(`Page ${ref.page_number}`);
      }
      if (ref.note) {
        segments.push(ref.note);
      }
      return segments.join(' • ');
    },
    [getDocumentLabel]
  );

  if (loading) {
    return <CaseWorkspaceSkeleton />;
  }

  if (missingCase) {
    return <CaseNotFoundState onBack={() => router.push('/dashboard/cases')} />;
  }

  return (
    <>
      <SetPageChrome
        title={caseData?.title || 'Case'}
        breadcrumbs={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Cases', href: '/dashboard/cases' },
          { label: caseData?.title || 'Case' }
        ]}
        actions={<CaseStatusPill status={caseStatus} />}
      />
      <div className="space-y-6 p-6">
        {error && (
          <div className="rounded-lg border border-[rgba(189,90,86,0.36)] bg-[rgba(189,90,86,0.12)] px-4 py-3 text-sm text-[rgb(219,156,153)]">
            <div className="flex items-start justify-between gap-4">
              <span>{error}</span>
              <button onClick={() => setError('')} className="text-[rgb(219,156,153)] hover:text-stone-100">×</button>
            </div>
          </div>
        )}

        <section className="rounded-lg border border-[rgba(82,90,99,0.4)] bg-[rgba(24,28,32,0.9)] px-5 py-4">
          <div className="grid gap-4 lg:grid-cols-[1.4fr_repeat(3,minmax(0,1fr))]">
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">Case Workspace</div>
              <div className="mt-2 text-xl font-semibold text-stone-100">{caseData?.title || caseId}</div>
              <div className="mt-1 text-sm text-stone-400">{borrowerLabel ? `Borrower / Client: ${borrowerLabel}` : `Case Reference: ${caseId}`}</div>
              <div className="mt-4 flex flex-wrap gap-2">
                <Button size="sm" variant="outline" onClick={() => { setActiveTab('documents'); router.replace(getCaseTabPath(caseId, 'documents'), { scroll: false }); }}>
                  Open Documents
                </Button>
                <Button size="sm" variant="outline" onClick={() => { setActiveTab('exceptions'); router.replace(getCaseTabPath(caseId, 'exceptions'), { scroll: false }); }}>
                  Review Exceptions
                </Button>
                <Button size="sm" variant="outline" onClick={() => { setActiveTab('exports'); router.replace(getCaseTabPath(caseId, 'exports'), { scroll: false }); }}>
                  Exports & Drafts
                </Button>
              </div>
            </div>
            <div className="rounded-md border border-[rgba(82,90,99,0.35)] bg-[rgba(34,39,45,0.75)] px-4 py-3">
              <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">Status</div>
              <div className="mt-2">
                <CaseStatusPill status={caseStatus} />
              </div>
            </div>
            <div className="rounded-md border border-[rgba(82,90,99,0.35)] bg-[rgba(34,39,45,0.75)] px-4 py-3">
              <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">Open Exceptions</div>
              <div className="mt-2 text-2xl font-semibold text-stone-100">{exceptions?.open_count ?? openExceptionTotal}</div>
            </div>
            <div className="rounded-md border border-[rgba(82,90,99,0.35)] bg-[rgba(34,39,45,0.75)] px-4 py-3">
              <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">Open CPs</div>
              <div className="mt-2 text-2xl font-semibold text-stone-100">{cps?.open_count ?? 0}</div>
            </div>
          </div>
        </section>

        <div className="flex gap-4 overflow-x-auto border-b border-[rgba(82,90,99,0.32)]">
          {CASE_TABS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => {
                setActiveTab(key);
                router.replace(getCaseTabPath(caseId, key), { scroll: false });
              }}
              data-tour={key === 'ocr-extractions' ? 'ocr-review' : key === 'exceptions' ? 'exceptions' : key === 'exports' ? 'export' : undefined}
              className={`pb-3 text-sm whitespace-nowrap transition-colors ${activeTab === key ? 'border-b-2 border-[rgba(126,133,111,0.88)] text-stone-100' : 'text-stone-500 hover:text-stone-200'}`}
            >
              {label}
              {key === 'exceptions' && exceptions?.open_count > 0 ? (
                <span className="ml-2 badge badge-error">{exceptions.open_count}</span>
              ) : null}
            </button>
          ))}
        </div>

      {/* Documents Tab */}
      {activeTab === 'documents' && (
        <DocumentsPanel
          caseId={caseId}
          documents={documents}
          initialDocumentId={docNavTarget?.docId ?? initialDocId}
          initialPage={docNavTarget?.page ?? (Number.isFinite(initialPage) ? initialPage : undefined)}
          onDocumentsChange={setDocuments}
        />
      )}

      {/* Dossier Tab - P14: Use DossierFieldsEditor */}
      {activeTab === 'dossier' && (
        dossierLoading && !dossier ? (
          <CaseTabSkeleton />
        ) : (
        <div className="space-y-6">
          {/* Autofill Card */}
          <div className="card">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <h3 className="text-lg font-semibold mb-3">Autofill from OCR</h3>
                <p className="mb-4 text-sm text-stone-400">
                  Extract key dossier fields (plot, block, phase, scheme, district, etc.) from OCR text across all documents.
                </p>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={autofillOverwrite}
                    onChange={(e) => setAutofillOverwrite(e.target.checked)}
                    className="checkbox"
                  />
                  <span className="text-sm text-stone-300">Overwrite existing values</span>
                </label>
              </div>
              <Button
                onClick={() => void handleAutofill()}
                disabled={autofilling}
                loading={autofilling}
              >
                {autofilling ? 'Running Autofill...' : 'Run Autofill'}
              </Button>
            </div>
            {autofillResult && (
              <div className="mt-4 rounded-lg border border-[rgba(82,90,99,0.38)] bg-[rgba(34,39,45,0.82)] p-4">
                <h4 className="mb-2 font-medium text-stone-100">Autofill Results</h4>
                <div className="space-y-1 text-sm">
                  <p className="text-[rgb(187,205,189)]">Updated: {autofillResult.updated_fields.length} fields</p>
                  {autofillResult.skipped_fields.length > 0 && (
                    <p className="text-[rgb(219,194,137)]">Skipped: {autofillResult.skipped_fields.length} fields (already set)</p>
                  )}
                  {autofillResult.errors.length > 0 && (
                    <p className="text-[rgb(219,156,153)]">Errors: {autofillResult.errors.join(', ')}</p>
                  )}
                </div>
                {autofillResult.extracted.length > 0 && (
                  <div className="mt-3">
                    <p className="mb-2 text-xs text-stone-500">Extracted Fields</p>
                    <div className="max-h-40 space-y-1 overflow-y-auto">
                      {autofillResult.extracted.map((ef: any, idx: number) => (
                        <div key={idx} className="rounded-md border border-[rgba(82,90,99,0.3)] bg-[rgba(24,28,32,0.8)] p-2 text-xs">
                          <span className="font-medium">{getFieldLabelMeta(ef.field_path).label}:</span> {ef.value} 
                          <span className="ml-2 text-stone-500">({Math.round(ef.confidence * 100)}% confidence)</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* P14: DossierFieldsEditor */}
          <div className="card">
            <div className="mb-4">
              <h2 className="text-lg font-semibold">Case Dossier</h2>
              <p className="text-sm text-slate-400">
                Edit dossier fields with notes and evidence links. Critical fields require evidence or Admin force.
              </p>
            </div>
            <DossierFieldsEditor caseId={caseId} documents={documents} />
          </div>
        </div>
        )
      )}

      {/* Audit Tab */}
      {activeTab === 'audit' && (
        <AuditPanel caseId={caseId} />
      )}

      {/* OCR Extractions Tab */}
      {activeTab === 'ocr-extractions' && (
        <div className="space-y-6">
          <div className="card">
            <h2 className="text-lg font-semibold mb-4">OCR Extractions</h2>
            <p className="text-slate-400 mb-4">
              Review and edit OCR-extracted fields before confirming them to the dossier.
            </p>
            <OCRExtractionsPanel
              caseId={caseId}
              documents={documents}
              onViewDocument={focusEvidence}
            />
          </div>
        </div>
      )}

      {/* Verification Tab */}
      {activeTab === 'verification' && (
        verificationsLoading && verifications.length === 0 ? (
          <CaseTabSkeleton />
        ) : (
        <div className="space-y-6">
          <div className="card">
            <h2 className="text-lg font-semibold mb-4">Assisted Verification</h2>
            <p className="text-slate-400 mb-6">Verify e-Stamp and Registry/ROD documents via official government portals.</p>
          </div>

          {verifications.length === 0 ? (
            <EmptyState
              title="No verification checks recorded."
              description="Verification requirements will appear here when registry or e-Stamp review is needed."
            />
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {verifications.map((v) => (
                <VerificationCard
                  key={v.id}
                  verification={v}
                  caseId={caseId}
                  documents={documents}
                  onUpdate={loadVerifications}
                  setError={setError}
                />
              ))}
            </div>
          )}
        </div>
        )
      )}

      {/* Exceptions Tab */}
      {activeTab === 'exceptions' && (
        <ExceptionsPanel
          caseId={caseId}
          documents={documents}
          onNavigateToDocument={handleNavigateToDocument}
          onExceptionsChange={setExceptions}
          onEvaluate={handleEvaluate}
          evaluating={evaluating}
        />
      )}

      {/* Conditions Precedent Tab */}
      {activeTab === 'cps' && (
        exceptionsLoading && !cps ? (
          <CaseTabSkeleton />
        ) : (
        <div className="space-y-6">
          <div className="card">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold">Conditions Precedent (CP)</h2>
                <p className="mt-1 text-sm text-slate-400">Track required undertakings, missing annexures, and satisfaction status before approval.</p>
              </div>
              <Button
                onClick={handleEvaluate}
                disabled={evaluating}
                loading={evaluating}
              >
                {evaluating ? 'Evaluating...' : 'Evaluate Rules'}
              </Button>
            </div>
          </div>

          <div className="card">
            <h3 className="font-semibold mb-4">
              Conditions Precedent
              {cps && <span className="text-slate-400 ml-2">({cps.open_count} open)</span>}
            </h3>
            {cpItems.length === 0 ? (
              <EmptyState
                title="No conditions precedent generated."
                description="When reviewer obligations or missing annexures are detected, they will appear here for closure tracking."
              />
            ) : (
              <div className="space-y-5">
                {cpsBySeverity.map((group) => (
                  <section key={group.severity} className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="text-xs font-semibold uppercase tracking-[0.08em] text-stone-400">
                        {group.severity} Severity
                      </div>
                      <span className={`badge ${getSeverityBadgeClass(group.severity)}`}>
                        {group.items.length}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                      {group.items.map((cp: any) => (
                        <div key={cp.id} className={`rounded-lg border p-4 ${getSeverityAccent(cp.severity)}`}>
                          <div className="flex justify-between items-start gap-3 mb-3">
                            <div className="flex flex-wrap gap-2">
                              <SeverityBadge severity={cp.severity} />
                              <span className={`badge ${getStatusBadgeClass(cp.status)}`}>
                                {getCpStatusLabel(cp.status)}
                              </span>
                              <span className={`badge ${cp.evidenceSatisfied ? 'badge-success' : 'badge-error'}`}>
                                {cp.evidenceSatisfied ? 'Evidence Satisfied' : 'Missing Evidence'}
                              </span>
                            </div>
                          </div>
                          <p className="text-sm text-stone-100">{cp.text}</p>
                          <dl className="mt-4 space-y-2 text-xs text-slate-300">
                            <div>
                              <dt className="text-slate-500">Evidence Required</dt>
                              <dd className="mt-1">{cp.evidenceDefinition.required_evidence.join(', ')}</dd>
                            </div>
                            <div>
                              <dt className="text-slate-500">Acceptable Substitutes</dt>
                              <dd className="mt-1">
                                {cp.evidenceDefinition.acceptable_substitutes.length > 0
                                  ? cp.evidenceDefinition.acceptable_substitutes.join(', ')
                                  : 'No substitute evidence defined.'}
                              </dd>
                            </div>
                            {cp.evidenceDefinition.closure_guidance ? (
                              <div>
                                <dt className="text-slate-500">Closure Guidance</dt>
                                <dd className="mt-1">{cp.evidenceDefinition.closure_guidance}</dd>
                              </div>
                            ) : null}
                            {cp.evidenceDefinition.cp_recommended_text ? (
                              <div>
                                <dt className="text-slate-500">Recommended CP Text</dt>
                                <dd className="mt-1">{cp.evidenceDefinition.cp_recommended_text}</dd>
                              </div>
                            ) : null}
                            <div>
                              <dt className="text-slate-500">Linked Evidence</dt>
                              {cp.linkedEvidence.length > 0 ? (
                                <div className="mt-2 space-y-2">
                                  {cp.linkedEvidence.map((ref: any) => (
                                    <div key={ref.id} className="rounded-md border border-[rgba(82,90,99,0.32)] bg-[rgba(24,28,32,0.45)] px-3 py-2">
                                      <div className="flex items-start justify-between gap-3">
                                        <div className="min-w-0 text-stone-100">{formatEvidenceLabel(ref)}</div>
                                        {ref.document_id ? (
                                          <Button
                                            size="sm"
                                            variant="ghost"
                                            onClick={() => handleNavigateToDocument(ref.document_id, ref.page_number ?? undefined)}
                                          >
                                            View
                                          </Button>
                                        ) : null}
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              ) : (
                                <dd className="mt-1">No supporting annexure linked.</dd>
                              )}
                            </div>
                            <div>
                              <dt className="text-slate-500">Due Date</dt>
                              <dd className="mt-1">Not scheduled</dd>
                            </div>
                            <div>
                              <dt className="text-slate-500">Status Note</dt>
                              <dd className="mt-1">
                                {cp.status === 'Open'
                                  ? cp.evidenceSatisfied
                                    ? 'Supporting annexure is linked, but the Condition Precedent remains open until it is formally satisfied.'
                                    : 'Condition Precedent remains open because the required annexure has not been linked yet.'
                                  : cp.status === 'Satisfied'
                                    ? 'Condition Precedent has been satisfied on the strength of linked evidence.'
                                    : 'Condition Precedent has been closed by waiver or workflow action.'}
                              </dd>
                            </div>
                            <div>
                              <dt className="text-slate-500">Rule Reference</dt>
                              <dd className="mt-1">{cp.rule_id || '—'}</dd>
                            </div>
                            {cp.evidenceDefinition.reviewer_confirmation_required ? (
                              <div>
                                <dt className="text-slate-500">Fallback Discipline</dt>
                                <dd className="mt-1 text-[rgb(234,215,170)]">Reviewer confirmation required.</dd>
                              </div>
                            ) : null}
                          </dl>
                        </div>
                      ))}
                    </div>
                  </section>
                ))}
              </div>
            )}
          </div>
        </div>
        )
      )}

      {/* Drafts Tab */}
      {activeTab === 'drafts' && (
        exportsLoading && !exports ? (
          <CaseTabSkeleton />
        ) : (
        <div className="space-y-6">
          <div className="card">
            <h2 className="text-lg font-semibold mb-4">Generate Draft Documents</h2>
            <p className="mb-6 text-stone-400">Generate bank-style DOCX drafts based on case data, exceptions, and dossier fields.</p>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="rounded-lg border border-[rgba(82,90,99,0.38)] bg-[rgba(34,39,45,0.82)] p-4">
                <h3 className="font-medium mb-2">Discrepancy Letter</h3>
                <p className="mb-4 text-sm text-stone-400">Formal letter to borrower listing discrepancies and required actions.</p>
                <Button 
                  onClick={() => handleGenerateDraft('discrepancy')}
                  className="w-full"
                  disabled={generating === 'discrepancy'}
                  loading={generating === 'discrepancy'}
                >
                  {generating === 'discrepancy' ? 'Generating...' : 'Generate'}
                </Button>
              </div>
              
              <div className="rounded-lg border border-[rgba(82,90,99,0.38)] bg-[rgba(34,39,45,0.82)] p-4">
                <h3 className="font-medium mb-2">Undertaking & Indemnity</h3>
                <p className="mb-4 text-sm text-stone-400">Standard undertaking and indemnity document for borrower signature.</p>
                <Button 
                  onClick={() => handleGenerateDraft('undertaking')}
                  className="w-full"
                  disabled={generating === 'undertaking'}
                  loading={generating === 'undertaking'}
                >
                  {generating === 'undertaking' ? 'Generating...' : 'Generate'}
                </Button>
              </div>
              
              <div className="rounded-lg border border-[rgba(82,90,99,0.38)] bg-[rgba(34,39,45,0.82)] p-4">
                <h3 className="font-medium mb-2">Internal Opinion</h3>
                <p className="mb-4 text-sm text-stone-400">Skeleton internal legal opinion with findings and recommendation.</p>
                <Button 
                  onClick={() => handleGenerateDraft('opinion')}
                  className="w-full"
                  disabled={generating === 'opinion'}
                  loading={generating === 'opinion'}
                >
                  {generating === 'opinion' ? 'Generating...' : 'Generate'}
                </Button>
              </div>
            </div>
          </div>

          {generatedDrafts.length > 0 && (
            <div className="card">
              <h3 className="font-semibold mb-4">Recently Generated</h3>
              <ul className="space-y-2">
                {generatedDrafts.map((draft, i) => (
                  <li key={i} className="flex items-center justify-between rounded-lg border border-[rgba(82,90,99,0.35)] bg-[rgba(34,39,45,0.82)] p-3">
                    <div>
                      <p className="font-medium">{draft.filename}</p>
                      <p className="text-sm text-stone-400">{draft.export_type}</p>
                    </div>
                    <Button asChild size="sm">
                      <a 
                        href={draft.url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                      >
                        Download
                      </a>
                    </Button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
        )
      )}

      {/* Export Tab */}
      {activeTab === 'exports' && (
        exportsLoading && !exports ? (
          <CaseTabSkeleton />
        ) : (
        <div className="space-y-6">
          <div className="card">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <h2 className="text-lg font-semibold mb-4">Bank Pack Export</h2>
                <p className="text-slate-400 mb-6">Generate a bank-format PDF memorandum with executive summary, exception register, Conditions Precedent register, and annexure references.</p>
              </div>
              <Button
                onClick={handleGenerateBankPack}
                disabled={generating === 'bankpack'}
                loading={generating === 'bankpack'}
              >
                {generating === 'bankpack' ? 'Generating Bank Pack...' : 'Generate Bank Pack PDF'}
              </Button>
            </div>
          </div>

          <div className="card">
            <h3 className="font-semibold mb-4">
              Export History
              {exports && <span className="text-slate-400 ml-2">({exports.total} exports)</span>}
            </h3>
            {!exports || exports.exports.length === 0 ? (
              <EmptyState
                title="No exports generated yet."
                description="Generate a bank pack to create the first export record for this case."
                className="min-h-[180px]"
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="text-left border-b border-slate-700">
                      <th className="pb-2 text-slate-400 font-medium">Filename</th>
                      <th className="pb-2 text-slate-400 font-medium">Type</th>
                      <th className="pb-2 text-slate-400 font-medium">Created</th>
                      <th className="pb-2 text-slate-400 font-medium">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {exports.exports.map((exp: any) => (
                      <tr key={exp.id} className="border-b border-slate-700/50">
                        <td className="py-3">{exp.filename}</td>
                        <td className="py-3">
                          <span className={`badge ${
                            exp.export_type === 'bank_pack_pdf' ? 'badge-success' : 'badge-info'
                          }`}>
                            {exp.export_type}
                          </span>
                        </td>
                        <td className="py-3 text-slate-400">
                          {new Date(exp.created_at).toLocaleString()}
                        </td>
                        <td className="py-3">
                          <a 
                            href={`/api/v1/exports/${exp.id}/download`}
                            className="text-[rgb(194,200,185)] transition-colors hover:text-stone-100"
                            onClick={async (e) => {
                              e.preventDefault();
                              try {
                                const res = await fetch(`/api/v1/exports/${exp.id}/download`, {
                                  credentials: 'include',
                                });
                                const data = await res.json();
                                window.open(data.url, '_blank');
                              } catch (e: any) {
                                setError(e.message);
                              }
                            }}
                          >
                            Download
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
        )
      )}

      {/* Executive Summary Tab */}
      {activeTab === 'summary' && (
        <div className="space-y-6">
          <div className="card">
            <div className="mb-4">
              <h2 className="text-lg font-semibold">Executive Summary</h2>
              <p className="text-sm text-slate-400">Primary review posture, credit decision signal, and operating context for this case.</p>
            </div>

            <div className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
              <div className="space-y-6">
                <section className="rounded-lg border border-[rgba(82,90,99,0.35)] bg-[rgba(34,39,45,0.75)] p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">Case Snapshot</div>
                      <div className="mt-2 text-base font-semibold text-stone-100">{caseData?.title || caseId}</div>
                      <div className="mt-1 text-sm text-stone-400">{borrowerLabel || 'Borrower / client not recorded'}</div>
                    </div>
                    <CaseStatusPill status={caseStatus} />
                  </div>

                  <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                    <div className="rounded-md border border-[rgba(82,90,99,0.3)] bg-[rgba(24,28,32,0.86)] px-3 py-3">
                      <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">Borrower</div>
                      <div className="mt-2 text-sm font-medium text-stone-100">{borrowerLabel || 'Not recorded'}</div>
                    </div>
                    <div className="rounded-md border border-[rgba(82,90,99,0.3)] bg-[rgba(24,28,32,0.86)] px-3 py-3">
                      <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">Documents</div>
                      <div className="mt-2 text-2xl font-semibold text-stone-100">{documents.length}</div>
                    </div>
                    <div className="rounded-md border border-[rgba(82,90,99,0.3)] bg-[rgba(24,28,32,0.86)] px-3 py-3">
                      <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">Exceptions</div>
                      <div className="mt-2 text-2xl font-semibold text-stone-100">{exceptionItems.length}</div>
                    </div>
                    <div className="rounded-md border border-[rgba(82,90,99,0.3)] bg-[rgba(24,28,32,0.86)] px-3 py-3">
                      <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">Conditions Precedent</div>
                      <div className="mt-2 text-2xl font-semibold text-stone-100">{cpItems.length}</div>
                    </div>
                    <div className="rounded-md border border-[rgba(82,90,99,0.3)] bg-[rgba(24,28,32,0.86)] px-3 py-3">
                      <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">Open Exceptions</div>
                      <div className="mt-2 text-2xl font-semibold text-stone-100">{openExceptionTotal}</div>
                    </div>
                    <div className="rounded-md border border-[rgba(82,90,99,0.3)] bg-[rgba(24,28,32,0.86)] px-3 py-3">
                      <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">Open Conditions Precedent</div>
                      <div className="mt-2 text-2xl font-semibold text-stone-100">{openCpCount}</div>
                    </div>
                  </div>
                </section>

                <section className="rounded-lg border border-[rgba(82,90,99,0.35)] bg-[rgba(34,39,45,0.75)] p-4">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">Risk Summary</div>
                  <div className="mt-4 grid gap-3 md:grid-cols-3">
                    <div className="rounded-md border border-[rgba(189,90,86,0.32)] bg-[rgba(189,90,86,0.1)] px-3 py-3">
                      <div className="text-xs text-stone-300">High Severity Open</div>
                      <div className="mt-2 text-2xl font-semibold text-[rgb(219,156,153)]">{openExceptionCounts.high}</div>
                    </div>
                    <div className="rounded-md border border-[rgba(184,151,95,0.32)] bg-[rgba(184,151,95,0.1)] px-3 py-3">
                      <div className="text-xs text-stone-300">Medium Severity Open</div>
                      <div className="mt-2 text-2xl font-semibold text-[rgb(219,194,137)]">{openExceptionCounts.medium}</div>
                    </div>
                    <div className="rounded-md border border-[rgba(71,128,159,0.32)] bg-[rgba(71,128,159,0.1)] px-3 py-3">
                      <div className="text-xs text-stone-300">Low Severity Open</div>
                      <div className="mt-2 text-2xl font-semibold text-[rgb(150,193,217)]">{openExceptionCounts.low}</div>
                    </div>
                  </div>
                </section>
              </div>

              <div className="space-y-6">
                <section className={`rounded-lg border p-4 ${decisionIndicator.surface}`}>
                  <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">Decision Indicator</div>
                  <div className={`mt-3 text-2xl font-semibold ${decisionIndicator.tone}`}>{decisionIndicator.label}</div>
                  <p className="mt-2 text-sm text-stone-300">{decisionIndicator.rationale}</p>
                  <dl className="mt-4 grid gap-3 text-xs text-stone-300">
                    <div className="flex items-center justify-between">
                      <dt className="text-stone-500">Open High Exceptions</dt>
                      <dd className="font-medium">{openExceptionCounts.high}</dd>
                    </div>
                    <div className="flex items-center justify-between">
                      <dt className="text-stone-500">Open Conditions Precedent</dt>
                      <dd className="font-medium">{openCpCount}</dd>
                    </div>
                    <div className="flex items-center justify-between">
                      <dt className="text-stone-500">Residual Medium / Low</dt>
                      <dd className="font-medium">{openExceptionCounts.medium + openExceptionCounts.low}</dd>
                    </div>
                  </dl>
                </section>

                <section className={`rounded-lg border p-4 ${approvalReadiness.surface}`}>
                  <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">Approval Readiness</div>
                  <div className={`mt-3 text-2xl font-semibold ${approvalReadiness.tone}`}>{approvalReadiness.label}</div>
                  <p className="mt-2 text-sm text-stone-300">{approvalReadiness.rationale}</p>
                  <dl className="mt-4 grid gap-3 text-xs text-stone-300">
                    <div className="flex items-center justify-between">
                      <dt className="text-stone-500">Open High Severity Exceptions</dt>
                      <dd className="font-medium">{openExceptionCounts.high}</dd>
                    </div>
                    <div className="flex items-center justify-between">
                      <dt className="text-stone-500">Waived Exceptions</dt>
                      <dd className="font-medium">{exceptions?.waived_count ?? waivedExceptionCount}</dd>
                    </div>
                    <div className="flex items-center justify-between">
                      <dt className="text-stone-500">Open Conditions Precedent</dt>
                      <dd className="font-medium">{cps?.open_count ?? openCpCount}</dd>
                    </div>
                    <div className="flex items-center justify-between">
                      <dt className="text-stone-500">Satisfied Conditions Precedent</dt>
                      <dd className="font-medium">{cps?.satisfied_count ?? satisfiedCpCount}</dd>
                    </div>
                  </dl>
                </section>

                <section className="rounded-lg border border-[rgba(82,90,99,0.35)] bg-[rgba(34,39,45,0.75)] p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">Key Issues</div>
                    <span className="text-xs text-stone-500">Top {Math.min(keyIssues.length, 5) || 0}</span>
                  </div>
                  {keyIssues.length === 0 ? (
                    <EmptyState
                      title="No key issues currently open."
                      description="The case has no unresolved exceptions requiring escalation in the executive summary."
                      className="mt-4 min-h-[220px]"
                    />
                  ) : (
                    <div className="mt-4 space-y-3">
                      {keyIssues.map((issue: any) => {
                        const firstEvidence = Array.isArray(issue.evidence_refs) ? issue.evidence_refs[0] : null;
                        return (
                          <div key={issue.id} className={`rounded-lg border p-3 ${getSeverityAccent(issue.severity)}`}>
                            <div className="flex items-start justify-between gap-3">
                              <div className="min-w-0">
                                <div className="font-medium text-stone-100">{issue.title}</div>
                                <p className="mt-1 text-sm text-stone-300 line-clamp-2">
                                  {truncateText(issue.description, 150) || 'No reviewer description recorded.'}
                                </p>
                                <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-400">
                                  {firstEvidence ? (
                                    <span>{formatEvidenceLabel(firstEvidence)}</span>
                                  ) : (
                                    <span>Evidence reference pending</span>
                                  )}
                                  {issue.cp_text ? <span>Condition imposed</span> : null}
                                </div>
                              </div>
                              <span className={`badge ${
                                issue.severity === 'High' ? 'badge-error' :
                                issue.severity === 'Medium' ? 'badge-warning' : 'badge-info'
                              }`}>
                                {issue.severity}
                              </span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </section>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="mb-4">
              <h2 className="text-lg font-semibold">Controls & Evidence Checklist</h2>
              <p className="text-sm text-slate-400">Operational controls, evidence readiness, and approval blockers for the current file.</p>
            </div>
            <CaseControlsCard
              controls={controls}
              onViewDocument={(docId) => focusEvidence(docId)}
              onNavigateToDocuments={navigateToDocuments}
            />
          </div>

          <div className="card">
            <div className="flex justify-between items-center mb-6">
              <div>
                <h2 className="text-lg font-semibold">Activity and Reviewer Signals</h2>
                <p className="text-sm text-stone-400">Exception, CP, verification, and OCR activity over time.</p>
              </div>
              <div className="flex gap-1 rounded-md border border-[rgba(82,90,99,0.45)] bg-[rgba(24,28,32,0.86)] p-1">
                {[7, 30, 90].map((d) => (
                  <button
                    key={d}
                    onClick={() => setInsightsDays(d)}
                    className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all ${
                      insightsDays === d
                        ? 'bg-[rgba(126,133,111,0.92)] text-stone-950'
                        : 'text-stone-500 hover:bg-[rgba(44,50,57,0.92)] hover:text-stone-100'
                    }`}
                  >
                    {d}d
                  </button>
                ))}
              </div>
            </div>

            {insightsLoading && !insights ? (
              <CaseTabSkeleton />
            ) : insights ? (
              <div className="space-y-6">
                {/* KPI Cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="rounded-lg border border-[rgba(82,90,99,0.38)] bg-[rgba(34,39,45,0.82)] p-4">
                    <p className="text-sm text-stone-400">Open High</p>
                    <p className="text-2xl font-semibold tracking-tight text-[rgb(219,156,153)]">{insights.summary.open_exceptions_high}</p>
                  </div>
                  <div className="rounded-lg border border-[rgba(82,90,99,0.38)] bg-[rgba(34,39,45,0.82)] p-4">
                    <p className="text-sm text-stone-400">Open Medium</p>
                    <p className="text-2xl font-semibold tracking-tight text-[rgb(219,194,137)]">{insights.summary.open_exceptions_medium}</p>
                  </div>
                  <div className="rounded-lg border border-[rgba(82,90,99,0.38)] bg-[rgba(34,39,45,0.82)] p-4">
                    <p className="text-sm text-stone-400">CP Completion</p>
                    <p className="text-2xl font-semibold tracking-tight text-[rgb(194,200,185)]">{insights.summary.cp_completion_pct}%</p>
                  </div>
                  <div className="rounded-lg border border-[rgba(82,90,99,0.38)] bg-[rgba(34,39,45,0.82)] p-4">
                    <p className="text-sm text-stone-400">Verification</p>
                    <p className="text-2xl font-semibold tracking-tight text-stone-100">{insights.summary.verification_completion_pct}%</p>
                  </div>
                </div>

                {/* Activity Summary */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="rounded-lg border border-[rgba(82,90,99,0.32)] bg-[rgba(34,39,45,0.62)] p-3">
                    <p className="text-xs text-stone-500">Open Low</p>
                    <p className="text-lg font-semibold text-[rgb(187,205,189)]">{insights.summary.open_exceptions_low}</p>
                  </div>
                  <div className="rounded-lg border border-[rgba(82,90,99,0.32)] bg-[rgba(34,39,45,0.62)] p-3">
                    <p className="text-xs text-stone-500">Exports</p>
                    <p className="text-lg font-semibold">{insights.summary.exports_generated}</p>
                  </div>
                  <div className="rounded-lg border border-[rgba(82,90,99,0.32)] bg-[rgba(34,39,45,0.62)] p-3">
                    <p className="text-xs text-stone-500">Last Rule Run</p>
                    <p className="text-sm">{insights.summary.last_rule_run_at ? new Date(insights.summary.last_rule_run_at).toLocaleDateString() : '—'}</p>
                  </div>
                  <div className="rounded-lg border border-[rgba(82,90,99,0.32)] bg-[rgba(34,39,45,0.62)] p-3">
                    <p className="text-xs text-stone-500">Last OCR</p>
                    <p className="text-sm">{insights.summary.last_ocr_at ? new Date(insights.summary.last_ocr_at).toLocaleDateString() : '—'}</p>
                  </div>
                </div>

                {/* Activity Timeline */}
                <div>
                  <h3 className="mb-4 text-base font-semibold">Activity Timeline ({insightsDays} days)</h3>
                  <div className="overflow-x-auto rounded-lg border border-[rgba(82,90,99,0.38)] bg-[rgba(34,39,45,0.82)] p-4">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-stone-500">
                          <th className="pb-2">Date</th>
                          <th className="pb-2">Exc. Opened</th>
                          <th className="pb-2">Exc. Resolved</th>
                          <th className="pb-2">CPs Satisfied</th>
                          <th className="pb-2">Verified</th>
                          <th className="pb-2">Exports</th>
                          <th className="pb-2">Rule Runs</th>
                          <th className="pb-2">OCR Pages</th>
                        </tr>
                      </thead>
                      <tbody>
                        {insights.timeseries.filter(t => 
                          t.exceptions_opened > 0 || t.exceptions_resolved > 0 || 
                          t.cps_satisfied > 0 || t.verifications_verified > 0 ||
                          t.exports_generated > 0 || t.rule_evaluations > 0 || t.ocr_pages_done > 0
                        ).slice(-10).map((t) => (
                          <tr key={t.date} className="border-t border-[rgba(82,90,99,0.38)]">
                            <td className="py-2">{new Date(t.date).toLocaleDateString()}</td>
                            <td className="py-2">{t.exceptions_opened || '—'}</td>
                            <td className="py-2">{t.exceptions_resolved || '—'}</td>
                            <td className="py-2">{t.cps_satisfied || '—'}</td>
                            <td className="py-2">{t.verifications_verified || '—'}</td>
                            <td className="py-2">{t.exports_generated || '—'}</td>
                            <td className="py-2">{t.rule_evaluations || '—'}</td>
                            <td className="py-2">{t.ocr_pages_done || '—'}</td>
                          </tr>
                        ))}
                        {insights.timeseries.filter(t => 
                          t.exceptions_opened > 0 || t.exceptions_resolved > 0 || 
                          t.cps_satisfied > 0 || t.verifications_verified > 0 ||
                          t.exports_generated > 0 || t.rule_evaluations > 0 || t.ocr_pages_done > 0
                        ).length === 0 && (
                          <tr>
                            <td colSpan={8} className="py-8 text-center text-stone-400">
                              No activity in this time range
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            ) : (
              <EmptyState
                title="Summary data unavailable"
                description="Activity metrics could not be loaded for this case. Core reviewer actions remain available in the other tabs."
              />
            )}
          </div>
        </div>
      )}
    </div>
    </>
  );
}

// ============================================================
// VerificationCard Component
// ============================================================

function VerificationCard({
  verification,
  caseId,
  documents,
  onUpdate,
  setError,
}: {
  verification: any;
  caseId: string;
  documents: any[];
  onUpdate: () => void;
  setError: (msg: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [keys, setKeys] = useState<Record<string, string>>(verification.keys_json || {});
  const [notes, setNotes] = useState(verification.notes || '');
  const [newKeyName, setNewKeyName] = useState('');
  const [newKeyValue, setNewKeyValue] = useState('');
  const [selectedDocId, setSelectedDocId] = useState('');
  const [failedNotes, setFailedNotes] = useState('');
  const [showFailedInput, setShowFailedInput] = useState(false);
  const [loading, setLoading] = useState(false);

  const typeLabel = verification.verification_type === 'e_stamp' ? 'e-Stamp' : 'Registry / ROD';
  const statusColor = verification.status === 'Verified' ? 'badge-success' : 
                       verification.status === 'Failed' ? 'badge-error' : 'badge-warning';

  const handleSaveKeys = async () => {
    setLoading(true);
    try {
      await updateVerificationKeys(caseId, verification.verification_type, keys, notes);
      setEditing(false);
      onUpdate();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAddKey = () => {
    if (newKeyName.trim()) {
      setKeys({ ...keys, [newKeyName.trim()]: newKeyValue });
      setNewKeyName('');
      setNewKeyValue('');
    }
  };

  const handleRemoveKey = (key: string) => {
    const updated = { ...keys };
    delete updated[key];
    setKeys(updated);
  };

  const handleOpenPortal = async () => {
    try {
      const result = await openVerificationPortal(caseId, verification.verification_type);
      window.open(result.url, '_blank');
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleAttachEvidence = async () => {
    if (!selectedDocId) {
      setError('Please select a document to attach');
      return;
    }
    setLoading(true);
    try {
      await attachVerificationEvidence(caseId, verification.verification_type, selectedDocId);
      setSelectedDocId('');
      onUpdate();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleMarkVerified = async () => {
    setLoading(true);
    try {
      await markVerificationVerified(caseId, verification.verification_type);
      onUpdate();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleMarkFailed = async () => {
    if (!failedNotes.trim()) {
      setError('Please provide notes explaining why verification failed');
      return;
    }
    setLoading(true);
    try {
      await markVerificationFailed(caseId, verification.verification_type, failedNotes);
      setShowFailedInput(false);
      setFailedNotes('');
      onUpdate();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadEvidence = async (docId: string) => {
    try {
      const result = await getDocumentDownloadUrl(docId);
      window.open(result.url, '_blank');
    } catch (e: any) {
      setError(e.message);
    }
  };

  const hasEvidence = verification.evidence_refs && verification.evidence_refs.length > 0;

  return (
    <div className="card">
      <div className="flex justify-between items-start mb-4">
        <h3 className="text-lg font-semibold">{typeLabel}</h3>
        <span className={`badge ${statusColor}`}>{verification.status}</span>
      </div>

      {/* Keys Section */}
      <div className="mb-4">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm text-stone-400">Verification Keys</span>
          {!editing && verification.status === 'Pending' && (
            <button 
              onClick={() => setEditing(true)} 
              className="text-sm text-[rgb(194,200,185)] transition-colors hover:text-stone-100"
            >
              Edit
            </button>
          )}
        </div>
        
        {editing ? (
          <div className="space-y-2">
            {/* ROD-specific fields */}
            {verification.verification_type === 'registry_rod' && (
              <>
                <div className="flex gap-2 items-center">
                  <label className="w-32 text-sm text-stone-400">Registry Office:</label>
                  <input
                    type="text"
                    value={keys.registry_office || ''}
                    onChange={(e) => setKeys({ ...keys, registry_office: e.target.value })}
                    className="input flex-1 text-sm"
                    placeholder="e.g., LDA Lahore"
                  />
                </div>
                <div className="flex gap-2 items-center">
                  <label className="w-32 text-sm text-stone-400">Registry Number:</label>
                  <input
                    type="text"
                    value={keys.registry_number || ''}
                    onChange={(e) => setKeys({ ...keys, registry_number: e.target.value })}
                    className="input flex-1 text-sm"
                    placeholder="e.g., 1234/2023"
                  />
                </div>
                <div className="flex gap-2 items-center">
                  <label className="w-32 text-sm text-stone-400">Instrument:</label>
                  <input
                    type="text"
                    value={keys.instrument || ''}
                    onChange={(e) => setKeys({ ...keys, instrument: e.target.value })}
                    className="input flex-1 text-sm"
                    placeholder="e.g., Sale Deed, Transfer Deed"
                  />
                </div>
                <div className="flex gap-2 items-center">
                  <label className="w-32 text-sm text-stone-400">Search Terms:</label>
                  <input
                    type="text"
                    value={keys.search_terms || ''}
                    onChange={(e) => setKeys({ ...keys, search_terms: e.target.value })}
                    className="input flex-1 text-sm"
                    placeholder="What you searched for"
                  />
                </div>
                <div className="my-2 border-t border-[rgba(82,90,99,0.4)]"></div>
              </>
            )}
            {Object.entries(keys).filter(([key]) => 
              verification.verification_type !== 'registry_rod' || 
              !['registry_office', 'registry_number', 'instrument', 'search_terms'].includes(key)
            ).map(([key, value]) => (
              <div key={key} className="flex gap-2 items-center">
                <input
                  type="text"
                  value={key}
                  disabled
                  className="input flex-1 bg-[rgba(44,50,57,0.96)] text-sm"
                />
                <input
                  type="text"
                  value={value}
                  onChange={(e) => setKeys({ ...keys, [key]: e.target.value })}
                  className="input flex-1 text-sm"
                />
                <button
                  onClick={() => handleRemoveKey(key)}
                  className="px-2 text-[rgb(219,156,153)] transition-colors hover:text-stone-100"
                >
                  ×
                </button>
              </div>
            ))}
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Key name..."
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                className="input flex-1 text-sm"
              />
              <input
                type="text"
                placeholder="Value..."
                value={newKeyValue}
                onChange={(e) => setNewKeyValue(e.target.value)}
                className="input flex-1 text-sm"
              />
              <Button variant="secondary" size="sm" onClick={handleAddKey}>
                Add
              </Button>
            </div>
            <textarea
              placeholder="Notes..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="input w-full text-sm"
              rows={2}
            />
            <div className="flex gap-2">
              <Button onClick={handleSaveKeys} size="sm" disabled={loading} loading={loading}>
                {loading ? 'Saving...' : 'Save'}
              </Button>
              <Button 
                variant="secondary"
                size="sm"
                onClick={() => { setEditing(false); setKeys(verification.keys_json || {}); }}
              >
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <div className="rounded-md border border-[rgba(82,90,99,0.35)] bg-[rgba(34,39,45,0.82)] p-3">
            {Object.keys(keys).length === 0 ? (
              <p className="text-sm text-stone-400">No verification keys set. Click Edit to add.</p>
            ) : (
              <div className="space-y-1">
                {Object.entries(keys).map(([key, value]) => (
                  <div key={key} className="flex justify-between text-sm">
                    <span className="text-stone-400">{key}:</span>
                    <span className="font-mono">{value}</span>
                  </div>
                ))}
              </div>
            )}
            {verification.notes && (
              <p className="mt-2 border-t border-[rgba(82,90,99,0.38)] pt-2 text-sm text-stone-400">
                {verification.notes}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Portal Button */}
      <Button
        variant="secondary"
        className="mb-4 w-full"
        onClick={handleOpenPortal}
      >
        Open Verification Portal ↗
      </Button>

      {/* Evidence Section */}
      <div className="mb-4">
        <span className="mb-2 block text-sm text-stone-400">Evidence</span>
        
        {hasEvidence ? (
          <ul className="space-y-2 mb-3">
            {verification.evidence_refs.map((ref: any) => {
              const doc = documents.find((d) => d.id === ref.document_id);
              return (
                <li key={ref.id} className="flex items-center justify-between rounded-md border border-[rgba(82,90,99,0.35)] bg-[rgba(34,39,45,0.82)] p-2 text-sm">
                  <span>{doc?.original_filename || ref.document_id.substring(0, 8)}</span>
                  <button 
                    onClick={() => handleDownloadEvidence(ref.document_id)}
                    className="text-sm text-[rgb(194,200,185)] transition-colors hover:text-stone-100"
                  >
                    View
                  </button>
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="mb-3 text-sm text-stone-400">No evidence attached yet.</p>
        )}

        {verification.status === 'Pending' && (
          <div className="flex gap-2">
            <select
              value={selectedDocId}
              onChange={(e) => setSelectedDocId(e.target.value)}
              className="input flex-1 text-sm"
            >
              <option value="">Select document...</option>
              {documents.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.original_filename}
                </option>
              ))}
            </select>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleAttachEvidence}
              disabled={loading || !selectedDocId}
              loading={loading}
            >
              Attach
            </Button>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      {verification.status === 'Pending' && (
        <div className="space-y-2 border-t border-[rgba(82,90,99,0.38)] pt-4">
          <Button
            onClick={handleMarkVerified}
            className="w-full"
            disabled={loading || !hasEvidence}
            loading={loading}
            title={!hasEvidence ? 'Attach evidence first' : ''}
          >
            {loading ? 'Processing...' : 'Mark as Verified'}
          </Button>
          
          {showFailedInput ? (
            <div className="space-y-2">
              <textarea
                placeholder="Reason for failure..."
                value={failedNotes}
                onChange={(e) => setFailedNotes(e.target.value)}
                className="input w-full text-sm"
                rows={2}
              />
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  onClick={handleMarkFailed}
                  className="flex-1"
                  disabled={loading}
                  loading={loading}
                >
                  Confirm Failed
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => { setShowFailedInput(false); setFailedNotes(''); }}
                  className="flex-1"
                >
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <Button
              variant="secondary"
              onClick={() => setShowFailedInput(true)}
              className="w-full"
            >
              Mark as Failed
            </Button>
          )}
        </div>
      )}

      {/* Verified/Failed info */}
      {verification.status === 'Verified' && verification.verified_at && (
        <p className="mt-4 text-sm text-[rgb(187,205,189)]">
          ✓ Verified on {new Date(verification.verified_at).toLocaleString()}
        </p>
      )}
      {verification.status === 'Failed' && verification.notes && (
        <p className="mt-4 text-sm text-[rgb(219,156,153)]">
          ✗ Failed: {verification.notes}
        </p>
      )}
      </div>
  );
}


