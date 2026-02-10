import { NextResponse } from "next/server";

export async function GET() {
  // TEMP: until auth is wired, take from env or default. Later derive from session/JWT.
  const role =
    (process.env.DEV_ROLE as "Admin" | "Reviewer" | "Approver" | "Viewer") ??
    "Reviewer";
  const email =
    (process.env.DEV_EMAIL as string) ?? "user@example.com";
  const org_name =
    (process.env.DEV_ORG_NAME as string) ?? "Organization";

  return NextResponse.json({ role, email, org_name });
}
