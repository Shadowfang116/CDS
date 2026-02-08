"use client";

import * as React from "react";
import { ExceptionRow } from "./exception-types";
import { SeverityBadge } from "@/components/ui/severity-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";

type Role = "Admin" | "Reviewer" | "Approver" | "Viewer";

export function ExceptionDetail(props: {
  ex: ExceptionRow;
  role: Role;
  onSelectEvidence: () => void;
  onResolve?: () => Promise<void>;
  onWaive?: (waiver_reason: string) => Promise<void>;
}) {
  const { ex, role, onSelectEvidence, onResolve, onWaive } = props;

  const canResolve = role === "Reviewer" || role === "Approver" || role === "Admin";
  const canWaive = role === "Approver" || role === "Admin";

  const [busy, setBusy] = React.useState(false);
  const [waiveReason, setWaiveReason] = React.useState("");

  const doResolve = async () => {
    if (!onResolve) return;
    setBusy(true);
    try {
      await onResolve();
    } finally {
      setBusy(false);
    }
  };

  const doWaive = async () => {
    if (!onWaive) return;
    const reason = waiveReason.trim();
    if (!reason) return;
    setBusy(true);
    try {
      await onWaive(reason);
      setWaiveReason("");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div>
            <CardTitle className="text-sm">{ex.title}</CardTitle>
            <div className="mt-1 text-xs text-muted-foreground">
              ID: {ex.id} • Module: {ex.module}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <SeverityBadge severity={ex.severity} />
            <Badge variant="outline">{ex.status.toUpperCase()}</Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        <div className="text-sm">{ex.description}</div>

        {ex.cp_text ? (
          <>
            <Separator />
            <div>
              <div className="text-xs font-medium text-muted-foreground">Recommended CP</div>
              <div className="mt-1 text-sm">{ex.cp_text}</div>
            </div>
          </>
        ) : null}

        {ex.status === "waived" && ex.waiver_reason ? (
          <>
            <Separator />
            <div>
              <div className="text-xs font-medium text-muted-foreground">Waiver Reason</div>
              <div className="mt-1 text-sm">{ex.waiver_reason}</div>
            </div>
          </>
        ) : null}

        <Separator />

        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" onClick={onSelectEvidence}>
            View evidence references
          </Button>

          <Button
            variant="outline"
            disabled={!canResolve || busy || ex.status !== "open"}
            onClick={doResolve}
          >
            Mark resolved
          </Button>

          <Dialog>
            <DialogTrigger asChild>
              <Button
                variant="outline"
                disabled={!canWaive || busy || ex.status !== "open"}
              >
                Waive
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Waive Exception</DialogTitle>
              </DialogHeader>
              <div className="text-sm text-muted-foreground">
                Waiver requires Approver role and a documented waiver reason.
              </div>
              <div className="mt-3">
                <div className="text-xs font-medium text-muted-foreground">Waiver reason</div>
                <Textarea
                  value={waiveReason}
                  onChange={(e) => setWaiveReason(e.target.value)}
                  placeholder="Enter waiver reason (bank language, concise but specific)…"
                  className="mt-2"
                />
              </div>
              <DialogFooter className="mt-4">
                <Button
                  onClick={doWaive}
                  disabled={!waiveReason.trim() || busy || !canWaive}
                >
                  Confirm waiver
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>

        <div className="text-xs text-muted-foreground">
          Role: {role}. Next: enforce RBAC server-side + write audit log entries.
        </div>
      </CardContent>
    </Card>
  );
}
