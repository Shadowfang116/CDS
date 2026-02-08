'use client';

import React, { useEffect, useState, useCallback, useMemo, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { getToken, getDashboard, DashboardResponse, NeedsAttentionItem, ActivityItem, listDashboardViews, createDashboardView, SavedView } from '@/lib/api';
// AppShell is now provided by root layout
import { Card, CardHeader, CardTitle, CardContent, MetricCard } from '@/components/ui/card';
import { Skeleton, SkeletonRow } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { EmptyState, EmptyIcon } from '@/components/ui/empty-state';
import { TrendLineChart, SeverityDonut, StatusBarChart, RadialMeter, chartPalette, SeverityLevel } from '@/components/dashboard/Charts';
import { DrilldownDrawer } from '@/components/dashboard/DrilldownDrawer';
import { SetPageChrome } from '@/components/layout/set-page-chrome';

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
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

// Get date portion from ISO string
function getDatePortion(dateString: string): string {
  return dateString.split('T')[0];
}

// Prettify action name
function prettifyAction(action: string): string {
  return action.replace(/\./g, ' · ').replace(/_/g, ' ');
}

export default function DashboardPage() {
  // #region agent log
  const renderCount = useRef(0);
  renderCount.current += 1;
  if (renderCount.current <= 20 || renderCount.current % 5 === 0) {
    fetch('http://127.0.0.1:7245/ingest/f5d810ee-7b87-46b0-a99a-93189a1118fe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'dashboard/page.tsx:48',message:'Dashboard render',data:{renderCount:renderCount.current},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
  }
  // #endregion
  const [mounted, setMounted] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [selectedDays, setSelectedDays] = useState(30);
  
  // Filter state
  const [selectedSeverity, setSelectedSeverity] = useState<SeverityLevel | null>(null);
  const [selectedStatus, setSelectedStatus] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  
  // Drawer state
  const [drawerOpen, setDrawerOpen] = useState(false);
  
  // Saved views state
  const [savedViews, setSavedViews] = useState<SavedView[]>([]);
  const [selectedViewId, setSelectedViewId] = useState<string | null>(null);
  const [showSaveView, setShowSaveView] = useState(false);
  const [newViewName, setNewViewName] = useState('');
  const [savingView, setSavingView] = useState(false);
  
  const router = useRouter();

  const fetchDashboard = useCallback(async (days: number) => {
    // #region agent log
    fetch('http://127.0.0.1:7245/ingest/f5d810ee-7b87-46b0-a99a-93189a1118fe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'dashboard/page.tsx:72',message:'fetchDashboard called',data:{days},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
    // #endregion
    setIsLoading(true);
    setError(null);
    try {
      const result = await getDashboard(days);
      // #region agent log
      fetch('http://127.0.0.1:7245/ingest/f5d810ee-7b87-46b0-a99a-93189a1118fe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'dashboard/page.tsx:77',message:'fetchDashboard success',data:{hasData:!!result},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
      // #endregion
      setData(result);
    } catch (e: any) {
      // #region agent log
      fetch('http://127.0.0.1:7245/ingest/f5d810ee-7b87-46b0-a99a-93189a1118fe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'dashboard/page.tsx:79',message:'fetchDashboard error',data:{error:e.message},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
      // #endregion
      setError(e.message || 'Failed to load dashboard');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    // #region agent log
    fetch('http://127.0.0.1:7245/ingest/f5d810ee-7b87-46b0-a99a-93189a1118fe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'dashboard/page.tsx:85',message:'Initial mount effect',data:{timestamp:Date.now()},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
    // #endregion
    setMounted(true);
    checkAuth();
    loadSavedViews();
  }, []);

  const loadSavedViews = async () => {
    // #region agent log
    fetch('http://127.0.0.1:7245/ingest/f5d810ee-7b87-46b0-a99a-93189a1118fe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'dashboard/page.tsx:91',message:'loadSavedViews called',data:{selectedViewId},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
    // #endregion
    try {
      const views = await listDashboardViews();
      setSavedViews(views);
      // Apply default view if exists
      const defaultView = views.find(v => v.is_default);
      // #region agent log
      fetch('http://127.0.0.1:7245/ingest/f5d810ee-7b87-46b0-a99a-93189a1118fe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'dashboard/page.tsx:97',message:'Checking default view',data:{hasDefaultView:!!defaultView,selectedViewId,willApply:!!(defaultView && !selectedViewId)},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
      // #endregion
      if (defaultView && !selectedViewId) {
        applyView(defaultView);
      }
    } catch (e) {
      console.error('Failed to load saved views:', e);
    }
  };

  const applyView = (view: SavedView) => {
    // #region agent log
    fetch('http://127.0.0.1:7245/ingest/f5d810ee-7b87-46b0-a99a-93189a1118fe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'dashboard/page.tsx:105',message:'applyView called',data:{viewId:view.id,days:view.config_json.days,currentSelectedDays:selectedDays},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
    // #endregion
    setSelectedViewId(view.id);
    setSelectedDays(view.config_json.days || 30);
    setSelectedSeverity(view.config_json.severity as SeverityLevel | null);
    setSelectedStatus(view.config_json.status || null);
    setSelectedDate(null); // Don't persist date filters
  };

  const handleSaveView = async () => {
    if (!newViewName.trim()) return;
    setSavingView(true);
    try {
      await createDashboardView({
        name: newViewName,
        config_json: {
          days: selectedDays,
          severity: selectedSeverity,
          status: selectedStatus,
        },
        is_default: false,
      });
      await loadSavedViews();
      setShowSaveView(false);
      setNewViewName('');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSavingView(false);
    }
  };

  useEffect(() => {
    // #region agent log
    fetch('http://127.0.0.1:7245/ingest/f5d810ee-7b87-46b0-a99a-93189a1118fe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'dashboard/page.tsx:136',message:'fetchDashboard effect triggered',data:{mounted,selectedDays,fetchDashboardChanged:true},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
    // #endregion
    if (mounted) {
      // #region agent log
      fetch('http://127.0.0.1:7245/ingest/f5d810ee-7b87-46b0-a99a-93189a1118fe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'dashboard/page.tsx:138',message:'Calling fetchDashboard',data:{selectedDays},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
      // #endregion
      fetchDashboard(selectedDays);
      // Clear filters when days range changes
      clearFilters();
    }
  }, [mounted, selectedDays, fetchDashboard]);

  const checkAuth = async () => {
    // #region agent log
    fetch('http://127.0.0.1:7245/ingest/f5d810ee-7b87-46b0-a99a-93189a1118fe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'dashboard/page.tsx:144',message:'checkAuth called',data:{},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
    // #endregion
    const token = await getToken();
    // #region agent log
    fetch('http://127.0.0.1:7245/ingest/f5d810ee-7b87-46b0-a99a-93189a1118fe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'dashboard/page.tsx:146',message:'checkAuth token check',data:{hasToken:!!token,willRedirect:!token},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
    // #endregion
    if (!token) {
      router.push('/');
      return;
    }
  };

  const handleDaysChange = (days: number) => {
    setSelectedDays(days);
  };

  const handleRetry = () => {
    fetchDashboard(selectedDays);
  };

  // Filter handlers with toggle behavior + open drawer
  const handleSeveritySelect = (severity: SeverityLevel) => {
    const newValue = selectedSeverity === severity ? null : severity;
    setSelectedSeverity(newValue);
    if (newValue) setDrawerOpen(true);
  };

  const handleStatusSelect = (status: string) => {
    const newValue = selectedStatus === status ? null : status;
    setSelectedStatus(newValue);
    if (newValue) setDrawerOpen(true);
  };

  const handleDateSelect = (date: string) => {
    const newValue = selectedDate === date ? null : date;
    setSelectedDate(newValue);
    if (newValue) setDrawerOpen(true);
  };

  const clearFilters = () => {
    setSelectedSeverity(null);
    setSelectedStatus(null);
    setSelectedDate(null);
  };

  const openDrawerWithFilters = () => {
    if (hasActiveFilters) {
      setDrawerOpen(true);
    }
  };

  const hasActiveFilters = selectedSeverity || selectedStatus || selectedDate;

  // Filtered work queue
  const filteredWorkQueue = useMemo(() => {
    if (!data) return [];
    
    let items = [...data.needs_attention];
    
    // Filter by severity
    if (selectedSeverity) {
      items = items.filter(item => {
        if (selectedSeverity === 'High') return item.open_high > 0;
        if (selectedSeverity === 'Medium') return item.open_medium > 0;
        if (selectedSeverity === 'Low') return item.open_low > 0;
        return true;
      });
    }
    
    // Filter by status
    if (selectedStatus) {
      items = items.filter(item => item.status === selectedStatus);
    }
    
    // Filter by date (updated_at)
    if (selectedDate) {
      items = items.filter(item => getDatePortion(item.updated_at) === selectedDate);
    }
    
    return items;
  }, [data, selectedSeverity, selectedStatus, selectedDate]);

  // Filtered activity
  const filteredActivity = useMemo(() => {
    if (!data) return [];
    
    let items = [...data.recent_activity];
    
    // Filter by date (created_at)
    if (selectedDate) {
      items = items.filter(item => getDatePortion(item.created_at) === selectedDate);
    }
    
    return items.slice(0, 15);
  }, [data, selectedDate]);

  if (!mounted) {
    return null;
  }

  return (
    <>
      <SetPageChrome title="Dashboard" breadcrumbs={[{ label: "Dashboard" }]} />
      {/* Page actions moved to AppShell in root layout */}
      <div className="flex items-center gap-2 mb-4 justify-end">
        <div className="flex items-center gap-2">
          {/* Saved Views Dropdown */}
          {savedViews.length > 0 && (
            <select
              value={selectedViewId || ''}
              onChange={(e) => {
                const view = savedViews.find(v => v.id === e.target.value);
                if (view) applyView(view);
                else {
                  setSelectedViewId(null);
                  clearFilters();
                }
              }}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
            >
              <option value="">All Activity</option>
              {savedViews.map(v => (
                <option key={v.id} value={v.id}>{v.name}{v.is_default ? ' ★' : ''}</option>
              ))}
            </select>
          )}
          <DaysSelector value={selectedDays} onChange={handleDaysChange} disabled={isLoading} />
          <Button variant="secondary" size="sm" onClick={() => setShowSaveView(true)} disabled={isLoading}>
            Save View
          </Button>
          <Button variant="secondary" size="sm" onClick={handleRetry} disabled={isLoading}>
            {isLoading ? 'Loading...' : 'Refresh'}
          </Button>
        </div>
      </div>

      {/* Error State */}
      {error && !isLoading && (
        <div className="mb-6 p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-rose-500/20 flex items-center justify-center">
                <ErrorIcon />
              </div>
              <div>
                <p className="text-sm font-medium text-rose-400">Failed to load dashboard</p>
                <p className="text-xs text-slate-400">{error}</p>
              </div>
            </div>
            <Button variant="outline" size="sm" onClick={handleRetry}>
              Retry
            </Button>
          </div>
        </div>
      )}

      {/* Active Filters Bar */}
      {hasActiveFilters && (
        <section className="mb-6">
          <div className="flex items-center gap-3 p-3 bg-slate-800/50 border border-slate-700/50 rounded-xl">
            <span className="text-sm text-slate-400">Active filters:</span>
            <div className="flex items-center gap-2 flex-wrap">
              {selectedSeverity && (
                <FilterBadge
                  label={`Severity: ${selectedSeverity}`}
                  color={
                    selectedSeverity === 'High' ? chartPalette.high :
                    selectedSeverity === 'Medium' ? chartPalette.medium :
                    chartPalette.low
                  }
                  onRemove={() => setSelectedSeverity(null)}
                />
              )}
              {selectedStatus && (
                <FilterBadge
                  label={`Status: ${selectedStatus}`}
                  color={chartPalette.primary}
                  onRemove={() => setSelectedStatus(null)}
                />
              )}
              {selectedDate && (
                <FilterBadge
                  label={`Date: ${formatDateDisplay(selectedDate)}`}
                  color={chartPalette.secondary}
                  onRemove={() => setSelectedDate(null)}
                />
              )}
            </div>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={openDrawerWithFilters}
              className="text-cyan-400 border-cyan-500/30 hover:bg-cyan-500/10"
            >
              View Details
            </Button>
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={clearFilters}
              className="text-slate-400 hover:text-slate-200"
            >
              Clear all
            </Button>
          </div>
        </section>
      )}

      {/* KPI Cards */}
      <section className="mb-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            title="Active Cases"
            value={data?.kpis.active_cases ?? ''}
            subtitle={data ? `In last ${data.range_days} days` : ''}
            loading={isLoading}
          />
          <MetricCard
            title="Open High Exceptions"
            value={data?.kpis.open_high_exceptions ?? ''}
            subtitle={data?.kpis.open_high_exceptions && data.kpis.open_high_exceptions > 0 ? 'Requires attention' : 'All clear'}
            loading={isLoading}
          />
          <MetricCard
            title="CP Completion"
            value={data ? `${data.kpis.cp_completion_pct}%` : ''}
            subtitle={data ? 'Conditions precedent' : ''}
            loading={isLoading}
          />
          <MetricCard
            title="Verification Completion"
            value={data ? `${data.kpis.verification_completion_pct}%` : ''}
            subtitle={data ? 'E-Stamp & Registry' : ''}
            loading={isLoading}
          />
        </div>
      </section>

      {/* Charts Row 1: Trend Line + Radial Meters */}
      <section className="mb-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Trend Line Chart */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Activity Trends</CardTitle>
              <p className="text-sm text-slate-500 mt-1">Cases created and exports generated · Click a point to filter by date</p>
            </CardHeader>
            <CardContent>
              <TrendLineChart
                data={data?.timeseries || []}
                loading={isLoading}
                selectedDate={selectedDate}
                onSelectDate={handleDateSelect}
              />
              {/* Legend */}
              <div className="flex justify-center gap-6 mt-4">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-0.5 rounded" style={{ backgroundColor: chartPalette.primary }} />
                  <span className="text-xs text-slate-400">Cases Created</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-0.5 rounded" style={{ backgroundColor: chartPalette.secondary }} />
                  <span className="text-xs text-slate-400">Exports Generated</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Radial Meters Stack */}
          <Card>
            <CardHeader>
              <CardTitle>Completion Rates</CardTitle>
              <p className="text-sm text-slate-500 mt-1">Progress overview</p>
            </CardHeader>
            <CardContent className="space-y-2">
              <RadialMeter
                value={data?.kpis.cp_completion_pct ?? 0}
                label="CP Completion"
                color={chartPalette.primary}
                loading={isLoading}
              />
              <Separator />
              <RadialMeter
                value={data?.kpis.verification_completion_pct ?? 0}
                label="Verification"
                color={chartPalette.secondary}
                loading={isLoading}
              />
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Charts Row 2: Status Bar + Severity Donut */}
      <section className="mb-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Status Bar Chart */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Cases by Status</CardTitle>
              <p className="text-sm text-slate-500 mt-1">Click a bar to filter work queue</p>
            </CardHeader>
            <CardContent>
              <StatusBarChart
                data={data?.cases_by_status || {}}
                loading={isLoading}
                selectedStatus={selectedStatus}
                onSelectStatus={handleStatusSelect}
              />
            </CardContent>
          </Card>

          {/* Severity Donut */}
          <Card>
            <CardHeader>
              <CardTitle>Open Exceptions</CardTitle>
              <p className="text-sm text-slate-500 mt-1">Click to filter by severity</p>
            </CardHeader>
            <CardContent>
              <SeverityDonut
                data={data?.exceptions_by_severity || { high: 0, medium: 0, low: 0 }}
                loading={isLoading}
                selectedSeverity={selectedSeverity}
                onSelectSeverity={handleSeveritySelect}
              />
            </CardContent>
          </Card>
        </div>
      </section>

      <Separator className="mb-6" />

      {/* Pending Verifications */}
      {data && data.kpis.pending_verifications > 0 && (
        <section className="mb-6">
          <Card className="bg-amber-500/5 border-amber-500/20">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-amber-400">Pending Verifications</CardTitle>
                <Badge variant="warning">{data.kpis.pending_verifications}</Badge>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-slate-400">
                {data.kpis.pending_verifications} verification{data.kpis.pending_verifications !== 1 ? 's' : ''} require attention. 
                Go to Cases → Verification tab to complete them.
              </p>
            </CardContent>
          </Card>
        </section>
      )}

      {/* Approvals Overlay (Phase 8) */}
      {data && (data.approvals_pending_count > 0 || data.ready_for_approval_count > 0) && (
        <section className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {/* Pending Approvals Card */}
          {data.approvals_pending_count > 0 && (
            <Card className="bg-amber-500/5 border-amber-500/20">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-amber-400 flex items-center gap-2">
                    <ApprovalIcon className="w-5 h-5" />
                    Approvals Pending
                  </CardTitle>
                  <Badge variant="warning">{data.approvals_pending_count}</Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {data.approvals_pending_preview.slice(0, 3).map((a) => (
                    <div key={a.id} className="flex items-center justify-between text-sm">
                      <span className="text-slate-300 truncate flex-1">{a.request_type_label}</span>
                      <span className="text-slate-500 text-xs ml-2">{formatRelativeTime(a.created_at)}</span>
                    </div>
                  ))}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full mt-3 border-amber-500/30 text-amber-400 hover:bg-amber-500/10"
                  onClick={() => router.push('/approvals')}
                >
                  Review Approvals
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Ready for Approval Card */}
          {data.ready_for_approval_count > 0 && (
            <Card className="bg-emerald-500/5 border-emerald-500/20">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-emerald-400 flex items-center gap-2">
                    <ReadyIcon className="w-5 h-5" />
                    Ready for Approval
                  </CardTitle>
                  <Badge variant="success">{data.ready_for_approval_count}</Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {data.ready_for_approval_list.slice(0, 3).map((c) => (
                    <button
                      key={c.case_id}
                      onClick={() => router.push(`/cases/${c.case_id}`)}
                      className="w-full flex items-center justify-between text-sm hover:bg-slate-800/50 rounded px-2 py-1 -mx-2"
                    >
                      <span className="text-slate-300 truncate flex-1 text-left">{c.title}</span>
                      <span className="text-emerald-400 text-xs ml-2">{c.cp_completion_pct}%</span>
                    </button>
                  ))}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full mt-3 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10"
                  onClick={() => {
                    setSelectedStatus('Ready for Approval');
                    setDrawerOpen(true);
                  }}
                >
                  View All Ready Cases
                </Button>
              </CardContent>
            </Card>
          )}
        </section>
      )}

      {/* Main Content Grid */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Work Queue - Left (2/3) */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Work Queue</CardTitle>
                <p className="text-sm text-slate-500 mt-1">
                  Cases requiring your attention
                  {hasActiveFilters && data && (
                    <span className="text-cyan-400 ml-2">
                      (showing {filteredWorkQueue.length} of {data.needs_attention.length})
                    </span>
                  )}
                </p>
              </div>
              {filteredWorkQueue.length > 0 && (
                <Badge variant="warning">{filteredWorkQueue.length} items</Badge>
              )}
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-slate-700/50">
                {isLoading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="p-4">
                      <SkeletonRow />
                    </div>
                  ))
                ) : filteredWorkQueue.length > 0 ? (
                  filteredWorkQueue.map((item) => (
                    <WorkQueueItem key={item.case_id} item={item} onClick={() => router.push(`/cases/${item.case_id}`)} />
                  ))
                ) : (
                  <div className="p-8">
                    <EmptyState
                      icon={hasActiveFilters ? <FilterIcon /> : <CheckIcon />}
                      title={hasActiveFilters ? "No matching cases" : "All caught up!"}
                      description={hasActiveFilters ? "Try adjusting your filters to see more results." : "No cases need immediate attention right now."}
                      action={hasActiveFilters ? (
                        <Button variant="outline" size="sm" onClick={clearFilters}>
                          Clear filters
                        </Button>
                      ) : undefined}
                    />
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Recent Activity - Right (1/3) */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
              <p className="text-sm text-slate-500 mt-1">
                Latest updates
                {selectedDate && (
                  <span className="text-cyan-400 ml-1">
                    on {formatDateDisplay(selectedDate)}
                  </span>
                )}
              </p>
              {(selectedSeverity || selectedStatus) && !selectedDate && (
                <p className="text-xs text-slate-600 mt-1">
                  Note: Severity and status filters apply to Work Queue only
                </p>
              )}
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-slate-700/50 max-h-[400px] overflow-y-auto">
                {isLoading ? (
                  Array.from({ length: 8 }).map((_, i) => (
                    <div key={i} className="px-4 py-3">
                      <div className="flex items-start gap-3">
                        <Skeleton className="h-8 w-8 rounded-full flex-shrink-0" />
                        <div className="flex-1 space-y-1.5">
                          <Skeleton className="h-3.5 w-full" />
                          <Skeleton className="h-3 w-2/3" />
                        </div>
                      </div>
                    </div>
                  ))
                ) : filteredActivity.length > 0 ? (
                  filteredActivity.map((item, i) => (
                    <ActivityItemRow key={`${item.created_at}-${i}`} item={item} />
                  ))
                ) : (
                  <div className="p-8">
                    <EmptyState
                      icon={selectedDate ? <FilterIcon /> : <EmptyIcon />}
                      title={selectedDate ? "No activity on this date" : "No activity yet"}
                      description={selectedDate ? "Try selecting a different date." : "Activity will appear here as you work on cases."}
                      action={selectedDate ? (
                        <Button variant="outline" size="sm" onClick={() => setSelectedDate(null)}>
                          Clear date filter
                        </Button>
                      ) : undefined}
                    />
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Save View Modal */}
      {showSaveView && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="fixed inset-0 bg-black/60" onClick={() => setShowSaveView(false)} />
          <div className="relative bg-slate-800 border border-slate-700 rounded-xl p-6 w-full max-w-md shadow-2xl">
            <h3 className="text-lg font-semibold text-slate-100 mb-4">Save Current View</h3>
            <p className="text-sm text-slate-400 mb-4">
              Days: {selectedDays}
              {selectedSeverity && ` • Severity: ${selectedSeverity}`}
              {selectedStatus && ` • Status: ${selectedStatus}`}
            </p>
            <input
              type="text"
              placeholder="View name..."
              value={newViewName}
              onChange={(e) => setNewViewName(e.target.value)}
              className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 mb-4"
              autoFocus
            />
            <div className="flex gap-2 justify-end">
              <Button variant="secondary" size="sm" onClick={() => setShowSaveView(false)}>
                Cancel
              </Button>
              <Button variant="primary" size="sm" onClick={handleSaveView} disabled={savingView || !newViewName.trim()}>
                {savingView ? 'Saving...' : 'Save'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Drilldown Drawer */}
      <DrilldownDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        days={selectedDays}
        filters={{
          severity: selectedSeverity,
          status: selectedStatus,
          date: selectedDate,
        }}
        onNavigateCase={(caseId) => {
          setDrawerOpen(false);
          router.push(`/cases/${caseId}`);
        }}
      />
    </>
  );
}

// Filter badge component
function FilterBadge({ label, color, onRemove }: { label: string; color: string; onRemove: () => void }) {
  return (
    <span 
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-700/50 border border-slate-600/50"
      style={{ borderColor: `${color}40` }}
    >
      <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
      <span className="text-slate-200">{label}</span>
      <button 
        onClick={onRemove}
        className="ml-0.5 text-slate-400 hover:text-slate-200 transition-colors"
      >
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </span>
  );
}

// Days selector component
function DaysSelector({ value, onChange, disabled }: { value: number; onChange: (days: number) => void; disabled: boolean }) {
  const options = [7, 30, 90];

  return (
    <div className="flex items-center gap-1 bg-slate-800 rounded-lg p-1">
      {options.map((days) => (
        <button
          key={days}
          onClick={() => onChange(days)}
          disabled={disabled}
          className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all ${
            value === days
              ? 'bg-cyan-500 text-slate-900'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700'
          } disabled:opacity-50`}
        >
          {days}d
        </button>
      ))}
    </div>
  );
}

// Work queue item component
function WorkQueueItem({ item, onClick }: { item: NeedsAttentionItem; onClick: () => void }) {
  const statusColors: Record<string, 'info' | 'warning' | 'success' | 'neutral'> = {
    New: 'info',
    Processing: 'info',
    Review: 'warning',
    'Pending Docs': 'warning',
    'Ready for Approval': 'success',
    Approved: 'success',
    Rejected: 'error' as any,
    Closed: 'neutral',
  };

  return (
    <div
      onClick={onClick}
      className="flex items-center gap-4 p-4 hover:bg-slate-700/30 transition-colors cursor-pointer"
    >
      <div className="w-10 h-10 rounded-full bg-slate-700/50 flex items-center justify-center flex-shrink-0">
        {item.open_high > 0 ? <ExceptionIcon /> : <VerificationIcon />}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-200 truncate">{item.title}</p>
        <div className="flex items-center gap-3 mt-1 text-xs text-slate-500">
          {item.open_high > 0 && (
            <span className="text-rose-400">High: {item.open_high}</span>
          )}
          {item.open_medium > 0 && (
            <span className="text-amber-400">Medium: {item.open_medium}</span>
          )}
          {item.open_low > 0 && (
            <span className="text-emerald-400">Low: {item.open_low}</span>
          )}
          {item.pending_verifications > 0 && (
            <span className="text-cyan-400">Pending: {item.pending_verifications}</span>
          )}
          <span>·</span>
          <span>{formatRelativeTime(item.updated_at)}</span>
        </div>
      </div>
      <Badge variant={statusColors[item.status] || 'neutral'}>{item.status}</Badge>
    </div>
  );
}

// Activity item component
function ActivityItemRow({ item }: { item: ActivityItem }) {
  const initials = item.actor_email
    ? item.actor_email.substring(0, 2).toUpperCase()
    : 'SYS';

  return (
    <div className="flex items-start gap-3 px-4 py-3 hover:bg-slate-700/20 transition-colors">
      <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center flex-shrink-0 text-xs font-medium text-slate-300">
        {initials}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-slate-300">
          <span className="font-medium capitalize">{prettifyAction(item.action)}</span>
        </p>
        <p className="text-xs text-slate-500 mt-0.5">
          {item.actor_email || 'System'} · {formatRelativeTime(item.created_at)}
        </p>
      </div>
    </div>
  );
}

// Icons
function ErrorIcon() {
  return (
    <svg className="w-5 h-5 text-rose-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg className="w-6 h-6 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}

function FilterIcon() {
  return (
    <svg className="w-6 h-6 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 3c2.755 0 5.455.232 8.083.678.533.09.917.556.917 1.096v1.044a2.25 2.25 0 01-.659 1.591l-5.432 5.432a2.25 2.25 0 00-.659 1.591v2.927a2.25 2.25 0 01-1.244 2.013L9.75 21v-6.568a2.25 2.25 0 00-.659-1.591L3.659 7.409A2.25 2.25 0 013 5.818V4.774c0-.54.384-1.006.917-1.096A48.32 48.32 0 0112 3z" />
    </svg>
  );
}

function ApprovalIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z" />
    </svg>
  );
}

function ReadyIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 01-1.043 3.296 3.745 3.745 0 01-3.296 1.043A3.745 3.745 0 0112 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 01-3.296-1.043 3.745 3.745 0 01-1.043-3.296A3.745 3.745 0 013 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 011.043-3.296 3.746 3.746 0 013.296-1.043A3.746 3.746 0 0112 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 013.296 1.043 3.746 3.746 0 011.043 3.296A3.745 3.745 0 0121 12z" />
    </svg>
  );
}

function ExceptionIcon() {
  return (
    <svg className="w-5 h-5 text-rose-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
    </svg>
  );
}

function VerificationIcon() {
  return (
    <svg className="w-5 h-5 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
    </svg>
  );
}
