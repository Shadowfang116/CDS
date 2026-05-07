'use client';

import { useState, useEffect, useCallback } from 'react';
import { SetPageChrome } from '@/components/layout/set-page-chrome';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/ui/empty-state';
import {
  listAdminUsers,
  listAuditLogs,
  resetDemoCase,
  AdminUser,
  AuditLogEntry,
} from '@/lib/api';

type TabValue = 'users' | 'audit';

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<TabValue>('users');
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [auditDays, setAuditDays] = useState(7);
  const [resettingDemo, setResettingDemo] = useState(false);
  const [demoResetMessage, setDemoResetMessage] = useState<string | null>(null);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listAdminUsers();
      setUsers(data);
    } catch (e: any) {
      setError(e.message || 'Failed to load users');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadAuditLogs = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listAuditLogs({ days: auditDays, limit: 200 });
      setAuditLogs(data);
    } catch (e: any) {
      setError(e.message || 'Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  }, [auditDays]);

  useEffect(() => {
    if (activeTab === 'users') {
      void loadUsers();
    } else {
      void loadAuditLogs();
    }
  }, [activeTab, loadUsers, loadAuditLogs]);

  const handleResetDemo = useCallback(async () => {
    setResettingDemo(true);
    setDemoResetMessage(null);
    setError(null);

    try {
      const result = await resetDemoCase();
      setDemoResetMessage(`Demo matter reset successfully. Matter ID: ${result.case_id.slice(0, 8)}`);
    } catch (e: any) {
      setError(e.message || 'Failed to reset demo matter');
    } finally {
      setResettingDemo(false);
    }
  }, []);

  return (
    <>
      <SetPageChrome
        title="Admin"
        subtitle="Approver and platform controls"
        breadcrumbs={[{ label: 'Admin' }]}
      />
      <div className="p-6 space-y-6" data-dashboard-reveal>
        <section className="rounded-xl border border-[rgba(82,90,99,0.36)] bg-[rgba(24,28,32,0.84)] p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="text-sm font-semibold text-stone-100">Demo controls</div>
              <p className="mt-1 text-sm text-stone-400">
                Reset the seeded Lahore demonstration matter for presentation use. This control is limited to the Admin workspace and is not exposed in the general user journey.
              </p>
            </div>
            <Button variant="outline" size="sm" onClick={handleResetDemo} loading={resettingDemo}>
              Reset Demo Matter
            </Button>
          </div>
          {demoResetMessage ? (
            <p className="mt-3 text-xs text-[rgb(187,205,189)]">{demoResetMessage}</p>
          ) : null}
        </section>

        <div className="flex gap-2 border-b border-[rgba(82,90,99,0.36)]">
          <button
            onClick={() => setActiveTab('users')}
            className={`px-4 py-2 font-medium ${
              activeTab === 'users'
                ? 'border-b-2 border-[rgba(126,133,111,0.9)] text-stone-100'
                : 'text-stone-500 hover:text-stone-300'
            }`}
          >
            Users
          </button>
          <button
            onClick={() => setActiveTab('audit')}
            className={`px-4 py-2 font-medium ${
              activeTab === 'audit'
                ? 'border-b-2 border-[rgba(126,133,111,0.9)] text-stone-100'
                : 'text-stone-500 hover:text-stone-300'
            }`}
          >
            Audit Log
          </button>
        </div>

        {error && (
          <div className="rounded-lg border border-[rgba(189,90,86,0.36)] bg-[rgba(189,90,86,0.12)] px-4 py-3 text-[rgb(219,156,153)]">
            {error}
          </div>
        )}

        {activeTab === 'users' && (
          <div data-dashboard-section>
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-slate-100">Users</h3>
              <Button onClick={() => alert('User creation UI would open here')}>
                Create User
              </Button>
            </div>

            {loading ? (
              <Skeleton className="h-32 w-full" />
            ) : users.length === 0 ? (
              <EmptyState message="No users found" />
            ) : (
              <div className="space-y-2">
                {users.map((user) => (
                  <div
                    key={user.id}
                    className="card flex items-center justify-between p-4"
                  >
                    <div>
                      <div className="font-medium text-slate-100">{user.full_name}</div>
                      <div className="text-sm text-slate-400">{user.email}</div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge variant="outline">{user.role}</Badge>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => alert(`Role change UI for ${user.email}`)}
                      >
                        Change Role
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'audit' && (
          <div data-dashboard-section>
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-slate-100">Audit Log</h3>
              <div className="flex gap-2">
                {[7, 30, 90].map((d) => (
                  <Button
                    key={d}
                    size="sm"
                    variant={auditDays === d ? 'default' : 'outline'}
                    onClick={() => setAuditDays(d)}
                  >
                    {d}d
                  </Button>
                ))}
              </div>
            </div>

            {loading ? (
              <Skeleton className="h-64 w-full" />
            ) : auditLogs.length === 0 ? (
              <EmptyState message="No audit logs found" />
            ) : (
              <div className="max-h-[600px] space-y-2 overflow-y-auto">
                {auditLogs.map((log) => (
                  <div
                    key={log.id}
                    className="card p-3 text-sm"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="font-medium text-stone-200">{log.action}</div>
                        <div className="mt-1 text-xs text-slate-500">
                          {log.entity_type} {log.entity_id ? `• ${log.entity_id.substring(0, 8)}` : ''}
                        </div>
                        {Object.keys(log.event_metadata || {}).length > 0 && (
                          <div className="mt-1 text-xs text-slate-400">
                            {JSON.stringify(log.event_metadata).substring(0, 100)}...
                          </div>
                        )}
                      </div>
                      <div className="text-xs text-slate-500">
                        {new Date(log.created_at).toLocaleString()}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </>
  );
}
