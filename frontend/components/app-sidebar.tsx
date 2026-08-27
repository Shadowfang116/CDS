"use client";

import Link from "next/link";
import type { CSSProperties } from "react";
import { usePathname, useRouter } from "next/navigation";
import { AlertTriangle, CheckSquare, FileText, FolderOpen, HelpCircle, Inbox, LogOut, Settings, Shield } from "lucide-react";

import { Sidebar, SidebarContent, SidebarFooter, SidebarHeader, SidebarMenu, SidebarMenuButton, SidebarMenuItem, useSidebar } from "@/components/ui/sidebar";
import { BRAND } from "@/lib/brand";
import { isDashboardNavActive } from "@/lib/cds-review-ui";
import { logout } from "@/lib/api";
import { openHelp } from "@/lib/help";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { cn } from "@/lib/utils";

type NavigationItem = {
  label: string;
  href: string;
  icon: typeof Inbox;
  roles?: string[];
};

const PRIMARY_NAVIGATION: NavigationItem[] = [
  { label: "Inbox", href: "/dashboard", icon: Inbox },
  { label: "Matters", href: "/dashboard/cases", icon: FolderOpen },
  { label: "Documents", href: "/dashboard/documents", icon: FileText },
  { label: "Issues", href: "/dashboard/exceptions", icon: AlertTriangle },
  { label: "Approval requirements", href: "/dashboard/cp", icon: CheckSquare },
  { label: "Approvals", href: "/approvals", icon: CheckSquare, roles: ["Approver", "Admin"] },
  { label: "Audit", href: "/dashboard/audit", icon: Shield, roles: ["Admin"] },
];

function visibleForRole(item: NavigationItem, role: string): boolean {
  return !item.roles || item.roles.includes(role);
}

export function AppSidebar() {
  const pathname = usePathname() ?? "/dashboard";
  const router = useRouter();
  const user = useCurrentUser();
  const { setOpenMobile } = useSidebar();
  const role = user?.role ?? "Viewer";
  const initials = (user?.email ?? "U").slice(0, 2).toUpperCase();

  const closeMobile = () => setOpenMobile(false);
  const signOut = () => {
    void logout().then(() => {
      router.replace("/");
      router.refresh();
    });
  };

  return (
    <Sidebar
      collapsible="offcanvas"
      className="border-r border-sidebar-border bg-sidebar text-sidebar-foreground"
      style={{ "--sidebar-width": "16rem" } as CSSProperties}
    >
      <SidebarHeader className="border-b border-sidebar-border px-5 py-5">
        <Link href="/dashboard" onClick={closeMobile} className="flex items-center gap-3" aria-label={BRAND.full}>
          <span className="flex size-9 items-center justify-center rounded-md border border-sidebar-border bg-sidebar-accent text-[10px] font-semibold tracking-[0.16em] text-sidebar-foreground">
            {BRAND.short}
          </span>
          <span className="min-w-0">
            <span className="block text-sm font-semibold text-sidebar-foreground">CDS</span>
            <span className="block text-xs text-sidebar-foreground/70">Review workspace</span>
          </span>
        </Link>
      </SidebarHeader>

      <SidebarContent className="px-3 py-4">
        <p className="px-3 pb-2 text-xs font-medium text-sidebar-foreground/70">Workspace</p>
        <SidebarMenu>
          {PRIMARY_NAVIGATION.filter((item) => visibleForRole(item, role)).map((item) => {
            const Icon = item.icon;
            const active = isDashboardNavActive(pathname, item.href);
            return (
              <SidebarMenuItem key={item.href}>
                <SidebarMenuButton asChild isActive={active} tooltip={item.label} className={cn("h-10 rounded-sm border-l-2 border-transparent px-3 text-sm text-sidebar-foreground/85", active && "border-sidebar-primary bg-sidebar-accent text-sidebar-accent-foreground")}>
                  <Link href={item.href} onClick={closeMobile} aria-current={active ? "page" : undefined}>
                    <Icon className="size-4" />
                    <span>{item.label}</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            );
          })}
        </SidebarMenu>

        <p className="px-3 pb-2 pt-7 text-xs font-medium text-sidebar-foreground/70">Account</p>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton asChild isActive={isDashboardNavActive(pathname, "/dashboard/settings")} tooltip="Settings" className={cn("h-10 rounded-sm border-l-2 border-transparent px-3 text-sm text-sidebar-foreground/85", isDashboardNavActive(pathname, "/dashboard/settings") && "border-sidebar-primary bg-sidebar-accent text-sidebar-accent-foreground")}>
              <Link href="/dashboard/settings" onClick={closeMobile}>
                <Settings className="size-4" />
                <span>Settings</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
          <SidebarMenuItem>
            <SidebarMenuButton type="button" tooltip="Help" className="h-10 rounded-sm border-l-2 border-transparent px-3 text-sm text-sidebar-foreground/85" onClick={() => { closeMobile(); openHelp(); }}>
              <HelpCircle className="size-4" />
              <span>Help</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarContent>

      <SidebarFooter className="border-t border-sidebar-border px-4 py-4">
        <div className="flex items-center gap-3">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-full border border-sidebar-border bg-sidebar-accent text-[10px] font-semibold text-sidebar-foreground">
            {initials}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-medium text-sidebar-foreground">{user?.email ?? "Signed in"}</p>
            <p className="truncate text-[11px] text-sidebar-foreground/70">{role}</p>
          </div>
          <button type="button" className="cds-hit-target flex size-8 items-center justify-center rounded-sm text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground" onClick={signOut} aria-label="Sign out">
            <LogOut className="size-4" />
          </button>
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
