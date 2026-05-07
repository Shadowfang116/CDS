'use client';

import React, { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react';
import { cn } from '@/lib/utils';

type ToastVariant = 'success' | 'error' | 'info';

type ToastItem = {
  id: string;
  title: string;
  description?: string;
  variant: ToastVariant;
};

type ToastOptions = {
  title: string;
  description?: string;
  variant?: ToastVariant;
  durationMs?: number;
};

type ToastContextValue = {
  toast: (options: ToastOptions) => void;
  dismiss: (id: string) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

function getToastClasses(variant: ToastVariant): string {
  switch (variant) {
    case 'success':
      return 'border-[rgba(88,140,102,0.35)] bg-[rgba(24,32,28,0.96)] text-[rgb(187,205,189)]';
    case 'error':
      return 'border-[rgba(189,90,86,0.36)] bg-[rgba(43,24,24,0.96)] text-[rgb(240,205,202)]';
    case 'info':
    default:
      return 'border-[rgba(82,90,99,0.45)] bg-[rgba(24,28,32,0.96)] text-stone-200';
  }
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const timeoutsRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  const dismiss = useCallback((id: string) => {
    const timeoutId = timeoutsRef.current.get(id);
    if (timeoutId) {
      clearTimeout(timeoutId);
      timeoutsRef.current.delete(id);
    }
    setItems((current) => current.filter((item) => item.id !== id));
  }, []);

  const toast = useCallback(
    ({ title, description, variant = 'info', durationMs = variant === 'error' ? 5200 : 3200 }: ToastOptions) => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      setItems((current) => [...current, { id, title, description, variant }]);

      const timeoutId = setTimeout(() => {
        dismiss(id);
      }, durationMs);

      timeoutsRef.current.set(id, timeoutId);
    },
    [dismiss]
  );

  const value = useMemo(() => ({ toast, dismiss }), [toast, dismiss]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 top-4 z-[70] flex justify-center px-4">
        <div className="flex w-full max-w-md flex-col gap-2">
          {items.map((item) => (
            <div
              key={item.id}
              className={cn(
                'pointer-events-auto rounded-lg border px-4 py-3 shadow-[0_18px_48px_rgba(0,0,0,0.28)] transition-opacity duration-150',
                getToastClasses(item.variant)
              )}
              role="status"
              aria-live="polite"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-sm font-medium">{item.title}</div>
                  {item.description ? (
                    <div className="mt-1 text-xs text-stone-400">{item.description}</div>
                  ) : null}
                </div>
                <button
                  type="button"
                  onClick={() => dismiss(item.id)}
                  className="rounded-md p-1 text-stone-500 transition-colors hover:text-stone-100"
                  aria-label="Dismiss notification"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}
