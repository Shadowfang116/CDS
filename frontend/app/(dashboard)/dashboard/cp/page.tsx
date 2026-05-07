'use client';

import { Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { ChevronRight, X } from 'lucide-react';
import { SetPageChrome } from '@/components/layout/set-page-chrome';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, MetricCard } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { EmptyState } from '@/components/ui/empty-state';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Textarea } from '@/components/ui/textarea';
import { ApiError, createApproval, listCPs, listCases } from '@/lib/api';
import { getCaseTabPath } from '@/lib/routes';
import { cn } from '@/lib/utils';
import { getRuleEvidenceDefinition, type RuleEvidenceDefinition } from '@/config/rules_evidence';
import type { CaseListItem } from '@/types/cases';

type AlertTone = 'error' | 'success' | 'warning';
type CPFilter = 'all' | 'open' | 'overdue' | 'fulfilled' | 'waived';
type CPSeverity = 'High' | 'Medium' | 'Low';
type CPStatus = 'Open' | 'Satisfied' | 'Waived';
type CPCategory =
  | 'Title'
  | 'Authority'
  | 'Corporate'
  | 'Security'
  | 'Approvals'
  | 'Documentation'
  | 'General';

interface EvidenceRef {
  id: string;
  document_id: string | null;
  page_number: number | null;
  note: string | null;
}

interface CPItemApi {
  id: string;
  rule_id: string;
  severity: string;
  text: string;
  evidence_required?: string | null;
  status: string;
  created_at: string;
  evidence_refs?: EvidenceRef[];
}

interface CPListApiResponse {
  case_id: string;
  total: number;
  open_count: number;
  satisfied_count: number;
  waived_count: number;
  cps: CPItemApi[];
}

interface CaseSummary {
  id: string;
  title: string;
  status: string;
}

interface CommandCP {
  id: string;
  caseId: string;
  caseName: string;
  caseStatus: string;
  ruleId: string;
  severity: CPSeverity;
  title: string;
  status: CPStatus;
  createdAt: string;
  dueDate: string | null;
  category: CPCategory;
  evidenceRefs: EvidenceRef[];
  evidenceCount: number;
  overdue: boolean;
  evidenceDefinition: RuleEvidenceDefinition;
}

type AlertState = {
  tone: AlertTone;
  text: string;
};

const FILTER_OPTIONS: ReadonlyArray<{ value: CPFilter; label: string }> = [
  { value: 'all', label: 'All' },
  { value: 'open', label: 'Open' },
  { value: 'overdue', label: 'Overdue' },
  { value: 'fulfilled', label: 'Fulfilled' },
  { value: 'waived', label: 'Waived' },
];

const INACTIVE_CASE_STATUSES = new Set(['Approved', 'Rejected', 'Closed']);

// TODO: replace with API-backed CP category taxonomy and due dates once the backend exposes them.
const CP_CATEGORY_KEYWORDS: ReadonlyArray<{ match: string; category: CPCategory }> = [
  { match: 'TITLE', category: 'Title' },
  { match: 'SALE_DEED', category: 'Title' },
  { match: 'REG_', category: 'Title' },
  { match: 'AUTHORITY', category: 'Authority' },
  { match: 'RUDA', category: 'Authority' },
  { match: 'CANT', category: 'Authority' },
  { match: 'SOC', category: 'Corporate' },
  { match: 'CAPACITY', category: 'Corporate' },
  { match: 'SECURITY', category: 'Security' },
  { match: 'MORTGAGE', category: 'Security' },
  { match: 'APPROVAL', category: 'Approvals' },
  { match: 'LAYOUT', category: 'Approvals' },
  { match: 'ANNEXURE', category: 'Documentation' },
  { match: 'DOC', category: 'Documentation' },
];

// TODO: replace with API-backed CP deadlines once due dates are returned by the rules service.
const CP_DUE_DAYS_BY_SEVERITY: Record<CPSeverity, number> = {
  High: 7,
  Medium: 14,
  Low: 21,
};

function normalizeCaseSummaries(raw: unknown): CaseSummary[] {
  const value = Array.isArray(raw)
    ? raw
    : Array.isArray((raw as { items?: unknown[] } | null)?.items)
      ? ((raw as { items: unknown[] }).items ?? [])
      : [];

  return value
    .map((item) => item as CaseListItem)
    .filter((item) => item?.id !== undefined && item?.id !== null)
    .map((item) => ({
      id: String(item.id),
      title: item.title?.trim() || `Case ${String(item.id).slice(0, 8)}`,
      status: item.status?.trim() || 'Processing',
    }));
}

function normalizeSeverity(value: string): CPSeverity {
  if (value === 'High' || value === 'Medium' || value === 'Low') {
    return value;
  }
  return 'Low';
}

function normalizeStatus(value: string): CPStatus {
  if (value === 'Satisfied' || value === 'Met') {
    return 'Satisfied';
  }
  if (value === 'Waived') {
    return 'Waived';
  }
  return 'Open';
}

function isActiveCase(caseItem: CaseSummary): boolean {
  return !INACTIVE_CASE_STATUSES.has(caseItem.status);
}

function deriveCategory(ruleId: string): CPCategory {
  const normalizedRuleId = ruleId.toUpperCase();
  const matched = CP_CATEGORY_KEYWORDS.find((entry) => normalizedRuleId.includes(entry.match));
  return matched?.category ?? 'General';
}

function deriveDueDate(createdAt: string, severity: CPSeverity): string | null {
  const timestamp = new Date(createdAt);
  if (Number.isNaN(timestamp.getTime())) {
    return null;
  }

  const dueAt = new Date(timestamp);
  dueAt.setDate(dueAt.getDate() + CP_DUE_DAYS_BY_SEVERITY[severity]);
  return dueAt.toISOString();
}

function formatDate(value?: string | null): string {
  if (!value) {
    return 'Not scheduled';
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return 'Not scheduled';
  }

  return parsed.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function formatDateTime(value?: string | null): string {
  if (!value) {
    return '—';
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return '—';
  }

  return parsed.toLocaleString();
}

function formatEvidenceLabel(ref: EvidenceRef): string {
  const documentLabel = ref.document_id ? `Document ${ref.document_id.slice(0, 8)}` : 'Manual note';
  if (ref.page_number) {
    return `${documentLabel} · Page ${ref.page_number}`;
  }
  return documentLabel;
}

function getStatusLabel(status: CPStatus): string {
  if (status === 'Satisfied') {
    return 'Fulfilled';
  }
  if (status === 'Open') {
    return 'Pending';
  }
  return 'Waived';
}

function getStatusVariant(status: CPStatus, overdue: boolean): 'warning' | 'success' | 'neutral' | 'error' {
  if (status === 'Satisfied') {
    return 'success';
  }
  if (status === 'Waived') {
    return 'neutral';
  }
  return overdue ? 'error' : 'warning';
}

function getCategoryVariant(category: CPCategory): 'info' | 'neutral' | 'warning' {
  if (category === 'Approvals' || category === 'Authority') {
    return 'warning';
  }
  if (category === 'Title' || category === 'Security') {
    return 'info';
  }
  return 'neutral';
}

function getSeverityVariant(severity: CPSeverity): 'warning' | 'info' | 'neutral' {
  if (severity === 'High') {
    return 'warning';
  }
  if (severity === 'Medium') {
    return 'info';
  }
  return 'neutral';
}

function sortCPs(left: CommandCP, right: CommandCP): number {
  const statusOrder: Record<CPStatus, number> = {
    Open: 0,
    Satisfied: 1,
    Waived: 2,
  };
  const severityOrder: Record<CPSeverity, number> = {
    High: 0,
    Medium: 1,
    Low: 2,
  };

  if (left.overdue !== right.overdue) {
    return left.overdue ? -1 : 1;
  }

  if (statusOrder[left.status] !== statusOrder[right.status]) {
    return statusOrder[left.status] - statusOrder[right.status];
  }

  if (severityOrder[left.severity] !== severityOrder[right.severity]) {
    return severityOrder[left.severity] - severityOrder[right.severity];
  }

  const leftDue = left.dueDate ? new Date(left.dueDate).getTime() : Number.MAX_SAFE_INTEGER;
  const rightDue = right.dueDate ? new Date(right.dueDate).getTime() : Number.MAX_SAFE_INTEGER;
  if (leftDue !== rightDue) {
    return leftDue - rightDue;
  }

  return left.title.localeCompare(right.title);
}

function matchesFilter(cpItem: CommandCP, filter: CPFilter): boolean {
  if (filter === 'all') {
    return true;
  }
  if (filter === 'open') {
    return cpItem.status === 'Open';
  }
  if (filter === 'overdue') {
    return cpItem.status === 'Open' && cpItem.overdue;
  }
  if (filter === 'fulfilled') {
    return cpItem.status === 'Satisfied';
  }
  return cpItem.status === 'Waived';
}

function normalizeCPs(response: CPListApiResponse, caseItem: CaseSummary): CommandCP[] {
  const now = Date.now();

  return (Array.isArray(response.cps) ? response.cps : []).map((cpItem) => {
    const severity = normalizeSeverity(cpItem.severity);
    const status = normalizeStatus(cpItem.status);
    const dueDate = deriveDueDate(cpItem.created_at, severity);
    const overdue =
      status === 'Open' &&
      dueDate !== null &&
      !Number.isNaN(new Date(dueDate).getTime()) &&
      new Date(dueDate).getTime() < now;

    const ruleId = cpItem.rule_id ?? '';
    return {
      id: cpItem.id,
      caseId: caseItem.id,
      caseName: caseItem.title,
      caseStatus: caseItem.status,
      ruleId,
      severity,
      title: cpItem.text,
      status,
      createdAt: cpItem.created_at,
      dueDate,
      category: deriveCategory(ruleId),
      evidenceRefs: Array.isArray(cpItem.evidence_refs) ? cpItem.evidence_refs : [],
      evidenceCount: Array.isArray(cpItem.evidence_refs) ? cpItem.evidence_refs.length : 0,
      overdue,
      evidenceDefinition: getRuleEvidenceDefinition(ruleId, cpItem.evidence_required ?? null),
    };
  });
}

function CPPageSkeleton() {
  return (
    <div className="space-y-4" data-dashboard-reveal>
      <div className="space-y-2">
        <Skeleton className="h-9 w-64" />
        <Skeleton className="h-5 w-[32rem] max-w-full" />
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <Skeleton key={index} className="h-32 rounded-[1.1rem]" />
        ))}
      </div>
      <Skeleton className="h-[26rem] rounded-[1.1rem]" />
    </div>
  );
}

function InlineNotice(props: { tone: AlertTone; children: string }) {
  const toneClass =
    props.tone === 'success'
      ? 'border-[rgba(111,140,115,0.34)] bg-[rgba(111,140,115,0.14)] text-[rgb(187,205,189)]'
      : props.tone === 'warning'
        ? 'border-[rgba(184,151,95,0.34)] bg-[rgba(184,151,95,0.14)] text-[rgb(219,194,137)]'
        : 'border-[rgba(189,90,86,0.34)] bg-[rgba(189,90,86,0.14)] text-[rgb(219,156,153)]';

  return <div className={cn('rounded-lg border px-4 py-3 text-sm', toneClass)}>{props.children}</div>;
}

interface CpDetailPanelProps {
  cpItem: CommandCP | null;
  open: boolean;
  isGlobalMode: boolean;
  onClose: () => void;
  onFulfill: (caseId: string) => void;
  onEvidence: (caseId: string) => void;
  onWaive: (cpItem: CommandCP) => void;
  className?: string;
}

function CpDetailPanel(props: CpDetailPanelProps) {
  const { cpItem, open, isGlobalMode, onClose, onFulfill, onEvidence, onWaive, className } = props;
  const requiredEvidence = cpItem?.evidenceDefinition.required_evidence ?? [];
  const dueDateLabel = cpItem?.dueDate ? formatDate(cpItem.dueDate) : 'N/A';
  const evidenceRequiredLabel =
    requiredEvidence.length > 0
      ? `${requiredEvidence.length} item${requiredEvidence.length === 1 ? '' : 's'}`
      : 'No';

  return (
    <Card
      aria-hidden={!open}
      className={cn(
        'flex h-full min-h-[36rem] flex-col overflow-hidden border-[rgba(82,90,99,0.42)] bg-[rgba(18,22,26,0.96)] shadow-[0_18px_40px_rgba(0,0,0,0.18)] transition-transform duration-150',
        open ? 'translate-x-0' : 'pointer-events-none translate-x-full',
        className
      )}
    >
      <CardHeader className="border-b border-[rgba(82,90,99,0.34)] pb-4">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-2">
            <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">
              {cpItem ? `CP · ${cpItem.ruleId}` : 'CP Detail'}
            </div>
            <CardTitle className="text-lg leading-6 text-stone-100">
              {cpItem?.title ?? 'Select a Condition Precedent to inspect details.'}
            </CardTitle>
            {cpItem ? (
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={getStatusVariant(cpItem.status, cpItem.overdue)}>{getStatusLabel(cpItem.status)}</Badge>
                <Badge variant={getSeverityVariant(cpItem.severity)}>{cpItem.severity}</Badge>
                <Badge variant={getCategoryVariant(cpItem.category)}>{cpItem.category}</Badge>
              </div>
            ) : (
              <p className="text-sm text-stone-500">Row selection opens the master-detail review panel.</p>
            )}
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={onClose}
            aria-label="Close details"
            className="text-stone-400 hover:text-stone-100"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>

      <CardContent className="flex flex-1 flex-col overflow-hidden p-0">
        {cpItem ? (
          <>
            <div className="flex-1 space-y-4 overflow-y-auto px-5 py-5">
              <div className="space-y-2">
                <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">
                  Description
                </div>
                <p className="text-sm leading-6 text-stone-200">{cpItem.title}</p>
              </div>

              <Separator className="bg-[rgba(82,90,99,0.28)]" />

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-md border border-[rgba(82,90,99,0.32)] bg-[rgba(29,34,39,0.76)] px-3 py-3">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">Due Date</div>
                  <div className="mt-2 text-sm text-stone-100">{dueDateLabel}</div>
                </div>
                <div className="rounded-md border border-[rgba(82,90,99,0.32)] bg-[rgba(29,34,39,0.76)] px-3 py-3">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">
                    Evidence Required
                  </div>
                  <div className="mt-2 text-sm text-stone-100">{evidenceRequiredLabel}</div>
                </div>
                <div className="rounded-md border border-[rgba(82,90,99,0.32)] bg-[rgba(29,34,39,0.76)] px-3 py-3">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">
                    Evidence Linked
                  </div>
                  <div className="mt-2 text-sm text-stone-100">
                    {cpItem.evidenceCount} item{cpItem.evidenceCount === 1 ? '' : 's'}
                  </div>
                </div>
                <div className="rounded-md border border-[rgba(82,90,99,0.32)] bg-[rgba(29,34,39,0.76)] px-3 py-3">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">Created</div>
                  <div className="mt-2 text-sm text-stone-100">{formatDateTime(cpItem.createdAt)}</div>
                </div>
                {isGlobalMode ? (
                  <div className="rounded-md border border-[rgba(82,90,99,0.32)] bg-[rgba(29,34,39,0.76)] px-3 py-3 sm:col-span-2">
                    <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">
                      Related Case
                    </div>
                    <div className="mt-2 text-sm text-stone-100">{cpItem.caseName}</div>
                  </div>
                ) : null}
              </div>

              <div className="space-y-2">
                <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">
                  Required Evidence
                </div>
                <div className="rounded-md border border-[rgba(82,90,99,0.32)] bg-[rgba(29,34,39,0.76)] px-3 py-3 text-sm text-stone-200">
                  {requiredEvidence.length > 0
                    ? requiredEvidence.join(', ')
                    : 'No structured evidence requirement returned.'}
                </div>
              </div>

              <div className="space-y-2">
                <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">
                  Linked Evidence
                </div>
                {cpItem.evidenceRefs.length === 0 ? (
                  <div className="rounded-md border border-dashed border-[rgba(82,90,99,0.32)] px-3 py-3 text-sm text-stone-500">
                    No evidence linked yet.
                  </div>
                ) : (
                  <div className="space-y-2">
                    {cpItem.evidenceRefs.map((ref) => (
                      <div
                        key={ref.id}
                        className="rounded-md border border-[rgba(82,90,99,0.32)] bg-[rgba(29,34,39,0.76)] px-3 py-3"
                      >
                        <div className="text-sm text-stone-100">{formatEvidenceLabel(ref)}</div>
                        <div className="mt-1 text-xs text-stone-500">{ref.note?.trim() || 'No note recorded.'}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">
                  Closure Guidance
                </div>
                <div className="rounded-md border border-[rgba(82,90,99,0.32)] bg-[rgba(29,34,39,0.76)] px-3 py-3 text-sm text-stone-200">
                  {cpItem.evidenceDefinition.closure_guidance || 'No closure guidance available.'}
                </div>
              </div>

              <div className="space-y-2">
                <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">
                  Recommended CP Text
                </div>
                <div className="rounded-md border border-[rgba(82,90,99,0.32)] bg-[rgba(29,34,39,0.76)] px-3 py-3 text-sm text-stone-200">
                  {cpItem.evidenceDefinition.cp_recommended_text || 'No recommended wording returned.'}
                </div>
              </div>

              <div className="space-y-2">
                <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">
                  Supplemental Notes
                </div>
                <div className="rounded-md border border-[rgba(82,90,99,0.32)] bg-[rgba(29,34,39,0.76)] px-3 py-3 text-sm text-stone-200">
                  {cpItem.evidenceDefinition.acceptable_substitutes.length > 0
                    ? `Acceptable substitutes: ${cpItem.evidenceDefinition.acceptable_substitutes.join(', ')}`
                    : 'No substitute evidence rule is configured.'}
                </div>
              </div>
            </div>

            <div className="border-t border-[rgba(82,90,99,0.34)] px-5 py-4">
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={cpItem.status !== 'Open'}
                  onClick={() => onFulfill(cpItem.caseId)}
                >
                  Fulfill
                </Button>
                <Button size="sm" variant="outline" onClick={() => onEvidence(cpItem.caseId)}>
                  Add/View Evidence
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={cpItem.status !== 'Open'}
                  onClick={() => onWaive(cpItem)}
                >
                  Waive
                </Button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex flex-1 items-center justify-center px-5 py-8 text-center text-sm text-stone-500">
            Select a Condition Precedent from the table to review its evidence and take action.
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function CPPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedCaseId = searchParams.get('caseId');

  const [filter, setFilter] = useState<CPFilter>('all');
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [globalRecords, setGlobalRecords] = useState<CommandCP[]>([]);
  const [globalLoading, setGlobalLoading] = useState(true);
  const [selectedCaseRecords, setSelectedCaseRecords] = useState<CommandCP[]>([]);
  const [selectedLoading, setSelectedLoading] = useState(false);
  const [selectedLoaded, setSelectedLoaded] = useState(false);
  const [selectedCpId, setSelectedCpId] = useState<string | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);
  const [alert, setAlert] = useState<AlertState | null>(null);
  const [waiveTarget, setWaiveTarget] = useState<CommandCP | null>(null);
  const [waiveReason, setWaiveReason] = useState('');
  const [waiveSubmitting, setWaiveSubmitting] = useState(false);

  const closePanel = useCallback(() => {
    setSelectedCpId(null);
    setPanelOpen(false);
  }, []);

  const toggleCpPanel = useCallback((cpId: string) => {
    setSelectedCpId((currentId) => {
      const nextId = currentId === cpId ? null : cpId;
      setPanelOpen(nextId !== null);
      return nextId;
    });
  }, []);

  const setCaseSelection = useCallback(
    (caseId: string | null) => {
      const nextParams = new URLSearchParams(searchParams.toString());
      if (caseId) {
        nextParams.set('caseId', caseId);
      } else {
        nextParams.delete('caseId');
      }

      const query = nextParams.toString();
      router.replace(`/dashboard/cp${query ? `?${query}` : ''}`, { scroll: false });
    },
    [router, searchParams]
  );

  useEffect(() => {
    let cancelled = false;

    const loadGlobalData = async () => {
      setGlobalLoading(true);

      try {
        const rawCases = await listCases();
        const normalizedCases = normalizeCaseSummaries(rawCases);
        if (cancelled) {
          return;
        }

        setCases(normalizedCases);

        const activeCases = normalizedCases.filter(isActiveCase);
        if (activeCases.length === 0) {
          setGlobalRecords([]);
          return;
        }

        const results = await Promise.allSettled(
          activeCases.map(async (caseItem) => {
            try {
              const response = (await listCPs(caseItem.id)) as CPListApiResponse;
              return normalizeCPs(response, caseItem);
            } catch (err) {
              // 404 means the case has no CPs yet — treat as empty, not an error.
              if (err instanceof ApiError && err.status === 404) {
                return [] as ReturnType<typeof normalizeCPs>;
              }
              throw err;
            }
          })
        );

        if (cancelled) {
          return;
        }

        const nextRecords: CommandCP[] = [];
        let failures = 0;
        for (const result of results) {
          if (result.status === 'fulfilled') {
            nextRecords.push(...result.value);
          } else {
            failures += 1;
          }
        }

        setGlobalRecords(nextRecords.sort(sortCPs));
        if (failures > 0) {
          setAlert({
            tone: 'warning',
            text: `${failures} case${failures === 1 ? '' : 's'} could not be reached. Showing data from ${activeCases.length - failures} case${activeCases.length - failures === 1 ? '' : 's'}.`,
          });
        }
      } catch (error) {
        if (!cancelled) {
          setAlert({
            tone: 'error',
            text: error instanceof Error ? error.message : 'Failed to load Conditions Precedent.',
          });
        }
      } finally {
        if (!cancelled) {
          setGlobalLoading(false);
        }
      }
    };

    void loadGlobalData();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    if (!selectedCaseId) {
      setSelectedCaseRecords([]);
      setSelectedLoaded(false);
      return;
    }

    const loadSelectedCase = async () => {
      setSelectedLoading(true);
      setSelectedLoaded(false);

      try {
        const matchingCase = cases.find((caseItem) => caseItem.id === selectedCaseId) ?? {
          id: selectedCaseId,
          title: `Case ${selectedCaseId.slice(0, 8)}`,
          status: 'Processing',
        };
        const response = (await listCPs(selectedCaseId)) as CPListApiResponse;
        if (cancelled) {
          return;
        }

        setSelectedCaseRecords(normalizeCPs(response, matchingCase).sort(sortCPs));
        setSelectedLoaded(true);
      } catch (error) {
        if (!cancelled) {
          setSelectedCaseRecords([]);
          setSelectedLoaded(true);
          setAlert({
            tone: 'error',
            text: error instanceof Error ? error.message : 'Failed to load case Conditions Precedent.',
          });
        }
      } finally {
        if (!cancelled) {
          setSelectedLoading(false);
        }
      }
    };

    void loadSelectedCase();

    return () => {
      cancelled = true;
    };
  }, [cases, selectedCaseId]);

  const selectedCase = useMemo(
    () => cases.find((caseItem) => caseItem.id === selectedCaseId) ?? null,
    [cases, selectedCaseId]
  );

  const caseBreadcrumbs = selectedCase
    ? [{ label: 'Conditions Precedent' }, { label: selectedCase.title }]
    : [{ label: 'Conditions Precedent' }];

  const visibleGlobalRecords = useMemo(
    () => globalRecords.filter((cpItem) => matchesFilter(cpItem, filter)).sort(sortCPs),
    [filter, globalRecords]
  );

  const selectedRecordsFallback = useMemo(() => {
    if (!selectedCaseId) {
      return [];
    }
    return globalRecords.filter((cpItem) => cpItem.caseId === selectedCaseId).sort(sortCPs);
  }, [globalRecords, selectedCaseId]);

  const activeSelectedRecords = selectedLoaded ? selectedCaseRecords : selectedRecordsFallback;

  const countsByFilter = useMemo(() => {
    return {
      all: globalRecords.length,
      open: globalRecords.filter((cpItem) => cpItem.status === 'Open').length,
      overdue: globalRecords.filter((cpItem) => cpItem.status === 'Open' && cpItem.overdue).length,
      fulfilled: globalRecords.filter((cpItem) => cpItem.status === 'Satisfied').length,
      waived: globalRecords.filter((cpItem) => cpItem.status === 'Waived').length,
    };
  }, [globalRecords]);

  const casesAwaitingClearance = useMemo(() => {
    const blockingCaseIds = new Set(
      globalRecords.filter((cpItem) => cpItem.status === 'Open').map((cpItem) => cpItem.caseId)
    );
    return blockingCaseIds.size;
  }, [globalRecords]);

  const selectedSummary = useMemo(() => {
    return {
      open: activeSelectedRecords.filter((cpItem) => cpItem.status === 'Open').length,
      overdue: activeSelectedRecords.filter((cpItem) => cpItem.status === 'Open' && cpItem.overdue).length,
      fulfilled: activeSelectedRecords.filter((cpItem) => cpItem.status === 'Satisfied').length,
      waived: activeSelectedRecords.filter((cpItem) => cpItem.status === 'Waived').length,
    };
  }, [activeSelectedRecords]);

  const currentRecords = useMemo(
    () => (selectedCaseId ? activeSelectedRecords : visibleGlobalRecords),
    [activeSelectedRecords, selectedCaseId, visibleGlobalRecords]
  );

  const selectedCp = useMemo(
    () => currentRecords.find((cpItem) => cpItem.id === selectedCpId) ?? null,
    [currentRecords, selectedCpId]
  );

  useEffect(() => {
    closePanel();
  }, [closePanel, selectedCaseId]);

  useEffect(() => {
    if (selectedCpId && !selectedCp) {
      closePanel();
    }
  }, [closePanel, selectedCp, selectedCpId]);

  const submitWaiverRequest = useCallback(async () => {
    if (!waiveTarget || !waiveReason.trim()) {
      return;
    }

    setWaiveSubmitting(true);
    try {
      await createApproval({
        case_id: waiveTarget.caseId,
        request_type: 'cp_waive',
        payload: {
          cp_id: waiveTarget.id,
          waiver_reason: waiveReason.trim(),
        },
      });
      setAlert({
        tone: 'success',
        text: `Waiver request submitted for ${waiveTarget.caseName}.`,
      });
      setWaiveReason('');
      setWaiveTarget(null);
    } catch (error) {
      setAlert({
        tone: 'error',
        text: error instanceof Error ? error.message : 'Failed to submit CP waiver request.',
      });
    } finally {
      setWaiveSubmitting(false);
    }
  }, [waiveReason, waiveTarget]);

  const openVerification = useCallback(
    (caseId: string) => {
      router.push(getCaseTabPath(caseId, 'verification'));
    },
    [router]
  );

  const openDocuments = useCallback(
    (caseId: string) => {
      router.push(getCaseTabPath(caseId, 'documents'));
    },
    [router]
  );

  const openWaiverDialog = useCallback((cpItem: CommandCP) => {
    setWaiveReason('');
    setWaiveTarget(cpItem);
  }, []);

  return (
    <>
      <SetPageChrome title="Conditions Precedent" breadcrumbs={caseBreadcrumbs} />

      <div className="space-y-6" data-dashboard-reveal>
        {alert ? <InlineNotice tone={alert.tone}>{alert.text}</InlineNotice> : null}

        {globalLoading && !selectedCaseId ? (
          <CPPageSkeleton />
        ) : selectedCaseId ? (
          <div className="space-y-6">
            <section className="space-y-3" data-dashboard-section>
              <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm text-stone-500">
                    <button
                      type="button"
                      onClick={() => setCaseSelection(null)}
                      className="inline-flex items-center gap-1 transition-colors hover:text-stone-300"
                    >
                      <ChevronRight className="h-4 w-4 rotate-180" />
                      All active cases
                    </button>
                    <span> / </span>
                    <span className="text-stone-300">{selectedCase?.title ?? `Case ${selectedCaseId.slice(0, 8)}`}</span>
                  </div>
                  <div>
                    <h1 className="text-3xl font-semibold tracking-[-0.04em] text-stone-100">
                      {selectedCase?.title ?? `Case ${selectedCaseId.slice(0, 8)}`}
                    </h1>
                    <p className="mt-1 text-sm text-stone-400">
                      Review Conditions Precedent, attached evidence, and clearance actions for this case.
                    </p>
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="warning">{selectedSummary.open} Open</Badge>
                  <Badge variant={selectedSummary.overdue > 0 ? 'error' : 'neutral'}>{selectedSummary.overdue} Overdue</Badge>
                  <Badge variant="success">{selectedSummary.fulfilled} Fulfilled</Badge>
                  <Button variant="outline" size="sm" onClick={() => router.push(getCaseTabPath(selectedCaseId, 'summary'))}>
                    Open workspace
                  </Button>
                </div>
              </div>
            </section>

            {selectedLoading && activeSelectedRecords.length === 0 ? (
              <Skeleton className="h-[28rem] rounded-[1.1rem]" />
            ) : activeSelectedRecords.length === 0 ? (
              <Card data-dashboard-section>
                <CardContent className="p-5">
                  <EmptyState
                    className="min-h-[140px]"
                    title="No Conditions Precedent on this case."
                    description="Rule-generated CPs will appear here once the evaluation workflow identifies pre-approval obligations."
                  />
                </CardContent>
              </Card>
            ) : (
              <div className="flex flex-col gap-4 xl:flex-row" data-dashboard-section>
                <Card className="min-w-0 flex-1">
                  <CardHeader className="pb-3">
                    <div className="flex flex-col gap-2 xl:flex-row xl:items-center xl:justify-between">
                      <div>
                        <CardTitle>Case CP Review</CardTitle>
                        <p className="mt-1 text-sm text-stone-400">
                          Dense review list with evidence detail, due-date pressure, and action routing to the existing workflow.
                        </p>
                      </div>
                      <div className="text-sm text-stone-500">
                        {activeSelectedRecords.length} CP record{activeSelectedRecords.length === 1 ? '' : 's'}
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="p-0">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-[38%]">CP</TableHead>
                          <TableHead>Category</TableHead>
                          <TableHead>Due Date</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead>Evidence</TableHead>
                          <TableHead className="text-right">Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {activeSelectedRecords.map((cpItem, index) => {
                          const isSelected = selectedCpId === cpItem.id && panelOpen;
                          return (
                            <TableRow
                              key={cpItem.id}
                              className={cn(
                                'cursor-pointer transition-colors',
                                isSelected ? 'bg-[rgba(44,50,57,0.72)]' : 'hover:bg-[rgba(34,39,45,0.45)]'
                              )}
                              onClick={() => toggleCpPanel(cpItem.id)}
                            >
                              <TableCell>
                                <div className="flex items-start gap-3">
                                  <div
                                    className={cn(
                                      'pt-0.5 text-stone-500 transition-transform duration-150',
                                      isSelected && 'translate-x-0.5 text-stone-300'
                                    )}
                                  >
                                    <ChevronRight className="h-4 w-4" />
                                  </div>
                                  <div className="min-w-0">
                                    <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">
                                      CP-{String(index + 1).padStart(3, '0')}
                                    </div>
                                    <div className="mt-1 font-medium text-stone-100">{cpItem.title}</div>
                                    <div className="mt-1 text-xs text-stone-500">
                                      {cpItem.ruleId} · Created {formatDateTime(cpItem.createdAt)}
                                    </div>
                                  </div>
                                </div>
                              </TableCell>
                              <TableCell>
                                <div className="flex items-center gap-2">
                                  <Badge variant={getCategoryVariant(cpItem.category)}>{cpItem.category}</Badge>
                                  <Badge variant={getSeverityVariant(cpItem.severity)}>{cpItem.severity}</Badge>
                                </div>
                              </TableCell>
                              <TableCell>
                                <div className="text-sm text-stone-200">{formatDate(cpItem.dueDate)}</div>
                                <div className="mt-1 text-xs text-stone-500">
                                  {cpItem.overdue ? 'Past due' : cpItem.status === 'Open' ? 'Within target' : 'Closed'}
                                </div>
                              </TableCell>
                              <TableCell>
                                <Badge variant={getStatusVariant(cpItem.status, cpItem.overdue)}>
                                  {getStatusLabel(cpItem.status)}
                                </Badge>
                              </TableCell>
                              <TableCell>
                                <div className="font-medium text-stone-100">{cpItem.evidenceCount}</div>
                                <div className="mt-1 text-xs text-stone-500">
                                  {cpItem.evidenceCount === 1 ? 'linked item' : 'linked items'}
                                </div>
                              </TableCell>
                              <TableCell>
                                <div
                                  className="flex flex-wrap justify-end gap-2"
                                  onClick={(event) => event.stopPropagation()}
                                >
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    disabled={cpItem.status !== 'Open'}
                                    onClick={() => openVerification(cpItem.caseId)}
                                  >
                                    Mark fulfilled
                                  </Button>
                                  <Button size="sm" variant="outline" onClick={() => openDocuments(cpItem.caseId)}>
                                    Request evidence
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    disabled={cpItem.status !== 'Open'}
                                    onClick={() => openWaiverDialog(cpItem)}
                                  >
                                    Waive
                                  </Button>
                                </div>
                              </TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>

                <div className="relative hidden xl:min-h-[36rem] xl:w-[400px] xl:flex-none xl:self-stretch xl:block">
                  <CpDetailPanel
                    cpItem={selectedCp}
                    open={panelOpen}
                    isGlobalMode={false}
                    onClose={closePanel}
                    onFulfill={openVerification}
                    onEvidence={openDocuments}
                    onWaive={openWaiverDialog}
                    className="absolute inset-0"
                  />
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-6">
            <section className="space-y-2" data-dashboard-section>
              <h1 className="text-3xl font-semibold tracking-[-0.04em] text-stone-100">Conditions Precedent</h1>
              <p className="text-sm text-stone-400">
                Track and manage CP obligations across all active cases.
              </p>
            </section>

            <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4" data-dashboard-section>
              <MetricCard title="Open CPs" value={countsByFilter.open} subtitle="Active obligations still pending clearance" />
              <MetricCard title="Overdue CPs" value={countsByFilter.overdue} subtitle="Open items past the derived review target" />
              <MetricCard title="Fulfilled CPs" value={countsByFilter.fulfilled} subtitle="Closed through verification or reviewer completion" />
              <MetricCard title="Cases Awaiting Clearance" value={casesAwaitingClearance} subtitle="Active matters with at least one open CP" />
            </section>

            {globalRecords.length === 0 ? (
              <Card data-dashboard-section>
                <CardContent className="p-5">
                  <EmptyState
                    className="min-h-[140px]"
                    title="No Conditions Precedent are currently tracked."
                    description="Once rule evaluation generates CP obligations, the active-case command view will populate automatically."
                  />
                </CardContent>
              </Card>
            ) : (
              <div className="flex flex-col gap-4 xl:flex-row" data-dashboard-section>
                <Card className="min-w-0 flex-1">
                  <CardHeader className="pb-3">
                    <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
                      <div className="flex flex-wrap items-center gap-2">
                        {FILTER_OPTIONS.map((option) => {
                          const count = countsByFilter[option.value];
                          const active = filter === option.value;
                          return (
                            <button
                              key={option.value}
                              type="button"
                              aria-pressed={active}
                              onClick={() => setFilter(option.value)}
                              className={cn(
                                'inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm font-medium transition-colors',
                                active
                                  ? 'border-[rgba(126,133,111,0.5)] bg-[rgba(126,133,111,0.14)] text-stone-100'
                                  : 'border-[rgba(82,90,99,0.42)] bg-[rgba(24,28,32,0.86)] text-stone-400 hover:bg-[rgba(34,39,45,0.92)] hover:text-stone-200'
                              )}
                            >
                              <span>{option.label}</span>
                              <span className="text-xs text-stone-500">{count}</span>
                            </button>
                          );
                        })}
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={countsByFilter.overdue === 0}
                        onClick={() => setFilter('overdue')}
                      >
                        Review Overdue CPs
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent className="p-0">
                    {visibleGlobalRecords.length === 0 ? (
                      <div className="px-5 py-6 text-sm text-stone-500">
                        No CP records match the current filter.
                      </div>
                    ) : (
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Case Name</TableHead>
                            <TableHead>CP Title</TableHead>
                            <TableHead>Category</TableHead>
                            <TableHead>Due Date</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead className="text-right">Actions</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {visibleGlobalRecords.map((cpItem) => {
                            const isSelected = selectedCpId === cpItem.id && panelOpen;
                            return (
                              <TableRow
                                key={`${cpItem.caseId}:${cpItem.id}`}
                                className={cn(
                                  'cursor-pointer transition-colors',
                                  isSelected ? 'bg-[rgba(44,50,57,0.72)]' : 'hover:bg-[rgba(34,39,45,0.45)]'
                                )}
                                onClick={() => toggleCpPanel(cpItem.id)}
                              >
                                <TableCell>
                                  <div className="font-medium text-stone-100">{cpItem.caseName}</div>
                                  <div className="mt-1 text-xs text-stone-500">{cpItem.caseStatus}</div>
                                </TableCell>
                                <TableCell>
                                  <div className="font-medium text-stone-100">{cpItem.title}</div>
                                  <div className="mt-1 text-xs text-stone-500">{cpItem.ruleId}</div>
                                </TableCell>
                                <TableCell>
                                  <Badge variant={getCategoryVariant(cpItem.category)}>{cpItem.category}</Badge>
                                </TableCell>
                                <TableCell>
                                  <div className="text-sm text-stone-200">{formatDate(cpItem.dueDate)}</div>
                                  <div className="mt-1 text-xs text-stone-500">
                                    {cpItem.overdue ? 'Past due' : cpItem.status === 'Open' ? 'In progress' : 'Closed'}
                                  </div>
                                </TableCell>
                                <TableCell>
                                  <Badge variant={getStatusVariant(cpItem.status, cpItem.overdue)}>
                                    {getStatusLabel(cpItem.status)}
                                  </Badge>
                                </TableCell>
                                <TableCell>
                                  <div className="flex justify-end" onClick={(event) => event.stopPropagation()}>
                                    <Button size="sm" variant="outline" onClick={() => setCaseSelection(cpItem.caseId)}>
                                      Open Case
                                    </Button>
                                  </div>
                                </TableCell>
                              </TableRow>
                            );
                          })}
                        </TableBody>
                      </Table>
                    )}
                  </CardContent>
                </Card>

                <div className="relative hidden xl:min-h-[36rem] xl:w-[400px] xl:flex-none xl:self-stretch xl:block">
                  <CpDetailPanel
                    cpItem={selectedCp}
                    open={panelOpen}
                    isGlobalMode
                    onClose={closePanel}
                    onFulfill={openVerification}
                    onEvidence={openDocuments}
                    onWaive={openWaiverDialog}
                    className="absolute inset-0"
                  />
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <Dialog
        open={waiveTarget !== null}
        onOpenChange={(open) => {
          if (!open) {
            setWaiveTarget(null);
            setWaiveReason('');
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Submit CP waiver request</DialogTitle>
            <DialogDescription>
              Waiver decisions route through the existing approvals workflow. Record the bank-style rationale before submission.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="rounded-md border border-[rgba(82,90,99,0.4)] bg-[rgba(24,28,32,0.78)] px-3 py-3 text-sm text-stone-200">
              {waiveTarget?.title}
            </div>
            <Textarea
              value={waiveReason}
              onChange={(event) => setWaiveReason(event.target.value)}
              placeholder="Enter the waiver rationale."
              className="min-h-[120px] border-[rgba(82,90,99,0.55)] bg-[rgba(22,26,30,0.92)] text-stone-100"
            />
          </div>
          <DialogFooter className="mt-2">
            <Button variant="outline" onClick={() => setWaiveTarget(null)}>
              Cancel
            </Button>
            <Button onClick={() => void submitWaiverRequest()} disabled={!waiveReason.trim()} loading={waiveSubmitting}>
              {waiveSubmitting ? 'Submitting...' : 'Submit waiver'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

export default function Page() {
  return (
    <Suspense>
      <CPPageContent />
    </Suspense>
  );
}

