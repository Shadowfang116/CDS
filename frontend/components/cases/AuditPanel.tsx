'use client';

import { Fragment, useCallback, useEffect, useMemo, useState } from 'react';
import { getCaseAuditTimeline } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { EmptyState } from '@/components/ui/empty-state';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

type CaseAuditEvent = {
  timestamp: string;
  user_id: string;
  user_name?: string | null;
  action: string;
  entity_type?: string | null;
  entity_id?: string | null;
  details: Record<string, any>;
};

type AuditPanelProps = {
  caseId: string;
};

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

function getActorLabel(event: CaseAuditEvent): string {
  return event.user_name?.trim() || event.user_id || 'System';
}

function getSummary(event: CaseAuditEvent): string {
  const details = event.details ?? {};

  if (typeof details.reason === 'string' && details.reason.trim()) {
    return details.reason.trim();
  }

  if (typeof details.note === 'string' && details.note.trim()) {
    return details.note.trim();
  }

  if (typeof details.title === 'string' && details.title.trim()) {
    return details.title.trim();
  }

  const changes = [
    details.old_status && details.new_status ? `${details.old_status} -> ${details.new_status}` : null,
    details.old_value !== undefined && details.new_value !== undefined
      ? `${String(details.old_value)} -> ${String(details.new_value)}`
      : null,
  ].filter(Boolean);

  if (changes.length > 0) {
    return changes.join(' • ');
  }

  return 'No additional summary recorded.';
}

function AuditTableSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 6 }).map((_, index) => (
        <div key={index} className="grid grid-cols-[1.3fr_1fr_1.1fr_0.9fr_0.9fr_1.6fr] gap-3 rounded-lg border border-[rgba(82,90,99,0.32)] bg-[rgba(24,28,32,0.82)] px-4 py-3">
          <Skeleton className="h-5 w-28" />
          <Skeleton className="h-5 w-24" />
          <Skeleton className="h-5 w-24" />
          <Skeleton className="h-5 w-20" />
          <Skeleton className="h-5 w-20" />
          <Skeleton className="h-5 w-full" />
        </div>
      ))}
    </div>
  );
}

export function AuditPanel({ caseId }: AuditPanelProps) {
  const [events, setEvents] = useState<CaseAuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [panelError, setPanelError] = useState<string | null>(null);
  const [expandedIndex, setExpandedIndex] = useState<string | null>(null);
  const [actorFilter, setActorFilter] = useState('');
  const [actionFilter, setActionFilter] = useState('');

  const loadAudit = useCallback(async () => {
    setLoading(true);
    setPanelError(null);

    try {
      const response = await getCaseAuditTimeline(caseId);
      const nextEvents = Array.isArray(response.events) ? response.events : [];
      nextEvents.sort((left, right) => new Date(right.timestamp).getTime() - new Date(left.timestamp).getTime());
      setEvents(nextEvents);
    } catch (error: any) {
      setPanelError(error.message || 'Failed to load audit history');
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    void loadAudit();
  }, [loadAudit]);

  const filteredEvents = useMemo(() => {
    const actorQuery = actorFilter.trim().toLowerCase();
    const actionQuery = actionFilter.trim().toLowerCase();

    return events.filter((event) => {
      const actorValue = getActorLabel(event).toLowerCase();
      const actionValue = event.action.toLowerCase();
      return (!actorQuery || actorValue.includes(actorQuery)) && (!actionQuery || actionValue.includes(actionQuery));
    });
  }, [actionFilter, actorFilter, events]);

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <CardTitle>Audit</CardTitle>
            <p className="mt-1 text-sm text-stone-400">
              Review case-level activity, reviewer actions, and change metadata.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <Input
              value={actorFilter}
              onChange={(event) => setActorFilter(event.target.value)}
              placeholder="Filter by actor"
            />
            <Input
              value={actionFilter}
              onChange={(event) => setActionFilter(event.target.value)}
              placeholder="Filter by action"
            />
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {panelError ? (
          <div className="rounded-lg border border-[rgba(189,90,86,0.36)] bg-[rgba(189,90,86,0.12)] px-4 py-3 text-sm text-[rgb(219,156,153)]">
            {panelError}
          </div>
        ) : null}

        {loading ? (
          <AuditTableSkeleton />
        ) : filteredEvents.length === 0 ? (
          <EmptyState
            title="No activity recorded."
            description="Audit entries will appear here as reviewer actions and automated checks are recorded."
          />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Timestamp</TableHead>
                <TableHead>Actor</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>Module</TableHead>
                <TableHead>Object</TableHead>
                <TableHead>Summary</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredEvents.map((event) => {
                const rowKey = `${event.timestamp}:${event.action}:${event.entity_id ?? 'none'}`;
                const isExpanded = expandedIndex === rowKey;

                return (
                  <Fragment key={rowKey}>
                    <TableRow className="cursor-pointer" onClick={() => setExpandedIndex(isExpanded ? null : rowKey)}>
                      <TableCell>{formatDateTime(event.timestamp)}</TableCell>
                      <TableCell>{getActorLabel(event)}</TableCell>
                      <TableCell>{event.action}</TableCell>
                      <TableCell>{event.entity_type || '—'}</TableCell>
                      <TableCell>{event.entity_id ? `${event.entity_id.slice(0, 8)}…` : '—'}</TableCell>
                      <TableCell>{getSummary(event)}</TableCell>
                    </TableRow>
                    {isExpanded ? (
                      <TableRow className="hover:bg-transparent">
                        <TableCell colSpan={6} className="bg-[rgba(22,26,30,0.9)]">
                          <div className="grid gap-4 lg:grid-cols-2">
                            <div className="space-y-3">
                              <div>
                                <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">Old Value</div>
                                <div className="mt-2 rounded-md border border-[rgba(82,90,99,0.36)] bg-[rgba(29,34,39,0.78)] px-3 py-2 text-sm text-stone-200">
                                  {event.details?.old_value !== undefined
                                    ? String(event.details.old_value)
                                    : event.details?.old_status ?? '—'}
                                </div>
                              </div>
                              <div>
                                <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">New Value</div>
                                <div className="mt-2 rounded-md border border-[rgba(82,90,99,0.36)] bg-[rgba(29,34,39,0.78)] px-3 py-2 text-sm text-stone-200">
                                  {event.details?.new_value !== undefined
                                    ? String(event.details.new_value)
                                    : event.details?.new_status ?? '—'}
                                </div>
                              </div>
                            </div>
                            <div>
                              <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">Metadata JSON</div>
                              <pre className="mt-2 overflow-x-auto rounded-md border border-[rgba(82,90,99,0.36)] bg-[rgba(29,34,39,0.78)] px-3 py-2 text-xs text-stone-300">
                                {JSON.stringify(event.details ?? {}, null, 2)}
                              </pre>
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
  );
}
