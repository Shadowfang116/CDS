"use client";

import * as React from "react";

export type Role = "Admin" | "Reviewer" | "Approver" | "Viewer";

export interface CurrentUser {
  email: string | null;
  role: Role;
  orgName?: string | null;
}

/**
 * Returns the current user from /api/me (role; email when API provides it).
 * Use for role-aware UI (e.g. Admin-only sidebar items) and header display.
 */
export function useCurrentUser(): CurrentUser | null {
  const [user, setUser] = React.useState<CurrentUser | null>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/me", { cache: "no-store" });
        const data = await res.json();
        if (cancelled) return;
        setUser({
          email: data?.email ?? null,
          role: (data?.role as Role) || "Viewer",
          orgName: data?.org_name ?? null,
        });
      } catch {
        if (!cancelled) setUser(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) return null;
  return user;
}
