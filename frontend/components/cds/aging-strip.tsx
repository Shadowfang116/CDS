"use client";

import { formatWait } from "@/lib/next-matter";
import type { NeedsAttentionItem } from "@/lib/api";

type AgingStripProps = {
  items: NeedsAttentionItem[];
  onOpen: (caseId: string) => void;
};

export function AgingStrip({ items, onOpen }: AgingStripProps) {
  if (items.length === 0) {
    return null;
  }

  return (
    <section className="border-t border-border pt-8">
      <p className="cds-meta mb-5">Aging</p>
      <div className="flex gap-10 overflow-x-auto pb-1">
        {items.map((item) => (
          <button
            key={item.case_id}
            type="button"
            onClick={() => onOpen(item.case_id)}
            className="min-w-[200px] max-w-[260px] shrink-0 border-0 bg-transparent p-0 text-left"
          >
            <div className="truncate text-[15px] text-foreground">{item.title}</div>
            <div className="mt-1.5 flex justify-between gap-4 text-xs text-muted-foreground">
              <span>{item.status}</span>
              <span className="tabular text-primary">{formatWait(item.updated_at)}</span>
            </div>
          </button>
        ))}
      </div>
    </section>
  );
}
