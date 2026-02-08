import { NextResponse } from "next/server";

export async function GET() {
  // TEMP: until auth is wired, take role from header or default to Reviewer.
  // You can later derive from session/JWT/org membership.
  const role =
    (process.env.DEV_ROLE as "Admin" | "Reviewer" | "Approver" | "Viewer") ??
    "Reviewer";

  return NextResponse.json({ role });
}
