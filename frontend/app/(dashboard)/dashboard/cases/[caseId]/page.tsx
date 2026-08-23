import { Suspense } from 'react';
import { MatterWorkbench } from '@/components/workbench/matter-workbench';

type CaseDetailPageProps = {
  params: Promise<{ caseId: string }>;
};

export default async function CaseDetailPage({ params }: CaseDetailPageProps) {
  const { caseId } = await params;
  return (
    <Suspense fallback={<p className="p-6 text-sm text-muted-foreground">Loading matter…</p>}>
      <MatterWorkbench caseId={caseId} />
    </Suspense>
  );
}
