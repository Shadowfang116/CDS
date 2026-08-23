import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

type CdsPillTone = "neutral" | "high" | "medium" | "low" | "good" | "stale" | "missing" | "proposed" | "confirmed" | "blocking" | "fail";

const TONE_CLASS: Record<CdsPillTone, string> = {
  neutral: "",
  high: "cds-pill-high",
  medium: "cds-pill-medium",
  low: "cds-pill-low",
  good: "cds-pill-good",
  stale: "cds-pill-stale",
  missing: "cds-pill-missing",
  proposed: "cds-pill-proposed",
  confirmed: "cds-pill-confirmed",
  blocking: "cds-pill-blocking",
  fail: "cds-pill-fail",
};

export function CdsPill({
  children,
  tone = "neutral",
  className,
}: {
  children: ReactNode;
  tone?: CdsPillTone;
  className?: string;
}) {
  return <span className={cn("cds-pill", TONE_CLASS[tone], className)}>{children}</span>;
}

export function severityTone(severity?: string | null): CdsPillTone {
  const value = (severity ?? "").toLowerCase();
  if (value === "high") return "high";
  if (value === "medium") return "medium";
  if (value === "low") return "low";
  return "neutral";
}
