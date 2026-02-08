import { PageHeader } from "@/components/ui/page-header";
import { EmptyState } from "@/components/ui/empty-state";
import { SeverityBadge } from "@/components/ui/severity-badge";

export default function Page() {
  return (
    <>
      <PageHeader
        title="Exceptions"
        subtitle="Review and resolve exceptions requiring attention"
        actions={<SeverityBadge severity="high" />}
      />

      <div className="p-4">
        <EmptyState
          title="Exceptions list not connected yet"
          description="Phase 2 will replace this with a reviewable exceptions table with evidence linking and resolution flows."
        />
      </div>
    </>
  );
}
