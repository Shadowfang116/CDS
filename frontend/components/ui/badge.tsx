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
    default: 'border-[rgba(82,90,99,0.5)] bg-[rgba(53,60,67,0.9)] text-stone-200',
    success: 'border-[rgba(111,140,115,0.34)] bg-[rgba(111,140,115,0.16)] text-[rgb(187,205,189)]',
    warning: 'border-[rgba(184,151,95,0.34)] bg-[rgba(184,151,95,0.16)] text-[rgb(219,194,137)]',
    error: 'border-[rgba(189,90,86,0.34)] bg-[rgba(189,90,86,0.16)] text-[rgb(219,156,153)]',
    info: 'border-[rgba(126,133,111,0.34)] bg-[rgba(126,133,111,0.16)] text-[rgb(194,200,185)]',
    neutral: 'border-[rgba(82,90,99,0.45)] bg-[rgba(34,39,45,0.85)] text-stone-300',
    outline: 'border-[rgba(82,90,99,0.55)] bg-transparent text-stone-200',
    secondary: 'border-[rgba(82,90,99,0.45)] bg-[rgba(34,39,45,0.85)] text-stone-300',
    destructive: 'border-[rgba(189,90,86,0.34)] bg-[rgba(189,90,86,0.16)] text-[rgb(219,156,153)]',
  };

  const sizes = {
    sm: 'min-h-5 px-2.5 py-0.5 text-[10px]',
    md: 'min-h-6 px-2.5 py-1 text-[11px]',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 whitespace-nowrap rounded-md border font-semibold uppercase leading-none tracking-[0.06em]',
        variants[variant],
        sizes[size],
        className
      )}
    >
      {children}
    </span>
  );
}

