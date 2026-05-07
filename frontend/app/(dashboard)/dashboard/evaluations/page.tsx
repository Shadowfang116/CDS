"use client";

import * as React from "react";
import Link from "next/link";
import { BarChart2, CheckCircle, XCircle, AlertCircle } from "lucide-react";
import { SetPageChrome } from "@/components/layout/set-page-chrome";
import { Card, CardContent, MetricCard } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { listCasesPaginated } from "@/lib/api";
import { getCaseDetailPath } from "@/lib/routes";
import type { CaseListItem } from "@/types/cases";

function pct(value: number | null): string {
  if (value === null || value === undefined) return "—";
  return `${Math.round(value * 100)}%`;
}

function RecallBadge({ value }: { value: number | null }) {
  if (value === null || value === undefined) {
    return <Badge variant="neutral">—</Badge>;
  }
  const pctVal = value * 100;
  if (pctVal >= 80) return <Badge variant="success">{Math.round(pctVal)}%</Badge>;
  if (pctVal >= 50) return <Badge variant="warning">{Math.round(pctVal)}%</Badge>;
  return <Badge variant="error">{Math.round(pctVal)}%</Badge>;
}

interface CaseEvalSummary {
  case: CaseListItem;
  critical_recall: number | null;
  overall_recall: number | null;
  precision: number | null;
  matched: number;
  missed: number;
  extra: number;
  status: string;
  run_id: string | null;
}

async function fetchCaseEvals(cases: CaseListItem[]): Promise<CaseEvalSummary[]> {
  const results = await Promise.allSettled(
    cases.map(async (c) => {
      try {
        const { getLatestEvaluationRun } = await import("@/lib/api");
        const run = await getLatestEvaluationRun(String(c.id));
        return {
          case: c,
          critical_recall: run.critical_recall,
          overall_recall: run.overall_recall,
          precision: run.precision,
          matched: run.matched_count,
          missed: run.missed_count,
          extra: run.extra_count,
          status: run.status,
          run_id: run.id,
        } as CaseEvalSummary;
      } catch {
        return {
          case: c,
          critical_recall: null,
          overall_recall: null,
          precision: null,
          matched: 0,
          missed: 0,
          extra: 0,
          status: "none",
          run_id: null,
        } as CaseEvalSummary;
      }
    })
  );

  return results.map((r, i) =>
    r.status === "fulfilled"
      ? r.value
      : {
          case: cases[i],
          critical_recall: null,
          overall_recall: null,
          precision: null,
          matched: 0,
          missed: 0,
          extra: 0,
          status: "none",
          run_id: null,
        }
  );
}

function EvaluationsPageContent() {
  const [summaries, setSummaries] = React.useState<CaseEvalSummary[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    listCasesPaginated({ page: 1, page_size: 50, sort: "updated_at", order: "desc" })
      .then((res) => fetchCaseEvals(res.items))
      .then((data) => {
        if (!cancelled) {
          setSummaries(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err?.message ?? "Failed to load evaluation data");
          setLoading(false);
        }
      });

    return () => { cancelled = true; };
  }, []);

  const evaluated = summaries.filter((s) => s.run_id !== null);
  const avgCriticalRecall =
    evaluated.length > 0
      ? evaluated.reduce((sum, s) => sum + (s.critical_recall ?? 0), 0) / evaluated.length
      : null;
  const avgOverallRecall =
    evaluated.length > 0
      ? evaluated.reduce((sum, s) => sum + (s.overall_recall ?? 0), 0) / evaluated.length
      : null;
  const totalMissed = evaluated.reduce((sum, s) => sum + s.missed, 0);

  if (loading) {
    return (
      <div className="p-6 space-y-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Card key={i} className="animate-pulse h-24" />
          ))}
        </div>
        <Card className="animate-pulse h-64" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <EmptyState
          icon={<AlertCircle className="h-8 w-8 text-red-400" />}
          title="Failed to load evaluations"
          message={error}
        />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6" data-dashboard-reveal>
      {/* Summary metric cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3" data-dashboard-section>
        <MetricCard
          title="Avg. Critical Recall"
          value={pct(avgCriticalRecall)}
          subtitle={`${evaluated.length} evaluated case${evaluated.length !== 1 ? "s" : ""}`}
        />
        <MetricCard
          title="Avg. Overall Recall"
          value={pct(avgOverallRecall)}
          subtitle="Matched expected findings"
        />
        <MetricCard
          title="Total Missed Critical"
          value={String(totalMissed)}
          subtitle="Across all evaluated cases"
        />
      </div>

      {/* Per-case table */}
      <Card data-dashboard-section>
        <CardContent className="p-0">
          {summaries.length === 0 ? (
            <EmptyState
              icon={<BarChart2 className="h-8 w-8 text-muted-foreground" />}
              title="No cases found"
              message="Create cases to begin evaluation."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-muted-foreground text-xs uppercase tracking-wide">
                    <th className="text-left px-4 py-3 font-medium">Case</th>
                    <th className="text-left px-4 py-3 font-medium">Critical Recall</th>
                    <th className="text-left px-4 py-3 font-medium">Overall Recall</th>
                    <th className="text-left px-4 py-3 font-medium">Precision</th>
                    <th className="text-right px-4 py-3 font-medium">Matched</th>
                    <th className="text-right px-4 py-3 font-medium">Missed</th>
                    <th className="text-right px-4 py-3 font-medium">Extra</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {summaries.map((s) => (
                    <tr key={String(s.case.id)} className="hover:bg-muted/30 transition-colors">
                      <td className="px-4 py-3">
                        <div className="font-medium text-stone-100 truncate max-w-[220px]">
                          {s.case.title ?? "Untitled"}
                        </div>
                        <div className="text-xs text-muted-foreground font-mono">
                          {String(s.case.id).slice(0, 8)}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        {s.run_id ? <RecallBadge value={s.critical_recall} /> : <Badge variant="neutral">No run</Badge>}
                      </td>
                      <td className="px-4 py-3">
                        {s.run_id ? <RecallBadge value={s.overall_recall} /> : <span className="text-muted-foreground">—</span>}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {s.run_id ? pct(s.precision) : "—"}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {s.run_id ? (
                          <span className="text-green-400 font-medium">{s.matched}</span>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {s.run_id ? (
                          <span className={s.missed > 0 ? "text-red-400 font-medium" : "text-muted-foreground"}>
                            {s.missed}
                          </span>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {s.run_id ? (
                          <span className={s.extra > 0 ? "text-amber-400 font-medium" : "text-muted-foreground"}>
                            {s.extra}
                          </span>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Link
                          href={`/dashboard/cases/${s.case.id}/evaluation`}
                          className="text-xs text-blue-400 hover:text-blue-300 underline-offset-2 hover:underline"
                        >
                          View
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function EvaluationsPage() {
  return (
    <>
      <SetPageChrome
        title="Evaluations"
        breadcrumbs={[{ label: "Evaluations" }]}
      />
      <React.Suspense
        fallback={
          <div className="p-6 space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {[0, 1, 2].map((i) => <Card key={i} className="animate-pulse h-24" />)}
            </div>
          </div>
        }
      >
        <EvaluationsPageContent />
      </React.Suspense>
    </>
  );
}
