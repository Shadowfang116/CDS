'use client';

import { useState, useEffect, useCallback } from 'react';
import { AppShell } from '@/components/app/AppShell';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/ui/empty-state';
import {
  listWebhooks,
  createWebhook,
  updateWebhook,
  deleteWebhook,
  listWebhookDeliveries,
  testWebhook,
  listEmailTemplates,
  createEmailTemplate,
  updateEmailTemplate,
  listEmailDeliveries,
  testEmail,
  getMe,
  ApiError,
  WebhookEndpoint,
  WebhookDelivery,
  EmailTemplate,
  EmailDelivery,
} from '@/lib/api';

type TabValue = 'webhooks' | 'email';

const VALID_EVENTS = ['approval.pending', 'approval.decided', 'case.decided', 'export.generated'];
const TEMPLATE_KEYS = ['approval.pending', 'approval.decided', 'case.decided', 'export.generated'];

export default function IntegrationsPage() {
  const [activeTab, setActiveTab] = useState<TabValue>('webhooks');
  const [webhooks, setWebhooks] = useState<WebhookEndpoint[]>([]);
  const [emailTemplates, setEmailTemplates] = useState<EmailTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createModal, setCreateModal] = useState<{ type: 'webhook' | 'email'; show: boolean }>({ type: 'webhook', show: false });
  const [selectedEndpoint, setSelectedEndpoint] = useState<string | null>(null);
  const [deliveries, setDeliveries] = useState<WebhookDelivery[] | EmailDelivery[]>([]);
  const [secretModal, setSecretModal] = useState<{ show: boolean; secret: string }>({ show: false, secret: '' });

  const fetchWebhooks = useCallback(async () => {
    try {
      const data = await listWebhooks();
      setWebhooks(data);
    } catch (e: any) {
      setError(e.message || 'Failed to load webhooks');
    }
  }, []);

  const fetchEmailTemplates = useCallback(async () => {
    try {
      const data = await listEmailTemplates();
      setEmailTemplates(data);
    } catch (e: any) {
      setError(e.message || 'Failed to load email templates');
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchWebhooks(), fetchEmailTemplates()]).finally(() => setLoading(false));
  }, [fetchWebhooks, fetchEmailTemplates]);

  const handleCreateWebhook = async (name: string, url: string, events: string[]) => {
    try {
      const result = await createWebhook({ name, url, subscribed_events: events });
      setSecretModal({ show: true, secret: result.secret });
      await fetchWebhooks();
      setCreateModal({ type: 'webhook', show: false });
    } catch (e: any) {
      setError(e.message || 'Failed to create webhook');
    }
  };

  const handleDeleteWebhook = async (id: string) => {
    if (!confirm('Delete this webhook endpoint?')) return;
    try {
      await deleteWebhook(id);
      await fetchWebhooks();
    } catch (e: any) {
      setError(e.message || 'Failed to delete webhook');
    }
  };

  const handleTestWebhook = async (id: string) => {
    try {
      await testWebhook(id);
      alert('Test event emitted');
    } catch (e: any) {
      setError(e.message || 'Failed to test webhook');
    }
  };

  const handleTestEmail = async () => {
    try {
      const result = await testEmail();
      alert(`Test email sent to ${result.to_email}`);
    } catch (e: any) {
      setError(e.message || 'Failed to send test email');
    }
  };

  const maskUrl = (url: string) => {
    try {
      const u = new URL(url);
      return `${u.protocol}//${u.hostname}${u.pathname.length > 20 ? '...' : u.pathname}`;
    } catch {
      return url.length > 30 ? url.substring(0, 30) + '...' : url;
    }
  };

  return (
    <AppShell pageTitle="Integrations">
      <div className="p-6 space-y-6">
        {/* Tabs */}
        <div className="flex gap-2 border-b border-slate-700">
          <button
            onClick={() => setActiveTab('webhooks')}
            className={`px-4 py-2 font-medium ${
              activeTab === 'webhooks'
                ? 'text-cyan-400 border-b-2 border-cyan-400'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Webhooks
          </button>
          <button
            onClick={() => setActiveTab('email')}
            className={`px-4 py-2 font-medium ${
              activeTab === 'email'
                ? 'text-cyan-400 border-b-2 border-cyan-400'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Email Templates
          </button>
        </div>

        {error && (
          <div className="bg-red-900/20 border border-red-500/50 text-red-200 px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

        {/* Webhooks Tab */}
        {activeTab === 'webhooks' && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-semibold text-slate-100">Webhook Endpoints</h3>
              <Button onClick={() => setCreateModal({ type: 'webhook', show: true })}>
                Create Webhook
              </Button>
            </div>

            {loading ? (
              <Skeleton className="h-32 w-full" />
            ) : webhooks.length === 0 ? (
              <EmptyState message="No webhook endpoints configured" />
            ) : (
              <div className="space-y-3">
                {webhooks.map((webhook) => (
                  <div
                    key={webhook.id}
                    className="bg-slate-800/50 border border-slate-700 rounded-lg p-4 space-y-2"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="font-medium text-slate-100">{webhook.name}</h4>
                          <Badge variant={webhook.is_enabled ? 'success' : 'secondary'}>
                            {webhook.is_enabled ? 'Enabled' : 'Disabled'}
                          </Badge>
                        </div>
                        <p className="text-sm text-slate-400 mt-1">{maskUrl(webhook.url)}</p>
                        <p className="text-xs text-slate-500 mt-1">
                          Secret: ••••{webhook.secret_preview}
                        </p>
                        <div className="flex gap-2 mt-2">
                          {webhook.subscribed_events.map((e) => (
                            <Badge key={e} variant="outline" className="text-xs">
                              {e}
                            </Badge>
                          ))}
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            setSelectedEndpoint(webhook.id);
                            listWebhookDeliveries(webhook.id).then(setDeliveries);
                          }}
                        >
                          View Deliveries
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => handleTestWebhook(webhook.id)}>
                          Test
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => updateWebhook(webhook.id, { is_enabled: !webhook.is_enabled }).then(fetchWebhooks)}
                        >
                          {webhook.is_enabled ? 'Disable' : 'Enable'}
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => handleDeleteWebhook(webhook.id)}
                        >
                          Delete
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Email Tab */}
        {activeTab === 'email' && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-semibold text-slate-100">Email Templates</h3>
              <Button onClick={handleTestEmail}>Send Test Email</Button>
            </div>

            {loading ? (
              <Skeleton className="h-32 w-full" />
            ) : (
              <div className="space-y-3">
                {TEMPLATE_KEYS.map((key) => {
                  const template = emailTemplates.find((t) => t.template_key === key);
                  return (
                    <div
                      key={key}
                      className="bg-slate-800/50 border border-slate-700 rounded-lg p-4 space-y-2"
                    >
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <h4 className="font-medium text-slate-100">{key}</h4>
                            {template && (
                              <Badge variant={template.is_enabled ? 'success' : 'secondary'}>
                                {template.is_enabled ? 'Enabled' : 'Disabled'}
                              </Badge>
                            )}
                          </div>
                          {template ? (
                            <div className="mt-2 space-y-1">
                              <p className="text-sm text-slate-300">Subject: {template.subject}</p>
                              <p className="text-xs text-slate-400 line-clamp-2">{template.body_md}</p>
                            </div>
                          ) : (
                            <p className="text-sm text-slate-500 mt-1">No template configured</p>
                          )}
                        </div>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            // In a real implementation, open an editor modal
                            alert('Template editor would open here');
                          }}
                        >
                          {template ? 'Edit' : 'Create'}
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            <div className="mt-6">
              <h4 className="text-md font-semibold text-slate-100 mb-2">Recent Deliveries</h4>
              {loading ? (
                <Skeleton className="h-24 w-full" />
              ) : (
                <EmailDeliveriesList />
              )}
            </div>
          </div>
        )}

        {/* Secret Modal */}
        {secretModal.show && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
            <div className="bg-slate-800 border border-slate-700 rounded-lg p-6 max-w-md w-full mx-4">
              <h3 className="text-lg font-semibold text-slate-100 mb-2">Webhook Secret</h3>
              <p className="text-sm text-slate-400 mb-4">
                Save this secret now. It will not be shown again.
              </p>
              <div className="bg-slate-900 p-3 rounded border border-slate-700 mb-4">
                <code className="text-sm text-cyan-400 break-all">{secretModal.secret}</code>
              </div>
              <div className="flex gap-2">
                <Button
                  onClick={() => {
                    navigator.clipboard.writeText(secretModal.secret);
                    alert('Copied to clipboard');
                  }}
                  className="flex-1"
                >
                  Copy
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setSecretModal({ show: false, secret: '' })}
                  className="flex-1"
                >
                  Close
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}

function EmailDeliveriesList() {
  const [deliveries, setDeliveries] = useState<EmailDelivery[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [userRole, setUserRole] = useState<string | null>(null);
  const [checkingRole, setCheckingRole] = useState(true);

  // Check user role first (Admin only)
  useEffect(() => {
    getMe()
      .then((user) => {
        setUserRole(user.role || null);
        setCheckingRole(false);
        
        // Only fetch deliveries if user is Admin
        if (user.role === 'Admin') {
          return listEmailDeliveries(50);
        } else {
          setError('This page is restricted to Admin users.');
          return [];
        }
      })
      .then((data) => {
        if (Array.isArray(data)) {
          setDeliveries(data);
        }
      })
      .catch((e: any) => {
        // Handle ApiError gracefully
        if (e instanceof ApiError) {
          if (e.status === 403 || e.status === 401) {
            setError('This page is restricted to Admin users.');
          } else {
            setError(e.detail || `Failed to load email deliveries: ${e.message}`);
          }
        } else {
          setError(e.message || 'Failed to load email deliveries');
        }
      })
      .finally(() => {
        setLoading(false);
        setCheckingRole(false);
      });
  }, []);

  if (checkingRole || loading) return <Skeleton className="h-24 w-full" />;
  
  // Show error message (including "Admin only" message) instead of crashing
  if (error) {
    return (
      <div className="bg-slate-800/30 border border-slate-700 rounded p-4 text-center">
        <p className="text-slate-300">{error}</p>
      </div>
    );
  }
  
  if (deliveries.length === 0) return <EmptyState message="No email deliveries yet" />;

  return (
    <div className="space-y-2">
      {deliveries.slice(0, 10).map((d) => (
        <div key={d.id} className="bg-slate-800/30 border border-slate-700 rounded p-3 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-300">{d.to_email}</span>
            <Badge variant={d.status === 'Success' ? 'success' : 'destructive'}>{d.status}</Badge>
          </div>
          <p className="text-xs text-slate-500 mt-1">{d.subject}</p>
          <p className="text-xs text-slate-600 mt-1">{new Date(d.created_at).toLocaleString()}</p>
        </div>
      ))}
    </div>
  );
}

