'use client';

import { useEffect, useMemo, useState } from 'react';

import {
  ONBOARDING_OPEN_EVENT,
  ONBOARDING_STEPS,
  ONBOARDING_STORAGE_KEY,
  type OnboardingStep,
} from '@/lib/onboarding-steps';

type OnboardingTourProps = {
  steps?: OnboardingStep[];
};

type RectLike = {
  top: number;
  left: number;
  width: number;
  height: number;
};

function readStorage(key: string): string | null {
  if (typeof window === 'undefined') {
    return null;
  }

  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeStorage(key: string, value: string): void {
  if (typeof window === 'undefined') {
    return;
  }

  try {
    localStorage.setItem(key, value);
  } catch {
    // no-op
  }
}

export function OnboardingTour({ steps = ONBOARDING_STEPS }: OnboardingTourProps) {
  const [open, setOpen] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [targetRect, setTargetRect] = useState<RectLike | null>(null);

  const currentStep = steps[stepIndex];

  useEffect(() => {
    if (readStorage(ONBOARDING_STORAGE_KEY) !== 'true') {
      setOpen(true);
      setStepIndex(0);
    }

    const handleOpen = () => {
      setOpen(true);
      setStepIndex(0);
    };

    window.addEventListener(ONBOARDING_OPEN_EVENT, handleOpen);
    return () => {
      window.removeEventListener(ONBOARDING_OPEN_EVENT, handleOpen);
    };
  }, []);

  useEffect(() => {
    if (!open || !currentStep) {
      return;
    }

    const recalc = () => {
      const node = document.querySelector(currentStep.target) as HTMLElement | null;
      if (!node) {
        setTargetRect(null);
        return;
      }

      const rect = node.getBoundingClientRect();
      setTargetRect({
        top: rect.top,
        left: rect.left,
        width: rect.width,
        height: rect.height,
      });
    };

    recalc();
    window.addEventListener('resize', recalc);
    window.addEventListener('scroll', recalc, true);

    return () => {
      window.removeEventListener('resize', recalc);
      window.removeEventListener('scroll', recalc, true);
    };
  }, [open, currentStep]);

  const closeTour = () => {
    writeStorage(ONBOARDING_STORAGE_KEY, 'true');
    setOpen(false);
  };

  const nextStep = () => {
    if (stepIndex >= steps.length - 1) {
      closeTour();
      return;
    }

    setStepIndex((value) => Math.min(value + 1, steps.length - 1));
  };

  const prevStep = () => {
    setStepIndex((value) => Math.max(value - 1, 0));
  };

  const tooltipStyle = useMemo(() => {
    if (!targetRect) {
      return {
        top: '20%',
        left: '50%',
        transform: 'translateX(-50%)',
      } as const;
    }

    const cardWidth = 340;
    const preferredLeft = targetRect.left + targetRect.width + 16;
    const fallbackLeft = Math.max(16, targetRect.left - cardWidth - 16);
    const fitsRight = preferredLeft + cardWidth < window.innerWidth - 16;

    return {
      top: `${Math.max(16, targetRect.top)}px`,
      left: `${fitsRight ? preferredLeft : fallbackLeft}px`,
      transform: 'none',
    } as const;
  }, [targetRect]);

  if (!open || !currentStep) {
    return null;
  }

  return (
    <>
      <div className="fixed inset-0 z-[120] bg-black/55" onClick={closeTour} />
      {targetRect ? (
        <div
          className="pointer-events-none fixed z-[121] rounded-lg border-2 border-[rgba(187,205,189,0.75)]"
          style={{
            top: targetRect.top - 6,
            left: targetRect.left - 6,
            width: targetRect.width + 12,
            height: targetRect.height + 12,
          }}
        >
          <span className="absolute inset-0 rounded-lg bdp-tour-ring" />
        </div>
      ) : null}

      <div className="fixed z-[122] w-[340px] rounded-xl border border-[rgba(127,138,149,0.35)] bg-[rgba(18,22,27,0.96)] p-4 shadow-[0_18px_42px_rgba(0,0,0,0.4)]" style={tooltipStyle}>
        <p className="text-xs font-medium uppercase tracking-[0.12em] text-stone-500">
          Step {stepIndex + 1} of {steps.length} — {currentStep.title}
        </p>
        <h3 className="mt-2 text-base font-semibold text-stone-100">{currentStep.title}</h3>
        <p className="mt-2 text-sm text-stone-300">{currentStep.description}</p>
        <p className="mt-2 text-xs text-[rgb(194,200,185)]">{currentStep.actionHint}</p>

        <div className="mt-4 flex items-center justify-between">
          <button
            type="button"
            onClick={prevStep}
            disabled={stepIndex === 0}
            className="rounded-md border border-[rgba(82,90,99,0.55)] px-3 py-1.5 text-xs text-stone-200 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Prev
          </button>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={closeTour}
              className="rounded-md border border-[rgba(82,90,99,0.55)] px-3 py-1.5 text-xs text-stone-200"
            >
              Close
            </button>
            <button
              type="button"
              onClick={nextStep}
              className="rounded-md bg-[rgb(187,205,189)] px-3 py-1.5 text-xs font-semibold text-zinc-900"
            >
              {stepIndex === steps.length - 1 ? 'Finish' : 'Next'}
            </button>
          </div>
        </div>
      </div>

      <style jsx global>{`
        @keyframes bdp-tour-pulse {
          0% {
            transform: scale(1);
            opacity: 0.95;
          }
          70% {
            transform: scale(1.04);
            opacity: 0.28;
          }
          100% {
            transform: scale(1.08);
            opacity: 0;
          }
        }

        .bdp-tour-ring {
          border: 2px solid rgba(187, 205, 189, 0.65);
          animation: bdp-tour-pulse 1.35s ease-out infinite;
        }
      `}</style>
    </>
  );
}


