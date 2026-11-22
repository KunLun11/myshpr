# ADR-10: Comments and checklists (no chat, no grades)

**Status:** Accepted.

## Decision

- Comments: teacher/school_admin write, student reads. No threads/replies.
  `visibility`: `student_visible` | `teachers_only`. Optional `stage`.
  New student-visible comment triggers a `new_comment` notification.
- Checklists: `checklist_items` template per year/school; `project_checklist_states`
  per project. States: `pending`, `in_progress`, `done`, `verified`, `skipped`.
  Student sets `in_progress`/`done`; only teacher sets `verified`/`skipped`.
- Checklist tracks progress, never grades. See [ADR-08](adr-08-privacy.md).
