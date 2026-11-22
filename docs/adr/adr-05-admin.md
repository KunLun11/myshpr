# ADR-05: Admin (thin FastAPI CRUD, Payload later)

**Status:** Accepted.

## Decision

- MVP admin = thin FastAPI CRUD endpoints + simple Next pages for reference data.
- Payload CMS, if adopted, is a **separate service/app** (stage 6), never an admin over
  operational tables owned by FastAPI.
- One owner per table/schema. See [ADR-07](adr-07-repo-schema.md).
