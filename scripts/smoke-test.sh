#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
compose=(docker compose --project-name "rewritebody-smoke-$$")
cleanup() {
    local status=$?
    if ((status != 0)); then
        "${compose[@]}" logs >&2 || true
    fi
    "${compose[@]}" down --rmi local
}
trap cleanup EXIT

"${compose[@]}" up --build --detach --wait
endpoint=$("${compose[@]}" port traefik 80)
response=$(curl --fail --silent --show-error --retry 15 --retry-all-errors \
    --retry-delay 1 --max-time 5 --header 'Host: whoami.localhost' \
    --header 'Accept: text/plain' "http://$endpoint/")
grep -Fx 'Name: foo' <<< "$response"
