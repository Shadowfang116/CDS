"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { SetPageChrome } from "@/components/layout/set-page-chrome";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import {
  getDashboardAnalytics,
  getDashboardSummary,
  listAdminUsers,
  listAuditLogs,
  listWebhooks,
  AdminUser,
  AuditLogEntry,
  DashboardAnalyticsResponse,
  DashboardSummaryResponse,
  WebhookEndpoint,
} from "@/lib/api";

const TABS = [
  { id: "users", label: "Users" },
  { id: "audit", label: "Audit" },
  { id: "integrations", label: "Integrations" },
  { id: "portfolio", label: "Portfolio" },
] as const;

export function GovernanceView() {
  const searchParams = useSearchParams();
  const tab = searchParams.get("tab") || "users";
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [audit, setAudit] = useState<AuditLogEntry[]>([]);
  const [webhooks, setWebhooks] = useState<WebhookEndpoint[]>([]);
  const [summary, setSummary] = useState<DashboardSummaryResponse | null>(null);
  const [analytics, setAnalytics] = useState<DashboardAnalyticsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      if (tab === "users") setUsers(await listAdminUsers());
      if (tab === "audit") setAudit(await listAuditLogs({ days: 7, limit: 200 }));
      if (tab === "integrations") {
        const data = await listWebhooks();
        setWebhooks(Array.isArray(data) ? data : []);
      }
      if (tab === "portfolio") {
        const [nextSummary, nextAnalytics] = await Promise.all([getDashboardSummary(), getDashboardAnalytics(30)]);
        setSummary(nextSummary);
        setAnalytics(nextAnalytics);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load governance");
    }
  }, [tab]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-6 px-6 py-6">
      <SetPageChrome title="Governance" subtitle="Users, audit, integrations, and portfolio reports" />
      <nav className="flex gap-4 border-b border-border pb-2 text-sm">
        {TABS.map((item) => (
          <Link
            key={item.id}
            href={`/governance?tab=${item.id}`}
            className={tab === item.id ? "text-foreground" : "text-muted-foreground"}
          >
            {item.label}
          </Link>
        ))}
      </nav>
      {error ? <p className="text-sm text-foreground">{error}</p> : null}

      {tab === "users" ? (
        users.length === 0 ? (
          <EmptyState title="No users" />
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="text-[11px] uppercase tracking-[0.12em] text-muted-foreground">
              <tr>
                <th className="pb-2 font-medium">Email</th>
                <th className="pb-2 font-medium">Role</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id ?? user.email} className="border-t border-border">
                  <td className="py-2">{user.email}</td>
                  <td className="py-2">{user.role}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )
      ) : null}

      {tab === "audit" ? (
        <ul className="space-y-2 text-sm">
          {audit.map((entry) => (
            <li key={entry.id} className="border-b border-border py-2">
              <span className="cds-meta">{entry.created_at}</span>
              <p>{entry.action}</p>
            </li>
          ))}
        </ul>
      ) : null}

      {tab === "integrations" ? (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">Webhook endpoints. Full email templates remain on the integrations API.</p>
          {webhooks.map((hook) => (
            <p key={hook.id} className="text-sm">
              {hook.name} · {hook.is_enabled ? "on" : "off"}
            </p>
          ))}
          <Button asChild variant="outline" size="sm">
            <Link href="/integrations">Open full integrations</Link>
          </Button>
        </div>
      ) : null}

      {tab === "portfolio" ? (
        <div className="space-y-4 text-sm">
          <p className="text-muted-foreground">Portfolio analytics moved here so Inbox can stay the daily home.</p>
          {summary ? (
            <div className="grid gap-4 sm:grid-cols-3">
              <div>
                <p className="cds-meta">Open matters</p>
                <p className="text-2xl tabular">{summary.kpis.active_cases}</p>
              </div>
              <div>
                <p className="cds-meta">High exceptions</p>
                <p className="text-2xl tabular">{summary.kpis.open_high_exceptions}</p>
              </div>
              <div>
                <p className="cds-meta">Ready</p>
                <p className="text-2xl tabular">{summary.ready_for_approval_count}</p>
              </div>
            </div>
          ) : null}
          {analytics ? <p className="text-muted-foreground">Cohort window loaded ({analytics.range_days} days).</p> : null}
        </div>
      ) : null}
    </div>
  );
}
