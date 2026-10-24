---
name: context_orchestrator
description: Use when handing off an active task between Claude Code (claude) and Antigravity (agy), when a usage limit is approaching (mad check returns handoff), or when pausing mid-task to preserve exact state in .opengsd_handoff.md and .global_dev_log.md.
---

# context_orchestrator

Supersedes `compacting-context-safely` and `handing-off-sessions` for the `mad` multi-agent workflow without modifying those plugin skills.

## Steps

1. **Compute the session delta** since the last `handoff` entry in `.global_dev_log.md`:
   ```bash
   git status -s
   git diff --stat
   tail -n 40 .global_dev_log.md
   ```
   Identify:
   - The single unresolved problem blocking completion.
   - The ordered next exact steps for the receiving CLI.
   - Any relevant `.active_context/<topic>.md` files to load.
   - The exact verification commands (`pytest -q`, `bats tests/cli.bats`, etc.).

2. **Write `.opengsd_handoff.md` and append the `handoff` log entry atomically** via `bin/mad handoff --write`:
   ```bash
   bin/mad handoff --write \
     --agent "<claude|agy>" \
     --problem "<unresolved problem>" \
     --step "<first next step>" \
     --step "<second next step>" \
     --context ".active_context/<topic>.md" \
     --verify "pytest -q && bats tests/cli.bats && shellcheck bin/mad"
   ```
   This produces `.opengsd_handoff.md` (OKF frontmatter + the four required sections `## Unresolved problem`, `## Next exact steps`, `## Context files to load`, `## Verify with`) and appends a `handoff` entry to `.global_dev_log.md`.

3. **Stop immediately** and print the handoff command for the user:
   ```bash
   bin/mad handoff
   ```
