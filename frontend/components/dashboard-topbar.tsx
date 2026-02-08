"use client";

import * as React from "react";
import { SidebarTrigger } from "@/components/ui/sidebar";

export function DashboardTopbar(props: { title: string; subtitle?: string }) {
  const { title, subtitle } = props;

  return (
    <div className="flex items-center justify-between border-b bg-background px-4 py-3">
      <div className="flex items-center gap-3">
        <SidebarTrigger />
        <div className="leading-tight">
          <div className="text-sm font-semibold">{title}</div>
          {subtitle ? (
            <div className="text-xs text-muted-foreground">{subtitle}</div>
          ) : null}
        </div>
      </div>

      {/* Placeholder for future: user menu, org switcher, notifications */}
      <div className="text-xs text-muted-foreground">Reviewer Console</div>
    </div>
  );
}
