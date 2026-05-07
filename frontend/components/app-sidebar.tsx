"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  AlertTriangle,
  BarChart2,
  Files,
  FolderOpen,
  History,
  LayoutDashboard,
  Scale,
  ShieldCheck,
} from "lucide-react";

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { BRAND } from "@/lib/brand";

type NavItem = {
  title: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  dataTour?: string;
};

const NAV_PRIMARY: NavItem[] = [
  { title: "Overview", href: "/dashboard", icon: LayoutDashboard },
  { title: "Cases", href: "/dashboard/cases", icon: FolderOpen, dataTour: "case-list" },
];

const NAV_REVIEW: NavItem[] = [
  { title: "Exceptions", href: "/dashboard/exceptions", icon: AlertTriangle, dataTour: "exceptions" },
  { title: "Conditions Precedent (CP)", href: "/dashboard/cp", icon: Scale },
  { title: "Documents", href: "/dashboard/documents", icon: Files, dataTour: "ocr-review" },
  { title: "Audit Log", href: "/dashboard/audit", icon: History },
];

const NAV_OPS: NavItem[] = [
  { title: "CDS", href: "/dashboard/cds", icon: Activity },
  { title: "Evaluation", href: "/dashboard/evaluations", icon: BarChart2 },
];

function NavSection({ items, pathname }: { items: NavItem[]; pathname: string | null }) {
  return (
    <SidebarMenu>
      {items.map((item) => {
        const active =
          pathname === item.href || (item.href !== "/dashboard" && pathname?.startsWith(item.href + "/"));
        const Icon = item.icon;

        return (
          <SidebarMenuItem key={item.href}>
            <SidebarMenuButton asChild isActive={active} tooltip={item.title}>
              <Link href={item.href} aria-current={active ? "page" : undefined} data-tour={item.dataTour}>
                <Icon className="h-4 w-4" />
                <span>{item.title}</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        );
      })}
    </SidebarMenu>
  );
}

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="px-3 py-3 group-data-[collapsible=icon]:h-auto group-data-[collapsible=icon]:px-2 group-data-[collapsible=icon]:py-3">
        <div className="flex w-full items-center justify-between group-data-[collapsible=icon]:flex-col group-data-[collapsible=icon]:items-center group-data-[collapsible=icon]:justify-start group-data-[collapsible=icon]:gap-2">
          <SidebarTrigger className="order-last h-8 w-8 shrink-0 rounded-md border border-zinc-700/80 bg-zinc-900/90 text-zinc-200 shadow-[0_6px_16px_rgba(0,0,0,0.28)] transition-colors hover:bg-zinc-800 hover:text-zinc-100 group-data-[collapsible=icon]:order-first group-data-[collapsible=icon]:mx-auto" />
          <div className="flex min-w-0 items-center gap-3 group-data-[collapsible=icon]:order-last group-data-[collapsible=icon]:gap-0">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-[rgba(127,138,149,0.28)] bg-[linear-gradient(180deg,rgba(39,46,51,0.98),rgba(28,34,38,0.98))] text-[13px] font-semibold text-stone-100 shadow-[0_10px_24px_rgba(0,0,0,0.18)] transition-[border-radius,width,height] duration-200 ease-out group-data-[collapsible=icon]:h-9 group-data-[collapsible=icon]:w-9 group-data-[collapsible=icon]:rounded-lg">
              {BRAND.short}
            </div>
            <div className="min-w-0 overflow-hidden transition-[width,opacity,transform] duration-200 ease-out group-data-[collapsible=icon]:pointer-events-none group-data-[collapsible=icon]:w-0 group-data-[collapsible=icon]:-translate-x-2 group-data-[collapsible=icon]:opacity-0">
              <div className="font-display text-[15px] font-medium leading-tight tracking-[-0.03em] text-stone-100">
                {BRAND.full}
              </div>
              <div className="mt-1 text-xs text-zinc-400">{BRAND.subtitle}</div>
            </div>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Workspace</SidebarGroupLabel>
          <SidebarGroupContent>
            <NavSection items={NAV_PRIMARY} pathname={pathname} />
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>Review</SidebarGroupLabel>
          <SidebarGroupContent>
            <NavSection items={NAV_REVIEW} pathname={pathname} />
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>Operations</SidebarGroupLabel>
          <SidebarGroupContent>
            <NavSection items={NAV_OPS} pathname={pathname} />
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="px-4 py-3 group-data-[collapsible=icon]:px-0 group-data-[collapsible=icon]:py-3">
        <div className="flex items-center gap-2 text-xs text-stone-500 group-data-[collapsible=icon]:justify-center">
          <ShieldCheck className="h-4 w-4 shrink-0 text-stone-500" />
          <span className="group-data-[collapsible=icon]:hidden">Org-scoped access</span>
        </div>
      </SidebarFooter>

      <SidebarRail />
    </Sidebar>
  );
}
