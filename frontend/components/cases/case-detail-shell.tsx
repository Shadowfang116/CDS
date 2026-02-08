import * as React from "react";
import { PageHeader } from "@/components/ui/page-header";
import { CaseStatusPill, CaseStatus } from "@/components/ui/case-status-pill";
import { SeverityBadge, Severity } from "@/components/ui/severity-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

export function CaseDetailShell(props: {
  caseId: string;
  status: CaseStatus;
  highestSeverity: Severity;
  openExceptions: number;
  openCps: number;
  children: React.ReactNode;
  rightPanel?: React.ReactNode;
}) {
  const {
    caseId,
    status,
    highestSeverity,
    openExceptions,
    openCps,
    children,
    rightPanel,
  } = props;

  return (
    <>
      <PageHeader
        title="Case Review"
        subtitle={`Case ID: ${caseId}`}
        actions={
          <div className="flex items-center gap-2">
            <CaseStatusPill status={status} />
            <SeverityBadge severity={highestSeverity} />
          </div>
        }
      />

      <div className="p-4">
        <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
          <div className="space-y-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Key Metrics</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div>
                    <div className="text-xs text-muted-foreground">Open Exceptions</div>
                    <div className="text-lg font-semibold">{openExceptions}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">Open CPs</div>
                    <div className="text-lg font-semibold">{openCps}</div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {children}
          </div>

          <div className="space-y-4">
            {rightPanel === undefined ? (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Evidence</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  Evidence panel placeholder. Next: document viewer + page references + "Add as Evidence".
                  <Separator className="my-3" />
                  <div className="text-xs">
                    Bank UX rule: every exception/CP must have clickable evidence refs.
                  </div>
                </CardContent>
              </Card>
            ) : (
              rightPanel
            )}
          </div>
        </div>
      </div>
    </>
  );
}
