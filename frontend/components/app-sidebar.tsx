"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

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
} from "@/components/ui/sidebar";

type NavItem = {
  title: string;
  href: string;
};

const NAV_PRIMARY: NavItem[] = [
  { title: "Cases", href: "/dashboard/cases" },
  { title: "Exceptions", href: "/dashboard/exceptions" },
  { title: "Conditions Precedent (CP)", href: "/dashboard/cp" },
  { title: "Documents", href: "/dashboard/documents" },
  { title: "Audit Log", href: "/dashboard/audit" },
];

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="px-3 py-2">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-md border" />
          <div className="leading-tight">
            <div className="text-sm font-semibold">Bank Diligence</div>
            <div className="text-xs text-muted-foreground">Case Workspace</div>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Workspace</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {NAV_PRIMARY.map((item) => {
                const active =
                  pathname === item.href || pathname?.startsWith(item.href + "/");
                return (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton asChild isActive={active}>
                      <Link href={item.href}>{item.title}</Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="px-3 py-2">
        <div className="text-xs text-muted-foreground">
          Org-scoped • RBAC enforced
        </div>
      </SidebarFooter>

      <SidebarRail />
    </Sidebar>
  );
}

