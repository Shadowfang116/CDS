import { Suspense } from "react";
import { GovernanceView } from "@/components/governance/governance-view";

export default function GlobalAuditRedirectPage() {
  return (
    <Suspense fallback={<p className="p-6 text-sm text-muted-foreground">Loading audit…</p>}>
      <GovernanceView fixedTab="audit" title="Audit" />
    </Suspense>
  );
}
