import { PageHeader } from "@/components/ui/page-header";
import { EmptyState } from "@/components/ui/empty-state";
import { CaseStatusPill } from "@/components/ui/case-status-pill";

export default function Page() {
  return (
    <>
      <PageHeader
        title="Conditions Precedent (CP)"
        subtitle="Track CP completion status and due dates"
        actions={<CaseStatusPill status="Pending Docs" />}
      />

      <div className="p-4">
        <EmptyState
          title="CP list not connected yet"
          description="Phase 2 will replace this with a CP tracking table showing due dates, status, and evidence requirements."
        />
      </div>
    </>
  );
}
