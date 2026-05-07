'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Drawer } from '@/components/ui/drawer';
import { EmptyState } from '@/components/ui/empty-state';
import {
  listOCRExtractions,
  editOCRExtraction,
  confirmOCRExtraction,
  rejectOCRExtraction,
  overrideOCRExtraction,
  OCRExtractionItem,
  OCRExtractionsResponse,
  enqueueOcr,
  autofillDossier,
} from '@/lib/api';
import { useRouter, useSearchParams } from 'next/navigation';
import { getCaseDocumentFocusPath } from '@/lib/routes';
import { getFieldLabelMeta } from '@/lib/field-labels';

interface OCRExtractionsPanelProps {
  caseId: string;
  documents?: Array<{ id: string; original_filename?: string; filename?: string }>;
  onViewDocument?: (documentId: string, pageNumber: number) => void;
}

const EMPTY_EXTRACTION_COUNTS = {
  pending: 0,
  confirmed: 0,
  rejected: 0,
} as const;

const WARNING_REASON_LABELS: Record<string, string> = {
  junk_token_pattern: 'Junk OCR token',
  short_cnic_candidate: 'CNIC too short',
  invalid_cnic_format: 'Invalid CNIC format',
  malformed_amount: 'Invalid amount',
  invalid_date_format: 'Invalid date',
  name_high_digit_ratio: 'Name contains digits',
  short_name_candidate: 'Short name',
  low_quality_page: 'Low quality page',
};

function normalizeConfidencePercentage(confidence: number | null): number | null {
  if (confidence === null) {
    return null;
  }

  let normalized = confidence;
  if (normalized > 1.5 && normalized <= 100) {
    normalized = normalized / 100;
  } else if (normalized > 100 && normalized <= 10000) {
    normalized = normalized / 100;
    if (normalized > 1.0) {
      normalized = 1.0;
    }
  }

  normalized = Math.max(0.0, Math.min(1.0, normalized));
  return Math.max(0, Math.min(100, Math.round(normalized * 100)));
}

function getWarningReasonLabel(reason?: string | null): string | null {
  if (!reason) {
    return null;
  }

  return WARNING_REASON_LABELS[reason] ?? reason;
}

function isNeedsReviewCandidate(item: OCRExtractionItem): boolean {
  if (item.review_status === 'needs_review' || item.needs_review === true) {
    return true;
  }

  return Boolean(item.is_low_quality && item.status === 'Pending');
}

type ConfidenceState = 'GOOD' | 'LOW' | 'REVIEW_REQUIRED';

const FIELD_KEY_ALIASES: Record<string, string> = {
  'property.plot_number': 'property.plot_no',
  'party.name.seller': 'party.name.raw',
  'party.seller.names': 'party.name.raw',
};

const FIELD_GUIDANCE: Record<string, string> = {
  'party.name.raw': 'Verify name matches sale deed exactly',
  'property.scheme_name': 'Must match approved society name (e.g. DHA, Bahria Town)',
  'property.plot_no': 'Cross-check with registry records',
};

const PROPERTY_DETAIL_FIELDS = new Set([
  'property.scheme_name',
  'property.phase',
  'property.block',
  'property.plot_no',
  'property.plot_number',
]);

const OWNERSHIP_FIELDS = new Set([
  'party.name.raw',
  'party.name.seller',
  'party.seller.names',
  'party.name.borrower',
  'party.name.buyer',
  'party.buyer.names',
]);

function normalizeFieldKey(fieldKey: string): string {
  return FIELD_KEY_ALIASES[fieldKey] ?? fieldKey;
}

function getConfidenceState(item: OCRExtractionItem): ConfidenceState {
  const quality = (item.quality_level || '').toUpperCase();
  if (item.review_status === 'needs_review' || item.needs_review || quality === 'REVIEW_REQUIRED') {
    return 'REVIEW_REQUIRED';
  }

  if (item.is_low_quality || quality === 'LOW' || quality === 'LOW_CONFIDENCE') {
    return 'LOW';
  }

  return 'GOOD';
}

function getConfidencePriority(item: OCRExtractionItem): number {
  const state = getConfidenceState(item);
  if (state === 'REVIEW_REQUIRED') {
    return 0;
  }

  if (state === 'LOW') {
    return 1;
  }

  return 2;
}

function getSectionName(fieldKey: string): 'Property Details' | 'Ownership' | 'Other Fields' {
  const normalized = normalizeFieldKey(fieldKey);
  if (PROPERTY_DETAIL_FIELDS.has(normalized)) {
    return 'Property Details';
  }

  if (OWNERSHIP_FIELDS.has(normalized)) {
    return 'Ownership';
  }

  return 'Other Fields';
}

function getFieldPresentation(fieldKey: string): { label: string; subtitle: string; guidance?: string } {
  const normalized = normalizeFieldKey(fieldKey);
  const meta = getFieldLabelMeta(normalized);
  return {
    ...meta,
    guidance: FIELD_GUIDANCE[normalized],
  };
}

function getConfidenceBadgeClass(state: ConfidenceState): string {
  if (state === 'REVIEW_REQUIRED') {
    return 'bg-red-100 text-red-800';
  }

  if (state === 'LOW') {
    return 'bg-yellow-100 text-yellow-800';
  }

  return 'bg-green-100 text-green-800';
}

function getConfidenceMessage(state: ConfidenceState): string | null {
  if (state === 'LOW') {
    return 'Low confidence — please verify before confirming';
  }

  if (state === 'REVIEW_REQUIRED') {
    return 'This field likely requires manual review (handwritten or unclear source)';
  }

  return null;
}

function normalizeExtractionsResponse(
  response: OCRExtractionsResponse | null | undefined
): OCRExtractionsResponse | null {
  if (!response) {
    return null;
  }

  return {
    ...response,
    counts: {
      ...EMPTY_EXTRACTION_COUNTS,
      ...(response.counts ?? {}),
    },
    items: Array.isArray(response.items) ? response.items : [],
  };
}

export function OCRExtractionsPanel({ caseId, documents = [], onViewDocument }: OCRExtractionsPanelProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  // Initialize filter from URL, default to 'all'
  const initialFilter = (searchParams.get('ocrStatus') || 'all') as 'all' | 'pending' | 'confirmed' | 'rejected';
  const [statusFilter, setStatusFilter] = useState<'all' | 'pending' | 'confirmed' | 'rejected'>(initialFilter);
  
  const [data, setData] = useState<OCRExtractionsResponse | null>(null);
  const [fullCounts, setFullCounts] = useState<{ pending: number; confirmed: number; rejected: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [rejectingId, setRejectingId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState<string>('');
  const [debounceTimers, setDebounceTimers] = useState<Map<string, NodeJS.Timeout>>(new Map());
  const [savingEdit, setSavingEdit] = useState<Set<string>>(new Set());
  const [confirming, setConfirming] = useState<Set<string>>(new Set());
  const [rejecting, setRejecting] = useState<Set<string>>(new Set());
  const [editValues, setEditValues] = useState<Map<string, string>>(new Map());
  const [abortControllers, setAbortControllers] = useState<Map<string, AbortController>>(new Map());
  const [forceConfirmingId, setForceConfirmingId] = useState<string | null>(null);
  const [forceConfirmReason, setForceConfirmReason] = useState<string>('');
  const [overridingId, setOverridingId] = useState<string | null>(null);
  const [overrideValue, setOverrideValue] = useState<string>('');
  const [overrideNote, setOverrideNote] = useState<string>('');
  const [viewingEvidenceId, setViewingEvidenceId] = useState<string | null>(null);
  const [panelError, setPanelError] = useState<string | null>(null);

  const loadExtractions = useCallback(async () => {
    try {
      setLoading(true);
      const result = normalizeExtractionsResponse(
        await listOCRExtractions(caseId, statusFilter === 'all' ? undefined : statusFilter)
      );
      if (!result) {
        throw new Error('Failed to load OCR extractions');
      }
      setData(result);
      setPanelError(null);
      
      // Always fetch full counts (without filter) to get accurate totals
      if (statusFilter !== 'all') {
        const fullResult = normalizeExtractionsResponse(await listOCRExtractions(caseId, undefined));
        setFullCounts(fullResult?.counts ?? EMPTY_EXTRACTION_COUNTS);
      } else {
        setFullCounts(result.counts);
      }
    } catch (e: any) {
      setPanelError(e.message || 'Failed to load OCR extractions');
    } finally {
      setLoading(false);
    }
  }, [caseId, statusFilter]);

  // Sync filter from URL on mount or URL change
  useEffect(() => {
    const urlFilter = (searchParams.get('ocrStatus') || 'all') as 'all' | 'pending' | 'confirmed' | 'rejected';
    if (urlFilter !== statusFilter) {
      setStatusFilter(urlFilter);
    }
  }, [searchParams, statusFilter]);

  useEffect(() => {
    void loadExtractions();
  }, [loadExtractions]);

  const counts = data?.counts ?? EMPTY_EXTRACTION_COUNTS;
  const items = useMemo(() => {
    const sourceItems = Array.isArray(data?.items) ? data.items : [];

    const groupedOrder: Record<'Property Details' | 'Ownership' | 'Other Fields', number> = {
      'Property Details': 0,
      Ownership: 1,
      'Other Fields': 2,
    };

    return [...sourceItems].sort((left, right) => {
      const confidenceDelta = getConfidencePriority(left) - getConfidencePriority(right);
      if (confidenceDelta !== 0) {
        return confidenceDelta;
      }

      const sectionDelta = groupedOrder[getSectionName(left.field_key)] - groupedOrder[getSectionName(right.field_key)];
      if (sectionDelta !== 0) {
        return sectionDelta;
      }

      return left.field_key.localeCompare(right.field_key);
    });
  }, [data?.items]);

  const handleEditChange = (item: OCRExtractionItem, value: string) => {
    // Update local edit value immediately
    setEditValues(prev => {
      const next = new Map(prev);
      next.set(item.id, value);
      return next;
    });
    
    // Cancel previous debounce timer for this item
    const existingTimer = debounceTimers.get(item.id);
    if (existingTimer) {
      clearTimeout(existingTimer);
    }
    
    // Cancel previous abort controller
    const existingAbort = abortControllers.get(item.id);
    if (existingAbort) {
      existingAbort.abort();
    }
    
    // Create new abort controller
    const abortController = new AbortController();
    setAbortControllers(prev => {
      const next = new Map(prev);
      next.set(item.id, abortController);
      return next;
    });
    
    // Set new timer for debounced save
    const timer = setTimeout(async () => {
      try {
        setSavingEdit(prev => new Set(prev).add(item.id));
        await editOCRExtraction(item.id, value.trim() || null);
        await loadExtractions();
      } catch (e: any) {
        if (e.name !== 'AbortError') {
          setPanelError(e.message || 'Failed to save extraction edit');
          alert(`Failed to save edit: ${e.message || 'Unknown error'}`);
        }
      } finally {
        setSavingEdit(prev => {
          const next = new Set(prev);
          next.delete(item.id);
          return next;
        });
      }
    }, 800);
    
    setDebounceTimers(prev => {
      const next = new Map(prev);
      next.set(item.id, timer);
      return next;
    });
  };

  const handleConfirm = async (item: OCRExtractionItem, e?: React.MouseEvent, forceConfirm?: boolean) => {
    // Prevent event bubbling
    if (e) {
      e.stopPropagation();
      e.preventDefault();
    }
    
    // Prevent double-firing - must check before setting state
    if (confirming.has(item.id) || savingEdit.has(item.id)) {
      return;
    }
    
    // If low quality and not force confirming, show modal (don't set confirming state for modal)
    if (item.is_low_quality && !forceConfirm) {
      setForceConfirmingId(item.id);
      setForceConfirmReason('');
      return;
    }
    
    // Set confirming state IMMEDIATELY to prevent race conditions (after all early returns)
    setConfirming(prev => new Set(prev).add(item.id));
    
    try {
      // Optimistic update: remove from pending list immediately
      if (data) {
        const updatedItems = data.items.filter(i => i.id !== item.id);
        setData({
          ...data,
          items: updatedItems,
          counts: {
            ...data.counts,
            pending: Math.max(0, data.counts.pending - 1),
            confirmed: data.counts.confirmed + 1,
          },
        });
      }
      
      await confirmOCRExtraction(item.id, undefined, undefined, forceConfirm || false, false);
      
      // Reload to get final state (server has confirmed, so this should show it as confirmed)
      await loadExtractions();
      
      // Close force confirm modal if open
      if (forceConfirm) {
        setForceConfirmingId(null);
        setForceConfirmReason('');
      }
    } catch (error: any) {
      setPanelError(error.message || 'Failed to confirm extraction');
      
      // Revert optimistic update on error by reloading
      await loadExtractions();
      
      // P14: Check for format validation error
      if (error.message && error.message.includes('format') && error.message.includes('force_format')) {
        alert(`Format invalid - please edit value to match required format: ${error.message}`);
        return;
      }
      
      // If error mentions force_confirm, show modal
      if (error.message && error.message.includes('force_confirm')) {
        setForceConfirmingId(item.id);
        setForceConfirmReason('');
      } else {
        alert(`Failed to confirm: ${error.message || 'Unknown error'}`);
      }
    } finally {
      setConfirming(prev => {
        const next = new Set(prev);
        next.delete(item.id);
        return next;
      });
    }
  };

  const handleOverride = async (item: OCRExtractionItem, e?: React.MouseEvent) => {
    // Prevent event bubbling
    if (e) {
      e.stopPropagation();
      e.preventDefault();
    }
    
    if (!overrideValue.trim()) {
      alert('Please provide an override value');
      return;
    }
    
    try {
      await overrideOCRExtraction(item.id, overrideValue.trim(), overrideNote.trim() || undefined);
      await loadExtractions();
      setOverridingId(null);
      setOverrideValue('');
      setOverrideNote('');
    } catch (error: any) {
      setPanelError(error.message || 'Failed to override extraction');
      alert(`Failed to override: ${error.message || 'Unknown error'}`);
    }
  };

  const handleReject = async (e?: React.MouseEvent) => {
    // Prevent event bubbling
    if (e) {
      e.stopPropagation();
      e.preventDefault();
    }
    
    if (!rejectingId || !rejectReason.trim()) {
      alert('Please provide a rejection reason');
      return;
    }
    
    // Prevent double-firing
    if (rejecting.has(rejectingId)) {
      return;
    }
    
    try {
      setRejecting(prev => new Set(prev).add(rejectingId!));
      
      // Optimistic update
      if (data) {
        const updatedItems = data.items.filter(i => i.id !== rejectingId);
        setData({
          ...data,
          items: updatedItems,
          counts: {
            ...data.counts,
            pending: Math.max(0, data.counts.pending - 1),
            rejected: data.counts.rejected + 1,
          },
        });
      }
      
      await rejectOCRExtraction(rejectingId, rejectReason.trim());
      
      // Reload to get final state
      await loadExtractions();
      setRejectingId(null);
      setRejectReason('');
    } catch (error: any) {
      setPanelError(error.message || 'Failed to reject extraction');
      
      // Revert optimistic update on error
      await loadExtractions();
      alert(`Failed to reject: ${error.message || 'Unknown error'}`);
    } finally {
      setRejecting(prev => {
        const next = new Set(prev);
        if (rejectingId) {
          next.delete(rejectingId);
        }
        return next;
      });
    }
  };

  if (loading && !data) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (!data) {
    return (
      <EmptyState
        title="OCR Extractions unavailable."
        description={panelError ?? 'No OCR extractions are available for this case yet.'}
        className="min-h-[220px]"
      />
    );
  }

  const isEdited = (item: OCRExtractionItem) => item.edited_value !== null && item.edited_value !== item.proposed_value;
  const totalExtractions =
    (fullCounts?.pending ?? counts.pending) +
    (fullCounts?.confirmed ?? counts.confirmed) +
    (fullCounts?.rejected ?? counts.rejected);

  return (
    <div className="space-y-4">
      {panelError ? (
        <div className="rounded-lg border border-[rgba(189,90,86,0.36)] bg-[rgba(189,90,86,0.12)] px-4 py-3 text-sm text-[rgb(219,156,153)]">
          {panelError}
        </div>
      ) : null}

      {/* Header with counts and filters */}
      <div className="flex justify-between items-center">
        <div className="flex gap-4 items-center">
          <div>
            <span className="text-slate-400">Confirmed: </span>
            <span className="font-semibold text-green-400">{fullCounts?.confirmed ?? counts.confirmed}</span>
          </div>
          <div>
            <span className="text-slate-400">Pending: </span>
            <span className="font-semibold text-yellow-400">{fullCounts?.pending ?? counts.pending}</span>
          </div>
          <div>
            <span className="text-slate-400">Rejected: </span>
            <span className="font-semibold text-red-400">{fullCounts?.rejected ?? counts.rejected}</span>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            variant={statusFilter === 'all' ? 'default' : 'outline'}
            size="sm"
            onClick={() => {
              const newFilter = 'all';
              setStatusFilter(newFilter);
              // Update URL without reload
              const params = new URLSearchParams(searchParams.toString());
              params.set('ocrStatus', newFilter);
              router.replace(`?${params.toString()}`, { scroll: false });
            }}
          >
            All
          </Button>
          <Button
            variant={statusFilter === 'pending' ? 'default' : 'outline'}
            size="sm"
            onClick={() => {
              const newFilter = 'pending';
              setStatusFilter(newFilter);
              const params = new URLSearchParams(searchParams.toString());
              params.set('ocrStatus', newFilter);
              router.replace(`?${params.toString()}`, { scroll: false });
            }}
          >
            Pending
          </Button>
          <Button
            variant={statusFilter === 'confirmed' ? 'default' : 'outline'}
            size="sm"
            onClick={() => {
              const newFilter = 'confirmed';
              setStatusFilter(newFilter);
              const params = new URLSearchParams(searchParams.toString());
              params.set('ocrStatus', newFilter);
              router.replace(`?${params.toString()}`, { scroll: false });
            }}
          >
            Confirmed
          </Button>
          <Button
            variant={statusFilter === 'rejected' ? 'default' : 'outline'}
            size="sm"
            onClick={() => {
              const newFilter = 'rejected';
              setStatusFilter(newFilter);
              const params = new URLSearchParams(searchParams.toString());
              params.set('ocrStatus', newFilter);
              router.replace(`?${params.toString()}`, { scroll: false });
            }}
          >
            Rejected
          </Button>
        </div>
      </div>

      {/* Items list */}
      {items.length === 0 ? (
        <div className="text-center py-8 text-slate-400">
          {statusFilter === 'pending' ? (
            <div className="space-y-4">
              {/* Improved empty state for pending=0 but confirmed>0 */}
              {(fullCounts?.confirmed ?? counts.confirmed) > 0 || (fullCounts?.rejected ?? counts.rejected) > 0 ? (
                <div className="space-y-3">
                  <div className="space-y-2">
                    <p className="text-slate-300 font-medium">No pending OCR extractions found.</p>
                    <p className="text-sm text-slate-500">
                      Confirmed: {fullCounts?.confirmed ?? counts.confirmed}. {(fullCounts?.rejected ?? counts.rejected) > 0 ? `Rejected: ${fullCounts?.rejected ?? counts.rejected}. ` : ''}
                      Use 'All' or 'Confirmed' to review.
                    </p>
                  </div>
                  <div className="flex gap-3 justify-center">
                    <button
                      className="btn btn-primary"
                      onClick={() => {
                        const newFilter = 'confirmed';
                        setStatusFilter(newFilter);
                        const params = new URLSearchParams(searchParams.toString());
                        params.set('ocrStatus', newFilter);
                        router.replace(`?${params.toString()}`, { scroll: false });
                      }}
                    >
                      Show Confirmed
                    </button>
                    <button
                      className="btn btn-secondary"
                      onClick={() => {
                        const newFilter = 'all';
                        setStatusFilter(newFilter);
                        const params = new URLSearchParams(searchParams.toString());
                        params.set('ocrStatus', newFilter);
                        router.replace(`?${params.toString()}`, { scroll: false });
                      }}
                    >
                      Show All
                    </button>
                  </div>
                </div>
              ) : (
                /* Truly empty state - no extractions at all */
                <div className="space-y-4">
                  <div className="space-y-2">
                    <p className="text-slate-300 font-medium">No pending OCR extractions found.</p>
                    <p className="text-sm text-slate-500">
                      OCR Extractions are generated by running Autofill on OCR text from documents.
                    </p>
                  </div>
                  {/* Empty state CTAs */}
                  {(fullCounts?.confirmed ?? counts.confirmed) === 0 && (fullCounts?.rejected ?? counts.rejected) === 0 && (
                    <div className="flex flex-col gap-3 items-center pt-4">
                      {documents && documents.length > 0 ? (
                        <>
                          <button
                            className="btn btn-primary"
                            onClick={async () => {
                              try {
                                // Run OCR for all documents sequentially
                                for (const doc of documents) {
                                  try {
                                    await enqueueOcr(doc.id, false);
                                  } catch {
                                    setPanelError(`Failed to queue OCR for document ${doc.id}.`);
                                  }
                                }
                                alert('OCR processing started for all documents. This may take a few moments.');
                                // Reload extractions after a delay to check for new candidates
                                setTimeout(() => loadExtractions(), 3000);
                              } catch (e: any) {
                                alert(`Failed to run OCR: ${e.message || 'Unknown error'}`);
                              }
                            }}
                          >
                            Run OCR for all documents
                          </button>
                          <button
                            className="btn btn-secondary"
                            onClick={async () => {
                              try {
                                await autofillDossier(caseId, false);
                                alert('Autofill completed. Review OCR Extractions for candidates.');
                                await loadExtractions();
                              } catch (e: any) {
                                alert(`Autofill failed: ${e.message || 'Unknown error'}`);
                              }
                            }}
                          >
                            Generate OCR Extractions (Autofill)
                          </button>
                          <p className="text-xs text-slate-500 mt-2">
                            Run OCR first to extract text from documents, then run Autofill to generate extraction candidates.
                          </p>
                        </>
                      ) : (
                        <p className="text-sm text-slate-500">
                          Upload documents first, then run OCR and Autofill to generate extraction candidates.
                        </p>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            totalExtractions === 0 ? (
              <EmptyState
                title="No OCR extractions yet"
                description={
                  documents.length > 0
                    ? 'Run OCR and autofill to generate extraction candidates for this case.'
                    : 'Upload documents first, then run OCR and autofill to generate extraction candidates.'
                }
                className="min-h-[220px]"
              />
            ) : (
              <p>No {statusFilter === 'all' ? '' : statusFilter} extractions found</p>
            )
          )}
        </div>
      ) : (
        <div className="space-y-3">
                    {items.map((item, index) => {
            const confidencePercent = normalizeConfidencePercentage(item.confidence);
            const warningLabel = getWarningReasonLabel(item.warning_reason);
            const needsReview = isNeedsReviewCandidate(item);
            const autofillBlocked = item.review_status === 'needs_review' || (needsReview && item.status === 'Pending');
            const fieldPresentation = getFieldPresentation(item.field_key);
            const confidenceState = getConfidenceState(item);
            const confidenceMessage = getConfidenceMessage(confidenceState);
            const sectionName = getSectionName(item.field_key);
            const previousSection = index > 0 ? getSectionName(items[index - 1].field_key) : null;
            const showSectionHeader = sectionName !== previousSection;

            return (
              <div key={item.id} className="space-y-2">
                {showSectionHeader ? (
                  <div className="pt-2">
                    <div className="text-sm font-semibold text-stone-200">{sectionName}</div>
                    <div className="mt-1 h-px w-full bg-[rgba(82,90,99,0.35)]" />
                  </div>
                ) : null}
                <div
                  className="rounded-lg border border-[rgba(82,90,99,0.42)] bg-[rgba(18,22,27,0.82)] p-4"
                  onClick={(e) => e.stopPropagation()}
                >
              <div className="flex gap-4 items-start">
                {/* Left: Field key + metadata */}
                <div className="flex-1 min-w-0">
                                    <div className="mb-2 flex flex-wrap items-start gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-stone-100">{fieldPresentation.label}</span>
                        <span
                          className="inline-flex h-4 w-4 cursor-help items-center justify-center rounded-full border border-[rgba(127,138,149,0.45)] text-[10px] text-stone-300"
                          title={fieldPresentation.guidance || fieldPresentation.subtitle}
                          aria-label={fieldPresentation.guidance || fieldPresentation.subtitle}
                        >
                          i
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-stone-500">{fieldPresentation.subtitle}</p>
                      {fieldPresentation.guidance ? (
                        <p className="mt-1 text-xs text-[rgb(194,200,185)]">i {fieldPresentation.guidance}</p>
                      ) : null}
                    </div>
                    <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-semibold ${getConfidenceBadgeClass(confidenceState)}`}>
                      {confidenceState}
                    </span>
                    {isEdited(item) && (
                      <Badge variant="outline" className="text-xs">Edited</Badge>
                    )}
                    {item.is_overridden && (
                      <Badge variant="neutral" className="text-xs">
                        Manual Override
                      </Badge>
                    )}
                    {item.status === 'Confirmed' && (
                      <Badge variant="success">Confirmed</Badge>
                    )}
                    {item.status === 'Rejected' && (
                      <Badge variant="error">Rejected</Badge>
                    )}
                    {autofillBlocked ? (
                      <Badge variant="error" className="text-xs">
                        Autofill Blocked
                      </Badge>
                    ) : null}
                    {item.extraction_method && (
                      <Badge variant="outline" className="text-xs">
                        {item.extraction_method}
                        {item.evidence_json?.label && ` · ${item.evidence_json.label}`}
                      </Badge>
                    )}
                  </div>
                  {confidenceMessage && item.status === 'Pending' ? (
                    <p className="mb-2 text-xs text-stone-300">{confidenceMessage}</p>
                  ) : null}
                  <p className="mb-2 text-xs text-stone-400">
                    {item.document_name} · p.{item.page_number}
                    {confidencePercent !== null ? ` · confidence ${confidencePercent}%` : ''}
                  </p>
                  {warningLabel && item.status === 'Pending' ? (
                    <p className="mb-2 text-xs text-stone-500">
                      Warning: {warningLabel}
                    </p>
                  ) : null}
                  {/* Middle: Editable input (for pending) or read-only (for confirmed/rejected) */}
                  {item.status === 'Pending' ? (
                    <input
                      type="text"
                      value={editValues.get(item.id) ?? (item.edited_value || item.proposed_value)}
                      onChange={(e) => {
                        handleEditChange(item, e.target.value);
                      }}
                      onFocus={() => {
                        if (!editValues.has(item.id)) {
                          setEditValues(prev => {
                            const next = new Map(prev);
                            next.set(item.id, item.edited_value || item.proposed_value);
                            return next;
                          });
                        }
                      }}
                      disabled={savingEdit.has(item.id)}
                      className="w-full rounded border border-[rgba(82,90,99,0.42)] bg-[rgba(14,18,22,0.72)] px-3 py-2 text-sm text-stone-100 disabled:opacity-50"
                      placeholder="Enter value..."
                    />
                  ) : (
                    <div className="font-medium text-stone-100">
                      {item.final_value || item.proposed_value}
                    </div>
                  )}
                  
                  {/* Evidence snippet preview (prefer evidence_json.snippet, fallback to snippet) */}
                  {(item.evidence_json?.snippet || item.snippet) && (
                    <div className="mt-2 space-y-1">
                      <p className="line-clamp-2 text-xs italic text-stone-500">
                        "{item.evidence_json?.snippet || item.snippet}"
                      </p>
                      {item.evidence_json && (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setViewingEvidenceId(item.id);
                          }}
                          className="text-xs text-[rgb(194,200,185)] underline transition-colors hover:text-stone-100"
                        >
                          View evidence
                        </button>
                      )}
                    </div>
                  )}
                </div>

                {/* Right: Actions */}
                <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                  {item.status === 'Pending' && (
                    <>
                      <Button
                        size="sm"
                        variant="default"
                        onClick={(e) => handleConfirm(item, e)}
                        disabled={confirming.has(item.id) || savingEdit.has(item.id)}
                        className={confidenceState !== 'GOOD' ? 'border-[rgba(184,151,95,0.72)] bg-[rgba(184,151,95,0.22)] text-[rgb(219,194,137)] shadow-none hover:bg-[rgba(184,151,95,0.28)]' : ''}
                      >
                        {confirming.has(item.id) ? 'Confirming...' : confidenceState !== 'GOOD' ? 'Force Confirm' : 'Confirm -> Write to dossier'}
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={(e) => {
                          e.stopPropagation();
                          setOverridingId(item.id);
                          setOverrideValue(item.edited_value || item.proposed_value);
                          setOverrideNote(item.override_note || '');
                        }}
                        disabled={confirming.has(item.id) || savingEdit.has(item.id)}
                      >
                        Override
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={(e) => {
                          e.stopPropagation();
                          setRejectingId(item.id);
                          setRejectReason('');
                        }}
                        disabled={rejecting.has(item.id) || savingEdit.has(item.id)}
                      >
                        Reject
                      </Button>
                    </>
                  )}
                  {onViewDocument && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={(e) => {
                        e.stopPropagation();
                        onViewDocument(item.document_id, item.page_number);
                      }}
                    >
                      View
                    </Button>
                  )}
                </div>
              </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Force Confirm Modal */}
      {forceConfirmingId && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 border border-amber-500/30 rounded-lg p-6 max-w-md w-full">
            <h3 className="text-lg font-semibold text-amber-400 mb-2">Force Confirm (Manual Verification)</h3>
            <p className="text-sm text-slate-400 mb-4">
              This extraction has low OCR quality. Manual verification is required.
            </p>
            {data?.items.find(i => i.id === forceConfirmingId)?.warning_reason && (
              <div className="mb-4 p-3 bg-amber-500/10 border border-amber-500/20 rounded text-sm text-amber-300">
                {getWarningReasonLabel(data.items.find(i => i.id === forceConfirmingId)?.warning_reason)}
              </div>
            )}
            <div className="mb-4">
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Verification reason (required):
              </label>
              <textarea
                value={forceConfirmReason}
                onChange={(e) => setForceConfirmReason(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-slate-100"
                rows={3}
                placeholder="e.g., Manually verified against source document."
              />
            </div>
            <div className="flex gap-2 justify-end">
              <Button
                variant="outline"
                onClick={() => {
                  setForceConfirmingId(null);
                  setForceConfirmReason('');
                }}
              >
                Cancel
              </Button>
              <Button
                variant="default"
                className="bg-amber-600 hover:bg-amber-700"
                onClick={(e) => {
                  const item = data?.items.find(i => i.id === forceConfirmingId);
                  if (item && forceConfirmReason.trim()) {
                    handleConfirm(item, e, true);
                  }
                }}
                disabled={!forceConfirmReason.trim() || Boolean(forceConfirmingId && confirming.has(forceConfirmingId))}
              >
                {forceConfirmingId && confirming.has(forceConfirmingId) ? 'Confirming...' : 'Force Confirm'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Override Modal */}
      {overridingId && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 border border-slate-700 rounded-lg p-6 max-w-md w-full">
            <h3 className="text-lg font-semibold text-slate-100 mb-4">Manual Override</h3>
            <div className="mb-4">
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Override Value (required):
              </label>
              <input
                type="text"
                value={overrideValue}
                onChange={(e) => setOverrideValue(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-slate-100"
                placeholder="Enter corrected value..."
              />
            </div>
            <div className="mb-4">
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Override Note (optional):
              </label>
              <textarea
                value={overrideNote}
                onChange={(e) => setOverrideNote(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-slate-100"
                rows={3}
                placeholder="e.g., OCR misread the text; manually verified against source document."
              />
            </div>
            <div className="flex gap-2 justify-end">
              <Button
                variant="outline"
                onClick={() => {
                  setOverridingId(null);
                  setOverrideValue('');
                  setOverrideNote('');
                }}
              >
                Cancel
              </Button>
              <Button
                variant="default"
                onClick={(e) => {
                  const item = data?.items.find(i => i.id === overridingId);
                  if (item) {
                    handleOverride(item, e);
                  }
                }}
                disabled={!overrideValue.trim()}
              >
                Save Override
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Evidence View Modal */}
      {viewingEvidenceId && (() => {
        const item = data?.items.find(i => i.id === viewingEvidenceId);
        if (!item || !item.evidence_json) return null;
        const evidence = item.evidence_json;
        const evidenceFieldPresentation = getFieldPresentation(item.field_key);
        return (
          <Drawer
            open={true}
            onClose={() => setViewingEvidenceId(null)}
            title="Extraction Evidence"
            width="xl"
          >
            <div className="p-6 space-y-4">
              <div className="space-y-2">
                <div>
                  <span className="text-sm font-medium text-slate-400">Field:</span>
                  <p className="text-slate-100">{evidenceFieldPresentation.label}</p>
                  <p className="text-xs text-slate-500">{evidenceFieldPresentation.subtitle}</p>
                </div>
                <div>
                  <span className="text-sm font-medium text-slate-400">Proposed Value:</span>
                  <p className="text-slate-100 font-medium">{item.proposed_value}</p>
                </div>
                <div>
                  <span className="text-sm font-medium text-slate-400">Source:</span>
                  <p className="text-slate-100">
                    {item.extraction_method || 'Unknown'}
                    {evidence.label && ` • ${evidence.label}`}
                  </p>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-sm font-medium text-slate-400">Page Number:</span>
                    <p className="text-slate-100">{item.page_number}</p>
                  </div>
                  {item.document_id && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        if (onViewDocument) {
                          onViewDocument(item.document_id, item.page_number);
                          return;
                        }
                        router.push(
                          getCaseDocumentFocusPath(caseId, item.document_id, item.page_number, item.id)
                        );
                      }}
                      className="ml-4"
                    >
                      View in document
                    </Button>
                  )}
                </div>
              </div>

              {evidence.snippet && (
                <div>
                  <span className="text-sm font-medium text-slate-400">Snippet:</span>
                  <p className="text-slate-100 bg-slate-800 p-3 rounded mt-1 font-mono text-sm whitespace-pre-wrap">
                    {evidence.snippet}
                  </p>
                </div>
              )}

              {evidence.bbox && evidence.bbox.length >= 4 && (
                <div>
                  <span className="text-sm font-medium text-slate-400">Bounding Box:</span>
                  <p className="text-slate-100 bg-slate-800 p-3 rounded mt-1 font-mono text-sm">
                    [{evidence.bbox.map((n: number) => n.toFixed(2)).join(', ')}]
                  </p>
                  <p className="text-xs text-slate-500 mt-1">Format: [x1, y1, x2, y2]</p>
                </div>
              )}

              {evidence.bbox_norm_1000 && evidence.bbox_norm_1000.length >= 4 && (
                <div>
                  <span className="text-sm font-medium text-slate-400">Bounding Box (Normalized to 1000):</span>
                  <p className="text-slate-100 bg-slate-800 p-3 rounded mt-1 font-mono text-sm">
                    [{evidence.bbox_norm_1000.map((n: number) => n.toFixed(2)).join(', ')}]
                  </p>
                </div>
              )}

              {/* P12: Display span offsets when bbox is null (text-only OCR) */}
              {(!evidence.bbox || evidence.bbox.length < 4) && evidence.span_start !== null && evidence.span_start !== undefined && evidence.span_end !== null && evidence.span_end !== undefined && (
                <div>
                  <span className="text-sm font-medium text-slate-400">Evidence: Text Span Offsets</span>
                  <p className="text-slate-100 bg-slate-800 p-3 rounded mt-1 font-mono text-sm">
                    Start: {evidence.span_start}, End: {evidence.span_end}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">Character offsets in page text (for text-only OCR)</p>
                </div>
              )}

              {evidence.token_indices && evidence.token_indices.length > 0 && (
                <div>
                  <span className="text-sm font-medium text-slate-400">Token Indices:</span>
                  <p className="text-slate-100 bg-slate-800 p-3 rounded mt-1 font-mono text-sm">
                    [{evidence.token_indices.join(', ')}]
                  </p>
                  <p className="text-xs text-slate-500 mt-1">
                    Indices of OCR tokens used to construct this value
                  </p>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4 text-sm">
                {evidence.extractor && (
                  <div>
                    <span className="text-slate-400">Extractor:</span>
                    <p className="text-slate-100">{evidence.extractor}</p>
                  </div>
                )}
                {evidence.model && (
                  <div>
                    <span className="text-slate-400">Model:</span>
                    <p className="text-slate-100">{evidence.model}</p>
                  </div>
                )}
                {evidence.ocr_engine && (
                  <div>
                    <span className="text-slate-400">OCR Engine:</span>
                    <p className="text-slate-100">{evidence.ocr_engine}</p>
                  </div>
                )}
                {evidence.extractor_version && (
                  <div>
                    <span className="text-slate-400">Extractor Version:</span>
                    <p className="text-slate-100">{evidence.extractor_version}</p>
                  </div>
                )}
              </div>
            </div>
          </Drawer>
        );
      })()}

      {/* Reject Modal */}
      {rejectingId && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 border border-slate-700 rounded-lg p-6 max-w-md w-full">
            <h3 className="text-lg font-semibold text-slate-100 mb-4">Reject Extraction</h3>
            <div className="mb-4">
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Reason (required):
              </label>
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-slate-100"
                rows={3}
                placeholder="e.g., Not a party name; it is narrative text."
              />
            </div>
            <div className="flex gap-2 justify-end">
              <Button
                variant="outline"
                onClick={() => {
                  setRejectingId(null);
                  setRejectReason('');
                }}
              >
                Cancel
              </Button>
              <Button
                variant="default"
                onClick={(e) => handleReject(e)}
                disabled={!rejectReason.trim() || Boolean(rejectingId && rejecting.has(rejectingId))}
              >
                {rejectingId && rejecting.has(rejectingId) ? 'Rejecting...' : 'Reject'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}














