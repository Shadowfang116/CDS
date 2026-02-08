"use client"

import * as React from "react"
import Link from "next/link"
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar"
import { AppSidebar } from "@/components/app-sidebar"
import { NotificationBell } from "@/components/app/NotificationBell"
import { PageChromeProvider, usePageChrome } from "./page-chrome"
import { cn } from "@/lib/utils"

interface AppShellProps {
  children: React.ReactNode
  title?: string
  actions?: React.ReactNode
}

function AppShellContent({ children }: { children: React.ReactNode }) {
  const { title, breadcrumbs, actions } = usePageChrome()
  
  // Use context values if available, otherwise fall back to props (for backward compatibility)
  const displayTitle = title || "Dashboard"
  const displayActions = actions

  return (
    <SidebarInset>
      {/* Top bar */}
      <header className="sticky top-0 z-30 h-16 bg-slate-900/80 backdrop-blur-md border-b border-slate-700/50">
        <div className="flex items-center justify-between h-full px-4 lg:px-6">
          <div className="flex items-center gap-4 min-w-0 flex-1">
            <SidebarTrigger />
            
            {/* Breadcrumbs + Title */}
            <div className="flex items-center gap-2 min-w-0">
              {breadcrumbs.length > 0 && (
                <nav className="flex items-center gap-1.5 text-sm text-slate-400 flex-shrink-0">
                  {breadcrumbs.map((crumb, index) => {
                    const isLast = index === breadcrumbs.length - 1
                    return (
                      <React.Fragment key={index}>
                        {crumb.href && !isLast ? (
                          <Link
                            href={crumb.href}
                            className="hover:text-slate-300 transition-colors truncate max-w-[120px]"
                          >
                            {crumb.label}
                          </Link>
                        ) : (
                          <span className={isLast ? "text-slate-300" : ""}>
                            {crumb.label}
                          </span>
                        )}
                        {!isLast && (
                          <span className="text-slate-600 mx-1">/</span>
                        )}
                      </React.Fragment>
                    )
                  })}
                </nav>
              )}
              {breadcrumbs.length > 0 && displayTitle && (
                <span className="text-slate-500 mx-1 hidden sm:inline">·</span>
              )}
              {displayTitle && (
                <h2 className="text-lg font-semibold text-slate-100 truncate">
                  {displayTitle}
                </h2>
              )}
            </div>
          </div>
          
          <div className="flex items-center gap-3 flex-shrink-0">
            <NotificationBell />
            {displayActions}
          </div>
        </div>
      </header>

      {/* Content area */}
      <main className="p-4 lg:p-6">
        <div className="max-w-7xl mx-auto">
          {children}
        </div>
      </main>
    </SidebarInset>
  )
}

export function AppShell({ children, title, actions }: AppShellProps) {
  return (
    <SidebarProvider>
      <AppSidebar />
      <PageChromeProvider>
        <AppShellContent>
          {children}
        </AppShellContent>
      </PageChromeProvider>
    </SidebarProvider>
  )
}

