'use client';

import { cn } from '@/lib/utils';
import { Slot } from '@radix-ui/react-slot';
import { ButtonHTMLAttributes, forwardRef, ReactNode } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'primary' | 'secondary' | 'ghost' | 'danger' | 'destructive' | 'outline';
  size?: 'sm' | 'md' | 'lg' | 'icon';
  children: ReactNode;
  loading?: boolean;
  asChild?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', children, loading, disabled, asChild = false, ...props }, ref) => {
    const baseStyles =
      'relative inline-flex items-center justify-center overflow-hidden rounded-md border text-sm font-medium transition-[transform,background-color,border-color,color,box-shadow] duration-200 ease-out focus:outline-none focus:ring-2 focus:ring-[rgba(154,165,137,0.85)] focus:ring-offset-0 disabled:cursor-not-allowed disabled:opacity-50 disabled:transform-none active:translate-y-px';

    const variants = {
      default:
        'border-[rgba(143,154,127,0.85)] bg-[linear-gradient(180deg,rgba(161,173,142,0.98),rgba(133,144,116,0.96))] text-[#111411] shadow-[0_10px_24px_rgba(103,116,83,0.18)] before:absolute before:inset-0 before:bg-[linear-gradient(120deg,transparent,rgba(255,255,255,0.22),transparent)] before:translate-x-[-140%] before:transition-transform before:duration-500 hover:border-[rgba(176,188,159,0.92)] hover:shadow-[0_14px_30px_rgba(103,116,83,0.22)] hover:before:translate-x-[140%]',
      primary:
        'border-[rgba(143,154,127,0.85)] bg-[linear-gradient(180deg,rgba(161,173,142,0.98),rgba(133,144,116,0.96))] text-[#111411] shadow-[0_10px_24px_rgba(103,116,83,0.18)] before:absolute before:inset-0 before:bg-[linear-gradient(120deg,transparent,rgba(255,255,255,0.22),transparent)] before:translate-x-[-140%] before:transition-transform before:duration-500 hover:border-[rgba(176,188,159,0.92)] hover:shadow-[0_14px_30px_rgba(103,116,83,0.22)] hover:before:translate-x-[140%]',
      secondary:
        'border-[rgba(91,101,112,0.62)] bg-[rgba(32,38,43,0.9)] text-stone-100 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)] hover:border-[rgba(115,126,139,0.78)] hover:bg-[rgba(40,47,53,0.96)] hover:text-stone-50',
      ghost: 'border-transparent bg-transparent text-stone-300 hover:bg-[rgba(44,50,57,0.72)] hover:text-stone-100',
      danger:
        'border-[rgba(170,88,84,0.72)] bg-[linear-gradient(180deg,rgba(157,75,72,0.95),rgba(132,58,56,0.94))] text-stone-50 shadow-[0_10px_24px_rgba(124,54,51,0.16)] hover:border-[rgba(197,110,105,0.82)] hover:shadow-[0_14px_30px_rgba(124,54,51,0.2)]',
      destructive:
        'border-[rgba(170,88,84,0.72)] bg-[linear-gradient(180deg,rgba(157,75,72,0.95),rgba(132,58,56,0.94))] text-stone-50 shadow-[0_10px_24px_rgba(124,54,51,0.16)] hover:border-[rgba(197,110,105,0.82)] hover:shadow-[0_14px_30px_rgba(124,54,51,0.2)]',
      outline:
        'border-[rgba(91,101,112,0.62)] bg-[rgba(18,22,26,0.44)] text-stone-200 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)] hover:border-[rgba(136,148,161,0.76)] hover:bg-[rgba(32,38,43,0.88)] hover:text-stone-50',
    };

    const sizes = {
      sm: 'h-8 px-3 text-sm gap-1.5',
      md: 'h-9 px-4 gap-2',
      lg: 'h-10 px-5 text-sm gap-2.5',
      icon: 'h-8 w-8 p-0',
    };

    if (asChild) {
      return (
        <Slot
          ref={ref}
          className={cn(baseStyles, variants[variant], sizes[size], className)}
          aria-disabled={disabled || loading}
          {...props}
        >
          {children}
        </Slot>
      );
    }

    const Comp = asChild ? Slot : 'button';

    return (
      <Comp
        ref={ref}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        disabled={disabled || loading}
        {...props}
      >
        <span className="relative z-10 inline-flex items-center gap-2">
        {loading && (
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        )}
        {children}
        </span>
      </Comp>
    );
  }
);

Button.displayName = 'Button';

