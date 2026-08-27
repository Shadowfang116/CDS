import { NextResponse } from "next/server";
import { resolveApiBaseUrl } from "@/lib/runtime-config";

export async function GET(
  req: Request,
  context: { params: Promise<{ caseId: string }> }
) {
  const { caseId } = await context.params;
  const upstream = `${resolveApiBaseUrl(process.env).replace(/\/+$/, "")}/api/v1/cases/${caseId}/exceptions`;

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
