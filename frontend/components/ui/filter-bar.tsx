"use client";

import * as React from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";

export interface FilterBarProps {
  searchPlaceholder?: string;
  searchValue: string;
  onSearchChange: (value: string) => void;
  statusOptions?: { label: string; value: string }[];
  statusValue?: string | null;
  onStatusChange?: (value: string | null) => void;
  dateValue?: string | null;
  onDateChange?: (value: string | null) => void;
  rightActions?: React.ReactNode;
}

export function FilterBar(props: FilterBarProps) {
  const {
    searchPlaceholder = "Search…",
    searchValue,
    onSearchChange,
    statusOptions,
    statusValue,
    onStatusChange,
    dateValue,
    onDateChange,
    rightActions,
  } = props;

  const activeStatusLabel = statusOptions?.find((o) => o.value === statusValue)?.label || "All";

  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-center gap-2 flex-1 min-w-0">
        {statusOptions && onStatusChange ? (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="shrink-0">
                Status: {activeStatusLabel}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="min-w-[12rem]">
              <DropdownMenuItem onClick={() => onStatusChange(null)}>All</DropdownMenuItem>
              {statusOptions.map((opt) => (
                <DropdownMenuItem key={opt.value} onClick={() => onStatusChange(opt.value)}>
                  {opt.label}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        ) : null}

        {onDateChange ? (
          <input
            type="date"
            value={dateValue || ""}
            onChange={(e) => onDateChange(e.target.value || null)}
            className="h-9 rounded-md border border-input bg-background px-2 text-sm text-foreground"
          />
        ) : null}

        <Input
          placeholder={searchPlaceholder}
          value={searchValue}
          onChange={(e) => onSearchChange(e.target.value)}
          className="max-w-sm"
        />
      </div>

      {rightActions ? <div className="flex items-center gap-2">{rightActions}</div> : null}
    </div>
  );
}