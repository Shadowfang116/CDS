'use client';

import { Fragment, useCallback, useEffect, useMemo, useState } from 'react';
import {
  getCaseAuditTimeline,
  getCaseExceptions,
  resolveException,
  waiveException,
} from '@/lib/api';
import {
  getRuleEvidenceDefinition,
  hasEvidenceRequirement,
  isEvidenceSatisfied,
} from '@/config/rules_evidence';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/toast';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { EmptyState } from '@/components/ui/empty-state';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Textarea } from '@/components/ui/textarea';

type ExceptionEvidenceRef = {
  id: string;
  document_id?: string | null;
  page_number?: number | null;
  note?: string | null;
};

type CaseException = {
  id: string;
  rule_id: string;
  module: string;
  severity: string;
  title: string;
  description?: string | null;
  cp_text?: string | null;
  resolution_conditions?: string | null;
  status: string;
  waiver_reason?: string | null;
  resolved_at?: string | null;
  waived_at?: string | null;
  created_at: string;
  evidence_refs: ExceptionEvidenceRef[];
};

type ExceptionsResponse = {
  case_id: string;
  total: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  open_count: number;
  resolved_count: number;
  waived_count: number;
  exceptions: CaseException[];
};

type ExceptionsPanelProps = {
  caseId: string;
  documents?: any[];
  onNavigateToDocument: (documentId: string, page?: number) => void;
  onExceptionsChange?: (data: ExceptionsResponse) => void;
  onEvaluate?: () => void | Promise<void>;
  evaluating?: boolean;
};

const severityOrder: Record<string, number> = {
  Critical: 0,
  High: 1,
  Medium: 2,
  Low: 3,
};

function getSeveritySortValue(severity?: string | null): number {
  return severityOrder[severity ?? ''] ?? 99;
}

function getSeverityClass(severity?: string | null): string {
  switch (severity) {
    case 'Critical':
      return 'border-[rgba(151,70,67,0.55)] bg-[rgba(151,70,67,0.16)] text-[rgb(240,205,202)]';
    case 'High':
      return 'border-[rgba(189,90,86,0.42)] bg-[rgba(189,90,86,0.12)] text-[rgb(240,205,202)]';
    case 'Medium':
      return 'border-[rgba(184,151,95,0.36)] bg-[rgba(184,151,95,0.12)] text-[rgb(234,215,170)]';
    case 'Low':
      return 'border-[rgba(71,128,159,0.36)] bg-[rgba(71,128,159,0.12)] text-[rgb(186,213,228)]';
    default:
      return 'border-[rgba(82,90,99,0.4)] bg-[rgba(34,39,45,0.82)] text-stone-300';
  }
}

function getStatusClass(status?: string | null): string {
  switch (status) {
    case 'Resolved':
      return 'border-[rgba(88,140,102,0.35)] bg-[rgba(88,140,102,0.12)] text-[rgb(187,205,189)]';
    case 'Waived':
      return 'border-[rgba(184,151,95,0.35)] bg-[rgba(184,151,95,0.12)] text-[rgb(234,215,170)]';
    case 'Open':
    default:
      return 'border-[rgba(82,90,99,0.4)] bg-[rgba(34,39,45,0.82)] text-stone-300';
  }
}

function getEvidenceStatusClass(satisfied: boolean): string {
  return satisfied
    ? 'border-[rgba(88,140,102,0.35)] bg-[rgba(88,140,102,0.12)] text-[rgb(187,205,189)]'
    : 'border-[rgba(189,90,86,0.42)] bg-[rgba(189,90,86,0.12)] text-[rgb(240,205,202)]';
}

function formatDateTime(value?: string | null): string {
  if (!value) {
    return '—';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return '—';
  }

  return date.toLocaleString();
}

function getUpdatedAt(exceptionItem: CaseException): string {
  return exceptionItem.resolved_at ?? exceptionItem.waived_at ?? exceptionItem.created_at;
}

function truncate(value?: string | null, maxLength: number = 140): string {
  const text = value?.trim() ?? '';
  if (!text) {
    return '—';
  }
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, maxLength).trimEnd()}...`;
}

function ExceptionRowsSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 6 }).map((_, index) => (
        <div key={index} className="grid grid-cols-[0.8fr_2fr_1fr_0.9fr_0.9fr_1.2fr_1.3fr] gap-3 rounded-lg border border-[rgba(82,90,99,0.32)] bg-[rgba(24,28,32,0.82)] px-4 py-3">
          <Skeleton className="h-5 w-16" />
          <Skeleton className="h-5 w-full" />
          <Skeleton className="h-5 w-20" />
          <Skeleton className="h-5 w-10" />
          <Skeleton className="h-5 w-12" />
          <Skeleton className="h-5 w-28" />
          <Skeleton className="h-8 w-28 justify-self-end" />
        </div>
      ))}
    </div>
  );
}

export function ExceptionsPanel({
  caseId,
  documents = [],
  onNavigateToDocument,
  onExceptionsChange,
  onEvaluate,
  evaluating = false,
}: ExceptionsPanelProps) {
  const { toast } = useToast();
  const [data, setData] = useState<ExceptionsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [panelError, setPanelError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [resolveTarget, setResolveTarget] = useState<CaseException | null>(null);
  const [waiveTarget, setWaiveTarget] = useState<CaseException | null>(null);
  const [resolveNote, setResolveNote] = useState('');
  const [waiveReason, setWaiveReason] = useState('');
  const [submittingId, setSubmittingId] = useState<string | null>(null);
  const [closureNotes, setClosureNotes] = useState<Record<string, string>>({});

  const documentLookup = useMemo(() => {
    const map = new Map<string, any>();
    documents.forEach((doc) => {
      if (typeof doc?.id === 'string' && doc.id) {
        map.set(doc.id, doc);
      }
    });
    return map;
  }, [documents]);

  const getDocumentLabel = useCallback((documentId?: string | null) => {
    if (!documentId) {
      return 'Annexure reference pending';
    }

    const document = documentLookup.get(documentId);
    return document?.original_filename || document?.filename || `${documentId.slice(0, 8)}…`;
  }, [documentLookup]);

  const loadExceptions = useCallback(async () => {
    setLoading(true);
    setPanelError(null);

    try {
      const [exceptionsResponse, auditResponse] = await Promise.all([
        getCaseExceptions(caseId),
        getCaseAuditTimeline(caseId).catch(() => ({ case_id: caseId, events: [] })),
      ]);

      setData(exceptionsResponse);
      onExceptionsChange?.(exceptionsResponse);

      const nextClosureNotes: Record<string, string> = {};
      for (const event of auditResponse.events ?? []) {
        const entityId = event.entity_id ?? event.details?.exception_id;
        if (!entityId || nextClosureNotes[entityId]) {
          continue;
        }

        if (event.action === 'exception.resolve' && typeof event.details?.reason === 'string' && event.details.reason.trim()) {
          nextClosureNotes[entityId] = event.details.reason.trim();
        }
      }
      setClosureNotes(nextClosureNotes);
    } catch (error: any) {
      setPanelError(error.message || 'Failed to load exceptions');
    } finally {
      setLoading(false);
    }
  }, [caseId, onExceptionsChange]);

  useEffect(() => {
    void loadExceptions();
  }, [loadExceptions]);

  const sortedExceptions = useMemo(() => {
    const items = Array.isArray(data?.exceptions) ? [...data.exceptions] : [];
    items.sort((left, right) => {
      const severityDelta = getSeveritySortValue(left.severity) - getSeveritySortValue(right.severity);
      if (severityDelta !== 0) {
        return severityDelta;
      }

      if (left.status !== right.status) {
        if (left.status === 'Open') return -1;
        if (right.status === 'Open') return 1;
      }

      return new Date(getUpdatedAt(right)).getTime() - new Date(getUpdatedAt(left)).getTime();
    });
    return items;
  }, [data]);

  const handleResolveSubmit = useCallback(async () => {
    if (!resolveTarget || !resolveNote.trim()) {
      return;
    }

    setSubmittingId(resolveTarget.id);
    setPanelError(null);

    try {
      await resolveException(resolveTarget.id, resolveNote.trim());
      setResolveTarget(null);
      setResolveNote('');
      toast({
        title: 'Exception resolved.',
        description: 'The closure note has been recorded.',
        variant: 'success',
      });
      await loadExceptions();
    } catch (error: any) {
      setPanelError(error.message || 'Failed to resolve exception');
      toast({
        title: 'Unable to resolve exception.',
        description: error.message || 'Please retry.',
        variant: 'error',
      });
    } finally {
      setSubmittingId(null);
    }
  }, [loadExceptions, resolveNote, resolveTarget, toast]);

  const handleWaiveSubmit = useCallback(async () => {
    if (!waiveTarget || !waiveReason.trim()) {
      return;
    }

    setSubmittingId(waiveTarget.id);
    setPanelError(null);

    try {
      await waiveException(waiveTarget.id, waiveReason.trim());
      setWaiveTarget(null);
      setWaiveReason('');
      toast({
        title: 'Waiver recorded.',
        description: 'The waiver rationale has been saved.',
        variant: 'success',
      });
      await loadExceptions();
    } catch (error: any) {
      setPanelError(error.message || 'Failed to waive exception');
      toast({
        title: 'Unable to record waiver.',
        description: error.message || 'Please retry.',
        variant: 'error',
      });
    } finally {
      setSubmittingId(null);
    }
  }, [loadExceptions, waiveReason, waiveTarget, toast]);

  const resolveLoading = resolveTarget ? submittingId === resolveTarget.id : false;
  const waiveLoading = waiveTarget ? submittingId === waiveTarget.id : false;
  const resolveTargetEvidence = resolveTarget
    ? getRuleEvidenceDefinition(resolveTarget.rule_id)
    : null;
  const resolveMissingEvidence = resolveTarget
    ? hasEvidenceRequirement(resolveTarget.rule_id) && !isEvidenceSatisfied(resolveTarget.evidence_refs)
    : false;
  const resolveNoteMinLength = resolveMissingEvidence ? 40 : 1;
  const canResolve = resolveNote.trim().length >= resolveNoteMinLength;

  return (
    <>
      <Card>
        <CardHeader className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <CardTitle>Exceptions</CardTitle>
            <p className="mt-1 text-sm text-stone-400">
              Review severity-ranked findings, linked annexures, and closure actions.
            </p>
          </div>
          {onEvaluate ? (
            <Button onClick={() => void onEvaluate()} disabled={evaluating} loading={evaluating}>
              {evaluating ? 'Evaluating...' : 'Evaluate Rules'}
            </Button>
          ) : null}
        </CardHeader>
        <CardContent className="space-y-4">
          {panelError ? (
            <div className="rounded-lg border border-[rgba(189,90,86,0.36)] bg-[rgba(189,90,86,0.12)] px-4 py-3 text-sm text-[rgb(219,156,153)]">
              {panelError}
            </div>
          ) : null}

          {loading ? (
            <ExceptionRowsSkeleton />
          ) : !data || sortedExceptions.length === 0 ? (
            <EmptyState
              title="No exceptions recorded for this case."
              description="Run rule evaluation to refresh the legal exception register for this file."
              actionLabel={onEvaluate ? 'Evaluate Rules' : undefined}
              onAction={onEvaluate ? () => void onEvaluate() : undefined}
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Severity</TableHead>
                  <TableHead>Title</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Evidence Count</TableHead>
                  <TableHead>CP Linked</TableHead>
                  <TableHead>Updated</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedExceptions.map((exceptionItem) => {
                  const isExpanded = expandedId === exceptionItem.id;
                  const closureNote = closureNotes[exceptionItem.id];
                  const evidenceDefinition = getRuleEvidenceDefinition(exceptionItem.rule_id);
                  const evidenceSatisfied = isEvidenceSatisfied(exceptionItem.evidence_refs);

                  return (
                    <Fragment key={exceptionItem.id}>
                      <TableRow key={exceptionItem.id} className="cursor-pointer" onClick={() => setExpandedId(isExpanded ? null : exceptionItem.id)}>
                        <TableCell>
                          <span className={`inline-flex rounded-md border px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.08em] ${getSeverityClass(exceptionItem.severity)}`}>
                            {exceptionItem.severity}
                          </span>
                        </TableCell>
                        <TableCell>
                          <div className="min-w-0">
                            <div className="flex flex-wrap items-center gap-2">
                              <div className="font-medium text-stone-100">{exceptionItem.title}</div>
                              <span className={`inline-flex rounded-md border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-[0.08em] ${getEvidenceStatusClass(evidenceSatisfied)}`}>
                                {evidenceSatisfied ? 'Satisfied' : 'Missing Evidence'}
                              </span>
                            </div>
                            <div className="mt-1 text-xs text-stone-500">
                              {exceptionItem.module} • {exceptionItem.rule_id}
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <span className={`inline-flex rounded-md border px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.08em] ${getStatusClass(exceptionItem.status)}`}>
                            {exceptionItem.status}
                          </span>
                        </TableCell>
                        <TableCell>{exceptionItem.evidence_refs?.length ?? 0}</TableCell>
                        <TableCell>{exceptionItem.cp_text ? 'Yes' : 'No'}</TableCell>
                        <TableCell>{formatDateTime(getUpdatedAt(exceptionItem))}</TableCell>
                        <TableCell className="text-right">
                          {exceptionItem.status === 'Open' ? (
                            <div className="flex justify-end gap-2" onClick={(event) => event.stopPropagation()}>
                              <Button
                                size="sm"
                                variant="secondary"
                                onClick={() => {
                                  setResolveTarget(exceptionItem);
                                  setResolveNote('');
                                }}
                              >
                                Resolve
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => {
                                  setWaiveTarget(exceptionItem);
                                  setWaiveReason('');
                                }}
                              >
                                Waive
                              </Button>
                            </div>
                          ) : (
                            <span className="text-xs text-stone-500">Closed</span>
                          )}
                        </TableCell>
                      </TableRow>
                      {isExpanded ? (
                        <TableRow key={`${exceptionItem.id}-expanded`} className="hover:bg-transparent">
                          <TableCell colSpan={7} className="bg-[rgba(22,26,30,0.9)]">
                            <div className="grid gap-4 lg:grid-cols-2">
                              <div className="space-y-4">
                                <div>
                                  <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">Description</div>
                                  <p className="mt-2 text-sm text-stone-200">{truncate(exceptionItem.description, 500)}</p>
                                </div>
                                <div>
                                  <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">Required Evidence</div>
                                  <ul className="mt-2 space-y-1 text-sm text-stone-200">
                                    {evidenceDefinition.required_evidence.map((item) => (
                                      <li key={item}>• {item}</li>
                                    ))}
                                  </ul>
                                </div>
                                <div>
                                  <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">Acceptable Substitutes</div>
                                  {evidenceDefinition.acceptable_substitutes.length > 0 ? (
                                    <ul className="mt-2 space-y-1 text-sm text-stone-200">
                                      {evidenceDefinition.acceptable_substitutes.map((item) => (
                                        <li key={item}>• {item}</li>
                                      ))}
                                    </ul>
                                  ) : (
                                    <p className="mt-2 text-sm text-stone-400">No substitute evidence defined.</p>
                                  )}
                                </div>
                                {evidenceDefinition.closure_guidance ? (
                                  <div>
                                    <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">Closure Guidance</div>
                                    <p className="mt-2 text-sm text-stone-200">{evidenceDefinition.closure_guidance}</p>
                                  </div>
                                ) : null}
                                {evidenceDefinition.cp_recommended_text ? (
                                  <div>
                                    <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">Recommended CP Text</div>
                                    <p className="mt-2 text-sm text-stone-200">{evidenceDefinition.cp_recommended_text}</p>
                                  </div>
                                ) : null}
                                {evidenceDefinition.reviewer_confirmation_required ? (
                                  <div className="rounded-md border border-[rgba(184,151,95,0.28)] bg-[rgba(184,151,95,0.08)] px-3 py-2 text-xs text-[rgb(234,215,170)]">
                                    Reviewer confirmation required. This rule is using the generic evidence fallback.
                                  </div>
                                ) : null}
                                <div>
                                  <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">Condition Precedent</div>
                                  <p className="mt-2 text-sm text-stone-200">{truncate(exceptionItem.cp_text, 500)}</p>
                                </div>
                                <div>
                                  <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">Closure Note</div>
                                  <p className="mt-2 text-sm text-stone-200">{closureNote || 'No closure note recorded.'}</p>
                                </div>
                                <div>
                                  <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">Waiver Reason</div>
                                  <p className="mt-2 text-sm text-stone-200">{exceptionItem.waiver_reason?.trim() || 'No waiver reason recorded.'}</p>
                                </div>
                              </div>

                              <div>
                                <div className="flex items-center justify-between gap-3">
                                  <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">Linked Evidence</div>
                                  <span className={`inline-flex rounded-md border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-[0.08em] ${getEvidenceStatusClass(evidenceSatisfied)}`}>
                                    {evidenceSatisfied ? 'Satisfied' : 'Missing Evidence'}
                                  </span>
                                </div>
                                {exceptionItem.evidence_refs?.length ? (
                                  <div className="mt-2 space-y-2">
                                    {exceptionItem.evidence_refs.map((ref) => (
                                      <div
                                        key={ref.id}
                                        className="flex items-start justify-between gap-3 rounded-lg border border-[rgba(82,90,99,0.36)] bg-[rgba(29,34,39,0.78)] px-3 py-2.5"
                                      >
                                        <div className="min-w-0">
                                          <div className="text-sm text-stone-100">{getDocumentLabel(ref.document_id)}</div>
                                          <div className="mt-1 text-xs text-stone-400">
                                            {ref.page_number ? `Page ${ref.page_number}` : 'Page reference pending'}
                                            {ref.note ? ` • ${ref.note}` : ''}
                                          </div>
                                        </div>
                                        {ref.document_id ? (
                                          <Button
                                            size="sm"
                                            variant="ghost"
                                            onClick={() => onNavigateToDocument(ref.document_id!, ref.page_number ?? undefined)}
                                          >
                                            View
                                          </Button>
                                        ) : null}
                                      </div>
                                    ))}
                                  </div>
                                ) : (
                                  <p className="mt-2 text-sm text-stone-400">Annexure reference pending.</p>
                                )}
                              </div>
                            </div>
                          </TableCell>
                        </TableRow>
                      ) : null}
                    </Fragment>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialog open={resolveTarget !== null} onOpenChange={(open) => {
        if (!open) {
          setResolveTarget(null);
          setResolveNote('');
        }
      }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Resolve Exception</DialogTitle>
            <DialogDescription>
              Record the closure note that supports resolution of this exception.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="rounded-md border border-[rgba(82,90,99,0.4)] bg-[rgba(24,28,32,0.88)] px-3 py-2 text-sm text-stone-200">
              {resolveTarget?.title}
            </div>
            {resolveMissingEvidence ? (
              <div className="rounded-md border border-[rgba(189,90,86,0.36)] bg-[rgba(189,90,86,0.12)] px-3 py-2 text-sm text-[rgb(240,205,202)]">
                This exception requires evidence before resolution.
                <div className="mt-1 text-xs text-stone-300">
                  Override is allowed only with a strong closure note explaining the documentary basis for closure.
                </div>
                {resolveTargetEvidence ? (
                  <div className="mt-2 text-xs text-stone-300">
                    Required: {resolveTargetEvidence.required_evidence.join(', ')}
                    {resolveTargetEvidence.acceptable_substitutes.length > 0
                      ? ` | Substitutes: ${resolveTargetEvidence.acceptable_substitutes.join(', ')}`
                      : ''}
                  </div>
                ) : null}
                {resolveTargetEvidence?.closure_guidance ? (
                  <div className="mt-2 text-xs text-stone-300">
                    Guidance: {resolveTargetEvidence.closure_guidance}
                  </div>
                ) : null}
              </div>
            ) : null}
            <Textarea
              value={resolveNote}
              onChange={(event) => setResolveNote(event.target.value)}
              placeholder={
                resolveMissingEvidence
                  ? 'Enter a strong closure note describing why resolution is appropriate without linked evidence.'
                  : 'Enter the reviewer closure note.'
              }
              className="min-h-[120px] border-[rgba(82,90,99,0.55)] bg-[rgba(22,26,30,0.92)] text-stone-100 placeholder:text-stone-500 focus-visible:ring-[rgba(126,133,111,0.85)] focus-visible:ring-offset-0"
            />
            {resolveMissingEvidence ? (
              <div className="text-xs text-stone-400">
                Minimum override note length: {resolveNoteMinLength} characters.
              </div>
            ) : null}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setResolveTarget(null);
              setResolveNote('');
            }}>
              Cancel
            </Button>
            <Button onClick={() => void handleResolveSubmit()} disabled={!canResolve} loading={resolveLoading}>
              {resolveLoading ? 'Resolving...' : 'Resolve'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={waiveTarget !== null} onOpenChange={(open) => {
        if (!open) {
          setWaiveTarget(null);
          setWaiveReason('');
        }
      }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Waive Exception</DialogTitle>
            <DialogDescription>
              Record the approver rationale for waiving this exception.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="rounded-md border border-[rgba(82,90,99,0.4)] bg-[rgba(24,28,32,0.88)] px-3 py-2 text-sm text-stone-200">
              {waiveTarget?.title}
            </div>
            <Textarea
              value={waiveReason}
              onChange={(event) => setWaiveReason(event.target.value)}
              placeholder="Enter the waiver reason."
              className="min-h-[120px] border-[rgba(82,90,99,0.55)] bg-[rgba(22,26,30,0.92)] text-stone-100 placeholder:text-stone-500 focus-visible:ring-[rgba(126,133,111,0.85)] focus-visible:ring-offset-0"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setWaiveTarget(null);
              setWaiveReason('');
            }}>
              Cancel
            </Button>
            <Button onClick={() => void handleWaiveSubmit()} disabled={!waiveReason.trim()} loading={waiveLoading}>
              {waiveLoading ? 'Waiving...' : 'Waive'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
