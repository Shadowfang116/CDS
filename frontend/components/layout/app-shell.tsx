"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { LogOut, Settings } from "lucide-react"

import { getMe, logout } from "@/lib/api"
import { AppSidebar } from "@/components/app-sidebar"
import { NotificationBell } from "@/components/app/NotificationBell"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"

import { ThemeToggle } from "./theme-toggle"
import { PageChromeProvider, usePageChrome } from "./page-chrome"
import { HelpDialog } from "@/components/help/help-dialog"
import { openHelp } from "@/lib/help"
import { OnboardingChecklist } from "@/components/OnboardingChecklist"
import { OnboardingTour } from "@/components/OnboardingTour"

interface AppShellProps {
  children: React.ReactNode
}

interface WorkspaceUser {
  displayName: string
  email: string
  role: string
  orgName: string
}

const HEADER_ICON_BUTTON_CLASSNAME = "cds-icon-btn"

const SETTINGS_ROUTE = "/dashboard/settings"
const SETTINGS_ROUTE_AVAILABLE = true

function truncateLabel(label: string, maxLength: number) {
  if (label.length <= maxLength) {
    return label
  }

  return `${label.slice(0, Math.max(0, maxLength - 3)).trimEnd()}...`
}

function getInitials(value: string) {
  const segments = value
    .replace(/[_-]+/g, " ")
    .split(" ")
    .map((segment) => segment.trim())
    .filter(Boolean)

  if (segments.length === 0) {
    return "U"
  }

  if (segments.length === 1) {
    return segments[0].slice(0, 2).toUpperCase()
  }

  return `${segments[0][0] ?? ""}${segments[1][0] ?? ""}`.toUpperCase()
}

function toWorkspaceUser(rawUser: Record<string, unknown> | null | undefined): WorkspaceUser | null {
  if (!rawUser) {
    return null
  }

  const email =
    typeof rawUser.email === "string" && rawUser.email.trim().length > 0
      ? rawUser.email.trim()
      : null
  const role =
    typeof rawUser.role === "string" && rawUser.role.trim().length > 0
      ? rawUser.role.trim()
      : null
  const orgName =
    typeof rawUser.org_name === "string" && rawUser.org_name.trim().length > 0
      ? rawUser.org_name.trim()
      : typeof rawUser.orgName === "string" && rawUser.orgName.trim().length > 0
        ? rawUser.orgName.trim()
        : "Organization"
  if (!email || !role) {
    return null
  }
  const displayNameSource =
    typeof rawUser.display_name === "string" && rawUser.display_name.trim().length > 0
      ? rawUser.display_name.trim()
      : typeof rawUser.full_name === "string" && rawUser.full_name.trim().length > 0
        ? rawUser.full_name.trim()
        : typeof rawUser.name === "string" && rawUser.name.trim().length > 0
          ? rawUser.name.trim()
          : email.split("@")[0] || role

  return {
    displayName: displayNameSource,
    email,
    role,
    orgName,
  }
}

async function getWorkspaceUser(): Promise<WorkspaceUser | null> {
  try {
    const me = (await getMe()) as Record<string, unknown>
    return toWorkspaceUser(me)
  } catch {
    return null
  }
}

function WorkspaceUserMenu() {
  const router = useRouter()
  const [user, setUser] = React.useState<WorkspaceUser | null>(null)
  const [loading, setLoading] = React.useState(true)

  React.useEffect(() => {
    let isMounted = true

    void (async () => {
      const nextUser = await getWorkspaceUser()
      if (isMounted) {
        if (!nextUser) {
          router.replace("/login")
          router.refresh()
          return
        }
        setUser(nextUser)
        setLoading(false)
      }
    })()

    return () => {
      isMounted = false
    }
  }, [router])

  const handleSettingsSelect = React.useCallback(() => {
    if (SETTINGS_ROUTE_AVAILABLE) {
      router.push(SETTINGS_ROUTE)
      return
    }

    console.info("Settings page not available yet. Route reserved for", SETTINGS_ROUTE)
  }, [router])

  const handleSignOut = React.useCallback(async () => {
    await logout()
    router.replace("/")
    router.refresh()
  }, [router])

  if (loading || !user) {
    return (
      <button
        type="button"
        disabled
        className="flex h-[41px] items-center gap-2 rounded border border-border bg-[hsl(var(--pill))] px-[11px] py-2 text-[11px] text-muted-foreground"
        aria-label="Loading account"
      >
        <span className="cds-pill">—</span>
        <span>Loading</span>
      </button>
    )
  }

  const displayName = truncateLabel(user.displayName, 16)
  const initials = getInitials(user.displayName)

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className="flex h-[41px] items-center gap-2 rounded border border-border bg-[hsl(var(--pill))] px-[11px] py-2 text-[11px] font-semibold text-foreground transition-colors hover:bg-muted"
          aria-label="Open account menu"
        >
          <span className="cds-pill">{initials}</span>
          <span className="max-w-28 truncate">{displayName}</span>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="end"
        className="w-72 rounded-lg border border-border bg-popover p-1 text-popover-foreground"
      >
        <DropdownMenuLabel className="px-3 py-3">
          <div className="flex items-start gap-3">
            <Avatar className="size-9 border-border bg-muted">
              <AvatarFallback className="bg-muted text-xs font-semibold text-foreground">
                {initials}
              </AvatarFallback>
            </Avatar>
            <div className="flex min-w-0 flex-col gap-1">
              <p className="truncate text-sm font-medium">{user.displayName}</p>
              <p className="truncate text-xs text-muted-foreground">{user.email}</p>
              <p className="text-xs text-muted-foreground">
                {user.role}
                {user.orgName ? ` • ${user.orgName}` : ""}
              </p>
            </div>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          className="gap-2 rounded-md px-3 py-2 text-[13px]"
          onSelect={handleSettingsSelect}
        >
          <Settings className="size-4" />
          Profile / Settings
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          className="gap-2 rounded-md px-3 py-2 text-[13px]"
          onSelect={() => {
            void handleSignOut()
          }}
        >
          <LogOut className="size-4" />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

function AppShellContent({ children }: { children: React.ReactNode }) {
  const { title, subtitle, breadcrumbs, actions } = usePageChrome()
  const pathname = usePathname()
  const isOverview = pathname === "/dashboard"
  const isMatter = Boolean(pathname && /\/dashboard\/cases\/[^/]+/.test(pathname))

  const displayTitle = title || "Inbox"
  const displaySubtitle = subtitle || "Active workspace"

  return (
    <SidebarInset className="dashboard-app-shell">
      <header className="sticky top-0 z-30 h-[58px] border-b border-border bg-[hsl(var(--header))]">
        <div className="flex h-[58px] items-center justify-between gap-4 px-5">
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <SidebarTrigger className="shrink-0" aria-label="Open navigation" />
            {isOverview ? (
              <p className="cds-meta">Inbox</p>
            ) : isMatter ? (
              <p className="cds-meta">Matter</p>
            ) : (
            <div className="min-w-0 flex-1">
              <div className="flex min-w-0 items-baseline gap-2">
                {breadcrumbs.length > 0 && breadcrumbs.at(-1)?.label !== displayTitle ? (
                  <nav
                    aria-label="Breadcrumb"
                    className="flex max-w-[40%] shrink-0 items-center gap-1.5 overflow-hidden text-xs text-muted-foreground"
                  >
                    {breadcrumbs.map((crumb, index) => {
                      const isLast = index === breadcrumbs.length - 1
                      return (
                        <React.Fragment key={`${crumb.label}-${index}`}>
                          {crumb.href && !isLast ? (
                            <Link
                              href={crumb.href}
                              className="max-w-[10rem] truncate transition-colors hover:text-foreground"
                            >
                              {crumb.label}
                            </Link>
                          ) : (
                            <span className={isLast ? "truncate text-foreground/80" : "truncate"}>
                              {crumb.label}
                            </span>
                          )}
                          {!isLast ? <span className="text-muted-foreground/60">/</span> : null}
                        </React.Fragment>
                      )
                    })}
                  </nav>
                ) : null}
                <h1 className="min-w-0 truncate text-xl font-medium tracking-[-0.03em] text-foreground sm:text-2xl">{displayTitle}</h1>
              </div>
              <p className="truncate text-sm text-muted-foreground">{displaySubtitle}</p>
            </div>
            )}
          </div>

          <div className="flex shrink-0 items-center gap-2.5">
            {actions && !isOverview && !isMatter ? <div className="flex items-center gap-2">{actions}</div> : null}
            <ThemeToggle className={HEADER_ICON_BUTTON_CLASSNAME} />
            <NotificationBell />
            <button
              type="button"
              className={HEADER_ICON_BUTTON_CLASSNAME}
              aria-label="Open CDS help"
              onClick={() => openHelp()}
            >
              ?
            </button>
            <WorkspaceUserMenu />
          </div>
        </div>
      </header>

      <main className={isOverview ? "dashboard-main min-h-0 flex-1 overflow-y-auto" : isMatter ? "dashboard-main min-h-0 flex-1 overflow-hidden" : "dashboard-main min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:px-5 lg:px-6 lg:py-6"}>
        <div className={isOverview ? "mx-auto max-w-[1600px]" : isMatter ? "h-full w-full" : "mx-auto max-w-[1480px]"}>{children}</div>
      </main>
      <HelpDialog />
      <OnboardingTour />
      <OnboardingChecklist />
    </SidebarInset>
  )
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="dashboard-shell">
      <SidebarProvider>
        <AppSidebar />
        <PageChromeProvider>
          <AppShellContent>{children}</AppShellContent>
        </PageChromeProvider>
      </SidebarProvider>
    </div>
  )
}





