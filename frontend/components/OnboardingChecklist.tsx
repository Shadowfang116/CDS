'use client';

import { useEffect, useMemo, useState } from 'react';
import { usePathname, useSearchParams } from 'next/navigation';

const CHECKLIST_STORAGE_KEY = 'bdp_checklist';

const CHECKLIST_STEPS = [
  { id: 'open_demo_case', label: 'Open demo case' },
  { id: 'review_documents', label: 'Review documents' },
  { id: 'verify_ocr_fields', label: 'Verify OCR fields' },
  { id: 'review_exceptions', label: 'Review exceptions' },
  { id: 'check_cp_list', label: 'Check CP list' },
  { id: 'generate_bank_pack', label: 'Generate bank pack' },
] as const;

type ChecklistState = {
  open: boolean;
  completed: Record<string, boolean>;
};

function isCaseDetailPath(pathname: string): boolean {
  return /^\/dashboard\/cases\/[^/]+$/.test(pathname);
}

function readChecklist(): ChecklistState {
  if (typeof window === 'undefined') {
    return { open: true, completed: {} };
  }

  try {
    const raw = localStorage.getItem(CHECKLIST_STORAGE_KEY);
    if (!raw) {
      return { open: true, completed: {} };
    }

    const parsed = JSON.parse(raw) as ChecklistState;
    return {
      open: parsed.open ?? true,
      completed: parsed.completed ?? {},
    };
  } catch {
    return { open: true, completed: {} };
  }
}

function persistChecklist(state: ChecklistState): void {
  if (typeof window === 'undefined') {
    return;
  }

  try {
    localStorage.setItem(CHECKLIST_STORAGE_KEY, JSON.stringify(state));
  } catch {
    // no-op
  }
}

export function OnboardingChecklist() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [open, setOpen] = useState(true);
  const [completed, setCompleted] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const existing = readChecklist();
    setOpen(existing.open);
    setCompleted(existing.completed);
  }, []);

  useEffect(() => {
    const tab = searchParams.get('tab');
    const updates: Record<string, boolean> = {};

    if (isCaseDetailPath(pathname)) {
      updates.open_demo_case = true;
    }

    if (pathname === '/dashboard/cases' || tab === 'documents') {
      updates.review_documents = true;
    }

    if (tab === 'ocr-extractions' || pathname.includes('/ocr')) {
      updates.verify_ocr_fields = true;
    }

    if (pathname === '/dashboard/exceptions' || tab === 'exceptions') {
      updates.review_exceptions = true;
    }

    if (pathname === '/dashboard/cp' || tab === 'cps') {
      updates.check_cp_list = true;
    }

    if (tab === 'exports') {
      updates.generate_bank_pack = true;
    }

    if (Object.keys(updates).length === 0) {
      return;
    }

    setCompleted((previous) => {
      const merged = { ...previous, ...updates };
      persistChecklist({ open, completed: merged });
      return merged;
    });
  }, [open, pathname, searchParams]);

  const completion = useMemo(() => {
    const done = CHECKLIST_STEPS.filter((step) => completed[step.id]).length;
    const percent = Math.round((done / CHECKLIST_STEPS.length) * 100);
    return { done, percent };
  }, [completed]);

  const toggleOpen = () => {
    setOpen((previous) => {
      const next = !previous;
      persistChecklist({ open: next, completed });
      return next;
    });
  };

  return (
    <>
      {open ? (
        <div className="fixed bottom-20 right-5 z-[90] w-[300px] rounded-xl border border-[rgba(127,138,149,0.3)] bg-[rgba(18,22,27,0.95)] p-4 shadow-[0_16px_36px_rgba(0,0,0,0.35)]">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-stone-100">Complete Your First Case</h3>
            <span className="text-xs text-stone-400">{completion.percent}%</span>
          </div>
          <div className="mt-2 h-1.5 w-full rounded-full bg-[rgba(82,90,99,0.42)]">
            <div
              className="h-1.5 rounded-full bg-[rgb(187,205,189)] transition-all"
              style={{ width: `${completion.percent}%` }}
            />
          </div>
          <div className="mt-3 space-y-2">
            {CHECKLIST_STEPS.map((step) => (
              <div key={step.id} className="flex items-center gap-2 text-xs text-stone-300">
                <span className={`inline-flex h-4 w-4 items-center justify-center rounded-full border ${completed[step.id] ? 'border-[rgb(187,205,189)] bg-[rgba(187,205,189,0.2)] text-[rgb(187,205,189)]' : 'border-[rgba(127,138,149,0.45)] text-stone-500'}`}>
                  {completed[step.id] ? '✓' : ''}
                </span>
                <span>{step.label}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <button
        type="button"
        onClick={toggleOpen}
        className="fixed bottom-5 right-5 z-[91] rounded-full border border-[rgba(127,138,149,0.4)] bg-[rgba(21,25,29,0.95)] px-4 py-2 text-xs font-medium text-stone-100 shadow-[0_10px_24px_rgba(0,0,0,0.35)]"
      >
        {open ? 'Hide Checklist' : 'Show Checklist'}
      </button>
    </>
  );
}
