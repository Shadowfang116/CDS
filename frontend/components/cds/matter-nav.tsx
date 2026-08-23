"use client";

import { CASE_TABS, type CaseTabKey } from "@/lib/routes";
import { cn } from "@/lib/utils";

const GROUPS = [
  { id: "file", label: "File", tabs: ["summary", "documents", "ocr-extractions"] as CaseTabKey[] },
  { id: "findings", label: "Findings", tabs: ["exceptions", "cps"] as CaseTabKey[] },
  { id: "dossier", label: "Dossier", tabs: ["dossier", "verification"] as CaseTabKey[] },
  { id: "pack", label: "Pack", tabs: ["drafts", "exports", "audit"] as CaseTabKey[] },
] as const;

type MatterNavProps = {
  activeTab: CaseTabKey;
  onSelect: (tab: CaseTabKey) => void;
  exceptionCount?: number;
};

export function MatterNav({ activeTab, onSelect, exceptionCount }: MatterNavProps) {
  const activeGroup = GROUPS.find((group) => group.tabs.includes(activeTab)) ?? GROUPS[0];

  return (
    <div className="border-b border-border">
      <div className="relative flex gap-8" role="tablist" aria-label="Matter domains">
        {GROUPS.map((group) => {
          const selected = group.id === activeGroup.id;
          return (
            <button
              key={group.id}
              type="button"
              role="tab"
              aria-selected={selected}
              className={cn(
                "relative pb-3 text-[11px] font-medium uppercase tracking-[0.16em]",
                selected ? "text-foreground" : "text-muted-foreground hover:text-foreground"
              )}
              onClick={() => {
                if (!group.tabs.includes(activeTab)) {
                  onSelect(group.tabs[0]);
                }
              }}
            >
              {group.label}
              {selected ? (
                <span data-nav-indicator className="absolute inset-x-0 -bottom-px h-px bg-foreground" />
              ) : null}
            </button>
          );
        })}
      </div>
      <div className="flex gap-6 py-3" role="tablist" aria-label="Matter sections">
        {activeGroup.tabs.map((key) => {
          const meta = CASE_TABS.find((tab) => tab.key === key);
          const selected = activeTab === key;
          return (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={selected}
              data-tour={key === "ocr-extractions" ? "ocr-review" : key === "exceptions" ? "exceptions" : key === "exports" ? "export" : undefined}
              className={cn(
                "text-[13px]",
                selected ? "text-foreground" : "text-muted-foreground hover:text-foreground"
              )}
              onClick={() => onSelect(key)}
            >
              {meta?.label}
              {key === "exceptions" && exceptionCount ? (
                <span className="ml-2 tabular text-primary">{String(exceptionCount).padStart(2, "0")}</span>
              ) : null}
            </button>
          );
        })}
      </div>
    </div>
  );
}
