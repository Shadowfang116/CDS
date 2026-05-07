'use client';

import { usePathname } from 'next/navigation';
import { useEffect } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

export function DashboardMotion() {
  const pathname = usePathname();

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reducedMotion) {
      return;
    }

    gsap.registerPlugin(ScrollTrigger);

    const ctx = gsap.context(() => {
      gsap.fromTo(
        '[data-dashboard-reveal]',
        { autoAlpha: 0, y: 24 },
        {
          autoAlpha: 1,
          y: 0,
          duration: 0.8,
          ease: 'power3.out',
          stagger: 0.08,
        }
      );

      gsap.utils.toArray<HTMLElement>('[data-dashboard-section]').forEach((section) => {
        gsap.fromTo(
          section,
          { autoAlpha: 0, y: 34 },
          {
            autoAlpha: 1,
            y: 0,
            duration: 0.9,
            ease: 'power3.out',
            scrollTrigger: {
              trigger: section,
              start: 'top 88%',
            },
          }
        );
      });

      gsap.to('[data-dashboard-drift="slow"]', {
        xPercent: 6,
        yPercent: -4,
        duration: 18,
        ease: 'sine.inOut',
        repeat: -1,
        yoyo: true,
      });

      gsap.to('[data-dashboard-drift="fast"]', {
        xPercent: -4,
        yPercent: 6,
        duration: 14,
        ease: 'sine.inOut',
        repeat: -1,
        yoyo: true,
      });
    });

    return () => {
      ctx.revert();
    };
  }, [pathname]);

  return null;
}
