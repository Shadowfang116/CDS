"use client"

import * as React from "react"

import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import {
  PRODUCT_WALKTHROUGH_STEPS,
  PRODUCT_WALKTHROUGH_STORAGE_KEY,
} from "@/config/product-walkthrough"
import { BRAND } from "@/lib/brand"
import { cn } from "@/lib/utils"

type TutorialDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
}

function markTutorialCompleted() {
  if (typeof window === "undefined") {
    return
  }

  localStorage.setItem(PRODUCT_WALKTHROUGH_STORAGE_KEY, "true")
}

export default function TutorialDialog({ open, onOpenChange }: TutorialDialogProps) {
  const [stepIndex, setStepIndex] = React.useState(0)

  React.useEffect(() => {
    if (open) {
      setStepIndex(0)
    }
  }, [open])

  const totalSteps = PRODUCT_WALKTHROUGH_STEPS.length
  const currentStep = PRODUCT_WALKTHROUGH_STEPS[stepIndex]
  const isLastStep = stepIndex === totalSteps - 1
  const progressWidth = `${((stepIndex + 1) / totalSteps) * 100}%`

  const handleSkip = React.useCallback(() => {
    onOpenChange(false)
  }, [onOpenChange])

  const handleFinish = React.useCallback(() => {
    markTutorialCompleted()
    onOpenChange(false)
  }, [onOpenChange])

  const handleOpenChange = React.useCallback(
    (nextOpen: boolean) => {
      onOpenChange(nextOpen)
    },
    [onOpenChange]
  )

  const handlePrevious = React.useCallback(() => {
    setStepIndex((currentValue) => Math.max(0, currentValue - 1))
  }, [])

  const handleNext = React.useCallback(() => {
    if (isLastStep) {
      handleFinish()
      return
    }

    setStepIndex((currentValue) => Math.min(totalSteps - 1, currentValue + 1))
  }, [handleFinish, isLastStep, totalSteps])

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent
        overlayClassName="bg-[rgba(16,18,21,0.8)] backdrop-blur-[2px]"
        className="max-w-[40rem] gap-0 overflow-hidden border-zinc-800/90 bg-[linear-gradient(180deg,rgba(28,30,33,0.98),rgba(20,22,25,0.98))] p-0 shadow-[0_28px_80px_rgba(0,0,0,0.5)] [&>button]:right-5 [&>button]:top-5 [&>button]:rounded-md [&>button]:text-zinc-500 [&>button]:ring-0 [&>button]:hover:bg-zinc-900 [&>button]:hover:text-zinc-100 [&>button]:data-[state=open]:bg-transparent"
      >
        <DialogHeader className="gap-4 border-b border-zinc-800/90 px-6 py-5 text-left">
          <div className="flex items-center justify-between gap-4 pr-10">
            <p className="text-xs font-medium tracking-[0.04em] text-zinc-500">
              Step {stepIndex + 1} of {totalSteps} — {currentStep.title}
            </p>
            <div className="text-xs text-zinc-600">{BRAND.full}</div>
          </div>
          <div className="space-y-3">
            <DialogTitle className="text-xl font-semibold text-zinc-100">
              {currentStep.title}
            </DialogTitle>
            <div className="h-1.5 overflow-hidden rounded-full bg-zinc-900">
              <div
                className="h-full rounded-full bg-zinc-500 transition-[width] duration-200 ease-out"
                style={{ width: progressWidth }}
              />
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-5 px-6 py-6">
          <p className="text-sm leading-7 text-zinc-300">{currentStep.description}</p>

          <div className="flex items-center gap-2">
            {PRODUCT_WALKTHROUGH_STEPS.map((step, index) => (
              <span
                key={step.title}
                className={cn(
                  "h-2 w-2 rounded-full bg-zinc-800 transition-colors duration-200",
                  index === stepIndex && "bg-zinc-500",
                  index < stepIndex && "bg-zinc-600"
                )}
              />
            ))}
          </div>
        </div>

        <div className="flex items-center justify-between gap-3 border-t border-zinc-800/90 bg-zinc-950/50 px-6 py-4">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="text-zinc-400 hover:bg-zinc-900 hover:text-zinc-100"
            onClick={handleSkip}
          >
            Skip for now
          </Button>

          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={stepIndex === 0}
              className="border-zinc-800 bg-zinc-950/80 text-zinc-300 hover:bg-zinc-900 hover:text-zinc-100"
              onClick={handlePrevious}
            >
              Back
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="border-zinc-700 bg-zinc-800 text-zinc-100 hover:border-zinc-600 hover:bg-zinc-700"
              onClick={handleNext}
            >
              {isLastStep ? "Finish" : "Next"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

