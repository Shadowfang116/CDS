"use client"

import { useEffect } from "react"
import { usePageChrome, type Breadcrumb } from "./page-chrome"

interface SetPageChromeProps {
  title?: string
  subtitle?: string
  breadcrumbs?: Breadcrumb[]
  actions?: React.ReactNode | null
}

export function SetPageChrome({ title, subtitle, breadcrumbs, actions }: SetPageChromeProps) {
  const { setTitle, setSubtitle, setBreadcrumbs, setActions } = usePageChrome()

  useEffect(() => {
    // Set chrome on mount/update
    if (title !== undefined) {
      setTitle(title)
    }
    if (subtitle !== undefined) {
      setSubtitle(subtitle)
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
      setSubtitle("")
      setBreadcrumbs([])
      setActions(null)
    }
  }, [title, subtitle, breadcrumbs, actions, setTitle, setSubtitle, setBreadcrumbs, setActions])

  return null
}
