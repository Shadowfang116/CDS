import { NextResponse } from "next/server";

const API_INTERNAL_BASE_URL = (
  process.env.API_INTERNAL_BASE_URL || process.env.API_BASE_URL || "http://localhost:8000"
).replace(/\/+$/, "");

export async function GET(
  req: Request,
  context: { params: Promise<{ caseId: string }> }
) {
  const { caseId } = await context.params;
  const upstream = `${API_INTERNAL_BASE_URL}/api/v1/cases/${caseId}/exceptions`;

  const cookie = req.headers.get("cookie");
  const headers: Record<string, string> = { "content-type": "application/json" };
  if (cookie) {
    headers.cookie = cookie;
  }

  const res = await fetch(upstream, {
    method: "GET",
    headers,
    cache: "no-store",
  });

  const text = await res.text();
  if (!res.ok) {
    return new NextResponse(text, {
      status: res.status,
      headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
    });
  }

  return new NextResponse(text, {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}
