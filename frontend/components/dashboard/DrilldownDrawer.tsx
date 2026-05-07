'use client';

import { useEffect, useState, useMemo, useCallback, useRef } from 'react';
import {
  Drawer,
  DrawerTabs,
  DrawerTabList,
  DrawerTabTrigger,
  DrawerTabContent,
} from '@/components/ui/drawer';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/ui/empty-state';
import { useToast } from '@/components/ui/toast';
import {
  getDashboardCohort,
  exportCohortCsv,
  exportCohortPdf,
  CohortResponse,
  CohortCaseItem,
  CohortActivityItem,
} from '@/lib/api';
import { SeverityLevel } from './Charts';

// Types for filters
export interface DrilldownFilters {
  severity?: SeverityLevel | null;
  status?: string | null;
  date?: string | null;
  owner?: 'Mine' | 'Unassigned' | null;
  escalation?: 'stale_unassigned' | null;
}

interface DrilldownDrawerProps {
  open: boolean;
  onClose: () => void;
  days: number;
  activeTab: 'cases' | 'activity';
  onActiveTabChange: (tab: 'cases' | 'activity') => void;
  filters: DrilldownFilters;
  onNavigateCase: (caseId: string) => void;
}

// Relative time formatter
function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

// Format date for display
function formatDateDisplay(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

// Aging / staleness classification — conservative thresholds for bank context
type AgingLevel = 'fresh' | 'aging' | 'stale' | 'overdue';
function getAgingLevel(dateString: string): AgingLevel {
  const diffMs = Date.now() - new Date(dateString).getTime();
  const diffDays = diffMs / (1000 * 60 * 60 * 24);
  if (diffDays < 1) return 'fresh';
  if (diffDays < 3) return 'aging';  // 1–3 days: watch
  if (diffDays < 7) return 'stale';  // 3–7 days: worth flagging
  return 'overdue';                   // 7+ days: escalation territory
}

// Compact idle label: only shown for aging/stale/overdue to avoid noise on fresh rows
function getIdleLabel(dateString: string): string | null {
  const level = getAgingLevel(dateString);
  const diffMs = Date.now() - new Date(dateString).getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

  if (level === 'fresh') return null;
  if (level === 'aging') {
    if (diffHours < 24) return null; // still same-day, skip
    return `Idle ${diffDays}d`;
  }
  if (level === 'stale') return `Stale · ${diffDays}d`;
  return `Overdue · ${diffDays}d`;
}

// Returns true if a work item should be escalation-flagged:
// high-severity exceptions present AND case has been idle 3+ days
// OR case is unassigned and idle 3+ days
function isEscalationRisk(item: CohortCaseItem): boolean {
  const aging = getAgingLevel(item.updated_at);
  const isStale = aging === 'stale' || aging === 'overdue';
  if (!isStale) return false;
  
  if (!item.assigned_to_user_id) return true;
  if (item.open_high > 0) return true;
  return false;
}

// Returns true if an approval request has been waiting too long (2+ days)
function isApprovalDelayed(updatedAt: string): boolean {
  const diffMs = Date.now() - new Date(updatedAt).getTime();
  return diffMs > 2 * 24 * 60 * 60 * 1000;
}

// Prettify action name
function prettifyAction(action: string): string {
  return action.replace(/\./g, ' · ').replace(/_/g, ' ');
}

// Build drawer title from filters
function buildTitle(filters: DrilldownFilters): string {
  const parts: string[] = [];
  if (filters.severity) parts.push(`Severity: ${filters.severity}`);
  if (filters.status) parts.push(`Status: ${filters.status}`);
  if (filters.date) parts.push(`Date: ${formatDateDisplay(filters.date)}`);
  if (filters.owner && filters.escalation !== 'stale_unassigned') {
    parts.push(`Owner: ${filters.owner === 'Mine' ? 'My cases' : 'Unassigned'}`);
  }
  if (filters.escalation === 'stale_unassigned') parts.push('Escalation: stale & unassigned');
  return parts.length > 0 ? parts.join(' + ') : 'Cohort Details';
}

// Build description from filters
function buildDescription(filters: DrilldownFilters, counts?: { cases: number; activity: number }): string {
  const filterParts: string[] = [];
  if (filters.severity) filterParts.push(`${filters.severity.toLowerCase()} severity cases`);
  if (filters.status) filterParts.push(`"${filters.status}" status`);
  if (filters.date) filterParts.push(`activity on ${formatDateDisplay(filters.date)}`);
  if (filters.owner === 'Mine') filterParts.push('my assigned cases');
  if (filters.owner === 'Unassigned' && filters.escalation !== 'stale_unassigned') {
    filterParts.push('unassigned cases');
  }
  if (filters.escalation === 'stale_unassigned') filterParts.push('stale unassigned escalation cases');
  
  if (filterParts.length === 0) return 'All cases and activity';
  
  let desc = `Showing ${filterParts.join(' with ')}`;
  if (counts) {
    desc += ` · ${counts.cases} case${counts.cases !== 1 ? 's' : ''}, ${counts.activity} event${counts.activity !== 1 ? 's' : ''}`;
  }
  return desc;
}

function getOwnerLabel(item: {
  assigned_to_name?: string | null;
  assigned_to_email?: string | null;
}): string {
  if (item.assigned_to_name) {
    return `Assigned to ${item.assigned_to_name}`;
  }

  if (item.assigned_to_email) {
    return `Assigned to ${item.assigned_to_email.split('@')[0]}`;
  }

  return 'Unassigned';
}

function getHandoffLabel(item: CohortCaseItem): string {
  if (!item.assigned_to_user_id && item.status === 'Ready for Approval') {
    return 'Ready but unassigned';
  }

  if (!item.assigned_to_user_id) {
    return 'Needs assignment';
  }

  if (item.status === 'Ready for Approval') {
    return 'Reviewer-owned';
  }

  return getOwnerLabel(item);
}

export function DrilldownDrawer({
  open,
  onClose,
  days,
  activeTab,
  onActiveTabChange,
  filters,
  onNavigateCase,
}: DrilldownDrawerProps) {
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<CohortResponse | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [exportingCsv, setExportingCsv] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [exportSuccess, setExportSuccess] = useState<string | null>(null);
  const { toast } = useToast();
  const dataRef = useRef<CohortResponse | null>(null);

  // Fetch cohort data when drawer opens or filters change
  const fetchCohort = useCallback(async () => {
    if (!open) return;

    const hasExistingData = dataRef.current !== null;
    if (hasExistingData) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError(null);

    try {
      const result = await getDashboardCohort({
        days,
        severity: filters.severity,
        status: filters.status,
        date: filters.date,
        owner: filters.owner ? filters.owner.toLowerCase() : null,
        escalation: filters.escalation,
        limit: 100,
      });
      setData(result);
      dataRef.current = result;
    } catch (e: any) {
      setError(e.message || 'Failed to load cohort data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [open, days, filters]);

  useEffect(() => {
    if (open) {
      void fetchCohort();
      setExportSuccess(null);
    }
  }, [open, fetchCohort]);

  // Handle CSV export
  const handleExportCsv = async () => {
    setExportingCsv(true);
    setExportSuccess(null);
    try {
      const result = await exportCohortCsv({
        days,
        severity: filters.severity,
        status: filters.status,
        date: filters.date,
        owner: filters.owner ? filters.owner.toLowerCase() : null,
        escalation: filters.escalation,
      });
      window.open(result.url, '_blank');
      setExportSuccess(`CSV: ${result.row_count} rows`);
      toast({
        title: 'Cohort CSV exported.',
        description: `${result.row_count} rows prepared for download.`,
        variant: 'success',
      });
    } catch (e: any) {
      setError(e.message || 'Export failed');
      toast({
        title: 'Unable to export CSV.',
        description: e.message || 'Please retry.',
        variant: 'error',
      });
    } finally {
      setExportingCsv(false);
    }
  };

  // Handle PDF export
  const handleExportPdf = async () => {
    setExportingPdf(true);
    setExportSuccess(null);
    try {
      const result = await exportCohortPdf({
        days,
        severity: filters.severity,
        status: filters.status,
        date: filters.date,
        owner: filters.owner ? filters.owner.toLowerCase() : null,
        escalation: filters.escalation,
      });
      window.open(result.url, '_blank');
      setExportSuccess(`PDF report generated`);
      toast({
        title: 'Cohort PDF exported.',
        description: 'The filtered report opened in a new tab.',
        variant: 'success',
      });
    } catch (e: any) {
      setError(e.message || 'PDF export failed');
      toast({
        title: 'Unable to export PDF.',
        description: e.message || 'Please retry.',
        variant: 'error',
      });
    } finally {
      setExportingPdf(false);
    }
  };

  // Filter cases by search query
  const filteredCases = useMemo(() => {
    if (!data?.cases) return [];
    if (!searchQuery.trim()) return data.cases;

    const query = searchQuery.toLowerCase();
    return data.cases.filter(
      (c) =>
        c.title.toLowerCase().includes(query) ||
        c.status.toLowerCase().includes(query)
    );
  }, [data?.cases, searchQuery]);

  const title = buildTitle(filters);
  const description = buildDescription(filters, data?.counts);

  return (
    <Drawer open={open} onClose={onClose} title={title} description={description} width="lg">
      {/* Export action bar */}
      <div className="flex items-center justify-between border-b border-[rgba(82,90,99,0.34)] bg-[rgba(18,22,27,0.72)] px-6 py-3">
        <div className="flex items-center gap-2">
          {exportSuccess && (
            <span className="flex items-center gap-1 text-xs text-[rgb(187,205,189)]">
              <CheckIcon className="w-3.5 h-3.5" />
              {exportSuccess}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleExportPdf}
            disabled={exportingPdf || exportingCsv || loading || !data?.counts.cases}
          >
            {exportingPdf ? 'Generating...' : 'Export PDF'}
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleExportCsv}
            disabled={exportingCsv || exportingPdf || loading || !data?.counts.cases}
          >
            {exportingCsv ? 'Exporting...' : 'Export CSV'}
          </Button>
        </div>
      </div>

      <DrawerTabs value={activeTab} onValueChange={(v) => onActiveTabChange(v as 'cases' | 'activity')}>
        <DrawerTabList>
          <DrawerTabTrigger
            value="cases"
            activeValue={activeTab}
            onSelect={(v) => onActiveTabChange(v as 'cases' | 'activity')}
            count={data?.counts.cases}
          >
            Cases
          </DrawerTabTrigger>
          <DrawerTabTrigger
            value="activity"
            activeValue={activeTab}
            onSelect={(v) => onActiveTabChange(v as 'cases' | 'activity')}
            count={data?.counts.activity}
          >
            Activity
          </DrawerTabTrigger>
        </DrawerTabList>

        {refreshing ? (
          <div className="border-b border-[rgba(82,90,99,0.3)] px-6 py-2 text-xs text-stone-400">
            Updating filtered cohort…
          </div>
        ) : null}
        {error && data ? (
          <div className="border-b border-[rgba(189,90,86,0.24)] bg-[rgba(189,90,86,0.08)] px-6 py-2 text-xs text-[rgb(240,205,202)]">
            Unable to refresh cohort details. Showing the most recent loaded results.
          </div>
        ) : null}

        {/* Cases Tab */}
        <DrawerTabContent value="cases" activeValue={activeTab}>
          {/* Search Box */}
          <div className="border-b border-[rgba(82,90,99,0.3)] p-4">
            <div className="relative">
              <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-500" />
              <input
                type="text"
                placeholder="Search cases by title..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-md border border-[rgba(82,90,99,0.5)] bg-[rgba(22,26,30,0.92)] py-2 pl-10 pr-4 text-sm text-stone-200 placeholder:text-stone-500 focus:outline-none focus:ring-2 focus:ring-[rgba(126,133,111,0.85)]"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-stone-500 transition-colors hover:text-stone-200"
                >
                  <CloseIcon className="w-4 h-4" />
                </button>
              )}
            </div>
            {searchQuery && (
              <p className="mt-2 text-xs text-stone-500">
                Showing {filteredCases.length} of {data?.cases.length || 0} cases
              </p>
            )}
          </div>

          {/* Cases List */}
          <div className="space-y-2 p-3">
            {loading && !data ? (
              Array.from({ length: 5 }).map((_, i) => (
                <CaseItemSkeleton key={i} />
              ))
            ) : error && !data ? (
              <ErrorState message={error} onRetry={fetchCohort} />
            ) : filteredCases.length > 0 ? (
              filteredCases.map((item) => (
                <CaseItem
                  key={item.case_id}
                  item={item}
                  onClick={() => onNavigateCase(item.case_id)}
                />
              ))
            ) : (
              <div className="p-8">
                <EmptyState
                  icon={<EmptyIcon />}
                  title={
                    searchQuery
                      ? 'No matching cases'
                      : filters.escalation === 'stale_unassigned'
                      ? 'No stale unassigned cases'
                      : 'No cases require attention'
                  }
                  description={
                    searchQuery
                      ? 'Try adjusting your search query.'
                      : filters.escalation === 'stale_unassigned'
                      ? 'No stale unassigned cases match the current dashboard filters.'
                      : 'No cases match the current dashboard filters.'
                  }
                  action={
                    searchQuery ? (
                      <Button variant="outline" size="sm" onClick={() => setSearchQuery('')}>
                        Clear search
                      </Button>
                    ) : undefined
                  }
                />
              </div>
            )}
          </div>
        </DrawerTabContent>

        {/* Activity Tab */}
        <DrawerTabContent value="activity" activeValue={activeTab}>
          <div className="space-y-2 p-3">
            {loading && !data ? (
              Array.from({ length: 8 }).map((_, i) => (
                <ActivityItemSkeleton key={i} />
              ))
            ) : error && !data ? (
              <ErrorState message={error} onRetry={fetchCohort} />
            ) : data && data.activity.length > 0 ? (
              data.activity.map((item, i) => (
                <ActivityItemRow
                  key={`${item.created_at}-${i}`}
                  item={item}
                  onNavigateCase={onNavigateCase}
                />
              ))
            ) : (
              <div className="p-8">
                <EmptyState
                  icon={<EmptyIcon />}
                  title="No recent activity recorded"
                  description="No activity matches the current dashboard filters."
                />
              </div>
            )}
          </div>
        </DrawerTabContent>
      </DrawerTabs>
    </Drawer>
  );
}

// Case item component
function CaseItem({ item, onClick }: { item: CohortCaseItem; onClick: () => void }) {
  const statusColors: Record<string, 'info' | 'warning' | 'success' | 'neutral'> = {
    New: 'info',
    Processing: 'info',
    Review: 'warning',
    'Pending Docs': 'warning',
    'Ready for Approval': 'success',
    Approved: 'success',
    Rejected: 'neutral',
    Closed: 'neutral',
  };

  const idleLabel = getIdleLabel(item.updated_at);
  const escalationRisk = isEscalationRisk(item);
  const approvalDelayed = item.status === 'Ready for Approval' && isApprovalDelayed(item.updated_at);

  return (
    <div className="flex items-center gap-4 rounded-md border border-[rgba(82,90,99,0.28)] bg-[rgba(18,22,27,0.76)] p-4 transition-colors hover:bg-[rgba(34,39,45,0.82)]">
      <div className="flex-1 min-w-0">
        <p className="truncate text-sm font-medium text-stone-200">{item.title}</p>
        <div className="mt-1.5 flex flex-wrap items-center gap-2.5">
          <Badge variant={statusColors[item.status] || 'neutral'} className="text-xs">
            {item.status}
          </Badge>
          {item.open_high > 0 && (
            <Badge variant="error" className="flex items-center gap-1">
              High {item.open_high}
              {escalationRisk && item.open_high > 0 && <span className="text-[10px] ml-1">⚠ Stale blocker</span>}
            </Badge>
          )}
          {escalationRisk && !item.assigned_to_user_id && (
             <Badge variant="warning" className="flex items-center gap-1">
               <span className="text-[10px]">⚠ Needs owner</span>
             </Badge>
          )}
          {item.open_medium > 0 && (
            <Badge variant="warning">Medium {item.open_medium}</Badge>
          )}
          {item.open_low > 0 && (
            <Badge variant="success">Low {item.open_low}</Badge>
          )}
          {item.pending_verifications > 0 && (
            <Badge variant="info">Pending {item.pending_verifications}</Badge>
          )}
          <span
            className={`text-xs ${item.assigned_to_user_id ? 'text-stone-400' : 'text-[rgb(219,156,153)] font-medium'}`}
            title={item.assigned_to_email || ''}
          >
            · {getHandoffLabel(item)}
          </span>
          <span className="text-xs text-stone-500">· {formatRelativeTime(item.updated_at)}</span>
          {idleLabel && (
            <div className={`text-xs ml-auto font-medium ${
              idleLabel.includes('Overdue') ? 'text-[rgb(219,156,153)]' :
              idleLabel.includes('Stale') ? 'text-[rgb(219,194,137)]' : 
              'text-stone-400'
            }`}>
              {idleLabel}
            </div>
          )}
          {approvalDelayed && (
            <div className="text-xs ml-auto font-medium text-[rgb(219,194,137)]">
              ⚠ Approval delayed
            </div>
          )}
        </div>
      </div>
      <Button variant="outline" size="sm" onClick={onClick}>
        Open
      </Button>
    </div>
  );
}

// Case item skeleton
function CaseItemSkeleton() {
  return (
    <div className="flex items-center gap-4 rounded-md border border-[rgba(82,90,99,0.2)] bg-[rgba(18,22,27,0.52)] p-4">
      <div className="flex-1 space-y-2">
        <Skeleton className="h-4 w-3/4" />
        <div className="flex gap-2">
          <Skeleton className="h-5 w-16 rounded-md" />
          <Skeleton className="h-5 w-12 rounded-md" />
          <Skeleton className="h-5 w-20" />
        </div>
      </div>
      <Skeleton className="h-8 w-16 rounded-lg" />
    </div>
  );
}

// Activity item component
function ActivityItemRow({
  item,
  onNavigateCase,
}: {
  item: CohortActivityItem;
  onNavigateCase: (id: string) => void;
}) {
  const initials = item.actor_email
    ? item.actor_email.substring(0, 2).toUpperCase()
    : 'SYS';

  return (
    <div className="flex items-start gap-3 rounded-md border border-[rgba(82,90,99,0.28)] bg-[rgba(18,22,27,0.76)] px-4 py-3 transition-colors hover:bg-[rgba(34,39,45,0.82)]">
      <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md border border-[rgba(82,90,99,0.34)] bg-[rgba(34,39,45,0.8)] text-xs font-medium text-stone-300">
        {initials}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-stone-300">
          <span className="font-medium capitalize">{prettifyAction(item.action)}</span>
        </p>
        {item.case_title && (
          <button
            onClick={() => item.case_id && onNavigateCase(item.case_id)}
            className="mt-0.5 block max-w-full truncate text-xs text-stone-200 transition-colors hover:text-stone-50"
          >
            {item.case_title}
          </button>
        )}
        <p className="mt-0.5 text-xs text-stone-500">
          {item.actor_email || 'System'} · {formatRelativeTime(item.created_at)}
        </p>
      </div>
    </div>
  );
}

// Activity item skeleton
function ActivityItemSkeleton() {
  return (
    <div className="flex items-start gap-3 rounded-md border border-[rgba(82,90,99,0.2)] bg-[rgba(18,22,27,0.52)] px-4 py-3">
      <Skeleton className="h-8 w-8 rounded-md flex-shrink-0" />
      <div className="flex-1 space-y-1.5">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-3 w-2/3" />
      </div>
    </div>
  );
}

// Error state component
function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="p-8">
      <div className="text-center">
        <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-md border border-[rgba(189,90,86,0.3)] bg-[rgba(151,70,67,0.16)]">
          <ErrorIcon className="w-6 h-6 text-[rgb(219,156,153)]" />
        </div>
        <p className="mb-1 text-sm font-medium text-stone-200">Failed to load</p>
        <p className="mb-4 text-xs text-stone-500">{message}</p>
        <Button variant="outline" size="sm" onClick={onRetry}>
          Retry
        </Button>
      </div>
    </div>
  );
}

// Icons
function SearchIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    </svg>
  );
}

function CloseIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
    </svg>
  );
}

function EmptyIcon() {
  return (
    <svg className="w-6 h-6 text-stone-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5m6 4.125l2.25 2.25m0 0l2.25 2.25M12 13.875l2.25-2.25M12 13.875l-2.25 2.25M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
    </svg>
  );
}

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
    </svg>
  );
}

function ErrorIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
    </svg>
  );
}
