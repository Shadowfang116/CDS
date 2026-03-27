import { CaseDetailShell } from "@/components/cases/case-detail-shell";
import { CaseDetailClient } from "@/components/cases/case-detail-client";
import { SetPageChrome } from "@/components/layout/set-page-chrome";
import { CaseStatusPill } from "@/components/ui/case-status-pill";
import { SeverityBadge } from "@/components/ui/severity-badge";

export default async function CaseDetailPage({ params }: any) {
  const { caseId } = params as { caseId: string };

  const status = "Review" as const;
  const highestSeverity = "high" as const;

  return (
    <>
      <SetPageChrome
        title="Case Review"
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Cases", href: "/dashboard/cases" },
          { label: String(caseId) },
        ]}
        actions={
          <div className="flex items-center gap-2">
            <CaseStatusPill status={status} />
            <SeverityBadge severity={highestSeverity} />
          </div>
        }
      />
      <CaseDetailShell
      caseId={caseId}
      status={status}
      highestSeverity={highestSeverity}
      openExceptions={3}
      openCps={2}
      rightPanel={null /* CaseDetailClient renders the panel */}
    >
      <CaseDetailClient caseId={caseId} />
      </CaseDetailShell>
    </>
  );
}
