# Phase 4: Pluggable State Backend Implementation Plan

> **Status: DRAFT, for later consideration. Do not start without the user's go-ahead** (`config.json` is `interactive`, `auto_advance` false). Depends on the `mads` store (`~/src/meso/mads/SPEC.md`) reaching its Task 10 (CLI verbs stable). Phase 4 must also be safe to ship with `mads` never built: the `files` backend is the default and is today's behavior.
>
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let mad keep its shared state either in the current controlled Markdown/JSON files (default, unchanged) or in the `mads` embedded store, selected by one setting, with the same CLI behavior and exit codes either way.

**Architecture:** Introduce a small `StateBackend` protocol in `mad/backend.py`. `FilesBackend` wraps today's `store.py`, `handoff.py`, `context.py` and `telemetry.py` without changing their output. `MadsBackend` (`mad/mads_client.py`) calls the `mads` CLI over `subprocess` with JSON in/out. `cli.py` asks `backend.get_backend(root)` and never branches on backend names. When `mads` is selected but missing, mad falls back to `files` and logs one `note` entry (graceful degradation).

**Tech Stack:** Bash, Python 3.14 standard library, pytest (tests only), bats, shellcheck. External, optional: the `mads` binary.

**Spec:** `docs/superpowers/specs/2026-10-23-mad-design.md` (§3 state files, §5 CLI) plus the `mads` contract `mads.contract/1` in `~/src/meso/mads/SPEC.md` §4. GSD: create `.planning/phases/04-pluggable-state-backend/04-CONTEXT.md` and `04-01-PLAN.md` pointing here when the phase is approved.

## Why this phase exists (measured)

- mad's state today: 18-line `.global_dev_log.md`, one telemetry JSON, Markdown handoff. It has no atomic claim, no checkpoint or rollback, and no way for climah (Rust) to read or write the same state except by parsing mad's files.
- `climah` has one real run on disk: 73 events, 23.9 KB. Volume is small, so the value of a store is coordination primitives, not scale.
- Nothing is measured failing in mad's file mode. This phase is optional until a coordination need (parallel `agy` workers, climah integration) is real. `agy_max_concurrent` is already 2 in `config/routing.json`, which is the first place a claim primitive would pay off.

## AGENTS.md amendment (apply in Task 5, not before)

Replace the "Out of scope" bullet `SQLite or Redis` and the invariant block with:

```markdown
- **Out of scope:** API keys or direct API calls (subscriptions only), Redis, any GUI, and any
  database access from mad's own code. (SQLite is allowed only inside the separate `mads`
  binary; mad reaches it through `mads --json` and never opens the database.)

## State backends

mad keeps shared state in one of two backends, chosen by `MAD_STATE_BACKEND`
(`files` default | `mads`) or `"state_backend"` in `config/routing.json`:

- `files`: the controlled Markdown/JSON files (`.global_dev_log.md`, `.active_context/`,
  `.opengsd_handoff.md`, `.agent_telemetry.json`). Authoritative. Stdlib only. Default.
- `mads`: the `mads` store is authoritative; the same files are regenerated projections
  (`mads export`) so `agy -i "$(cat .opengsd_handoff.md)"` keeps working.

Invariants that hold for both: `.global_dev_log.md` stays append-only in effect; every state
file is OKF Markdown with frontmatter; `route.classify` stays pure; no API keys; `mad/` runtime
imports only the standard library (`mads_client.py` uses `subprocess` and `json`).
If `mads` is selected but not on `PATH`, mad falls back to `files` and writes one `note` log entry.
```

## Global Constraints

- Runtime code imports only the Python standard library; no new `pip` dependency.
- Default behavior (`files`) is byte-identical to today: all existing `pytest -q` tests and `bats tests/cli.bats` pass with no edits to their assertions.
- Exit codes unchanged: `0` ok, `1` runtime error, `2` usage error, `10` handoff needed. `mads` error codes are mapped, never leaked as mad exit codes.
- No test launches real `claude`, `agy`, or the real `mads`: tests use `MAD_CLAUDE_BIN`, `MAD_AGY_BIN`, and `MADS_BIN` pointing at stubs.
- `route.classify` stays pure and untouched.
- Backend choice must never change routing decisions.

## Contracts

```python
# mad/backend.py
from typing import Protocol, Mapping, Sequence
from pathlib import Path

class StateBackend(Protocol):            # 5 members; add variation via config, not methods
    def append_log(self, kind: str, agent: str, fields: Mapping[str, str]) -> str: ...
    def write_handoff(self, agent: str, problem: str, steps: Sequence[str],
                      context_files: Sequence[str] = (), verify_cmds: Sequence[str] = ()) -> Path: ...
    def fetch_context(self, keywords: Sequence[str], budget_bytes: int) -> str: ...
    def read_telemetry(self) -> dict: ...
    def write_telemetry(self, data: Mapping) -> Path: ...

def get_backend(root: Path, env: Mapping[str, str] | None = None) -> StateBackend: ...
```

`mads` wire calls used (all `mads --json <verb>`; one JSON object in on stdin, one out):
`event.append`, `write_handoff`, `get_agent_context`, `put_artifact` (kind `telemetry`),
`get_artifact`, `export`. Errors are the closed set `USAGE CONFLICT NOT_FOUND VALIDATION
STORE_BUSY LEASE_LOST FORBIDDEN INTERNAL`; `mads_client` raises `MadsError(code, message,
retryable)` and `MadsBackend` maps `STORE_BUSY` to up to 3 jittered retries, everything else to
mad's exit code `1` with the message on stderr.

## Tasks

### Task 1: Backend protocol and `FilesBackend` (pure refactor)

**Files:**
- Create: `mad/backend.py`, `mad/files_backend.py`
- Modify: `mad/cli.py` (route calls through `get_backend`)
- Test: `tests/test_backend_files.py`

- [ ] Write failing tests: `FilesBackend.append_log` output equals `store.append_log` for the same inputs; `write_handoff` file equals `handoff.write_handoff` output; unknown `MAD_STATE_BACKEND` value exits `2`.
- [ ] Implement `FilesBackend` as thin call-throughs; wire `cli.py`.
- [ ] Verify: `pytest -q` → all pre-existing tests plus new ones pass; `bats tests/cli.bats` → unchanged pass count.

### Task 2: Backend contract test suite

**Files:**
- Create: `tests/backend_contract.py` (shared checks), `tests/test_backend_contract.py`
- Test: parametrized over `FilesBackend` now, `MadsBackend` in Task 4.

- [ ] Write the shared contract: append-only log growth, handoff validation (empty problem or zero steps raises `ValueError`), context never exceeds `budget_bytes`, telemetry round-trip.
- [ ] Verify: `pytest tests/test_backend_contract.py -q` → pass for `FilesBackend`.

### Task 3: `mads_client` over `subprocess`

**Files:**
- Create: `mad/mads_client.py` (≤150 lines), `tests/stubs/mads_stub.py`, `tests/test_mads_client.py`

- [ ] Write failing tests with `MADS_BIN` pointing at the stub: success envelope parsed; each error code raises `MadsError` with the right `retryable`; non-JSON stdout or non-zero exit with no envelope raises `MadsError("INTERNAL")`; timeout (default 10 s, `MADS_TIMEOUT_S`) raises.
- [ ] Implement `call(verb, payload) -> dict` (argv list, never `shell=True`; payload via stdin).
- [ ] Verify: `pytest tests/test_mads_client.py -q`; `shellcheck` unaffected.

### Task 4: `MadsBackend` and degradation

**Files:**
- Create: `mad/mads_backend.py`
- Modify: `mad/backend.py` (`get_backend` selection and fallback), `tests/test_backend_contract.py`

- [ ] Write failing tests: `MadsBackend` passes the shared contract against the stub; when `mads` is absent, `get_backend` returns `FilesBackend` and exactly one `note` entry is appended per process; a stub that returns `STORE_BUSY` twice then OK succeeds (retry); `NOT_FOUND` on context fetch yields empty context, not a crash.
- [ ] Implement; keep all `mads` verbs behind this class.
- [ ] Verify: `pytest -q`; `bats tests/cli.bats` with `MAD_STATE_BACKEND=mads MADS_BIN=<stub>` and with it unset → both pass.

### Task 5: Real-binary integration, projections, AGENTS.md amendment

**Files:**
- Modify: `AGENTS.md` (apply the amendment above), `CLAUDE.md`/`GEMINI.md` untouched (they point to AGENTS.md)
- Create: `tests/test_mads_integration.py` (skipped unless `MADS_BIN` is a real binary), `docs/user-guide/state-backends.md`

- [ ] Write integration test: `init`, `log`, `handoff --write`, `fetch`, `check` against a temp project in `mads` mode; assert the exported `.opengsd_handoff.md` equals `FilesBackend` output for the same inputs (modulo the `updated:` date) and that the handoff validates with `validate_handoff`.
- [ ] Apply the AGENTS.md amendment; write the user-guide page (when to choose each backend, how to switch, how to migrate with `mads import --from mad`, how to roll back by setting `files`).
- [ ] Verify: full suite `pytest -q && bats tests/cli.bats && shellcheck bin/mad scripts/*.sh`; integration test run once manually with the real `mads` and the result noted in `04-01-SUMMARY.md`.

## Threat & Failure Model

| Threat / edge case | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `mads` missing or crashes mid-call | Med | Low | Fall back to `files`, one `note` entry; no data loss because projections are written on every state change |
| Two sources of truth after switching backends | Med | Med | Switching is explicit and documented; `mads import --from mad` is idempotent; never run both writers on the same run (`mads` refuses via `store_mode`) |
| Backend output drifts from file format | Med | Med | Golden-equality tests in Tasks 1, 2, 5 |
| Untrusted agent text reaches `mads` | High | Med | `mad` passes values only as JSON on stdin (no shell interpolation); `mads` validates and redacts |
| Hang on `mads` call | Low | Med | Timeout per call; failure falls back to `files` for read paths and exits `1` for writes |
| Scope creep into routing | Low | Med | Global constraint: `route.classify` untouched; a test asserts decisions are identical in both modes |

## Verification Plan

```bash
pytest -q
bats tests/cli.bats
shellcheck bin/mad scripts/*.sh
MAD_STATE_BACKEND=mads MADS_BIN=tests/stubs/mads_stub.py pytest -q tests/test_backend_contract.py
# once, with the real binary:
MADS_BIN=$(command -v mads) pytest -q tests/test_mads_integration.py
```

Expected: all pre-existing tests still pass with no assertion edits; the contract suite passes for both backends; integration test passes or is explicitly skipped with a stated reason.

## Open items to settle at approval time

- Whether `state_backend` lives in `config/routing.json` or a new `config/state.json` (default: `routing.json`, one config file).
- Whether telemetry should move at all. Claude-window counting reads local transcripts and is host-specific; default is to keep `telemetry` on `files` even in `mads` mode and mirror it. Decide with the user.
