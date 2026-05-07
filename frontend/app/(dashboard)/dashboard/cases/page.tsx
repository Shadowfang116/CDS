"use client";

import * as React from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { DataTable } from "@/components/data/data-table";
import { caseColumns } from "@/features/cases/case-columns";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/ui/empty-state";
import { useToast } from "@/components/ui/toast";
import { listCasesPaginated, createCase } from "@/lib/api";
import type { CaseListItem, CaseListResponse } from "@/types/cases";
import { Card, CardContent } from "@/components/ui/card";
import { SetPageChrome } from "@/components/layout/set-page-chrome";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";

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
  const order: "asc" | "desc" =
    searchParams.get("order") === "asc" ? "asc" : "desc";

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

function CasesPageContent() {
  const router = useRouter();
  const { toast } = useToast();
  const searchParams = useSearchParams();
  const urlQ = searchParams.get("q") ?? "";
  const [searchInput, setSearchInput] = React.useState(urlQ);
  const [newCaseOpen, setNewCaseOpen] = React.useState(false);
  const [newCaseTitle, setNewCaseTitle] = React.useState("");
  const [creating, setCreating] = React.useState(false);
  const [createError, setCreateError] = React.useState<string | null>(null);
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

  const handleNewCaseClose = React.useCallback((open: boolean) => {
    if (!open) {
      setNewCaseTitle("");
      setCreateError(null);
    }
    setNewCaseOpen(open);
  }, []);

  const handleCreateCase = React.useCallback(async () => {
    const title = newCaseTitle.trim();
    if (!title) return;
    setCreating(true);
    setCreateError(null);
    try {
      const newCase = await createCase(title);
      if (typeof newCase?.id !== "string" || !newCase.id) {
        setCreateError("Unexpected response from server");
        return;
      }
      setNewCaseOpen(false);
      setNewCaseTitle("");
      toast({ title: "Case created successfully", variant: "success" });
      router.push(`/dashboard/cases/${newCase.id}?tab=documents`);
    } catch (err: unknown) {
      setCreateError(err instanceof Error ? err.message : "Failed to create case");
    } finally {
      setCreating(false);
    }
  }, [newCaseTitle, router, toast]);

  const cases = React.useMemo(
    () => (Array.isArray(data) ? data : []),
    [data]
  );

  React.useEffect(() => {
    setSearchInput(params.q);
  }, [params.q]);

  const debouncedSetQ = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  React.useEffect(
    () => () => {
      if (debouncedSetQ.current) {
        clearTimeout(debouncedSetQ.current);
        debouncedSetQ.current = null;
      }
    },
    []
  );

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
      <SetPageChrome
        title="Cases"
        breadcrumbs={[{ label: "Cases" }]}
        actions={null}
      />

      <Dialog open={newCaseOpen} onOpenChange={handleNewCaseClose}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>New Case</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-3 py-2">
            <Input
              placeholder="Case title"
              value={newCaseTitle}
              onChange={(e) => setNewCaseTitle(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !creating) handleCreateCase(); }}
              autoFocus
            />
            {createError && (
              <p className="text-sm text-destructive">{createError}</p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => handleNewCaseClose(false)} disabled={creating}>
              Cancel
            </Button>
            <Button onClick={handleCreateCase} disabled={creating || !newCaseTitle.trim()}>
              {creating ? "Creating…" : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <div className="flex flex-col gap-6" data-dashboard-reveal>
        <section className="rounded-lg border border-[rgba(82,90,99,0.4)] bg-[rgba(24,28,32,0.9)] px-5 py-4" data-dashboard-section>
          <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
            <div className="space-y-2">
              <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">
                Case Operations
              </div>
              <div className="text-sm text-stone-400">
                New, in-flight, review, pending documents, approval-ready, and closed files in one operations queue.
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
              <Button
                size="sm"
                onClick={() => { setNewCaseTitle(""); setCreateError(null); setNewCaseOpen(true); }}
              >
                New Case
              </Button>
              <span className="rounded-md border border-[rgba(82,90,99,0.4)] bg-[rgba(34,39,45,0.85)] px-3 py-2 text-stone-300">
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
                className="h-9 rounded-md border border-[rgba(82,90,99,0.55)] bg-[rgba(22,26,30,0.92)] px-3 text-sm text-stone-200"
              >
                {PAGE_SIZE_OPTIONS.map((n) => (
                  <option key={n} value={n}>
                    {n} per page
                  </option>
                ))}
              </select>
            </div>
          </div>
        </section>

        <Card data-dashboard-section data-tour="case-list">
          <CardContent className="flex flex-col gap-4 p-5">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <Input
                placeholder="Search by case title"
                value={searchInput}
                onChange={(e) => onSearchChange(e.target.value)}
                className="max-w-md"
              />
              <div className="text-sm text-stone-500">
                Sorted by {params.sort.replace("_", " ")} · {params.order}
              </div>
            </div>

            {error ? (
              <EmptyState
                title="Failed to load cases"
                description={error || "Please try again."}
                action={
                  <Button variant="outline" size="sm" onClick={retry}>
                    Retry
                  </Button>
                }
              />
            ) : !loading && cases.length === 0 ? (
              <EmptyState
                title="No cases found"
                description="Try adjusting the current search or return to the wider dashboard review queue."
              />
            ) : (
              <DataTable<CaseListItem, unknown>
                columns={caseColumns}
                data={cases}
                loading={loading}
                emptyText="No cases found."
                getRowId={(row) => String(row.id)}
              />
            )}
          </CardContent>
        </Card>

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

export default function CasesPage() {
  return (
    <React.Suspense
      fallback={
        <div className="space-y-4">
          <section className="rounded-lg border border-[rgba(82,90,99,0.4)] bg-[rgba(24,28,32,0.9)] px-5 py-4">
            <div className="text-sm text-stone-400">Loading cases…</div>
          </section>
          <Card>
            <CardContent className="p-5">
              <div className="text-sm text-stone-400">Preparing operations queue…</div>
            </CardContent>
          </Card>
        </div>
      }
    >
      <CasesPageContent />
    </React.Suspense>
  );
}

