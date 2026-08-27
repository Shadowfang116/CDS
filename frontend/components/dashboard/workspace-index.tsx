"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getDashboardSummary, type DashboardSummaryResponse } from "@/lib/api";
import { SetPageChrome } from "@/components/layout/set-page-chrome";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";

type WorkspaceSurface = "documents" | "issues" | "requirements";

const SURFACE_COPY: Record<WorkspaceSurface, { title: string; description: string }> = {
  documents: {
    title: "Documents",
    description: "See matters with documents still being analyzed or needing review.",
  },
  issues: {
    title: "Issues",
    description: "See matters where evidence, facts, or review items need attention.",
  },
  requirements: {
    title: "Approval requirements",
    description: "See approval requests and matters moving toward a decision.",
  },
};

export function WorkspaceIndex({ surface }: { surface: WorkspaceSurface }) {
  const [summary, setSummary] = useState<DashboardSummaryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const copy = SURFACE_COPY[surface];

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getDashboardSummary(30, true)
      .then((data) => {
        if (!cancelled) {
          setSummary(data);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Unable to load this workspace.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const matters = summary?.needs_attention ?? [];
  const approvalRequests = summary?.approvals_pending_preview ?? [];
  const readyMatters = summary?.ready_for_approval_list ?? [];

  return (
    <div className="space-y-6">
      <SetPageChrome title={copy.title} subtitle={copy.description} />
      {error ? (
        <EmptyState title="Workspace unavailable" description={error} action={<Button onClick={() => window.location.reload()}>Retry</Button>} />
      ) : loading ? (
        <Card><CardContent className="p-6 text-sm text-muted-foreground">Loading workspace…</CardContent></Card>
      ) : (
        <>
          <div className="grid gap-px border border-border bg-border sm:grid-cols-3">
            <Metric label="Matters needing attention" value={matters.length} />
            <Metric label="Documents still processing" value={summary?.processing_cases_count ?? 0} />
            <Metric label="Approval requests" value={summary?.approvals_pending_count ?? 0} />
          </div>

          {surface === "requirements" ? (
            <div className="grid gap-6 lg:grid-cols-2">
              <ItemList title="Approval requests" empty="No approval requests are waiting." items={approvalRequests.map((item) => ({
                key: item.id,
                title: item.case_title,
                detail: item.request_type_label,
                href: `/dashboard/cases/${item.case_id}?surface=decision`,
              }))} />
              <ItemList title="Ready for approval" empty="No matters are ready for approval." items={readyMatters.map((item) => ({
                key: item.case_id,
                title: item.title,
                detail: `${item.cp_completion_pct}% of approval requirements complete`,
                href: `/dashboard/cases/${item.case_id}?surface=decision`,
              }))} />
            </div>
          ) : (
            <ItemList
              title={surface === "documents" ? "Matters with document work" : "Matters needing review"}
              empty={surface === "documents" ? "No matters currently need document work." : "No matters currently need issue review."}
              items={matters.map((item) => ({
                key: item.case_id,
                title: item.title,
                detail: surface === "documents"
                  ? `${item.pending_verifications} document check${item.pending_verifications === 1 ? "" : "s"} pending`
                  : `${item.open_high + item.open_medium + item.open_low} issue${item.open_high + item.open_medium + item.open_low === 1 ? "" : "s"} open`,
                href: `/dashboard/cases/${item.case_id}?surface=${surface === "documents" ? "documents" : "review"}`,
              }))}
            />
          )}
        </>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return <div className="bg-card px-4 py-4"><p className="text-sm text-muted-foreground">{label}</p><p className="mt-1 text-2xl tabular">{value}</p></div>;
}

function ItemList({ title, empty, items }: { title: string; empty: string; items: Array<{ key: string; title: string; detail: string; href: string }> }) {
  return (
    <Card>
      <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
      <CardContent className="p-0">
        {items.length === 0 ? <p className="px-6 pb-6 text-sm text-muted-foreground">{empty}</p> : (
          <div className="divide-y divide-border">
            {items.map((item) => <Link key={item.key} href={item.href} className="flex items-center justify-between gap-4 px-6 py-4 hover:bg-muted/40"><span className="min-w-0"><span className="block truncate text-sm font-medium">{item.title}</span><span className="block text-sm text-muted-foreground">{item.detail}</span></span><span className="shrink-0 text-sm text-muted-foreground">Open</span></Link>)}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
