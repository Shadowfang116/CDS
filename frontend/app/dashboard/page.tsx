'use client';

import React, { Suspense, useEffect, useState, useCallback, useMemo, useRef } from 'react';
import dynamic from 'next/dynamic';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { motion, AnimatePresence, useReducedMotion } from 'motion/react';
import {
  getMe,
  getDashboardSummary,
  getDashboardAnalytics,
  DashboardSummaryResponse,
  DashboardAnalyticsResponse,
  NeedsAttentionItem,
  ActivityItem,
  listDashboardViews,
  createDashboardView,
  updateCaseAssignment,
  listAllCases,
  SavedView,
} from '@/lib/api';
// AppShell is now provided by root layout
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Skeleton, SkeletonRow } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { EmptyIcon } from '@/components/ui/empty-state';
import { useToast } from '@/components/ui/toast';
import { SetPageChrome } from '@/components/layout/set-page-chrome';
import { getCaseDetailPath } from '@/lib/routes';
import { useCurrentUser } from '@/hooks/useCurrentUser';
import type { SeverityLevel } from '@/components/dashboard/Charts';
import { PRODUCT_WALKTHROUGH_OPEN_EVENT } from '@/config/product-walkthrough';
import { ONBOARDING_OPEN_EVENT } from '@/lib/onboarding-steps';

const DashboardAnalyticsSection = dynamic(
  () =>
    import('@/components/dashboard/DashboardAnalyticsSection').then(
      (mod) => mod.DashboardAnalyticsSection
    ),
  {
    ssr: false,
    loading: () => <DashboardAnalyticsSkeleton />,
  }
);

const DrilldownDrawer = dynamic(
  () =>
    import('@/components/dashboard/DrilldownDrawer').then(
      (mod) => mod.DrilldownDrawer
    ),
  { ssr: false }
);

const dashboardFilterPalette = {
  high: '#bd5a56',
  medium: '#b8975f',
  low: '#6f8c73',
  primary: '#7a856f',
  secondary: '#948167',
};

const DEMO_CASE_TITLE = 'PILOT DEMO CASE';
const DEMO_CASE_FALLBACK_KEYWORD = 'demo';

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

// Aging / staleness classification — conservative thresholds for bank context
// Returns null for fresh items to avoid noise
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
function isEscalationRisk(item: NeedsAttentionItem): boolean {
  const aging = getAgingLevel(item.updated_at);
  const isStale = aging === 'stale' || aging === 'overdue';
  if (!isStale) return false;
  
  if (!item.assigned_to_user_id) return true;
  if (item.open_high > 0) return true;
  return false;
}

// Returns true if an approval request has been waiting too long (2+ days)
function isApprovalDelayed(createdAt: string): boolean {
  const diffMs = Date.now() - new Date(createdAt).getTime();
  return diffMs > 2 * 24 * 60 * 60 * 1000;
}

// Prettify action name
function prettifyAction(action: string): string {
  return action.replace(/\./g, " · ").replace(/_/g, " ");
}

// Short primary blocker reason — concise, direct
function getAttentionReason(item: NeedsAttentionItem): string {
  if (item.open_high > 0) {
    return `${item.open_high} unresolved high-severity exception${item.open_high === 1 ? '' : 's'}`;
  }
  if (item.pending_verifications > 0) {
    return `${item.pending_verifications} verification${item.pending_verifications === 1 ? '' : 's'} still pending`;
  }
  if (item.open_medium > 0 || item.open_low > 0) {
    const totalOpen = item.open_medium + item.open_low;
    return `${totalOpen} open exception${totalOpen === 1 ? '' : 's'} — closure or waiver required`;
  }
  return 'Active in review queue';
}

function getOwnerLabel(item: {
  assigned_to_name?: string | null;
  assigned_to_email?: string | null;
}): string {
  if (item.assigned_to_name) {
    return `Assigned to ${item.assigned_to_name}`;
  }

  if (item.assigned_to_email) {
    const mailbox = item.assigned_to_email.split('@')[0];
    return `Assigned to ${mailbox}`;
  }

  return 'Unassigned';
}

function matchesOwnerFilter(
  item: {
    assigned_to_user_id?: string | null;
    assigned_to_email?: string | null;
  },
  selectedOwner: 'All' | 'Mine' | 'Unassigned',
  currentUserEmail: string | null | undefined
): boolean {
  if (selectedOwner === 'Mine') {
    return Boolean(currentUserEmail) && item.assigned_to_email === currentUserEmail;
  }

  if (selectedOwner === 'Unassigned') {
    return !item.assigned_to_user_id;
  }

  return true;
}

function isStaleUnassigned(item: {
  updated_at: string;
  assigned_to_user_id?: string | null;
}): boolean {
  const aging = getAgingLevel(item.updated_at);
  const isStale = aging === 'stale' || aging === 'overdue';
  return isStale && !item.assigned_to_user_id;
}

function matchesEscalationFilter(
  item: {
    updated_at: string;
    assigned_to_user_id?: string | null;
  },
  selectedEscalation: 'stale_unassigned' | null
): boolean {
  if (!selectedEscalation) {
    return true;
  }

  if (selectedEscalation === 'stale_unassigned') {
    return isStaleUnassigned(item);
  }

  return true;
}

function getWorkItemOwnerCue(
  item: {
    assigned_to_user_id?: string | null;
    assigned_to_email?: string | null;
    assigned_to_name?: string | null;
  },
  currentUserEmail?: string | null
): string {
  if (!item.assigned_to_user_id) {
    return 'Needs assignment';
  }

  if (currentUserEmail && item.assigned_to_email === currentUserEmail) {
    return 'Assigned to you';
  }

  return getOwnerLabel(item);
}

// Urgency score for sorting — higher = more urgent
function getUrgencyScore(item: NeedsAttentionItem): number {
  return (
    item.open_high * 1000 +
    item.pending_verifications * 100 +
    item.open_medium * 10 +
    item.open_low
  );
}

// Build a human-readable activity narrative: "Actor did X · time ago"
function getActivityNarrative(item: ActivityItem): { line: string; hint: string | null } {
  const actor = item.actor_email
    ? item.actor_email.split('@')[0]
    : 'System';

  // Map known action codes to readable verbs
  const actionMap: Record<string, string> = {
    'exception.waived': 'waived an exception',
    'exception.resolved': 'resolved an exception',
    'exception.created': 'flagged a new exception',
    'evidence.linked': 'linked evidence',
    'evidence.attached': 'attached evidence',
    'verification.verified': 'marked verification complete',
    'verification.failed': 'marked verification failed',
    'verification.updated': 'updated verification',
    'case.created': 'created a new case',
    'case.updated': 'updated case details',
    'case.status_changed': 'changed case status',
    'approval.created': 'submitted an approval request',
    'approval.approved': 'approved a request',
    'approval.rejected': 'rejected a request',
    'document.uploaded': 'uploaded a document',
    'document.processed': 'processed a document',
    'cp.created': 'added a condition precedent',
    'cp.updated': 'updated condition precedent',
    'cp.completed': 'completed a condition precedent',
  };

  const verb = actionMap[item.action] ?? prettifyAction(item.action);
  const line = `${actor} ${verb}`;

  // Mark actions that indicate something requires follow-up
  const requiresReviewActions = new Set([
    'exception.created',
    'document.uploaded',
    'approval.created',
    'verification.failed',
  ]);

  const noteworthyActions = new Set([
    'exception.waived',
    'exception.resolved',
    'verification.verified',
    'approval.approved',
    'approval.rejected',
    'case.status_changed',
  ]);

  const hint = requiresReviewActions.has(item.action)
    ? 'Requires review'
    : noteworthyActions.has(item.action)
    ? 'Decision recorded'
    : null;

  return { line, hint };
}


export default function DashboardPage() {
  return (
    <Suspense fallback={<DashboardPageFallback />}>
      <DashboardPageContent />
    </Suspense>
  );
}

function DashboardPageContent() {
const [mounted, setMounted] = useState(false);
  const prefersReducedMotion = useReducedMotion();
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [summaryRefreshing, setSummaryRefreshing] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [summaryData, setSummaryData] = useState<DashboardSummaryResponse | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [analyticsRefreshing, setAnalyticsRefreshing] = useState(false);
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);
  const [analyticsData, setAnalyticsData] = useState<DashboardAnalyticsResponse | null>(null);
  // Track when summary data was last successfully loaded for data-freshness signal
  const [summaryLoadedAt, setSummaryLoadedAt] = useState<Date | null>(null);
  const [selectedDays, setSelectedDays] = useState(() => {
    const parsed = Number(searchParams.get('days') ?? '30');
    return parsed === 7 || parsed === 30 || parsed === 90 ? parsed : 30;
  });
  
  // Filter state
  const [selectedSeverity, setSelectedSeverity] = useState<SeverityLevel | null>(() => {
    const value = searchParams.get('severity');
    return value === 'High' || value === 'Medium' || value === 'Low' ? value : null;
  });
  const [selectedStatus, setSelectedStatus] = useState<string | null>(() => searchParams.get('status'));
  const [selectedDate, setSelectedDate] = useState<string | null>(() => searchParams.get('date'));
  const [selectedOwner, setSelectedOwner] = useState<'All' | 'Mine' | 'Unassigned'>(() => {
    const value = searchParams.get('owner');
    return value === 'Mine' || value === 'Unassigned' ? value : 'All';
  });
  const [selectedEscalation, setSelectedEscalation] = useState<'stale_unassigned' | null>(() =>
    searchParams.get('escalation') === 'stale_unassigned' ? 'stale_unassigned' : null
  );
  
  // Drawer state
  const [drawerOpen, setDrawerOpen] = useState(() => searchParams.get('drawer') === '1');
  const [drawerTab, setDrawerTab] = useState<'cases' | 'activity'>(() =>
    searchParams.get('drawerTab') === 'activity' ? 'activity' : 'cases'
  );
  
  // Saved views state
  const [savedViews, setSavedViews] = useState<SavedView[]>([]);
  const [selectedViewId, setSelectedViewId] = useState<string | null>(() => searchParams.get('view'));
  const [showSaveView, setShowSaveView] = useState(false);
  const [newViewName, setNewViewName] = useState('');
  const [savingView, setSavingView] = useState(false);
  const [assignmentPendingCaseId, setAssignmentPendingCaseId] = useState<string | null>(null);
  const [demoCaseId, setDemoCaseId] = useState<string | null>(null);
  const [demoCaseLookupLoading, setDemoCaseLookupLoading] = useState(false);
  
  const router = useRouter();
  const { toast } = useToast();
  const currentUser = useCurrentUser();
  const didInitRef = useRef(false);
  const summaryRef = useRef<DashboardSummaryResponse | null>(null);
  const analyticsRef = useRef<DashboardAnalyticsResponse | null>(null);
  const summaryRequestIdRef = useRef(0);
  const analyticsRequestIdRef = useRef(0);
  const refreshIntentRef = useRef(false);
  const dashboardUrlRef = useRef<string | null>(null);

  const fetchDashboardSummary = useCallback(async (days: number, force = false) => {
    const hasExistingData = summaryRef.current !== null;
    const requestId = ++summaryRequestIdRef.current;

    if (hasExistingData) {
      setSummaryRefreshing(true);
    } else {
      setSummaryLoading(true);
    }
    setSummaryError(null);

    try {
      const result = await getDashboardSummary(days, force);
      if (summaryRequestIdRef.current !== requestId) {
        return;
      }
      summaryRef.current = result;
      setSummaryData(result);
      setSummaryLoadedAt(new Date());
    } catch (e: any) {
      if (summaryRequestIdRef.current === requestId) {
        setSummaryError(e.message || 'Failed to load dashboard');
      }
    } finally {
      if (summaryRequestIdRef.current === requestId) {
        setSummaryLoading(false);
        setSummaryRefreshing(false);
      }
    }
  }, []);

  const fetchDashboardAnalytics = useCallback(async (days: number, force = false) => {
    const hasExistingData = analyticsRef.current !== null;
    const requestId = ++analyticsRequestIdRef.current;

    if (hasExistingData) {
      setAnalyticsRefreshing(true);
    } else {
      setAnalyticsLoading(true);
    }
    setAnalyticsError(null);

    try {
      const result = await getDashboardAnalytics(days, force);
      if (analyticsRequestIdRef.current !== requestId) {
        return;
      }
      analyticsRef.current = result;
      setAnalyticsData(result);
    } catch (e: any) {
      if (analyticsRequestIdRef.current === requestId) {
        setAnalyticsError(e.message || 'Failed to load analytics');
      }
    } finally {
      if (analyticsRequestIdRef.current === requestId) {
        setAnalyticsLoading(false);
        setAnalyticsRefreshing(false);
      }
    }
  }, []);

  const clearFilters = useCallback(() => {
    setSelectedSeverity(null);
    setSelectedStatus(null);
    setSelectedDate(null);
    setSelectedOwner('All');
    setSelectedEscalation(null);
  }, []);

  const applyView = useCallback((view: SavedView) => {
setSelectedViewId(view.id);
    setSelectedDays(view.config_json.days || 30);
    setSelectedSeverity(view.config_json.severity as SeverityLevel | null);
    setSelectedStatus(view.config_json.status || null);
    setSelectedOwner(
      view.config_json.owner === 'Mine' || view.config_json.owner === 'Unassigned'
        ? view.config_json.owner
        : 'All'
    );
    setSelectedEscalation(null);
    setSelectedDate(null); // Don't persist date filters
  }, []);

  const loadSavedViews = useCallback(async () => {
try {
      const views = await listDashboardViews();
      setSavedViews(views);
      const selectedView = selectedViewId ? views.find((v) => v.id === selectedViewId) : null;
      if (selectedView) {
        applyView(selectedView);
        return;
      }
      // Apply default view if exists
      const defaultView = views.find(v => v.is_default);
if (defaultView && !selectedViewId) {
        applyView(defaultView);
      }
    } catch (e) {
      console.error('Failed to load saved views:', e);
    }
  }, [applyView, selectedViewId]);

  const checkAuth = useCallback(async () => {
try {
      await getMe();
    } catch {
      router.push('/');
      return;
    }
  }, [router]);

  useEffect(() => {
    if (didInitRef.current) {
      return;
    }
    didInitRef.current = true;
setMounted(true);
    void checkAuth();
    void loadSavedViews();
  }, [checkAuth, loadSavedViews]);


  useEffect(() => {
    if (!mounted) {
      return;
    }

    let cancelled = false;
    setDemoCaseLookupLoading(true);

    void listAllCases({ sort: 'updated_at', order: 'desc', page_size: 100 })
      .then((cases) => {
        if (cancelled) {
          return;
        }

        const normalizedTitle = DEMO_CASE_TITLE.toLowerCase();
        const demoCase =
          cases.find((item) => item.title?.trim().toLowerCase() === normalizedTitle) ??
          cases.find((item) => item.title?.toLowerCase().includes(DEMO_CASE_FALLBACK_KEYWORD));
        setDemoCaseId(demoCase ? String(demoCase.id) : null);
      })
      .catch(() => {
        if (!cancelled) {
          setDemoCaseId(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setDemoCaseLookupLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [mounted]);

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
          owner: selectedOwner !== 'All' ? selectedOwner : null,
        },
        is_default: false,
      });
      await loadSavedViews();
      setShowSaveView(false);
      setNewViewName('');
      toast({
        title: 'Dashboard view saved.',
        description: 'The current filter set is available from the saved views list.',
        variant: 'success',
      });
    } catch (e: any) {
      setSummaryError(e.message);
      toast({
        title: 'Unable to save dashboard view.',
        description: e.message || 'Please try again.',
        variant: 'error',
      });
    } finally {
      setSavingView(false);
    }
  };

  useEffect(() => {
    if (!mounted) {
      return;
    }

    let cancelled = false;
    void fetchDashboardSummary(selectedDays).finally(() => {
      if (cancelled) {
        return;
      }
      window.setTimeout(() => {
        if (!cancelled) {
          void fetchDashboardAnalytics(selectedDays);
        }
      }, 0);
    });

    return () => {
      cancelled = true;
    };
  }, [mounted, selectedDays, fetchDashboardSummary, fetchDashboardAnalytics]);

  useEffect(() => {
    if (!mounted) {
      return;
    }

    const nextParams = new URLSearchParams();
    nextParams.set('days', String(selectedDays));

    if (selectedSeverity) {
      nextParams.set('severity', selectedSeverity);
    }
    if (selectedStatus) {
      nextParams.set('status', selectedStatus);
    }
    if (selectedDate) {
      nextParams.set('date', selectedDate);
    }
    if (selectedOwner !== 'All') {
      nextParams.set('owner', selectedOwner);
    }
    if (selectedEscalation) {
      nextParams.set('escalation', selectedEscalation);
    }
    if (selectedViewId) {
      nextParams.set('view', selectedViewId);
    }
    if (drawerOpen) {
      nextParams.set('drawer', '1');
      nextParams.set('drawerTab', drawerTab);
    }

    const nextSearch = nextParams.toString();
    const nextUrl = nextSearch ? `${pathname}?${nextSearch}` : pathname;

    if (dashboardUrlRef.current === nextUrl || nextUrl === `${pathname}?${searchParams.toString()}` || (!searchParams.toString() && nextUrl === pathname)) {
      dashboardUrlRef.current = nextUrl;
      return;
    }

    dashboardUrlRef.current = nextUrl;
    router.replace(nextUrl, { scroll: false });
  }, [
    mounted,
    pathname,
    router,
    searchParams,
    selectedDays,
    selectedSeverity,
    selectedStatus,
    selectedDate,
    selectedOwner,
    selectedEscalation,
    selectedViewId,
    drawerOpen,
    drawerTab,
  ]);

  const handleDaysChange = (days: number) => {
    setSelectedDays(days);
  };

  const handleOwnerFilterChange = useCallback(
    (owner: 'All' | 'Mine' | 'Unassigned') => {
      setSelectedOwner(owner);
      setSelectedEscalation(null);
      toast({
        title:
          owner === 'Mine'
            ? 'Showing cases assigned to you.'
            : owner === 'Unassigned'
            ? 'Showing unassigned cases.'
            : 'Showing all case ownership states.',
        variant: 'info',
      });
    },
    [toast]
  );

  const openEscalationView = useCallback(() => {
    setSelectedSeverity(null);
    setSelectedStatus(null);
    setSelectedDate(null);
    setSelectedOwner('Unassigned');
    setSelectedEscalation('stale_unassigned');
    setDrawerTab('cases');
    setDrawerOpen(true);
    toast({
      title: 'Showing stale unassigned cases.',
      description: 'Escalation view is focused on cases that need ownership now.',
      variant: 'info',
    });
  }, [toast]);

  const openProductWalkthrough = useCallback(() => {
    if (typeof window === 'undefined') {
      return;
    }

    window.dispatchEvent(new Event(PRODUCT_WALKTHROUGH_OPEN_EVENT));
  }, []);

  const openGuidedWalkthrough = useCallback(() => {
    if (typeof window === 'undefined') {
      return;
    }

    window.dispatchEvent(new Event(ONBOARDING_OPEN_EVENT));
  }, []);

  const handleOpenDemoCase = useCallback(() => {
    if (demoCaseId) {
      router.push(getCaseDetailPath(demoCaseId));
      return;
    }

    // Preload lookup may still be in-flight — do a real-time lookup as fallback
    setDemoCaseLookupLoading(true);
    void listAllCases({ sort: 'updated_at', order: 'desc', page_size: 100 })
      .then((cases) => {
        const normalizedTitle = DEMO_CASE_TITLE.toLowerCase();
        const found =
          cases.find((item) => item.title?.trim().toLowerCase() === normalizedTitle) ??
          cases.find((item) => item.title?.toLowerCase().includes(DEMO_CASE_FALLBACK_KEYWORD));
        if (found) {
          router.push(getCaseDetailPath(String(found.id)));
        } else {
          toast({
            title: 'Demo matter not currently available.',
            description: 'Open the matters list or reset the demo matter from the Admin workspace.',
            variant: 'info',
          });
          router.push('/dashboard/cases');
        }
      })
      .catch(() => {
        toast({
          title: 'Demo matter not currently available.',
          description: 'Open the matters list or reset the demo matter from the Admin workspace.',
          variant: 'info',
        });
        router.push('/dashboard/cases');
      })
      .finally(() => {
        setDemoCaseLookupLoading(false);
      });
  }, [demoCaseId, router, toast]);

  const handleRetry = () => {
    refreshIntentRef.current = true;
    void fetchDashboardSummary(selectedDays, true);
    window.setTimeout(() => {
      void fetchDashboardAnalytics(selectedDays, true);
    }, 0);
  };

  const handleAssignmentAction = useCallback(
    async (caseId: string, action: 'claim' | 'unassign') => {
      setAssignmentPendingCaseId(caseId);
      try {
        await updateCaseAssignment(caseId, action);
        toast({
          title: action === 'claim' ? 'Case assigned to you.' : 'Case assignment cleared.',
          description:
            action === 'claim'
              ? 'Ownership has been recorded on the case.'
              : 'The case is now available for reassignment.',
          variant: 'success',
        });
        await fetchDashboardSummary(selectedDays, true);
      } catch (error: any) {
        toast({
          title: action === 'claim' ? 'Unable to assign case.' : 'Unable to clear assignment.',
          description: error?.message || 'Please retry.',
          variant: 'error',
        });
      } finally {
        setAssignmentPendingCaseId(null);
      }
    },
    [fetchDashboardSummary, selectedDays, toast]
  );

  useEffect(() => {
    if (!refreshIntentRef.current) {
      return;
    }

    const stillRefreshing = summaryRefreshing || analyticsRefreshing || summaryLoading || analyticsLoading;
    if (stillRefreshing) {
      return;
    }

    refreshIntentRef.current = false;

    if (summaryError || analyticsError) {
      toast({
        title: 'Dashboard refresh could not be completed.',
        description: summaryError || analyticsError || 'Please retry.',
        variant: 'error',
      });
      return;
    }

    toast({
      title: 'Dashboard refreshed.',
      description: 'Summary and analytics data are up to date.',
      variant: 'success',
    });
  }, [
    analyticsError,
    analyticsLoading,
    analyticsRefreshing,
    summaryError,
    summaryLoading,
    summaryRefreshing,
    toast,
  ]);

  // Filter handlers with toggle behavior + open drawer
  const handleSeveritySelect = (severity: SeverityLevel) => {
    const newValue = selectedSeverity === severity ? null : severity;
    setSelectedSeverity(newValue);
    if (newValue) {
      setDrawerTab('cases');
      setDrawerOpen(true);
    }
  };

  const handleStatusSelect = (status: string) => {
    const newValue = selectedStatus === status ? null : status;
    setSelectedStatus(newValue);
    if (newValue) {
      setDrawerTab('cases');
      setDrawerOpen(true);
    }
  };

  const handleDateSelect = (date: string) => {
    const newValue = selectedDate === date ? null : date;
    setSelectedDate(newValue);
    if (newValue) {
      setDrawerTab('activity');
      setDrawerOpen(true);
    }
  };

  const openDrawerWithFilters = () => {
    if (hasActiveFilters) {
      if (selectedEscalation) {
        setDrawerTab('cases');
      } else if (!selectedSeverity && !selectedStatus && selectedDate) {
        setDrawerTab('activity');
      } else {
        setDrawerTab('cases');
      }
      setDrawerOpen(true);
    }
  };

  const hasActiveFilters =
    selectedSeverity || selectedStatus || selectedDate || selectedOwner !== 'All' || selectedEscalation;

  // Filtered work queue — sorted by urgency score (highest first)
  const filteredWorkQueue = useMemo(() => {
    if (!summaryData) return [];
    
    let items = [...summaryData.needs_attention];
    
    // Filter by owner
    items = items.filter((item) => matchesOwnerFilter(item, selectedOwner, currentUser?.email));

    // Filter by escalation slice
    items = items.filter((item) => matchesEscalationFilter(item, selectedEscalation));
    
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
    
    // Sort by urgency: high exceptions > pending verifications > medium/low
    items.sort((a, b) => getUrgencyScore(b) - getUrgencyScore(a));
    
    return items;
  }, [summaryData, selectedSeverity, selectedStatus, selectedDate, selectedOwner, selectedEscalation, currentUser?.email]);

  // Filtered activity
  const filteredActivity = useMemo(() => {
    if (!summaryData) return [];
    
    let items = [...summaryData.recent_activity];
    
    // Filter by date (created_at)
    if (selectedDate) {
      items = items.filter(item => getDatePortion(item.created_at) === selectedDate);
    }
    
    return items;
  }, [summaryData, selectedDate]);

  const queuePreview = useMemo(() => filteredWorkQueue.slice(0, 8), [filteredWorkQueue]);
  const activityPreview = useMemo(() => filteredActivity.slice(0, 6), [filteredActivity]);
  const currentRole = currentUser?.role ?? 'Viewer';
  const summaryUnavailable = Boolean(summaryError && !summaryData);

  const dashboardCopy = useMemo(() => {
    switch (currentRole) {
      case 'Reviewer':
        return {
          heroDescription: 'Focus on cases that need review, what remains blocked, and the latest case movement across the selected window.',
          queueTitle: 'What needs review now',
          queueDescription: 'Top priority cases requiring reviewer action.',
          approvalsTitle: 'What can move forward',
          approvalsDescription: 'Cases nearing approver review and decisions still waiting.',
          activityTitle: 'What changed recently',
          activityDescription: 'Latest reviewer-relevant case and approval updates.',
        };
      case 'Approver':
        return {
          heroDescription: 'Focus on what is ready for decision, what remains blocked, and the latest movement across the selected window.',
          queueTitle: 'What still blocks approval',
          queueDescription: 'Cases with open issues that still need closure before decision.',
          approvalsTitle: 'What is ready for decision',
          approvalsDescription: 'Pending approvals, ready cases, and remaining verification pressure.',
          activityTitle: 'Recent approval activity',
          activityDescription: 'Latest changes that affect approval flow.',
        };
      case 'Admin':
        return {
          heroDescription: 'Focus on operational backlog, processing pressure, and the latest platform activity across the selected window.',
          queueTitle: 'Operational queue',
          queueDescription: 'Cases creating the most near-term review or processing pressure.',
          approvalsTitle: 'Approval readiness',
          approvalsDescription: 'Decision pressure and verification load across the pipeline.',
          activityTitle: 'Operational activity',
          activityDescription: 'Recent case, approval, and system actions in this range.',
        };
      default:
        return {
          heroDescription: 'What needs action now, what is blocked, and what changed recently across the selected monitoring window.',
          queueTitle: 'Cases requiring attention',
          queueDescription: 'Top cases currently requiring operational attention.',
          approvalsTitle: 'Approval readiness',
          approvalsDescription: 'Pending approvals, ready cases, and verification pressure.',
          activityTitle: 'Recent activity',
          activityDescription: 'Latest updates across case, approval, and review workflows.',
        };
    }
  }, [currentRole]);

  const casesRequiringAttention = summaryData ? summaryData.needs_attention.length : undefined;
  const processingCount = summaryData?.processing_cases_count;
  const primaryLoading = summaryLoading && !summaryData;
  const isRefreshing = summaryRefreshing || analyticsRefreshing;
  const openHighExceptions = summaryData?.kpis.open_high_exceptions;

  const moveForwardPreview = useMemo(() => {
    if (!summaryData) {
      return [];
    }

    // READY: all conditions met, can move immediately
    const readyCases = summaryData.ready_for_approval_list.slice(0, 3).map((item) => ({
      id: `ready-${item.case_id}`,
      title: item.title,
      readinessState: 'ready' as const,
      supportingLabel: 'Ready for approval',
      supportingDetail:
        item.cp_completion_pct >= 100
          ? 'All conditions precedent complete.'
          : `${item.cp_completion_pct}% of conditions precedent complete.`,
      updatedAt: item.updated_at,
      cta: 'Open case',
      onClick: () => router.push(getCaseDetailPath(item.case_id)),
      tone: 'success' as const,
      assigned_to_user_id: item.assigned_to_user_id ?? null,
      assigned_to_email: item.assigned_to_email ?? null,
      assigned_to_name: item.assigned_to_name ?? null,
      ownerLabel: !item.assigned_to_user_id
        ? 'Ready but unassigned'
        : currentUser?.email && item.assigned_to_email === currentUser.email
        ? 'Assigned to you · ready to advance'
        : `${getOwnerLabel(item)} · ready to advance`,
    }));

    // PENDING DECISION: approval request submitted, awaiting approver action
    const approvalRequests = summaryData.approvals_pending_preview.slice(0, 2).map((request) => ({
      id: `approval-${request.id}`,
      title: request.case_title,
      readinessState: 'pending' as const,
      supportingLabel: 'With approver',
      supportingDetail: `${request.request_type_label} awaiting decision.`,
      updatedAt: request.created_at,
      cta: 'Review approvals',
      onClick: () => router.push('/approvals'),
      tone: 'warning' as const,
      assigned_to_user_id: request.assigned_to_user_id ?? null,
      assigned_to_email: request.assigned_to_email ?? null,
      assigned_to_name: request.assigned_to_name ?? null,
      ownerLabel: request.assigned_to_user_id
        ? currentUser?.email && request.assigned_to_email === currentUser.email
          ? 'With approver · assigned to you'
          : 'With approver · reviewer-owned'
        : 'With approver · reviewer owner missing',
    }));

    // NEARLY READY: no high exceptions, but still has pending verifications
    const nearlyReadyCases = summaryData.needs_attention
      .filter((item) => item.open_high === 0 && item.pending_verifications > 0)
      .slice(0, 2)
      .map((item) => ({
        id: `nearly-${item.case_id}`,
        title: item.title,
        readinessState: 'nearlyReady' as const,
        supportingLabel: 'Nearly ready',
        supportingDetail: `${item.pending_verifications} verification${item.pending_verifications === 1 ? '' : 's'} still open`,
        updatedAt: item.updated_at,
        cta: 'Open case',
        onClick: () => router.push(getCaseDetailPath(item.case_id)),
      tone: 'warning' as const,
      assigned_to_user_id: item.assigned_to_user_id ?? null,
      assigned_to_email: item.assigned_to_email ?? null,
      assigned_to_name: item.assigned_to_name ?? null,
      ownerLabel: !item.assigned_to_user_id
        ? 'Needs assignment'
        : currentUser?.email && item.assigned_to_email === currentUser.email
        ? 'Assigned to you'
        : getOwnerLabel(item),
    }));

    // Compose: ready → pending decision → nearly ready, cap at 6
    return [...readyCases, ...approvalRequests, ...nearlyReadyCases]
      .filter((item) => matchesOwnerFilter(item, selectedOwner, currentUser?.email))
      .slice(0, 6);
  }, [router, summaryData, selectedOwner, currentUser?.email]);

  const ownershipScopedApprovalMetrics = useMemo(() => {
    if (!summaryData) {
      return {
        pendingApprovals: 0,
        readyCases: 0,
        openVerifications: 0,
      };
    }

    return {
      pendingApprovals: summaryData.approvals_pending_preview.filter((item) =>
        matchesOwnerFilter(item, selectedOwner, currentUser?.email)
      ).length,
      readyCases: summaryData.ready_for_approval_list.filter((item) =>
        matchesOwnerFilter(item, selectedOwner, currentUser?.email)
      ).length,
      openVerifications: summaryData.needs_attention
        .filter((item) => item.open_high === 0 && item.pending_verifications > 0)
        .filter((item) => matchesOwnerFilter(item, selectedOwner, currentUser?.email))
        .reduce((total, item) => total + item.pending_verifications, 0),
    };
  }, [summaryData, selectedOwner, currentUser?.email]);

  const managementCounters = useMemo(() => {
    if (!summaryData) {
      return {
        assignedToMe: 0,
        unassignedStale: 0,
        readyButUnassigned: 0,
        withApprover: 0,
        delayedApprovals: 0,
      };
    }

    const assignedCaseIds = new Set<string>();
    const currentEmail = currentUser?.email ?? null;

    if (currentEmail) {
      for (const item of summaryData.needs_attention) {
        if (item.assigned_to_email === currentEmail) {
          assignedCaseIds.add(item.case_id);
        }
      }
      for (const item of summaryData.ready_for_approval_list) {
        if (item.assigned_to_email === currentEmail) {
          assignedCaseIds.add(item.case_id);
        }
      }
      for (const item of summaryData.approvals_pending_preview) {
        if (item.assigned_to_email === currentEmail) {
          assignedCaseIds.add(item.case_id);
        }
      }
    }

    const delayedApprovals = summaryData.approvals_pending_preview.filter((item) =>
      isApprovalDelayed(item.created_at)
    ).length;

    return {
      assignedToMe: assignedCaseIds.size,
      unassignedStale: summaryData.needs_attention.filter((item) => isStaleUnassigned(item)).length,
      readyButUnassigned: summaryData.ready_for_approval_list.filter((item) => !item.assigned_to_user_id).length,
      withApprover: summaryData.approvals_pending_preview.length,
      delayedApprovals,
    };
  }, [summaryData, currentUser?.email]);

  const escalationPreview = useMemo(() => {
    if (!summaryData) {
      return [];
    }

    return summaryData.needs_attention
      .filter((item) => matchesOwnerFilter(item, selectedOwner, currentUser?.email))
      .filter((item) => isStaleUnassigned(item))
      .sort((a, b) => getUrgencyScore(b) - getUrgencyScore(a))
      .slice(0, 3);
  }, [currentUser?.email, selectedOwner, summaryData]);

  const nextStepSummary = useMemo(() => {
    if (primaryLoading) {
      return 'Loading current review queue and activity status.';
    }

    if (summaryUnavailable) {
      return 'Primary dashboard data is unavailable. Retry to restore queue, readiness, and activity previews.';
    }

    if (queuePreview.length > 0) {
      return `${queuePreview.length} case${queuePreview.length === 1 ? '' : 's'} need review next. Open the queue to continue.`;
    }

    if (escalationPreview.length > 0) {
      return `${escalationPreview.length} stale unassigned case${escalationPreview.length === 1 ? '' : 's'} require escalation or claim.`;
    }

    if (moveForwardPreview.length > 0) {
      return `${moveForwardPreview.length} item${moveForwardPreview.length === 1 ? '' : 's'} can move forward. Review approvals or open the next case.`;
    }

    return 'No immediate backlog in this window. Monitor recent activity or open all cases.';
  }, [escalationPreview.length, moveForwardPreview.length, primaryLoading, queuePreview.length, summaryUnavailable]);

  if (!mounted) {
    return null;
  }

  return (
    <>
      <SetPageChrome title="Dashboard" breadcrumbs={[{ label: "Dashboard" }]} />
      <section data-dashboard-section data-tour="dashboard" className="dashboard-surface dashboard-summary-shell relative mb-6 overflow-hidden rounded-[1.75rem]">
        <div className="dashboard-summary-orb dashboard-summary-orb-a" />
        <div className="dashboard-summary-orb dashboard-summary-orb-b" />
        <div className="absolute inset-x-0 top-0 h-px bg-[linear-gradient(90deg,transparent,rgba(204,214,190,0.45),transparent)]" />
        <div className="relative grid gap-6 px-5 py-5 lg:px-6 xl:grid-cols-[minmax(0,1.55fr)_minmax(320px,0.95fr)]">
          <div className="space-y-5">
            <div className="space-y-3" data-dashboard-reveal>
              <div className="max-w-3xl">
                <div className="text-lg font-semibold tracking-tight text-stone-100">
                  Case Diligence Suite
                </div>
                <p className="mt-1 max-w-2xl text-sm leading-6 text-stone-500">
                  {nextStepSummary}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-stone-500">
                {summaryLoadedAt && !isRefreshing ? (
                  <span>Queue data loaded {formatRelativeTime(summaryLoadedAt.toISOString())}</span>
                ) : null}
                {summaryError && summaryData ? (
                  <span className="text-[rgb(219,156,153)]">Partial data returned on the last refresh.</span>
                ) : null}
                {isRefreshing ? <span className="text-stone-300">Refreshing dashboard.</span> : null}
              </div>
            </div>

            <AnimatePresence>
            {hasActiveFilters && (
              <motion.div
                key="filter-strip"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.18, ease: 'easeInOut' }}
                className="overflow-hidden"
              >
                <div className="dashboard-surface-muted flex flex-wrap items-center gap-2 rounded-[1.15rem] px-3 py-2.5" data-dashboard-reveal>
                <span className="text-xs font-medium text-stone-500">Filtered view</span>
                {selectedSeverity && (
                  <FilterBadge
                    label={`Severity • ${selectedSeverity}`}
                    color={
                      selectedSeverity === 'High' ? dashboardFilterPalette.high :
                      selectedSeverity === 'Medium' ? dashboardFilterPalette.medium :
                      dashboardFilterPalette.low
                    }
                    onRemove={() => setSelectedSeverity(null)}
                  />
                )}
                {selectedStatus && (
                  <FilterBadge
                    label={`Status • ${selectedStatus}`}
                    color={dashboardFilterPalette.primary}
                    onRemove={() => setSelectedStatus(null)}
                  />
                )}
                {selectedDate && (
                  <FilterBadge
                    label={`Date • ${formatDateDisplay(selectedDate)}`}
                    color={dashboardFilterPalette.secondary}
                    onRemove={() => setSelectedDate(null)}
                  />
                )}
                {selectedOwner !== 'All' && (
                  <FilterBadge
                    label={`Owner • ${selectedOwner === 'Mine' ? 'My cases' : 'Unassigned'}`}
                    color={dashboardFilterPalette.primary}
                    onRemove={() => setSelectedOwner('All')}
                  />
                )}
                {selectedEscalation && (
                  <FilterBadge
                    label="Escalation • Stale + unassigned"
                    color={dashboardFilterPalette.high}
                    onRemove={() => setSelectedEscalation(null)}
                  />
                )}
                <div className="ml-auto flex items-center gap-2">
                  <Button variant="outline" size="sm" onClick={openDrawerWithFilters}>
                    View details
                  </Button>
                  <Button variant="ghost" size="sm" onClick={clearFilters}>
                    Clear
                  </Button>
                </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

            <motion.div
              initial={prefersReducedMotion ? { opacity: 0 } : { opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, ease: [0.25, 0.1, 0.25, 1] }}
              className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"
              data-dashboard-reveal
            >
              <DashboardKpi
                label="Cases Requiring Attention"
                value={summaryUnavailable ? '—' : casesRequiringAttention}
                sublabel={
                  summaryUnavailable
                    ? 'Summary unavailable'
                    : casesRequiringAttention
                      ? 'Needs reviewer attention'
                      : 'No active queue'
                }
                tone="warning"
                loading={primaryLoading}
              />
              <DashboardKpi
                label="Open High Exceptions"
                value={summaryUnavailable ? '—' : openHighExceptions}
                sublabel={
                  summaryUnavailable
                    ? 'Summary unavailable'
                    : openHighExceptions
                      ? 'Requires closure or waiver'
                      : 'No critical blockers'
                }
                tone="danger"
                loading={primaryLoading}
              />
              <DashboardKpi
                label="Documents Processing"
                value={summaryUnavailable ? '—' : processingCount}
                sublabel={
                  summaryUnavailable
                    ? 'Summary unavailable'
                    : processingCount
                      ? (summaryData?.oldest_processing_case_updated_at
                          ? `Oldest: ${formatRelativeTime(summaryData.oldest_processing_case_updated_at)}`
                          : 'Extraction or review running')
                      : 'No processing backlog'
                }
                tone="warning"
                loading={primaryLoading}
              />
              <DashboardKpi
                label="Ready for Approval"
                value={summaryUnavailable ? '—' : summaryData?.ready_for_approval_count}
                sublabel={
                  summaryUnavailable
                    ? 'Summary unavailable'
                    : summaryData?.ready_for_approval_count
                      ? 'Cases can move forward'
                      : 'None currently ready'
                }
                tone="success"
                loading={primaryLoading}
              />
            </motion.div>

            <div className="flex flex-wrap gap-3">
              <Button size="sm" onClick={openGuidedWalkthrough}>
                Guided Walkthrough
              </Button>
              <Button size="sm" variant="outline" onClick={openProductWalkthrough}>
                Product Tour
              </Button>
              <Button variant="ghost" size="sm" data-tour="export" onClick={handleOpenDemoCase} loading={demoCaseLookupLoading}>
                Open Demo Case
              </Button>
            </div>
          </div>

          <div className="space-y-4" data-dashboard-reveal>
            <div className="dashboard-surface-muted rounded-[1.35rem] p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-sm font-medium text-stone-200">Current slice</div>
                  <p className="mt-1 text-xs leading-5 text-stone-500">
                    Save a view, shift the monitoring window, or refresh the queue without leaving the page.
                  </p>
                </div>
                <Button variant="outline" size="sm" onClick={handleRetry} disabled={isRefreshing} loading={isRefreshing}>
                  {isRefreshing ? 'Refreshing' : 'Refresh'}
                </Button>
              </div>
              <div className="mt-4 space-y-3">
                {savedViews.length > 0 && (
                  <select
                    value={selectedViewId || ''}
                    onChange={(e) => {
                      const view = savedViews.find((v) => v.id === e.target.value);
                      if (view) applyView(view);
                      else {
                        setSelectedViewId(null);
                        clearFilters();
                      }
                    }}
                    className="h-10 w-full rounded-xl border border-[rgba(92,103,114,0.42)] bg-[rgba(16,20,24,0.84)] px-3 text-sm text-stone-200 shadow-[inset_0_1px_0_rgba(255,255,255,0.02)] focus:outline-none focus:ring-2 focus:ring-[rgba(154,165,137,0.72)]"
                  >
                    <option value="">All activity</option>
                    {savedViews.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.name}
                        {v.is_default ? ' *' : ''}
                      </option>
                    ))}
                  </select>
                )}
                <div className="flex flex-wrap items-center gap-2">
                  <DaysSelector value={selectedDays} onChange={handleDaysChange} disabled={summaryLoading || summaryRefreshing} />
                  <Button variant="secondary" size="sm" onClick={() => setShowSaveView(true)} disabled={summaryLoading || summaryRefreshing}>
                    Save view
                  </Button>
                </div>
              </div>
            </div>

            {!summaryUnavailable && !primaryLoading ? (
              <div className="dashboard-surface-muted rounded-[1.35rem] p-4">
                <div>
                  <div className="text-sm font-medium text-stone-200">Ownership and handoff</div>
                  <p className="mt-1 text-xs leading-5 text-stone-500">
                    Assignment pressure, missing owners, and approval items waiting for action.
                  </p>
                </div>
                <div className="mt-4 grid gap-2 sm:grid-cols-2">
                  <ManagementCounter
                    label="Assigned to me"
                    value={managementCounters.assignedToMe}
                    detail={managementCounters.assignedToMe ? 'Owned by you' : 'Nothing assigned'}
                    onClick={currentUser?.email ? () => handleOwnerFilterChange('Mine') : undefined}
                  />
                  <ManagementCounter
                    label="Unassigned stale"
                    value={managementCounters.unassignedStale}
                    detail={managementCounters.unassignedStale ? 'Escalate or claim now' : 'No stale ownership gap'}
                    tone={managementCounters.unassignedStale > 0 ? 'danger' : 'neutral'}
                    onClick={managementCounters.unassignedStale > 0 ? openEscalationView : undefined}
                  />
                  <ManagementCounter
                    label="Ready but unassigned"
                    value={managementCounters.readyButUnassigned}
                    detail={managementCounters.readyButUnassigned ? 'Handoff owner missing' : 'Owner coverage clear'}
                    tone={managementCounters.readyButUnassigned > 0 ? 'warning' : 'neutral'}
                  />
                  <ManagementCounter
                    label="With approver"
                    value={managementCounters.withApprover}
                    detail={
                      managementCounters.delayedApprovals > 0
                        ? `${managementCounters.delayedApprovals} delayed`
                        : managementCounters.withApprover
                          ? 'Pending decision'
                          : 'No approval wait'
                    }
                    tone={managementCounters.delayedApprovals > 0 ? 'warning' : 'neutral'}
                    onClick={() => router.push('/approvals')}
                  />
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </section>

      <section data-dashboard-section className="mb-6 grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.8fr)_minmax(320px,1fr)]">
        <motion.div
          initial={prefersReducedMotion ? { opacity: 0 } : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.1, ease: [0.25, 0.1, 0.25, 1] }}
        >
          <Card className="overflow-hidden">
          <CardHeader className="flex flex-col gap-3 border-b border-[rgba(82,90,99,0.34)] lg:flex-row lg:items-start lg:justify-between">
            <div>
              <CardTitle className="text-base font-semibold tracking-tight normal-case text-stone-100">{dashboardCopy.queueTitle}</CardTitle>
              <p className="mt-1 text-sm text-stone-400">
                {dashboardCopy.queueDescription}
                {hasActiveFilters && summaryData ? (
                  <span className="ml-2 text-stone-300">• {filteredWorkQueue.length} of {summaryData.needs_attention.length} shown</span>
                ) : !primaryLoading && queuePreview.length > 0 ? (
                  <span className="ml-2 text-stone-500">• sorted by urgency</span>
                ) : null}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {queuePreview.length > 0 ? <Badge variant="warning">{queuePreview.length}</Badge> : null}
              
              <div className="relative">
                <select
                  value={selectedOwner}
                  onChange={(e) => handleOwnerFilterChange(e.target.value as 'All' | 'Mine' | 'Unassigned')}
                  className="appearance-none rounded-md border border-[rgba(82,90,99,0.5)] bg-[rgba(18,21,24,0.7)] py-1 pl-3 pr-8 text-sm text-stone-200 shadow-sm transition-colors hover:border-[rgba(82,90,99,0.8)] focus:border-[#c59a5c] focus:outline-none focus:ring-1 focus:ring-[#c59a5c]"
                >
                  <option value="All">All ownership</option>
                  <option value="Mine">My cases</option>
                  <option value="Unassigned">Unassigned</option>
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-stone-400">
                  <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>

              {hasActiveFilters ? (
                <Button variant="outline" size="sm" onClick={openDrawerWithFilters}>
                  Open drilldown
                </Button>
              ) : (
                <Button variant="outline" size="sm" onClick={() => router.push('/dashboard/cases')}>
                  View all cases
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {!summaryUnavailable && escalationPreview.length > 0 ? (
              <div className="border-b border-[rgba(82,90,99,0.28)] bg-[rgba(189,90,86,0.06)] px-4 py-3">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <div className="text-xs font-medium text-[rgb(219,156,153)]">Needs escalation</div>
                    <p className="mt-1 text-xs text-stone-400">
                      Stale cases without an owner are creating operational risk.
                    </p>
                  </div>
                  <Button variant="outline" size="sm" onClick={openEscalationView}>
                    Open escalation view
                  </Button>
                </div>
                <div className="mt-3 divide-y divide-[rgba(82,90,99,0.22)] rounded-md border border-[rgba(82,90,99,0.28)] bg-[rgba(18,22,26,0.36)]">
                  {escalationPreview.map((item) => (
                    <button
                      key={`escalation-${item.case_id}`}
                      type="button"
                      onClick={() => router.push(getCaseDetailPath(item.case_id))}
                      className="flex w-full items-center justify-between gap-3 px-3 py-3 text-left transition-colors hover:bg-[rgba(34,39,45,0.78)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[rgba(126,133,111,0.85)]"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-sm font-medium text-stone-200">{item.title}</div>
                        <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-stone-500">
                          <span className="text-[rgb(219,156,153)]">{getAttentionReason(item)}</span>
                          <span>· {getIdleLabel(item.updated_at) ?? 'Stale'}</span>
                          <span>· Needs assignment</span>
                        </div>
                      </div>
                      <div className="text-xs font-medium text-stone-400">Open case →</div>
                    </button>
                  ))}
                </div>
              </div>
            ) : null}
            <div className="divide-y divide-[rgba(82,90,99,0.28)]">
              {summaryUnavailable ? (
                <div className="p-4">
                  <CompactCardState
                    variant="error"
                    title="Unable to load review queue."
                    description={summaryError || 'Primary dashboard data is unavailable right now.'}
                    action={
                      <Button variant="outline" size="sm" onClick={handleRetry}>
                        Retry
                      </Button>
                    }
                  />
                </div>
              ) : primaryLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="p-4">
                    <SkeletonRow />
                  </div>
                ))
              ) : queuePreview.length > 0 ? (
                queuePreview.map((item) => (
                  <WorkQueueItem
                    key={item.case_id}
                    item={item}
                    onClick={() => router.push(getCaseDetailPath(item.case_id))}
                    onAssignmentAction={handleAssignmentAction}
                    assignmentPending={assignmentPendingCaseId === item.case_id}
                    canClaim={currentRole === 'Reviewer' || currentRole === 'Approver' || currentRole === 'Admin'}
                    isCurrentUserOwner={Boolean(currentUser?.email) && item.assigned_to_email === currentUser?.email}
                    currentUserEmail={currentUser?.email}
                  />
                ))
              ) : (
                <div className="p-4">
                  <CompactCardState
                    icon={hasActiveFilters ? <FilterIcon /> : <CheckIcon />}
                    title={
                      selectedEscalation
                        ? '✓ No stale unassigned cases.'
                        : hasActiveFilters
                        ? 'No matching cases'
                        : '✓ Review queue is clear.'
                    }
                    description={
                      selectedEscalation
                        ? 'No stale unassigned work currently requires escalation.'
                        : hasActiveFilters
                        ? 'Adjust the current filters to broaden the review queue.'
                        : summaryData && summaryData.needs_attention.length === 0
                          ? `No cases require attention in the ${selectedDays}-day window. Queue is operational.`
                          : 'The review queue is clear for the selected monitoring window.'
                    }
                    action={
                      selectedEscalation ? (
                        <Button variant="outline" size="sm" onClick={() => setSelectedEscalation(null)}>
                          Clear escalation
                        </Button>
                      ) : hasActiveFilters ? (
                        <Button variant="outline" size="sm" onClick={clearFilters}>
                          Clear filters
                        </Button>
                      ) : (
                        <Button variant="outline" size="sm" onClick={() => router.push('/dashboard/cases')}>
                          View all cases
                        </Button>
                      )
                    }
                  />
                </div>
              )}
            </div>
          </CardContent>
          </Card>
        </motion.div>

        <div className="space-y-6">
          <Card className="overflow-hidden">
            <CardHeader className="border-b border-[rgba(82,90,99,0.34)]">
              <CardTitle className="text-base font-semibold tracking-tight normal-case text-stone-100">{dashboardCopy.approvalsTitle}</CardTitle>
              <p className="mt-1 text-sm text-stone-400">{dashboardCopy.approvalsDescription}</p>
            </CardHeader>
            <CardContent className="space-y-4">
              {summaryUnavailable ? (
                <CompactCardState
                  variant="error"
                  title="Approval preview unavailable."
                  description="Primary dashboard data is unavailable, so readiness and approval items could not be loaded."
                  action={
                    <Button variant="outline" size="sm" onClick={handleRetry}>
                      Retry
                    </Button>
                  }
                />
              ) : primaryLoading ? (
                <div className="space-y-3">
                  {Array.from({ length: 4 }).map((_, index) => (
                    <SkeletonRow key={index} />
                  ))}
                </div>
              ) : summaryData && (moveForwardPreview.length > 0 || summaryData.kpis.pending_verifications > 0) ? (
                <>
                  <div className="grid gap-2 sm:grid-cols-3">
                    <InlineMetric
                      label="Pending approvals"
                      value={ownershipScopedApprovalMetrics.pendingApprovals}
                      detail={ownershipScopedApprovalMetrics.pendingApprovals ? 'Awaiting decision' : 'None pending'}
                    />
                    <InlineMetric
                      label="Ready to advance"
                      value={ownershipScopedApprovalMetrics.readyCases}
                      detail={ownershipScopedApprovalMetrics.readyCases ? 'Can move forward now' : 'None ready'}
                    />
                    <InlineMetric
                      label="Open verifications"
                      value={ownershipScopedApprovalMetrics.openVerifications}
                      detail={ownershipScopedApprovalMetrics.openVerifications ? 'Still blocking progress' : 'Queue clear'}
                    />
                  </div>

                  <div className="rounded-md border border-[rgba(82,90,99,0.34)] bg-[rgba(18,22,26,0.44)]">
                    <div className="border-b border-[rgba(82,90,99,0.24)] px-3 py-2 text-xs font-medium text-stone-500">
                      Readiness preview
                    </div>
                    <div className="divide-y divide-[rgba(82,90,99,0.24)]">
                      {moveForwardPreview.length > 0 ? (
                        moveForwardPreview.map((item) => (
                          <ApprovalReadinessRow key={item.id} item={item} />
                        ))
                      ) : (
                        <CompactCardState
                          title="No cases are currently ready for approval."
                          description="Verification items remain open before cases can move forward."
                          action={
                            <Button variant="outline" size="sm" onClick={() => router.push('/dashboard/cases')}>
                              Open review queue
                            </Button>
                          }
                        />
                      )}
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" className="flex-1" onClick={() => router.push('/approvals')}>
                      Review approvals
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1"
                      onClick={() => {
                        setSelectedStatus('Ready for Approval');
                        setDrawerTab('cases');
                        setDrawerOpen(true);
                      }}
                    >
                      View ready cases
                    </Button>
                  </div>
                </>
              ) : (
                <CompactCardState
                  icon={<CheckIcon />}
                  title="No immediate approval pressure."
                  description="No approval requests or ready cases require attention right now."
                  action={
                    <Button variant="outline" size="sm" onClick={() => router.push('/approvals')}>
                      Review approvals
                    </Button>
                  }
                />
              )}
            </CardContent>
          </Card>

          <Card className="overflow-hidden">
            <CardHeader className="flex flex-row items-start justify-between border-b border-[rgba(82,90,99,0.34)]">
              <div>
                <CardTitle className="text-base font-semibold tracking-tight normal-case text-stone-100">{dashboardCopy.activityTitle}</CardTitle>
                <p className="mt-1 text-sm text-stone-400">
                  {dashboardCopy.activityDescription}
                  {selectedDate ? <span className="ml-2 text-stone-300">• {formatDateDisplay(selectedDate)}</span> : null}
                </p>
              </div>
              {!primaryLoading && activityPreview.length > 0 && (
                <Badge variant="neutral">{activityPreview.length}</Badge>
              )}
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-[rgba(82,90,99,0.28)]">
                {summaryUnavailable ? (
                  <div className="p-4">
                    <CompactCardState
                      variant="error"
                      title="Activity preview unavailable."
                      description="Dashboard data could not be loaded. Retry to restore the activity feed."
                      action={
                        <Button variant="outline" size="sm" onClick={handleRetry}>
                          Retry
                        </Button>
                      }
                    />
                  </div>
                ) : primaryLoading ? (
                  Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className="px-4 py-3">
                      <div className="flex items-start gap-3">
                        <Skeleton className="h-8 w-8 rounded-md flex-shrink-0" />
                        <div className="flex-1 space-y-1.5">
                          <Skeleton className="h-3.5 w-full" />
                          <Skeleton className="h-3 w-2/3" />
                        </div>
                      </div>
                    </div>
                  ))
                ) : activityPreview.length > 0 ? (
                  activityPreview.map((item, i) => (
                    <ActivityItemRow key={`${item.created_at}-${i}`} item={item} />
                  ))
                ) : (
                  <div className="p-4">
                    <CompactCardState
                      icon={selectedDate ? <FilterIcon /> : <EmptyIcon />}
                      title={
                        selectedDate
                          ? 'No activity on this date.'
                          : summaryData
                          ? 'No activity in this window.'
                          : 'No recent activity recorded.'
                      }
                      description={
                        selectedDate
                          ? 'Select a different date or clear the date filter.'
                          : 'No case, approval, or verification events recorded in the selected range.'
                      }
                      action={
                        selectedDate ? (
                          <Button variant="outline" size="sm" onClick={() => setSelectedDate(null)}>
                            Clear date
                          </Button>
                        ) : (
                          <Button variant="outline" size="sm" onClick={() => router.push('/dashboard/cases')}>
                            Open review queue
                          </Button>
                        )
                      }
                    />
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      <section data-dashboard-section>
        <DashboardAnalyticsSection
          data={analyticsData}
          loading={analyticsLoading}
          error={analyticsError}
          selectedDate={selectedDate}
          selectedStatus={selectedStatus}
          selectedSeverity={selectedSeverity}
          onSelectDate={handleDateSelect}
          onSelectStatus={handleStatusSelect}
          onSelectSeverity={handleSeveritySelect}
          onRetry={() => {
            void fetchDashboardAnalytics(selectedDays, true);
          }}
        />
      </section>

      {/* Save View Modal */}
      {showSaveView && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="fixed inset-0 bg-black/60" onClick={() => setShowSaveView(false)} />
          <div className="relative w-full max-w-md rounded-lg border border-[rgba(82,90,99,0.5)] bg-[rgba(29,34,39,0.98)] p-6 shadow-[0_18px_48px_rgba(0,0,0,0.35)]">
            <h3 className="mb-4 text-lg font-semibold text-stone-100">Save Current View</h3>
            <p className="mb-4 text-sm text-stone-400">
              Days: {selectedDays}
              {selectedSeverity && ` · Severity: ${selectedSeverity}`}
              {selectedStatus && ` · Status: ${selectedStatus}`}
            </p>
            <input
              type="text"
              placeholder="View name..."
              value={newViewName}
              onChange={(e) => setNewViewName(e.target.value)}
              className="mb-4 w-full rounded-md border border-[rgba(82,90,99,0.55)] bg-[rgba(22,26,30,0.92)] px-4 py-2 text-stone-100 placeholder:text-stone-500 focus:outline-none focus:ring-2 focus:ring-[rgba(126,133,111,0.85)]"
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
        activeTab={drawerTab}
        onActiveTabChange={setDrawerTab}
        filters={{
          severity: selectedSeverity,
          status: selectedStatus,
          date: selectedDate,
          owner: selectedOwner !== 'All' ? selectedOwner : null,
          escalation: selectedEscalation,
        }}
        onNavigateCase={(caseId) => {
          setDrawerOpen(false);
          router.push(getCaseDetailPath(caseId));
        }}
      />
    </>
  );
}

function DashboardKpi({
  label,
  value,
  sublabel,
  tone = 'neutral',
  loading = false,
}: {
  label: string;
  value?: string | number;
  sublabel?: string;
  tone?: 'neutral' | 'warning' | 'danger' | 'success';
  loading?: boolean;
}) {
  const valueTone =
    tone === 'danger'
      ? 'text-[rgb(219,156,153)]'
      : tone === 'warning'
        ? 'text-[rgb(219,194,137)]'
        : tone === 'success'
          ? 'text-[rgb(187,205,189)]'
          : 'text-stone-100';

  const markerTone =
    tone === 'danger'
      ? 'bg-[rgb(189,90,86)]'
      : tone === 'warning'
        ? 'bg-[rgb(184,151,95)]'
        : tone === 'success'
          ? 'bg-[rgb(127,160,133)]'
          : 'bg-[rgba(143,154,127,0.8)]';

  return (
    <div className="dashboard-surface-muted rounded-[1.2rem] px-4 py-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[11px] font-medium leading-5 text-stone-500">{label}</div>
          <div className={`mt-2 font-display text-[1.9rem] font-semibold leading-none tracking-[-0.05em] ${valueTone}`}>
        {loading ? '—' : value ?? '—'}
          </div>
        </div>
        <span className={`mt-1 h-2.5 w-2.5 flex-shrink-0 rounded-full ${markerTone}`} />
      </div>
      {sublabel ? <div className="mt-2 text-[11px] leading-5 text-stone-500">{sublabel}</div> : null}
    </div>
  );
}

function DashboardPageFallback() {
  return (
    <>
      <SetPageChrome title="Dashboard" breadcrumbs={[{ label: "Dashboard" }]} />
      <section className="space-y-6">
        <div className="dashboard-surface rounded-[1.75rem] px-5 py-5">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <div key={index} className="dashboard-surface-muted rounded-[1.2rem] px-4 py-4">
                <Skeleton className="h-3 w-28" />
                <Skeleton className="mt-3 h-8 w-16" />
                <Skeleton className="mt-2 h-3 w-24" />
              </div>
            ))}
          </div>
        </div>
        <section className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.8fr)_minmax(320px,1fr)]">
          <Card>
            <CardHeader className="border-b border-[rgba(82,90,99,0.34)]">
              <Skeleton className="h-5 w-40" />
              <Skeleton className="mt-2 h-4 w-72" />
            </CardHeader>
            <CardContent className="space-y-3">
              {Array.from({ length: 5 }).map((_, index) => (
                <SkeletonRow key={index} />
              ))}
            </CardContent>
          </Card>
          <div className="space-y-6">
            {Array.from({ length: 2 }).map((_, index) => (
              <Card key={index}>
                <CardHeader className="border-b border-[rgba(82,90,99,0.34)]">
                  <Skeleton className="h-5 w-32" />
                  <Skeleton className="mt-2 h-4 w-56" />
                </CardHeader>
                <CardContent className="space-y-3">
                  {Array.from({ length: 3 }).map((__, rowIndex) => (
                    <SkeletonRow key={rowIndex} />
                  ))}
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
      </section>
    </>
  );
}

function InlineMetric({
  label,
  value,
  detail,
}: {
  label: string;
  value?: string | number;
  detail: string;
}) {
  return (
    <div className="dashboard-surface-muted rounded-[1rem] px-3 py-3">
      <div className="text-[11px] font-medium text-stone-500">{label}</div>
      <div className="mt-1 font-display text-lg font-semibold leading-none tracking-[-0.04em] text-stone-100">{value ?? '—'}</div>
      <div className="mt-1 text-[11px] leading-5 text-stone-500">{detail}</div>
    </div>
  );
}

function ManagementCounter({
  label,
  value,
  detail,
  tone = 'neutral',
  onClick,
}: {
  label: string;
  value: number;
  detail: string;
  tone?: 'neutral' | 'warning' | 'danger';
  onClick?: () => void;
}) {
  const toneClass =
    tone === 'danger'
      ? 'border-[rgba(189,90,86,0.28)] bg-[rgba(189,90,86,0.08)]'
      : tone === 'warning'
      ? 'border-[rgba(184,151,95,0.28)] bg-[rgba(184,151,95,0.08)]'
      : 'border-[rgba(82,90,99,0.26)] bg-[rgba(18,22,26,0.44)]';

  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        className={`rounded-[1rem] border px-3 py-3 text-left transition-colors ${toneClass} hover:bg-[rgba(34,39,45,0.74)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(126,133,111,0.85)]`}
      >
        <div className="text-[11px] font-medium text-stone-500">{label}</div>
        <div className="mt-1 font-display text-lg font-semibold leading-none tracking-[-0.04em] text-stone-100">{value}</div>
        <div className="mt-1 text-[11px] leading-5 text-stone-500">{detail}</div>
      </button>
    );
  }

  return (
    <div className={`rounded-[1rem] border px-3 py-3 text-left ${toneClass}`}>
      <div className="text-[11px] font-medium text-stone-500">{label}</div>
      <div className="mt-1 font-display text-lg font-semibold leading-none tracking-[-0.04em] text-stone-100">{value}</div>
      <div className="mt-1 text-[11px] leading-5 text-stone-500">{detail}</div>
    </div>
  );
}

function CompactCardState({
  title,
  description,
  action,
  icon,
  variant = 'neutral',
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
  icon?: React.ReactNode;
  variant?: 'neutral' | 'error';
}) {
  const containerClass =
    variant === 'error'
      ? 'border-[rgba(189,90,86,0.32)] bg-[rgba(189,90,86,0.08)]'
      : 'border-[rgba(82,90,99,0.32)] bg-[rgba(18,22,26,0.44)]';
  const titleClass = variant === 'error' ? 'text-[rgb(219,156,153)]' : 'text-stone-100';

  return (
    <div className={`rounded-[1.1rem] border px-4 py-4 ${containerClass}`}>
      <div className="flex items-start gap-3">
        {icon ? (
          <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-[rgba(82,90,99,0.32)] bg-[rgba(34,39,45,0.78)]">
            {icon}
          </div>
        ) : null}
        <div className="min-w-0 flex-1">
          <div className={`text-sm font-medium ${titleClass}`}>{title}</div>
          <div className="mt-1 text-xs leading-5 text-stone-400">{description}</div>
          {action ? <div className="mt-3">{action}</div> : null}
        </div>
      </div>
    </div>
  );
}

function DashboardAnalyticsSkeleton() {
  return (
    <section className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.65fr)_minmax(0,1fr)]">
      <Card>
        <CardHeader className="border-b border-[rgba(82,90,99,0.34)]">
          <Skeleton className="h-5 w-36" />
          <Skeleton className="mt-2 h-4 w-72" />
        </CardHeader>
        <CardContent>
          <div className="h-64 rounded-md border border-[rgba(82,90,99,0.24)] bg-[rgba(18,22,26,0.44)]" />
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-6">
        {Array.from({ length: 2 }).map((_, index) => (
          <Card key={index}>
            <CardHeader className="border-b border-[rgba(82,90,99,0.34)]">
              <Skeleton className="h-5 w-32" />
              <Skeleton className="mt-2 h-4 w-64" />
            </CardHeader>
            <CardContent>
              <div className="h-48 rounded-md border border-[rgba(82,90,99,0.24)] bg-[rgba(18,22,26,0.44)]" />
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}

// Filter badge component
function FilterBadge({ label, color, onRemove }: { label: string; color: string; onRemove: () => void }) {
  return (
    <span 
      className="inline-flex items-center gap-1.5 rounded-full border bg-[rgba(30,35,40,0.88)] px-2.5 py-1 text-[11px] font-medium shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]"
      style={{ borderColor: `${color}40` }}
    >
      <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
      <span className="text-stone-200">{label}</span>
      <button 
        onClick={onRemove}
        className="ml-0.5 text-stone-500 transition-colors hover:text-stone-200"
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
    <div className="flex items-center gap-1 rounded-xl border border-[rgba(82,90,99,0.42)] bg-[rgba(24,28,32,0.9)] p-1">
      {options.map((days) => (
        <button
          key={days}
          onClick={() => onChange(days)}
          disabled={disabled}
          className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-all ${
            value === days
              ? 'bg-[rgba(154,165,137,0.96)] text-[#101410] shadow-[0_8px_18px_rgba(103,116,83,0.18)]'
              : 'text-stone-400 hover:bg-[rgba(44,50,57,0.92)] hover:text-stone-100'
          } disabled:opacity-50`}
        >
          {days}d
        </button>
      ))}
    </div>
  );
}

// Work queue item component — urgency-ranked, blocker-first, with aging + escalation cues
function WorkQueueItem({
  item,
  onClick,
  onAssignmentAction,
  assignmentPending,
  canClaim,
  isCurrentUserOwner,
  currentUserEmail,
}: {
  item: NeedsAttentionItem;
  onClick: () => void;
  onAssignmentAction: (caseId: string, action: 'claim' | 'unassign') => Promise<void>;
  assignmentPending: boolean;
  canClaim: boolean;
  isCurrentUserOwner: boolean;
  currentUserEmail?: string | null;
}) {
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

  // Urgency stripe color: red for high exceptions, yellow for pending verifications, dim otherwise
  const urgencyStripe =
    item.open_high > 0
      ? 'bg-[rgb(189,90,86)]'
      : item.pending_verifications > 0
      ? 'bg-[rgb(184,151,95)]'
      : 'bg-[rgba(82,90,99,0.4)]';

  const idleLabel = getIdleLabel(item.updated_at);
  const escalation = isEscalationRisk(item);

  return (
    <div className="relative flex w-full items-start gap-4 p-4 pl-5 transition-colors hover:bg-[rgba(34,39,45,0.88)]">
      {/* Urgency stripe on the left edge */}
      <span className={`absolute left-0 top-3 bottom-3 w-[3px] rounded-full ${urgencyStripe}`} />
      <button
        type="button"
        onClick={onClick}
        className="flex min-w-0 flex-1 items-start gap-4 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[rgba(126,133,111,0.85)]"
      >
        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-md border border-[rgba(82,90,99,0.36)] bg-[rgba(34,39,45,0.75)]">
          {item.open_high > 0 ? <ExceptionIcon /> : <VerificationIcon />}
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-stone-200">{item.title}</p>
          {/* Primary blocker reason — the most important line */}
          <p className={`mt-0.5 text-xs font-medium ${item.open_high > 0 ? 'text-[rgb(219,156,153)]' : item.pending_verifications > 0 ? 'text-[rgb(219,194,137)]' : 'text-stone-400'}`}>
            ⚠ {getAttentionReason(item)}
          </p>
          <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-stone-500">
            {item.open_medium > 0 && (
              <span className="text-[rgb(219,194,137)]">+{item.open_medium} medium</span>
            )}
            {item.open_low > 0 && (
              <span className="text-stone-500">{item.open_low} low</span>
            )}
            <span
              className={item.assigned_to_user_id ? 'text-stone-400' : 'text-[rgb(219,156,153)] font-medium'}
              title={item.assigned_to_email || ''}
            >
              · {getWorkItemOwnerCue(item, currentUserEmail)}
            </span>
            <span>· Updated {formatRelativeTime(item.updated_at)}</span>
            {/* Aging label — only shown for stale/overdue cases to reduce noise */}
            {idleLabel && (
              <span className={`font-medium ${
                getAgingLevel(item.updated_at) === 'overdue'
                  ? 'text-[rgb(219,156,153)]'
                  : 'text-[rgb(219,194,137)]'
              }`}>
                {idleLabel}
              </span>
            )}
          </div>
          {/* Escalation cue */}
          {escalation && (
            <div className="mt-1.5">
              <span className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium text-[rgb(219,156,153)] bg-[rgba(189,90,86,0.12)] border border-[rgba(189,90,86,0.22)]">
                {(!item.assigned_to_user_id) ? 'Stale & Unassigned — needs owner' : 'Stale blocker — needs escalation'}
              </span>
            </div>
          )}
        </div>
      </button>
      <div className="flex shrink-0 flex-col items-end gap-2">
        <Badge variant={statusColors[item.status] || 'neutral'}>{item.status}</Badge>
        {canClaim ? (
          !item.assigned_to_user_id ? (
            <Button
              variant="outline"
              size="sm"
              disabled={assignmentPending}
              loading={assignmentPending}
              onClick={() => {
                void onAssignmentAction(item.case_id, 'claim');
              }}
            >
              {assignmentPending ? 'Assigning…' : 'Assign to me'}
            </Button>
          ) : isCurrentUserOwner ? (
            <Button
              variant="ghost"
              size="sm"
              disabled={assignmentPending}
              loading={assignmentPending}
              onClick={() => {
                void onAssignmentAction(item.case_id, 'unassign');
              }}
            >
              {assignmentPending ? 'Clearing…' : 'Clear assignment'}
            </Button>
          ) : null
        ) : null}
        <button
          type="button"
          onClick={onClick}
          className="text-xs font-medium text-stone-400 transition-colors hover:text-stone-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(126,133,111,0.85)]"
        >
          Open case →
        </button>
      </div>
    </div>
  );
}

// Approval readiness row — distinguishes READY / NEARLY READY / PENDING DECISION with aging
function ApprovalReadinessRow({
  item,
}: {
  item: {
    id: string;
    title: string;
    readinessState: 'ready' | 'nearlyReady' | 'pending';
    supportingLabel: string;
    supportingDetail: string;
    ownerLabel: string;
    updatedAt: string;
    cta: string;
    onClick: () => void;
    tone: 'success' | 'warning';
  };
}) {
  const stateIcon =
    item.readinessState === 'ready'
      ? '✓'
      : item.readinessState === 'nearlyReady'
      ? '⏳'
      : '⏵';

  const idleLabel = getIdleLabel(item.updatedAt);
  // Approval requests waiting 2+ days get an "Approval delayed" cue
  const approvalDelayed = item.readinessState === 'pending' && isApprovalDelayed(item.updatedAt);
  const ownerLabelNormalized = item.ownerLabel.toLowerCase();
  const ownershipGap =
    (ownerLabelNormalized.includes('unassigned') || ownerLabelNormalized.includes('owner missing')) &&
    (item.readinessState === 'ready' || item.readinessState === 'pending');

  return (
    <button
      type="button"
      onClick={item.onClick}
      className="flex w-full items-start justify-between gap-3 px-3 py-3 text-left transition-colors hover:bg-[rgba(34,39,45,0.78)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[rgba(126,133,111,0.85)]"
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <Badge variant={item.tone}>
            {stateIcon} {item.supportingLabel}
          </Badge>
          <span className="truncate text-sm font-medium text-stone-200">{item.title}</span>
        </div>
        <div className="mt-1 line-clamp-1 text-xs text-stone-500">{item.supportingDetail}</div>
        <div className="mt-1 text-[11px] text-stone-500">{item.ownerLabel}</div>
        {ownershipGap && (
          <div className="mt-1">
            <span className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium text-[rgb(219,194,137)] bg-[rgba(184,151,95,0.1)] border border-[rgba(184,151,95,0.22)]">
              Ownership gap — ready without a reviewer owner
            </span>
          </div>
        )}
        {/* Approval delayed cue */}
        {approvalDelayed && (
          <div className="mt-1">
            <span className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium text-[rgb(219,194,137)] bg-[rgba(184,151,95,0.1)] border border-[rgba(184,151,95,0.22)]">
              Approval delayed — waiting {idleLabel ?? formatRelativeTime(item.updatedAt)}
            </span>
          </div>
        )}
      </div>
      <div className="shrink-0 text-right">
        <div className="text-xs text-stone-500">{formatRelativeTime(item.updatedAt)}</div>
        {idleLabel && !approvalDelayed && (
          <div className={`mt-0.5 text-[10px] font-medium ${
            getAgingLevel(item.updatedAt) === 'overdue' ? 'text-[rgb(219,156,153)]' : 'text-stone-500'
          }`}>
            {idleLabel}
          </div>
        )}
        <div className="mt-1 text-xs font-medium text-stone-400">{item.cta} →</div>
      </div>
    </button>
  );
}

// Activity item component — shows actor + action narrative + time + importance hint
function ActivityItemRow({ item }: { item: ActivityItem }) {
  const router = useRouter();

  const initials = item.actor_email
    ? item.actor_email.substring(0, 2).toUpperCase()
    : 'SY';

  const { line, hint } = getActivityNarrative(item);

  // Phase 4: Use direct case_id and case_title if available, otherwise fallback
  const directCaseLink = item.case_id && item.case_title;
  let entityRef: React.ReactNode = null;
  
  if (directCaseLink) {
    entityRef = (
      <span 
        className="ml-1.5 cursor-pointer text-stone-300 hover:text-stone-100 hover:underline transition-colors"
        onClick={(e) => {
          e.stopPropagation();
          router.push(getCaseDetailPath(item.case_id!));
        }}
        title={`Go to case: ${item.case_title}`}
      >
        · {item.case_title}
      </span>
    );
  } else if (item.entity_type === 'case' && item.entity_id) {
    entityRef = <span className="ml-1.5 text-stone-500">· case #{String(item.entity_id).slice(0, 8)}</span>;
  } else if (item.entity_type && item.entity_id) {
    entityRef = <span className="ml-1.5 text-stone-500">· {item.entity_type.replace(/_/g, ' ')} #{String(item.entity_id).slice(0, 8)}</span>;
  }

  return (
    <div className="flex items-start gap-3 px-4 py-3 transition-colors hover:bg-[rgba(34,39,45,0.8)]">
      <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md border border-[rgba(82,90,99,0.34)] bg-[rgba(34,39,45,0.8)] text-[10px] font-semibold text-stone-300 uppercase tracking-wide">
        {initials}
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm text-stone-200 leading-snug">
          {line}
          {entityRef}
        </p>
        <div className="mt-0.5 flex items-center gap-2">
          <span className="text-xs text-stone-500">{formatRelativeTime(item.created_at)}</span>
          {hint === 'Requires review' && (
            <span className="text-[10px] font-medium text-[rgb(219,194,137)] bg-[rgba(219,194,137,0.1)] rounded px-1.5 py-0.5">
              Requires review
            </span>
          )}
          {hint === 'Decision recorded' && (
            <span className="text-[10px] font-medium text-[rgb(187,205,189)] bg-[rgba(187,205,189,0.1)] rounded px-1.5 py-0.5">
              Decision recorded
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

// Icons
function CheckIcon() {
  return (
    <svg className="w-6 h-6 text-[rgb(187,205,189)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}

function FilterIcon() {
  return (
    <svg className="w-6 h-6 text-stone-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 3c2.755 0 5.455.232 8.083.678.533.09.917.556.917 1.096v1.044a2.25 2.25 0 01-.659 1.591l-5.432 5.432a2.25 2.25 0 00-.659 1.591v2.927a2.25 2.25 0 01-1.244 2.013L9.75 21v-6.568a2.25 2.25 0 00-.659-1.591L3.659 7.409A2.25 2.25 0 013 5.818V4.774c0-.54.384-1.006.917-1.096A48.32 48.32 0 0112 3z" />
    </svg>
  );
}

function ExceptionIcon() {
  return (
    <svg className="w-5 h-5 text-[rgb(219,156,153)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
    </svg>
  );
}

function VerificationIcon() {
  return (
    <svg className="w-5 h-5 text-stone-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
    </svg>
  );
}




