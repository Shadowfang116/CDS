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
        'rounded-[1.1rem] border border-[rgba(86,96,107,0.48)] bg-[linear-gradient(180deg,rgba(24,29,33,0.96),rgba(20,24,28,0.96))] shadow-[0_18px_40px_rgba(0,0,0,0.18),inset_0_1px_0_rgba(255,255,255,0.03)] backdrop-blur-[18px]',
        hover && 'cursor-pointer hover:border-[rgba(126,138,152,0.72)] hover:bg-[linear-gradient(180deg,rgba(30,36,40,0.98),rgba(22,27,31,0.98))]',
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
    <div className={cn('border-b border-[rgba(82,90,99,0.28)] px-5 py-4', className)}>
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
    <h3 className={cn('font-display text-[1.02rem] font-semibold tracking-[-0.03em] text-stone-100', className)}>
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
    <p className={cn('mt-1 text-sm text-stone-400', className)}>
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
    <div className={cn('border-t border-[rgba(82,90,99,0.4)] px-5 py-4', className)}>
      {children}
    </div>
  );
}

// Metric Card for dashboard KPIs
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
        <div className="animate-pulse">
          <div className="h-4 w-24 bg-slate-700/50 rounded mb-3" />
          <div className="h-9 w-16 bg-slate-700/50 rounded mb-2" />
          <div className="h-3 w-32 bg-slate-700/50 rounded" />
        </div>
      </Card>
    );
  }

  return (
    <Card className={cn('p-5', className)}>
      <p className="mb-2 text-[11px] font-medium text-stone-500">{title}</p>
      <p className="font-display text-3xl font-semibold tracking-[-0.04em] text-stone-100">{value}</p>
      {subtitle && (
        <p className="mt-1 text-sm text-stone-400">{subtitle}</p>
      )}
      {trend && (
        <div className={cn(
          'mt-3 flex items-center gap-1 text-xs font-medium uppercase tracking-[0.08em]',
          trend.positive ? 'text-[rgb(187,205,189)]' : 'text-[rgb(219,156,153)]'
        )}>
          <span>{trend.positive ? '↑' : '↓'}</span>
          <span>{trend.value}%</span>
          <span className="text-stone-500">{trend.label}</span>
        </div>
      )}
    </Card>
  );
}

