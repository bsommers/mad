# Session Checkpoint — mad (`v1.2.0` shipped & pushed)

**Updated:** 2026-11-07
**Status:** COMPLETE — `v1.2.0` committed, tagged, and pushed to `origin`

## Goal (User's Words)
1. `push first. then should we checkpoint and compact before Phase 5 planning?` → Pushed `5712ed4..8e37af8 main -> main` to `origin`.
2. `yes` → Created Phase 5 context and implementation plans (`05-CONTEXT.md`, `docs/superpowers/plans/2026-11-07-phase-5-worker-leases-and-handoff-claims.md`, `05-01-PLAN.md`).
3. `using parallel subagents: do 1, but if we need to clear or compact first, let's do that` → Dispatched 3 parallel `flash` subagents across disjoint file scopes (Stub/Client, Backend Protocol, CLI/Docs) and completed Phase 5 (`COORD-01..03`).
4. `1. then checkpoint` → Committed Phase 5 (`v1.2`), tagged `v1.2.0`, pushed `main` and `v1.2.0` to `origin`, and refreshed this checkpoint.

## User Decisions Verbatim
- Phase 4 open decisions (`2026-10-30`):
  - `1 - config - take recommended default` (`"state_backend": "files"` in `config/routing.json`, `D-04`)
  - `2 - telemetry backend - recommended default` (keep `.agent_telemetry.json` on `files` in both modes and mirror into `mads` via `put_artifact(kind="telemetry", key="mad/agent_telemetry")`, `D-05`)
- Next steps order (`2026-11-05`):
  - `1, then 2, then 3, then 4`
- Phase 5 planning, execution & release (`2026-11-07`):
  - `push first. then should we checkpoint and compact before Phase 5 planning?`
  - `yes`
  - `using parallel subagents: do 1, but if we need to clear or compact first, let's do that`
  - `1. then checkpoint`

## Key Architectural Decisions (Phase 5)
- **D-01 (`StateBackend` + `CoordinationBackend` split):** Kept `StateBackend` at 5 members (`designing-plugin-contracts` Rule 1: 2–5 members) and introduced a 3-member `CoordinationBackend` protocol (`take_handoff`, `claim_slot`, `release_slot`) in `mad/backend.py`.
- **D-02 (`mad handoff --take`):** Calls `mads tool take_handoff` in `mads` mode, exports Markdown to `.opengsd_handoff.md` atomically, and launches `agy` (or prints with `--print` / `--dry-run`); a second taker gets exit `1` (`mad: no open handoff`). In `files` mode, reads and validates `.opengsd_handoff.md`.
- **D-03 (`mad claim` / `mad release`):** Probes `agy:slot:1..agy_max_concurrent` (2) via `mads tool claim_task` / `release_task` in `mads` mode; deterministic no-op JSON in `files` mode.

## Dead Ends
- None.

## Working-Tree & Process State
- **Branch:** `main` (pushed to `origin/main` with annotated tag `v1.2.0`)
- **Uncommitted files:** None (clean working tree)
- **Background processes / subagents:** None running
- **Verification Results:**
  - `pytest -q` → `79 passed, 1 skipped`
  - `MADS_BIN=/home/bill/src/meso/mads/target/release/mads pytest -q` → `80 passed`
  - `bats tests/cli.bats` → `17/17 passed`
  - `shellcheck bin/mad scripts/*.sh tests/stub_cli.sh` → `0 warnings`

## Authorizations
- Milestones `v1.0`, `v1.1`, and `v1.2` (Phases 1–5) are complete and pushed. `auto_advance` in `.planning/config.json` is `false`; confirm with user before starting any new milestone or cross-repo changes.

## Exact Next Command
In a fresh session (`/exit`, `Ctrl+D`, or New Chat), resume with:
```text
Read docs/CHECKPOINT.md and .planning/STATE.md, verify git status and pytest -q, and ask the user for the next milestone or cross-repo task (e.g., ~/src/meso/mads Phase 4 climah adapter).
```
