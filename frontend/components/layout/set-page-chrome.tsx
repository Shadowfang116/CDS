"use client"

import { useEffect } from "react"
import { usePageChrome, type Breadcrumb } from "./page-chrome"

interface SetPageChromeProps {
  title?: string
  breadcrumbs?: Breadcrumb[]
  actions?: React.ReactNode | null
}

export function SetPageChrome({ title, breadcrumbs, actions }: SetPageChromeProps) {
  const { setTitle, setBreadcrumbs, setActions } = usePageChrome()

  useEffect(() => {
    // Set chrome on mount/update
    if (title !== undefined) {
      setTitle(title)
    }
    if (breadcrumbs !== undefined) {
      setBreadcrumbs(breadcrumbs)
    }
    if (actions !== undefined) {
      setActions(actions)
    }

    // Reset on unmount
    return () => {
      setTitle("")
      setBreadcrumbs([])
      setActions(null)
    }
  }, [title, breadcrumbs, actions, setTitle, setBreadcrumbs, setActions])

  return null
}
