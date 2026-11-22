import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Optimistic auth guard only (see ADR-03/ADR-04). It checks for the presence
 * of a session cookie and redirects; it never validates the token. Real
 * authorization happens on the server (FastAPI + server components).
 */
const PROTECTED_PREFIXES = ["/cabinet", "/teacher", "/admin"];

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isProtected = PROTECTED_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );

  if (!isProtected) {
    return NextResponse.next();
  }

  const hasSession = request.cookies.has("refresh_token");
  if (hasSession) {
    return NextResponse.next();
  }

  const loginUrl = new URL("/login", request.url);
  loginUrl.searchParams.set("next", pathname);
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: ["/cabinet/:path*", "/teacher/:path*", "/admin/:path*"],
};
