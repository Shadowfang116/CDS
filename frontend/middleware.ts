import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';

const PUBLIC_PATHS = ['/', '/login', '/favicon.ico'];
const PASSWORD_CHANGE_PATH = '/change-password';

type SessionPayload = {
  exp?: number;
  must_change_password?: boolean;
};

function getSessionPayload(token: string | undefined): SessionPayload | null {
  if (!token) {
    return null;
  }

  const parts = token.split('.');
  if (parts.length !== 3) {
    return null;
  }

  try {
    const padded = parts[1].replace(/-/g, '+').replace(/_/g, '/').padEnd(Math.ceil(parts[1].length / 4) * 4, '=');
    const payload = JSON.parse(atob(padded)) as SessionPayload;
    if (typeof payload.exp === 'number' && payload.exp * 1000 <= Date.now()) {
      return null;
    }
    return payload;
  } catch {
    return null;
  }
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const accessToken = request.cookies.get('access_token')?.value;
  const session = getSessionPayload(accessToken);
  const hasSession = session !== null;
  const mustChangePassword = session?.must_change_password === true;

  if (
    pathname.startsWith('/api')
    || pathname.startsWith('/_next')
    || pathname.includes('.')
  ) {
    return NextResponse.next();
  }

  if (PUBLIC_PATHS.includes(pathname)) {
    if (hasSession && (pathname === '/' || pathname === '/login')) {
      return NextResponse.redirect(new URL(mustChangePassword ? PASSWORD_CHANGE_PATH : '/dashboard', request.url));
    }
    return NextResponse.next();
  }

  if (!hasSession) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('next', `${pathname}${request.nextUrl.search}`);
    return NextResponse.redirect(loginUrl);
  }

  if (mustChangePassword && pathname !== PASSWORD_CHANGE_PATH) {
    return NextResponse.redirect(new URL(PASSWORD_CHANGE_PATH, request.url));
  }

  if (!mustChangePassword && pathname === PASSWORD_CHANGE_PATH) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: '/:path*',
};
