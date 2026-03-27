"use client";

import * as React from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { DocumentViewer } from "@/components/documents/DocumentViewer";

import { ExceptionsTable } from "@/components/exceptions/exceptions-table";
import { ExceptionDetail } from "@/components/exceptions/exception-detail";
import { ExceptionRow } from "@/components/exceptions/exception-types";

export function CaseDetailTabs(props: {
  caseId: string;
  exceptions: ExceptionRow[];
  onEvidenceFromException?: (ex: ExceptionRow) => void;
  onResolve?: (ex: ExceptionRow) => Promise<void>;
  onWaive?: (ex: ExceptionRow, waiver_reason: string) => Promise<void>;
  role: "Admin" | "Reviewer" | "Approver" | "Viewer";
}) {
  const { caseId, exceptions, onEvidenceFromException, onResolve, onWaive, role } = props;

  const [selectedId, setSelectedId] = React.useState<string>(exceptions[0]?.id ?? "");

  React.useEffect(() => {
    if (!selectedId && exceptions.length) setSelectedId(exceptions[0].id);
  }, [exceptions, selectedId]);

  const selected = React.useMemo(
    () => exceptions.find((e) => e.id === selectedId) ?? exceptions[0],
    [exceptions, selectedId]
  );

  return (
    <Tabs defaultValue="summary" className="w-full">
      <TabsList className="w-full justify-start">
        <TabsTrigger value="summary">Executive Summary</TabsTrigger>
        <TabsTrigger value="exceptions">Exceptions</TabsTrigger>
        <TabsTrigger value="cp">Conditions Precedent</TabsTrigger>
        <TabsTrigger value="documents">Documents</TabsTrigger>
        <TabsTrigger value="dossier">Dossier</TabsTrigger>
        <TabsTrigger value="audit">Audit</TabsTrigger>
      </TabsList>

      <TabsContent value="summary" className="mt-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Executive Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <EmptyState
              title="Not connected yet"
              description="Next: render structured dossier summary + key risks + recommended decision posture."
            />
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent value="exceptions" className="mt-4">
        <div className="grid gap-4 lg:grid-cols-[1fr_420px]">
          <ExceptionsTable rows={exceptions} selectedId={selectedId} onSelect={setSelectedId} />

          {selected ? (
            <ExceptionDetail
              ex={selected}
              role={role}
              onSelectEvidence={() => onEvidenceFromException?.(selected)}
              onResolve={() => onResolve?.(selected)}
              onWaive={(reason) => onWaive?.(selected, reason)}
            />
          ) : (
            <EmptyState
              title="No exception selected"
              description="Select an exception to review details and evidence."
            />
          )}
        </div>
      </TabsContent>

      <TabsContent value="cp" className="mt-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Conditions Precedent (CP)</CardTitle>
          </CardHeader>
          <CardContent>
            <EmptyState
              title="No CP data wired"
              description="Next: CP list (due date, evidence required, status) + close-out evidence workflow."
            />
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent value="documents" className="mt-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Documents / Annexures</CardTitle>
          </CardHeader>
          <CardContent>
            <DocumentViewer caseId={caseId} />
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent value="dossier" className="mt-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Dossier</CardTitle>
          </CardHeader>
          <CardContent>
            <EmptyState
              title="No dossier editor wired"
              description="Next: editable structured fields with audit logging and reviewer/approver constraints."
            />
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent value="audit" className="mt-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Audit</CardTitle>
          </CardHeader>
          <CardContent>
            <EmptyState
              title="No audit entries loaded"
              description="Next: audit table filterable by actor/action/entity with diff preview."
            />
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>
  );
}
