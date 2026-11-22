/**
 * Client-safe environment access.
 *
 * The browser talks to the same origin under `/api/backend`; Next rewrites
 * that to the FastAPI service (configured in `next.config.ts`). This keeps
 * auth cookies first-party and avoids CORS.
 */
export const env = {
  apiBase: process.env.NEXT_PUBLIC_API_BASE ?? "/api/backend",
  isProd: process.env.NODE_ENV === "production",
} as const;
