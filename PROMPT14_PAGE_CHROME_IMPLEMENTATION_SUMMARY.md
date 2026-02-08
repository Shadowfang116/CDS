# Prompt 14: Header Titles, Breadcrumbs, Page Actions, Sidebar Persistence - Implementation Summary

## Overview
Implemented an opt-in system for dynamic page titles, breadcrumbs, per-page header actions, and sidebar state persistence. All changes are minimal and backward-compatible.

## Files Created

### 1. `frontend/components/layout/page-chrome.tsx`
- React context + hook for page chrome state
- Exposes: `setTitle()`, `setBreadcrumbs()`, `setActions()`
- Defaults: title="", breadcrumbs=[], actions=null
- Provider stores state and exposes setters

### 2. `frontend/components/layout/set-page-chrome.tsx`
- Helper component that calls chrome setters on mount/update
- Resets to defaults on unmount (prevents sticky chrome across navigation)
- Props: `title?: string`, `breadcrumbs?: Breadcrumb[]`, `actions?: ReactNode`

## Files Modified

### 1. `frontend/components/layout/app-shell.tsx`
- Wrapped shell content (header + main) in `<PageChromeProvider>`
- Header layout:
  - **Left**: SidebarTrigger
  - **Middle**: Breadcrumbs + Title (from context)
    - Breadcrumbs: inline, "/" separators, last crumb not a link, truncate on small screens
    - Title: fallback to "Dashboard" if empty
  - **Right**: actions slot (render if not null)
- Backward compatible: still accepts `title` and `actions` props for non-context usage

### 2. `frontend/components/ui/sidebar.tsx`
- Added localStorage persistence for sidebar open/closed state
- Storage key: `"brp.sidebar.open"`
- On first client load, initialize from stored value (default true)
- On toggle, write to localStorage
- SSR-safe: only access localStorage when `typeof window !== "undefined"`

### 3. `frontend/components/layout/conditional-app-shell.tsx`
- Updated to exclude auth routes from AppShell
- Checks for `/login`, `/auth/login`, `/signin` routes
- If no auth routes exist, behavior unchanged

### 4. `frontend/app/page.tsx` (Cases)
- Added `<SetPageChrome title="Cases" breadcrumbs={[{label:"Cases"}]} />`
- Wrapped return in fragment to include SetPageChrome

### 5. `frontend/app/dashboard/page.tsx`
- Added import for `SetPageChrome`
- Added `<SetPageChrome title="Dashboard" breadcrumbs={[{label:"Dashboard"}]} />`
- Already had fragment wrapper from previous prompt

### 6. `frontend/app/cases/[id]/page.tsx` (Case Detail)
- Added import for `SetPageChrome`
- Added `<SetPageChrome>` with:
  - `title={caseData?.title || 'Case'}`
  - `breadcrumbs={[{label:"Cases", href:"/"}, {label: caseData?.title || 'Case'}]}`
  - `actions={autofillAction}` - conditionally shows "Run Autofill" button in header when dossier tab is active
- Wrapped return in fragment

## Implementation Details

### Page Chrome Context
- Context provides isolated state per page
- Automatically resets on navigation (via SetPageChrome unmount)
- No global state pollution

### Breadcrumbs
- Inline display with "/" separators
- Last crumb is not a link (current page)
- Truncates on small screens (max-width: 120px per crumb)
- Responsive: hides separator on very small screens

### Sidebar Persistence
- State persists across page refreshes
- Defaults to `true` (open) if no stored value
- Only writes on toggle (not on every state change)
- SSR-safe implementation

### Page Actions
- Actions slot in header (right side, next to NotificationBell)
- Only renders if not null
- Example: Autofill button in case detail page (only shows in dossier tab)

## Where SetPageChrome Was Added

1. **`frontend/app/page.tsx`** (line ~240)
   ```tsx
   <SetPageChrome title="Cases" breadcrumbs={[{ label: "Cases" }]} />
   ```

2. **`frontend/app/dashboard/page.tsx`** (line ~241)
   ```tsx
   <SetPageChrome title="Dashboard" breadcrumbs={[{ label: "Dashboard" }]} />
   ```

3. **`frontend/app/cases/[id]/page.tsx`** (line ~525)
   ```tsx
   <SetPageChrome
     title={caseData?.title || 'Case'}
     breadcrumbs={[
       { label: 'Cases', href: '/' },
       { label: caseData?.title || 'Case' }
     ]}
     actions={autofillAction}
   />
   ```

## Sidebar Persistence Verification

### Implementation
- Storage key: `"brp.sidebar.open"`
- Location: `frontend/components/ui/sidebar.tsx` (lines ~49-67)
- Initialization: Reads from localStorage on mount (SSR-safe)
- Persistence: Writes to localStorage on toggle

### Testing
1. Open sidebar (default: open)
2. Collapse sidebar (click trigger or Cmd/Ctrl+B)
3. Refresh page
4. **Expected**: Sidebar state persists (closed if collapsed, open if expanded)

## Acceptance Checks

### ✅ Dynamic Page Titles
- Navigate to `/` → Title: "Cases"
- Navigate to `/dashboard` → Title: "Dashboard"
- Navigate to `/cases/{id}` → Title: Case title
- Navigate away → Title resets (no sticky chrome)

### ✅ Breadcrumbs
- `/` → "Cases"
- `/dashboard` → "Dashboard"
- `/cases/{id}` → "Cases / Case Title"
- Breadcrumbs are clickable (except last)

### ✅ Page Actions
- Case detail page shows "Run Autofill" button in header when dossier tab is active
- Button disappears when switching to other tabs

### ✅ Sidebar Persistence
- Collapse sidebar → Refresh → Sidebar remains collapsed
- Expand sidebar → Refresh → Sidebar remains expanded

### ✅ Build Verification
```bash
cd frontend
npm run build
```
**Expected**: Build passes without errors

## Notes

- **Minimal Diffs**: Only 3 pages modified (opt-in system)
- **Backward Compatible**: AppShell still accepts props for non-context usage
- **No Refactoring**: OCR Extractions panel unchanged
- **SSR-Safe**: All localStorage access guarded
- **Auto-Reset**: Chrome resets on navigation (prevents sticky state)

## Future Enhancements (Not in Scope)

1. Dynamic breadcrumbs based on route hierarchy
2. Breadcrumb generation from route metadata
3. Page action context for complex actions
4. Sidebar state sync across tabs (BroadcastChannel API)
