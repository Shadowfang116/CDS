'use client';

import { cn } from '@/lib/utils';
import { ReactNode } from 'react';
import { Button } from "@/components/ui/button";

interface EmptyStateProps {
  icon?: ReactNode;
  title?: string;
  message?: string;
  description?: string;
  action?: ReactNode;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export function EmptyState({ 
  icon, 
  title, 
  message,
  description, 
  action, 
  actionLabel, 
  onAction, 
  className 
}: EmptyStateProps) {
  const resolvedTitle = title ?? message ?? "";

  return (
    <div
      className={cn(
        "flex min-h-[180px] flex-col items-center justify-center rounded-lg border border-[rgba(82,90,99,0.45)] bg-[rgba(24,28,32,0.88)] p-6 text-center",
        className
      )}
    >
      {icon && (
        <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-lg border border-[rgba(82,90,99,0.4)] bg-[rgba(34,39,45,0.9)]">
          {icon}
        </div>
      )}
      <div className="max-w-xl text-[15px] font-semibold tracking-[-0.02em] text-stone-100">{resolvedTitle}</div>
      {description ? (
        <div className="mt-2 max-w-xl text-sm leading-6 text-stone-400">{description}</div>
      ) : null}
      {action ? (
        <div className="mt-4">{action}</div>
      ) : actionLabel && onAction ? (
        <Button className="mt-4" onClick={onAction}>
          {actionLabel}
        </Button>
      ) : null}
    </div>
  );
}

// Default empty icon
export function EmptyIcon() {
  return (
    <svg className="w-6 h-6 text-stone-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5m6 4.125l2.25 2.25m0 0l2.25 2.25M12 13.875l2.25-2.25M12 13.875l-2.25 2.25M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
    </svg>
  );
}

