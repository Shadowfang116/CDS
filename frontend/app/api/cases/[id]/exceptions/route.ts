import { NextResponse } from "next/server";

const API_BASE_URL = process.env.API_BASE_URL || "http://localhost:8000";

export async function GET(
  _req: Request,
  ctx: { params: Promise<{ id: string }> }
) {
  const { id } = await ctx.params;

  const upstream = `${API_BASE_URL}/api/v1/cases/${id}/exceptions`;

  const res = await fetch(upstream, {
    method: "GET",
    headers: { "content-type": "application/json" },
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
