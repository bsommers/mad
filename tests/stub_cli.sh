#!/usr/bin/env bash
set -euo pipefail
: "${STUB_OUT:?STUB_OUT must be set}"
printf '%s\n' "$@" > "$STUB_OUT"
