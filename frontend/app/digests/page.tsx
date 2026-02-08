'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { AppShell } from '@/components/app/AppShell';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/ui/empty-state';
import {
  listDigestSchedules,
  listDigestRuns,
  createDigestSchedule,
  updateDigestSchedule,
  deleteDigestSchedule,
  runDigestNow,
  getExportDownloadUrl,
  DigestSchedule,
  DigestRun,
  DigestScheduleCreate,
} from '@/lib/api';

// Days of week labels
const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

// Format hour for display
function formatHour(hour: number): string {
  const period = hour >= 12 ? 'PM' : 'AM';
  const displayHour = hour % 12 || 12;
  return `${displayHour}:00 ${period}`;
}

// Format relative time
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

export default function DigestsPage() {
  const router = useRouter();
  const [schedules, setSchedules] = useState<DigestSchedule[]>([]);
  const [runs, setRuns] = useState<DigestRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [runningScheduleId, setRunningScheduleId] = useState<string | null>(null);
  const [downloadingRunId, setDownloadingRunId] = useState<string | null>(null);

  // Form state
  const [formName, setFormName] = useState('');
  const [formCadence, setFormCadence] = useState<'daily' | 'weekly'>('weekly');
  const [formHour, setFormHour] = useState(9);
  const [formWeekday, setFormWeekday] = useState(0);
  const [formDays, setFormDays] = useState(30);
  const [formSubmitting, setFormSubmitting] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [schedulesData, runsData] = await Promise.all([
        listDigestSchedules(),
        listDigestRuns(50),
      ]);
      setSchedules(schedulesData);
      setRuns(runsData);
    } catch (e: any) {
      setError(e.message || 'Failed to load digests');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleCreateSchedule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formName.trim()) return;

    setFormSubmitting(true);
    try {
      const payload: DigestScheduleCreate = {
        name: formName.trim(),
        cadence: formCadence,
        hour_local: formHour,
        weekday: formCadence === 'weekly' ? formWeekday : undefined,
        is_enabled: true,
        filters_json: { days: formDays },
      };
      await createDigestSchedule(payload);
      setShowCreateForm(false);
      setFormName('');
      await fetchData();
    } catch (e: any) {
      setError(e.message || 'Failed to create schedule');
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleToggleEnabled = async (schedule: DigestSchedule) => {
    try {
      await updateDigestSchedule(schedule.id, { is_enabled: !schedule.is_enabled });
      await fetchData();
    } catch (e: any) {
      setError(e.message || 'Failed to update schedule');
    }
  };

  const handleDelete = async (scheduleId: string) => {
    if (!confirm('Delete this digest schedule? This cannot be undone.')) return;
    try {
      await deleteDigestSchedule(scheduleId);
      await fetchData();
    } catch (e: any) {
      setError(e.message || 'Failed to delete schedule');
    }
  };

  const handleRunNow = async (scheduleId: string) => {
    setRunningScheduleId(scheduleId);
    try {
      await runDigestNow(scheduleId);
      // Wait a moment then refresh runs
      setTimeout(() => fetchData(), 1000);
    } catch (e: any) {
      setError(e.message || 'Failed to trigger run');
    } finally {
      setRunningScheduleId(null);
    }
  };

  const handleDownloadRun = async (run: DigestRun) => {
    if (!run.output_export_id) return;
    setDownloadingRunId(run.id);
    try {
      const result = await getExportDownloadUrl(run.output_export_id);
      window.open(result.url, '_blank');
    } catch (e: any) {
      setError(e.message || 'Failed to get download URL');
    } finally {
      setDownloadingRunId(null);
    }
  };

  return (
    <AppShell
      pageTitle="Scheduled Digests"
      pageActions={
        <Button variant="primary" size="sm" onClick={() => setShowCreateForm(true)}>
          Create Schedule
        </Button>
      }
    >
      <div className="space-y-8">
        {error && (
          <div className="bg-rose-500/10 border border-rose-500/30 rounded-lg px-4 py-3 text-sm text-rose-400">
            {error}
            <button onClick={() => setError(null)} className="ml-4 underline">
              Dismiss
            </button>
          </div>
        )}

        {/* Create Form Modal */}
        {showCreateForm && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
            <div className="bg-slate-900 border border-slate-700 rounded-xl p-6 w-full max-w-md shadow-2xl">
              <h2 className="text-lg font-semibold text-slate-100 mb-4">Create Digest Schedule</h2>
              <form onSubmit={handleCreateSchedule} className="space-y-4">
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Name</label>
                  <input
                    type="text"
                    value={formName}
                    onChange={(e) => setFormName(e.target.value)}
                    placeholder="Weekly Risk Summary"
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
                    required
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Cadence</label>
                    <select
                      value={formCadence}
                      onChange={(e) => setFormCadence(e.target.value as 'daily' | 'weekly')}
                      className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
                    >
                      <option value="daily">Daily</option>
                      <option value="weekly">Weekly</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Time (UTC)</label>
                    <select
                      value={formHour}
                      onChange={(e) => setFormHour(Number(e.target.value))}
                      className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
                    >
                      {Array.from({ length: 24 }, (_, h) => (
                        <option key={h} value={h}>
                          {formatHour(h)}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                {formCadence === 'weekly' && (
                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Day of Week</label>
                    <select
                      value={formWeekday}
                      onChange={(e) => setFormWeekday(Number(e.target.value))}
                      className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
                    >
                      {WEEKDAYS.map((day, i) => (
                        <option key={i} value={i}>
                          {day}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Data Range</label>
                  <select
                    value={formDays}
                    onChange={(e) => setFormDays(Number(e.target.value))}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
                  >
                    <option value={7}>Last 7 days</option>
                    <option value={30}>Last 30 days</option>
                    <option value={90}>Last 90 days</option>
                  </select>
                </div>
                <div className="flex gap-3 pt-2">
                  <Button
                    type="button"
                    variant="outline"
                    className="flex-1"
                    onClick={() => setShowCreateForm(false)}
                    disabled={formSubmitting}
                  >
                    Cancel
                  </Button>
                  <Button type="submit" variant="primary" className="flex-1" disabled={formSubmitting}>
                    {formSubmitting ? 'Creating...' : 'Create'}
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Schedules Section */}
        <section>
          <h2 className="text-lg font-semibold text-slate-100 mb-4">Schedules</h2>
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="card p-4">
                  <div className="flex items-center gap-4">
                    <Skeleton className="h-6 w-48" />
                    <Skeleton className="h-5 w-20 rounded-full" />
                    <div className="flex-1" />
                    <Skeleton className="h-8 w-24" />
                  </div>
                </div>
              ))}
            </div>
          ) : schedules.length === 0 ? (
            <div className="card p-8">
              <EmptyState
                icon={<CalendarIcon />}
                title="No schedules yet"
                description="Create a digest schedule to automatically generate reports."
                action={
                  <Button variant="primary" size="sm" onClick={() => setShowCreateForm(true)}>
                    Create Schedule
                  </Button>
                }
              />
            </div>
          ) : (
            <div className="space-y-3">
              {schedules.map((schedule) => (
                <div key={schedule.id} className="card p-4">
                  <div className="flex items-center gap-4 flex-wrap">
                    <div className="flex-1 min-w-[200px]">
                      <p className="font-medium text-slate-200">{schedule.name}</p>
                      <p className="text-xs text-slate-500 mt-0.5">
                        {schedule.cadence === 'weekly'
                          ? `${WEEKDAYS[schedule.weekday || 0]} at ${formatHour(schedule.hour_local)}`
                          : `Daily at ${formatHour(schedule.hour_local)}`}
                        {' · '}Last {schedule.filters_json?.days || 30} days
                      </p>
                    </div>
                    <Badge variant={schedule.is_enabled ? 'success' : 'neutral'}>
                      {schedule.is_enabled ? 'Enabled' : 'Disabled'}
                    </Badge>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleToggleEnabled(schedule)}
                      >
                        {schedule.is_enabled ? 'Disable' : 'Enable'}
                      </Button>
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => handleRunNow(schedule.id)}
                        disabled={runningScheduleId === schedule.id}
                      >
                        {runningScheduleId === schedule.id ? 'Running...' : 'Run Now'}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(schedule.id)}
                        className="text-rose-400 hover:text-rose-300"
                      >
                        Delete
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Recent Runs Section */}
        <section>
          <h2 className="text-lg font-semibold text-slate-100 mb-4">Recent Runs</h2>
          {loading ? (
            <div className="space-y-2">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="card p-3">
                  <div className="flex items-center gap-4">
                    <Skeleton className="h-5 w-24 rounded-full" />
                    <Skeleton className="h-4 w-32" />
                    <div className="flex-1" />
                    <Skeleton className="h-8 w-20" />
                  </div>
                </div>
              ))}
            </div>
          ) : runs.length === 0 ? (
            <div className="card p-6 text-center text-slate-500 text-sm">
              No digest runs yet. Runs will appear here when schedules execute.
            </div>
          ) : (
            <div className="space-y-2">
              {runs.map((run) => {
                const schedule = schedules.find((s) => s.id === run.schedule_id);
                return (
                  <div key={run.id} className="card p-3">
                    <div className="flex items-center gap-4 flex-wrap">
                      <Badge
                        variant={
                          run.status === 'success'
                            ? 'success'
                            : run.status === 'failed'
                            ? 'error'
                            : 'warning'
                        }
                      >
                        {run.status}
                      </Badge>
                      <span className="text-sm text-slate-300">{schedule?.name || 'Unknown'}</span>
                      <span className="text-xs text-slate-500">{formatRelativeTime(run.run_at)}</span>
                      {run.error_message && (
                        <span className="text-xs text-rose-400 truncate max-w-[200px]">
                          {run.error_message}
                        </span>
                      )}
                      <div className="flex-1" />
                      {run.output_export_id && run.status === 'success' && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDownloadRun(run)}
                          disabled={downloadingRunId === run.id}
                        >
                          {downloadingRunId === run.id ? 'Loading...' : 'Download'}
                        </Button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </div>
    </AppShell>
  );
}

// Icons
function CalendarIcon() {
  return (
    <svg
      className="w-6 h-6 text-slate-500"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={1.5}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5"
      />
    </svg>
  );
}

