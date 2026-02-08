"use client";

import * as React from "react";
import Link from "next/link";
import { ColumnDef } from "@tanstack/react-table";

import { CaseRow } from "./case-types";
import { CaseStatusPill } from "@/components/ui/case-status-pill";
import { SeverityBadge } from "@/components/ui/severity-badge";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

function shortId(id: string) {
  return id.length > 10 ? `${id.slice(0, 8)}…` : id;
}

export const casesColumns: ColumnDef<CaseRow>[] = [
  {
    accessorKey: "id",
    header: "Case",
    cell: ({ row }) => {
      const id = row.original.id;
      return (
        <div className="space-y-0.5">
          <div className="font-medium">{shortId(id)}</div>
          <div className="text-xs text-muted-foreground">{id}</div>
        </div>
      );
    },
  },
  {
    accessorKey: "borrower_name",
    header: "Borrower / Customer",
    cell: ({ row }) => (
      <div className="font-medium">{row.original.borrower_name}</div>
    ),
  },
  {
    accessorKey: "property_type",
    header: "Property",
    cell: ({ row }) => (
      <Badge variant="outline" className="font-medium">
        {row.original.property_type}
      </Badge>
    ),
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <CaseStatusPill status={row.original.status} />,
  },
  {
    accessorKey: "highest_severity",
    header: "Highest Severity",
    cell: ({ row }) => (
      <SeverityBadge severity={row.original.highest_severity} />
    ),
  },
  {
    accessorKey: "open_exceptions",
    header: "Open Exceptions",
  },
  {
    accessorKey: "open_cps",
    header: "Open CPs",
  },
  {
    accessorKey: "updated_at",
    header: "Updated",
    cell: ({ row }) => {
      const d = new Date(row.original.updated_at);
      const text = isNaN(d.getTime())
        ? row.original.updated_at
        : d.toLocaleString();
      return <div className="text-sm text-muted-foreground">{text}</div>;
    },
  },
  {
    id: "actions",
    header: "",
    cell: ({ row }) => {
      const id = row.original.id;
      return (
        <div className="flex justify-end">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm">
                Actions
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-52">
              <DropdownMenuLabel>Case Actions</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <Link href={`/dashboard/cases/${id}`}>Open case</Link>
              </DropdownMenuItem>
              <DropdownMenuItem disabled>
                Export Bank Pack (coming soon)
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      );
    },
  },
];
