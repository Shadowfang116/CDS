"use client";

import * as React from "react";
import { EvidenceItem } from "./evidence-types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

export function EvidencePanel(props: {
  items: EvidenceItem[];
  selectedId?: string;
  onSelect: (id: string) => void;
  onClear?: () => void;
}) {
  const { items, selectedId, onSelect, onClear } = props;

  const selected = items.find((i) => i.id === selectedId) ?? items[0];

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle>Evidence Register</CardTitle>
          {onClear ? (
            <Button variant="outline" size="sm" onClick={onClear}>
              Clear
            </Button>
          ) : null}
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {items.length === 0 ? (
          <div className="text-sm text-muted-foreground">
            No evidence references loaded. Select an exception to populate the review register.
          </div>
        ) : (
          <>
            <div className="space-y-2">
              {items.map((it) => (
                <button
                  key={it.id}
                  onClick={() => onSelect(it.id)}
                  className={[
                    "w-full rounded-md border border-[rgba(82,90,99,0.42)] px-3 py-2 text-left text-sm",
                    it.id === selected?.id
                      ? "bg-[rgba(44,50,57,0.72)] text-stone-100"
                      : "bg-[rgba(24,28,32,0.74)] hover:bg-[rgba(34,39,45,0.92)]",
                  ].join(" ")}
                >
                  <div className="font-medium text-stone-100">{it.title}</div>
                  <div className="text-xs text-muted-foreground">
                    {it.refs.length} reference(s)
                  </div>
                </button>
              ))}
            </div>

            <Separator />

            {selected ? (
              <div className="space-y-2">
                <div className="text-sm font-semibold uppercase tracking-[0.08em] text-stone-400">References</div>
                <div className="space-y-2">
                  {selected.refs.map((r, idx) => (
                    <div key={idx} className="rounded-md border border-[rgba(82,90,99,0.4)] bg-[rgba(24,28,32,0.72)] p-3 text-sm">
                      <div className="text-xs font-medium uppercase tracking-[0.08em] text-muted-foreground">
                        Document {r.doc_id} · Page {r.page}
                      </div>
                      {r.snippet ? (
                        <div className="mt-2 text-sm leading-6 text-stone-200">{r.snippet}</div>
                      ) : null}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </>
        )}
      </CardContent>
    </Card>
  );
}
