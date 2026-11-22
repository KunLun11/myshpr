# ADR-09: Files (storage abstraction, private access)

**Status:** Accepted.

## Decision

- Files stored outside the DB; metadata in `project_files`.
- `StorageBackend` interface (`save`, `open`, `delete`, `presigned_url`); `LocalStorage`
  in dev, `S3Storage` in prod. Bucket private; download via authorized endpoint or a
  short-lived signed URL.
- Limits: 25 MB/file (`MAX_UPLOAD_BYTES`), configurable file count, MIME/extension
  allowlist, signature check, sha256 dedupe.
- Keys are opaque: `projects/{project_id}/{uuid}{ext}`; never use the original name as key.
- Soft delete in DB + deferred storage deletion; antivirus hook `uploaded -> available|quarantined`.

Implemented in stage 4. Schema (`project_files`) already present.
