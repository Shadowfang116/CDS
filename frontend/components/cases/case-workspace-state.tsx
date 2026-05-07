'use client';

import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';
import { Skeleton, SkeletonCard, SkeletonText } from '@/components/ui/skeleton';

export function CaseWorkspaceSkeleton() {
  return (
    <div className="space-y-6 p-6">
      <div className="rounded-lg border border-[rgba(82,90,99,0.4)] bg-[rgba(24,28,32,0.9)] px-5 py-4">
        <div className="grid gap-4 lg:grid-cols-[1.4fr_repeat(3,minmax(0,1fr))]">
          <div className="space-y-3">
            <Skeleton className="h-3 w-24" />
            <Skeleton className="h-8 w-80" />
            <Skeleton className="h-4 w-56" />
          </div>
          {Array.from({ length: 3 }).map((_, index) => (
            <SkeletonCard key={index} className="rounded-md border-[rgba(82,90,99,0.35)] bg-[rgba(34,39,45,0.75)]" />
          ))}
        </div>
      </div>

      <div className="flex gap-4 overflow-x-auto border-b border-[rgba(82,90,99,0.32)] pb-3">
        {Array.from({ length: 6 }).map((_, index) => (
          <Skeleton key={index} className="h-4 w-28" />
        ))}
      </div>

      <CaseTabSkeleton />
    </div>
  );
}

export function CaseTabSkeleton() {
  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-[rgba(82,90,99,0.45)] bg-[rgba(24,28,32,0.88)] p-5">
        <Skeleton className="mb-3 h-6 w-56" />
        <SkeletonText lines={2} className="max-w-3xl" />
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <SkeletonCard className="min-h-[240px]" />
        <SkeletonCard className="min-h-[240px]" />
      </div>
    </div>
  );
}

export function CaseNotFoundState(props: {
  onBack: () => void;
  title?: string;
  description?: string;
}) {
  const {
    onBack,
    title = 'Matter not found',
    description = 'This matter does not exist or you do not have access. Return to the matters list to continue.',
  } = props;

  return (
    <div className="p-6">
      <EmptyState
        title={title}
        description={description}
        action={
          <Button variant="outline" onClick={onBack}>
            Back to Cases
          </Button>
        }
      />
    </div>
  );
}
