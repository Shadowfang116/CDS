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
        <div className="grid grid-cols-[120px_140px_1fr_120px] gap-0 border-b border-[rgba(82,90,99,0.36)] bg-[rgba(31,36,41,0.96)] px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
          <div>Severity</div>
          <div>Module</div>
          <div>Exception</div>
          <div>Status</div>
        </div>

        {filtered.length === 0 ? (
          <div className="p-4 text-sm text-muted-foreground">No results.</div>
        ) : (
          <div className="divide-y divide-[rgba(82,90,99,0.28)]">
            {filtered.map((r) => {
              const active = r.id === selectedId;
              return (
                <button
                  key={r.id}
                  onClick={() => onSelect(r.id)}
                  className={[
                    "grid w-full grid-cols-[120px_140px_1fr_120px] gap-0 px-3 py-3 text-left text-sm",
                    active ? "bg-[rgba(44,50,57,0.72)]" : "bg-[rgba(24,28,32,0.74)] hover:bg-[rgba(34,39,45,0.92)]",
                  ].join(" ")}
                >
                  <div>
                    <SeverityBadge severity={r.severity} />
                  </div>
                  <div className="text-muted-foreground">{r.module}</div>
                  <div>
                    <div className="font-medium text-stone-100">{r.title}</div>
                    <div className="mt-1 text-xs text-muted-foreground">{r.id}</div>
                  </div>
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
