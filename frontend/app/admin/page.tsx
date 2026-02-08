'use client';

import { useState, useEffect } from 'react';
import { AppShell } from '@/components/app/AppShell';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/ui/empty-state';
import {
  listAdminUsers,
  createAdminUser,
  updateAdminUserRole,
  listAuditLogs,
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

  useEffect(() => {
    if (activeTab === 'users') {
      loadUsers();
    } else {
      loadAuditLogs();
    }
  }, [activeTab, auditDays]);

  const loadUsers = async () => {
    setLoading(true);
    try {
      const data = await listAdminUsers();
      setUsers(data);
    } catch (e: any) {
      setError(e.message || 'Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  const loadAuditLogs = async () => {
    setLoading(true);
    try {
      const data = await listAuditLogs({ days: auditDays, limit: 200 });
      setAuditLogs(data);
    } catch (e: any) {
      setError(e.message || 'Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell pageTitle="Admin">
      <div className="p-6 space-y-6">
        {/* Tabs */}
        <div className="flex gap-2 border-b border-slate-700">
          <button
            onClick={() => setActiveTab('users')}
            className={`px-4 py-2 font-medium ${
              activeTab === 'users'
                ? 'text-cyan-400 border-b-2 border-cyan-400'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Users
          </button>
          <button
            onClick={() => setActiveTab('audit')}
            className={`px-4 py-2 font-medium ${
              activeTab === 'audit'
                ? 'text-cyan-400 border-b-2 border-cyan-400'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Audit Log
          </button>
        </div>

        {error && (
          <div className="bg-red-900/20 border border-red-500/50 text-red-200 px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

        {/* Users Tab */}
        {activeTab === 'users' && (
          <div>
            <div className="flex justify-between items-center mb-4">
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
                    className="bg-slate-800/50 border border-slate-700 rounded-lg p-4 flex justify-between items-center"
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

        {/* Audit Log Tab */}
        {activeTab === 'audit' && (
          <div>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-slate-100">Audit Log</h3>
              <div className="flex gap-2">
                {[7, 30, 90].map((d) => (
                  <Button
                    key={d}
                    size="sm"
                    variant={auditDays === d ? "default" : "outline"}
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
              <div className="space-y-2 max-h-[600px] overflow-y-auto">
                {auditLogs.map((log) => (
                  <div
                    key={log.id}
                    className="bg-slate-800/50 border border-slate-700 rounded-lg p-3 text-sm"
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <div className="font-medium text-cyan-400">{log.action}</div>
                        <div className="text-xs text-slate-500 mt-1">
                          {log.entity_type} {log.entity_id ? `• ${log.entity_id.substring(0, 8)}` : ''}
                        </div>
                        {Object.keys(log.event_metadata || {}).length > 0 && (
                          <div className="text-xs text-slate-400 mt-1">
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
    </AppShell>
  );
}

