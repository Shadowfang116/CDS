"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { PRODUCT_WALKTHROUGH_STEPS } from "@/config/product-walkthrough";
import { HELP_OPEN_EVENT } from "@/lib/help";

const EXTRA_SECTIONS = [
  {
    title: "Keyboard",
    description:
      "J / K move pages. N jumps to the next blocker. E attaches the current page or selected text as evidence. The Matter is the workspace — do not leave it to confirm a field or clear a finding.",
  },
  {
    title: "Evidence workflow",
    description:
      "Select text on the page or attach the whole page to the finding in the Work pane. Verified, Resolved, and Confirmed all require a document and page. OCR values stay Proposed until you confirm them against the source.",
  },
  {
    title: "How waivers work",
    description:
      "High exceptions that are waivable require an Approver and a reason. Hard-stop findings cannot be waived. Maker and checker are separate people; the API refuses self-approval, including for Admin.",
  },
] as const;

const SECTIONS = [...PRODUCT_WALKTHROUGH_STEPS, ...EXTRA_SECTIONS];

export function HelpDialog() {
  const [open, setOpen] = React.useState(false);
  const [index, setIndex] = React.useState(0);

  React.useEffect(() => {
    const onOpen = () => {
      setIndex(0);
      setOpen(true);
    };
    window.addEventListener(HELP_OPEN_EVENT, onOpen);
    return () => window.removeEventListener(HELP_OPEN_EVENT, onOpen);
  }, []);

  const current = SECTIONS[index];
  const last = index === SECTIONS.length - 1;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-w-xl gap-4 border-border bg-background p-6">
        <DialogHeader>
          <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            CDS Help · {index + 1} / {SECTIONS.length}
          </p>
          <DialogTitle className="text-lg font-medium tracking-[-0.02em]">{current.title}</DialogTitle>
        </DialogHeader>
        <p className="text-sm leading-relaxed text-muted-foreground">{current.description}</p>
        <div className="flex justify-between gap-2">
          <Button type="button" variant="ghost" disabled={index === 0} onClick={() => setIndex((value) => value - 1)}>
            Previous
          </Button>
          <Button type="button" onClick={() => (last ? setOpen(false) : setIndex((value) => value + 1))}>
            {last ? "Close" : "Next"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
