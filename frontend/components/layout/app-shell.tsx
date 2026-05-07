"use client"

import * as React from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { ChevronDown, HelpCircle, LogOut, Settings } from "lucide-react"

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
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"

import { DashboardMotion } from "./dashboard-motion"
import { ThemeToggle } from "./theme-toggle"
import { PageChromeProvider, usePageChrome } from "./page-chrome"
import TutorialDialog from "./TutorialDialog"
import { OnboardingTour } from "@/components/OnboardingTour"
import { OnboardingChecklist } from "@/components/OnboardingChecklist"
import { PRODUCT_WALKTHROUGH_OPEN_EVENT, PRODUCT_WALKTHROUGH_STORAGE_KEY } from "@/config/product-walkthrough"

interface AppShellProps {
  children: React.ReactNode
}

interface WorkspaceUser {
  displayName: string
  email: string
  role: string
  orgName: string
}

const HEADER_ICON_BUTTON_CLASSNAME =
  "flex h-8 w-8 items-center justify-center rounded-md border border-zinc-800 bg-zinc-900/70 text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-zinc-200"

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
        className="flex h-9 items-center gap-2 rounded-md border border-zinc-800/90 bg-zinc-950/70 px-2.5 text-[13px] text-zinc-500"
        aria-label="Loading account"
      >
        <span className="h-7 w-7 rounded-full bg-zinc-900" />
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
          className="flex h-9 items-center gap-2 rounded-md border border-zinc-800/90 bg-zinc-950/70 px-2.5 text-[13px] text-zinc-200 shadow-[inset_0_1px_0_rgba(255,255,255,0.02)] transition-colors hover:bg-zinc-900 hover:text-zinc-50"
          aria-label="Open account menu"
        >
          <Avatar className="h-7 w-7 border-zinc-700/90 bg-zinc-900">
            <AvatarFallback className="bg-zinc-800 text-[10px] font-semibold tracking-[0.02em] text-zinc-200">
              {initials}
            </AvatarFallback>
          </Avatar>
          <span className="max-w-28 truncate font-medium text-zinc-200">{displayName}</span>
          <ChevronDown className="size-3.5 text-zinc-500" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="end"
        className="w-72 rounded-lg border border-zinc-800 bg-zinc-950 p-1 text-zinc-100 backdrop-blur-none shadow-[0_18px_40px_rgba(0,0,0,0.5)]"
      >
        <DropdownMenuLabel className="px-3 py-3">
          <div className="flex items-start gap-3">
            <Avatar className="h-9 w-9 border-zinc-700/90 bg-zinc-900">
              <AvatarFallback className="bg-zinc-800 text-xs font-semibold text-zinc-200">
                {initials}
              </AvatarFallback>
            </Avatar>
            <div className="min-w-0 space-y-1">
              <p className="truncate text-sm font-medium text-zinc-100">{user.displayName}</p>
              <p className="truncate text-xs text-zinc-400">{user.email}</p>
              <p className="text-xs text-zinc-500">
                {user.role}
                {user.orgName ? ` • ${user.orgName}` : ""}
              </p>
            </div>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator className="bg-zinc-800/90" />
        <DropdownMenuItem
          className="gap-2 rounded-md px-3 py-2 text-[13px] text-zinc-300 focus:bg-zinc-800/90 focus:text-zinc-100"
          onSelect={handleSettingsSelect}
        >
          <Settings className="size-4" />
          Profile / Settings
        </DropdownMenuItem>
        <DropdownMenuSeparator className="bg-zinc-800/90" />
        <DropdownMenuItem
          className="gap-2 rounded-md px-3 py-2 text-[13px] text-zinc-300 focus:bg-zinc-800/90 focus:text-zinc-100"
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
  const [tutorialOpen, setTutorialOpen] = React.useState(false)

  React.useEffect(() => {
    if (typeof window === "undefined") {
      return
    }

    const handleOpenTutorial = () => {
      setTutorialOpen(true)
    }

    if (localStorage.getItem(PRODUCT_WALKTHROUGH_STORAGE_KEY) !== "true") {
      setTutorialOpen(true)
    }

    window.addEventListener(PRODUCT_WALKTHROUGH_OPEN_EVENT, handleOpenTutorial)
    return () => {
      window.removeEventListener(PRODUCT_WALKTHROUGH_OPEN_EVENT, handleOpenTutorial)
    }
  }, [])

  const displayTitle = title || "Dashboard"
  const displaySubtitle = subtitle || "Active workspace"

  return (
    <SidebarInset className="dashboard-app-shell">
      <header className="sticky top-0 z-30 border-b border-zinc-800/80 bg-zinc-950/85 backdrop-blur-xl">
        <div className="flex min-h-[4.75rem] items-center justify-between gap-4 px-4 sm:px-5 lg:px-6">
          <div className="flex min-w-0 flex-1 items-start gap-3">
            <div className="min-w-0 flex-1">
              {breadcrumbs.length > 0 ? (
                <nav
                  aria-label="Breadcrumb"
                  className="mb-1 flex min-w-0 items-center gap-1.5 overflow-hidden text-xs text-zinc-400"
                >
                  {breadcrumbs.map((crumb, index) => {
                    const isLast = index === breadcrumbs.length - 1
                    return (
                      <React.Fragment key={`${crumb.label}-${index}`}>
                        {crumb.href && !isLast ? (
                          <Link
                            href={crumb.href}
                            className="max-w-[10rem] truncate transition-colors hover:text-zinc-200"
                          >
                            {crumb.label}
                          </Link>
                        ) : (
                          <span className={isLast ? "truncate text-zinc-300" : "truncate"}>
                            {crumb.label}
                          </span>
                        )}
                        {!isLast ? <span className="text-zinc-600">/</span> : null}
                      </React.Fragment>
                    )
                  })}
                </nav>
              ) : null}

              <div className="min-w-0">
                <h1 className="truncate text-sm font-semibold text-zinc-100">{displayTitle}</h1>
                <p className="truncate text-xs text-zinc-500">{displaySubtitle}</p>
              </div>
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
            <ThemeToggle />
            <NotificationBell />
            <button
              type="button"
              className={HEADER_ICON_BUTTON_CLASSNAME}
              aria-label="Open CDS tutorial"
              onClick={() => setTutorialOpen(true)}
            >
              <HelpCircle className="size-4" />
            </button>
            <WorkspaceUserMenu />
          </div>
        </div>
      </header>

      <main className="dashboard-main min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:px-5 lg:px-6 lg:py-6">
        <div className="mx-auto max-w-[1480px]">{children}</div>
      </main>

      <OnboardingTour />
      <React.Suspense><OnboardingChecklist /></React.Suspense>
      <TutorialDialog open={tutorialOpen} onOpenChange={setTutorialOpen} />
    </SidebarInset>
  )
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="dashboard-shell">
      <DashboardMotion />
      <div className="dashboard-backdrop" aria-hidden="true">
        <div className="dashboard-backdrop__grid" />
        <div className="dashboard-backdrop__orb dashboard-backdrop__orb--primary" data-dashboard-drift="slow" />
        <div className="dashboard-backdrop__orb dashboard-backdrop__orb--secondary" data-dashboard-drift="fast" />
        <div className="dashboard-backdrop__orb dashboard-backdrop__orb--ambient" data-dashboard-drift="slow" />
      </div>
      <SidebarProvider>
        <AppSidebar />
        <PageChromeProvider>
          <AppShellContent>{children}</AppShellContent>
        </PageChromeProvider>
      </SidebarProvider>
    </div>
  )
}





