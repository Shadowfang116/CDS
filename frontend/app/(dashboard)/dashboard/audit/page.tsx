import { PageHeader } from "@/components/ui/page-header";
import { EmptyState } from "@/components/ui/empty-state";

export default function Page() {
  return (
    <>
      <PageHeader
        title="Audit Log"
        subtitle="View activity history and changes"
      />

      <div className="p-4">
        <EmptyState
          title="Audit log not connected yet"
          description="Phase 4 will replace this with an audit log table with filters and diff preview."
        />
      </div>
    </>
  );
}
