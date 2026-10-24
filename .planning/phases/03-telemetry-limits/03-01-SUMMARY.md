---
phase: 03-telemetry-limits
plan: 01
subsystem: telemetry
tags: [telemetry, jsonl, atomic-write, claude-hooks, bash, stdlib]

requires:
  - phase: 01-foundation
    provides: "mad.store (find_root), mad.route (load_config), mad.cli"
  - phase: 02-context-skills
    provides: "mad handoff --write, skills/context_orchestrator/SKILL.md, skills/route_task/SKILL.md"
provides:
  - "Claude JSONL window prompt counter (mad.telemetry.count_claude_messages)"
  - "Atomic .agent_telemetry.json store (mad.telemetry.read_telemetry, write_telemetry_atomic)"
  - "Usage limit evaluator (mad.telemetry.check_limits) wired to mad check"
  - "Project-level Claude Code UserPromptSubmit hook (.claude/settings.json + scripts/claude-check-hook.sh)"
affects: []

tech-stack:
  added: []
  patterns:
    - "Atomic JSON persistence via tempfile.mkstemp in target directory + fsync + os.replace"
    - "Transcript prompt counting filtering out isMeta: true, tool_result-only messages, and out-of-window entries"
    - "Claude Code UserPromptSubmit hook emitting hookSpecificOutput.additionalContext on mad check exit 10"

key-files:
  created:
    - mad/telemetry.py
    - scripts/claude-check-hook.sh
    - .claude/settings.json
    - tests/test_telemetry.py
  modified:
    - config/routing.json
    - mad/cli.py
    - tests/cli.bats
    - AGENTS.md

key-decisions:
  - "Counted type=='user' JSONL entries within window_hours in MAD_CLAUDE_PROJECTS_DIR (default ~/.claude/projects), excluding isMeta:true and tool_result-only messages (D-04, D-05)"
  - "Preserved agy.running and agy.last_rate_limit in .agent_telemetry.json with MAD_AGY_RUNNING env override and --record-rate-limit CLI flag so tests never scan host processes (D-07)"
  - "Wired .claude/settings.json UserPromptSubmit hook to scripts/claude-check-hook.sh emitting hookSpecificOutput additionalContext on exit 10 (D-10, D-11)"

patterns-established:
  - "write_telemetry_atomic unlinks temporary file on any exception before os.replace completes"
  - "setup() in tests/cli.bats exports MAD_CLAUDE_PROJECTS_DIR to an isolated temp directory"

requirements-completed: [TEL-01, TEL-02, TEL-03, TEL-04]

coverage:
  - id: D1
    description: ".agent_telemetry.json follows the design §7 schema; writes are atomic (temp file + rename)"
    requirement: TEL-01
    verification:
      - kind: unit
        ref: "tests/test_telemetry.py#test_atomic_write_preserves_valid_json_on_interrupted_replace"
        status: pass
      - kind: integration
        ref: "tests/cli.bats#mad check counts 35 prompts as ok and 36 as handoff, writing .agent_telemetry.json"
        status: pass
    human_judgment: false
  - id: D2
    description: "Claude window usage is estimated from user-prompt entries in ~/.claude/projects/*/*.jsonl within window_hours; transcript root is overridable for tests"
    requirement: TEL-02
    verification:
      - kind: unit
        ref: "tests/test_telemetry.py#test_count_claude_messages_filters_window_meta_and_tool_results"
        status: pass
    human_judgment: false
  - id: D3
    description: "mad check exits 10 (handoff) at ceil(budget * ratio) claude messages, or when agy is at max_concurrent or was rate-limited within 15 min; otherwise exits 0 (ok)"
    requirement: TEL-03
    verification:
      - kind: unit
        ref: "tests/test_telemetry.py#test_threshold_35_is_ok_and_36_triggers_handoff"
        status: pass
      - kind: unit
        ref: "tests/test_telemetry.py#test_agy_concurrency_and_rate_limit_cooldown"
        status: pass
      - kind: integration
        ref: "tests/cli.bats#mad check counts 35 prompts as ok and 36 as handoff, writing .agent_telemetry.json"
        status: pass
    human_judgment: false
  - id: D4
    description: "Project .claude/settings.json UserPromptSubmit hook runs mad check and, on exit 10, injects the context_orchestrator instruction"
    requirement: TEL-04
    verification:
      - kind: integration
        ref: "tests/cli.bats#mad check --record-rate-limit triggers handoff and UserPromptSubmit hook injects instruction"
        status: pass
    human_judgment: false

duration: 6min
completed: 2026-10-23
status: complete
---

# Phase 3 Plan 01: Telemetry & Limits Summary

**Atomic `.agent_telemetry.json` store, Claude JSONL 5-hour window prompt estimator, full `mad check` limit gate (36-message threshold, `agy` concurrency, and 15-minute rate-limit cooldown), and project-level Claude Code `UserPromptSubmit` hook (`.claude/settings.json` + `scripts/claude-check-hook.sh`)**

## Performance

- **Duration:** 6 min
- **Started:** 2026-10-24T01:17:00Z
- **Completed:** 2026-10-24T01:23:00Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments
- Implemented `mad.telemetry` (`count_claude_messages`, `read_telemetry`, `write_telemetry_atomic`, `check_limits`) using stdlib only, atomic `tempfile.mkstemp` + `os.fsync` + `os.replace`, and filtering out `isMeta: true`, `tool_result`-only turns, and out-of-window entries.
- Wired `mad check [--transcripts-dir PATH] [--record-rate-limit]` in `mad.cli` to update `.agent_telemetry.json` and exit `10` (`handoff`) at `ceil(45 * 0.8) = 36` Claude messages, `agy.running >= 2`, `agy.last_rate_limit` within 15 minutes, or `MAD_FORCE_HANDOFF=1`.
- Added `.claude/settings.json` and `scripts/claude-check-hook.sh` to run `bin/mad check` on `UserPromptSubmit` and inject the `context_orchestrator` handoff instruction when exit code is `10`.
- Verified all gates: `pytest -q` (`37 passed`), `bats tests/cli.bats` (`15/15 passed`), and `shellcheck bin/mad tests/stub_cli.sh scripts/install-skills.sh scripts/claude-check-hook.sh` (`0 warnings`).

## Task Commits

Each task was committed atomically:

1. **Task 1: Telemetry store, transcript counter, and limit evaluator (`mad/telemetry.py`)** - `54a5a96` (feat)
2. **Task 2: Wire `mad check` in `mad/cli.py` and Claude Code `UserPromptSubmit` hook** - `c974736` (feat)

## Files Created/Modified
- `config/routing.json` - Added `"telemetry"` defaults (`window_hours`: 5, `window_message_budget`: 45, `handoff_ratio`: 0.8, `agy_max_concurrent`: 2, `agy_rate_limit_cooldown_minutes`: 15)
- `mad/telemetry.py` - Transcript counter, atomic JSON persistence, and limit evaluation
- `mad/cli.py` - Replaced Phase 2 `check` stub with full `check_limits` integration
- `scripts/claude-check-hook.sh` - `UserPromptSubmit` hook script calling `bin/mad check`
- `.claude/settings.json` - Project-level Claude Code hook configuration
- `tests/test_telemetry.py` - 4 unit tests covering transcript filtering, 35 vs 36 threshold, `agy` limits, and atomic write crash resilience
- `tests/cli.bats` - 2 new integration tests covering `mad check` 35/36 threshold, `--record-rate-limit`, and `scripts/claude-check-hook.sh` (15 total)
- `AGENTS.md` - Updated commands and architecture map for Milestone v1.0 completion

## Decisions Made
- Followed all locked decisions `D-01` through `D-11` from `03-CONTEXT.md`.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - `.claude/settings.json` is active automatically when running Claude Code in this repository.

## Next Phase Readiness
- Phase 3 and Milestone **v1.0 Orchestration core** (`STORE-01..02`, `ROUTE-01..03`, `CTX-01..05`, `TEL-01..04`) are 100% complete and verified.

## Self-Check: PASSED

---
*Phase: 03-telemetry-limits*
*Completed: 2026-10-23*
