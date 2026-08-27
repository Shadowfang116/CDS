'use client';

import { cn } from '@/lib/utils';
import { ReactNode } from 'react';

interface BadgeProps {
  children: ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info' | 'neutral' | 'outline' | 'secondary' | 'destructive';
  size?: 'sm' | 'md';
  className?: string;
}

export function Badge({ children, variant = 'default', size = 'sm', className }: BadgeProps) {
  const variants = {
    default: 'border-border bg-muted text-foreground',
    success: 'border-[hsl(var(--sage)/0.35)] bg-[hsl(var(--sage)/0.12)] text-[hsl(var(--sage))]',
    warning: 'border-[hsl(var(--gold)/0.35)] bg-[hsl(var(--gold)/0.12)] text-[hsl(var(--gold))]',
    error: 'border-[hsl(var(--status-high)/0.35)] bg-[hsl(var(--status-high)/0.12)] text-[hsl(var(--status-high))]',
    info: 'border-[hsl(var(--info)/0.35)] bg-[hsl(var(--info)/0.12)] text-[hsl(var(--info))]',
    neutral: 'border-border bg-muted text-muted-foreground',
    outline: 'border-border bg-transparent text-foreground',
    secondary: 'border-border bg-muted text-muted-foreground',
    destructive: 'border-[hsl(var(--status-high)/0.35)] bg-[hsl(var(--status-high)/0.12)] text-[hsl(var(--status-high))]',
  };

  const sizes = {
    sm: 'min-h-5 px-2.5 py-0.5 text-[11px]',
    md: 'min-h-6 px-2.5 py-1 text-[11px]',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 whitespace-nowrap rounded-md border font-semibold leading-none tracking-wide',
        variants[variant],
        sizes[size],
        className
      )}
    >
      {children}
    </span>
  );
}

