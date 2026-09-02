#!/bin/sh
set -eu

if [ "${REQUIRE_OIDC:-false}" = "true" ]; then
  missing=""
  for key in OIDC_ISSUER_URL OIDC_CLIENT_ID OIDC_CLIENT_SECRET; do
    eval "value=\${$key:-}"
    if [ -z "$value" ]; then
      missing="$missing $key"
    fi
  done
  if [ -n "$missing" ]; then
    echo "Refusing to start public TrueForge without required OIDC configuration:$missing" >&2
    echo "Set the secret-backed OIDC values in the hosting dashboard before exposing this service." >&2
    exit 1
  fi
fi

# Bootstrap runs as a sidecar process in the same container. It waits for the
# TrueForge HTTP API, then idempotently provisions the model provider,
# FaultLine MCP connector, and named harness-os agent. Secrets remain env-only.
if [ "${TRUEFORGE_BOOTSTRAP_ENABLED:-true}" = "true" ]; then
  node /usr/local/lib/harness-os/bootstrap.mjs &
fi

exec node node_modules/@truefoundry/trueforge/dist/main.js
