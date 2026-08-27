"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  createCase,
  listInbox,
  updateCaseAssignment,
  uploadDocument,
  InboxItem,
  InboxResponse,
} from "@/lib/api";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { getCaseWorkbenchPath } from "@/lib/routes";
import { useToast } from "@/components/ui/toast";

const QUEUES = [
  { id: "mine", label: "Needs me" },
  { id: "blocked", label: "Blocked" },
  { id: "waiting", label: "Waiting" },
  { id: "ready", label: "Ready" },
  { id: "aging", label: "Aging" },
] as const;

function ageLabel(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const hours = Math.max(0, Math.floor(ms / 36e5));
  const days = Math.floor(hours / 24);
  if (days <= 0) return `${hours}h`;
  return `${days}d`;
}

export function InboxView() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const user = useCurrentUser();
  const { toast } = useToast();
  const defaultQueue = user?.role === "Approver" ? "ready" : "mine";
  const queue = searchParams.get("queue") || defaultQueue;
  const [data, setData] = useState<InboxResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [title, setTitle] = useState("");
  const [propertyType, setPropertyType] = useState("Society plot");
  const [propertyRegime, setPropertyRegime] = useState("SOCIETY");
  const [files, setFiles] = useState<FileList | null>(null);
  const newMatterFormRef = useRef<HTMLFormElement | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const next = await listInbox({ queue, page_size: 50 });
      setData(next);
    } catch (error) {
      toast({ title: "Inbox failed to load", description: error instanceof Error ? error.message : "Error", variant: "error" });
    } finally {
      setLoading(false);
    }
  }, [queue, toast]);

  useEffect(() => {
    void load();
  }, [load]);

  const counts = data?.counts;
  const items = data?.items ?? [];
  const highRiskMatters = items.filter((item) => item.open_high > 0).length;
  const incompleteMatters = items.filter((item) => item.next_action.toLowerCase().includes("missing")).length;

  const createMatter = async () => {
    if (!title.trim()) return;
    setCreating(true);
    try {
      const created = await createCase(title.trim(), {
        property_type: propertyType,
        property_regime: propertyRegime,
      });
      const caseId = created.id as string;
      if (files?.length) {
        for (const file of Array.from(files)) {
          await uploadDocument(caseId, file);
        }
      }
      router.push(getCaseWorkbenchPath(caseId, { field: "property.type" }));
    } catch (error) {
      toast({ title: "Could not create matter", description: error instanceof Error ? error.message : "Error", variant: "error" });
    } finally {
      setCreating(false);
    }
  };

  const claim = async (item: InboxItem) => {
    await updateCaseAssignment(item.id, "claim");
    await load();
  };

  return (
    <div className="flex min-h-[calc(100vh-4rem)] flex-col gap-6 px-6 py-6" data-tour="dashboard">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="cds-meta text-muted-foreground">Dashboard</p>
          <h1 className="mt-1 text-2xl font-medium tracking-[-0.03em]">Review queue</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Start with the matters that need a decision, then follow the evidence and next action.
          </p>
        </div>
        <form
          data-tour="new-matter"
          ref={newMatterFormRef}
          className="flex flex-wrap items-end gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            void createMatter();
          }}
        >
          <label className="flex flex-col gap-1 text-xs text-muted-foreground">
            New matter
            <input
              className="h-9 w-56 rounded-sm border border-border bg-background px-2 text-sm text-foreground"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Borrower / file name"
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-muted-foreground">
            Property
            <select
              className="h-9 rounded-sm border border-border bg-background px-2 text-sm"
              value={propertyType}
              onChange={(event) => setPropertyType(event.target.value)}
            >
              <option>Society plot</option>
              <option>Urban house</option>
            </select>
          </label>
          <label className="flex flex-col gap-1 text-xs text-muted-foreground">
            Documents <span className="text-[11px] text-muted-foreground/70">Optional to start</span>
            <input
              className="max-w-[16rem] text-xs text-muted-foreground file:mr-2 file:rounded file:border-0 file:bg-muted file:px-2 file:py-1 file:text-xs file:text-foreground"
              type="file"
              multiple
              accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff,.docx"
              onChange={(event) => setFiles(event.target.files)}
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-muted-foreground">
            Authority / regime
            <select
              className="h-9 rounded-sm border border-border bg-background px-2 text-sm"
              value={propertyRegime}
              onChange={(event) => setPropertyRegime(event.target.value)}
              required
            >
              <option value="SOCIETY">Housing society</option>
              <option value="LDA">LDA</option>
              <option value="DHA">DHA</option>
              <option value="RUDA">RUDA</option>
              <option value="REVENUE">Revenue / land records</option>
              <option value="CANTONMENT">Cantonment board</option>
              <option value="MUNICIPAL">Municipal / TMA</option>
            </select>
          </label>
          <Button type="submit" disabled={creating || !title.trim()}>
            {creating ? "Creating…" : "Create"}
          </Button>
        </form>
      </header>

      <section className="grid border-y border-border sm:grid-cols-2 xl:grid-cols-4" aria-label="Dashboard overview">
        <OverviewLink href="/dashboard?queue=mine" label="Needs me" value={counts?.mine ?? 0} detail="Reviewer action" />
        <OverviewLink href="/dashboard?queue=blocked" label="Blocked" value={counts?.blocked ?? 0} detail="Waiting on evidence" />
        <OverviewLink href="/dashboard?queue=ready" label="Ready" value={counts?.ready ?? 0} detail="Ready for decision" />
        <div className="border-border px-4 py-4 sm:border-l xl:border-l">
          <p className="text-sm font-medium text-foreground">Current view</p>
          <p className="mt-2 text-2xl font-medium tabular text-foreground">{highRiskMatters}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            High-risk matters{incompleteMatters ? ` · ${incompleteMatters} missing information` : ""}
          </p>
        </div>
      </section>

      <nav className="flex flex-wrap gap-4 border-b border-border pb-2" aria-label="Inbox queues">
        {QUEUES.map((item) => {
          const count = counts?.[item.id] ?? 0;
          const selected = queue === item.id;
          return (
            <Link
              key={item.id}
              href={`/dashboard?queue=${item.id}`}
              className={selected ? "border-b border-[hsl(var(--crimson-border))] pb-2 text-sm text-foreground" : "pb-2 text-sm text-muted-foreground hover:text-foreground"}
            >
              {item.label}
              <span className="ml-2 tabular">{String(count).padStart(2, "0")}</span>
            </Link>
          );
        })}
      </nav>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading queue…</p>
      ) : items.length === 0 ? (
        <EmptyState
          title="No matters need you"
          description="Create a matter to start a review, or switch queues to see blocked and ready work."
          actionLabel="Create a matter"
          onAction={() => {
            newMatterFormRef.current?.querySelector<HTMLInputElement>("input[placeholder='Borrower / file name']")?.focus();
          }}
        />
      ) : (
        <table className="w-full text-left text-sm" data-tour="case-list">
          <thead className="text-xs font-medium text-muted-foreground">
            <tr>
              <th className="pb-2 font-medium">Matter</th>
              <th className="pb-2 font-medium">Decision</th>
              <th className="pb-2 font-medium">Next</th>
              <th className="pb-2 font-medium">Age</th>
              <th className="pb-2 font-medium" />
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="border-t border-border">
                <td className="py-3">
                  <Link href={getCaseWorkbenchPath(item.id)} className="font-medium hover:underline">
                    {item.title}
                  </Link>
                  <p className="text-xs text-muted-foreground">
                    {item.status}
                    {item.open_high ? ` · High risk ${item.open_high}` : ""}
                    {item.open_cps ? ` · CP ${item.open_cps}` : ""}
                  </p>
                  {item.open_high > 0 ? (
                    <p className="mt-1 text-xs text-[hsl(var(--status-high))]">
                      High-risk findings remain open and need reviewer attention.
                    </p>
                  ) : item.open_medium > 0 ? (
                    <p className="mt-1 text-xs text-[hsl(var(--status-medium))]">
                      Medium-risk findings remain open; review the next action.
                    </p>
                  ) : null}
                </td>
                <td className="py-3 tabular">{item.decision ?? "—"}</td>
                <td className="py-3 text-muted-foreground">{item.next_action}</td>
                <td className="py-3 tabular text-muted-foreground">{ageLabel(item.updated_at)}</td>
                <td className="py-3 text-right">
                  {!item.assigned_to_user_id ? (
                    <Button type="button" variant="ghost" size="sm" onClick={() => void claim(item)}>
                      Claim
                    </Button>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function OverviewLink({ href, label, value, detail }: { href: string; label: string; value: number; detail: string }) {
  return (
    <Link href={href} className="border-border px-4 py-4 transition-colors hover:bg-[hsl(var(--pill))] sm:border-r xl:last:border-r-0">
      <p className="text-sm font-medium text-foreground">{label}</p>
      <p className="mt-2 text-2xl font-medium tabular text-foreground">{value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
    </Link>
  );
}
