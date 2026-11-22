# ADR-03: Authentication (JWT + httpOnly cookies + BFF)

**Status:** Accepted.

## Decision

- Access token 15 min, refresh token 30 days.
- Both delivered as `httpOnly`, `Secure` (prod), `SameSite=Lax` cookies.
- Refresh tokens stored hashed, rotated on refresh; reuse revokes the whole chain.
- Frontend calls same-origin `/api/...`; Next proxies to FastAPI (no cross-origin cookies).
- `proxy.ts` does only an optimistic cookie-based redirect; real auth on the server.

Implemented in stage 2. Config for secrets/TTLs already validated at startup
(`app/core/config.py`). See [ADR-01](adr-01-sqlalchemy.md).
