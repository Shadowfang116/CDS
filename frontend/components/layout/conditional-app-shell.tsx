"use client";

import { usePathname } from "next/navigation";
import { AppShell } from "@/components/app/AppShell";

interface ConditionalAppShellProps {
  children: React.ReactNode;
}

export function ConditionalAppShell({ children }: ConditionalAppShellProps) {
  const pathname = usePathname();

  // Public/auth routes: no AppShell
  const authRoutes = ["/login", "/auth/login", "/signin"];
  const isAuthRoute =
    pathname &&
    authRoutes.some(
      (route) => pathname === route || pathname.startsWith(route + "/")
    );

  if (isAuthRoute) {
    return <>{children}</>;
  }

  // Dashboard and all other app routes: canonical AppShell (sidebar + header)
  return <AppShell>{children}</AppShell>;
}

