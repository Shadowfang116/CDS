'use client';

import { usePathname } from 'next/navigation';
import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';

const PUBLIC_ROUTES = ['/', '/login', '/auth/login', '/signin'];

function isPublicRoute(pathname: string) {
  return PUBLIC_ROUTES.some((route) => pathname === route || pathname.startsWith(`${route}/`));
}

export function DashboardCursor() {
  const pathname = usePathname();
  const dotRef = useRef<HTMLDivElement>(null);
  const ringRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const currentPath = pathname ?? '';
    if (!currentPath || isPublicRoute(currentPath) || typeof window === 'undefined') {
      return;
    }

    const finePointer = window.matchMedia('(pointer:fine)').matches;
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (!finePointer || reducedMotion || !dotRef.current || !ringRef.current) {
      return;
    }

    const body = document.body;
    body.classList.add('dashboard-cursor-enabled');

    const dotX = gsap.quickTo(dotRef.current, 'x', { duration: 0.12, ease: 'power3.out' });
    const dotY = gsap.quickTo(dotRef.current, 'y', { duration: 0.12, ease: 'power3.out' });
    const ringX = gsap.quickTo(ringRef.current, 'x', { duration: 0.28, ease: 'power3.out' });
    const ringY = gsap.quickTo(ringRef.current, 'y', { duration: 0.28, ease: 'power3.out' });

    const handlePointerMove = (event: PointerEvent) => {
      dotX(event.clientX);
      dotY(event.clientY);
      ringX(event.clientX);
      ringY(event.clientY);

      const target = event.target instanceof HTMLElement ? event.target : null;
      const isTextField = Boolean(target?.closest('input, textarea, select, [contenteditable="true"]'));
      const isInteractive = Boolean(
        target?.closest('button, a, [role="button"], [data-cursor-hover="true"], summary')
      );

      body.classList.toggle('dashboard-cursor-text', isTextField);
      body.classList.toggle('dashboard-cursor-active', !isTextField && isInteractive);
    };

    const resetState = () => {
      body.classList.remove('dashboard-cursor-active', 'dashboard-cursor-text');
    };

    window.addEventListener('pointermove', handlePointerMove);
    window.addEventListener('blur', resetState);
    document.addEventListener('pointerleave', resetState);

    return () => {
      body.classList.remove('dashboard-cursor-enabled', 'dashboard-cursor-active', 'dashboard-cursor-text');
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('blur', resetState);
      document.removeEventListener('pointerleave', resetState);
    };
  }, [pathname]);

  return (
    <>
      <div ref={ringRef} className="dashboard-cursor-ring" aria-hidden="true" />
      <div ref={dotRef} className="dashboard-cursor-dot" aria-hidden="true" />
    </>
  );
}
