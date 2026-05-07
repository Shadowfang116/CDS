import { NextRequest, NextResponse } from 'next/server';

function upstream() {
  return (
    process.env.API_INTERNAL_BASE_URL ||
    process.env.API_BASE_URL ||
    'http://localhost:8000'
  ).replace(/\/+$/, '');
}

async function proxy(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  const slug = path.join('/');
  const search = req.nextUrl.search || '';
  const url = `${upstream()}/api/v1/${slug}${search}`;

  const headers = new Headers();
  for (const [k, v] of req.headers.entries()) {
    if (['host', 'connection', 'transfer-encoding'].includes(k.toLowerCase())) continue;
    headers.set(k, v);
  }

  const body =
    req.method === 'GET' || req.method === 'HEAD' ? undefined : req.body;

  const upstreamRes = await fetch(url, {
    method: req.method,
    headers,
    body,
    // @ts-expect-error Node fetch supports duplex
    duplex: body ? 'half' : undefined,
    cache: 'no-store',
  });

  const resHeaders = new Headers();
  for (const [k, v] of upstreamRes.headers.entries()) {
    if (['transfer-encoding', 'connection'].includes(k.toLowerCase())) continue;
    resHeaders.set(k, v);
  }

  return new NextResponse(upstreamRes.body, {
    status: upstreamRes.status,
    headers: resHeaders,
  });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
export const HEAD = proxy;
export const OPTIONS = proxy;
