"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { History } from "lucide-react";
import { SetPageChrome } from "@/components/layout/set-page-chrome";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { listAllCases, listGlobalAuditLogs, type AuditLogEntry } from "@/lib/api";
import { getCaseTabPath } from "@/lib/routes";
import type { CaseListItem } from "@/types/cases";

type AuditRow = {
  id: string;
  actor: string;
  action: string;
  caseId: string | null;
  caseLabel: string;
  timestamp: string;
};

function getCaseLabel(caseItem: CaseListItem): string {
  const caseId = String(caseItem.id);
  return caseItem.title?.trim() || `Case ${caseId.slice(0, 8)}`;
}

function getActorLabel(entry: AuditLogEntry): string {
  return entry.actor_user_id ? entry.actor_user_id.slice(0, 8) : "System";
}

function formatCaseLabel(caseLabel: string, caseId: string | null): string {
  if (!caseId) {
    return "-";
  }

  return `${caseLabel} · ${caseId.slice(0, 8)}`;
}

function formatDateTime(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

function AuditTableSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 6 }).map((_, index) => (
        <div key={index} className="grid grid-cols-[1fr_1.7fr_1.8fr_1.3fr] gap-3 rounded-lg border border-[rgba(82,90,99,0.32)] bg-[rgba(24,28,32,0.82)] px-4 py-3">
          <Skeleton className="h-5 w-20" />
          <Skeleton className="h-5 w-full" />
          <Skeleton className="h-5 w-full" />
          <Skeleton className="h-5 w-32" />
        </div>
      ))}
    </div>
  );
}

export default function Page() {
  const router = useRouter();
  const [rows, setRows] = React.useState<AuditRow[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError(null);

      try {
        const [cases, auditEntries] = await Promise.all([
          listAllCases({ sort: "updated_at", order: "desc", page_size: 100 }),
          listGlobalAuditLogs({ limit: 100 }),
        ]);

        if (cancelled) {
          return;
        }

        const caseLookup = new Map<string, string>(
          cases.map((caseItem: CaseListItem) => [String(caseItem.id), getCaseLabel(caseItem)])
        );

        const nextRows = auditEntries.map((entry: AuditLogEntry) => ({
          id: entry.id,
          actor: getActorLabel(entry),
          action: entry.action,
          caseId: entry.case_id ?? null,
          caseLabel: entry.case_id ? caseLookup.get(entry.case_id) || `Case ${entry.case_id.slice(0, 8)}` : "-",
          timestamp: entry.created_at,
        }));

        setRows(nextRows);
      } catch (err: any) {
        if (!cancelled) {
          setError(err?.message ?? "Failed to load audit log");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void load();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <>
      <SetPageChrome title="Audit Log" breadcrumbs={[{ label: "Audit Log" }]} />

      <div className="p-6 space-y-6" data-dashboard-reveal>
        {error ? (
          <div className="rounded-lg border border-[rgba(189,90,86,0.36)] bg-[rgba(189,90,86,0.12)] px-4 py-3 text-sm text-[rgb(219,156,153)]">
            {error}
          </div>
        ) : null}

        <Card>
          <CardContent className="p-0">
            {loading ? (
              <div className="p-5">
                <AuditTableSkeleton />
              </div>
            ) : rows.length === 0 ? (
              <div className="p-5">
                <EmptyState
                  icon={<History className="h-6 w-6 text-stone-400" />}
                  title="No audit activity found"
                  description="Recent activity across all cases will appear here."
                />
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Actor</TableHead>
                    <TableHead>Action</TableHead>
                    <TableHead>Case</TableHead>
                    <TableHead>Timestamp</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((row) => (
                    <TableRow
                      key={row.id}
                      className={row.caseId ? "cursor-pointer" : undefined}
                      onClick={row.caseId ? () => router.push(getCaseTabPath(row.caseId!, "audit")) : undefined}
                    >
                      <TableCell>{row.actor}</TableCell>
                      <TableCell>{row.action}</TableCell>
                      <TableCell>{formatCaseLabel(row.caseLabel, row.caseId)}</TableCell>
                      <TableCell>{formatDateTime(row.timestamp)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
