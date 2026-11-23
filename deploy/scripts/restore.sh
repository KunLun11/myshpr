#!/usr/bin/env bash
# Restore a Postgres dump and (optionally) the media archive.
#
#   deploy/scripts/restore.sh db-20261123-030000.dump [--yes] [--media media-...tgz]
#
# DESTRUCTIVE: pg_restore runs with --clean --if-exists. Stop the backend and
# worker first. Always restore into a staging database when rehearsing.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-${SCRIPT_DIR}/../docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-${SCRIPT_DIR}/../.env}"

DUMP="${1:-}"
shift || true
CONFIRM="no"
MEDIA=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes) CONFIRM="yes" ;;
    --media) MEDIA="${2:-}"; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

if [[ -z "${DUMP}" || ! -f "${DUMP}" ]]; then
  echo "Usage: $0 <db-backup.dump> [--yes] [--media <media-backup.tgz>]" >&2
  exit 2
fi
if [[ "${CONFIRM}" != "yes" ]]; then
  echo "This will overwrite the production database. Re-run with --yes." >&2
  exit 1
fi
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

POSTGRES_USER="${POSTGRES_USER:-myschoolproject}"
POSTGRES_DB="${POSTGRES_DB:-myschoolproject}"

compose() {
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
}

echo "==> Stopping backend and worker"
compose stop backend worker

echo "==> Restoring database"
compose exec -T db pg_restore -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
  --clean --if-exists --no-owner < "${DUMP}"

if [[ -n "${MEDIA}" ]]; then
  if [[ ! -f "${MEDIA}" ]]; then
    echo "Media archive not found: ${MEDIA}" >&2
    exit 1
  fi
  echo "==> Restoring media volume"
  compose exec -T backend sh -c 'rm -rf /app/media && mkdir -p /app/media'
  compose exec -T backend tar xzf - -C /app < "${MEDIA}"
fi

echo "==> Starting backend and worker"
compose start backend worker

echo "Restore complete. Run deploy/scripts/smoke.sh next."
