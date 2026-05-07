import Link from 'next/link';

import { SetPageChrome } from '@/components/layout/set-page-chrome';
import { Button } from '@/components/ui/button';
import { PRODUCT_WALKTHROUGH_STEPS } from '@/config/product-walkthrough';

export default function TutorialPage() {
  return (
    <div className="space-y-8">
      <SetPageChrome
        title="Tutorial"
        subtitle="Guided walkthrough of the diligence workflow"
        breadcrumbs={[{ label: 'Tutorial' }]}
      />

      <section className="overflow-hidden rounded-[30px] border border-[rgba(127,138,149,0.18)] bg-[linear-gradient(135deg,rgba(19,23,28,0.98),rgba(32,26,19,0.96))] p-8 shadow-[0_24px_60px_rgba(0,0,0,0.22)]">
        <div className="max-w-3xl space-y-4">
          <p className="text-xs font-medium uppercase tracking-[0.22em] text-[rgba(210,191,156,0.72)]">
            Product Walkthrough
          </p>
          <h1 className="font-display text-[2.2rem] font-semibold tracking-[-0.055em] text-stone-100">
            Review the end-to-end legal diligence flow for Pakistan property-backed finance matters.
          </h1>
          <p className="text-sm leading-7 text-[rgba(224,228,232,0.78)]">
            This guide follows the same path a Reviewer and Approver use in production: intake, OCR validation, Exceptions, CP closure, dossier confirmation, audit review, export drafting, and final approval governance.
          </p>
          <div className="flex flex-wrap gap-3 pt-2">
            <Button asChild className="h-10 text-sm">
              <Link href="/dashboard">Open Dashboard</Link>
            </Button>
            <Button asChild variant="outline" className="h-10 border-[rgba(127,138,149,0.22)] bg-transparent text-sm text-stone-200">
              <Link href="/dashboard/cases">Open Cases</Link>
            </Button>
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        {PRODUCT_WALKTHROUGH_STEPS.map((section, index) => (
          <article
            key={section.title}
            className="rounded-[24px] border border-[rgba(127,138,149,0.16)] bg-[rgba(21,25,29,0.92)] p-6 shadow-[0_18px_44px_rgba(0,0,0,0.16)]"
          >
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-[rgba(167,175,183,0.62)]">
              Step {index + 1}
            </p>
            <h2 className="mt-2 text-xl font-semibold tracking-[-0.03em] text-stone-100">
              {section.title}
            </h2>
            <p className="mt-3 text-sm leading-7 text-[rgba(210,215,220,0.78)]">
              {section.description}
            </p>
          </article>
        ))}
      </section>
    </div>
  );
}
