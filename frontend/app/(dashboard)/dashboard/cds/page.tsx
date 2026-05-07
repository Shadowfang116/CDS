"use client";

import * as React from "react";
import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Clock,
  FileStack,
  Gauge,
  RefreshCw,
  ShieldAlert,
  TrendingUp,
  Zap,
} from "lucide-react";
import {
  AreaChart,
  Area,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
} from "recharts";
import { SetPageChrome } from "@/components/layout/set-page-chrome";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  getDashboardSummary,
  getDashboardAnalytics,
  type DashboardSummaryResponse,
  type DashboardAnalyticsResponse,
  type NeedsAttentionItem,
  type ActivityItem,
  type TimeseriesEntry,
} from "@/lib/api";

// ─── helpers ────────────────────────────────────────────────────────────────

function fmtPct(v: number): string {
  return `${Math.round(v)}%`;
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function actionLabel(action: string): string {
  return action
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function statusColor(status: string): string {
  switch (status?.toLowerCase()) {
    case "open":
    case "active":
      return "text-blue-400";
    case "review":
    case "pending":
      return "text-amber-400";
    case "closed":
    case "approved":
      return "text-green-400";
    case "processing":
      return "text-violet-400";
    default:
      return "text-stone-400";
  }
}

function statusBadgeVariant(status: string): "success" | "warning" | "error" | "neutral" {
  switch (status?.toLowerCase()) {
    case "closed":
    case "approved":
      return "success";
    case "review":
    case "pending":
      return "warning";
    case "open":
      return "neutral";
    default:
      return "neutral";
  }
}

// ─── sub-components ─────────────────────────────────────────────────────────

function BriefingCard({
  icon,
  label,
  value,
  sub,
  accent,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  sub?: string;
  accent?: string;
}) {
  return (
    <div className="flex flex-col gap-1 rounded-lg border border-border bg-[rgba(28,32,38,0.7)] px-4 py-3">
      <div className="flex items-center gap-2 text-xs text-muted-foreground uppercase tracking-wide">
        <span className={accent ?? "text-stone-400"}>{icon}</span>
        {label}
      </div>
      <div className={`text-2xl font-semibold tabular-nums ${accent ?? "text-stone-100"}`}>
        {value}
      </div>
      {sub && <div className="text-xs text-muted-foreground">{sub}</div>}
    </div>
  );
}

function SectionHeader({ title, icon }: { title: string; icon: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <span className="text-stone-400">{icon}</span>
      <span className="text-xs font-semibold uppercase tracking-widest text-stone-400">{title}</span>
    </div>
  );
}

function Sparkline({ data }: { data: TimeseriesEntry[] }) {
  if (!data?.length) return null;
  return (
    <ResponsiveContainer width="100%" height={60}>
      <AreaChart data={data} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="cdsGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#818cf8" stopOpacity={0.25} />
            <stop offset="95%" stopColor="#818cf8" stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis dataKey="date" hide />
        <RechartsTooltip
          contentStyle={{
            background: "rgba(20,24,30,0.95)",
            border: "1px solid rgba(82,90,99,0.4)",
            borderRadius: 6,
            fontSize: 11,
          }}
          labelStyle={{ color: "#a8b3cf" }}
          itemStyle={{ color: "#818cf8" }}
        />
        <Area
          type="monotone"
          dataKey="cases_created"
          stroke="#818cf8"
          strokeWidth={1.5}
          fill="url(#cdsGrad)"
          dot={false}
          name="Cases"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function PipelineStatusRow({
  label,
  count,
  total,
  color,
}: {
  label: string;
  count: number;
  total: number;
  color: string;
}) {
  const pct = total > 0 ? (count / total) * 100 : 0;
  return (
    <div className="flex items-center gap-3">
      <div className="w-28 text-xs text-stone-400 capitalize">{label}</div>
      <div className="flex-1 h-1.5 rounded-full bg-stone-800 overflow-hidden">
        <div
          className={`h-full rounded-full ${color} transition-all`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="w-8 text-right text-xs tabular-nums text-stone-300">{count}</div>
    </div>
  );
}

function NeedsAttentionRow({ item }: { item: NeedsAttentionItem }) {
  return (
    <Link
      href={`/dashboard/cases/${item.case_id}`}
      className="flex items-center gap-3 px-4 py-2.5 hover:bg-white/5 transition-colors group"
    >
      <div className="flex-1 min-w-0">
        <div className="text-sm text-stone-200 truncate group-hover:text-stone-100">
          {item.title ?? "Untitled"}
        </div>
        <div className="flex items-center gap-2 mt-0.5">
          <Badge variant={statusBadgeVariant(item.status)} className="text-[10px] px-1.5 py-0">
            {item.status}
          </Badge>
          {item.open_high > 0 && (
            <span className="text-[10px] text-red-400 font-medium">{item.open_high} high</span>
          )}
          {item.pending_verifications > 0 && (
            <span className="text-[10px] text-amber-400">{item.pending_verifications} verif.</span>
          )}
        </div>
      </div>
      <ChevronRight className="h-3.5 w-3.5 text-stone-600 group-hover:text-stone-400 shrink-0" />
    </Link>
  );
}

function ActivityRow({ item }: { item: ActivityItem }) {
  return (
    <div className="flex items-start gap-3 px-4 py-2.5 border-b border-border/50 last:border-0">
      <div className="mt-0.5 h-1.5 w-1.5 rounded-full bg-indigo-500 shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="text-xs text-stone-300 leading-snug">
          <span className="font-medium text-stone-200">{item.actor_email ?? "System"}</span>
          {" — "}
          {actionLabel(item.action)}
          {item.case_title && (
            <span className="text-stone-500"> on {item.case_title}</span>
          )}
        </div>
        <div className="text-[10px] text-stone-600 mt-0.5">{relativeTime(item.created_at)}</div>
      </div>
    </div>
  );
}

// ─── main content ────────────────────────────────────────────────────────────

function CDSContent() {
  const [summary, setSummary] = React.useState<DashboardSummaryResponse | null>(null);
  const [analytics, setAnalytics] = React.useState<DashboardAnalyticsResponse | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [lastRefresh, setLastRefresh] = React.useState<Date>(new Date());

  const load = React.useCallback(async () => {
    setLoading(true);
    const [s, a] = await Promise.allSettled([
      getDashboardSummary(30, true),
      getDashboardAnalytics(30, true),
    ]);
    if (s.status === "fulfilled") setSummary(s.value);
    if (a.status === "fulfilled") setAnalytics(a.value);
    setLastRefresh(new Date());
    setLoading(false);
  }, []);

  React.useEffect(() => {
    load();
  }, [load]);

  // Derived values
  const kpis = summary?.kpis;
  const casesByStatus = analytics?.cases_by_status ?? {};
  const totalCases = Object.values(casesByStatus).reduce((s, v) => s + v, 0);
  const exceptionsBySev = analytics?.exceptions_by_severity;
  const timeseries = analytics?.timeseries ?? [];
  const needsAttention = summary?.needs_attention ?? [];
  const recentActivity = summary?.recent_activity ?? [];

  const STATUS_COLORS: Record<string, string> = {
    open: "bg-blue-500",
    active: "bg-blue-500",
    processing: "bg-violet-500",
    review: "bg-amber-500",
    pending: "bg-amber-500",
    approved: "bg-green-500",
    closed: "bg-green-600",
  };

  return (
    <div className="p-5 space-y-5 min-h-screen" style={{ backgroundColor: "var(--bg-primary)" }} data-dashboard-reveal>
      {/* Header bar */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-stone-100 tracking-tight">
            CDS — Operations Dashboard
          </h1>
          <p className="text-xs text-stone-500 mt-0.5">
            30-day rolling window · Last refresh {relativeTime(lastRefresh.toISOString())}
          </p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-md border border-border bg-[rgba(28,32,38,0.7)] px-3 py-1.5 text-xs text-stone-400 hover:text-stone-200 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* ── Briefing bar ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5" data-dashboard-section>
        <BriefingCard
          icon={<FileStack className="h-3.5 w-3.5" />}
          label="Active Cases"
          value={loading ? "—" : (kpis?.active_cases ?? "—")}
          sub="under management"
          accent="text-blue-400"
        />
        <BriefingCard
          icon={<ShieldAlert className="h-3.5 w-3.5" />}
          label="High Exceptions"
          value={loading ? "—" : (kpis?.open_high_exceptions ?? "—")}
          sub="open · high severity"
          accent={kpis && kpis.open_high_exceptions > 0 ? "text-red-400" : "text-stone-400"}
        />
        <BriefingCard
          icon={<Clock className="h-3.5 w-3.5" />}
          label="Pending Verif."
          value={loading ? "—" : (kpis?.pending_verifications ?? "—")}
          sub="awaiting review"
          accent={kpis && kpis.pending_verifications > 0 ? "text-amber-400" : "text-stone-400"}
        />
        <BriefingCard
          icon={<Gauge className="h-3.5 w-3.5" />}
          label="Approvals Queue"
          value={loading ? "—" : (summary?.approvals_pending_count ?? "—")}
          sub="pending approval"
          accent={summary && summary.approvals_pending_count > 0 ? "text-violet-400" : "text-stone-400"}
        />
        <BriefingCard
          icon={<CheckCircle2 className="h-3.5 w-3.5" />}
          label="CP Completion"
          value={loading ? "—" : (kpis ? fmtPct(kpis.cp_completion_pct) : "—")}
          sub="conditions precedent"
          accent={kpis && kpis.cp_completion_pct >= 80 ? "text-green-400" : "text-amber-400"}
        />
      </div>

      {/* ── Main two-column ───────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3" data-dashboard-section>
        {/* Left column – Pipeline + Attention */}
        <div className="space-y-5 lg:col-span-2">

          {/* Processing Pipeline */}
          <Card className="bg-[rgba(18,22,28,0.85)] border-border">
            <CardContent className="p-4">
              <SectionHeader
                title="Processing Pipeline"
                icon={<Zap className="h-3.5 w-3.5" />}
              />
              {loading ? (
                <div className="space-y-2">
                  {[0, 1, 2, 3].map((i) => (
                    <div key={i} className="h-4 rounded bg-stone-800 animate-pulse" />
                  ))}
                </div>
              ) : totalCases === 0 ? (
                <p className="text-xs text-stone-500">No case data available.</p>
              ) : (
                <div className="space-y-2.5">
                  {Object.entries(casesByStatus)
                    .sort(([, a], [, b]) => b - a)
                    .map(([status, count]) => (
                      <PipelineStatusRow
                        key={status}
                        label={status}
                        count={count}
                        total={totalCases}
                        color={STATUS_COLORS[status.toLowerCase()] ?? "bg-stone-500"}
                      />
                    ))}
                  <div className="pt-1 border-t border-border/50 flex justify-between text-xs text-stone-500">
                    <span>Total</span>
                    <span className="tabular-nums text-stone-300">{totalCases}</span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Case Pipeline – Needs Attention */}
          <Card className="bg-[rgba(18,22,28,0.85)] border-border overflow-hidden">
            <div className="px-4 pt-4 pb-2">
              <SectionHeader
                title="Needs Attention"
                icon={<AlertTriangle className="h-3.5 w-3.5 text-amber-400" />}
              />
            </div>
            {loading ? (
              <div className="px-4 pb-4 space-y-2">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="h-10 rounded bg-stone-800 animate-pulse" />
                ))}
              </div>
            ) : needsAttention.length === 0 ? (
              <div className="px-4 pb-4 text-xs text-stone-500">All cases are on track.</div>
            ) : (
              <div className="divide-y divide-border/50">
                {needsAttention.slice(0, 8).map((item) => (
                  <NeedsAttentionRow key={item.case_id} item={item} />
                ))}
                {needsAttention.length > 8 && (
                  <div className="px-4 py-2.5 text-xs text-stone-500">
                    +{needsAttention.length - 8} more cases
                  </div>
                )}
              </div>
            )}
          </Card>
        </div>

        {/* Right column – Sparkline, Exceptions, Activity */}
        <div className="space-y-5">

          {/* Timeseries sparkline */}
          <Card className="bg-[rgba(18,22,28,0.85)] border-border">
            <CardContent className="p-4">
              <SectionHeader
                title="Case Volume (30d)"
                icon={<TrendingUp className="h-3.5 w-3.5" />}
              />
              {loading ? (
                <div className="h-14 rounded bg-stone-800 animate-pulse" />
              ) : timeseries.length === 0 ? (
                <p className="text-xs text-stone-500">No timeseries data.</p>
              ) : (
                <Sparkline data={timeseries} />
              )}
            </CardContent>
          </Card>

          {/* Exceptions by severity */}
          <Card className="bg-[rgba(18,22,28,0.85)] border-border">
            <CardContent className="p-4">
              <SectionHeader
                title="Exceptions by Severity"
                icon={<ShieldAlert className="h-3.5 w-3.5" />}
              />
              {loading ? (
                <div className="space-y-2">
                  {[0, 1, 2].map((i) => (
                    <div key={i} className="h-5 rounded bg-stone-800 animate-pulse" />
                  ))}
                </div>
              ) : !exceptionsBySev ? (
                <p className="text-xs text-stone-500">No data.</p>
              ) : (
                <div className="space-y-2.5">
                  {(
                    [
                      { key: "high", label: "High", color: "bg-red-500", text: "text-red-400" },
                      { key: "medium", label: "Medium", color: "bg-amber-500", text: "text-amber-400" },
                      { key: "low", label: "Low", color: "bg-blue-500", text: "text-blue-400" },
                    ] as const
                  ).map(({ key, label, color, text }) => {
                    const val = exceptionsBySev[key] ?? 0;
                    const total =
                      (exceptionsBySev.high ?? 0) +
                      (exceptionsBySev.medium ?? 0) +
                      (exceptionsBySev.low ?? 0);
                    return (
                      <div key={key} className="flex items-center gap-3">
                        <div className={`w-14 text-xs ${text}`}>{label}</div>
                        <div className="flex-1 h-1.5 rounded-full bg-stone-800 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${color}`}
                            style={{ width: total > 0 ? `${(val / total) * 100}%` : "0%" }}
                          />
                        </div>
                        <div className={`w-6 text-right text-xs tabular-nums ${text}`}>{val}</div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Live Activity Feed */}
          <Card className="bg-[rgba(18,22,28,0.85)] border-border overflow-hidden">
            <div className="px-4 pt-4 pb-2 flex items-center justify-between">
              <div>
                <SectionHeader
                  title="Live Activity Feed"
                  icon={<Activity className="h-3.5 w-3.5 text-indigo-400" />}
                />
              </div>
              <span className="text-[10px] text-stone-600 -mt-2">
                {recentActivity.length} events
              </span>
            </div>
            {loading ? (
              <div className="px-4 pb-4 space-y-2">
                {[0, 1, 2, 3].map((i) => (
                  <div key={i} className="h-8 rounded bg-stone-800 animate-pulse" />
                ))}
              </div>
            ) : recentActivity.length === 0 ? (
              <div className="px-4 pb-4 text-xs text-stone-500">No recent activity.</div>
            ) : (
              <div className="max-h-80 overflow-y-auto">
                {recentActivity.slice(0, 20).map((item, i) => (
                  <ActivityRow key={i} item={item} />
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}

// ─── page export ─────────────────────────────────────────────────────────────

export default function CDSPage() {
  return (
    <>
      <SetPageChrome
        title="CDS"
        breadcrumbs={[{ label: "CDS" }]}
      />
      <React.Suspense fallback={<div className="p-5 text-sm text-stone-500">Loading…</div>}>
        <CDSContent />
      </React.Suspense>
    </>
  );
}
