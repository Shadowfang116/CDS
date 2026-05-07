'use client';

import { useState, useEffect, useCallback } from 'react';
import { SetPageChrome } from '@/components/layout/set-page-chrome';
import { Skeleton } from '@/components/ui/skeleton';
import { getDashboard } from '@/lib/api';

export default function AnalyticsPage() {
  const [timeseries, setTimeseries] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const dashboardData = await getDashboard(days);
      // Extract timeseries totals
      const totals = dashboardData.timeseries.reduce((acc: any, entry: any) => {
        acc.cases_created = (acc.cases_created || 0) + entry.cases_created;
        acc.exports_generated = (acc.exports_generated || 0) + entry.exports_generated;
        acc.high_exceptions = (acc.high_exceptions || 0) + entry.high_exceptions_created;
        return acc;
      }, {});
      setTimeseries({ ...totals, entries: dashboardData.timeseries });
    } catch (e: any) {
      console.error('Failed to load analytics:', e);
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  return (
    <>
      <SetPageChrome
        title="Analytics"
        breadcrumbs={[{ label: 'Analytics' }]}
      />
      <div className="p-6 space-y-6" data-dashboard-reveal>
        {/* Time Range Selector */}
        <div className="flex gap-2">
          {[7, 30, 90].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`px-4 py-2 rounded-lg ${
                days === d
                  ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/50'
                  : 'bg-slate-800/50 text-slate-400 border border-slate-700'
              }`}
            >
              {d} days
            </button>
          ))}
        </div>

        {loading ? (
          <Skeleton className="h-64 w-full" />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4" data-dashboard-section>
            <div className="card p-4">
              <div className="text-sm" style={{ color: 'var(--text-muted)' }}>Cases Created</div>
              <div className="text-2xl font-bold mt-2" style={{ color: 'var(--text-primary)' }}>
                {timeseries?.cases_created?.total || 0}
              </div>
            </div>
            <div className="card p-4">
              <div className="text-sm" style={{ color: 'var(--text-muted)' }}>Exports Generated</div>
              <div className="text-2xl font-bold mt-2" style={{ color: 'var(--text-primary)' }}>
                {timeseries?.exports_generated?.total || 0}
              </div>
            </div>
            <div className="card p-4">
              <div className="text-sm" style={{ color: 'var(--text-muted)' }}>High Exceptions</div>
              <div className="text-2xl font-bold text-red-400 mt-2">
                {timeseries?.high_exceptions?.total || 0}
              </div>
            </div>
          </div>
        )}

        {/* Charts would go here - reusing dashboard components */}
        <div className="card p-4" data-dashboard-section>
          <p className="text-slate-400 text-sm">
            Detailed trend charts available in Dashboard view
          </p>
        </div>
      </div>
    </>
  );
}

