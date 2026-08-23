'use client';

import { cn } from '@/lib/utils';
import { ReactNode } from 'react';

interface CardProps {
  children?: ReactNode;
  className?: string;
  hover?: boolean;
  onClick?: () => void;
}

export function Card({ children, className, hover, onClick }: CardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border border-border bg-card',
        hover && 'cursor-pointer hover:bg-muted',
        onClick && 'cursor-pointer',
        className
      )}
      onClick={onClick}
    >
      {children}
    </div>
  );
}

interface CardHeaderProps {
  children: ReactNode;
  className?: string;
}

export function CardHeader({ children, className }: CardHeaderProps) {
  return (
    <div className={cn('flex flex-col gap-1 border-b border-border px-5 py-4', className)}>
      {children}
    </div>
  );
}

interface CardTitleProps {
  children: ReactNode;
  className?: string;
}

export function CardTitle({ children, className }: CardTitleProps) {
  return (
    <h3 className={cn('font-display text-base font-semibold tracking-[-0.03em] text-card-foreground', className)}>
      {children}
    </h3>
  );
}

interface CardDescriptionProps {
  children: ReactNode;
  className?: string;
}

export function CardDescription({ children, className }: CardDescriptionProps) {
  return (
    <p className={cn('text-sm text-muted-foreground', className)}>
      {children}
    </p>
  );
}

interface CardContentProps {
  children: ReactNode;
  className?: string;
}

export function CardContent({ children, className }: CardContentProps) {
  return (
    <div className={cn('px-5 py-4', className)}>
      {children}
    </div>
  );
}

interface CardFooterProps {
  children: ReactNode;
  className?: string;
}

export function CardFooter({ children, className }: CardFooterProps) {
  return (
    <div className={cn('border-t border-border px-5 py-4', className)}>
      {children}
    </div>
  );
}

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: {
    value: number;
    label: string;
    positive?: boolean;
  };
  className?: string;
  loading?: boolean;
}

export function MetricCard({ title, value, subtitle, trend, className, loading }: MetricCardProps) {
  if (loading) {
    return (
      <Card className={cn('p-5', className)}>
        <div className="flex flex-col gap-3">
          <div className="h-4 w-24 rounded bg-muted" />
          <div className="h-9 w-16 rounded bg-muted" />
          <div className="h-3 w-32 rounded bg-muted" />
        </div>
      </Card>
    );
  }

  return (
    <Card className={cn('p-5', className)}>
      <p className="mb-2 text-[11px] font-medium text-muted-foreground">{title}</p>
      <p className="font-display text-3xl font-semibold tracking-[-0.04em] text-primary">{value}</p>
      {subtitle && (
        <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
      )}
      {trend && (
        <div className={cn(
          'mt-3 flex items-center gap-1 text-xs font-medium uppercase tracking-[0.08em]',
          trend.positive ? 'text-primary' : 'text-destructive'
        )}>
          <span>{trend.positive ? '↑' : '↓'}</span>
          <span>{trend.value}%</span>
          <span className="text-muted-foreground">{trend.label}</span>
        </div>
      )}
    </Card>
  );
}
