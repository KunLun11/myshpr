#!/usr/bin/env bash
# Post-deploy smoke test (T7.4).
#
#   BASE_URL=https://project.school.example deploy/scripts/smoke.sh
#
# Checks the public entrypoint, the BFF path to FastAPI and the security
# headers. Exit code is non-zero on the first failed check.
set -euo pipefail

BASE_URL="${BASE_URL:-https://project.school.example}"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

check_status() {
  local path="$1" expected="$2"
  local code
  code="$(curl -sS -o /dev/null -w '%{http_code}' "${BASE_URL}${path}")"
  [[ "${code}" == "${expected}" ]] || fail "${path} -> ${code} (expected ${expected})"
  echo "ok ${path} (${code})"
}

echo "Smoke test: ${BASE_URL}"

check_status "/login" 200
check_status "/api/backend/healthz" 200
check_status "/api/backend/readyz" 200

body="$(curl -sS "${BASE_URL}/api/backend/readyz")"
[[ "${body}" == *'"ready"'* ]] || fail "readyz body: ${body}"
echo "ok readyz body"

headers="$(curl -sSI "${BASE_URL}/login")"
grep -qi '^x-content-type-options: nosniff' <<<"${headers}" \
  || fail "missing X-Content-Type-Options"
grep -qi '^x-frame-options: DENY' <<<"${headers}" \
  || fail "missing X-Frame-Options"
echo "ok security headers"

admin_headers="$(curl -sSI "${BASE_URL}/admin")"
grep -qi '^x-robots-tag: noindex' <<<"${admin_headers}" \
  || fail "admin area is indexable"
echo "ok admin noindex"

echo "Smoke test passed."
