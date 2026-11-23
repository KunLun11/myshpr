#!/usr/bin/env bash
# Daily backup for the production stack (T7.4).
#
#   deploy/scripts/backup.sh
#
# Outputs `db-<ts>.dump` (pg_dump custom format) and, when files live on the
# local volume, `media-<ts>.tgz`, plus SHA-256 checksums. Copy the directory
# off the server (rsync, object storage, tape) — a backup on the same disk is
# not a backup.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-${SCRIPT_DIR}/../docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-${SCRIPT_DIR}/../.env}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}; copy deploy/.env.example and fill it in." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

BACKUP_DIR="${BACKUP_DIR:-./backups}"
BACKUP_KEEP_DAYS="${BACKUP_KEEP_DAYS:-30}"
POSTGRES_USER="${POSTGRES_USER:-myschoolproject}"
POSTGRES_DB="${POSTGRES_DB:-myschoolproject}"
TS="$(date +%Y%m%d-%H%M%S)"

mkdir -p "${BACKUP_DIR}"

compose() {
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
}

echo "==> Postgres dump"
compose exec -T db pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Fc \
  > "${BACKUP_DIR}/db-${TS}.dump"

if [[ "${STORAGE_BACKEND:-local}" == "local" ]]; then
  echo "==> Media volume archive"
  compose exec -T backend tar czf - -C /app media \
    > "${BACKUP_DIR}/media-${TS}.tgz"
else
  echo "==> Files live in object storage; rely on bucket versioning/replication."
fi

echo "==> Checksums"
(
  cd "${BACKUP_DIR}"
  files=("db-${TS}.dump")
  if [[ -f "media-${TS}.tgz" ]]; then
    files+=("media-${TS}.tgz")
  fi
  sha256sum "${files[@]}" > "SHA256SUMS-${TS}"
)

echo "==> Retention (${BACKUP_KEEP_DAYS} days)"
find "${BACKUP_DIR}" -maxdepth 1 -type f -mtime "+${BACKUP_KEEP_DAYS}" \
  \( -name 'db-*.dump' -o -name 'media-*.tgz' -o -name 'SHA256SUMS-*' \) -delete

echo "Done: ${BACKUP_DIR} (${TS})"
echo "Verify a restore monthly: deploy/scripts/restore.sh ${BACKUP_DIR}/db-${TS}.dump --yes"
