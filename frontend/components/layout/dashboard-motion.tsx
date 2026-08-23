'use client';

import { usePathname } from 'next/navigation';
import { gsap, useGSAP } from '@/lib/gsap';

export function DashboardMotion() {
  const pathname = usePathname();

  useGSAP(
    () => {
      if (typeof window === 'undefined') {
        return;
      }

      const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      if (reducedMotion) {
        return;
      }

      const reveals = gsap.utils.toArray<HTMLElement>('[data-dashboard-reveal]');
      if (reveals.length === 0) {
        return;
      }

      gsap.fromTo(
        reveals,
        { autoAlpha: 0, y: 12 },
        {
          autoAlpha: 1,
          y: 0,
          duration: 0.45,
          ease: 'power3.out',
          stagger: 0.06,
        }
      );
    },
    { dependencies: [pathname], revertOnUpdate: true }
  );

  return null;
}
