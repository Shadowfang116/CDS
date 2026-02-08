"use client"

import { usePathname } from "next/navigation"
import { AppShell } from "./app-shell"

interface ConditionalAppShellProps {
  children: React.ReactNode
}

export function ConditionalAppShell({ children }: ConditionalAppShellProps) {
  const pathname = usePathname()
  
  // Exclude AppShell from auth routes (if they exist)
  const authRoutes = ["/login", "/auth/login", "/signin"]
  const isAuthRoute = pathname && authRoutes.some(route => pathname === route || pathname.startsWith(route + "/"))
  
  if (isAuthRoute) {
    return <>{children}</>
  }
  
  // Show AppShell on all other pages
  // Title is now handled by PageChrome context, but keep for backward compatibility
  let title = "Dashboard"
  if (pathname?.startsWith("/cases")) {
    title = "Cases"
  } else if (pathname === "/dashboard") {
    title = "Dashboard"
  } else if (pathname === "/reports") {
    title = "Reports"
  } else if (pathname === "/analytics") {
    title = "Analytics"
  } else if (pathname === "/approvals") {
    title = "Approvals"
  } else if (pathname === "/integrations") {
    title = "Integrations"
  } else if (pathname === "/admin") {
    title = "Admin"
  }
  
  return (
    <AppShell title={title}>
      {children}
    </AppShell>
  )
}

