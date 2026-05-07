"use client";

import { usePathname } from "next/navigation";
import { AppShell } from "@/components/layout/app-shell";

interface ConditionalAppShellProps {
  children: React.ReactNode;
}

export function ConditionalAppShell({ children }: ConditionalAppShellProps) {
  const pathname = usePathname();

  // Public/auth routes: no AppShell
  const publicRoutes = ["/", "/login", "/auth/login", "/signin", "/change-password"];
  const isPublicRoute =
    pathname &&
    publicRoutes.some(
      (route) => pathname === route || pathname.startsWith(route + "/")
    );

  if (isPublicRoute) {
    return <>{children}</>;
  }

  // Dashboard and all other app routes: canonical AppShell (sidebar + header)
  return <AppShell>{children}</AppShell>;
}

