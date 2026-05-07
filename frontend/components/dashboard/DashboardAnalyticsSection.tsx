'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  TrendLineChart,
  chartPalette,
  type SeverityLevel,
} from '@/components/dashboard/Charts';
import { DashboardAnalyticsResponse } from '@/lib/api';

interface DashboardAnalyticsSectionProps {
  data: DashboardAnalyticsResponse | null;
  loading: boolean;
  error: string | null;
  selectedDate: string | null;
  selectedStatus: string | null;
  selectedSeverity: SeverityLevel | null;
  onSelectDate: (date: string) => void;
  onSelectStatus: (status: string) => void;
  onSelectSeverity: (severity: SeverityLevel) => void;
  onRetry: () => void;
}

export function DashboardAnalyticsSection({
  data,
  loading,
  error,
  selectedDate,
  selectedStatus,
  selectedSeverity,
  onSelectDate,
  onSelectStatus,
  onSelectSeverity,
  onRetry,
}: DashboardAnalyticsSectionProps) {
  const trendTotals = (data?.timeseries || []).reduce(
    (acc, entry) => {
      acc.casesCreated += entry.cases_created;
      acc.exportsGenerated += entry.exports_generated;
      return acc;
    },
    { casesCreated: 0, exportsGenerated: 0 }
  );

  const severityItems = [
    { label: 'High', value: data?.exceptions_by_severity.high ?? 0, tone: 'error' as const, color: chartPalette.high },
    { label: 'Medium', value: data?.exceptions_by_severity.medium ?? 0, tone: 'warning' as const, color: chartPalette.medium },
    { label: 'Low', value: data?.exceptions_by_severity.low ?? 0, tone: 'success' as const, color: chartPalette.low },
  ];

  const statusItems = Object.entries(data?.cases_by_status || {})
    .filter(([, value]) => value > 0)
    .sort(([, left], [, right]) => right - left)
    .slice(0, 5);

  if (error && !data) {
    return (
      <section className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.65fr)_minmax(0,1fr)]">
        <Card>
          <CardHeader className="border-b border-[rgba(82,90,99,0.34)]">
            <CardTitle className="text-base font-semibold tracking-tight normal-case text-stone-100">Analytics unavailable</CardTitle>
            <p className="mt-1 text-sm text-stone-400">Secondary dashboard analytics failed to load. Core queue and activity remain available.</p>
          </CardHeader>
          <CardContent>
            <div className="flex min-h-[320px] flex-col items-center justify-center gap-4 text-center">
              <p className="max-w-md text-sm text-stone-400">{error}</p>
              <Button variant="outline" size="sm" onClick={onRetry}>
                Retry analytics
              </Button>
            </div>
          </CardContent>
        </Card>
      </section>
    );
  }

  const chartLoading = loading && !data;

  return (
    <section className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.65fr)_minmax(0,1fr)]">
      <Card>
        <CardHeader className="border-b border-[rgba(82,90,99,0.34)]">
          <CardTitle className="text-base font-semibold tracking-tight text-stone-100">Recent operating trend</CardTitle>
          <p className="mt-1 text-sm text-stone-400">A compact 14-day view of cases opened and exports generated. Select a point to filter by date.</p>
        </CardHeader>
        <CardContent>
          <TrendLineChart
            data={data?.timeseries || []}
            loading={chartLoading}
            selectedDate={selectedDate}
            onSelectDate={onSelectDate}
          />
          <div className="mt-4 grid gap-3 border-t border-[rgba(82,90,99,0.28)] pt-4 sm:grid-cols-2">
            <AnalyticsMiniStat
              label="Cases created"
              value={trendTotals.casesCreated}
              hint="Selected window"
              color={chartPalette.primary}
            />
            <AnalyticsMiniStat
              label="Exports generated"
              value={trendTotals.exportsGenerated}
              hint="Selected window"
              color={chartPalette.secondary}
            />
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-6">
        <Card>
          <CardHeader className="border-b border-[rgba(82,90,99,0.34)]">
            <CardTitle className="text-base font-semibold tracking-tight text-stone-100">Current exception mix</CardTitle>
            <p className="mt-1 text-sm text-stone-400">Use severity filters to narrow the queue without opening a full chart view.</p>
          </CardHeader>
          <CardContent className="space-y-2">
            {chartLoading ? (
              Array.from({ length: 3 }).map((_, index) => (
                <div
                  key={index}
                  className="h-14 rounded-md border border-[rgba(82,90,99,0.28)] bg-[rgba(18,22,26,0.44)]"
                />
              ))
            ) : severityItems.some((item) => item.value > 0) ? (
              severityItems.map((item) => {
                const isSelected = selectedSeverity === item.label;
                const hasOtherSelection = selectedSeverity && selectedSeverity !== item.label;

                return (
                  <button
                    key={item.label}
                    type="button"
                    onClick={() => onSelectSeverity(item.label as SeverityLevel)}
                    className={`flex w-full items-center justify-between gap-3 rounded-md border px-3 py-3 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(126,133,111,0.85)] ${
                      isSelected
                        ? 'border-[rgba(126,133,111,0.55)] bg-[rgba(34,39,45,0.9)]'
                        : 'border-[rgba(82,90,99,0.32)] bg-[rgba(18,22,26,0.44)] hover:bg-[rgba(26,31,36,0.68)]'
                    } ${hasOtherSelection ? 'opacity-60' : 'opacity-100'}`}
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 text-sm font-medium text-stone-200">
                        <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: item.color }} />
                        {item.label}
                      </div>
                      <div className="mt-1 text-xs text-stone-500">Open exceptions in the current window</div>
                    </div>
                    <Badge variant={item.tone}>{item.value}</Badge>
                  </button>
                );
              })
            ) : (
              <CompactPanelEmptyState message="No open exceptions in this range." />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="border-b border-[rgba(82,90,99,0.34)]">
            <CardTitle className="text-base font-semibold tracking-tight text-stone-100">Operational status mix</CardTitle>
            <p className="mt-1 text-sm text-stone-400">Top active statuses for the selected window. Open one to focus the queue.</p>
          </CardHeader>
          <CardContent className="space-y-2">
            {chartLoading ? (
              Array.from({ length: 4 }).map((_, index) => (
                <div
                  key={index}
                  className="h-12 rounded-md border border-[rgba(82,90,99,0.28)] bg-[rgba(18,22,26,0.44)]"
                />
              ))
            ) : statusItems.length > 0 ? (
              statusItems.map(([status, count]) => {
                const isSelected = selectedStatus === status;
                const hasOtherSelection = selectedStatus && selectedStatus !== status;

                return (
                  <button
                    key={status}
                    type="button"
                    onClick={() => onSelectStatus(status)}
                    className={`flex w-full items-center justify-between gap-3 rounded-md border px-3 py-2.5 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(126,133,111,0.85)] ${
                      isSelected
                        ? 'border-[rgba(126,133,111,0.55)] bg-[rgba(34,39,45,0.9)]'
                        : 'border-[rgba(82,90,99,0.32)] bg-[rgba(18,22,26,0.44)] hover:bg-[rgba(26,31,36,0.68)]'
                    } ${hasOtherSelection ? 'opacity-60' : 'opacity-100'}`}
                  >
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium text-stone-200">{status}</div>
                      <div className="mt-0.5 text-xs text-stone-500">Cases currently in this stage</div>
                    </div>
                    <span className="text-sm font-semibold text-stone-100">{count}</span>
                  </button>
                );
              })
            ) : (
              <CompactPanelEmptyState message="No case status changes in this range." />
            )}
          </CardContent>
        </Card>
      </div>
    </section>
  );
}

function AnalyticsMiniStat({
  label,
  value,
  hint,
  color,
}: {
  label: string;
  value: number;
  hint: string;
  color: string;
}) {
  return (
    <div className="rounded-md border border-[rgba(82,90,99,0.32)] bg-[rgba(18,22,26,0.44)] px-3 py-3">
      <div className="flex items-center gap-2 text-xs text-stone-500">
        <span className="h-0.5 w-4 rounded" style={{ backgroundColor: color }} />
        {label}
      </div>
      <div className="mt-2 text-xl font-semibold tracking-tight text-stone-100">{value}</div>
      <div className="mt-1 text-xs text-stone-500">{hint}</div>
    </div>
  );
}

function CompactPanelEmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-[rgba(82,90,99,0.32)] bg-[rgba(18,22,26,0.44)] px-4 py-6 text-center text-sm text-stone-500">
      {message}
    </div>
  );
}
