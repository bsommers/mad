# Phase 5: Worker leases & atomic handoff claims - Context

**Gathered:** 2026-11-07
**Status:** Planned (awaiting user go-ahead for code execution)

<domain>
## Phase Boundary

Prevent concurrent `agy` workers from exceeding `agy_max_concurrent` or double-consuming a handoff when `MAD_STATE_BACKEND=mads`, while remaining a safe no-op in `files` mode (`COORD-01..03`). Out of this phase: any change to `route.classify`, any change to `StateBackend`'s 5 core methods, any database access from `mad`'s own code, or API keys.

</domain>

<decisions>
## Decisions

- **D-01 (`StateBackend` + `CoordinationBackend` split):** Keep `StateBackend` at its 5 members (`append_log`, `write_handoff`, `fetch_context`, `read_telemetry`, `write_telemetry`) per `designing-plugin-contracts` Rule 1 (2–5 members per protocol). Introduce a separate 3-member `CoordinationBackend` protocol (`take_handoff`, `claim_slot`, `release_slot`) in `mad/backend.py` implemented by both `FilesBackend` and `MadsBackend`.
- **D-02 (`mad handoff --take`):** In `mads` mode, `mad handoff --take` calls `mads tool take_handoff` (`{"agent": agent, "run_id": MAD_RUN_ID}`), exports the taken handoff Markdown to `.opengsd_handoff.md` atomically, and either launches `agy` (default), prints the launch argv (`--dry-run`), or prints the claimed Markdown (`--print`). A second taker when no open handoff remains receives `NOT_FOUND` from `mads`, mapped to `ValueError("no open handoff")` and exit code `1`. In `files` mode, `take_handoff` reads and validates `.opengsd_handoff.md`.
- **D-03 (`mad claim` and `mad release`):** `mad claim [--agent agy] [--ttl 60]` probes `agy:slot:1..agy_max_concurrent` (default `2` from `config/routing.json`) via `mads tool claim_task` in `mads` mode, returning the first granted lease JSON (`{slot, resource, claim_id, fencing_token, expires_at}`) with exit `0`, or exiting `1` when all slots return `CONFLICT`. `mad release --claim-id ID --token TOKEN [--outcome released]` calls `mads tool release_task` and prints `{"released": true}` (exit `0`, or `1` on `LEASE_LOST`/`NOT_FOUND`). In `files` mode, `claim_slot` and `release_slot` return deterministic no-op JSON responses and exit `0`.

## Canonical references

- Step plan: `docs/superpowers/plans/2026-11-07-phase-5-worker-leases-and-handoff-claims.md`
- mads spec and wire contract (`mads.contract/1`): `~/src/meso/mads/SPEC.md` §4.1, §4.4

</decisions>
