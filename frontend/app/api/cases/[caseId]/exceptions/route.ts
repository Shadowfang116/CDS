import { NextResponse } from "next/server";

// Use container-to-container hostname by default
const API_BASE_URL = process.env.API_BASE_URL || "http://api:8000";

export async function GET(
  req: Request,
  context: any
) {
  const { caseId } = (context?.params || {}) as { caseId: string };

  const upstream = `${API_BASE_URL}/api/v1/cases/${caseId}/exceptions`;

  // Forward Authorization header if present
  const auth = req.headers.get("authorization");
  const headers: Record<string, string> = { "content-type": "application/json" };
  if (auth) headers["authorization"] = auth;

  const res = await fetch(upstream, {
    method: "GET",
    headers,
    cache: "no-store",
  });

  const text = await res.text();
  if (!res.ok) {
    return NextResponse.json(
      { error: "upstream_error", status: res.status, body: text },
      { status: 502 }
    );
  }

  // upstream returns JSON already; keep as-is
  return new NextResponse(text, {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}
