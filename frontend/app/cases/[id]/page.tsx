'use client';

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import {
  getToken,
  getCase,
  listDocuments,
  uploadDocument,
  getDocument,
  getDocumentDownloadUrl,
  enqueueOcr,
  getOcrStatus,
  extractDossier,
  getDossier,
  updateDossierField,
  autofillDossier,
  evaluateCase,
  listExceptions,
  listCPs,
  resolveException,
  waiveException,
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
import { SetPageChrome } from '@/components/layout/set-page-chrome';

type Tab = 'documents' | 'dossier' | 'ocr-extractions' | 'verification' | 'exceptions' | 'drafts' | 'exports' | 'insights';

export default function CaseDetailPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const caseId = params.id as string;

  const [caseData, setCaseData] = useState<any>(null);
  const [documents, setDocuments] = useState<any[]>([]);
  const [controls, setControls] = useState<CaseControlsResponse | null>(null);
  const [dossier, setDossier] = useState<any>(null);
  const [exceptions, setExceptions] = useState<any>(null);
  const [cps, setCps] = useState<any>(null);
  const [exports, setExports] = useState<any>(null);
  const [verifications, setVerifications] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<Tab>('documents');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [uploading, setUploading] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [generating, setGenerating] = useState<string | null>(null);
  const [autofillOverwrite, setAutofillOverwrite] = useState(false);
  const [autofilling, setAutofilling] = useState(false);
  const [autofillResult, setAutofillResult] = useState<any>(null);
  const [selectedDoc, setSelectedDoc] = useState<any>(null);
  const [focusedDocId, setFocusedDocId] = useState<string | null>(null);
  const [focusedPage, setFocusedPage] = useState<number | null>(null);
  const [ocrStatus, setOcrStatus] = useState<any>(null);
  const [selectedExc, setSelectedExc] = useState<any>(null);
  const [waiverReason, setWaiverReason] = useState('');
  const [userRole, setUserRole] = useState('Reviewer');
  const [generatedDrafts, setGeneratedDrafts] = useState<any[]>([]);
  const [insights, setInsights] = useState<CaseInsightsResponse | null>(null);
  const [insightsDays, setInsightsDays] = useState(30);
  const [insightsLoading, setInsightsLoading] = useState(false);
  const [initialLoadComplete, setInitialLoadComplete] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const loadedTabsRef = useRef<Set<string>>(new Set());
  const checkAuthAndLoadRef = useRef<null | (() => void | Promise<void>)>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const focusedPageButtonRef = useRef<HTMLButtonElement | null>(null);

  // Memoize caseId to prevent unnecessary re-renders
  const memoizedCaseId = useMemo(() => caseId, [caseId]);

  const loadCase = useCallback(async () => {
    // Check if request was aborted
    if (abortControllerRef.current?.signal.aborted) {
      return;
    }
    
    setLoading(true);
    setError(''); // Clear previous errors
    try {
      // Load case, documents, and controls in parallel (single source of truth)
      const [c, docs, ctrls] = await Promise.all([
        getCase(memoizedCaseId),
        listDocuments(memoizedCaseId),
        getCaseControls(memoizedCaseId),
      ]);
      
      // Check if request was aborted before setting state
      if (abortControllerRef.current?.signal.aborted) {
        return;
      }
      
      setCaseData(c);
      setDocuments(docs);
      setControls(ctrls);
      setInitialLoadComplete(true); // Mark initial load as complete
    } catch (e: any) {
      // Ignore abort errors
      if (e.name === 'AbortError') {
        return;
      }
      
      // Handle ApiError with structured details
      if (e instanceof ApiError) {
        setError(e.detail || `Failed to load case: ${e.message}`);
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
    const token = await getToken();
    if (!token) {
      router.push('/');
      return;
    }
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      setUserRole(payload.role || 'Reviewer');
    } catch {}
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

  // Separate effect for URL query params (only runs when searchParams change, after documents are loaded)
  useEffect(() => {
    if (!initialLoadComplete || documents.length === 0) return;
    
    // P14: Handle URL query params for document/page navigation
    // Support both old params (docId, page) and new params (focusDocId, focusPage, focusCandidateId)
    const tabParam = searchParams.get('tab');
    const docIdParam = searchParams.get('docId') || searchParams.get('focusDocId');
    const pageParam = searchParams.get('page') || searchParams.get('focusPage');
    const candidateIdParam = searchParams.get('focusCandidateId');
    
    // If focusDocId exists, ensure we're on documents tab
    if (searchParams.get('focusDocId')) {
      setActiveTab('documents');
    } else if (tabParam) {
      setActiveTab(tabParam as Tab);
    }
    
    if (docIdParam) {
      const doc = documents.find(d => d.id === docIdParam);
      if (doc) {
        setSelectedDoc(doc);
        setFocusedDocId(docIdParam);
        if (pageParam) {
          const pageNum = parseInt(pageParam);
          if (!isNaN(pageNum) && pageNum > 0) {
            setFocusedPage(pageNum);
          } else {
            setFocusedPage(null);
          }
        } else {
          setFocusedPage(null);
        }
      }
    } else {
      setFocusedDocId(null);
      setFocusedPage(null);
    }
  }, [searchParams, documents, initialLoadComplete]); // Safe: only runs after initial load

  // Scroll focused page button into view when focus changes
  useEffect(() => {
    if (!focusedPage || !focusedDocId || !selectedDoc || focusedDocId !== selectedDoc.id) return;
    if (typeof window === 'undefined') return; // SSR guard
    
    // Wait a bit for DOM to render
    const timeoutId = setTimeout(() => {
      const button = document.querySelector(`button[data-page-number="${focusedPage}"]`) as HTMLButtonElement;
      if (button) {
        button.scrollIntoView({ block: 'center', behavior: 'smooth' });
        focusedPageButtonRef.current = button;
      }
    }, 100);
    
    return () => clearTimeout(timeoutId);
  }, [focusedPage, focusedDocId, selectedDoc, activeTab]);

  const loadDossier = useCallback(async () => {
    try {
      const d = await getDossier(memoizedCaseId);
      setDossier(d);
    } catch (e: any) {
      console.error('Failed to load dossier:', e);
    }
  }, [memoizedCaseId]);

  const loadExceptionsAndCPs = useCallback(async () => {
    try {
      const [exc, cp] = await Promise.all([
        listExceptions(memoizedCaseId),
        listCPs(memoizedCaseId),
      ]);
      setExceptions(exc);
      setCps(cp);
    } catch (e: any) {
      console.error('Failed to load exceptions:', e);
    }
  }, [memoizedCaseId]);

  const loadExports = useCallback(async () => {
    try {
      const exp = await listExports(memoizedCaseId);
      setExports(exp);
    } catch (e: any) {
      console.error('Failed to load exports:', e);
    }
  }, [memoizedCaseId]);

  const loadVerifications = useCallback(async () => {
    try {
      const v = await listVerifications(memoizedCaseId);
      setVerifications(v);
    } catch (e: any) {
      console.error('Failed to load verifications:', e);
    }
  }, [memoizedCaseId]);

  const loadInsights = useCallback(async (days: number) => {
    setInsightsLoading(true);
    try {
      const data = await getCaseInsights(memoizedCaseId, days);
      setInsights(data);
    } catch (e: any) {
      console.error('Failed to load insights:', e);
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
    } else if (activeTab === 'exceptions') {
      loadExceptionsAndCPs();
      loadedTabsRef.current.add(tabKey);
    } else if (activeTab === 'drafts' || activeTab === 'exports') {
      loadExports();
      loadedTabsRef.current.add(tabKey);
    } else if (activeTab === 'insights') {
      loadInsights(insightsDays);
      loadedTabsRef.current.add(tabKey);
    }
  }, [activeTab, memoizedCaseId, insightsDays, initialLoadComplete, loadDossier, loadVerifications, loadExceptionsAndCPs, loadExports, loadInsights]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const allowedTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg'];
    if (!allowedTypes.includes(file.type)) {
      setError('Only PDF and image files (PNG, JPG) are allowed');
      // Clear the input value so user can try again
      e.target.value = '';
      return;
    }

    setUploading(true);
    setError('');
    try {
      await uploadDocument(caseId, file);
      const docs = await listDocuments(caseId);
      setDocuments(docs);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setUploading(false);
      // Clear the input value after upload (allows re-uploading the same file)
      e.target.value = '';
    }
  };

  const handleRunOcr = async (docId: string) => {
    try {
      await enqueueOcr(docId);
      setError('');
      pollOcrStatus(docId);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const pollOcrStatus = async (docId: string) => {
    try {
      const status = await getOcrStatus(docId);
      setOcrStatus(status);
      const pending = (status.status_counts.NotStarted || 0) + 
                      (status.status_counts.Queued || 0) + 
                      (status.status_counts.Processing || 0);
      if (pending > 0) {
        setTimeout(() => pollOcrStatus(docId), 2000);
      }
    } catch (e: any) {
      console.error('OCR status poll failed:', e);
    }
  };

  const handleViewDoc = async (docId: string) => {
    try {
      const doc = await getDocument(docId);
      setSelectedDoc(doc);
      const status = await getOcrStatus(docId);
      setOcrStatus(status);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const focusEvidence = useCallback((docId: string, pageNum?: number, candidateId?: string) => {
    // Switch to Documents tab
    setActiveTab('documents');
    
    // Set focus state
    setFocusedDocId(docId);
    if (pageNum != null) {
      setFocusedPage(pageNum);
    } else {
      setFocusedPage(null);
    }
    
    // Select the document if it exists in the documents list
    const found = documents.find(d => d.id === docId);
    if (found) {
      setSelectedDoc(found);
    }
    
    // Update URL query params without full reload
    // Use new param names (focusDocId, focusPage, focusCandidateId) for deep linking
    const params = new URLSearchParams();
    params.set('tab', 'documents');
    params.set('focusDocId', docId);
    if (pageNum != null && pageNum > 0) {
      params.set('focusPage', String(pageNum));
    }
    if (candidateId) {
      params.set('focusCandidateId', candidateId);
    }
    router.push(`/cases/${caseId}?${params.toString()}`);
  }, [documents, router, caseId]);

  const handleExtract = useCallback(async () => {
    try {
      // Extract dossier (triggers extraction process)
      await extractDossier(memoizedCaseId);
      // Autofill to create OCR extraction candidates
      await autofillDossier(memoizedCaseId, false);
      await loadDossier();
      // Switch to OCR Extractions tab to show candidates
      setActiveTab('ocr-extractions');
    } catch (e: any) {
      // Handle ApiError with structured details
      if (e instanceof ApiError) {
        setError(e.detail || `Failed to extract dossier: ${e.message}`);
      } else {
        setError(e.message || 'Failed to extract dossier');
      }
    }
  }, [memoizedCaseId, loadDossier]);

  const handleAutofill = async () => {
    setAutofilling(true);
    setAutofillResult(null);
    try {
      const result = await autofillDossier(caseId, autofillOverwrite);
      setAutofillResult(result);
      await loadDossier(); // Reload dossier to show updated fields
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

  const handleConfirmField = async (fieldKey: string) => {
    try {
      await updateDossierField(caseId, fieldKey, undefined, true);
      await loadDossier();
    } catch (e: any) {
      setError(e.message);
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

  const handleResolve = async (excId: string) => {
    try {
      await resolveException(excId);
      await loadExceptionsAndCPs();
      setSelectedExc(null);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleWaive = async (excId: string) => {
    if (!waiverReason.trim()) {
      setError('Waiver reason is required');
      return;
    }
    try {
      await waiveException(excId, waiverReason);
      await loadExceptionsAndCPs();
      setSelectedExc(null);
      setWaiverReason('');
    } catch (e: any) {
      setError(e.message);
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

  const canWaive = userRole === 'Admin' || userRole === 'Approver';
  const canResolve = userRole === 'Admin' || userRole === 'Approver' || userRole === 'Reviewer';

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-slate-400">Loading...</p>
      </div>
    );
  }

  // Prepare autofill action for header (only show in dossier tab)
  const autofillAction = activeTab === 'dossier' ? (
    <button
      onClick={handleAutofill}
      disabled={autofilling}
      className="btn btn-primary"
    >
      {autofilling ? 'Running Autofill...' : 'Run Autofill'}
    </button>
  ) : null

  return (
    <>
      <SetPageChrome
        title={caseData?.title || 'Case'}
        breadcrumbs={[
          { label: 'Cases', href: '/' },
          { label: caseData?.title || 'Case' }
        ]}
        actions={autofillAction}
      />
      <div className="min-h-screen p-6">
        <header className="flex justify-between items-center mb-6">
          <div>
            <a href="/" className="text-cyan-400 hover:text-cyan-300 text-sm">← Back to Cases</a>
            <h1 className="text-2xl font-bold mt-2">{caseData?.title || 'Case'}</h1>
          </div>
        </header>

      {error && (
        <div className="bg-red-500/20 border border-red-500 text-red-400 p-3 rounded mb-4">
          {error}
          <button onClick={() => setError('')} className="float-right">×</button>
        </div>
      )}

      {/* Controls & Evidence Checklist */}
      <div className="mb-6">
        <CaseControlsCard
          caseId={caseId}
          controls={controls}
          onViewDocument={(docId) => {
            // Switch to documents tab and select the document
            setActiveTab('documents');
            // Find and select the document
            const doc = documents.find(d => d.id === docId);
            if (doc) {
              handleViewDoc(docId);
            }
          }}
        />
      </div>

      {/* Tabs */}
      <div className="flex gap-4 mb-6 border-b border-slate-700 overflow-x-auto">
        <button
          onClick={() => setActiveTab('documents')}
          className={`pb-3 px-1 whitespace-nowrap ${activeTab === 'documents' ? 'text-cyan-400 border-b-2 border-cyan-400' : 'text-slate-400'}`}
        >
          Documents
        </button>
          <button
            onClick={() => setActiveTab('dossier')}
            className={`pb-3 px-1 whitespace-nowrap ${activeTab === 'dossier' ? 'text-cyan-400 border-b-2 border-cyan-400' : 'text-slate-400'}`}
          >
            Dossier
          </button>
          <button
            onClick={() => setActiveTab('ocr-extractions')}
            className={`pb-3 px-1 whitespace-nowrap ${activeTab === 'ocr-extractions' ? 'text-cyan-400 border-b-2 border-cyan-400' : 'text-slate-400'}`}
          >
            OCR Extractions
          </button>
          <button
            onClick={() => setActiveTab('verification')}
            className={`pb-3 px-1 whitespace-nowrap ${activeTab === 'verification' ? 'text-cyan-400 border-b-2 border-cyan-400' : 'text-slate-400'}`}
          >
            Verification
          </button>
        <button
          onClick={() => setActiveTab('exceptions')}
          className={`pb-3 px-1 whitespace-nowrap ${activeTab === 'exceptions' ? 'text-cyan-400 border-b-2 border-cyan-400' : 'text-slate-400'}`}
        >
          Exceptions & CPs
          {exceptions && exceptions.open_count > 0 && (
            <span className="ml-2 badge badge-error">{exceptions.open_count}</span>
          )}
        </button>
        <button
          onClick={() => setActiveTab('drafts')}
          className={`pb-3 px-1 whitespace-nowrap ${activeTab === 'drafts' ? 'text-cyan-400 border-b-2 border-cyan-400' : 'text-slate-400'}`}
        >
          Drafts
        </button>
        <button
          onClick={() => setActiveTab('exports')}
          className={`pb-3 px-1 whitespace-nowrap ${activeTab === 'exports' ? 'text-cyan-400 border-b-2 border-cyan-400' : 'text-slate-400'}`}
        >
          Export
        </button>
        <button
          onClick={() => setActiveTab('insights')}
          className={`pb-3 px-1 whitespace-nowrap ${activeTab === 'insights' ? 'text-cyan-400 border-b-2 border-cyan-400' : 'text-slate-400'}`}
        >
          Insights
        </button>
      </div>

      {/* Documents Tab */}
      {activeTab === 'documents' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="card">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold">Documents</h2>
              <div className="relative">
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={uploading}
                  data-testid="documents-upload-button"
                  onClick={() => {
                    // Deterministic: always triggers the file picker
                    fileInputRef.current?.click();
                  }}
                >
                  {uploading ? "Uploading..." : "Upload File"}
                </button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="application/pdf,image/png,image/jpeg,image/jpg"
                  onChange={handleFileUpload}
                  data-testid="documents-upload-input"
                  style={{ position: 'absolute', width: 0, height: 0, opacity: 0, overflow: 'hidden' }}
                  tabIndex={-1}
                />
              </div>
            </div>

            {documents.length === 0 ? (
              <p className="text-slate-400">No documents uploaded yet.</p>
            ) : (
              <ul className="space-y-2">
                {documents.map((doc) => (
                  <li
                    key={doc.id}
                    className={`p-3 rounded cursor-pointer transition-colors ${
                      selectedDoc?.id === doc.id ? 'bg-cyan-500/20 border border-cyan-500' : 'bg-slate-700 hover:bg-slate-600'
                    }`}
                    onClick={() => handleViewDoc(doc.id)}
                  >
                    <div className="flex justify-between items-center">
                      <div className="flex-1">
                        <p className="font-medium truncate">{doc.original_filename}</p>
                        <p className="text-sm text-slate-400">
                          {doc.page_count || '?'} pages • {doc.status}
                        </p>
                      </div>
                      <div className="flex gap-2 items-center">
                        {doc.status === 'Split' && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleRunOcr(doc.id);
                            }}
                            className="btn btn-sm btn-primary"
                            title="Run OCR for this document"
                          >
                            Run OCR
                          </button>
                        )}
                        <span className={`badge ${
                          doc.status === 'Split' ? 'badge-success' : 
                          doc.status === 'Failed' ? 'badge-error' : 'badge-warning'
                        }`}>
                          {doc.status}
                        </span>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="card">
            {selectedDoc ? (
              <>
                <h2 className="text-lg font-semibold mb-4">{selectedDoc.original_filename}</h2>
                {focusedPage != null && focusedDocId === selectedDoc.id && (
                  <div className="mb-4 p-3 bg-cyan-500/20 border border-cyan-500 rounded-lg">
                    <p className="text-cyan-400 font-medium text-sm">
                      Evidence focus: Page {focusedPage}
                    </p>
                  </div>
                )}
                <div className="space-y-4">
                  <div>
                    <span className="text-slate-400 text-sm">Status: </span>
                    <span className={`badge ${
                      selectedDoc.status === 'Split' ? 'badge-success' : 
                      selectedDoc.status === 'Failed' ? 'badge-error' : 'badge-warning'
                    }`}>
                      {selectedDoc.status}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 text-sm">Pages: </span>
                    <span>{selectedDoc.page_count || 0}</span>
                  </div>
                  {selectedDoc.page_count && selectedDoc.page_count > 0 && (
                    <div className="space-y-2">
                      <span className="text-slate-400 text-sm block">Page List:</span>
                      <div className="flex flex-wrap gap-2">
                        {Array.from({ length: selectedDoc.page_count }, (_, i) => i + 1).map((pageNum) => {
                          const isFocused = focusedPage === pageNum && focusedDocId === selectedDoc.id;
                          return (
                            <button
                              key={pageNum}
                              ref={isFocused ? focusedPageButtonRef : null}
                              data-page-number={pageNum}
                              onClick={() => {
                                setFocusedPage(pageNum);
                                const params = new URLSearchParams(searchParams.toString());
                                // Use focusPage for consistency with deep linking
                                params.set('focusPage', String(pageNum));
                                params.set('focusDocId', selectedDoc.id);
                                router.replace(`?${params.toString()}`, { scroll: false });
                              }}
                              className={`px-3 py-1 rounded text-sm transition-colors ${
                                isFocused
                                  ? 'bg-cyan-500 text-white border-2 border-cyan-400 ring-2 ring-cyan-400'
                                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                              }`}
                            >
                              {pageNum}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {selectedDoc.status === 'Split' && (
                    <button onClick={() => handleRunOcr(selectedDoc.id)} className="btn btn-primary">
                      Run OCR
                    </button>
                  )}

                  {ocrStatus && (
                    <div className="mt-4">
                      <h3 className="font-medium mb-2">OCR Status</h3>
                      <div className="flex gap-2 mb-3 flex-wrap">
                        {Object.entries(ocrStatus.status_counts).map(([status, count]) => (
                          <span key={status} className={`badge ${
                            status === 'Done' ? 'badge-success' :
                            status === 'Failed' ? 'badge-error' :
                            status === 'Processing' ? 'badge-info' : 'badge-neutral'
                          }`}>
                            {status}: {count as number}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <p className="text-slate-400">Select a document to view details.</p>
            )}
          </div>
        </div>
      )}

      {/* Dossier Tab - P14: Use DossierFieldsEditor */}
      {activeTab === 'dossier' && (
        <div className="space-y-6">
          {/* Autofill Card */}
          <div className="card bg-slate-800/50 border border-slate-700">
            <h3 className="text-lg font-semibold mb-3">Autofill from OCR</h3>
            <p className="text-sm text-slate-400 mb-4">
              Extract key dossier fields (plot, block, phase, scheme, district, etc.) from OCR text across all documents.
            </p>
            <div className="flex items-center gap-4 mb-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={autofillOverwrite}
                  onChange={(e) => setAutofillOverwrite(e.target.checked)}
                  className="checkbox"
                />
                <span className="text-sm text-slate-300">Overwrite existing values</span>
              </label>
            </div>
            <button
              onClick={async () => {
                try {
                  await handleAutofill();
                  alert('Autofill completed. Review OCR Extractions tab for candidates.');
                  setActiveTab('ocr-extractions');
                } catch (e: any) {
                  alert('Autofill failed: ' + (e.message || 'Unknown error'));
                }
              }}
              disabled={autofilling}
              className="btn btn-primary"
            >
              {autofilling ? 'Running Autofill...' : 'Run Autofill'}
            </button>
            {autofillResult && (
              <div className="mt-4 p-4 bg-slate-700 rounded">
                <h4 className="font-medium mb-2">Autofill Results</h4>
                <div className="text-sm space-y-1">
                  <p className="text-green-400">✅ Updated: {autofillResult.updated_fields.length} fields</p>
                  {autofillResult.skipped_fields.length > 0 && (
                    <p className="text-yellow-400">⚠️ Skipped: {autofillResult.skipped_fields.length} fields (already set)</p>
                  )}
                  {autofillResult.errors.length > 0 && (
                    <p className="text-red-400">❌ Errors: {autofillResult.errors.join(', ')}</p>
                  )}
                </div>
                {autofillResult.extracted.length > 0 && (
                  <div className="mt-3">
                    <p className="text-xs text-slate-400 mb-2">Extracted Fields:</p>
                    <div className="space-y-1 max-h-40 overflow-y-auto">
                      {autofillResult.extracted.map((ef: any, idx: number) => (
                        <div key={idx} className="text-xs bg-slate-600 p-2 rounded">
                          <span className="font-medium">{ef.field_path}:</span> {ef.value} 
                          <span className="text-slate-400 ml-2">({Math.round(ef.confidence * 100)}% confidence)</span>
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
        <div className="space-y-6">
          <div className="card">
            <h2 className="text-lg font-semibold mb-4">Assisted Verification</h2>
            <p className="text-slate-400 mb-6">Verify e-Stamp and Registry/ROD documents via official government portals.</p>
          </div>

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
        </div>
      )}

      {/* Exceptions & CPs Tab */}
      {activeTab === 'exceptions' && (
        <div className="space-y-6">
          <div className="card">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-lg font-semibold">Rule Evaluation</h2>
                {exceptions && (
                  <div className="flex gap-3 mt-2 flex-wrap">
                    <span className="badge badge-error">High: {exceptions.high_count}</span>
                    <span className="badge badge-warning">Medium: {exceptions.medium_count}</span>
                    <span className="badge badge-info">Low: {exceptions.low_count}</span>
                    <span className="text-slate-400">|</span>
                    <span className="text-slate-400">Open: {exceptions.open_count}</span>
                    <span className="text-green-400">Resolved: {exceptions.resolved_count}</span>
                    <span className="text-yellow-400">Waived: {exceptions.waived_count}</span>
                  </div>
                )}
              </div>
              <button 
                onClick={handleEvaluate} 
                className="btn btn-primary"
                disabled={evaluating}
              >
                {evaluating ? 'Evaluating...' : 'Evaluate Rules'}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="card">
              <h3 className="font-semibold mb-4">Exceptions</h3>
              {!exceptions || exceptions.exceptions.length === 0 ? (
                <p className="text-slate-400">No exceptions. Run evaluation first.</p>
              ) : (
                <ul className="space-y-2 max-h-96 overflow-y-auto">
                  {exceptions.exceptions.map((exc: any) => (
                    <li
                      key={exc.id}
                      onClick={() => setSelectedExc(exc)}
                      className={`p-3 rounded cursor-pointer transition-colors ${
                        selectedExc?.id === exc.id ? 'bg-cyan-500/20 border border-cyan-500' : 'bg-slate-700 hover:bg-slate-600'
                      }`}
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <p className="font-medium">{exc.title}</p>
                          <p className="text-sm text-slate-400">{exc.module} • {exc.rule_id}</p>
                        </div>
                        <div className="flex gap-1">
                          <span className={`badge ${
                            exc.severity === 'High' ? 'badge-error' :
                            exc.severity === 'Medium' ? 'badge-warning' : 'badge-info'
                          }`}>
                            {exc.severity}
                          </span>
                          <span className={`badge ${
                            exc.status === 'Open' ? 'badge-neutral' :
                            exc.status === 'Resolved' ? 'badge-success' : 'badge-warning'
                          }`}>
                            {exc.status}
                          </span>
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="card">
              {selectedExc ? (
                <div className="space-y-4">
                  <div className="flex justify-between items-start">
                    <h3 className="font-semibold">{selectedExc.title}</h3>
                    <span className={`badge ${
                      selectedExc.severity === 'High' ? 'badge-error' :
                      selectedExc.severity === 'Medium' ? 'badge-warning' : 'badge-info'
                    }`}>
                      {selectedExc.severity}
                    </span>
                  </div>
                  
                  <div>
                    <p className="text-slate-400 text-sm">Module</p>
                    <p>{selectedExc.module}</p>
                  </div>
                  
                  <div>
                    <p className="text-slate-400 text-sm">Description</p>
                    <p>{selectedExc.description || '—'}</p>
                  </div>

                  {selectedExc.evidence_refs && selectedExc.evidence_refs.length > 0 && (
                    <div>
                      <p className="text-slate-400 text-sm mb-2">Evidence References</p>
                      <ul className="space-y-1">
                        {selectedExc.evidence_refs.map((ref: any, i: number) => (
                          <li key={i} className="text-sm bg-slate-600 p-2 rounded">
                            Doc: {ref.document_id?.substring(0, 8)}... 
                            {ref.page_number && ` • Page ${ref.page_number}`}
                            {ref.note && ` • ${ref.note}`}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {selectedExc.status === 'Open' && (
                    <div className="space-y-3 pt-4 border-t border-slate-600">
                      {canResolve && (
                        <button 
                          onClick={() => handleResolve(selectedExc.id)}
                          className="btn btn-primary w-full"
                        >
                          Mark as Resolved
                        </button>
                      )}
                      
                      {canWaive && (
                        <div className="space-y-2">
                          <input
                            type="text"
                            placeholder="Waiver reason..."
                            value={waiverReason}
                            onChange={(e) => setWaiverReason(e.target.value)}
                            className="input w-full"
                          />
                          <button 
                            onClick={() => handleWaive(selectedExc.id)}
                            className="btn btn-secondary w-full"
                          >
                            Waive Exception
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-slate-400">Select an exception to view details.</p>
              )}
            </div>
          </div>

          <div className="card">
            <h3 className="font-semibold mb-4">
              Conditions Precedent
              {cps && <span className="text-slate-400 ml-2">({cps.open_count} open)</span>}
            </h3>
            {!cps || cps.cps.length === 0 ? (
              <p className="text-slate-400">No conditions precedent.</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {cps.cps.map((cp: any) => (
                  <div key={cp.id} className="p-3 bg-slate-700 rounded">
                    <div className="flex justify-between items-start mb-2">
                      <span className={`badge ${
                        cp.severity === 'High' ? 'badge-error' :
                        cp.severity === 'Medium' ? 'badge-warning' : 'badge-info'
                      }`}>
                        {cp.severity}
                      </span>
                      <span className={`badge ${
                        cp.status === 'Open' ? 'badge-neutral' :
                        cp.status === 'Satisfied' ? 'badge-success' : 'badge-warning'
                      }`}>
                        {cp.status}
                      </span>
                    </div>
                    <p className="text-sm">{cp.text}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Drafts Tab */}
      {activeTab === 'drafts' && (
        <div className="space-y-6">
          <div className="card">
            <h2 className="text-lg font-semibold mb-4">Generate Draft Documents</h2>
            <p className="text-slate-400 mb-6">Generate bank-style DOCX drafts based on case data, exceptions, and dossier fields.</p>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 bg-slate-700 rounded">
                <h3 className="font-medium mb-2">Discrepancy Letter</h3>
                <p className="text-sm text-slate-400 mb-4">Formal letter to borrower listing discrepancies and required actions.</p>
                <button 
                  onClick={() => handleGenerateDraft('discrepancy')}
                  className="btn btn-primary w-full"
                  disabled={generating === 'discrepancy'}
                >
                  {generating === 'discrepancy' ? 'Generating...' : 'Generate'}
                </button>
              </div>
              
              <div className="p-4 bg-slate-700 rounded">
                <h3 className="font-medium mb-2">Undertaking & Indemnity</h3>
                <p className="text-sm text-slate-400 mb-4">Standard undertaking and indemnity document for borrower signature.</p>
                <button 
                  onClick={() => handleGenerateDraft('undertaking')}
                  className="btn btn-primary w-full"
                  disabled={generating === 'undertaking'}
                >
                  {generating === 'undertaking' ? 'Generating...' : 'Generate'}
                </button>
              </div>
              
              <div className="p-4 bg-slate-700 rounded">
                <h3 className="font-medium mb-2">Internal Opinion</h3>
                <p className="text-sm text-slate-400 mb-4">Skeleton internal legal opinion with findings and recommendation.</p>
                <button 
                  onClick={() => handleGenerateDraft('opinion')}
                  className="btn btn-primary w-full"
                  disabled={generating === 'opinion'}
                >
                  {generating === 'opinion' ? 'Generating...' : 'Generate'}
                </button>
              </div>
            </div>
          </div>

          {generatedDrafts.length > 0 && (
            <div className="card">
              <h3 className="font-semibold mb-4">Recently Generated</h3>
              <ul className="space-y-2">
                {generatedDrafts.map((draft, i) => (
                  <li key={i} className="p-3 bg-slate-700 rounded flex justify-between items-center">
                    <div>
                      <p className="font-medium">{draft.filename}</p>
                      <p className="text-sm text-slate-400">{draft.export_type}</p>
                    </div>
                    <a 
                      href={draft.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="btn btn-primary text-sm"
                    >
                      Download
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Export Tab */}
      {activeTab === 'exports' && (
        <div className="space-y-6">
          <div className="card">
            <h2 className="text-lg font-semibold mb-4">Bank Pack Export</h2>
            <p className="text-slate-400 mb-6">Generate a comprehensive PDF report with executive summary, all exceptions, conditions precedent, and document index.</p>
            
            <button 
              onClick={handleGenerateBankPack}
              className="btn btn-primary"
              disabled={generating === 'bankpack'}
            >
              {generating === 'bankpack' ? 'Generating Bank Pack...' : 'Generate Bank Pack PDF'}
            </button>
          </div>

          <div className="card">
            <h3 className="font-semibold mb-4">
              Export History
              {exports && <span className="text-slate-400 ml-2">({exports.total} exports)</span>}
            </h3>
            {!exports || exports.exports.length === 0 ? (
              <p className="text-slate-400">No exports generated yet.</p>
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
                            className="text-cyan-400 hover:text-cyan-300"
                            onClick={async (e) => {
                              e.preventDefault();
                              try {
                                const token = await getToken();
                                const res = await fetch(`/api/v1/exports/${exp.id}/download`, {
                                  headers: { Authorization: `Bearer ${token}` }
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
      )}

      {/* Insights Tab */}
      {activeTab === 'insights' && (
        <div className="space-y-6">
          <div className="card">
            <div className="flex justify-between items-center mb-6">
              <div>
                <h2 className="text-lg font-semibold">Case Insights</h2>
                <p className="text-slate-400 text-sm">Analytics and activity over time</p>
              </div>
              <div className="flex gap-1 bg-slate-700 rounded-lg p-1">
                {[7, 30, 90].map((d) => (
                  <button
                    key={d}
                    onClick={() => setInsightsDays(d)}
                    className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all ${
                      insightsDays === d
                        ? 'bg-cyan-500 text-slate-900'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-600'
                    }`}
                  >
                    {d}d
                  </button>
                ))}
              </div>
            </div>

            {insightsLoading ? (
              <div className="text-center py-12 text-slate-400">Loading insights...</div>
            ) : insights ? (
              <div className="space-y-6">
                {/* KPI Cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-slate-700 rounded-lg p-4">
                    <p className="text-sm text-slate-400">Open High</p>
                    <p className="text-2xl font-bold text-rose-400">{insights.summary.open_exceptions_high}</p>
                  </div>
                  <div className="bg-slate-700 rounded-lg p-4">
                    <p className="text-sm text-slate-400">Open Medium</p>
                    <p className="text-2xl font-bold text-amber-400">{insights.summary.open_exceptions_medium}</p>
                  </div>
                  <div className="bg-slate-700 rounded-lg p-4">
                    <p className="text-sm text-slate-400">CP Completion</p>
                    <p className="text-2xl font-bold text-cyan-400">{insights.summary.cp_completion_pct}%</p>
                  </div>
                  <div className="bg-slate-700 rounded-lg p-4">
                    <p className="text-sm text-slate-400">Verification</p>
                    <p className="text-2xl font-bold text-purple-400">{insights.summary.verification_completion_pct}%</p>
                  </div>
                </div>

                {/* Activity Summary */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-slate-700/50 rounded-lg p-3">
                    <p className="text-xs text-slate-400">Open Low</p>
                    <p className="text-lg font-semibold text-emerald-400">{insights.summary.open_exceptions_low}</p>
                  </div>
                  <div className="bg-slate-700/50 rounded-lg p-3">
                    <p className="text-xs text-slate-400">Exports</p>
                    <p className="text-lg font-semibold">{insights.summary.exports_generated}</p>
                  </div>
                  <div className="bg-slate-700/50 rounded-lg p-3">
                    <p className="text-xs text-slate-400">Last Rule Run</p>
                    <p className="text-sm">{insights.summary.last_rule_run_at ? new Date(insights.summary.last_rule_run_at).toLocaleDateString() : '—'}</p>
                  </div>
                  <div className="bg-slate-700/50 rounded-lg p-3">
                    <p className="text-xs text-slate-400">Last OCR</p>
                    <p className="text-sm">{insights.summary.last_ocr_at ? new Date(insights.summary.last_ocr_at).toLocaleDateString() : '—'}</p>
                  </div>
                </div>

                {/* Activity Timeline */}
                <div>
                  <h3 className="font-semibold mb-4">Activity Timeline ({insightsDays} days)</h3>
                  <div className="bg-slate-700 rounded-lg p-4 overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-slate-400 text-left">
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
                          <tr key={t.date} className="border-t border-slate-600">
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
                            <td colSpan={8} className="py-8 text-center text-slate-400">
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
              <p className="text-slate-400 text-center py-8">Failed to load insights</p>
            )}
          </div>
        </div>
      )}
    </div>
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
          <span className="text-sm text-slate-400">Verification Keys</span>
          {!editing && verification.status === 'Pending' && (
            <button 
              onClick={() => setEditing(true)} 
              className="text-sm text-cyan-400 hover:text-cyan-300"
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
                  <label className="text-sm text-slate-400 w-32">Registry Office:</label>
                  <input
                    type="text"
                    value={keys.registry_office || ''}
                    onChange={(e) => setKeys({ ...keys, registry_office: e.target.value })}
                    className="input flex-1 text-sm"
                    placeholder="e.g., LDA Lahore"
                  />
                </div>
                <div className="flex gap-2 items-center">
                  <label className="text-sm text-slate-400 w-32">Registry Number:</label>
                  <input
                    type="text"
                    value={keys.registry_number || ''}
                    onChange={(e) => setKeys({ ...keys, registry_number: e.target.value })}
                    className="input flex-1 text-sm"
                    placeholder="e.g., 1234/2023"
                  />
                </div>
                <div className="flex gap-2 items-center">
                  <label className="text-sm text-slate-400 w-32">Instrument:</label>
                  <input
                    type="text"
                    value={keys.instrument || ''}
                    onChange={(e) => setKeys({ ...keys, instrument: e.target.value })}
                    className="input flex-1 text-sm"
                    placeholder="e.g., Sale Deed, Transfer Deed"
                  />
                </div>
                <div className="flex gap-2 items-center">
                  <label className="text-sm text-slate-400 w-32">Search Terms:</label>
                  <input
                    type="text"
                    value={keys.search_terms || ''}
                    onChange={(e) => setKeys({ ...keys, search_terms: e.target.value })}
                    className="input flex-1 text-sm"
                    placeholder="What you searched for"
                  />
                </div>
                <div className="border-t border-slate-600 my-2"></div>
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
                  className="input flex-1 text-sm bg-slate-600"
                />
                <input
                  type="text"
                  value={value}
                  onChange={(e) => setKeys({ ...keys, [key]: e.target.value })}
                  className="input flex-1 text-sm"
                />
                <button
                  onClick={() => handleRemoveKey(key)}
                  className="text-red-400 hover:text-red-300 px-2"
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
              <button onClick={handleAddKey} className="btn btn-secondary text-sm">
                Add
              </button>
            </div>
            <textarea
              placeholder="Notes..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="input w-full text-sm"
              rows={2}
            />
            <div className="flex gap-2">
              <button 
                onClick={handleSaveKeys} 
                className="btn btn-primary text-sm"
                disabled={loading}
              >
                {loading ? 'Saving...' : 'Save'}
              </button>
              <button 
                onClick={() => { setEditing(false); setKeys(verification.keys_json || {}); }}
                className="btn btn-secondary text-sm"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <div className="bg-slate-700 rounded p-3">
            {Object.keys(keys).length === 0 ? (
              <p className="text-slate-400 text-sm">No verification keys set. Click Edit to add.</p>
            ) : (
              <div className="space-y-1">
                {Object.entries(keys).map(([key, value]) => (
                  <div key={key} className="flex justify-between text-sm">
                    <span className="text-slate-400">{key}:</span>
                    <span className="font-mono">{value}</span>
                  </div>
                ))}
              </div>
            )}
            {verification.notes && (
              <p className="text-sm text-slate-400 mt-2 pt-2 border-t border-slate-600">
                {verification.notes}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Portal Button */}
      <button
        onClick={handleOpenPortal}
        className="btn btn-secondary w-full mb-4"
      >
        Open Verification Portal ↗
      </button>

      {/* Evidence Section */}
      <div className="mb-4">
        <span className="text-sm text-slate-400 block mb-2">Evidence</span>
        
        {hasEvidence ? (
          <ul className="space-y-2 mb-3">
            {verification.evidence_refs.map((ref: any) => {
              const doc = documents.find((d) => d.id === ref.document_id);
              return (
                <li key={ref.id} className="flex justify-between items-center p-2 bg-slate-700 rounded text-sm">
                  <span>{doc?.original_filename || ref.document_id.substring(0, 8)}</span>
                  <button 
                    onClick={() => handleDownloadEvidence(ref.document_id)}
                    className="text-cyan-400 hover:text-cyan-300 text-sm"
                  >
                    View
                  </button>
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="text-sm text-slate-400 mb-3">No evidence attached yet.</p>
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
            <button
              onClick={handleAttachEvidence}
              className="btn btn-secondary text-sm"
              disabled={loading || !selectedDocId}
            >
              Attach
            </button>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      {verification.status === 'Pending' && (
        <div className="space-y-2 pt-4 border-t border-slate-600">
          <button
            onClick={handleMarkVerified}
            className="btn btn-primary w-full"
            disabled={loading || !hasEvidence}
            title={!hasEvidence ? 'Attach evidence first' : ''}
          >
            {loading ? 'Processing...' : 'Mark as Verified'}
          </button>
          
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
                <button
                  onClick={handleMarkFailed}
                  className="btn btn-secondary flex-1"
                  disabled={loading}
                >
                  Confirm Failed
                </button>
                <button
                  onClick={() => { setShowFailedInput(false); setFailedNotes(''); }}
                  className="btn btn-secondary flex-1"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setShowFailedInput(true)}
              className="btn btn-secondary w-full"
            >
              Mark as Failed
            </button>
          )}
        </div>
      )}

      {/* Verified/Failed info */}
      {verification.status === 'Verified' && verification.verified_at && (
        <p className="text-sm text-green-400 mt-4">
          ✓ Verified on {new Date(verification.verified_at).toLocaleString()}
        </p>
      )}
      {verification.status === 'Failed' && verification.notes && (
        <p className="text-sm text-red-400 mt-4">
          ✗ Failed: {verification.notes}
        </p>
      )}
      </div>
    </>
  );
}
