'use client';

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Skeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/ui/empty-state';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { useToast } from '@/components/ui/toast';
import {
  CaseDocumentItem,
  DocumentOcrStatus,
  OCRTextResponse,
  listDocuments,
  getPageRenderUrl,
  getPageThumbnailUrl,
  getOcrText,
  getOcrStatus,
  getPageOcrReview,
  enqueueOcr,
  getMe,
  listExceptions,
  listCPs,
  attachExceptionEvidenceSnippet,
  attachCPEvidenceSnippet,
  putOcrTextCorrection,
  deleteOcrTextCorrection,
  deleteDocument,
  autofillDossier,
} from '@/lib/api';
import { useRouter } from 'next/navigation';
import { getCaseTabPath } from '@/lib/routes';
import { cn } from '@/lib/utils';
import { urduTextProps } from '@/lib/text-script';
import { formatDocumentType as formatType, formatQualityLabel, getQualityToneClass } from './document-viewer-format';

type PageQualityMeta = {
  quality_level?: string | null;
  quality_score?: number | null;
  warning_reason?: string | null;
};

type DocumentStage = {
  label: string;
  progress: number;
};

const DOCUMENT_STAGE_MAP: Record<string, DocumentStage> = {
  uploaded: { label: 'Uploaded', progress: 10 },
  queued: { label: 'Queued', progress: 20 },
  preprocessing: { label: 'Preprocessing', progress: 35 },
  ocr_in_progress: { label: 'OCR in progress', progress: 55 },
  extracting: { label: 'Extracting fields', progress: 70 },
  rules_evaluation: { label: 'Rules evaluation', progress: 85 },
  complete: { label: 'Complete', progress: 100 },
  needs_review: { label: 'Needs review', progress: 100 },
  failed: { label: 'Failed', progress: 0 },
};

function normalizeStatusValue(value?: string | null): string {
  return (value ?? '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, '_');
}

function getDocumentStage(status?: string | null): DocumentStage {
  const normalizedStatus = normalizeStatusValue(status);
  return DOCUMENT_STAGE_MAP[normalizedStatus] ?? { label: 'Processing', progress: 40 };
}

function isTerminalDocumentStatus(status?: string | null): boolean {
  const normalizedStatus = normalizeStatusValue(status);
  return normalizedStatus === 'complete' || normalizedStatus === 'completed' || normalizedStatus === 'failed' || normalizedStatus === 'needs_review';
}

interface DocumentViewerProps {
  caseId: string;
  documents?: CaseDocumentItem[]; // Passed from parent (single source of truth) - if provided, don't fetch independently
  onAttachEvidence?: (documentId: string, pageNumber: number) => void;
  initialDocId?: string;
  initialPage?: number;
  onUploadRequest?: () => void;
  onDocumentDeleted?: () => void;
  variant?: "default" | "workbench" | "evidence";
  highlightLabel?: string | null;
  highlightValue?: string | null;
  onOpenFullViewer?: () => void;
  onUseAsFact?: (text: string) => void;
  evidenceMode?: "source" | "text" | "split";
  showHighlightPanel?: boolean;
}

export function DocumentViewer({
  caseId,
  documents: documentsProp,
  onAttachEvidence,
  initialDocId,
  initialPage,
  onUploadRequest,
  onDocumentDeleted,
  variant = "default",
  highlightLabel,
  highlightValue,
  onOpenFullViewer,
  onUseAsFact,
  evidenceMode = "split",
  showHighlightPanel = true,
}: DocumentViewerProps) {
  const router = useRouter();
  const { toast } = useToast();
  const getDocumentId = (doc: CaseDocumentItem | null | undefined): string | null => {
    if (!doc || typeof doc.id !== 'string') return null;
    const trimmed = doc.id.trim();
    if (!trimmed || trimmed === 'undefined') return null;
    return trimmed;
  };
  // Use documents from prop if provided (single source of truth), otherwise fetch independently
  const [documentsState, setDocumentsState] = useState<CaseDocumentItem[]>([]);
  const documents = useMemo(() => {
    const docsRaw = documentsProp ?? documentsState;
    return Array.isArray(docsRaw)
      ? docsRaw
      : [];
  }, [documentsProp, documentsState]);
  const [selectedDoc, setSelectedDoc] = useState<CaseDocumentItem | null>(null);
  const [selectedPage, setSelectedPage] = useState<number>(1);
  const [pageImageUrl, setPageImageUrl] = useState<string | null>(null);
  const [pageRenderMode, setPageRenderMode] = useState<'pdf' | 'image'>('image');
  const [ocrText, setOcrText] = useState<string>('');
  const [ocrTextData, setOcrTextData] = useState<OCRTextResponse | null>(null);
  const [ocrMode, setOcrMode] = useState<'effective' | 'raw' | 'corrected'>('effective');
  const [editingOcr, setEditingOcr] = useState(false);
  const [ocrCorrectionText, setOcrCorrectionText] = useState('');
  const [ocrCorrectionNote, setOcrCorrectionNote] = useState('');
  const [savingCorrection, setSavingCorrection] = useState(false);
  const [loading, setLoading] = useState(true);
  const [pageLoading, setPageLoading] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [ocrStatus, setOcrStatus] = useState<DocumentOcrStatus | null>(null);
  const [pageQualityMeta, setPageQualityMeta] = useState<PageQualityMeta | null>(null);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [exceptions, setExceptions] = useState<any[]>([]);
  const [cps, setCps] = useState<any[]>([]);
  const [selectedSnippet, setSelectedSnippet] = useState<string>('');
  const [showSnippetModal, setShowSnippetModal] = useState(false);
  const [snippetTarget, setSnippetTarget] = useState<'exception' | 'cp' | null>(null);
  const [snippetTargetId, setSnippetTargetId] = useState<string>('');
  const [autofilling, setAutofilling] = useState(false);
  const [viewerError, setViewerError] = useState<string | null>(null);
  const [revertDialogOpen, setRevertDialogOpen] = useState(false);
  const [deletingCorrection, setDeletingCorrection] = useState(false);
  const [attachingSnippet, setAttachingSnippet] = useState(false);
  const [deleteDocDialogOpen, setDeleteDocDialogOpen] = useState(false);
  const [documentToDelete, setDocumentToDelete] = useState<CaseDocumentItem | null>(null);
  const [deletingDoc, setDeletingDoc] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const loadedRef = useRef<{ caseId: string | null }>({ caseId: null });
  const lastNavigationTargetRef = useRef<string | null>(null);

  // Only fetch documents if not provided as prop (parent is single source of truth)
    const loadDocuments = useCallback(async () => {
    // Skip if documents are provided as prop
    if (documentsProp) {
      setLoading(false);
      return;
    }
    // Prevent duplicate loads for the same caseId
    if (loadedRef.current.caseId === caseId) {
      return;
    }
    // Abort previous request if still in flight
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const abortController = new AbortController();
    abortControllerRef.current = abortController;
    setLoading(true);
    try {
      const docs = await listDocuments(caseId);
      if (abortController.signal.aborted) {
        return;
      }
      const arr = Array.isArray(docs) ? docs : [];
      setDocumentsState(arr);
      const firstValidDoc = arr.find((doc) => getDocumentId(doc));
      if (firstValidDoc && !selectedDoc) {
        setSelectedDoc(firstValidDoc);
      }
      loadedRef.current.caseId = caseId;
      const userData = await getMe();
      if (abortController.signal.aborted) return;
      setCurrentUser(userData);
      if (userData && (userData.role === 'Admin' || userData.role === 'Reviewer')) {
        Promise.all([
          listExceptions(caseId).then(excData => setExceptions(excData.exceptions || [])).catch(() => {}),
          listCPs(caseId).then(cpData => setCps(cpData.cps || [])).catch(() => {}),
        ]);
      }
      setViewerError(null);
    } catch (e: any) {
      if (e.name === 'AbortError') {
        return;
      }
      setViewerError(e.message || 'Failed to load documents');
    } finally {
      if (!abortController.signal.aborted) {
        setLoading(false);
      }
    }
  }, [caseId, selectedDoc, documentsProp]);

  // Initial load effect - only depends on caseId and documentsProp
  useEffect(() => {
    loadDocuments();
    
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [loadDocuments]);
  
  // Update selectedDoc when documents prop changes
  useEffect(() => {
    if (documentsProp && documentsProp.length > 0 && !selectedDoc) {
      const firstValidDoc = documentsProp.find((doc) => getDocumentId(doc));
      if (firstValidDoc) {
        setSelectedDoc(firstValidDoc);
      }
    }
  }, [documentsProp, selectedDoc]);

  useEffect(() => {
    if (!selectedDoc || documents.length === 0) {
      return;
    }

    const latestSelectedDoc = documents.find((document) => document.id === selectedDoc.id);
    if (latestSelectedDoc && latestSelectedDoc !== selectedDoc) {
      setSelectedDoc(latestSelectedDoc);
    }
  }, [documents, selectedDoc]);

  // Apply document/page navigation targets from the parent whenever they change.
  useEffect(() => {
    if (!initialDocId || documents.length === 0) {
      return;
    }

    const targetKey = `${initialDocId}:${initialPage ?? 1}`;
    if (lastNavigationTargetRef.current === targetKey) {
      return;
    }

    const doc = documents.find((document) => document.id === initialDocId);
    if (!doc) {
      return;
    }

    setSelectedDoc(doc);
    if (initialPage && initialPage >= 1) {
      setSelectedPage(initialPage);
    }
    lastNavigationTargetRef.current = targetKey;
  }, [initialDocId, initialPage, documents]);

  const loadPage = useCallback(async () => {
    const documentId = getDocumentId(selectedDoc);
    if (!documentId) return;
    
    setPageLoading(true);
    try {
      // Use a review-sized PNG render so the page stays crisp and visible in every
      // browser, including embedded browser surfaces that do not render PDF frames.
      try {
        setPageImageUrl(getPageRenderUrl(documentId, selectedPage));
        setPageRenderMode('image');
      } catch {
        const imageResult = await getPageThumbnailUrl(documentId, selectedPage);
        setPageImageUrl(imageResult.url);
        setPageRenderMode('image');
      }

      // Load OCR text (P14: use new API with corrections support)
      try {
        const ocrResult = await getOcrText(documentId, selectedPage, ocrMode);
        setOcrTextData(ocrResult);
        setOcrText(ocrResult.effective_text || ocrResult.raw_text || '');
      } catch {
        setOcrText('OCR not available');
        setOcrTextData(null);
      }

      try {
        const pageReview = await getPageOcrReview(caseId, documentId, selectedPage);
        const meta = pageReview.meta as PageQualityMeta | undefined;
        setPageQualityMeta({
          quality_level: meta?.quality_level ?? null,
          quality_score: typeof meta?.quality_score === 'number' ? meta.quality_score : null,
          warning_reason: meta?.warning_reason ?? null,
        });
      } catch {
        setPageQualityMeta(null);
      }
      setViewerError(null);
    } catch (e: any) {
      setViewerError(e.message || 'Failed to load document page');
    } finally {
      setPageLoading(false);
    }
  }, [caseId, selectedDoc, selectedPage, ocrMode]);

  const loadOcrStatus = useCallback(async () => {
    const documentId = getDocumentId(selectedDoc);
    if (!documentId) return;
    try {
      const status = await getOcrStatus(documentId);
      setOcrStatus(status);
    } catch {
      setViewerError('Failed to load OCR status');
    }
  }, [selectedDoc]);

  useEffect(() => {
    if (selectedDoc && selectedPage) {
      void loadPage();
    }
  }, [selectedDoc, selectedPage, loadPage]);

  useEffect(() => {
    if (selectedDoc) {
      void loadOcrStatus();
    }
  }, [selectedDoc, loadOcrStatus]);

  const handleForceOcr = async () => {
    const documentId = getDocumentId(selectedDoc);
    if (!documentId) return;
    setOcrLoading(true);
    try {
      await enqueueOcr(documentId, true);
      toast({
        title: 'OCR rerun queued.',
        description: 'Processing will continue in the background.',
        variant: 'success',
      });
      // Poll for status update
      setTimeout(() => {
        loadOcrStatus();
        setOcrLoading(false);
      }, 2000);
    } catch (e: any) {
      setViewerError('Failed to queue OCR rerun');
      toast({
        title: 'Unable to queue OCR rerun.',
        description: e.message || 'Please retry.',
        variant: 'error',
      });
      setOcrLoading(false);
    }
  };

  const handleConfirmDeleteDocument = useCallback(async () => {
    const docId = getDocumentId(documentToDelete);
    if (!docId) return;
    setDeletingDoc(true);
    try {
      await deleteDocument(docId);
      setDeleteDocDialogOpen(false);
      toast({ title: 'Document removed.', description: documentToDelete?.original_filename, variant: 'success' });
      // Select adjacent document if possible
      const remaining = documents.filter((d) => d.id !== docId);
      if (remaining.length > 0) {
        setSelectedDoc(remaining[0]);
        setSelectedPage(1);
      } else {
        setSelectedDoc(null);
      }
      setDocumentToDelete(null);
      onDocumentDeleted?.();
    } catch (e: any) {
      toast({ title: 'Failed to remove document.', description: e.message || 'Please retry.', variant: 'error' });
    } finally {
      setDeletingDoc(false);
    }
  }, [documentToDelete, documents, onDocumentDeleted, toast]);

  const selectedPageOcrStatus = useMemo(
    () => ocrStatus?.pages.find((page) => page.page_number === selectedPage) ?? null,
    [ocrStatus, selectedPage]
  );

  const documentQualityLevel = pageQualityMeta?.quality_level ?? ocrStatus?.quality_level ?? null;
  const documentWarningReason =
    pageQualityMeta?.warning_reason ?? ocrStatus?.quality_reasons?.[0] ?? null;

  const getOcrStatusBadge = () => {
    if (!ocrStatus) return null;
    const status = ocrStatus.status_counts;
    if (status?.Done === ocrStatus.total_pages && ocrStatus.failed_count === 0) {
      return <Badge variant="success">Done</Badge>;
    } else if (status?.Processing || status?.Queued) {
      return <Badge variant="warning">Processing</Badge>;
    } else if (ocrStatus.failed_count > 0) {
      return <Badge variant="error">Failed</Badge>;
    }
    return <Badge variant="outline">Queued</Badge>;
  };

  const renderQualityBadge = (
    qualityLevel?: string | null,
    qualityScore?: number | null,
    warningReason?: string | null,
    className?: string
  ) => {
    if (!qualityLevel) {
      return null;
    }

    return (
      <TooltipProvider delayDuration={150}>
        <div className={`flex flex-wrap items-center gap-2 ${className ?? ''}`}>
          <Tooltip>
            <TooltipTrigger asChild>
              <span
                className={`inline-flex min-h-5 items-center rounded-md border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.06em] ${getQualityToneClass(
                  qualityLevel
                )}`}
              >
                OCR {formatQualityLabel(qualityLevel)}
              </span>
            </TooltipTrigger>
            <TooltipContent className="max-w-xs border-[rgba(82,90,99,0.5)] bg-[rgba(29,34,39,0.98)] text-xs text-stone-200">
              {warningReason || 'OCR quality metadata available for this document page.'}
            </TooltipContent>
          </Tooltip>
          {typeof qualityScore === 'number' ? (
            <span className="text-[11px] text-stone-400">{qualityScore.toFixed(2)}</span>
          ) : null}
          {warningReason ? <span className="text-[11px] text-stone-500">{warningReason}</span> : null}
        </div>
      </TooltipProvider>
    );
  };

  if (loading) {
    return <Skeleton className="h-96 w-full" />;
  }

  if (documents.length === 0) {
    return (
      <EmptyState
        title="No documents have been added to this case."
        description="Upload annexures, title documents, and supporting evidence to begin review."
        actionLabel={onUploadRequest ? 'Upload Documents' : undefined}
        onAction={onUploadRequest}
        className="min-h-[420px]"
      />
    );
  }

  const compact = variant === "workbench" || variant === "evidence";
  const selectedSnippetText = selectedSnippet || highlightValue || "";

  return (
    <div className={compact ? "flex h-full min-h-0 bg-background" : "flex h-[calc(100vh-200px)] bg-[rgba(14,18,22,0.92)]"}>
      {/* Left: Document List */}
      {compact ? null : (
      <div className="w-64 overflow-y-auto border-r border-[rgba(82,90,99,0.34)] bg-[rgba(18,22,27,0.72)]">
        <div className="p-4 space-y-2">
          {documents.map((doc) => {
            const normalizedStatus = normalizeStatusValue(doc.status);
            const stage = getDocumentStage(doc.status);
            const showFailedState = normalizedStatus === 'failed';
            const showCompleteState = normalizedStatus === 'complete' || normalizedStatus === 'completed';
            const showNeedsReviewState = normalizedStatus === 'needs_review';
            const showProgress = !isTerminalDocumentStatus(doc.status);

            return (
            <div key={doc.id} className="group relative">
            <button
              onClick={() => {
                if (!getDocumentId(doc)) return;
                setSelectedDoc(doc);
                setSelectedPage(1);
              }}
              className={`w-full text-left p-3 rounded-lg border transition-colors ${
                selectedDoc?.id === doc.id
                  ? 'border-[rgba(152,161,135,0.34)] bg-[rgba(152,161,135,0.12)] text-stone-100 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]'
                  : 'border-[rgba(82,90,99,0.32)] bg-[rgba(18,22,27,0.82)] text-stone-300 hover:bg-[rgba(34,39,45,0.82)]'
              }`}
            >
              <div className="font-medium text-sm">{doc.original_filename}</div>
              <div className="mt-1 flex flex-wrap items-center gap-2">
                {doc.predicted_doc_type && (
                  <Badge variant="info" className="text-xs">
                    {formatType(doc.predicted_doc_type)}
                  </Badge>
                )}
                {doc.needs_review ? (
                  <Badge variant="warning" className="text-xs">Needs Review</Badge>
                ) : null}
                {doc.doc_type && (
                  <Badge variant="outline" className="text-xs">
                    {formatType(doc.doc_type)}
                  </Badge>
                )}
                <span className="text-xs text-stone-500">
                  {doc.page_count || 0} pages
                </span>
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                {showCompleteState ? <Badge variant="success">Complete</Badge> : null}
                {showNeedsReviewState ? <Badge variant="warning">Needs Review</Badge> : null}
                {showFailedState ? <Badge variant="error">Failed</Badge> : null}
                {!showCompleteState && !showNeedsReviewState && !showFailedState ? (
                  <Badge variant="neutral" className="text-xs">
                    {stage.label}
                  </Badge>
                ) : null}
              </div>
              {showProgress ? (
                <div className="mt-2">
                  <div className="mb-1 text-[11px] text-stone-500">{stage.label}</div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-[rgba(34,39,45,0.92)]">
                    <div
                      className="h-full rounded-full bg-[rgba(152,161,135,0.62)] transition-[width]"
                      style={{ width: `${stage.progress}%` }}
                    />
                  </div>
                </div>
              ) : null}
              {showFailedState && doc.error_message ? (
                <div className="mt-2 text-[11px] text-[rgb(219,156,153)]">{doc.error_message}</div>
              ) : null}
              <div className="mt-1 text-[11px] text-stone-500">
                {typeof doc.classification_confidence === 'number' && (
                  <span>Conf {Math.round(Number(doc.classification_confidence) * 100)}%</span>
                )}
                {doc.classification_status && (
                  <span className="ml-2">Status {String(doc.classification_status)}</span>
                )}
              </div>
            </button>
            {currentUser?.role === 'Admin' && (
              <button
                type="button"
                aria-label={`Remove ${doc.original_filename}`}
                onClick={(e) => {
                  e.stopPropagation();
                  setDocumentToDelete(doc);
                  setDeleteDocDialogOpen(true);
                }}
                className="cds-hit-target absolute right-1.5 top-1.5 hidden h-6 w-6 items-center justify-center rounded border border-[rgba(189,90,86,0.4)] bg-[rgba(189,90,86,0.12)] text-[rgb(219,156,153)] opacity-0 transition-opacity hover:bg-[rgba(189,90,86,0.24)] group-hover:flex group-hover:opacity-100"
              >
                <Trash2 className="size-3.5" />
              </button>
            )}
            </div>
            );
          })}
        </div>
      </div>
      )}

      {/* Middle: Page Thumbnails */}
      {selectedDoc && evidenceMode !== "text" && (
        <div className={compact
          ? "w-[76px] shrink-0 overflow-y-auto border-r border-border bg-[hsl(var(--canvas))] px-0 py-[18px]"
          : "w-32 overflow-y-auto border-r border-[rgba(82,90,99,0.34)] bg-[rgba(18,22,27,0.58)]"
        }>
          {variant === "evidence" ? <p className="cds-meta mb-2.5 px-3">Pages</p> : null}
          <div className={compact ? "flex flex-col items-center gap-2.5" : "p-2 space-y-2"}>
            {Array.from({ length: selectedDoc.page_count || 0 }, (_, i) => i + 1).map((pageNum) => (
              <button
                key={pageNum}
                onClick={() => setSelectedPage(pageNum)}
                className={compact
                  ? `relative h-24 w-[72px] overflow-hidden rounded-[3px] border ${
                      selectedPage === pageNum
                        ? "border-2 border-[hsl(var(--crimson-border))] bg-[#2e3030] text-foreground"
                        : "border-border bg-[hsl(var(--pill))] text-muted-foreground"
                    }`
                  : `w-full aspect-[3/4] rounded border-2 transition-colors ${
                  selectedPage === pageNum
                    ? 'border-[rgba(152,161,135,0.45)] bg-[rgba(24,28,32,0.92)] shadow-[inset_0_0_0_1px_rgba(152,161,135,0.18)]'
                    : 'border-[rgba(82,90,99,0.32)] bg-[rgba(18,22,27,0.82)] hover:border-[rgba(126,133,111,0.38)]'
                }`}
              >
                <div className={`flex h-full w-full flex-col items-center justify-center gap-2 px-1 text-xs ${compact ? "font-display text-[10px]" : "bg-[rgba(34,39,45,0.72)] text-stone-500"}`}>
                  <span>{pageNum}</span>
                  {selectedPage === pageNum && selectedPageOcrStatus ? (
                    <Badge variant="outline" className="text-[9px]">
                      {selectedPageOcrStatus.status}
                    </Badge>
                  ) : null}
                  {selectedPage === pageNum
                    ? renderQualityBadge(
                        pageQualityMeta?.quality_level,
                        pageQualityMeta?.quality_score,
                        pageQualityMeta?.warning_reason,
                        'justify-center'
                      )
                    : null}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Main: Page Viewer */}
      <div className="flex-1 flex flex-col">
        {viewerError ? (
          <div className="border-b border-[rgba(189,90,86,0.32)] bg-[rgba(189,90,86,0.1)] px-4 py-2 text-sm text-[rgb(219,156,153)]">
            {viewerError}
          </div>
        ) : null}

        {/* Toolbar */}
        {variant === "workbench" ? null : (
        <div className={compact ? "border-b border-border bg-[hsl(var(--canvas))]" : "border-b border-[rgba(82,90,99,0.34)] bg-[rgba(20,24,28,0.78)]"}>
          <div className={compact ? "flex h-[38px] items-center gap-2.5 px-[18px]" : "flex min-h-12 items-center justify-between px-4 py-2"}>
            <div className="flex flex-wrap items-center gap-2">
              <span className={compact ? "text-[11px] font-medium text-muted-foreground" : "text-sm text-stone-300"}>
                Page {selectedPage} of {selectedDoc?.page_count || 0}
              </span>
              {compact ? (
                <>
                  <span className="cds-pill">{Math.round(zoom * 100)}%</span>
                  <button type="button" className="cds-btn cds-btn-ghost px-3" onClick={() => setZoom(Math.max(0.5, zoom - 0.25))}>−</button>
                  <button type="button" className="cds-btn cds-btn-ghost px-3" onClick={() => setZoom(Math.min(2, zoom + 0.25))}>+</button>
                  {highlightLabel ? (
                    <span className="font-display text-[10px] text-muted-foreground">Selected source: {highlightLabel}</span>
                  ) : null}
                </>
              ) : (
                <>
              {selectedDoc && selectedDoc.doc_type && (
                <Badge variant="outline" className="text-xs">
                  Type: {formatType(selectedDoc.doc_type)}
                </Badge>
              )}
              {selectedDoc?.predicted_doc_type && (
                <Badge variant="info" className="text-xs">Predicted: {formatType(selectedDoc.predicted_doc_type)}</Badge>
              )}
              {selectedDoc?.needs_review && (
                <Badge variant="warning" className="text-xs">Needs Review</Badge>
              )}
              {typeof selectedDoc?.classification_confidence === "number" && (
                <span className="text-xs text-stone-400">Conf {Math.round(Number(selectedDoc.classification_confidence) * 100)}%</span>
              )}
              {selectedDoc?.classification_status && (
                <span className="text-xs text-stone-400">Status {String(selectedDoc.classification_status)}</span>
              )}
              {selectedDoc && getOcrStatusBadge()}
              {renderQualityBadge(documentQualityLevel, pageQualityMeta?.quality_score, documentWarningReason)}
                </>
              )}
            </div>
            {compact ? null : (
            <div className="flex items-center gap-2">
              <Button size="sm" variant="outline" aria-label="Zoom out" onClick={() => setZoom(Math.max(0.5, zoom - 0.25))}>
                −
              </Button>
              <span className="w-12 text-center text-xs text-stone-400">{Math.round(zoom * 100)}%</span>
              <Button size="sm" variant="outline" aria-label="Zoom in" onClick={() => setZoom(Math.min(2, zoom + 0.25))}>
                +
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setZoom(1)}>Fit</Button>
              {onAttachEvidence && selectedDoc && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    const documentId = getDocumentId(selectedDoc);
                    if (!documentId) return;
                    onAttachEvidence(documentId, selectedPage);
                  }}
                >
                  Attach as Evidence
                </Button>
              )}
              {selectedDoc && (currentUser?.role === 'Admin' || currentUser?.role === 'Reviewer') && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleForceOcr}
                  disabled={ocrLoading}
                >
                  {ocrLoading ? 'Processing...' : 'Re-run OCR (force)'}
                </Button>
              )}
            </div>
            )}
          </div>
          
          {/* OCR Quality Info */}
          {ocrStatus && !compact ? (
            <div className="border-t border-[rgba(82,90,99,0.24)] bg-[rgba(18,22,27,0.62)] px-4 py-2">
              <div className="flex flex-wrap items-center gap-4 text-xs text-stone-400">
                {selectedPageOcrStatus ? <span>Page OCR: {selectedPageOcrStatus.status}</span> : null}
                {ocrStatus.average_ocr_chars_per_page && (
                  <span>Avg chars/page: {Math.round(ocrStatus.average_ocr_chars_per_page)}</span>
                )}
                {ocrStatus.processing_seconds && (
                  <span>Processing: {Math.round(ocrStatus.processing_seconds)}s</span>
                )}
                {Array.isArray(ocrStatus.quality_reasons) && ocrStatus.quality_reasons.length > 0 ? (
                  <span className="text-stone-500">{ocrStatus.quality_reasons[0]}</span>
                ) : null}
                {Array.isArray(ocrStatus?.failed_pages) && ocrStatus.failed_pages.length > 0 && (
                  <div className="flex items-center gap-2">
                    <span className="text-[rgb(219,156,153)]">Failed pages:</span>
                    {ocrStatus.failed_pages.map((fp, idx) => (
                      <button
                        key={idx}
                        onClick={() => setSelectedPage(fp.page_number)}
                        className="text-[rgb(219,156,153)] underline transition-colors hover:text-stone-100"
                      >
                        {fp.page_number}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : null}
        </div>
        )}

        {/* Page Image */}
        <div className={cn(compact ? "flex min-h-0 flex-1 gap-3.5 overflow-hidden bg-[hsl(var(--canvas))] p-[18px]" : "flex flex-1 items-center justify-center overflow-auto bg-[rgba(14,18,22,0.92)] p-4", evidenceMode === "text" && "hidden")}>
          <div className={compact
            ? "relative flex min-h-0 flex-1 items-start justify-center overflow-auto"
            : "relative flex h-full w-full items-center justify-center rounded-lg border border-[rgba(82,90,99,0.24)] bg-[rgba(18,22,27,0.52)] p-4"
          }>
            {pageImageUrl ? (
              <>
                {pageRenderMode === 'pdf' ? (
                  <iframe
                    src={pageImageUrl}
                    title={`Page ${selectedPage} of ${selectedDoc?.original_filename || 'document'}`}
                    className={compact
                      ? "h-full min-h-[520px] w-full border border-border bg-[#f2f0e5] shadow-none transition-opacity duration-150"
                      : "h-full min-h-[620px] w-full rounded-md border border-[rgba(82,90,99,0.22)] bg-[#f2f0e5] shadow-[0_18px_44px_rgba(0,0,0,0.24)] transition-opacity duration-150"
                    }
                    style={{ transform: `scale(${zoom})`, transformOrigin: 'center center', opacity: pageLoading ? 0.72 : 1 }}
                    onDoubleClick={() => onOpenFullViewer?.()}
                  />
                ) : (
                  <img
                    src={pageImageUrl}
                    alt={`Page ${selectedPage}`}
                    className={compact
                      ? "h-auto max-h-full border border-[#b2b2ad] bg-[#f2f0e5] object-contain shadow-none transition-opacity duration-150"
                      : "h-auto max-w-full rounded-md border border-[rgba(82,90,99,0.22)] shadow-[0_18px_44px_rgba(0,0,0,0.24)] transition-opacity duration-150"
                    }
                    style={{ transform: `scale(${zoom})`, opacity: pageLoading ? 0.72 : 1 }}
                    onDoubleClick={() => onOpenFullViewer?.()}
                  />
                )}
                {pageLoading ? (
                  <div className="absolute inset-0 flex items-center justify-center rounded-lg bg-black/24">
                    <div className="rounded-md border border-[rgba(82,90,99,0.36)] bg-[rgba(24,28,32,0.92)] px-3 py-2 text-xs text-stone-200">
                      Loading page {selectedPage}…
                    </div>
                  </div>
                ) : null}
              </>
            ) : pageLoading ? (
              <Skeleton className="h-full w-full max-w-4xl" />
            ) : (
              <div className="text-stone-400">No image available</div>
            )}
          </div>
          {compact && showHighlightPanel && (selectedSnippetText || highlightLabel) ? (
            <aside className={variant === "evidence"
              ? "flex w-[270px] shrink-0 flex-col gap-2.5 rounded-[5px] border border-border bg-[hsl(var(--surface))] p-3.5"
              : "flex w-[130px] shrink-0 flex-col gap-2"
            }>
              {variant === "workbench" ? <span className="cds-pill cds-pill-high w-fit">Selected</span> : <p className="cds-meta">Selected evidence</p>}
              {variant === "workbench" ? <p className="text-[10px] font-medium text-muted-foreground">Evidence highlight</p> : null}
              <p className="text-[12px] font-semibold text-foreground">{highlightLabel || "Selected text"}</p>
              <p className={variant === "evidence" ? "text-[26px] font-semibold leading-[38px] text-foreground" : "text-[20px] font-semibold leading-[29px] text-foreground"}>
                {selectedSnippetText || highlightValue || "—"}
              </p>
              <p className="text-[10px] text-muted-foreground">Source: p.{selectedPage}</p>
              {variant === "evidence" ? (
                <>
                  <div className="h-px bg-border" />
                  <p className="cds-meta">Candidate</p>
                  <span className="cds-pill cds-pill-proposed w-fit">Proposed</span>
                  {highlightLabel ? <p className="font-display text-[10px] text-muted-foreground">{highlightLabel}</p> : null}
                </>
              ) : null}
              <button
                type="button"
                className="cds-btn cds-btn-primary"
                onClick={() => {
                  const text = selectedSnippetText || ocrText;
                  if (!text) return;
                  onUseAsFact?.(text);
                }}
              >
                {variant === "evidence" ? "Use as field value" : "Use as fact"}
              </button>
              {variant === "evidence" ? (
                <button
                  type="button"
                  className="cds-btn cds-btn-ghost"
                  onClick={() => {
                    const documentId = getDocumentId(selectedDoc);
                    if (!documentId) return;
                    onAttachEvidence?.(documentId, selectedPage);
                  }}
                >
                  Attach to finding
                </button>
              ) : (
                <button
                  type="button"
                  className="cds-btn cds-btn-ghost"
                  onClick={() => {
                    const text = selectedSnippetText || ocrText;
                    if (!text) return;
                    navigator.clipboard.writeText(text);
                  }}
                >
                  Copy text
                </button>
              )}
            </aside>
          ) : null}
        </div>

        {/* OCR Text Panel - P14: Correction Support */}
        {evidenceMode !== "source" ? <div className={compact
          ? cn("flex shrink-0 flex-col overflow-hidden border-t border-border bg-[hsl(var(--surface))] px-4 py-3.5", evidenceMode === "text" ? "min-h-0 flex-1" : "h-[clamp(190px,26vh,280px)] min-h-[190px]")
          : "flex h-64 flex-col overflow-hidden border-t border-[rgba(82,90,99,0.34)] bg-[rgba(18,22,27,0.82)] p-4"
        }>
          <div className="-mx-1 mb-3 flex shrink-0 items-center justify-between gap-3 bg-[hsl(var(--surface))] px-1 pb-2">
            <div className="flex items-center gap-2">
              <h4 className={compact ? "cds-meta" : "text-sm font-medium text-stone-100"}>
                {variant === "evidence" ? "OCR / Native text" : compact ? "Extracted text" : "OCR Text"}
              </h4>
              {ocrTextData?.has_correction && (
                <Badge className="bg-amber-600/20 text-amber-200 border-amber-600/50 text-xs">
                  Corrected
                </Badge>
              )}
              {!editingOcr && (currentUser?.role === 'Admin' || currentUser?.role === 'Reviewer') && (
                <div className="flex gap-1">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setOcrMode('raw');
                    }}
                    className={ocrMode === 'raw' ? 'border-[rgba(152,161,135,0.3)] bg-[rgba(152,161,135,0.14)] text-stone-100' : ''}
                  >
                    Raw
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setOcrMode('effective');
                    }}
                    className={ocrMode === 'effective' ? 'border-[rgba(152,161,135,0.3)] bg-[rgba(152,161,135,0.14)] text-stone-100' : ''}
                  >
                    Effective
                  </Button>
                  {ocrTextData?.has_correction && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setOcrMode('corrected');
                      }}
                      className={ocrMode === 'corrected' ? 'border-[rgba(152,161,135,0.3)] bg-[rgba(152,161,135,0.14)] text-stone-100' : ''}
                    >
                      Corrected
                    </Button>
                  )}
                </div>
              )}
            </div>
            <div className="flex gap-2">
              {!editingOcr && (currentUser?.role === 'Admin' || currentUser?.role === 'Reviewer') && (
                <>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setEditingOcr(true);
                      setOcrCorrectionText(ocrTextData?.corrected_text || ocrTextData?.raw_text || ocrText);
                      setOcrCorrectionNote('');
                    }}
                  >
                    Edit OCR Text
                  </Button>
                  {ocrTextData?.has_correction && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setRevertDialogOpen(true)}
                    >
                      Revert to Raw
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant="default"
                    onClick={async () => {
                      setAutofilling(true);
                      try {
                        await autofillDossier(caseId, false);
                        toast({
                          title: 'Autofill completed.',
                          description: 'Review the OCR Extractions tab for refreshed field suggestions.',
                          variant: 'success',
                        });
                        router.push(getCaseTabPath(caseId, 'ocr-extractions'));
                      } catch (e: any) {
                        toast({
                          title: 'Autofill could not be completed.',
                          description: e.message || 'Please retry.',
                          variant: 'error',
                        });
                      } finally {
                        setAutofilling(false);
                      }
                    }}
                    disabled={autofilling}
                  >
                    {autofilling ? 'Running...' : 'Re-run Autofill'}
                  </Button>
                </>
              )}
              {selectedSnippet && !editingOcr && (currentUser?.role === 'Admin' || currentUser?.role === 'Reviewer') && (
                <Button
                  size="sm"
                  variant="default"
                  onClick={() => setShowSnippetModal(true)}
                >
                  Attach Selected Text
                </Button>
              )}
              {!editingOcr && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    if (ocrText) {
                      navigator.clipboard.writeText(ocrText);
                      toast({
                        title: 'OCR text copied.',
                        description: 'The current page text is now on the clipboard.',
                        variant: 'success',
                      });
                    }
                  }}
                >
                  Copy
                </Button>
              )}
            </div>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto">
          {editingOcr ? (
            <div className="space-y-3">
              <div className="bg-amber-900/20 border border-amber-700 rounded p-2 text-xs text-amber-200">
                You are editing OCR text corrections (does not overwrite raw OCR).
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-stone-300">Corrected Text</label>
                <textarea
                  value={ocrCorrectionText}
                  onChange={(e) => setOcrCorrectionText(e.target.value)}
                  className="cds-extract-text w-full rounded border border-[rgba(82,90,99,0.42)] bg-[rgba(18,22,27,0.82)] px-3 py-2 text-xs text-stone-100"
                  rows={8}
                  {...urduTextProps(ocrCorrectionText)}
                />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-stone-300">
                  Note <span className="text-red-400">*</span>
                </label>
                <textarea
                  value={ocrCorrectionNote}
                  onChange={(e) => setOcrCorrectionNote(e.target.value)}
                  className="w-full rounded border border-[rgba(82,90,99,0.42)] bg-[rgba(18,22,27,0.82)] px-3 py-2 text-stone-100"
                  rows={2}
                  placeholder="Explain the correction (min 5 characters)"
                />
                {ocrCorrectionNote.length > 0 && ocrCorrectionNote.length < 5 && (
                  <p className="text-xs text-red-400 mt-1">Note must be at least 5 characters</p>
                )}
              </div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setEditingOcr(false);
                    setOcrCorrectionText('');
                    setOcrCorrectionNote('');
                  }}
                >
                  Cancel
                </Button>
                <Button
                  size="sm"
                  variant="default"
                  onClick={async () => {
                    if (ocrCorrectionNote.trim().length < 5) {
                      toast({
                        title: 'Correction note is too short.',
                        description: 'Provide at least 5 characters before saving.',
                        variant: 'error',
                      });
                      return;
                    }
                    setSavingCorrection(true);
                    try {
                      const documentId = getDocumentId(selectedDoc);
                      if (!documentId) {
                        throw new Error('No document selected');
                      }
                      await putOcrTextCorrection(documentId, selectedPage, {
                        corrected_text: ocrCorrectionText,
                        note: ocrCorrectionNote,
                      });
                      setEditingOcr(false);
                      setOcrCorrectionText('');
                      setOcrCorrectionNote('');
                      await loadPage();
                      toast({
                        title: 'OCR correction saved.',
                        description: 'The corrected text is now active for this page.',
                        variant: 'success',
                      });
                    } catch (e: any) {
                      toast({
                        title: 'Unable to save OCR correction.',
                        description: e.message || 'Please retry.',
                        variant: 'error',
                      });
                    } finally {
                      setSavingCorrection(false);
                    }
                  }}
                  disabled={savingCorrection || ocrCorrectionNote.trim().length < 5}
                >
                  {savingCorrection ? 'Saving...' : 'Save Correction'}
                </Button>
              </div>
            </div>
          ) : (
            <>
            <div
              className={cn(
                "cds-extract-text select-text whitespace-pre-wrap",
                compact
                  ? "max-w-none text-[13px] leading-7 text-foreground"
                  : "rounded-md border border-[rgba(82,90,99,0.22)] bg-[rgba(14,18,22,0.5)] px-3 py-2 text-xs text-stone-300"
              )}
              {...urduTextProps(ocrText)}
              onMouseUp={() => {
                const selection = window.getSelection();
                if (selection && selection.toString().trim()) {
                  setSelectedSnippet(selection.toString().trim());
                } else {
                  setSelectedSnippet('');
                }
              }}
            >
              {ocrText || 'OCR text not available'}
            </div>
            {compact && highlightLabel && selectedSnippetText ? (
              <p className="mt-2 font-display text-[10px] text-muted-foreground">
                {variant === "evidence"
                  ? "Text is preserved as extracted. Reviewer corrections create a separate audited value."
                  : `Selected fact: ${highlightLabel} = ${selectedSnippetText}`}
              </p>
            ) : compact && variant === "evidence" ? (
              <p className="mt-2 text-[10px] text-muted-foreground">
                Text is preserved as extracted. Reviewer corrections create a separate audited value.
              </p>
            ) : null}
            </>
          )}
          </div>
        </div> : null}

        {/* Snippet Attachment Modal */}
        {showSnippetModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
            <div className="w-full max-w-md rounded-md border border-[rgba(82,90,99,0.42)] bg-[linear-gradient(180deg,rgba(23,28,33,0.96),rgba(17,21,25,0.96))] p-6">
              <h3 className="mb-4 text-lg font-semibold text-stone-100">Attach Snippet as Evidence</h3>
              
              <div className="mb-4">
                <label className="mb-2 block text-sm font-medium text-stone-300">Selected Text:</label>
                <div className="max-h-32 overflow-y-auto rounded border border-[rgba(82,90,99,0.42)] bg-[rgba(18,22,27,0.82)] p-2 text-xs text-stone-300">
                  {selectedSnippet}
                </div>
              </div>

              <div className="mb-4">
                <label className="mb-2 block text-sm font-medium text-stone-300">Attach to:</label>
                <select
                  className="w-full rounded border border-[rgba(82,90,99,0.42)] bg-[rgba(18,22,27,0.82)] px-3 py-2 text-stone-100"
                  value={snippetTarget || ''}
                  onChange={(e) => {
                    setSnippetTarget(
                      e.target.value === 'exception' || e.target.value === 'cp'
                        ? e.target.value
                        : null
                    );
                    setSnippetTargetId('');
                  }}
                >
                  <option value="">Select target...</option>
                  <option value="exception">Exception</option>
                  <option value="cp">Condition Precedent (CP)</option>
                </select>
              </div>

              {snippetTarget && (
                <div className="mb-4">
                  <label className="mb-2 block text-sm font-medium text-stone-300">
                    {snippetTarget === 'exception' ? 'Exception:' : 'CP:'}
                  </label>
                  <select
                    className="w-full rounded border border-[rgba(82,90,99,0.42)] bg-[rgba(18,22,27,0.82)] px-3 py-2 text-stone-100"
                    value={snippetTargetId}
                    onChange={(e) => setSnippetTargetId(e.target.value)}
                  >
                    <option value="">Select {snippetTarget === 'exception' ? 'exception' : 'CP'}...</option>
                    {snippetTarget === 'exception' && exceptions.map((exc) => (
                      <option key={exc.id} value={exc.id}>
                        {exc.title} ({exc.severity})
                      </option>
                    ))}
                    {snippetTarget === 'cp' && cps.map((cp) => (
                      <option key={cp.id} value={cp.id}>
                        {cp.text} ({cp.severity})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div className="flex gap-2 justify-end">
                <Button
                  variant="outline"
                  onClick={() => {
                    setShowSnippetModal(false);
                    setSelectedSnippet('');
                    setSnippetTarget(null);
                    setSnippetTargetId('');
                  }}
                >
                  Cancel
                </Button>
                <Button
                  variant="default"
                  disabled={!snippetTarget || !snippetTargetId || !selectedSnippet || attachingSnippet}
                  onClick={async () => {
                    const documentId = getDocumentId(selectedDoc);
                    if (!documentId || !snippetTarget || !snippetTargetId || !selectedSnippet) return;
                    
                    try {
                      setAttachingSnippet(true);
                      if (snippetTarget === 'exception') {
                        await attachExceptionEvidenceSnippet(
                          snippetTargetId,
                          documentId,
                          selectedPage,
                          selectedSnippet
                        );
                      } else {
                        await attachCPEvidenceSnippet(
                          snippetTargetId,
                          documentId,
                          selectedPage,
                          selectedSnippet
                        );
                      }

                      setShowSnippetModal(false);
                      setSelectedSnippet('');
                      setSnippetTarget(null);
                      setSnippetTargetId('');
                      toast({
                        title: 'Evidence snippet attached.',
                        description: 'The selected text is now linked to the review item.',
                        variant: 'success',
                      });
                    } catch (e: any) {
                      setViewerError(e.message || 'Failed to attach evidence snippet');
                      toast({
                        title: 'Unable to attach evidence snippet.',
                        description: e.message || 'Please retry.',
                        variant: 'error',
                      });
                    } finally {
                      setAttachingSnippet(false);
                    }
                  }}
                >
                  {attachingSnippet ? 'Attaching...' : 'Attach'}
                </Button>
              </div>
            </div>
          </div>
        )}

        <Dialog open={deleteDocDialogOpen} onOpenChange={setDeleteDocDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Remove Document</DialogTitle>
              <DialogDescription>
                Permanently delete &ldquo;{documentToDelete?.original_filename}&rdquo; and all its pages from this case? This cannot be undone.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeleteDocDialogOpen(false)} disabled={deletingDoc}>
                Cancel
              </Button>
              <Button variant="danger" loading={deletingDoc} onClick={() => void handleConfirmDeleteDocument()}>
                {deletingDoc ? 'Removing...' : 'Remove Document'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        <Dialog open={revertDialogOpen} onOpenChange={setRevertDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Revert OCR Correction</DialogTitle>
              <DialogDescription>
                This will remove the current correction and restore the raw OCR text for this page.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setRevertDialogOpen(false)} disabled={deletingCorrection}>
                Cancel
              </Button>
              <Button
                variant="danger"
                loading={deletingCorrection}
                onClick={async () => {
                  const documentId = getDocumentId(selectedDoc);
                  if (!documentId) return;

                  setDeletingCorrection(true);
                  try {
                    await deleteOcrTextCorrection(documentId, selectedPage);
                    setRevertDialogOpen(false);
                    await loadPage();
                    toast({
                      title: 'OCR correction reverted.',
                      description: 'The raw OCR text is active again for this page.',
                      variant: 'success',
                    });
                  } catch (e: any) {
                    toast({
                      title: 'Unable to revert OCR correction.',
                      description: e.message || 'Please retry.',
                      variant: 'error',
                    });
                  } finally {
                    setDeletingCorrection(false);
                  }
                }}
              >
                {deletingCorrection ? 'Reverting...' : 'Revert to Raw'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}











