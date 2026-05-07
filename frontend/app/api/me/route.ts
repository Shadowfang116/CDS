import { NextRequest, NextResponse } from "next/server";

const API_INTERNAL_BASE_URL = process.env.API_INTERNAL_BASE_URL ?? "http://api:8000";

export async function GET(request: NextRequest) {
  const cookie = request.headers.get("cookie");
  const response = await fetch(`${API_INTERNAL_BASE_URL}/api/v1/auth/me`, {
    headers: cookie ? { cookie } : {},
    cache: "no-store",
  });

  const body = await response.text();

  return new NextResponse(body, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
    },
  });
}
