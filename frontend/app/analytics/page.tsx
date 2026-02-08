'use client';

import { useState, useEffect } from 'react';
import { AppShell } from '@/components/app/AppShell';
import { Skeleton } from '@/components/ui/skeleton';
import { getDashboard } from '@/lib/api';

export default function AnalyticsPage() {
  const [metrics, setMetrics] = useState<any>(null);
  const [timeseries, setTimeseries] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);

  useEffect(() => {
    loadData();
  }, [days]);

  const loadData = async () => {
    setLoading(true);
    try {
      const dashboardData = await getDashboard(days);
      setMetrics(dashboardData.kpis);
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
  };

  return (
    <AppShell pageTitle="Analytics">
      <div className="p-6 space-y-6">
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
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
              <div className="text-sm text-slate-400">Cases Created</div>
              <div className="text-2xl font-bold text-slate-100 mt-2">
                {timeseries?.cases_created?.total || 0}
              </div>
            </div>
            <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
              <div className="text-sm text-slate-400">Exports Generated</div>
              <div className="text-2xl font-bold text-slate-100 mt-2">
                {timeseries?.exports_generated?.total || 0}
              </div>
            </div>
            <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
              <div className="text-sm text-slate-400">High Exceptions</div>
              <div className="text-2xl font-bold text-red-400 mt-2">
                {timeseries?.high_exceptions?.total || 0}
              </div>
            </div>
          </div>
        )}

        {/* Charts would go here - reusing dashboard components */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
          <p className="text-slate-400 text-sm">
            Detailed trend charts available in Dashboard view
          </p>
        </div>
      </div>
    </AppShell>
  );
}

