---
phase: 05-worker-leases-and-handoff-claims
plan: 01
subsystem: coordination
tags: [coordination, leases, handoff, mads, protocol, cli]

requires:
  - phase: 04-pluggable-state-backend
    provides: "StateBackend, FilesBackend, MadsBackend, mads_client"
provides:
  - "3-member CoordinationBackend protocol (take_handoff, claim_slot, release_slot) in mad.backend"
  - "Atomic handoff claim & consumption (mad handoff --take [--print] [--dry-run]) via mads tool take_handoff"
  - "Worker concurrency slot leasing (mad claim / mad release) on agy:slot:1..agy_max_concurrent via mads tool claim_task / release_task"
  - "Deterministic no-op coordination parity in FilesBackend"
affects: []

tech-stack:
  added: []
  patterns:
    - "3-member CoordinationBackend Protocol kept separate from 5-member StateBackend (designing-plugin-contracts Rule 1)"
    - "Slot-probing loop across agy:slot:1..max_concurrent mapping CONFLICT to next slot and all-busy to exit 1"
    - "Single-consumption handoff take exporting Markdown atomically before launching agy"

key-files:
  created:
    - .planning/phases/05-worker-leases-and-handoff-claims/05-CONTEXT.md
    - .planning/phases/05-worker-leases-and-handoff-claims/05-01-PLAN.md
    - .planning/phases/05-worker-leases-and-handoff-claims/05-01-SUMMARY.md
    - docs/superpowers/plans/2026-11-07-phase-5-worker-leases-and-handoff-claims.md
  modified:
    - mad/backend.py
    - mad/files_backend.py
    - mad/mads_backend.py
    - mad/cli.py
    - tests/stubs/mads_stub.py
    - tests/test_mads_client.py
    - tests/backend_contract.py
    - tests/test_backend_files.py
    - tests/test_backend_contract.py
    - tests/test_mads_integration.py
    - tests/cli.bats
    - AGENTS.md
    - README.md
    - docs/user-guide/README.md
    - docs/user-guide/state-backends.md

key-decisions:
  - "Split CoordinationBackend (3 members: take_handoff, claim_slot, release_slot) from StateBackend (5 members) per designing-plugin-contracts Rule 1 (D-01)"
  - "Mapped mads NOT_FOUND on take_handoff to ValueError('no open handoff') and exit code 1 (D-02)"
  - "Probed agy:slot:1..agy_max_concurrent via mads tool claim_task, returning lease JSON on first grant or exiting 1 when all slots conflict (D-03)"

patterns-established:
  - "Parallel subagent execution across disjoint file scopes (Stub/Client, Backend Protocol, CLI/Docs)"

requirements-completed: [COORD-01, COORD-02, COORD-03]

coverage:
  - id: C1
    description: "mad handoff --take atomically claims and consumes oldest open handoff via mads tool take_handoff in mads mode and validates .opengsd_handoff.md in files mode"
    requirement: COORD-01
    verification:
      - kind: unit
        ref: "tests/test_backend_contract.py#test_mads_backend_take_handoff_single_consumption"
        status: pass
      - kind: integration
        ref: "tests/test_mads_integration.py#test_real_mads_end_to_end_and_handoff_parity"
        status: pass
    human_judgment: false
  - id: C2
    description: "mad claim and mad release acquire/release agy:slot:1..agy_max_concurrent via mads tool claim_task / release_task in mads mode"
    requirement: COORD-02
    verification:
      - kind: unit
        ref: "tests/test_backend_contract.py#test_mads_backend_slot_claims_respect_max_concurrent_and_fencing"
        status: pass
      - kind: integration
        ref: "tests/test_mads_integration.py#test_real_mads_end_to_end_and_handoff_parity"
        status: pass
    human_judgment: false
  - id: C3
    description: "All existing files mode behavior and tests remain 100% unchanged"
    requirement: COORD-03
    verification:
      - kind: unit
        ref: "tests/test_backend_files.py"
        status: pass
      - kind: system
        ref: "tests/cli.bats"
        status: pass
    human_judgment: false

duration: 8min
completed: 2026-11-07
status: complete
---

# Phase 5 Plan 01: Worker Leases & Atomic Handoff Claims Summary

**3-member `CoordinationBackend` protocol (`mad/backend.py`), atomic single-consumption `mad handoff --take` (`COORD-01`), bounded `agy:slot:1..N` worker leases via `mad claim` / `mad release` (`COORD-02`), and 100% `files`-mode backward compatibility (`COORD-03`) verified against both `mads_stub.py` and the real `mads` binary**

## Performance

- **Duration:** 8 min
- **Started:** 2026-11-07T16:04:10-05:00
- **Completed:** 2026-11-07T16:12:15-05:00
- **Tasks:** 3 (dispatched across 3 parallel `flash` subagents with disjoint file scopes)
- **Files modified:** 15

## Accomplishments
- Extended `tests/stubs/mads_stub.py` and `tests/test_mads_client.py` with stateful `take_handoff`, `claim_task`, and `release_task` support matching `mads.contract/1`.
- Added `CoordinationBackend` protocol (`take_handoff`, `claim_slot`, `release_slot`) in `mad/backend.py` while keeping `StateBackend` at 5 members, with full implementations on `FilesBackend` (`mad/files_backend.py`) and `MadsBackend` (`mad/mads_backend.py`).
- Wired `mad handoff --take [--print] [--dry-run]`, `mad claim [--agent agy] [--ttl 60]`, and `mad release --claim-id ID --token TOKEN [--outcome O]` in `mad/cli.py`.
- Verified end-to-end against both `tests/stubs/mads_stub.py` and the real `mads` binary (`/home/bill/src/meso/mads/target/release/mads`).

## Verification Output
- `pytest -q`: `79 passed, 1 skipped in 1.71s`
- `MADS_BIN=/home/bill/src/meso/mads/target/release/mads pytest -q`: `80 passed in 1.71s`
- `bats tests/cli.bats`: `17/17 passed`
- `shellcheck bin/mad scripts/*.sh tests/stub_cli.sh`: `0 warnings`

## Self-Check: PASSED

---
*Phase: 05-worker-leases-and-handoff-claims*
*Completed: 2026-11-07*
