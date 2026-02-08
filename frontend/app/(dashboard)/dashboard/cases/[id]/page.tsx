import { CaseDetailShell } from "@/components/cases/case-detail-shell";
import { CaseDetailClient } from "@/components/cases/case-detail-client";

export default async function CaseDetailPage(props: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await props.params;

  const status = "Review" as const;
  const highestSeverity = "high" as const;

  return (
    <CaseDetailShell
      caseId={id}
      status={status}
      highestSeverity={highestSeverity}
      openExceptions={3}
      openCps={2}
      rightPanel={null /* CaseDetailClient renders the panel */}
    >
      <CaseDetailClient caseId={id} />
    </CaseDetailShell>
  );
}
