"use client";

import * as React from "react";

export type Role = "Admin" | "Reviewer" | "Approver" | "Viewer";

export function useMeRole() {
  const [role, setRole] = React.useState<Role>("Viewer");
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    (async () => {
      try {
        const res = await fetch("/api/me", { cache: "no-store" });
        const data = await res.json();
        setRole((data?.role as Role) || "Viewer");
      } catch {
        setRole("Viewer");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return { role, loading };
}
