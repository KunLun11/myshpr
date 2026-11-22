# ADR-07: One repo, two images, separate DB schemas

**Status:** Accepted.

## Decision

- `backend/` (FastAPI), `frontend/` (Next.js), `deploy/` (compose).
- One Postgres: schema `public` owned by FastAPI; schema `payload` owned by Payload
  if/when enabled. Owners never mix.
- DB roles: `app_migrator` (owns `public`, migrates), `app_rw` (runtime), `app_ro`
  (reports), `payload` (CMS).

See [ADR-05](adr-05-admin.md).
