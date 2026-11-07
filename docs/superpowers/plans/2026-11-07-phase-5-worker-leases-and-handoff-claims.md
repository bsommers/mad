# Phase 5: Worker Leases & Atomic Handoff Claims Implementation Plan

> **Status: COMPLETE (2026-11-07).** Executed via TDD and parallel subagents against both the stateful stub (`tests/stubs/mads_stub.py`) and the real `mads` binary (`~/src/meso/mads/target/release/mads`).
>
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Prevent concurrent `agy` workers from exceeding `agy_max_concurrent` or double-consuming a handoff when `MAD_STATE_BACKEND=mads`, while remaining a safe, deterministic no-op in `files` mode (`COORD-01..03`).

**Motivation (measured):** `config/routing.json` sets `"agy_max_concurrent": 2`, and `~/src/meso/mads` already implements `take_handoff`, `claim_task`, and `release_task` (`mads.contract/1` §4.1, §4.4). Without `mad`-side wiring, two `agy` workers launched in `mads` mode both read `.opengsd_handoff.md` and race on the same handoff, and nothing enforces the 2-slot `agy` lease ceiling.

**Current → Proposed Architecture:**

```text
mad/cli.py (handoff --take | claim | release)
  └── get_backend(root, env) -> StateBackend (5 methods, unchanged) + CoordinationBackend (3 methods)
        ├── FilesBackend:
        │     ├── take_handoff(agent) -> validate_handoff(.opengsd_handoff.md)
        │     ├── claim_slot(agent, max_concurrent, ttl_s) -> {"slot": 1, "claim_id": "files-noop", ...}
        │     └── release_slot(claim_id, fencing_token, outcome) -> {"released": True}
        └── MadsBackend:
              ├── take_handoff(agent) -> mads tool take_handoff + export md -> .opengsd_handoff.md
              ├── claim_slot(agent, max_concurrent, ttl_s) -> mads tool claim_task on agy:slot:1..N
              └── release_slot(claim_id, fencing_token, outcome) -> mads tool release_task
```

**Tech Stack:** Bash, Python 3.14 standard library, pytest (tests only), bats, shellcheck. External, optional: the `mads` binary (`~/src/meso/mads/target/release/mads`).

**Spec:** `docs/superpowers/specs/2026-10-23-mad-design.md`, `~/src/meso/mads/SPEC.md` §4.1 & §4.4, `.planning/phases/05-worker-leases-and-handoff-claims/05-CONTEXT.md`.

## Global Constraints

- Runtime code imports only the Python standard library; no new dependencies.
- `StateBackend` remains a 5-member protocol (`designing-plugin-contracts` Rule 1: 2–5 members per protocol). Coordination primitives live on a separate 3-member `CoordinationBackend` protocol in `mad/backend.py`.
- Default behavior (`files`) is 100% unchanged: all 68 existing `pytest -q` tests and 16 `bats tests/cli.bats` tests pass without edits to existing assertions (`COORD-03`).
- Exit codes unchanged: `0` ok, `1` runtime error (`no open handoff`, `all agy slots busy`, `lease lost`), `2` usage error, `10` handoff needed.
- `route.classify` stays pure and untouched.

## Contracts

```python
# mad/backend.py
class CoordinationBackend(Protocol):     # 3 members (designing-plugin-contracts Rule 1)
    def take_handoff(self, agent: str = "agy") -> str: ...
    def claim_slot(
        self,
        agent: str = "agy",
        max_concurrent: int = 2,
        ttl_s: int = 60,
    ) -> dict[str, Any]: ...
    def release_slot(
        self,
        claim_id: str,
        fencing_token: int,
        outcome: str | None = None,
    ) -> dict[str, Any]: ...
```

### CLI Surface (`mad/cli.py`)

- `mad handoff --take [--agent agy] [--print] [--dry-run] [--model M] [--file PATH]`:
  - Mutually exclusive with `--write` (combining `--write` and `--take` exits `2`).
  - Calls `content = backend.take_handoff(agent=ns.agent or "agy")`.
  - If `--print` is passed: prints `content` (without trailing extra newline) and exits `0`.
  - If `--dry-run` is passed: prints `shlex.join(cmd)` and exits `0`.
  - Otherwise: checks `_require_tty()` (unless `MAD_NO_TTY_CHECK=1`) and execs `agy --model M -i <content>`.
  - When no open handoff exists in `mads` mode, `MadsBackend.take_handoff` catches `MadsError(code="NOT_FOUND")` and raises `ValueError("no open handoff")` → `cli.py` prints `mad: no open handoff` to stderr and exits `1`.
- `mad claim [--agent agy] [--ttl 60]`:
  - Reads `max_concurrent = int(cfg.get("telemetry", {}).get("agy_max_concurrent", 2))`.
  - Calls `backend.claim_slot(agent=ns.agent, max_concurrent=max_concurrent, ttl_s=ns.ttl)`.
  - Prints compact JSON `{"slot": N, "resource": "agy:slot:N", "claim_id": "...", "fencing_token": T, "expires_at": "..."}` to stdout and exits `0`.
  - If all slots `1..max_concurrent` conflict in `mads` mode, raises `ValueError(f"all agy slots busy (max_concurrent={max_concurrent})")` → exits `1`.
- `mad release --claim-id ID --token TOKEN [--outcome released]`:
  - Calls `backend.release_slot(claim_id=ns.claim_id, fencing_token=ns.token, outcome=ns.outcome)`.
  - Prints `{"released": true}` to stdout and exits `0`.
  - On `MadsError` (`LEASE_LOST`, `NOT_FOUND`, `VALIDATION`), raises `ValueError(exc.message)` → exits `1`.

## Exhaustive Pre-Build Test Matrix

| ID | Scenario | Category | Tier | Target Test File |
|---|---|---|---|---|
| `T-01` | `FilesBackend` and `MadsBackend` both satisfy `CoordinationBackend` | Happy / Contract | `unit` | `tests/test_backend_contract.py` |
| `T-02` | `take_handoff` in `mads` mode claims oldest open handoff and second taker raises `ValueError("no open handoff")` | Happy + Concurrency | `unit` | `tests/test_backend_contract.py` |
| `T-03` | `take_handoff` in `files` mode reads and validates `.opengsd_handoff.md` (and raises `ValueError` if missing) | Happy + Negative | `unit` | `tests/test_backend_files.py` |
| `T-04` | `claim_slot` in `mads` mode acquires `agy:slot:1`, then `agy:slot:2`, and 3rd call raises `ValueError("all agy slots busy")` | Boundary / Concurrency | `unit` | `tests/test_backend_contract.py` |
| `T-05` | `release_slot` in `mads` mode frees slot so next `claim_slot` re-acquires with higher `fencing_token`; stale token raises `ValueError` | Idempotency / Fault | `unit` | `tests/test_backend_contract.py` |
| `T-06` | `claim_slot` and `release_slot` in `files` mode are deterministic no-ops returning valid dicts | Happy / Parity | `unit` | `tests/test_backend_files.py` |
| `T-07` | CLI `mad handoff --write --take` is rejected with exit `2`; `mad handoff --take --print` and `mad claim`/`mad release` work end-to-end | CLI / Negative | `system` | `tests/cli.bats` |
| `T-08` | Real `mads` binary (`~/src/meso/mads/target/release/mads`) passes `handoff --take` single-consumption and 2-slot `claim`/`release` | Integration | `integration` | `tests/test_mads_integration.py` |

## Tasks

### Task 1: Extend `mads_stub.py` with `take_handoff`, `claim_task`, and `release_task`

**Files:**
- Modify: `tests/stubs/mads_stub.py`, `tests/test_mads_client.py`
- Produces: Stateful `take_handoff`, `claim_task`, and `release_task` in `tests/stubs/mads_stub.py` matching `mads.contract/1`.

- [x] Write failing unit tests in `tests/test_mads_client.py`:
  - `write_handoff` followed by `take_handoff` returns `{handoff_id, from_agent, run_id, problem, steps, context_refs, verify}` on first call and raises `MadsError("NOT_FOUND")` on second call.
  - `claim_task` on `agy:slot:1` returns `{claim_id, fencing_token: 1, expires_at}`; second live claim on `agy:slot:1` raises `MadsError("CONFLICT")`; `release_task` returns `{"released": True}`; re-claiming `agy:slot:1` returns `fencing_token: 2`; releasing with wrong token raises `MadsError("LEASE_LOST")`.
- [x] Implement `take_handoff`, `claim_task`, and `release_task` in `tests/stubs/mads_stub.py`.
- [x] Verify: `pytest tests/test_mads_client.py -q` → all pass.

### Task 2: `CoordinationBackend` protocol, `FilesBackend`, and `MadsBackend` methods (`COORD-01`, `COORD-02`, `COORD-03`)

**Files:**
- Modify: `mad/backend.py`, `mad/files_backend.py`, `mad/mads_backend.py`
- Test: `tests/backend_contract.py`, `tests/test_backend_files.py`, `tests/test_backend_contract.py`
- Produces: `CoordinationBackend` protocol and `take_handoff`, `claim_slot`, `release_slot` on `FilesBackend` and `MadsBackend`.

- [x] Write failing tests (`T-01`..`T-06`) in `tests/test_backend_files.py`, `tests/backend_contract.py`, and `tests/test_backend_contract.py`.
- [x] Implement `CoordinationBackend` in `mad/backend.py`, no-op/file methods in `mad/files_backend.py`, and `mads` tool calls in `mad/mads_backend.py`.
- [x] Verify: `pytest tests/test_backend_files.py tests/test_backend_contract.py -q` → all pass.

### Task 3: CLI wiring (`mad handoff --take`, `mad claim`, `mad release`) and end-to-end verification

**Files:**
- Modify: `mad/cli.py`, `tests/cli.bats`, `tests/test_mads_integration.py`, `AGENTS.md`, `docs/user-guide/state-backends.md`
- Produces: CLI flags/subcommands and real-binary integration test (`T-07`, `T-08`).

- [x] Write failing CLI and integration tests in `tests/cli.bats` and `tests/test_mads_integration.py`.
- [x] Wire `--take` / `--print` on `mad handoff` and subcommands `mad claim` / `mad release` in `mad/cli.py`.
- [x] Update `AGENTS.md` and `docs/user-guide/state-backends.md` with the new commands.
- [x] Verify:
  - `pytest -q`
  - `MADS_BIN=/home/bill/src/meso/mads/target/release/mads pytest -q`
  - `bats tests/cli.bats`
  - `shellcheck bin/mad scripts/*.sh`

## Threat & Failure Model

| Threat / edge case | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Two `agy` workers call `mad handoff --take` simultaneously | Med | Med | `mads tool take_handoff` executes in one `BEGIN IMMEDIATE` SQLite transaction; loser gets `NOT_FOUND` → exit `1` |
| Worker crashes while holding `agy:slot:N` | Med | Low | `claim_task` carries a bounded TTL (`ttl_s`, default 60s); `mads` automatically expires stale claims on the next `claim_task` |
| Stale worker tries to release a reclaimed slot | Low | Low | `mads` checks `fencing_token` and returns `LEASE_LOST` → `mad release` exits `1` |
| `mad handoff --write` and `--take` passed together | Low | Low | `cli.py` rejects with `parser.error(...)` (exit `2`) |

## Verification Plan

```bash
pytest -q
MADS_BIN=/home/bill/src/meso/mads/target/release/mads pytest -q
bats tests/cli.bats
shellcheck bin/mad scripts/*.sh
```

Expected: all existing + new Python unit/contract/integration tests and BATS CLI tests pass with zero warnings from `shellcheck`.
