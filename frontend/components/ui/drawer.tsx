'use client';

import { useEffect, useRef, useCallback, useState } from 'react';
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
  const closeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [shouldRender, setShouldRender] = useState(open);
  const [visible, setVisible] = useState(open);

  // Handle escape key
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    },
    [onClose]
  );

  useEffect(() => {
    if (open) {
      if (closeTimerRef.current) {
        clearTimeout(closeTimerRef.current);
        closeTimerRef.current = null;
      }
      setShouldRender(true);
      const frame = window.requestAnimationFrame(() => setVisible(true));
      return () => window.cancelAnimationFrame(frame);
    }

    setVisible(false);
    closeTimerRef.current = setTimeout(() => {
      setShouldRender(false);
      closeTimerRef.current = null;
    }, 180);

    return () => {
      if (closeTimerRef.current) {
        clearTimeout(closeTimerRef.current);
        closeTimerRef.current = null;
      }
    };
  }, [open]);

  // Focus trap and escape handler
  useEffect(() => {
    if (shouldRender) {
      previousActiveElement.current = document.activeElement;
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';

      // Focus the drawer
      const timeoutId = window.setTimeout(() => {
        drawerRef.current?.focus();
      }, 100);

      return () => {
        window.clearTimeout(timeoutId);
        document.removeEventListener('keydown', handleKeyDown);
        document.body.style.overflow = '';
        // Restore focus
        if (previousActiveElement.current instanceof HTMLElement) {
          previousActiveElement.current.focus();
        }
      };
    }
  }, [shouldRender, handleKeyDown]);

  if (!shouldRender) return null;

  return (
    <div className="fixed inset-0 z-50" aria-modal="true" role="dialog">
      {/* Backdrop */}
      <div
        data-state={visible ? 'open' : 'closed'}
        className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity duration-150 data-[state=closed]:pointer-events-none data-[state=closed]:opacity-0 data-[state=open]:opacity-100"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer panel */}
      <div
        ref={drawerRef}
        tabIndex={-1}
        data-state={visible ? 'open' : 'closed'}
        className={cn(
          'fixed right-0 top-0 h-full w-full border-l border-[rgba(82,90,99,0.34)] bg-[rgba(17,21,25,0.98)] shadow-[0_24px_64px_rgba(0,0,0,0.32)]',
          'transform transition-transform duration-150 ease-out',
          'focus:outline-none',
          'data-[state=open]:translate-x-0 data-[state=closed]:translate-x-full',
          widthClasses[width],
          className
        )}
      >
        {/* Header */}
        {(title || description) && (
          <div className="flex items-start justify-between border-b border-[rgba(82,90,99,0.34)] bg-[rgba(20,24,28,0.82)] p-6">
            <div>
              {title && (
                <h2 className="text-lg font-semibold text-stone-100">{title}</h2>
              )}
              {description && (
                <p className="mt-1 text-sm text-stone-400">{description}</p>
              )}
            </div>
            <button
              onClick={onClose}
              className="rounded-lg p-2 text-stone-400 transition-colors hover:bg-[rgba(34,39,45,0.9)] hover:text-stone-100"
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
  value?: string;
  onValueChange?: (value: string) => void;
  children: React.ReactNode;
}

export function DrawerTabs({ children }: TabsProps) {
  return (
    <div className="relative flex h-full flex-col">
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
        'flex border-b border-[rgba(82,90,99,0.34)] bg-[rgba(18,22,27,0.72)] px-6',
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
          ? 'text-stone-100'
          : 'text-stone-400 hover:text-stone-200'
      )}
    >
      <span className="flex items-center gap-2">
        {children}
        {typeof count === 'number' && (
          <span
            className={cn(
              'rounded-full px-1.5 py-0.5 text-xs',
              isActive
                ? 'bg-[rgba(152,161,135,0.14)] text-stone-100 ring-1 ring-[rgba(152,161,135,0.3)]'
                : 'bg-[rgba(34,39,45,0.82)] text-stone-400'
            )}
          >
            {count}
          </span>
        )}
      </span>
      {isActive && (
        <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[rgba(152,161,135,0.82)]" />
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
  return (
    <div
      role="tabpanel"
      aria-hidden={value !== activeValue}
      data-state={value === activeValue ? 'active' : 'inactive'}
      className={cn(
        'flex-1 overflow-y-auto transition-opacity duration-150 data-[state=inactive]:pointer-events-none data-[state=inactive]:absolute data-[state=inactive]:inset-0 data-[state=inactive]:opacity-0 data-[state=active]:relative data-[state=active]:opacity-100',
        className
      )}
    >
      {children}
    </div>
  );
}
