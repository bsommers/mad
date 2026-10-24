#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"

set +e
"$REPO_ROOT/bin/mad" check >/dev/null 2>&1
rc=$?
set -e

if [ "$rc" -eq 10 ]; then
  cat <<'EOF'
{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"[mad limit guard] Usage threshold reached (mad check exited 10: handoff). Immediately invoke the context_orchestrator skill (`bin/mad handoff --write --agent claude --problem ... --step ...`), stop execution, and tell the user to run `bin/mad handoff`."}}
EOF
fi

exit 0
