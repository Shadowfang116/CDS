'use client';

import * as React from 'react';

import { cn } from '@/lib/utils';

type AlertProps = React.HTMLAttributes<HTMLDivElement> & {
  variant?: 'default' | 'destructive';
};

const variants = {
  default: 'border-[rgba(184,151,95,0.34)] bg-[rgba(184,151,95,0.12)] text-[rgb(219,194,137)]',
  destructive: 'border-[rgba(189,90,86,0.34)] bg-[rgba(189,90,86,0.12)] text-[rgb(219,156,153)]',
};

const Alert = React.forwardRef<HTMLDivElement, AlertProps>(({ className, variant = 'default', ...props }, ref) => (
  <div
    ref={ref}
    role='alert'
    className={cn(
      'relative w-full rounded-lg border px-4 py-3 text-sm shadow-[inset_0_1px_0_rgba(255,255,255,0.02)]',
      variants[variant],
      className,
    )}
    {...props}
  />
));
Alert.displayName = 'Alert';

const AlertTitle = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => (
    <p ref={ref} className={cn('mb-1 font-semibold leading-none tracking-tight', className)} {...props} />
  ),
);
AlertTitle.displayName = 'AlertTitle';

const AlertDescription = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('text-sm leading-relaxed [&_p]:leading-relaxed', className)} {...props} />
  ),
);
AlertDescription.displayName = 'AlertDescription';

export { Alert, AlertDescription, AlertTitle };