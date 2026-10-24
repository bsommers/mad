---
phase: 02-context-skills
plan: 01
subsystem: cli
tags: [context-fetcher, handoff, skills, okf, bash, stdlib]

requires:
  - phase: 01-foundation
    provides: "mad.store (init_store, append_log, find_root), mad.route (load_config), mad.launch (exec_command), mad.cli"
provides:
  - "Selective context fetcher and INDEX.md reindexer (mad.context: parse_frontmatter, fetch_context, reindex_context)"
  - "State handoff artifact writer, validator, and launcher (mad.handoff: write_handoff, validate_handoff, build_handoff_command)"
  - "CLI subcommands: mad fetch, mad handoff (--write & launch), mad check (Phase 2 stub)"
  - "Shared skills: skills/context_orchestrator/SKILL.md, skills/context_fetcher/SKILL.md, skills/route_task/SKILL.md"
  - "Symlink installer: scripts/install-skills.sh"
affects: [03-telemetry-limits]

tech-stack:
  added: []
  patterns:
    - "Keyword/title token scoring (2 pts keyword, 1 pt title) with (-score, filename) tie-breaking and skip-and-continue byte budget"
    - "Atomic handoff file write (.opengsd_handoff.md) paired with .global_dev_log.md handoff entry"
    - "Env-overridable skill target directories (MAD_CLAUDE_SKILLS_DIR, MAD_AGY_SKILLS_DIR) for safe testing"

key-files:
  created:
    - mad/context.py
    - mad/handoff.py
    - skills/context_orchestrator/SKILL.md
    - skills/context_fetcher/SKILL.md
    - skills/route_task/SKILL.md
    - scripts/install-skills.sh
    - tests/test_context.py
    - tests/test_handoff.py
  modified:
    - config/routing.json
    - mad/cli.py
    - tests/cli.bats

key-decisions:
  - "Provided mad handoff --write CLI helper so context_orchestrator handoffs are atomic and deterministically testable (D-09)"
  - "Added Phase 2 mad check stub supporting MAD_FORCE_HANDOFF=1 (exit 10) for route_task testing before Phase 3 telemetry (D-10)"
  - "Used skip-and-continue byte budget enforcement and (-score, filename) tie-breaking in mad fetch (D-01, D-02)"

patterns-established:
  - "validate_handoff enforces OKF frontmatter and all four spec §6 headings in order before launching agy"
  - "scripts/install-skills.sh replaces symlinks via ln -sfn and refuses to overwrite real directories"

requirements-completed: [CTX-01, CTX-02, CTX-03, CTX-04, CTX-05]

coverage:
  - id: D1
    description: "context_orchestrator skill and mad handoff --write produce .opengsd_handoff.md with the four design §6 sections and append a handoff log entry"
    requirement: CTX-01
    verification:
      - kind: unit
        ref: "tests/test_handoff.py#test_write_and_validate_handoff"
        status: pass
      - kind: integration
        ref: "tests/cli.bats#handoff --write creates .opengsd_handoff.md and handoff launches agy stub"
        status: pass
    human_judgment: false
  - id: D2
    description: "mad fetch scores .active_context/*.md within fetch_budget_bytes and --reindex regenerates INDEX.md; wrapped by context_fetcher skill"
    requirement: CTX-02
    verification:
      - kind: unit
        ref: "tests/test_context.py#test_fetch_matches_only_docker_fixture"
        status: pass
      - kind: unit
        ref: "tests/test_context.py#test_fetch_budget_skips_oversized_and_continues"
        status: pass
      - kind: unit
        ref: "tests/test_context.py#test_reindex_empty_and_populated"
        status: pass
      - kind: integration
        ref: "tests/cli.bats#fetch prints only matching docker file and --reindex updates INDEX.md"
        status: pass
    human_judgment: false
  - id: D3
    description: "route_task skill and mad check gate (ok / exit 0 vs handoff / exit 10)"
    requirement: CTX-03
    verification:
      - kind: integration
        ref: "tests/cli.bats#check stub exits 0 by default and 10 when MAD_FORCE_HANDOFF=1"
        status: pass
    human_judgment: false
  - id: D4
    description: "mad handoff validates .opengsd_handoff.md, passes content to agy via -i, and exits 1 when missing or malformed"
    requirement: CTX-04
    verification:
      - kind: unit
        ref: "tests/test_handoff.py#test_validate_handoff_missing_or_empty"
        status: pass
      - kind: unit
        ref: "tests/test_handoff.py#test_validate_handoff_malformed_sections"
        status: pass
      - kind: integration
        ref: "tests/cli.bats#handoff --write creates .opengsd_handoff.md and handoff launches agy stub"
        status: pass
    human_judgment: false
  - id: D5
    description: "scripts/install-skills.sh symlinks skills into Claude and agy directories and supports --dry-run"
    requirement: CTX-05
    verification:
      - kind: integration
        ref: "tests/cli.bats#install-skills.sh --dry-run lists symlinks and touches nothing"
        status: pass
      - kind: integration
        ref: "tests/cli.bats#install-skills.sh creates symlinks and refuses real directory collision"
        status: pass
    human_judgment: false

duration: 5min
completed: 2026-10-23
status: complete
---

# Phase 2 Plan 01: Context Skills Summary

**Selective OKF context fetcher (`mad fetch`), validated state handoff writer/launcher (`mad handoff`), shared `context_orchestrator` / `context_fetcher` / `route_task` skills, and dual-CLI symlink installer (`scripts/install-skills.sh`)**

## Performance

- **Duration:** 5 min
- **Started:** 2026-10-23T22:09:00Z
- **Completed:** 2026-10-23T22:14:00Z
- **Tasks:** 5
- **Files modified:** 11

## Accomplishments
- Implemented `mad.context` (`parse_frontmatter`, `fetch_context`, `reindex_context`) with `2`-pt keyword / `1`-pt title scoring, `(-score, filename)` tie-breaking, skip-and-continue byte budget enforcement (`fetch_budget_bytes`: 24,000), and deterministic `.active_context/INDEX.md` generation.
- Implemented `mad.handoff` (`write_handoff`, `validate_handoff`, `build_handoff_command`) producing and validating OKF `.opengsd_handoff.md` files with the four required spec §6 headings and logging `handoff` entries to `.global_dev_log.md`.
- Extended `mad.cli` with `mad fetch`, `mad handoff` (`--write` and launch modes), and the Phase 2 `mad check` stub (`MAD_FORCE_HANDOFF=1` → exit `10`).
- Authored `skills/context_orchestrator/SKILL.md`, `skills/context_fetcher/SKILL.md`, `skills/route_task/SKILL.md`, and `scripts/install-skills.sh` with `--dry-run` and real-directory collision protection.
- Verified all gates: `pytest -q` (`33 passed`), `bats tests/cli.bats` (`13/13 passed`), and `shellcheck bin/mad tests/stub_cli.sh scripts/install-skills.sh` (`0 warnings`).

## Task Commits

Each task was committed atomically:

1. **Task 1: Context fetcher and indexer (`mad/context.py`)** - `9c37250` (feat)
2. **Task 2: Handoff writer, validator, and launcher (`mad/handoff.py`)** - `c88f787` (feat)
3. **Task 3: CLI wiring for `fetch`, `handoff`, and `check`** - `400713e` (feat)
4. **Task 4: Shared skills and `scripts/install-skills.sh`** - `b86d277` (feat)

## Files Created/Modified
- `config/routing.json` - Added `"fetch_budget_bytes": 24000`
- `mad/context.py` - OKF frontmatter parser, keyword/title scorer, and `INDEX.md` reindexer
- `mad/handoff.py` - `.opengsd_handoff.md` writer, validator, and `agy -i` argv builder
- `mad/cli.py` - Added `fetch`, `handoff`, and `check` subcommands
- `skills/context_orchestrator/SKILL.md` - Handoff orchestration instructions
- `skills/context_fetcher/SKILL.md` - Selective context loading instructions
- `skills/route_task/SKILL.md` - Pre-task capacity check and subagent model-tier policy
- `scripts/install-skills.sh` - Symlink installer with `--dry-run` and env-var target overrides
- `tests/test_context.py` - 6 unit tests for `mad.context`
- `tests/test_handoff.py` - 4 unit tests for `mad.handoff`
- `tests/cli.bats` - 5 new CLI and installer integration tests (13 total)

## Decisions Made
- Followed all locked decisions `D-01` through `D-15` from `02-CONTEXT.md`.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - run `scripts/install-skills.sh` manually only if you want symlinks created in `~/.claude/skills` and `~/.gemini/config/skills`.

## Next Phase Readiness
- Phase 2 is complete and verified.
- Ready to discuss/plan **Phase 3: Telemetry & limits** (`TEL-01..04`: `.agent_telemetry.json`, Claude JSONL transcript window counting, full `mad check` implementation, and `.claude/settings.json` `UserPromptSubmit` hook) upon user go-ahead.

## Self-Check: PASSED

---
*Phase: 02-context-skills*
*Completed: 2026-10-23*
