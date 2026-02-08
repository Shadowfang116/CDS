"use client";

import * as React from "react";
import { CaseDetailTabs } from "./case-detail-tabs";
import { EvidencePanel } from "@/components/evidence/evidence-panel";
import { EvidenceItem } from "@/components/evidence/evidence-types";
import { ExceptionRow } from "@/components/exceptions/exception-types";
import { fetchCaseExceptions, resolveException, waiveException } from "@/lib/exceptions-api";
import { useMeRole } from "@/lib/use-me-role";

function evidenceFromException(ex: ExceptionRow): EvidenceItem {
  return {
    id: `ev-${ex.id}`,
    title: ex.title,
    refs: ex.evidence_refs.map((r) => ({
      doc_id: r.doc_id,
      page: r.page,
      snippet: r.snippet,
    })),
  };
}

export function CaseDetailClient(props: { caseId: string }) {
  const { role } = useMeRole();

  const [exceptions, setExceptions] = React.useState<ExceptionRow[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  // Evidence panel state
  const [items, setItems] = React.useState<EvidenceItem[]>([]);
  const [selectedId, setSelectedId] = React.useState<string | undefined>(undefined);

  React.useEffect(() => {
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const rows = await fetchCaseExceptions(props.caseId);
        setExceptions(rows);
      } catch (e: any) {
        setError(e?.message || "Failed to load exceptions");
        setExceptions([]);
      } finally {
        setLoading(false);
      }
    })();
  }, [props.caseId]);

  const onEvidenceFromException = (ex: ExceptionRow) => {
    const item = evidenceFromException(ex);
    setItems((prev) => (prev.some((p) => p.id === item.id) ? prev : [item, ...prev]));
    setSelectedId(item.id);
  };

  const onResolve = async (ex: ExceptionRow) => {
    // Minimal payload for now; later include evidence binding + notes
    const updated = await resolveException(ex.id, { case_id: props.caseId });
    setExceptions((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
  };

  const onWaive = async (ex: ExceptionRow, waiver_reason: string) => {
    const updated = await waiveException(ex.id, { waiver_reason });
    setExceptions((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
  };

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
      <div className="space-y-4">
        {loading ? (
          <div className="rounded-lg border bg-background p-4 text-sm text-muted-foreground">
            Loading exception data…
          </div>
        ) : error ? (
          <div className="rounded-lg border bg-background p-4 text-sm text-red-700 dark:text-red-300">
            {error}
          </div>
        ) : null}

        <CaseDetailTabs
          exceptions={exceptions}
          onEvidenceFromException={onEvidenceFromException}
          onResolve={onResolve}
          onWaive={onWaive}
          role={role}
        />
      </div>

      <EvidencePanel
        items={items}
        selectedId={selectedId}
        onSelect={setSelectedId}
        onClear={() => {
          setItems([]);
          setSelectedId(undefined);
        }}
      />
    </div>
  );
}
