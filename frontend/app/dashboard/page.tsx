'use client';

import { Suspense } from 'react';
import { InboxView } from '@/components/inbox/inbox-view';

export default function DashboardInboxPage() {
  return (
    <Suspense fallback={<p className="p-6 text-sm text-muted-foreground">Loading inbox…</p>}>
      <InboxView />
    </Suspense>
  );
}
