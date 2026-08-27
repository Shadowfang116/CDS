'use client'

import * as React from 'react'
import { Moon, Sun } from 'lucide-react'

const THEME_KEY = 'bdp_theme'

function getStoredTheme(): 'dark' | 'light' {
  if (typeof window === 'undefined') return 'light'
  try {
    const v = localStorage.getItem(THEME_KEY)
    if (v === 'dark') return 'dark'
  } catch {
    // ignore
  }
  return 'light'
}

function applyTheme(theme: 'dark' | 'light') {
  const root = document.documentElement
  if (theme === 'dark') {
    root.classList.add('dark')
    root.classList.remove('light')
  } else {
    root.classList.remove('dark')
    root.classList.add('light')
  }
  try {
    localStorage.setItem(THEME_KEY, theme)
  } catch {
    // ignore
  }
}

export function ThemeToggle({ className }: { className?: string }) {
  const [theme, setTheme] = React.useState<'dark' | 'light'>('light')
  const [mounted, setMounted] = React.useState(false)

  React.useEffect(() => {
    const stored = getStoredTheme()
    setTheme(stored)
    applyTheme(stored)
    setMounted(true)
  }, [])

  const toggle = () => {
    const next: 'dark' | 'light' = theme === 'dark' ? 'light' : 'dark'
    setTheme(next)
    applyTheme(next)
  }

  if (!mounted) return null

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
      className={[
        'cds-hit-target flex size-8 items-center justify-center rounded-md border border-border bg-background text-muted-foreground transition-colors hover:bg-muted hover:text-foreground',
        className ?? '',
      ].join(' ')}
    >
      {theme === 'dark' ? <Sun className="size-4" /> : <Moon className="size-4" />}
    </button>
  )
}
