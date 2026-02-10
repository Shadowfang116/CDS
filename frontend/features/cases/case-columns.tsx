"use client";

import Link from "next/link";
import { ColumnDef } from "@tanstack/react-table";
import { CaseListItem } from "@/types/cases";
import { CaseStatusPill } from "@/components/ui/case-status-pill";
import { Button } from "@/components/ui/button";

function shortRef(id: string | number): string {
  const s = String(id ?? "");
  if (!s || s.length < 12) return s;
  return `${s.slice(0, 8)}…`;
}

function formatUpdated(iso: string | null | undefined): string {
  const d = new Date(iso ?? "");
  if (isNaN(d.getTime())) return iso ?? "—";
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);
  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return d.toLocaleDateString();
}

export const caseColumns: ColumnDef<CaseListItem>[] = [
  {
    id: "ref_title",
    header: "Case ref / Title",
    cell: ({ row }) => {
      const c = row.original;
      const ref = shortRef(c.id);
      return (
        <div className="space-y-0.5">
          <div className="font-medium">{c.title || "Untitled"}</div>
          <div className="text-xs text-muted-foreground">Ref: {ref}</div>
        </div>
      );
    },
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => {
      const status = row.original.status;
      if (!status) return <span className="text-muted-foreground">—</span>;
      return (
        <CaseStatusPill
          status={status as Parameters<typeof CaseStatusPill>[0]["status"]}
        />
      );
    },
  },
  {
    accessorKey: "updated_at",
    header: "Updated",
    cell: ({ row }) => (
      <span className="text-sm text-muted-foreground">
        {formatUpdated(row.original.updated_at ?? undefined)}
      </span>
    ),
  },
  {
    id: "actions",
    header: "",
    cell: ({ row }) => {
      const id = row.original.id;
      return (
        <div className="flex justify-end">
          <Button variant="outline" size="sm" asChild>
            <Link href={`/dashboard/cases/${String(id)}`}>View</Link>
          </Button>
        </div>
      );
    },
  },
];
