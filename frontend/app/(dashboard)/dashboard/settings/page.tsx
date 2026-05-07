"use client";

import * as React from "react";
import { SetPageChrome } from "@/components/layout/set-page-chrome";
import { getMe } from "@/lib/api";

type WorkspaceUser = {
  displayName: string;
  email: string;
  role: string;
  orgName: string;
};

function toWorkspaceUser(raw: Record<string, unknown>): WorkspaceUser {
  const email = typeof raw.email === "string" ? raw.email : "";
  const role = typeof raw.role === "string" ? raw.role : "Reviewer";
  const orgName = typeof raw.org_name === "string" ? raw.org_name : "";
  const displayName =
    typeof raw.name === "string" && raw.name.trim().length > 0
      ? raw.name.trim()
      : email.split("@")[0] || role;
  return { displayName, email, role, orgName };
}

export default function SettingsPage() {
  const [user, setUser] = React.useState<WorkspaceUser | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    void (getMe() as Promise<Record<string, unknown>>)
      .then((raw) => {
        if (!cancelled) setUser(toWorkspaceUser(raw));
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const name = user?.displayName ?? "—";
  const email = user?.email ?? "—";
  const role = user?.role ?? "—";
  const organisation = user?.orgName ?? "—";

  return (
    <>
      <SetPageChrome
        title="Profile & Settings"
        subtitle="Workspace account details"
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Profile & Settings" },
        ]}
      />

      <div className="flex flex-col gap-6" data-dashboard-reveal>
        <section className="rounded-lg border border-zinc-800/80 bg-zinc-950 p-5">
          <h2 className="text-base font-semibold text-zinc-100">
            Profile &amp; Settings
          </h2>
          <p className="mt-1 text-sm text-zinc-400">
            Review your account identity and workspace access details.
          </p>
        </section>

        <section className="rounded-lg border border-zinc-800/80 bg-zinc-900/90 p-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <p className="text-xs uppercase tracking-[0.08em] text-zinc-500">
                Name
              </p>
              <p className="mt-1 text-sm text-zinc-100">{name}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.08em] text-zinc-500">
                Email
              </p>
              <p className="mt-1 text-sm text-zinc-100">{email}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.08em] text-zinc-500">
                Role
              </p>
              <p className="mt-1 text-sm text-zinc-100">{role}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.08em] text-zinc-500">
                Organisation
              </p>
              <p className="mt-1 text-sm text-zinc-100">{organisation}</p>
            </div>
          </div>
        </section>

        <section className="rounded-lg border border-zinc-800/80 bg-zinc-950 p-5">
          <h3 className="text-sm font-semibold text-zinc-100">
            Change Password
          </h3>
          <p className="mt-2 text-sm text-zinc-300">
            Password changes are managed by your administrator.
          </p>
        </section>
      </div>
    </>
  );
}
