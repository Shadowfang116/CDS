import * as React from "react";
import { cn } from "@/lib/utils";
import { Separator } from "@/components/ui/separator";

export function PageHeader(props: {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  className?: string;
}) {
  const { title, subtitle, actions, className } = props;

  return (
    <div className={cn("px-4 pt-4", className)}>
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="leading-tight">
          <div className="text-[11px] font-semibold uppercase tracking-[0.1em] text-muted-foreground">Workspace</div>
          <div className="mt-1 text-2xl font-semibold tracking-tight">{title}</div>
          {subtitle ? (
            <div className="mt-2 max-w-3xl text-sm text-muted-foreground">{subtitle}</div>
          ) : null}
        </div>
        {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
      </div>
      <Separator className="mt-5" />
    </div>
  );
}
