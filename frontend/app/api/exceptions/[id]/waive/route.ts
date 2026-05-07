import { NextResponse } from "next/server";

const API_INTERNAL_BASE_URL = (
  process.env.API_INTERNAL_BASE_URL || process.env.API_BASE_URL || "http://localhost:8000"
).replace(/\/+$/, "");

export async function POST(
  req: Request,
  ctx: { params: Promise<{ id: string }> }
) {
  const { id } = await ctx.params;
  const body = await req.json().catch(() => ({}));
  const cookie = req.headers.get("cookie");
  const auth = req.headers.get("authorization");

  const upstream = `${API_INTERNAL_BASE_URL}/api/v1/exceptions/${id}/waive`;
  const res = await fetch(upstream, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      ...(cookie ? { cookie } : {}),
      ...(auth ? { authorization: auth } : {}),
    },
    body: JSON.stringify(body),
  });

  const text = await res.text();
  return new NextResponse(text, {
    status: res.status,
    headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
  });
}
