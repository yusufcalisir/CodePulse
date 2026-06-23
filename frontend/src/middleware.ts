/**
 * Middleware — protects dashboard routes.
 * Unauthenticated users are redirected to the landing page.
 */

export { auth as middleware } from "@/auth";

export const config = {
  matcher: ["/dashboard/:path*", "/repos/:path*", "/insights/:path*"],
};
