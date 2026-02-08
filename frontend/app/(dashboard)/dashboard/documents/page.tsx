import { PageHeader } from "@/components/ui/page-header";
import { EmptyState } from "@/components/ui/empty-state";

export default function Page() {
  return (
    <>
      <PageHeader
        title="Documents"
        subtitle="View and manage case documents"
      />

      <div className="p-4">
        <EmptyState
          title="Documents list not connected yet"
          description="Phase 3 will replace this with a document viewer with thumbnails, OCR text panel, and evidence linking."
        />
      </div>
    </>
  );
}
