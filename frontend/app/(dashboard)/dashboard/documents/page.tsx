"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Files } from "lucide-react";
import { SetPageChrome } from "@/components/layout/set-page-chrome";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { listAllCases, listDocuments, type CaseDocumentItem } from "@/lib/api";
import { getCaseDocumentFocusPath } from "@/lib/routes";
import type { CaseListItem } from "@/types/cases";

type DocumentRow = {
  id: string;
  name: string;
  caseId: string;
  caseTitle: string;
  classification: string;
  status: string;
  uploadedAt?: string;
};

function getCaseLabel(caseItem: CaseListItem): string {
  const caseId = String(caseItem.id);
  return caseItem.title?.trim() || `Case ${caseId.slice(0, 8)}`;
}

function getClassificationLabel(documentItem: CaseDocumentItem): string {
  return (
    documentItem.corrected_doc_type?.trim() ||
    documentItem.doc_type?.trim() ||
    documentItem.predicted_doc_type?.trim() ||
    documentItem.classification_status?.trim() ||
    "-"
  );
}

function getStatusVariant(status: string): "success" | "warning" | "error" | "neutral" {
  const normalizedStatus = status.trim().toLowerCase();

  if (["complete", "completed"].includes(normalizedStatus)) {
    return "success";
  }

  if (["needs_review", "queued", "processing", "ocr_in_progress", "extracting", "rules_evaluation"].includes(normalizedStatus)) {
    return "warning";
  }

  if (normalizedStatus === "failed") {
    return "error";
  }

  return "neutral";
}

function formatDateTime(value?: string): string {
  if (!value) {
    return "-";
  }

  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "-" : parsed.toLocaleString();
}

function formatCaseCell(title: string, caseId: string): string {
  return `${title} · ${caseId.slice(0, 8)}`;
}

function DocumentsTableSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 6 }).map((_, index) => (
        <div key={index} className="grid grid-cols-[2fr_1.7fr_1.3fr_1fr_1.3fr] gap-3 rounded-lg border border-[rgba(82,90,99,0.32)] bg-[rgba(24,28,32,0.82)] px-4 py-3">
          <Skeleton className="h-5 w-full" />
          <Skeleton className="h-5 w-full" />
          <Skeleton className="h-5 w-28" />
          <Skeleton className="h-5 w-16" />
          <Skeleton className="h-5 w-32" />
        </div>
      ))}
    </div>
  );
}

export default function Page() {
  const router = useRouter();
  const [rows, setRows] = React.useState<DocumentRow[]>([]);
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
            const documents = await listDocuments(String(caseItem.id));
            const caseTitle = getCaseLabel(caseItem);

            return (Array.isArray(documents) ? documents : []).map((documentItem: CaseDocumentItem) => ({
              id: documentItem.id,
              name: documentItem.original_filename,
              caseId: String(caseItem.id),
              caseTitle,
              classification: getClassificationLabel(documentItem),
              status: documentItem.status || "-",
              uploadedAt: documentItem.created_at,
            }));
          })
        );

        if (cancelled) {
          return;
        }

        const nextRows = results
          .flatMap((result) => result.status === "fulfilled" ? result.value : [])
          .sort((left, right) => new Date(right.uploadedAt ?? 0).getTime() - new Date(left.uploadedAt ?? 0).getTime());

        setRows(nextRows);
      } catch (err: any) {
        if (!cancelled) {
          setError(err?.message ?? "Failed to load documents");
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
      <SetPageChrome title="Documents" breadcrumbs={[{ label: "Documents" }]} />

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
                <DocumentsTableSkeleton />
              </div>
            ) : rows.length === 0 ? (
              <div className="p-5">
                <EmptyState
                  icon={<Files className="h-6 w-6 text-stone-400" />}
                  title="No documents found"
                  description="Uploaded case documents will appear here across the portfolio."
                />
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Document Name</TableHead>
                    <TableHead>Case</TableHead>
                    <TableHead>Type/Classification</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Uploaded Date</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((row) => (
                    <TableRow
                      key={row.id}
                      className="cursor-pointer"
                      onClick={() => router.push(getCaseDocumentFocusPath(row.caseId, row.id))}
                    >
                      <TableCell>{row.name}</TableCell>
                      <TableCell>{formatCaseCell(row.caseTitle, row.caseId)}</TableCell>
                      <TableCell>{row.classification}</TableCell>
                      <TableCell>
                        <Badge variant={getStatusVariant(row.status)}>{row.status}</Badge>
                      </TableCell>
                      <TableCell>{formatDateTime(row.uploadedAt)}</TableCell>
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
