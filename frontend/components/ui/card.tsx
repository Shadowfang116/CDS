'use client';

import { cn } from '@/lib/utils';
import { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  onClick?: () => void;
}

export function Card({ children, className, hover, onClick }: CardProps) {
  return (
    <div
      className={cn(
        'bg-slate-800/80 backdrop-blur-sm rounded-xl border border-slate-700/60',
        'shadow-lg shadow-black/10',
        hover && 'hover:border-slate-600 hover:bg-slate-800 transition-all duration-200 cursor-pointer',
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
    <div className={cn('px-5 py-4 border-b border-slate-700/50', className)}>
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
    <h3 className={cn('text-base font-semibold text-slate-100', className)}>
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
    <p className={cn('text-sm text-slate-400 mt-1', className)}>
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
    <div className={cn('px-5 py-4 border-t border-slate-700/50', className)}>
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
      <p className="text-sm font-medium text-slate-400 mb-1">{title}</p>
      <p className="text-3xl font-bold text-slate-100 tracking-tight">{value}</p>
      {subtitle && (
        <p className="text-sm text-slate-500 mt-1">{subtitle}</p>
      )}
      {trend && (
        <div className={cn(
          'flex items-center gap-1 text-sm mt-2',
          trend.positive ? 'text-emerald-400' : 'text-rose-400'
        )}>
          <span>{trend.positive ? '↑' : '↓'}</span>
          <span>{trend.value}%</span>
          <span className="text-slate-500">{trend.label}</span>
        </div>
      )}
    </Card>
  );
}

