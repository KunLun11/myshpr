# ADR-02: AsyncSession + repositories + services

**Status:** Accepted.

## Decision

- Engine/session factory created once; `get_session()` yields one `AsyncSession` per request.
- Repositories accept a session, never commit, never import HTTP.
- Services own business rules and own the transaction (`async with session.begin()`).
- Routers validate input, call a service, return a Pydantic schema.
- Complex read models (dashboard) live in a dedicated query module with explicit joins.

See [ADR-01](adr-01-sqlalchemy.md).
