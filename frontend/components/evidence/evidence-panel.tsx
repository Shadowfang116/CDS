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
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">Evidence</CardTitle>
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
            No evidence selected yet. Select an Exception or CP to load its evidence references.
          </div>
        ) : (
          <>
            <div className="space-y-2">
              {items.map((it) => (
                <button
                  key={it.id}
                  onClick={() => onSelect(it.id)}
                  className={[
                    "w-full rounded-md border px-3 py-2 text-left text-sm",
                    it.id === selected?.id
                      ? "bg-muted"
                      : "bg-background hover:bg-muted/50",
                  ].join(" ")}
                >
                  <div className="font-medium">{it.title}</div>
                  <div className="text-xs text-muted-foreground">
                    {it.refs.length} reference(s)
                  </div>
                </button>
              ))}
            </div>

            <Separator />

            {selected ? (
              <div className="space-y-2">
                <div className="text-sm font-semibold">References</div>
                <div className="space-y-2">
                  {selected.refs.map((r, idx) => (
                    <div key={idx} className="rounded-md border p-2 text-sm">
                      <div className="text-xs text-muted-foreground">
                        Doc: {r.doc_id} • Page: {r.page}
                      </div>
                      {r.snippet ? (
                        <div className="mt-1 text-xs">{r.snippet}</div>
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
