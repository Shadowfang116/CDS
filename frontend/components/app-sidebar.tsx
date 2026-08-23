"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  AlertTriangle,
  CheckSquare,
  ChevronLeft,
  FolderOpen,
  HelpCircle,
  Inbox,
  LogOut,
  Search,
  Settings,
  Shield,
} from "lucide-react";

import { Sidebar, useSidebar } from "@/components/ui/sidebar";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { BRAND } from "@/lib/brand";
import { logout } from "@/lib/api";
import { openHelp } from "@/lib/help";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { cn } from "@/lib/utils";

const EASE = "cubic-bezier(0.25, 1.1, 0.4, 1)";

type SectionId = "inbox" | "matters" | "findings" | "approvals" | "audit" | "settings";

type NavLink = {
  label: string;
  href?: string;
  onClick?: () => void;
};

type NavSection = {
  title: string;
  items: NavLink[];
};

type RailItem = {
  id: SectionId;
  title: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  match: (pathname: string) => boolean;
};

function sectionFromPath(pathname: string): SectionId {
  if (pathname.startsWith("/dashboard/settings")) return "settings";
  if (pathname.startsWith("/dashboard/audit") || pathname.startsWith("/governance") || pathname.startsWith("/integrations")) {
    return "audit";
  }
  if (pathname.startsWith("/approvals")) return "approvals";
  if (pathname.startsWith("/dashboard/exceptions") || pathname.startsWith("/dashboard/cp") || pathname.startsWith("/dashboard/evaluations")) {
    return "findings";
  }
  if (pathname.startsWith("/dashboard/cases") || pathname.startsWith("/matters") || pathname.startsWith("/dashboard/documents")) {
    return "matters";
  }
  return "inbox";
}

function IconButton({
  active,
  label,
  children,
  onClick,
  href,
}: {
  active?: boolean;
  label: string;
  children: React.ReactNode;
  onClick?: () => void;
  href?: string;
}) {
  const className = cn(
    "flex size-10 items-center justify-center rounded-lg text-muted-foreground transition-colors duration-300 hover:bg-[hsl(var(--pill))] hover:text-foreground",
    active && "bg-[hsl(var(--pill))] text-foreground"
  );

  const body = href ? (
    <Link
      href={href}
      aria-label={label}
      aria-current={active ? "page" : undefined}
      className={className}
      onClick={onClick}
    >
      {children}
    </Link>
  ) : (
    <button type="button" aria-label={label} className={className} onClick={onClick}>
      {children}
    </button>
  );

  return (
    <Tooltip>
      <TooltipTrigger asChild>{body}</TooltipTrigger>
      <TooltipContent side="right">{label}</TooltipContent>
    </Tooltip>
  );
}

function DetailLink({
  item,
  active,
  collapsed,
}: {
  item: NavLink;
  active: boolean;
  collapsed: boolean;
}) {
  const className = cn(
    "flex h-10 w-full items-center rounded-lg px-3 text-[13px] text-foreground/90 transition-colors hover:bg-[hsl(var(--pill))]",
    active && "bg-[hsl(var(--pill))] text-foreground"
  );

  if (item.onClick) {
    return (
      <button type="button" className={className} onClick={item.onClick} title={collapsed ? item.label : undefined}>
        {collapsed ? null : item.label}
      </button>
    );
  }

  return (
    <Link href={item.href ?? "#"} className={className} aria-current={active ? "page" : undefined} title={collapsed ? item.label : undefined}>
      {collapsed ? null : item.label}
    </Link>
  );
}

export function AppSidebar() {
  const pathname = usePathname() ?? "/dashboard";
  const router = useRouter();
  const user = useCurrentUser();
  const { setOpen, state } = useSidebar();
  const collapsed = state === "collapsed";
  const role = user?.role ?? "Viewer";
  const inMatter = Boolean(pathname && /\/dashboard\/cases\/[^/]+/.test(pathname));
  const [query, setQuery] = React.useState("");
  const activeSection = sectionFromPath(pathname);

  React.useEffect(() => {
    setOpen(!inMatter);
  }, [pathname, setOpen, inMatter]);

  React.useEffect(() => {
    setQuery("");
  }, [activeSection]);

  const railItems = React.useMemo<RailItem[]>(() => {
    const items: RailItem[] = [
      { id: "inbox", title: "Inbox", href: "/dashboard", icon: Inbox, match: (path) => sectionFromPath(path) === "inbox" },
      {
        id: "matters",
        title: "Matters",
        href: "/dashboard/cases",
        icon: FolderOpen,
        match: (path) => sectionFromPath(path) === "matters",
      },
      {
        id: "findings",
        title: "Findings",
        href: "/dashboard/exceptions",
        icon: AlertTriangle,
        match: (path) => sectionFromPath(path) === "findings",
      },
    ];
    if (role === "Approver" || role === "Admin") {
      items.push({
        id: "approvals",
        title: "Approvals",
        href: "/approvals",
        icon: CheckSquare,
        match: (path) => sectionFromPath(path) === "approvals",
      });
    }
    if (role === "Admin") {
      items.push({
        id: "audit",
        title: "Audit",
        href: "/dashboard/audit",
        icon: Shield,
        match: (path) => sectionFromPath(path) === "audit",
      });
    }
    return items;
  }, [role]);

  const detail = React.useMemo<{ title: string; sections: NavSection[] }>(() => {
    const canApprove = role === "Approver" || role === "Admin";
    const isAdmin = role === "Admin";

    const map: Record<SectionId, { title: string; sections: NavSection[] }> = {
      inbox: {
        title: "Inbox",
        sections: [
          {
            title: "Workspace",
            items: [
              { label: "Inbox", href: "/dashboard" },
              { label: "All matters", href: "/dashboard/cases" },
            ],
          },
          {
            title: "Review",
            items: [
              { label: "Findings", href: "/dashboard/exceptions" },
              ...(canApprove ? [{ label: "Approvals", href: "/approvals" }] : []),
            ],
          },
        ],
      },
      matters: {
        title: "Matters",
        sections: [
          {
            title: "Matters",
            items: [
              { label: "All matters", href: "/dashboard/cases" },
              { label: "Inbox", href: "/dashboard" },
              { label: "Documents", href: "/dashboard/documents" },
            ],
          },
          {
            title: "Work",
            items: [
              { label: "Findings", href: "/dashboard/exceptions" },
              { label: "Conditions precedent", href: "/dashboard/cp" },
            ],
          },
        ],
      },
      findings: {
        title: "Findings",
        sections: [
          {
            title: "Findings",
            items: [
              { label: "Exceptions", href: "/dashboard/exceptions" },
              { label: "Conditions precedent", href: "/dashboard/cp" },
              { label: "Evaluations", href: "/dashboard/evaluations" },
            ],
          },
        ],
      },
      approvals: {
        title: "Approvals",
        sections: [
          {
            title: "Queue",
            items: [
              { label: "Approvals", href: "/approvals" },
              { label: "Findings", href: "/dashboard/exceptions" },
              { label: "Inbox", href: "/dashboard" },
            ],
          },
        ],
      },
      audit: {
        title: "Audit",
        sections: [
          {
            title: "Governance",
            items: [
              { label: "Audit log", href: "/dashboard/audit" },
              { label: "Governance", href: "/governance" },
              { label: "Integrations", href: "/integrations" },
            ],
          },
        ],
      },
      settings: {
        title: "Settings",
        sections: [
          {
            title: "Account",
            items: [
              { label: "Profile / Settings", href: "/dashboard/settings" },
              { label: "Help", onClick: () => openHelp() },
              {
                label: "Sign out",
                onClick: () => {
                  void logout().then(() => {
                    router.replace("/");
                    router.refresh();
                  });
                },
              },
            ],
          },
        ],
      },
    };

    if (!isAdmin && activeSection === "audit") return map.inbox;
    return map[activeSection];
  }, [activeSection, role, router]);

  const filteredSections = React.useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return detail.sections;
    return detail.sections
      .map((section) => ({
        ...section,
        items: section.items.filter((item) => item.label.toLowerCase().includes(needle)),
      }))
      .filter((section) => section.items.length > 0);
  }, [detail.sections, query]);

  const initials = (user?.email ?? "U").slice(0, 2).toUpperCase();
  const expandIfCollapsed = React.useCallback(() => {
    if (collapsed && !inMatter) setOpen(true);
  }, [collapsed, inMatter, setOpen]);

  return (
    <Sidebar collapsible="icon" className="!flex-row items-stretch border-r border-border bg-[hsl(var(--rail))]">
      <aside
        className={cn(
          "flex h-full w-16 shrink-0 flex-col items-center px-2 py-4",
          collapsed ? "border-r-0" : "border-r border-border"
        )}
      >
        <Link
          href="/dashboard"
          aria-label={BRAND.full}
          className="mb-3 flex size-10 items-center justify-center rounded-lg border border-border bg-[hsl(var(--pill))] text-[10px] font-semibold tracking-[0.18em] text-foreground"
          onClick={(event) => {
            if (collapsed && !inMatter) {
              event.preventDefault();
              setOpen(true);
            }
          }}
        >
          {BRAND.short}
        </Link>

        <nav className="flex w-full flex-col items-center gap-1.5">
          {railItems.map((item) => {
            const Icon = item.icon;
            const active = item.match(pathname);
            return (
              <IconButton key={item.id} href={item.href} label={item.title} active={active} onClick={expandIfCollapsed}>
                <Icon className="size-4" />
              </IconButton>
            );
          })}
        </nav>

        <div className="flex-1" />

        <div className="flex flex-col items-center gap-1.5">
          <IconButton
            href="/dashboard/settings"
            label="Settings"
            active={activeSection === "settings"}
            onClick={expandIfCollapsed}
          >
            <Settings className="size-4" />
          </IconButton>
          <IconButton label="Help" onClick={() => openHelp()}>
            <HelpCircle className="size-4" />
          </IconButton>
          <div
            className="mt-1 flex size-8 items-center justify-center rounded-full border border-border bg-[hsl(var(--pill))] text-[10px] font-semibold text-foreground"
            title={user?.email ?? "Account"}
          >
            {initials}
          </div>
        </div>
      </aside>

      <aside
        className={cn(
          "flex h-full min-w-0 flex-col bg-[hsl(var(--rail))] py-4 transition-[width,opacity,padding] duration-500",
          collapsed ? "pointer-events-none w-0 overflow-hidden p-0 opacity-0" : "w-80 px-4 opacity-100"
        )}
        style={{ transitionTimingFunction: EASE }}
        aria-hidden={collapsed}
        inert={collapsed ? true : undefined}
      >
        <div className="mb-3 flex items-center justify-between">
          <div>
            <p className="px-2 text-[11px] font-medium tracking-[0.16em] text-muted-foreground">{BRAND.short}</p>
            <h2 className="px-2 text-[18px] font-semibold leading-7 text-foreground">{detail.title}</h2>
          </div>
          {inMatter ? null : (
            <button
              type="button"
              aria-label="Collapse sidebar"
              className="flex size-10 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-[hsl(var(--pill))] hover:text-foreground"
              onClick={() => setOpen(false)}
            >
              <ChevronLeft className="size-4" />
            </button>
          )}
        </div>

        <label className="relative mb-4 flex h-10 items-center rounded-lg border border-border bg-black/40 px-2">
          <Search className="size-4 shrink-0 text-muted-foreground" />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search…"
            className="h-10 w-full bg-transparent px-2 text-[13px] text-foreground outline-none placeholder:text-muted-foreground"
            tabIndex={collapsed ? -1 : 0}
          />
        </label>

        <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto">
          {filteredSections.map((section) => (
            <div key={section.title} className="flex flex-col gap-1">
              <p className="px-3 text-[12px] text-muted-foreground">{section.title}</p>
              {section.items.map((item) => (
                <DetailLink
                  key={item.label}
                  item={item}
                  collapsed={collapsed}
                  active={Boolean(item.href && (pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href))))}
                />
              ))}
            </div>
          ))}
        </div>

        <div className="mt-auto flex items-center gap-2 border-t border-border pt-3">
          <div className="flex size-8 items-center justify-center rounded-full border border-border bg-[hsl(var(--pill))] text-[10px] font-semibold">
            {initials}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-[13px] text-foreground">{user?.email ?? "Signed in"}</p>
            <p className="truncate text-[11px] text-muted-foreground">{role}</p>
          </div>
          <button
            type="button"
            aria-label="Sign out"
            className="flex size-8 items-center justify-center rounded-md text-muted-foreground hover:bg-[hsl(var(--pill))] hover:text-foreground"
            onClick={() => {
              void logout().then(() => {
                router.replace("/");
                router.refresh();
              });
            }}
          >
            <LogOut className="size-4" />
          </button>
        </div>
      </aside>
    </Sidebar>
  );
}
