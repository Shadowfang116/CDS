import { PageHeader } from "@/components/ui/page-header";
import { CasesTable } from "@/components/cases/cases-table";
import { casesColumns } from "@/components/cases/cases-columns";
import { CaseRow } from "@/components/cases/case-types";

const MOCK: CaseRow[] = [
  {
    id: "f14f2276-96c0-4f06-aea8-5a9c9eb9a9c8",
    borrower_name: "Sample Borrower",
    property_type: "Society Plot",
    status: "Review",
    highest_severity: "high",
    open_exceptions: 3,
    open_cps: 2,
    updated_at: new Date().toISOString(),
  },
  {
    id: "8fa48b2d-c169-450e-8b16-8855b6a83def",
    borrower_name: "Customer / Applicant",
    property_type: "Urban House",
    status: "Processing",
    highest_severity: "medium",
    open_exceptions: 1,
    open_cps: 0,
    updated_at: new Date(Date.now() - 1000 * 60 * 90).toISOString(),
  },
];

export default function CasesPage() {
  return (
    <>
      <PageHeader
        title="Cases"
        subtitle="New → Processing → Review → Pending Docs → Ready for Approval → Approved/Rejected → Closed"
      />

      <div className="p-4">
        <CasesTable data={MOCK} columns={casesColumns} />
      </div>
    </>
  );
}
