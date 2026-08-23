"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  createCase,
  listInbox,
  patchDossierField,
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
  const [files, setFiles] = useState<FileList | null>(null);

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

  const createMatter = async () => {
    if (!title.trim()) return;
    setCreating(true);
    try {
      const created = await createCase(title.trim());
      const caseId = created.id as string;
      await patchDossierField(caseId, "property.type", {
        value: propertyType,
        note: "Set at new matter intake",
      }).catch(() => undefined);
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
    <div className="flex min-h-[calc(100vh-4rem)] flex-col gap-6 px-6 py-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="cds-meta text-muted-foreground">Queue</p>
          <h1 className="mt-1 text-2xl font-medium tracking-[-0.03em]">Inbox</h1>
        </div>
        <form
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
          <input type="file" multiple accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff,.docx" onChange={(event) => setFiles(event.target.files)} />
          <Button type="submit" disabled={creating || !title.trim()}>
            {creating ? "Creating…" : "Create"}
          </Button>
        </form>
      </header>

      <nav className="flex flex-wrap gap-4 border-b border-border pb-2" aria-label="Inbox queues">
        {QUEUES.map((item) => {
          const count = counts?.[item.id] ?? 0;
          const selected = queue === item.id;
          return (
            <Link
              key={item.id}
              href={`/dashboard?queue=${item.id}`}
              className={selected ? "text-sm text-foreground" : "text-sm text-muted-foreground hover:text-foreground"}
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
        <EmptyState title="No matters need you" description="When a file is blocked, waiting, or ready, it will appear here." />
      ) : (
        <table className="w-full text-left text-sm">
          <thead className="text-[11px] uppercase tracking-[0.12em] text-muted-foreground">
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
                    {item.open_high ? ` · HIGH ${item.open_high}` : ""}
                    {item.open_cps ? ` · CP ${item.open_cps}` : ""}
                  </p>
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
