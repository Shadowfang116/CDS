'use client';

import { useEffect, useRef, useCallback } from 'react';
import { cn } from '@/lib/utils';

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  children: React.ReactNode;
  className?: string;
  width?: 'sm' | 'md' | 'lg' | 'xl';
}

const widthClasses = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
};

export function Drawer({
  open,
  onClose,
  title,
  description,
  children,
  className,
  width = 'lg',
}: DrawerProps) {
  const drawerRef = useRef<HTMLDivElement>(null);
  const previousActiveElement = useRef<Element | null>(null);

  // Handle escape key
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    },
    [onClose]
  );

  // Focus trap and escape handler
  useEffect(() => {
    if (open) {
      previousActiveElement.current = document.activeElement;
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';

      // Focus the drawer
      setTimeout(() => {
        drawerRef.current?.focus();
      }, 100);

      return () => {
        document.removeEventListener('keydown', handleKeyDown);
        document.body.style.overflow = '';
        // Restore focus
        if (previousActiveElement.current instanceof HTMLElement) {
          previousActiveElement.current.focus();
        }
      };
    }
  }, [open, handleKeyDown]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50" aria-modal="true" role="dialog">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity duration-300"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer panel */}
      <div
        ref={drawerRef}
        tabIndex={-1}
        className={cn(
          'fixed right-0 top-0 h-full w-full bg-slate-900 border-l border-slate-700/50 shadow-2xl',
          'transform transition-transform duration-300 ease-out',
          'focus:outline-none',
          open ? 'translate-x-0' : 'translate-x-full',
          widthClasses[width],
          className
        )}
      >
        {/* Header */}
        {(title || description) && (
          <div className="flex items-start justify-between p-6 border-b border-slate-700/50">
            <div>
              {title && (
                <h2 className="text-lg font-semibold text-slate-100">{title}</h2>
              )}
              {description && (
                <p className="mt-1 text-sm text-slate-400">{description}</p>
              )}
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
              aria-label="Close drawer"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-y-auto h-[calc(100vh-80px)]">
          {children}
        </div>
      </div>
    </div>
  );
}

// Tab components for drawer
interface TabsProps {
  value: string;
  onValueChange: (value: string) => void;
  children: React.ReactNode;
}

export function DrawerTabs({ value, onValueChange, children }: TabsProps) {
  return (
    <div className="flex flex-col h-full">
      {children}
    </div>
  );
}

interface TabListProps {
  children: React.ReactNode;
  className?: string;
}

export function DrawerTabList({ children, className }: TabListProps) {
  return (
    <div
      className={cn(
        'flex border-b border-slate-700/50 px-6',
        className
      )}
      role="tablist"
    >
      {children}
    </div>
  );
}

interface TabTriggerProps {
  value: string;
  activeValue: string;
  onSelect: (value: string) => void;
  children: React.ReactNode;
  count?: number;
}

export function DrawerTabTrigger({
  value,
  activeValue,
  onSelect,
  children,
  count,
}: TabTriggerProps) {
  const isActive = value === activeValue;

  return (
    <button
      role="tab"
      aria-selected={isActive}
      onClick={() => onSelect(value)}
      className={cn(
        'relative px-4 py-3 text-sm font-medium transition-colors',
        isActive
          ? 'text-cyan-400'
          : 'text-slate-400 hover:text-slate-200'
      )}
    >
      <span className="flex items-center gap-2">
        {children}
        {typeof count === 'number' && (
          <span
            className={cn(
              'px-1.5 py-0.5 text-xs rounded-full',
              isActive
                ? 'bg-cyan-400/20 text-cyan-400'
                : 'bg-slate-700 text-slate-400'
            )}
          >
            {count}
          </span>
        )}
      </span>
      {isActive && (
        <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-400" />
      )}
    </button>
  );
}

interface TabContentProps {
  value: string;
  activeValue: string;
  children: React.ReactNode;
  className?: string;
}

export function DrawerTabContent({
  value,
  activeValue,
  children,
  className,
}: TabContentProps) {
  if (value !== activeValue) return null;

  return (
    <div
      role="tabpanel"
      className={cn('flex-1 overflow-y-auto', className)}
    >
      {children}
    </div>
  );
}
