"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle } from "lucide-react";
import { SetPageChrome } from "@/components/layout/set-page-chrome";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { SeverityBadge } from "@/components/ui/severity-badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { listAllCases, listExceptions } from "@/lib/api";
import { getCaseTabPath } from "@/lib/routes";
import type { CaseListItem } from "@/types/cases";

type ExceptionItem = {
  id: string;
  title: string;
  severity: string;
  status: string;
  created_at?: string;
};

type ExceptionRow = {
  id: string;
  caseId: string;
  caseTitle: string;
  severity: string;
  title: string;
  status: string;
  createdAt?: string;
};

function getCaseLabel(caseItem: CaseListItem): string {
  const caseId = String(caseItem.id);
  return caseItem.title?.trim() || `Case ${caseId.slice(0, 8)}`;
}

function getSeverityRank(severity: string): number {
  switch (severity) {
    case "Critical":
      return 0;
    case "High":
      return 1;
    case "Medium":
      return 2;
    case "Low":
      return 3;
    default:
      return 4;
  }
}

function getStatusVariant(status: string): "success" | "warning" | "neutral" {
  switch (status) {
    case "Resolved":
      return "success";
    case "Waived":
      return "warning";
    default:
      return "neutral";
  }
}

function formatCaseCell(title: string, caseId: string): string {
  return `${title} • ${caseId.slice(0, 8)}`;
}

function ExceptionsTableSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 6 }).map((_, index) => (
        <div key={index} className="grid grid-cols-[0.9fr_2.2fr_1.8fr_1fr] gap-3 rounded-lg border border-[rgba(82,90,99,0.32)] bg-[rgba(24,28,32,0.82)] px-4 py-3">
          <Skeleton className="h-5 w-16" />
          <Skeleton className="h-5 w-full" />
          <Skeleton className="h-5 w-full" />
          <Skeleton className="h-5 w-16" />
        </div>
      ))}
    </div>
  );
}

export default function Page() {
  const router = useRouter();
  const [rows, setRows] = React.useState<ExceptionRow[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError(null);

      try {
        const cases = await listAllCases({ sort: "updated_at", order: "desc", page_size: 100 });
        const results = await Promise.allSettled(
          cases.map(async (caseItem) => {
            const response = await listExceptions(String(caseItem.id));
            const exceptions = Array.isArray(response?.exceptions)
              ? (response.exceptions as ExceptionItem[])
              : [];

            return exceptions.map((exceptionItem) => ({
              id: exceptionItem.id,
              caseId: String(caseItem.id),
              caseTitle: getCaseLabel(caseItem),
              severity: exceptionItem.severity,
              title: exceptionItem.title,
              status: exceptionItem.status,
              createdAt: exceptionItem.created_at,
            }));
          })
        );

        if (cancelled) {
          return;
        }

        const nextRows = results
          .flatMap((result) => result.status === "fulfilled" ? result.value : [])
          .sort((left, right) => {
            const severityDelta = getSeverityRank(left.severity) - getSeverityRank(right.severity);
            if (severityDelta !== 0) {
              return severityDelta;
            }

            return new Date(right.createdAt ?? 0).getTime() - new Date(left.createdAt ?? 0).getTime();
          });

        setRows(nextRows);
      } catch (err: any) {
        if (!cancelled) {
          setError(err?.message ?? "Failed to load exceptions");
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
      <SetPageChrome title="Exceptions" breadcrumbs={[{ label: "Exceptions" }]} />

      <div className="p-6 space-y-6" data-dashboard-reveal>
        {error ? (
          <div className="rounded-lg border border-[rgba(189,90,86,0.36)] bg-[rgba(189,90,86,0.12)] px-4 py-3 text-sm text-[rgb(219,156,153)]">
            {error}
          </div>
        ) : null}

        <Card data-tour="exceptions">
          <CardContent className="p-0">
            {loading ? (
              <div className="p-5">
                <ExceptionsTableSkeleton />
              </div>
            ) : rows.length === 0 ? (
              <div className="p-5">
                <EmptyState
                  icon={<AlertTriangle className="h-6 w-6 text-stone-400" />}
                  title="No exceptions found"
                  description="Exceptions will appear here across all matters once evaluations create them."
                />
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Severity</TableHead>
                    <TableHead>Title</TableHead>
                    <TableHead>Matter</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((row) => (
                    <TableRow
                      key={row.id}
                      className="cursor-pointer"
                      onClick={() => router.push(getCaseTabPath(row.caseId, "exceptions"))}
                    >
                      <TableCell>
                        <SeverityBadge severity={row.severity} />
                      </TableCell>
                      <TableCell>{row.title}</TableCell>
                      <TableCell>{formatCaseCell(row.caseTitle, row.caseId)}</TableCell>
                      <TableCell>
                        <Badge variant={getStatusVariant(row.status)}>{row.status || "Open"}</Badge>
                      </TableCell>
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

