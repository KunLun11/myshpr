# ADR-05: Admin (thin FastAPI CRUD, Payload later)

**Status:** Accepted. Stage 6 decision: **variant A — no Payload for the MVP.**

## Decision

- MVP admin = thin FastAPI CRUD endpoints + Next pages for operational data.
- Payload CMS, if adopted, is a **separate service/app**, never an admin over
  operational tables owned by FastAPI.
- One owner per table/schema. See [ADR-07](adr-07-repo-schema.md).

## Stage 6 spike (T6.1/T6.2)

The spike was a desk review, not a temporary Payload install: adding
`payload`, `@payloadcms/next` and a second Next runtime to the repo for an
MVP with one school is disproportionate. Findings:

| Question | Finding for this project |
|---|---|
| Does Payload solve an MVP problem? | No. The MVP needs CRUD for schools, years, classes, reference data, checkpoints and checklist templates — all narrow, well-typed forms. |
| Who would own the data? | FastAPI already owns `public`. Payload would own a second schema (`payload`) and a second migration pipeline. |
| Version coupling | Payload pins its own Next/React range. Keeping the product frontend on Next 16 and an admin app on a different version doubles the build and upgrade surface. |
| Auth | The product already has JWT cookies + RBAC. Payload would add a second admin identity store unless integrated. |
| Content editing | Interest areas, product categories and guidance are edited rarely; an inline admin form is enough. |

**Go/no-go:** no-go for Payload in the MVP. Revisit only if non-technical staff
start editing long-form help content weekly; then build a separate `admin/`
app (variant B), never inside `frontend/` (variant C).

## What stage 6 actually shipped (variant A)

- FastAPI admin API:
  - `GET/POST/PATCH /admin/schools` (super admin);
  - `GET/POST/PATCH /admin/academic-years` (school-scoped, one current year);
  - `GET/POST/PATCH /admin/interest-areas` and `/admin/product-categories`
    (read for school admins, mutations for super admin);
  - existing `/admin/classes`, `/admin/checklist-items`, `/admin/checkpoints`;
  - `GET /admin/students`, `POST /admin/students/import` (CSV);
  - `GET /admin/audit-log`.
- Every admin mutation writes to `audit_log` with actor, school, action,
  entity and a JSON payload (no secrets).
- Origin (CSRF) guard for unsafe methods; `SameSite=Lax` cookies remain the
  primary defence.
- Next pages under `/admin/**`: годы, справочники, чек-лист, точки, ученики,
  журнал, школы. Dense tables, inline edit panels, skeletons, 44px targets.
- Admin routes are `noindex` (metadata + `X-Robots-Tag` + `robots.txt`).

## Consequences

- FastAPI stays the single owner of `public`; there is no second schema owner.
- Admin UI uses the same session/RBAC and design tokens as the product.
- If Payload is adopted later, it must be a separate service with its own
  schema, secrets and deploy step; FastAPI would read its content through a
  read-only role or webhook cache invalidation.
- The admin is not hardened as a separate public app (no VPN/2FA yet); see
  `docs/runbook.md` for the current operational constraints.
