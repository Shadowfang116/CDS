"use client"

import * as React from "react"

interface Breadcrumb {
  label: string
  href?: string
}

interface PageChromeContextValue {
  title: string
  breadcrumbs: Breadcrumb[]
  actions: React.ReactNode | null
  setTitle: (title: string) => void
  setBreadcrumbs: (breadcrumbs: Breadcrumb[]) => void
  setActions: (actions: React.ReactNode | null) => void
}

const PageChromeContext = React.createContext<PageChromeContextValue | null>(null)

export function PageChromeProvider({ children }: { children: React.ReactNode }) {
  const [title, setTitle] = React.useState<string>("")
  const [breadcrumbs, setBreadcrumbs] = React.useState<Breadcrumb[]>([])
  const [actions, setActions] = React.useState<React.ReactNode | null>(null)

  const value: PageChromeContextValue = React.useMemo(
    () => ({
      title,
      breadcrumbs,
      actions,
      setTitle,
      setBreadcrumbs,
      setActions,
    }),
    [title, breadcrumbs, actions]
  )

  return (
    <PageChromeContext.Provider value={value}>
      {children}
    </PageChromeContext.Provider>
  )
}

export function usePageChrome() {
  const context = React.useContext(PageChromeContext)
  if (!context) {
    throw new Error("usePageChrome must be used within PageChromeProvider")
  }
  return context
}

export type { Breadcrumb }
