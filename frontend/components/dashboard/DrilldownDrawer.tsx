'use client';

import { useEffect, useState, useMemo, useCallback } from 'react';
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
import {
  getDashboardCohort,
  exportCohortCsv,
  exportCohortPdf,
  CohortResponse,
  CohortCaseItem,
  CohortActivityItem,
} from '@/lib/api';
import { chartPalette, SeverityLevel } from './Charts';

// Types for filters
export interface DrilldownFilters {
  severity?: SeverityLevel | null;
  status?: string | null;
  date?: string | null;
}

interface DrilldownDrawerProps {
  open: boolean;
  onClose: () => void;
  days: number;
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
  return parts.length > 0 ? parts.join(' + ') : 'Cohort Details';
}

// Build description from filters
function buildDescription(filters: DrilldownFilters, counts?: { cases: number; activity: number }): string {
  const filterParts: string[] = [];
  if (filters.severity) filterParts.push(`${filters.severity.toLowerCase()} severity cases`);
  if (filters.status) filterParts.push(`"${filters.status}" status`);
  if (filters.date) filterParts.push(`activity on ${formatDateDisplay(filters.date)}`);
  
  if (filterParts.length === 0) return 'All cases and activity';
  
  let desc = `Showing ${filterParts.join(' with ')}`;
  if (counts) {
    desc += ` · ${counts.cases} case${counts.cases !== 1 ? 's' : ''}, ${counts.activity} event${counts.activity !== 1 ? 's' : ''}`;
  }
  return desc;
}

export function DrilldownDrawer({
  open,
  onClose,
  days,
  filters,
  onNavigateCase,
}: DrilldownDrawerProps) {
  const [activeTab, setActiveTab] = useState<'cases' | 'activity'>('cases');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<CohortResponse | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [exportingCsv, setExportingCsv] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [exportSuccess, setExportSuccess] = useState<string | null>(null);

  // Fetch cohort data when drawer opens or filters change
  const fetchCohort = useCallback(async () => {
    if (!open) return;

    setLoading(true);
    setError(null);

    try {
      const result = await getDashboardCohort({
        days,
        severity: filters.severity,
        status: filters.status,
        date: filters.date,
        limit: 100,
      });
      setData(result);
    } catch (e: any) {
      setError(e.message || 'Failed to load cohort data');
    } finally {
      setLoading(false);
    }
  }, [open, days, filters]);

  useEffect(() => {
    if (open) {
      fetchCohort();
      setSearchQuery('');
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
      });
      window.open(result.url, '_blank');
      setExportSuccess(`CSV: ${result.row_count} rows`);
    } catch (e: any) {
      setError(e.message || 'Export failed');
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
      });
      window.open(result.url, '_blank');
      setExportSuccess(`PDF report generated`);
    } catch (e: any) {
      setError(e.message || 'PDF export failed');
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
      <div className="px-6 py-3 border-b border-slate-700/50 flex items-center justify-between bg-slate-800/30">
        <div className="flex items-center gap-2">
          {exportSuccess && (
            <span className="text-xs text-emerald-400 flex items-center gap-1">
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

      <DrawerTabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'cases' | 'activity')}>
        <DrawerTabList>
          <DrawerTabTrigger
            value="cases"
            activeValue={activeTab}
            onSelect={(v) => setActiveTab(v as 'cases' | 'activity')}
            count={data?.counts.cases}
          >
            Cases
          </DrawerTabTrigger>
          <DrawerTabTrigger
            value="activity"
            activeValue={activeTab}
            onSelect={(v) => setActiveTab(v as 'cases' | 'activity')}
            count={data?.counts.activity}
          >
            Activity
          </DrawerTabTrigger>
        </DrawerTabList>

        {/* Cases Tab */}
        <DrawerTabContent value="cases" activeValue={activeTab}>
          {/* Search Box */}
          <div className="p-4 border-b border-slate-700/50">
            <div className="relative">
              <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="text"
                placeholder="Search cases by title..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                >
                  <CloseIcon className="w-4 h-4" />
                </button>
              )}
            </div>
            {searchQuery && (
              <p className="mt-2 text-xs text-slate-500">
                Showing {filteredCases.length} of {data?.cases.length || 0} cases
              </p>
            )}
          </div>

          {/* Cases List */}
          <div className="divide-y divide-slate-700/50">
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <CaseItemSkeleton key={i} />
              ))
            ) : error ? (
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
                  title={searchQuery ? 'No matching cases' : 'No cases found'}
                  description={
                    searchQuery
                      ? 'Try adjusting your search query.'
                      : 'No cases match the current filters.'
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
          <div className="divide-y divide-slate-700/50">
            {loading ? (
              Array.from({ length: 8 }).map((_, i) => (
                <ActivityItemSkeleton key={i} />
              ))
            ) : error ? (
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
                  title="No activity found"
                  description="No activity matches the current filters."
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

  return (
    <div className="flex items-center gap-4 p-4 hover:bg-slate-800/50 transition-colors">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-200 truncate">{item.title}</p>
        <div className="flex items-center gap-3 mt-1.5 flex-wrap">
          <Badge variant={statusColors[item.status] || 'neutral'} className="text-xs">
            {item.status}
          </Badge>
          {item.open_high > 0 && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-400">
              High: {item.open_high}
            </span>
          )}
          {item.open_medium > 0 && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400">
              Med: {item.open_medium}
            </span>
          )}
          {item.open_low > 0 && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400">
              Low: {item.open_low}
            </span>
          )}
          {item.pending_verifications > 0 && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-400">
              Pending: {item.pending_verifications}
            </span>
          )}
          <span className="text-xs text-slate-500">{formatRelativeTime(item.updated_at)}</span>
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
    <div className="flex items-center gap-4 p-4">
      <div className="flex-1 space-y-2">
        <Skeleton className="h-4 w-3/4" />
        <div className="flex gap-2">
          <Skeleton className="h-5 w-16 rounded-full" />
          <Skeleton className="h-5 w-12 rounded-full" />
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
    <div className="flex items-start gap-3 px-4 py-3 hover:bg-slate-800/50 transition-colors">
      <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center flex-shrink-0 text-xs font-medium text-slate-300">
        {initials}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-slate-300">
          <span className="font-medium capitalize">{prettifyAction(item.action)}</span>
        </p>
        {item.case_title && (
          <button
            onClick={() => item.case_id && onNavigateCase(item.case_id)}
            className="text-xs text-cyan-400 hover:text-cyan-300 mt-0.5 truncate block max-w-full"
          >
            {item.case_title}
          </button>
        )}
        <p className="text-xs text-slate-500 mt-0.5">
          {item.actor_email || 'System'} · {formatRelativeTime(item.created_at)}
        </p>
      </div>
    </div>
  );
}

// Activity item skeleton
function ActivityItemSkeleton() {
  return (
    <div className="flex items-start gap-3 px-4 py-3">
      <Skeleton className="w-8 h-8 rounded-full flex-shrink-0" />
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
        <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-rose-500/20 flex items-center justify-center">
          <ErrorIcon className="w-6 h-6 text-rose-400" />
        </div>
        <p className="text-sm font-medium text-slate-200 mb-1">Failed to load</p>
        <p className="text-xs text-slate-500 mb-4">{message}</p>
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
    <svg className="w-6 h-6 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
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
