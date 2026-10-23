---
phase: 01-foundation
plan: 01
subsystem: cli
tags: [routing, markdown-store, okf, argparse, bash, stdlib]

requires: []
provides:
  - "Pure routing classifier (mad.route: load_config, Decision, classify)"
  - "Append-only OKF Markdown dev log and active context store (mad.store)"
  - "Command builder and exec launcher for claude and agy (mad.launch)"
  - "CLI front end and bash entry point (mad.cli, bin/mad)"
affects: [02-context-skills, 03-telemetry-limits]

tech-stack:
  added: [pytest, bats, shellcheck]
  patterns:
    - "Pure deterministic routing via config/routing.json word-boundary regexes"
    - "Append-only OKF Markdown log with flattened single-line field values"
    - "Stub binary injection via MAD_CLAUDE_BIN and MAD_AGY_BIN environment variables"

key-files:
  created:
    - pyproject.toml
    - config/routing.json
    - mad/__init__.py
    - mad/route.py
    - mad/store.py
    - mad/launch.py
    - mad/cli.py
    - mad/__main__.py
    - bin/mad
    - tests/test_route.py
    - tests/test_store.py
    - tests/test_launch.py
    - tests/cli.bats
    - tests/stub_cli.sh
    - .global_dev_log.md
    - .active_context/INDEX.md
  modified: []

key-decisions:
  - "Renamed project, package, and CLI from maiors to mad (user request)"
  - "Added 12th classify test case covering agy --model override row (spec §4.2)"

patterns-established:
  - "Word-boundary phrase matching: (?<!\\w) + re.escape(phrase) + (?!\\w)"
  - "bin/mad resolves symlinks via readlink -f before setting PYTHONPATH"

requirements-completed: [STORE-01, STORE-02, ROUTE-01, ROUTE-02, ROUTE-03]

coverage:
  - id: D1
    description: "Idempotent OKF store initialization (mad init)"
    requirement: STORE-01
    verification:
      - kind: unit
        ref: "tests/test_store.py#test_init_creates_then_is_idempotent"
        status: pass
      - kind: unit
        ref: "tests/test_store.py#test_init_never_overwrites"
        status: pass
      - kind: integration
        ref: "tests/cli.bats#init twice"
        status: pass
    human_judgment: false
  - id: D2
    description: "Append-only OKF dev log with newline flattening (mad log)"
    requirement: STORE-02
    verification:
      - kind: unit
        ref: "tests/test_store.py#test_append_preserves_prior_bytes"
        status: pass
      - kind: unit
        ref: "tests/test_store.py#test_multiline_values_flattened"
        status: pass
      - kind: integration
        ref: "tests/cli.bats#log with bad --field"
        status: pass
    human_judgment: false
  - id: D3
    description: "Agent and model routing classifier (mad route)"
    requirement: ROUTE-01
    verification:
      - kind: unit
        ref: "tests/test_route.py#test_classify"
        status: pass
      - kind: integration
        ref: "tests/cli.bats#route prints claude/sonnet for debug"
        status: pass
    human_judgment: false
  - id: D4
    description: "Model tier selection and override support"
    requirement: ROUTE-02
    verification:
      - kind: unit
        ref: "tests/test_route.py#test_classify"
        status: pass
    human_judgment: false
  - id: D5
    description: "Command builder, dry-run, transition logging, and stub exec (mad run)"
    requirement: ROUTE-03
    verification:
      - kind: unit
        ref: "tests/test_launch.py#test_claude_argv"
        status: pass
      - kind: unit
        ref: "tests/test_launch.py#test_agy_argv_uses_dash_i"
        status: pass
      - kind: integration
        ref: "tests/cli.bats#run --dry-run prints argv and writes nothing"
        status: pass
      - kind: integration
        ref: "tests/cli.bats#run execs stub and logs transition"
        status: pass
    human_judgment: false

duration: 6min
completed: 2026-10-23
status: complete
---

# Phase 1 Plan 01: Foundation Summary

**Stdlib-only `bin/mad` router CLI (`init`, `route`, `run`, `log`), word-boundary keyword/file-count classifier, and append-only OKF Markdown state store**

## Performance

- **Duration:** 6 min
- **Started:** 2026-10-23T20:24:00Z
- **Completed:** 2026-10-23T20:30:00Z
- **Tasks:** 5
- **Files modified:** 16

## Accomplishments
- Implemented `mad.route` with word-boundary regex classification against `config/routing.json` for `claude` (`haiku`/`sonnet`/`opus`) and `agy` (`gemini-3.8-flash-medium`/`gemini-4-argon-high`).
- Implemented `mad.store` for idempotent `.active_context/INDEX.md` and append-only `.global_dev_log.md` management with single-line value flattening.
- Implemented `mad.launch` and `mad.cli` / `bin/mad` supporting `init`, `route`, `run` (with `--dry-run`), and `log`, plus symlink-safe invocation and `--` dashed prompt handling.
- Passed all verification gates: `pytest -q` (23 passed), `bats tests/cli.bats` (8 passed), and `shellcheck bin/mad tests/stub_cli.sh` (0 warnings).

## Task Commits

Each task was committed atomically:

1. **Task 1: Routing config and classify** - `13648dc` (feat), renamed to `mad` in `b5c2f01` (chore)
2. **Task 2: OKF store (`init_store`, `append_log`, `find_root`)** - `4244e3f` (feat)
3. **Task 3: Command builder (`build_command`, `exec_command`)** - `6a365a9` (feat)
4. **Task 4: CLI front end and `bin/mad`** - `c4dc130` (feat)

## Files Created/Modified
- `pyproject.toml` - pytest configuration (`pythonpath = ["."]`, `testpaths = ["tests"]`)
- `config/routing.json` - keyword lists, file threshold (5), and model IDs
- `mad/route.py` - `load_config`, `Decision`, and `classify`
- `mad/store.py` - `find_root`, `init_store`, and `append_log`
- `mad/launch.py` - `build_command` and `exec_command`
- `mad/cli.py` - argparse CLI for `init`, `route`, `run`, `log`
- `mad/__main__.py` - module entry point
- `bin/mad` - symlink-safe bash entry point
- `tests/test_route.py` - 13 unit tests for routing and JSON serialization
- `tests/test_store.py` - 7 unit tests for store idempotence and append-only invariants
- `tests/test_launch.py` - 3 unit tests for `claude`/`agy` argv construction
- `tests/cli.bats` & `tests/stub_cli.sh` - 8 integration tests for `bin/mad`

## Decisions Made
- Renamed repository, package, CLI binary, and environment variables from `maiors`/`MAIORS_*` to `mad`/`MAD_*` per user instruction.
- Added a 12th parametrized case in `tests/test_route.py` so every row of spec §4.2 (including `agy` `--model` override) is covered.

## Deviations from Plan

None - plan executed as written (with the user-requested rename from `maiors` to `mad` and 1 extra test case for spec §4.2 completeness).

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 1 foundation is complete and dogfooded (`.global_dev_log.md` and `.active_context/INDEX.md` initialized).
- Ready to plan Phase 2 (Context skills: `context_orchestrator`, `context_fetcher`, `route_task`, `mad handoff`) upon user go-ahead.

## Self-Check: PASSED

---
*Phase: 01-foundation*
*Completed: 2026-10-23*
