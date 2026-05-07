import { CaseWorkspace } from '@/components/cases/case-workspace';

type CaseDetailPageProps = {
  params: Promise<{ caseId: string }>;
};

export default async function CaseDetailPage({ params }: CaseDetailPageProps) {
  const { caseId } = await params;

  return <CaseWorkspace caseId={caseId} />;
}
