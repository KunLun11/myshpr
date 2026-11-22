# ADR-04: Next.js 16 (proxy.ts, Cache Components)

**Status:** Accepted.

## Decision

- `middleware.ts` is `proxy.ts` in Next 16 — use only `proxy.ts`.
- `cookies()`/session reads are request-time; wrap user-dependent UI in `<Suspense>`.
- `cacheComponents` and `partialPrefetching` are enabled: use `use cache`/`cacheLife`,
  not `dynamic`/`revalidate`/`fetchCache`.
- Read local docs in `frontend/node_modules/next/dist/docs/` before writing code
  (see `frontend/AGENTS.md`).

See [ADR-03](adr-03-auth.md).
