'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { SetPageChrome } from '@/components/layout/set-page-chrome';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/ui/empty-state';
import {
  listApprovals,
  approveRequest,
  rejectRequest,
  cancelApproval,
  ApprovalRequest,
} from '@/lib/api';
import { getCaseDetailPath } from '@/lib/routes';

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

type TabValue = 'pending' | 'decided' | 'mine';

export default function ApprovalsPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<TabValue>('pending');
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [decisionModal, setDecisionModal] = useState<{
    approval: ApprovalRequest;
    action: 'approve' | 'reject';
  } | null>(null);
  const [decisionReason, setDecisionReason] = useState('');

  const fetchApprovals = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      let params: { status?: string; mine_only?: boolean } = {};
      if (activeTab === 'pending') {
        params.status = 'Pending';
      } else if (activeTab === 'decided') {
        // Fetch non-pending
      } else if (activeTab === 'mine') {
        params.mine_only = true;
      }
      const result = await listApprovals(params);
      
      // Filter for decided tab
      if (activeTab === 'decided') {
        setApprovals(result.approvals.filter(a => a.status !== 'Pending'));
      } else {
        setApprovals(result.approvals);
      }
    } catch (e: any) {
      setError(e.message || 'Failed to load approvals');
    } finally {
      setLoading(false);
    }
  }, [activeTab]);

  useEffect(() => {
    fetchApprovals();
  }, [fetchApprovals]);

  const handleApprove = async (approval: ApprovalRequest) => {
    setDecisionModal({ approval, action: 'approve' });
    setDecisionReason('');
  };

  const handleReject = async (approval: ApprovalRequest) => {
    setDecisionModal({ approval, action: 'reject' });
    setDecisionReason('');
  };

  const handleCancel = async (approvalId: string) => {
    if (!confirm('Cancel this approval request?')) return;
    setActionLoading(approvalId);
    try {
      await cancelApproval(approvalId);
      await fetchApprovals();
    } catch (e: any) {
      setError(e.message || 'Failed to cancel');
    } finally {
      setActionLoading(null);
    }
  };

  const submitDecision = async () => {
    if (!decisionModal) return;
    setActionLoading(decisionModal.approval.id);
    try {
      if (decisionModal.action === 'approve') {
        await approveRequest(decisionModal.approval.id, decisionReason || undefined);
      } else {
        await rejectRequest(decisionModal.approval.id, decisionReason || undefined);
      }
      setDecisionModal(null);
      await fetchApprovals();
    } catch (e: any) {
      setError(e.message || 'Failed to submit decision');
    } finally {
      setActionLoading(null);
    }
  };

  const statusColors: Record<string, 'success' | 'error' | 'warning' | 'neutral'> = {
    Pending: 'warning',
    Approved: 'success',
    Rejected: 'error',
    Cancelled: 'neutral',
  };

  const requestTypeColors: Record<string, string> = {
    exception_waive: 'bg-[rgba(189,90,86,0.16)] text-[rgb(219,156,153)]',
    cp_waive: 'bg-[rgba(184,151,95,0.16)] text-[rgb(219,194,137)]',
    case_decision: 'bg-[rgba(126,133,111,0.16)] text-[rgb(194,200,185)]',
    export_release: 'bg-[rgba(111,140,115,0.16)] text-[rgb(187,205,189)]',
  };

  return (
    <>
      <SetPageChrome
        title="Approvals"
        breadcrumbs={[{ label: 'Approvals' }]}
      />
      <div className="space-y-6" data-dashboard-reveal>
        {error && (
          <div className="rounded-lg border border-[rgba(189,90,86,0.36)] bg-[rgba(189,90,86,0.12)] px-4 py-3 text-sm text-[rgb(219,156,153)]">
            {error}
            <button onClick={() => setError(null)} className="ml-4 underline">
              Dismiss
            </button>
          </div>
        )}

        {/* Tabs */}
        <div className="flex items-center gap-2 border-b border-[rgba(82,90,99,0.36)] pb-px">
          {(['pending', 'decided', 'mine'] as TabValue[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab
                  ? 'border-[rgba(126,133,111,0.9)] text-stone-100'
                  : 'border-transparent text-stone-500 hover:text-stone-300'
              }`}
            >
              {tab === 'pending' && 'Pending'}
              {tab === 'decided' && 'Decided'}
              {tab === 'mine' && 'My Requests'}
            </button>
          ))}
        </div>

        {/* Approvals list */}
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="card p-4">
                <div className="flex items-center gap-4">
                  <Skeleton className="h-6 w-32 rounded-full" />
                  <Skeleton className="h-5 w-48" />
                  <div className="flex-1" />
                  <Skeleton className="h-8 w-24" />
                </div>
              </div>
            ))}
          </div>
        ) : approvals.length === 0 ? (
          <div className="card p-8">
            <EmptyState
              icon={<CheckCircleIcon />}
              title={
                activeTab === 'pending'
                  ? 'No pending approvals'
                  : activeTab === 'mine'
                  ? 'No requests submitted'
                  : 'No decided approvals'
              }
              description={
                activeTab === 'pending'
                  ? 'All approval requests have been processed.'
                  : activeTab === 'mine'
                  ? "You haven't submitted any approval requests yet."
                  : 'No decisions have been made yet.'
              }
            />
          </div>
        ) : (
          <div className="space-y-3">
            {approvals.map((approval) => (
              <div key={approval.id} className="card p-4">
                <div className="flex items-start gap-4 flex-wrap">
                  <div className="flex-1 min-w-[250px]">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full ${
                          requestTypeColors[approval.request_type] || 'bg-slate-500/20 text-slate-400'
                        }`}
                      >
                        {approval.request_type_label}
                      </span>
                      <Badge variant={statusColors[approval.status] || 'neutral'}>
                        {approval.status}
                      </Badge>
                    </div>
                    <p className="text-sm font-medium text-slate-200">
                      {approval.case_title || 'Unknown Case'}
                    </p>
                    <p className="text-xs text-slate-500 mt-1">
                      Requested by {approval.requested_by_email || 'Unknown'} ·{' '}
                      {formatRelativeTime(approval.created_at)}
                    </p>
                    {approval.decided_at && (
                      <p className="text-xs text-slate-500 mt-0.5">
                        Decided by {approval.decided_by_email || 'Unknown'} ·{' '}
                        {formatRelativeTime(approval.decided_at)}
                        {approval.decision_reason && ` · "${approval.decision_reason}"`}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    {approval.status === 'Pending' && activeTab !== 'mine' && (
                      <>
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={() => handleApprove(approval)}
                          disabled={actionLoading === approval.id}
                        >
                          Approve
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleReject(approval)}
                          disabled={actionLoading === approval.id}
                        >
                          Reject
                        </Button>
                      </>
                    )}
                    {approval.status === 'Pending' && activeTab === 'mine' && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleCancel(approval.id)}
                        disabled={actionLoading === approval.id}
                        className="text-rose-400 hover:text-rose-300"
                      >
                        Cancel
                      </Button>
                    )}
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => router.push(getCaseDetailPath(approval.case_id))}
                    >
                      View Case
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Decision Modal */}
        {decisionModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
            <div className="w-full max-w-md rounded-lg border border-[rgba(82,90,99,0.5)] bg-[rgba(29,34,39,0.98)] p-6 shadow-[0_18px_48px_rgba(0,0,0,0.35)]">
              <h2 className="mb-2 text-lg font-semibold text-stone-100">
                {decisionModal.action === 'approve' ? 'Approve Request' : 'Reject Request'}
              </h2>
              <p className="mb-4 text-sm text-stone-400">
                {decisionModal.approval.request_type_label} for{' '}
                {decisionModal.approval.case_title || 'Unknown Case'}
              </p>
              <div className="mb-4">
                <label className="block text-sm text-slate-400 mb-1">
                  Reason (optional)
                </label>
                <textarea
                  value={decisionReason}
                  onChange={(e) => setDecisionReason(e.target.value)}
                  placeholder="Add a reason for your decision..."
                  rows={3}
                  className="w-full rounded-md border border-[rgba(82,90,99,0.55)] bg-[rgba(22,26,30,0.92)] px-3 py-2 text-sm text-stone-200 placeholder:text-stone-500 focus:outline-none focus:ring-2 focus:ring-[rgba(126,133,111,0.85)]"
                />
              </div>
              <div className="flex gap-3">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => setDecisionModal(null)}
                  disabled={!!actionLoading}
                >
                  Cancel
                </Button>
                <Button
                  variant={decisionModal.action === 'approve' ? 'primary' : 'outline'}
                  className={`flex-1 ${
                    decisionModal.action === 'reject' ? 'text-stone-50' : ''
                  }`}
                  onClick={submitDecision}
                  disabled={!!actionLoading}
                >
                  {actionLoading
                    ? 'Processing...'
                    : decisionModal.action === 'approve'
                    ? 'Approve'
                    : 'Reject'}
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

function CheckCircleIcon() {
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
        d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}

