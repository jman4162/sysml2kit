#!/usr/bin/env bash
# Wait for a Systems Modeling API server to answer; used locally and in CI.
set -u

URL="${SYSML2KIT_API_URL:-http://localhost:9000}"
DEADLINE=$((SECONDS + ${WAIT_FOR_API_TIMEOUT:-180}))

echo "[wait_for_api] polling ${URL}/projects"
while [ $SECONDS -lt $DEADLINE ]; do
  if curl -sf "${URL}/projects" >/dev/null 2>&1; then
    echo "[wait_for_api] server is up (${SECONDS}s)"
    exit 0
  fi
  sleep 3
done
echo "[wait_for_api] timed out after ${WAIT_FOR_API_TIMEOUT:-180}s" >&2
exit 1
