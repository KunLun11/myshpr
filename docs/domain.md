# Domain model (MVP)

Source of truth for the full model: `TASKS.md` §5. This file summarises the
implemented schema (`backend/app/models/`) and the rules enforced so far.

## Tables

| Group | Tables |
|-------|--------|
| Organization & identity | `schools`, `academic_years`, `classes`, `users`, `student_profiles`, `class_invites`, `refresh_tokens` |
| Reference | `interest_areas`, `product_categories` |
| Core process | `projects`, `topic_submissions`, `topics` |
| Engagement | `checkpoints`, `notifications`, `project_events` |
| Work | `project_files`, `project_comments`, `checklist_items`, `project_checklist_states` |

## Project status scale

`idea(10) → topic_draft(20) → topic_submitted(30) → topic_approved(40) →
product_draft(50) → product_defined(60) → in_progress(70) → ready_for_defense(80) →
defended(90)`, plus `archived`.

Rank lives in `app/models/enums.py::PROJECT_STATUS_RANK` (not in enum ordering).

## Key integrity rules (DB-level, stage 1)

1. One project per student per academic year — `uq_projects_student_year`.
2. At most one active topic submission per project
   (`UNIQUE (project_id) WHERE status IN ('draft','submitted')`).
3. Exact duplicate topic title per school forbidden — `uq_topics_school_title`.
4. File size bounded — `ck_project_files_size` (`0 < size_bytes <= 26214400`).
5. One checklist state per (project, item) — `uq_project_checklist_states`.
6. One current academic year per school (partial unique index).
7. Global and school-scoped checkpoints/checklist items coexist
   (`UNIQUE NULLS NOT DISTINCT`).

Service-level rules (teacher cannot review own topic, school isolation, status
transitions forward-only) arrive with stages 2–5.

## Not modelled (intentionally)

Chats/video, online file review, grades/journal, parents, external integrations,
ML/embeddings topic checks.
