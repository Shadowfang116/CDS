import { NextRequest, NextResponse } from "next/server";
import { resolveApiBaseUrl } from "@/lib/runtime-config";

export async function GET(request: NextRequest) {
  const cookie = request.headers.get("cookie");
  try {
    const response = await fetch(`${resolveApiBaseUrl(process.env)}/api/v1/auth/me`, {
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
  } catch {
    return NextResponse.json(
      { detail: "The CDS API is unavailable. Start the local API service and try again." },
      { status: 503 }
    );
  }
}
