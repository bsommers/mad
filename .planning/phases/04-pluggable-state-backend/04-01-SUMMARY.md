---
phase: 04-pluggable-state-backend
plan: 01
subsystem: backend
tags: [backend, mads, protocol, subprocess, projections, stdlib]

requires:
  - phase: 01-foundation
    provides: "mad.store, mad.route, mad.cli"
  - phase: 02-context-skills
    provides: "mad.context, mad.handoff"
  - phase: 03-telemetry-limits
    provides: "mad.telemetry"
provides:
  - "5-method StateBackend protocol and get_backend selector (mad.backend)"
  - "FilesBackend wrapper preserving byte-identical default file behavior (mad.files_backend)"
  - "Subprocess JSON-over-CLI mads client speaking mads.contract/1 (mad.mads_client)"
  - "MadsBackend with STORE_BUSY retry, projections, and graceful fallback to files (mad.mads_backend)"
affects: []

tech-stack:
  added: []
  patterns:
    - "5-method StateBackend Protocol separating CLI orchestration from storage substrate"
    - "Subprocess JSON-over-stdin client (never shell=True) mapping closed error set and STORE_BUSY retry"
    - "Once-per-process graceful degradation to FilesBackend with a single note entry when mads is absent"

key-files:
  created:
    - mad/backend.py
    - mad/files_backend.py
    - mad/mads_client.py
    - mad/mads_backend.py
    - docs/user-guide/state-backends.md
    - tests/test_backend_files.py
    - tests/backend_contract.py
    - tests/test_backend_contract.py
    - tests/stubs/mads_stub.py
    - tests/test_mads_client.py
    - tests/test_mads_integration.py
  modified:
    - config/routing.json
    - mad/telemetry.py
    - mad/cli.py
    - AGENTS.md

key-decisions:
  - "Added state_backend: 'files' to config/routing.json, overridden by MAD_STATE_BACKEND (D-04)"
  - "Kept .agent_telemetry.json on files in both modes and mirrored into mads via put_artifact(kind='telemetry', key='mad/agent_telemetry') in mads mode (D-05)"
  - "Amended AGENTS.md so SQLite may exist only inside the separate mads binary reached via subprocess JSON-over-CLI (D-01)"

patterns-established:
  - "Shared backend contract suite (tests/backend_contract.py) parametrized across FilesBackend and MadsBackend"
  - "Real-binary integration suite (tests/test_mads_integration.py) skipped unless MADS_BIN points to a real mads binary"

requirements-completed: [BACK-01, BACK-02, BACK-03, BACK-04, BACK-05]

coverage:
  - id: D1
    description: "StateBackend protocol fronts append_log, write_handoff, fetch_context, and telemetry read/write; FilesBackend reproduces output byte-for-byte"
    requirement: BACK-01
    verification:
      - kind: unit
        ref: "tests/test_backend_files.py"
        status: pass
      - kind: contract
        ref: "tests/test_backend_contract.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "MAD_STATE_BACKEND (files default | mads) selects backend; unknown value exits 2"
    requirement: BACK-02
    verification:
      - kind: unit
        ref: "tests/test_backend_files.py#test_unknown_mad_state_backend_exits_2"
        status: pass
    human_judgment: false
  - id: D3
    description: "mad/mads_client.py (stdlib subprocess + json, no shell=True) calls mads CLI and maps closed error set; STORE_BUSY retries up to 3 times"
    requirement: BACK-03
    verification:
      - kind: unit
        ref: "tests/test_mads_client.py"
        status: pass
      - kind: unit
        ref: "tests/test_backend_contract.py#test_mads_backend_retries_store_busy_twice_then_succeeds"
        status: pass
    human_judgment: false
  - id: D4
    description: "If mads is selected but absent, mad falls back to files and logs one note entry; routing decisions are identical in both modes"
    requirement: BACK-04
    verification:
      - kind: unit
        ref: "tests/test_backend_contract.py#test_mads_absent_falls_back_to_files_and_logs_one_note_per_process"
        status: pass
      - kind: unit
        ref: "tests/test_backend_contract.py#test_route_output_identical_in_both_modes"
        status: pass
    human_judgment: false
  - id: D5
    description: "AGENTS.md amended; exported .opengsd_handoff.md equals files-backend output modulo updated: date"
    requirement: BACK-05
    verification:
      - kind: integration
        ref: "tests/test_mads_integration.py#test_real_mads_end_to_end_and_handoff_parity"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-10-30
status: complete
---

# Phase 4 Plan 01: Pluggable State Backend Summary

**5-method `StateBackend` protocol (`mad/backend.py`), byte-identical `FilesBackend` (`mad/files_backend.py`), stdlib `subprocess` client (`mad/mads_client.py`, 138 lines), `MadsBackend` with `STORE_BUSY` retry and once-per-process fallback (`mad/mads_backend.py`), shared contract suite, real-binary integration test, and `AGENTS.md` amendment**

## Performance

- **Duration:** 12 min
- **Started:** 2026-10-30T20:58:00-04:00
- **Completed:** 2026-10-30T21:10:00-04:00
- **Tasks:** 5
- **Files modified:** 15

## Accomplishments
- Implemented `StateBackend` protocol and `get_backend` in `mad/backend.py`, plus `FilesBackend` in `mad/files_backend.py`, routing `mad/cli.py` through `get_backend` while keeping all pre-existing `pytest` and `bats` tests unchanged.
- Created `mad/mads_client.py` (138 lines, stdlib `subprocess` + `json`, never `shell=True`) speaking `mads.contract/1` (`tool <verb>`, operator `<verb>`, `init`, and `export`) and mapping the closed 8-error-code set to `MadsError(code, message, retryable, detail)`.
- Implemented `MadsBackend` in `mad/mads_backend.py` with up to 3 jittered retries on `STORE_BUSY`, `NOT_FOUND` empty-context degradation, file projections for `.global_dev_log.md` and `.opengsd_handoff.md`, telemetry mirroring (`D-05`), and once-per-process fallback to `FilesBackend` when `mads` is absent.
- Verified with real `mads` binary (`MADS_BIN=/home/bill/src/meso/mads/target/release/mads pytest -q tests/test_mads_integration.py` → `1 passed in 0.09s`), confirming `.opengsd_handoff.md` exported from `mads` equals `FilesBackend` output modulo `updated:` date and passes `validate_handoff`.
- Amended `AGENTS.md` and added `docs/user-guide/state-backends.md`.

## Verification Output
- `pytest -q`: `68 passed, 1 skipped`
- `MADS_BIN=/home/bill/src/meso/mads/target/release/mads pytest -q`: `69 passed`
- `bats tests/cli.bats`: `15/15 passed`
- `MAD_STATE_BACKEND=mads MADS_BIN=$PWD/tests/stubs/mads_stub.py bats tests/cli.bats`: `15/15 passed`
- `shellcheck bin/mad scripts/*.sh tests/stub_cli.sh`: `0 warnings`

## Self-Check: PASSED

---
*Phase: 04-pluggable-state-backend*
*Completed: 2026-10-30*
