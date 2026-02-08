"use client";

import * as React from "react";
import { ExceptionRow } from "./exception-types";
import { SeverityBadge } from "@/components/ui/severity-badge";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";

function statusBadge(status: ExceptionRow["status"]) {
  if (status === "resolved") return <Badge variant="outline">Resolved</Badge>;
  if (status === "waived") return <Badge variant="outline">Waived</Badge>;
  return <Badge variant="outline">Open</Badge>;
}

export function ExceptionsTable(props: {
  rows: ExceptionRow[];
  selectedId?: string;
  onSelect: (id: string) => void;
}) {
  const { rows, selectedId, onSelect } = props;
  const [q, setQ] = React.useState("");

  const filtered = React.useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!s) return rows;
    return rows.filter((r) => {
      return (
        r.title.toLowerCase().includes(s) ||
        r.module.toLowerCase().includes(s) ||
        r.id.toLowerCase().includes(s) ||
        r.status.toLowerCase().includes(s)
      );
    });
  }, [q, rows]);

  return (
    <div className="space-y-3">
      <Input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search exceptions by title/module/status/id…"
        className="md:max-w-md"
      />

      <div className="rounded-lg border bg-background">
        <div className="grid grid-cols-[140px_120px_1fr_120px] gap-0 border-b px-3 py-2 text-xs font-medium text-muted-foreground">
          <div>Severity</div>
          <div>Module</div>
          <div>Title</div>
          <div>Status</div>
        </div>

        {filtered.length === 0 ? (
          <div className="p-4 text-sm text-muted-foreground">No results.</div>
        ) : (
          <div className="divide-y">
            {filtered.map((r) => {
              const active = r.id === selectedId;
              return (
                <button
                  key={r.id}
                  onClick={() => onSelect(r.id)}
                  className={[
                    "grid w-full grid-cols-[140px_120px_1fr_120px] gap-0 px-3 py-3 text-left text-sm",
                    active ? "bg-muted" : "bg-background hover:bg-muted/50",
                  ].join(" ")}
                >
                  <div>
                    <SeverityBadge severity={r.severity} />
                  </div>
                  <div className="text-muted-foreground">{r.module}</div>
                  <div className="font-medium">{r.title}</div>
                  <div>{statusBadge(r.status)}</div>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
