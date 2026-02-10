"use client";

import * as React from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { PageHeader } from "@/components/ui/page-header";
import { DataTable } from "@/components/data/data-table";
import { caseColumns } from "@/features/cases/case-columns";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { listCasesPaginated } from "@/lib/api";
import type { CaseListItem, CaseListResponse } from "@/types/cases";
import { Plus } from "lucide-react";

const PAGE_SIZE_OPTIONS = [20, 50, 100] as const;
const ALLOWED_SORT = ["created_at", "updated_at", "status", "title"] as const;
const DEFAULT_SORT = "created_at";
const DEFAULT_ORDER = "desc";
const DEBOUNCE_MS = 300;

function useCasesList() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const q = searchParams.get("q") ?? "";
  const page = Math.max(1, parseInt(searchParams.get("page") ?? "1", 10) || 1);
  const pageSize = Math.min(
    100,
    Math.max(1, parseInt(searchParams.get("page_size") ?? "20", 10) || 20)
  );
  const sort =
    searchParams.get("sort") && ALLOWED_SORT.includes(searchParams.get("sort") as typeof ALLOWED_SORT[number])
      ? (searchParams.get("sort") as typeof ALLOWED_SORT[number])
      : DEFAULT_SORT;
  const order =
    searchParams.get("order") === "asc" || searchParams.get("order") === "desc"
      ? searchParams.get("order")
      : DEFAULT_ORDER;

  const [data, setData] = React.useState<CaseListResponse | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [retryKey, setRetryKey] = React.useState(0);

  const setParams = React.useCallback(
    (updates: {
      q?: string;
      page?: number;
      page_size?: number;
      sort?: string;
      order?: string;
    }) => {
      const next = new URLSearchParams(searchParams.toString());
      if (updates.q !== undefined) {
        if (updates.q) next.set("q", updates.q);
        else next.delete("q");
      }
      if (updates.page !== undefined) {
        if (updates.page <= 1) next.delete("page");
        else next.set("page", String(updates.page));
      }
      if (updates.page_size !== undefined) {
        if (updates.page_size === 20) next.delete("page_size");
        else next.set("page_size", String(updates.page_size));
      }
      if (updates.sort !== undefined) {
        if (updates.sort === DEFAULT_SORT) next.delete("sort");
        else next.set("sort", updates.sort);
      }
      if (updates.order !== undefined) {
        if (updates.order === DEFAULT_ORDER) next.delete("order");
        else next.set("order", updates.order);
      }
      router.replace(`/dashboard/cases?${next.toString()}`, { scroll: false });
    },
    [router, searchParams]
  );

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listCasesPaginated({ q, page, page_size: pageSize, sort, order })
      .then((res) => {
        if (!cancelled) {
          setData(res);
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err?.message ?? "Failed to load cases");
          setData(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [q, page, pageSize, sort, order, retryKey]);

  const retry = React.useCallback(() => {
    setError(null);
    setRetryKey((k) => k + 1);
  }, []);

  return {
    data: data?.items ?? [],
    total: data?.total ?? 0,
    page: data?.page ?? page,
    pageSize: data?.page_size ?? pageSize,
    totalPages: data?.total_pages ?? 1,
    loading,
    error,
    params: { q, page, pageSize, sort, order },
    setParams,
    retry,
  };
}

export default function CasesPage() {
  const user = useCurrentUser();
  const searchParams = useSearchParams();
  const urlQ = searchParams.get("q") ?? "";
  const [searchInput, setSearchInput] = React.useState(urlQ);
  const {
    data,
    total,
    page,
    pageSize,
    totalPages,
    loading,
    error,
    params,
    setParams,
    retry,
  } = useCasesList();

  const canCreateCase =
    user?.role === "Admin" || user?.role === "Approver" || user?.role === "Reviewer";

  React.useEffect(() => {
    setSearchInput(params.q);
  }, [params.q]);

  const debouncedSetQ = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  const onSearchChange = (value: string) => {
    setSearchInput(value);
    if (debouncedSetQ.current) clearTimeout(debouncedSetQ.current);
    debouncedSetQ.current = setTimeout(() => {
      setParams({ q: value.trim() || undefined, page: 1 });
      debouncedSetQ.current = null;
    }, DEBOUNCE_MS);
  };

  return (
    <>
      <PageHeader
        title="Cases"
        subtitle="New → Processing → Review → Pending Docs → Ready for Approval → Approved/Rejected → Closed"
        actions={
          canCreateCase ? (
            <Button asChild>
              <Link href="/dashboard/cases/new">
                <Plus className="h-4 w-4 mr-2" />
                New Case
              </Link>
            </Button>
          ) : undefined
        }
      />

      <div className="p-4 space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <Input
            placeholder="Search by case title…"
            value={searchInput}
            onChange={(e) => onSearchChange(e.target.value)}
            className="max-w-sm"
          />
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <span>
              {total} case{total !== 1 ? "s" : ""}
            </span>
            <select
              value={pageSize}
              onChange={(e) =>
                setParams({
                  page_size: Number(e.target.value) as 20 | 50 | 100,
                  page: 1,
                })
              }
              className="h-9 rounded-md border border-input bg-background px-2 text-sm"
            >
              {PAGE_SIZE_OPTIONS.map((n) => (
                <option key={n} value={n}>
                  {n} per page
                </option>
              ))}
            </select>
          </div>
        </div>

        {error ? (
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm flex items-center justify-between gap-3 flex-wrap">
            <span className="text-destructive">{error}</span>
            <Button variant="outline" size="sm" onClick={retry}>
              Retry
            </Button>
          </div>
        ) : null}

        <DataTable<CaseListItem, unknown>
          columns={caseColumns}
          data={data}
          loading={loading}
          emptyText="No cases found."
          getRowId={(row) => String(row.id)}
        />

        {totalPages > 1 && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">
              Page {page} of {totalPages}
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setParams({ page: page - 1 })}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setParams({ page: page + 1 })}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
