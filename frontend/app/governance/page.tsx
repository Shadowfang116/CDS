import { Suspense } from "react";
import { GovernanceView } from "@/components/governance/governance-view";

export default function GovernancePage() {
  return (
    <Suspense fallback={<p className="p-6 text-sm text-muted-foreground">Loading governance…</p>}>
      <GovernanceView />
    </Suspense>
  );
}
