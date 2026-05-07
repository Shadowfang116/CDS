"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { AlertCircle, CheckCircle2, XCircle, MinusCircle, Plus, Trash2, Play } from "lucide-react";
import { SetPageChrome } from "@/components/layout/set-page-chrome";
import { Card, CardContent, CardHeader, CardTitle, MetricCard } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SeverityBadge as GlobalSeverityBadge } from "@/components/ui/severity-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/ui/empty-state";
import { getCaseDetailPath } from "@/lib/routes";
import {
  triggerEvaluationRun,
  getLatestEvaluationRun,
  listEvaluationHistory,
  listExpectations,
  createExpectation,
  deleteExpectation,
  ApiError,
  type EvaluationRun,
  type EvaluationFinding,
  type Expectation,
  type ExpectationCreate,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function pct(value: number | null): string {
  if (value === null || value === undefined) return "—";
  return `${Math.round(value * 100)}%`;
}

function durationLabel(ms: number | null): string {
  if (ms === null || ms === undefined) return "—";
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`;
}

function MatchBadge({ status }: { status: EvaluationFinding["match_status"] }) {
  if (status === "matched") return <Badge variant="success">Matched</Badge>;
  if (status === "missed") return <Badge variant="error">Missed</Badge>;
  return <Badge variant="warning">Extra</Badge>;
}

function FindingSeverityBadge({ severity }: { severity: string | null }) {
  if (!severity) return <span className="text-muted-foreground text-xs">-</span>;
  return <GlobalSeverityBadge severity={severity} />;
}

function RecallBar({ value, label }: { value: number | null; label: string }) {
  const pctVal = value !== null ? Math.round(value * 100) : null;
  const color =
    pctVal === null ? "bg-muted" : pctVal >= 80 ? "bg-green-500" : pctVal >= 50 ? "bg-amber-500" : "bg-red-500";

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>{label}</span>
        <span className="font-medium text-stone-200">{pct(value)}</span>
      </div>
      <div className="h-1.5 rounded-full bg-muted overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${color}`}
          style={{ width: pctVal !== null ? `${pctVal}%` : "0%" }}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Add Expectation Form
// ---------------------------------------------------------------------------

const SEVERITIES = ["High", "Medium", "Low"];

function AddExpectationForm({
  caseId,
  onCreated,
}: {
  caseId: string;
  onCreated: () => void;
}) {
  const [open, setOpen] = React.useState(false);
  const [saving, setSaving] = React.useState(false);
  const [form, setForm] = React.useState<ExpectationCreate>({
    finding_type: "exception",
    expected_title: "",
    expected_rule_id: "",
    expected_severity: "High",
    expected_text: "",
    is_critical: false,
    notes: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.expected_title.trim()) return;
    setSaving(true);
    try {
      await createExpectation(caseId, {
        ...form,
        expected_rule_id: form.expected_rule_id?.trim() || undefined,
        expected_text: form.expected_text?.trim() || undefined,
        notes: form.notes?.trim() || undefined,
      });
      setForm({
        finding_type: "exception",
        expected_title: "",
        expected_rule_id: "",
        expected_severity: "High",
        expected_text: "",
        is_critical: false,
        notes: "",
      });
      setOpen(false);
      onCreated();
    } catch {
      // keep form open
    } finally {
      setSaving(false);
    }
  };

  if (!open) {
    return (
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
        <Plus className="h-3.5 w-3.5 mr-1" /> Add Expected Finding
      </Button>
    );
  }

  return (
    <Card className="border-dashed">
      <CardContent className="pt-4">
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Type</label>
              <select
                value={form.finding_type}
                onChange={(e) => setForm((f) => ({ ...f, finding_type: e.target.value as "exception" | "cp" }))}
                className="w-full h-9 rounded-md border border-[rgba(82,90,99,0.55)] bg-[rgba(22,26,30,0.92)] px-3 text-sm text-stone-100 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="exception">Exception</option>
                <option value="cp">Condition Precedent</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Severity</label>
              <select
                value={form.expected_severity ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, expected_severity: e.target.value || undefined }))}
                className="w-full h-9 rounded-md border border-[rgba(82,90,99,0.55)] bg-[rgba(22,26,30,0.92)] px-3 text-sm text-stone-100 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="">— Any —</option>
                {SEVERITIES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Expected Title <span className="text-red-400">*</span></label>
            <Input
              value={form.expected_title}
              onChange={(e) => setForm((f) => ({ ...f, expected_title: e.target.value }))}
              placeholder="e.g. Sale deed not registered"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Rule ID (optional)</label>
              <Input
                value={form.expected_rule_id ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, expected_rule_id: e.target.value }))}
                placeholder="e.g. TITLE_001"
              />
            </div>
            <div className="space-y-1 flex items-end">
              <label className="flex items-center gap-2 text-sm text-stone-200 cursor-pointer pb-1">
                <input
                  type="checkbox"
                  checked={form.is_critical ?? false}
                  onChange={(e) => setForm((f) => ({ ...f, is_critical: e.target.checked }))}
                  className="rounded"
                />
                Critical finding
              </label>
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Expected Text (optional)</label>
            <textarea
              value={form.expected_text ?? ""}
              onChange={(e) => setForm((f) => ({ ...f, expected_text: e.target.value }))}
              rows={2}
              placeholder="Describe the expected finding text..."
              className="w-full rounded-md border border-[rgba(82,90,99,0.55)] bg-[rgba(22,26,30,0.92)] px-3 py-2 text-sm text-stone-100 resize-none focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div className="flex justify-end gap-2 pt-1">
            <Button type="button" variant="ghost" size="sm" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" size="sm" loading={saving}>
              Save Expectation
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Findings Table
// ---------------------------------------------------------------------------

function FindingsTable({ findings }: { findings: EvaluationFinding[] }) {
  const [filter, setFilter] = React.useState<"all" | "matched" | "missed" | "extra">("all");

  const visible = findings.filter((f) => filter === "all" || f.match_status === filter);

  const counts = {
    matched: findings.filter((f) => f.match_status === "matched").length,
    missed: findings.filter((f) => f.match_status === "missed").length,
    extra: findings.filter((f) => f.match_status === "extra").length,
  };

  return (
    <div className="space-y-3">
      {/* Filter tabs */}
      <div className="flex gap-1">
        {(["all", "matched", "missed", "extra"] as const).map((tab) => {
          const count = tab === "all" ? findings.length : counts[tab];
          const active = filter === tab;
          return (
            <button
              key={tab}
              onClick={() => setFilter(tab)}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                active
                  ? "bg-[rgba(82,90,99,0.5)] text-stone-100"
                  : "text-muted-foreground hover:text-stone-200 hover:bg-muted/40"
              }`}
            >
              {tab === "all" ? "All" : tab.charAt(0).toUpperCase() + tab.slice(1)} ({count})
            </button>
          );
        })}
      </div>

      {visible.length === 0 ? (
        <p className="text-sm text-muted-foreground py-4 text-center">No findings in this category.</p>
      ) : (
        <div className="overflow-x-auto rounded-md border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-muted-foreground text-xs uppercase tracking-wide bg-muted/20">
                <th className="text-left px-4 py-2.5 font-medium">Status</th>
                <th className="text-left px-4 py-2.5 font-medium">Type</th>
                <th className="text-left px-4 py-2.5 font-medium">Expected</th>
                <th className="text-left px-4 py-2.5 font-medium">Actual</th>
                <th className="text-left px-4 py-2.5 font-medium">Severity</th>
                <th className="text-left px-4 py-2.5 font-medium">Rule ID</th>
                <th className="text-right px-4 py-2.5 font-medium">Score</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {visible.map((f) => (
                <tr key={f.id} className="hover:bg-muted/20 transition-colors">
                  <td className="px-4 py-3">
                    <MatchBadge status={f.match_status} />
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant="neutral">
                      {f.finding_type === "exception" ? "Exception" : "CP"}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 max-w-[200px]">
                    {f.expected_title ? (
                      <div className="truncate text-stone-200">{f.expected_title}</div>
                    ) : (
                      <span className="text-muted-foreground text-xs">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 max-w-[200px]">
                    {f.actual_title || f.actual_text ? (
                      <div className="truncate text-stone-200">{f.actual_title ?? f.actual_text}</div>
                    ) : (
                      <span className="text-muted-foreground text-xs">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <FindingSeverityBadge severity={f.actual_severity ?? f.expected_severity} />
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                    {f.actual_rule_id ?? f.expected_rule_id ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-right text-xs text-muted-foreground">
                    {f.similarity_score !== null && f.similarity_score !== undefined
                      ? `${Math.round(f.similarity_score * 100)}%`
                      : f.match_status === "matched" && f.actual_rule_id === f.expected_rule_id
                      ? "Exact"
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function CaseEvaluationPage() {
  const params = useParams();
  const caseId = String(params.caseId);

  const [run, setRun] = React.useState<EvaluationRun | null>(null);
  const [expectations, setExpectations] = React.useState<Expectation[]>([]);
  const [history, setHistory] = React.useState<EvaluationRun[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [running, setRunning] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [isAdmin] = React.useState(() => {
    if (typeof window === "undefined") return false;
    try {
      const token = localStorage.getItem("token");
      if (!token) return false;
      const payload = JSON.parse(atob(token.split(".")[1]));
      return payload.role === "Admin";
    } catch {
      return false;
    }
  });

  const load = React.useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.allSettled([
      getLatestEvaluationRun(caseId).catch((err) => {
        if (err instanceof ApiError && err.status === 404) {
          return null;
        }
        throw err;
      }),
      listExpectations(caseId),
      listEvaluationHistory(caseId),
    ]).then(([runRes, expRes, histRes]) => {
      setRun(runRes.status === "fulfilled" ? runRes.value : null);
      setExpectations(expRes.status === "fulfilled" ? expRes.value : []);
      setHistory((histRes.status === "fulfilled" ? histRes.value : []) as EvaluationRun[]);
      if (runRes.status === "rejected") {
        setError(runRes.reason?.message ?? "Failed to load latest evaluation");
      }
      setLoading(false);
    });
  }, [caseId]);

  React.useEffect(() => { load(); }, [load]);

  const handleRun = async () => {
    setRunning(true);
    try {
      const newRun = await triggerEvaluationRun(caseId);
      setRun(newRun);
      setHistory((prev) => [newRun, ...prev]);
    } catch (err: any) {
      setError(err?.message ?? "Evaluation failed");
    } finally {
      setRunning(false);
    }
  };

  const handleDeleteExpectation = async (id: string) => {
    await deleteExpectation(id);
    setExpectations((prev) => prev.filter((e) => e.id !== id));
  };

  if (loading) {
    return (
      <>
        <SetPageChrome
          title="Evaluation"
          breadcrumbs={[
            { label: "Cases", href: "/dashboard/cases" },
            { label: "Evaluation" },
          ]}
        />
        <div className="p-6 space-y-4" data-dashboard-reveal>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
            {[0, 1, 2, 3].map((i) => <Card key={i} className="animate-pulse h-24" />)}
          </div>
          <Card className="animate-pulse h-64" />
        </div>
      </>
    );
  }

  const criticalExpectations = expectations.filter((e) => e.is_critical);

  return (
    <>
      <SetPageChrome
        title="Evaluation"
        breadcrumbs={[
          { label: "Cases", href: "/dashboard/cases" },
          { label: "Evaluation" },
        ]}
        actions={
          <Button size="sm" onClick={handleRun} loading={running} disabled={running}>
            <Play className="h-3.5 w-3.5 mr-1.5" />
            Run Evaluation
          </Button>
        }
      />

      <div className="p-6 space-y-6" data-dashboard-reveal>
        {error && (
          <div className="rounded-md border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {error}
          </div>
        )}

        {/* Metrics */}
        {run && run.status === "completed" ? (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4" data-dashboard-section>
            <MetricCard
              title="Critical Recall"
              value={pct(run.critical_recall)}
              subtitle={`${criticalExpectations.length} critical expected`}
            />
            <MetricCard
              title="Overall Recall"
              value={pct(run.overall_recall)}
              subtitle={`${run.matched_count} of ${run.expected_count} matched`}
            />
            <MetricCard
              title="Precision"
              value={pct(run.precision)}
              subtitle="Matched vs. total actual"
            />
            <MetricCard
              title="Processing Time"
              value={durationLabel(run.duration_ms)}
              subtitle={run.completed_at ? new Date(run.completed_at).toLocaleString() : ""}
            />
          </div>
        ) : run?.status === "failed" ? (
          <div className="rounded-md border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            Last run failed: {run.error_message ?? "Unknown error"}
          </div>
        ) : (
          <Card>
            <CardContent className="py-8">
              <EmptyState
                icon={<BarChart2Icon />}
                title="No evaluation run yet"
                message="Add expected findings below, then click Run Evaluation."
              />
            </CardContent>
          </Card>
        )}

        {/* Recall bars */}
        {run && run.status === "completed" && (
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Recall Overview</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <RecallBar value={run.critical_recall} label="Critical Recall" />
              <RecallBar value={run.overall_recall} label="Overall Recall" />
              <RecallBar value={run.precision} label="Precision" />
            </CardContent>
          </Card>
        )}

        {/* Findings table */}
        {run && run.findings && run.findings.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Findings</CardTitle>
            </CardHeader>
            <CardContent>
              <FindingsTable findings={run.findings} />
            </CardContent>
          </Card>
        )}

        {/* Expected Findings / Expectations */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-sm">
              Expected Findings
              {expectations.length > 0 && (
                <span className="ml-2 text-muted-foreground font-normal">({expectations.length})</span>
              )}
            </CardTitle>
            {isAdmin && (
              <AddExpectationForm caseId={caseId} onCreated={load} />
            )}
          </CardHeader>
          <CardContent>
            {expectations.length === 0 ? (
              <EmptyState
                title="No expected findings"
                message={
                  isAdmin
                    ? "Add expected findings using the button above to define the gold standard for this case."
                    : "No gold-standard expectations have been defined for this case."
                }
              />
            ) : (
              <div className="overflow-x-auto rounded-md border border-border">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-muted-foreground text-xs uppercase tracking-wide bg-muted/20">
                      <th className="text-left px-4 py-2.5 font-medium">Type</th>
                      <th className="text-left px-4 py-2.5 font-medium">Title</th>
                      <th className="text-left px-4 py-2.5 font-medium">Rule ID</th>
                      <th className="text-left px-4 py-2.5 font-medium">Severity</th>
                      <th className="text-left px-4 py-2.5 font-medium">Critical</th>
                      {isAdmin && <th className="px-4 py-2.5" />}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {expectations.map((exp) => (
                      <tr key={exp.id} className="hover:bg-muted/20 transition-colors">
                        <td className="px-4 py-3">
                          <Badge variant="neutral">
                            {exp.finding_type === "exception" ? "Exception" : "CP"}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-stone-200 max-w-[240px] truncate">
                          {exp.expected_title}
                        </td>
                        <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                          {exp.expected_rule_id ?? "—"}
                        </td>
                        <td className="px-4 py-3">
                          <FindingSeverityBadge severity={exp.expected_severity} />
                        </td>
                        <td className="px-4 py-3">
                          {exp.is_critical ? (
                            <Badge variant="error">Critical</Badge>
                          ) : (
                            <span className="text-muted-foreground text-xs">—</span>
                          )}
                        </td>
                        {isAdmin && (
                          <td className="px-4 py-3 text-right">
                            <button
                              onClick={() => handleDeleteExpectation(exp.id)}
                              className="text-muted-foreground hover:text-red-400 transition-colors"
                              title="Remove expectation"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Run History */}
        {history.length > 1 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Evaluation History</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto rounded-md border border-border">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-muted-foreground text-xs uppercase tracking-wide bg-muted/20">
                      <th className="text-left px-4 py-2.5 font-medium">Date</th>
                      <th className="text-left px-4 py-2.5 font-medium">Status</th>
                      <th className="text-right px-4 py-2.5 font-medium">Critical Recall</th>
                      <th className="text-right px-4 py-2.5 font-medium">Overall Recall</th>
                      <th className="text-right px-4 py-2.5 font-medium">Matched</th>
                      <th className="text-right px-4 py-2.5 font-medium">Missed</th>
                      <th className="text-right px-4 py-2.5 font-medium">Processing Time</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {history.map((h) => (
                      <tr key={h.id} className="hover:bg-muted/20 transition-colors">
                        <td className="px-4 py-3 text-muted-foreground text-xs">
                          {new Date(h.started_at).toLocaleString()}
                        </td>
                        <td className="px-4 py-3">
                          {h.status === "completed" ? (
                            <Badge variant="success">Completed</Badge>
                          ) : h.status === "failed" ? (
                            <Badge variant="error">Failed</Badge>
                          ) : (
                            <Badge variant="neutral">Running</Badge>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right text-muted-foreground">{pct(h.critical_recall)}</td>
                        <td className="px-4 py-3 text-right text-muted-foreground">{pct(h.overall_recall)}</td>
                        <td className="px-4 py-3 text-right text-green-400">{h.matched_count}</td>
                        <td className="px-4 py-3 text-right">
                          <span className={h.missed_count > 0 ? "text-red-400" : "text-muted-foreground"}>
                            {h.missed_count}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right text-muted-foreground text-xs">
                          {durationLabel(h.duration_ms)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </>
  );
}

function BarChart2Icon() {
  return <div className="h-8 w-8 text-muted-foreground">📊</div>;
}

