"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  canProposeWaiver,
  firstEvidenceRef,
  FindingRow,
  hasPendingWaiver,
  requiredEvidenceLabel,
} from "@/lib/workbench/findings";

type FindingsListProps = {
  items: FindingRow[];
  filter: "all" | "exception" | "cp";
  selectedId: string | null;
  pendingWaiverIds?: Iterable<string>;
  onSelect: (item: FindingRow) => void;
  onResolve?: (item: FindingRow) => void;
  onWaive?: (item: FindingRow, reason: string) => void;
  onSatisfyCp?: (item: FindingRow) => void;
  onJumpToEvidence?: (documentId: string, page?: number) => void;
};

export function FindingsList({
  items,
  filter,
  selectedId,
  pendingWaiverIds = [],
  onSelect,
  onResolve,
  onWaive,
  onSatisfyCp,
  onJumpToEvidence,
}: FindingsListProps) {
  const visible = items.filter((item) => filter === "all" || item.kind === filter);
  const [waiveTarget, setWaiveTarget] = useState<FindingRow | null>(null);
  const [reason, setReason] = useState("");

  if (visible.length === 0) {
    return <p className="px-3 py-6 text-sm text-muted-foreground">No findings in this filter.</p>;
  }

  return (
    <>
      <ul className="divide-y divide-border">
        {visible.map((item) => {
          const selected = item.id === selectedId;
          const pending = hasPendingWaiver(item, pendingWaiverIds);
          const evidence = firstEvidenceRef(item);
          const required = requiredEvidenceLabel(item);
          return (
            <li key={`${item.kind}-${item.id}`} className={selected ? "bg-muted/40" : undefined}>
              <button type="button" className="w-full px-3 py-3 text-left" onClick={() => onSelect(item)}>
                <p className="text-[11px] uppercase tracking-[0.12em] text-muted-foreground">
                  {item.kind === "cp" ? "CP" : "Exception"}
                  {item.rule_id ? ` · ${item.rule_id}` : ""}
                  {` · ${item.severity}`}
                  {item.is_hard_stop ? " · hard-stop" : ""}
                </p>
                <p className="mt-1 text-sm text-foreground">{item.title}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {pending ? "Waiver pending" : item.status}
                  {item.status === "Waived" && item.waiver_reason ? ` — ${item.waiver_reason}` : ""}
                </p>
              </button>
              {selected ? (
                <div className="space-y-2 px-3 pb-3 text-sm text-muted-foreground">
                  {item.description ? <p className="text-foreground">{item.description}</p> : null}
                  {item.cp_text ? <p>CP: {item.cp_text}</p> : null}
                  {required ? <p>Required: {required}</p> : null}
                  {evidence ? (
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={() => onJumpToEvidence?.(evidence.documentId, evidence.page)}
                    >
                      Open evidence
                      {evidence.page ? ` · p.${evidence.page}` : ""}
                    </Button>
                  ) : null}
                </div>
              ) : null}
              {item.status === "Open" ? (
                <div className="flex gap-2 px-3 pb-3">
                  {item.kind === "exception" ? (
                    <Button type="button" size="sm" variant="secondary" onClick={() => onResolve?.(item)}>
                      Resolve
                    </Button>
                  ) : (
                    <Button type="button" size="sm" variant="secondary" onClick={() => onSatisfyCp?.(item)}>
                      Mark met
                    </Button>
                  )}
                  {canProposeWaiver(item, pendingWaiverIds) ? (
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setWaiveTarget(item);
                        setReason("");
                      }}
                    >
                      Propose waiver
                    </Button>
                  ) : null}
                  {pending ? <p className="self-center text-xs text-muted-foreground">Waiting for checker</p> : null}
                </div>
              ) : null}
            </li>
          );
        })}
      </ul>
      <Dialog open={Boolean(waiveTarget)} onOpenChange={(open) => !open && setWaiveTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Propose waiver</DialogTitle>
            <DialogDescription>
              {waiveTarget?.rule_id ? `${waiveTarget.rule_id} — ` : ""}
              {waiveTarget?.title}. A different person must approve this.
            </DialogDescription>
          </DialogHeader>
          <Textarea
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            placeholder="Recorded reason"
            rows={4}
          />
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => setWaiveTarget(null)}>
              Cancel
            </Button>
            <Button
              type="button"
              disabled={!reason.trim()}
              onClick={() => {
                if (!waiveTarget || !reason.trim()) return;
                onWaive?.(waiveTarget, reason.trim());
                setWaiveTarget(null);
                setReason("");
              }}
            >
              Submit waiver
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
